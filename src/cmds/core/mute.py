from datetime import datetime

import discord
from discord import ApplicationContext, slash_command
from discord.errors import Forbidden
from discord.ext import commands
from discord.ext.commands import has_any_role

from src.bot import Bot
from src.core import settings
from src.database.models import Mute
from src.database.session import AsyncSessionLocal
from src.helpers.ban import unmute_member
from src.helpers.checks import member_is_staff
from src.helpers.duration import validate_duration
from src.helpers.getters import get_member_safe
from src.helpers.schedule import schedule


class MuteCog(commands.Cog):
    """Mute related commands."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command(
        guild_ids=settings.guild_ids,
        description="Mute a person (adds the Muted role to person)."
    )
    @has_any_role(*settings.role_groups.get("ALL_ADMINS"), *settings.role_groups.get("ALL_MODS"))
    async def mute(self, ctx: ApplicationContext, user: discord.Member, duration: str, reason: str) -> None:
        """Mute a person (adds the Muted role to person)."""
        member = await get_member_safe(user, ctx.guild)
        if member is None:
            await ctx.respond(f"{user.mention} is not in this server.")
            return

        if member_is_staff(member):
            await ctx.respond("You cannot mute another staff member.")
            return

        dur, dur_exc = validate_duration(duration)
        if dur_exc:
            await ctx.respond(dur_exc, delete_after=15)
            return

        mute_ = Mute(
            user_id=member.id,
            reason=reason if reason else "Time to shush, innit?",
            moderator_id=ctx.user.id,
            unmute_time=dur,
        )
        async with AsyncSessionLocal() as session:
            session.add(mute_)

        role = ctx.guild.get_role(settings.roles.MUTED)
        await member.add_roles(role)
        await ctx.respond(f"{member.mention} ({member.id}) has been muted for {duration}.")
        try:
            await member.send(f"You have been muted for {duration}. Reason:\n>>> {reason}")
        except Forbidden:
            await ctx.respond(f"Cannot DM {member.mention} ({member.id}) due to their privacy settings.")

        self.bot.loop.create_task(schedule(unmute_member(ctx.guild, member), run_at=datetime.fromtimestamp(dur)))

    @slash_command(
        guild_ids=settings.guild_ids, description="Unmute the user removing the Muted role."
    )
    @has_any_role(*settings.role_groups.get("ALL_ADMINS"), *settings.role_groups.get("ALL_MODS"))
    async def unmute(self, ctx: ApplicationContext, user: discord.Member) -> None:
        """Unmute the user removing the Muted role."""
        member = await get_member_safe(user, ctx.guild)

        if member is None:
            await ctx.respond("Error: Cannot retrieve member.")
            return

        await unmute_member(ctx.guild, member)
        await ctx.respond(f"{member.mention} ({member.id}) has been unmuted.")


def setup(bot: Bot) -> None:
    """Load the `MuteCog` cog."""
    bot.add_cog(MuteCog(bot))
