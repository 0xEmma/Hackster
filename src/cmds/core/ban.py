import logging
from datetime import datetime

import discord
from discord import ApplicationContext, slash_command
from discord.ext import commands
from discord.ext.commands import has_any_role
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from src.bot import Bot
from src.core import settings
from src.database.models import Ban, Infraction
from src.database.session import AsyncSessionLocal
from src.helpers.ban import add_infraction, ban_member, unban_member
from src.helpers.duration import validate_duration
from src.helpers.getters import get_member_safe
from src.helpers.schedule import schedule

logger = logging.getLogger(__name__)


class BanCog(commands.Cog):
    """Ban related commands."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command(guild_ids=settings.guild_ids, description="Ban a user from the server permanently.")
    @has_any_role(*settings.role_groups.get("ALL_ADMINS"), *settings.role_groups.get("ALL_SR_MODS"))
    async def ban(self, ctx: ApplicationContext, user: discord.Member, reason: str) -> None:
        """Ban a user from the server permanently."""
        member = await get_member_safe(user, ctx.guild)
        response = await ban_member(self.bot, ctx.guild, member, "500w", reason, ctx.user, needs_approval=False)
        if response:
            await ctx.respond(response.message, delete_after=response.delete_after)

    @slash_command(
        guild_ids=settings.guild_ids, description="Ban a user from the server temporarily."
    )
    @has_any_role(
        *settings.role_groups.get("ALL_ADMINS"), *settings.role_groups.get("ALL_MODS"),
        *settings.role_groups.get("ALL_HTB_STAFF")
    )
    async def tempban(self, ctx: ApplicationContext, user: discord.Member, duration: str, reason: str) -> None:
        """Ban a user from the server temporarily."""
        member = await get_member_safe(user, ctx.guild)
        response = await ban_member(self.bot, ctx.guild, member, duration, reason, ctx.user, needs_approval=True)
        if response:
            await ctx.respond(response.message, delete_after=response.delete_after)

    @slash_command(guild_ids=settings.guild_ids, description="Unbans a user from the server.")
    @has_any_role(
        *settings.role_groups.get("ALL_ADMINS"), *settings.role_groups.get("ALL_MODS"),
        *settings.role_groups.get("ALL_HTB_SUPPORT")
    )
    async def unban(self, ctx: ApplicationContext, user: discord.Member) -> None:
        """Unbans a user from the server."""
        member = await get_member_safe(user, ctx.guild)
        user = await unban_member(ctx.guild, member)
        if user is None:
            await ctx.respond("Failed to unban user. Are they perhaps not banned at all?")
            return

        await ctx.respond(f"User #{user.id} has been unbanned.")

    @slash_command(description="Deny a ban request and unban the member.")
    @has_any_role(*settings.role_groups.get("ALL_ADMINS"), *settings.role_groups.get("ALL_SR_MODS"))
    async def deny(self, ctx: ApplicationContext, ban_id: int) -> None:
        """Deny a ban request and unban the member."""
        async with AsyncSessionLocal() as session:
            ban = await session.get(Ban, ban_id)
            if ban and ban.user_id:
                await session.delete(ban)
                await session.commit()
                await ctx.respond("Ban request denied. The user has been unbanned.")
            else:
                await ctx.respond("Cannot find record of ban request. Has this user already been unbanned?")
                raise NoResultFound(f"Ban with id {ban_id} not found")

    @slash_command(description="Approve a ban request.")
    @has_any_role(*settings.role_groups.get("ALL_ADMINS"), *settings.role_groups.get("ALL_SR_MODS"))
    async def approve(self, ctx: ApplicationContext, ban_id: int) -> None:
        """Approve a ban request."""
        async with AsyncSessionLocal() as session:
            ban_to_update = await session.get(Ban, ban_id)
            if not ban_to_update:
                await ctx.respond("Cannot find record of ban request. Has this user already been unbanned?")
                raise NoResultFound(f"Ban with id {ban_id} not found")
            ban_to_update.approved = True
            await session.commit()

            stmt = select(Ban).filter(Ban.id == ban_id)
            result = await session.scalars(stmt)
            ban: Ban = result.first()

        member = await get_member_safe(ban.user_id, ctx.guild)
        if not member:
            await ctx.respond(f"User {ban.user_id} not found in guild.")
            return

        self.bot.loop.create_task(
            schedule(unban_member(ctx.guild, member), run_at=datetime.fromtimestamp(ban.unban_time))
        )

        await ctx.respond("Ban approval has been recorded.")

    @slash_command(description="Dispute a ban request by changing the ban duration, then approve it.")
    @has_any_role(*settings.role_groups.get("ALL_ADMINS"), *settings.role_groups.get("ALL_SR_MODS"))
    async def dispute(self, ctx: ApplicationContext, ban_id: int, duration: str) -> None:
        """Dispute a ban request by changing the ban duration, then approve it."""
        try:
            ban_id = int(ban_id)
        except ValueError:
            await ctx.respond("Ban ID must be a number.")
            return

        dur, dur_exc = validate_duration(duration)
        if dur_exc:
            await ctx.respond(dur_exc, delete_after=15)
            return

        async with AsyncSessionLocal() as session:
            ban = await session.get(Ban, ban_id)

            if not ban or not ban.timestamp:
                await ctx.respond(f"Cannot dispute ban {ban_id}: record not found.")
                return

            ban.unban_time = dur
            ban.approved = True
            session.add(ban)
            await session.commit()

        new_unban_at = datetime.fromtimestamp(dur)
        member = await get_member_safe(ban.user_id, ctx.guild)
        if not member:
            await ctx.respond(f"User {ban.user_id} not found in guild.")
            return

        self.bot.loop.create_task(schedule(unban_member(ctx.guild, member), run_at=new_unban_at))
        await ctx.respond(
            f"Ban duration updated and approved. "
            f"The member will be unbanned on {new_unban_at.strftime('%B %d, %Y')} UTC."
        )

    @slash_command(
        guild_ids=settings.guild_ids,
        description="Warns a user of an action. Adds no weight but DMs the user about the warning and the reason why."
    )
    @has_any_role(*settings.role_groups.get("ALL_ADMINS"), *settings.role_groups.get("ALL_MODS"))
    async def warn(self, ctx: ApplicationContext, user: discord.Member, reason: str) -> None:
        """Warns a user of an action. Adds no weight but DMs the user about the warning and the reason why."""
        member = await get_member_safe(user, ctx.guild)
        if not member:
            await ctx.respond(f"User {user} not found in guild.")
            return
        await add_infraction(ctx.guild, member, 0, reason, ctx.user)

    @slash_command(
        guild_ids=settings.guild_ids,
        description="Strike the user with the selected weight. DMs the user about the strike and the reason why."
    )
    @has_any_role(*settings.role_groups.get("ALL_ADMINS"), *settings.role_groups.get("ALL_MODS"))
    async def strike(self, ctx: ApplicationContext, user: discord.Member, weight: int, reason: str) -> None:
        """Strike the user with the selected weight. DMs the user about the strike and the reason why."""
        member = await get_member_safe(user, ctx.guild)
        if not member:
            await ctx.respond(f"User {user} not found in guild.")
            return
        await add_infraction(ctx.guild, member, weight, reason, ctx.user)

    @slash_command(
        guild_ids=settings.guild_ids,
        description="Remove a warning or a strike from a user by providing the infraction ID to remove.",
    )
    @has_any_role(*settings.role_groups.get("ALL_ADMINS"), *settings.role_groups.get("ALL_SR_MODS"))
    async def remove_infraction(self, ctx: ApplicationContext, infraction_id: int) -> None:
        """Remove a warning or a strike from a user by providing the infraction ID to remove."""
        async with AsyncSessionLocal() as session:
            infraction = await session.get(Infraction, infraction_id)
            if infraction and infraction.id:
                await session.delete(infraction)
                await session.commit()
                await ctx.respond(f"Infraction record #{infraction_id} has been deleted.")
            else:
                await ctx.respond(f"Infraction record #{infraction_id} has not been found.")
                raise NoResultFound(f"Infraction with id {infraction_id} not found")


def setup(bot: Bot) -> None:
    """Load the `BanCog` cog."""
    bot.add_cog(BanCog(bot))
