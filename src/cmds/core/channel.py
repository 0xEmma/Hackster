import logging

from discord import ApplicationContext, slash_command
from discord.abc import GuildChannel
from discord.ext import commands
from discord.ext.commands import has_any_role

from src.bot import Bot
from src.core import settings

logger = logging.getLogger(__name__)


class ChannelCog(commands.Cog):
    """Ban related commands."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command(
        guild_ids=settings.guild_ids,
        description="Add slow-mode to the channel. Specifying a value of 0 removes the slow-mode again."
    )
    @has_any_role(*settings.role_groups.get("ALL_ADMINS"), *settings.role_groups.get("ALL_MODS"))
    async def slowmode(
        self, ctx: ApplicationContext, channel: GuildChannel, seconds: int
    ) -> None:
        """Add slow-mode to the channel. Specifying a value of 0 removes the slow-mode again."""
        guild = ctx.guild

        if isinstance(channel, str):
            try:
                channel_id = int(channel.replace("<#", "").replace(">", ""))
                channel = guild.get_channel(channel_id)
            except ValueError:
                await ctx.respond(
                    f"I don't know what {channel} is. Please use #channel-reference or a channel ID.", )
                return
        try:
            seconds = int(seconds)
        except ValueError:
            await ctx.respond(f"Malformed amount of seconds: {seconds}.")
            return

        if seconds < 0:
            seconds = 0
        if seconds > 30:
            seconds = 30
        await channel.edit(slowmode_delay=seconds)
        await ctx.respond(f"Slow-mode set in {channel.name} to {seconds} seconds.")


def setup(bot: Bot) -> None:
    """Load the `ChannelManageCog` cog."""
    bot.add_cog(ChannelCog(bot))
