import logging

from discord import ApplicationContext, Interaction, Option, WebhookMessage
from discord.ext.commands import BucketType, Cog, cooldown, slash_command

from src.bot import Bot
from src.core import settings
from src.helpers.getters import get_member_safe

logger = logging.getLogger(__name__)


class Fun(Cog):
    """Fun commands."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command(guild_ids=settings.guild_ids, name="ban-song")
    @cooldown(1, 60, BucketType.user)
    async def ban_song(self, ctx: ApplicationContext) -> Interaction | WebhookMessage:
        """Ban ban ban ban ban ..."""
        return await ctx.respond("https://www.youtube.com/watch?v=FXPKJUE86d0")

    @slash_command(guild_ids=settings.guild_ids)
    @cooldown(1, 60, BucketType.user)
    async def google(
        self, ctx: ApplicationContext, query: Option(str, "What do you need help googling?")
    ) -> Interaction | WebhookMessage:
        """Let me google that for you!"""
        goggle = query
        goggle = goggle.replace("@", "")
        goggle = goggle.replace(" ", "%20")
        goggle = goggle.replace("&", "")
        goggle = goggle.replace("<", "")
        goggle = goggle.replace(">", "")
        return await ctx.respond(f"https://lmgtfy.com?q={goggle}")

    @slash_command(guild_ids=settings.guild_ids)
    @cooldown(1, 60, BucketType.user)
    async def flag(self, ctx: ApplicationContext) -> Interaction | WebhookMessage:
        """Get the flag!"""
        return await ctx.respond("There is no flag here. Get back to hacking!")

    @slash_command(guild_ids=settings.guild_ids)
    async def sharing(self, ctx: ApplicationContext) -> Interaction | WebhookMessage:
        """CA: No 3rd Party Help!"""
        return await ctx.respond(
            "It's an ongoing competition, please respect and read the rules. 3rd party exchanging / seeking help is "
            "prohibited and a disqualification offence"
        )

    @slash_command(guild_ids=settings.guild_ids)
    async def vpn(self, ctx: ApplicationContext) -> Interaction | WebhookMessage:
        """Get the flag!"""
        await ctx.respond(
            "There is no need to use a VPN to connect for any of the CA Challenges, they are all accessible via the "
            "public IP's given when started. Not all challenges have an HTTP server however, some you need to connect "
            "via nc."
        )

    @slash_command(guild_ids=settings.guild_ids)
    @cooldown(1, 60, BucketType.user)
    async def beep(self, ctx: ApplicationContext) -> Interaction | WebhookMessage:
        """Beep Beep!"""
        car = "Beetle"
        member = await get_member_safe(ctx.user, ctx.guild)
        await member.edit(name=car)
        return await ctx.respond(f"BEEP BEEP! {car}")

    @slash_command(guild_ids=settings.guild_ids, name="start-here", default_permission=True)
    @cooldown(1, 60, BucketType.user)
    async def start_here(self, ctx: ApplicationContext) -> Interaction | WebhookMessage:
        """Get Started."""
        return await ctx.respond(
            "Get Started with the HTB Beginners Bible: https://www.hackthebox.com/blog/learn-to-hack-beginners-bible"
        )


def setup(bot: Bot) -> None:
    """Load the `Fun` cog."""
    bot.add_cog(Fun(bot))
