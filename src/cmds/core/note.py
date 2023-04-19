import logging

import arrow
import discord
from discord import ApplicationContext, SlashCommandGroup
from discord.ext import commands
from discord.ext.commands import has_any_role

from src.bot import Bot
from src.core import settings
from src.database.models import UserNote
from src.database.session import AsyncSessionLocal
from src.helpers.getters import get_member_safe

logger = logging.getLogger(__name__)


class NoteCog(commands.Cog):
    """Manage user notes."""

    def __init__(self, bot: Bot):
        self.bot = bot

    note = SlashCommandGroup("note", "Manage user notes.", guild_ids=settings.guild_ids)

    @note.command(description="Add a note to the users history records. Only intended for staff convenience.")
    @has_any_role(*settings.role_groups.get("ALL_ADMINS"), *settings.role_groups.get("ALL_MODS"))
    async def add(self, ctx: ApplicationContext, user: discord.Member, note: str) -> None:
        """Add a note to the users history records. Only intended for staff convenience."""
        member = await get_member_safe(user, ctx.guild)

        if len(note) == 0:
            await ctx.respond("The note is empty. Try again...")
            return

        moderator_id = ctx.user.id
        today = arrow.utcnow().format("YYYY-MM-DD")
        user_note = UserNote(user_id=member.id, note=note, date=today, moderator_id=moderator_id)
        async with AsyncSessionLocal() as session:
            session.add(user_note)
            await session.commit()

        await ctx.respond("Note added.")

    @note.command(description="Remove a note from a user by providing the note ID to remove.")
    @has_any_role(*settings.role_groups.get("ALL_ADMINS"), *settings.role_groups.get("ALL_SR_MODS"))
    async def remove(self, ctx: ApplicationContext, note_id: int) -> None:
        """Remove a note from a user by providing the note ID to remove."""
        async with AsyncSessionLocal() as session:
            user_note = await session.get(UserNote, note_id)
            if user_note:
                await session.delete(user_note)
                await session.commit()
                await ctx.respond(f"Note #{note_id} has been deleted.")
            else:
                await ctx.respond(f"Note #{note_id} has not been found.")


def setup(bot: Bot) -> None:
    """Load the `NoteCog` cog."""
    bot.add_cog(NoteCog(bot))
