import logging
from typing import Tuple, Union

import discord
from discord import Member, Option, User
from discord.commands import ApplicationContext, slash_command
from discord.errors import Forbidden, HTTPException
from discord.ext import commands
from discord.ext.commands import cooldown, has_any_role
from sqlalchemy import or_, select

from src.bot import Bot
from src.core import settings
from src.database.models import HtbDiscordLink
from src.database.session import AsyncSessionLocal
from src.helpers.getters import get_member_safe, get_user_safe

logger = logging.getLogger(__name__)


class UserCog(commands.Cog):
    """Ban related commands."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command(
        guild_ids=settings.guild_ids,
        description="Changes the nickname of a user to ChangeMe."
    )
    @has_any_role(*settings.role_groups.get("ALL_ADMINS"), *settings.role_groups.get("ALL_MODS"))
    async def bad_name(self, ctx: ApplicationContext, user: discord.Member) -> None:
        """Changes the nickname of a user to ChangeMe."""
        member = await get_member_safe(user, ctx.guild)
        if not member:
            await ctx.respond(f"User {user} not found in guild.")
            return

        new_name = "ChangeMe"

        try:
            await member.edit(nick=new_name)
        except Forbidden:
            await ctx.respond(f"Cannot rename {member.mention} ({member.id}). Am I even allowed to?")
            return

        try:
            await member.send(
                "Greetings! It has been determined by a member of the staff team that your nickname "
                "was breaking the rules. As a result your nickname has been randomized. Please verify your "
                "HTB account (see #welcome for how) to have your name reset to your HTB username."
            )
        except Forbidden:
            await ctx.respond(
                f"Cannot DM user {member.mention} ({member.id}). Perhaps they do not allow DMs from strangers?"
            )
            return

        await ctx.respond(f"{member.name}'s name has been updated to {new_name}")

    @slash_command(
        guild_ids=settings.guild_ids, description="Kick a user from the server."
    )
    @has_any_role(*settings.role_groups.get("ALL_ADMINS"), *settings.role_groups.get("ALL_MODS"))
    async def kick(self, ctx: ApplicationContext, user: discord.Member, reason: str) -> None:
        """Kick a user from the server."""
        member = await get_member_safe(user, ctx.guild)
        if not member:
            await ctx.respond(f"User {user} not found in guild.")
            return

        if len(reason) == 0:
            reason = "No reason given..."

        try:
            await member.send(f"You have been kicked from {ctx.guild.name} for the following reason:\n>>> {reason}\n")
        except Forbidden as ex:
            await ctx.respond("Could not DM member due to privacy settings, however will still attempt to kick them...")
            logger.warning(f"HTTPException when trying to unban user with ID {user.id}: {ex}")
        except HTTPException as ex:
            await ctx.respond(
                "Here's a 400 Bad Request for you. Just like when you tried to ask me out, last week.",
            )
            logger.warning(f"HTTPException when trying to unban user with ID {user.id}: {ex}")
            return

        await ctx.guild.kick(user=member, reason=reason)
        await ctx.respond(f"{member.name} got the boot!")

    @staticmethod
    def _match_role(role_name: str) -> Tuple[Union[dict, None], Union[str, None]]:
        role_name = role_name.lower()
        matches = [{k: v[0]} for k, v in settings.roles_to_join.items() if role_name in k.lower()]
        if not matches:
            return None, "I don't know what role that is. Did you spell it right?"
        if len(matches) > 1:
            return None, "Matched multiple roles, try being more specific"

        return matches[0], None

    @slash_command(
        guild_ids=settings.guild_ids,
        description="Join a vanity role if such is specified, otherwise list the vanity roles available to join.",
    )
    @cooldown(1, 10, commands.BucketType.user)
    async def join(self, ctx: ApplicationContext, role_name: str) -> None:
        """Join a vanity role if such is specified, otherwise list the vanity roles available to join."""
        # No role or empty role name passed
        if not role_name or role_name.isspace():
            embed = discord.Embed(title=" ", color=0x3D85C6)
            embed.set_author(name="Join-able Roles")
            embed.set_footer(text="Use the command /join <role> to join a role.")
            for role, value in settings.roles_to_join.items():
                embed.add_field(name=role, value=value[1], inline=True)
            await ctx.respond(embed=embed)
            return

        matches, exc = self._match_role(role_name)
        if exc:
            await ctx.respond(exc, ephemeral=True)
            return

        role_id = matches.get('role_id') or matches['role_id']
        guild_role = ctx.guild.get_role(role_id)
        await ctx.user.add_roles(guild_role)
        await ctx.respond(f"Welcome to {guild_role.name}!", ephemeral=True)

    @slash_command(
        guild_ids=settings.guild_ids, description="Removes the vanity role from your user."
    )
    @cooldown(1, 10, commands.BucketType.user)
    async def leave(self, ctx: ApplicationContext, role_name: str) -> None:
        """Removes the vanity role from your user."""
        matches, exc = self._match_role(role_name)
        if exc:
            await ctx.respond(exc, ephemeral=True)
            return

        role_id = matches.get('role_id') or matches['role_id']
        guild_role = ctx.guild.get_role(role_id)
        await ctx.user.remove_roles(guild_role)
        await ctx.respond(f"You have left {guild_role.name}.")

    @slash_command(
        guild_ids=settings.guild_ids,
        description="Remove all records of identification the user has made from the database.",
    )
    @has_any_role(*settings.role_groups.get("ALL_ADMINS"), *settings.role_groups.get("ALL_MODS"))
    async def remove_user_token(self, ctx: ApplicationContext, user: discord.Member) -> None:
        """Remove all records of identification the user has made from the database."""
        member = await get_user_safe(user, self.bot)
        if not member:
            await ctx.respond(f"User {user} not found.")
            return

        async with AsyncSessionLocal() as session:
            stmt = (
                select(HtbDiscordLink)
                .filter(or_(HtbDiscordLink.discord_user_id == member.id, HtbDiscordLink.htb_user_id == member.id))
            )
            result = await session.scalars(stmt)
            htb_discord_links = result.all()

            if not htb_discord_links:
                await ctx.respond(f"Could not find '{member.id}' as a Discord or HTB ID in the records.")
                return

            for link in htb_discord_links:
                await session.delete(link)
            await session.commit()

        await ctx.respond(f"All tokens related to Discord or HTB ID '{member.id}' have been deleted.")

    @slash_command(guild_ids=settings.guild_ids, description="Show the associated HTB user.")
    @has_any_role(
        *settings.role_groups.get("ALL_ADMINS"), *settings.role_groups.get("ALL_MODS"),
        *settings.role_groups.get("ALL_HTB_STAFF")
    )
    async def whois(
        self, ctx: ApplicationContext,
        user: Option(User | Member, description="Member to show cases of", required=True)
    ) -> None:
        """Given a Discord user ID, show the associated HTB user ID and vise versa."""
        member = await get_user_safe(user, self.bot)

        if member is None:
            logger.debug(f"Could not find user by id: {user.id}")
            await ctx.respond("Error: Cannot retrieve user.")
            return

        async with AsyncSessionLocal() as session:
            stmt = (
                select(HtbDiscordLink)
                .filter(or_(HtbDiscordLink.discord_user_id == member.id, HtbDiscordLink.htb_user_id == member.id))
                .limit(1)
            )
            result = await session.scalars(stmt)
            htb_discord_link: HtbDiscordLink = result.first()

        if not htb_discord_link:
            await ctx.respond(f"Could not find '{member.id}' as a Discord or HTB ID in the records.")
            return

        fetched_user = await self.bot.fetch_user(htb_discord_link.discord_user_id_as_int)
        assert fetched_user.id == member.id

        embed = discord.Embed(title=" ", color=0xB98700)
        if member.avatar is not None:
            embed.set_author(name=member, icon_url=member.avatar)
            embed.set_thumbnail(url=member.avatar)
        else:
            embed.set_author(name=member)
        embed.add_field(name="Username:", value=fetched_user.name, inline=True)
        embed.add_field(name="Discord ID:", value=str(fetched_user.id), inline=True)
        embed.add_field(
            name="HTB Profile:",
            value=f"<https://www.hackthebox.com/home/users/profile/{htb_discord_link.htb_user_id}>", inline=False, )
        embed.set_footer(text=f"More info: /history {fetched_user.id}")
        await ctx.respond(embed=embed)


def setup(bot: Bot) -> None:
    """Load the `UserCog` cog."""
    bot.add_cog(UserCog(bot))
