from unittest.mock import patch

import pytest

from src.cmds.core import channel_manage
from tests.helpers import MockTextChannel


class TestChannelManage:
    """Test the `ChannelManage` cog."""

    @pytest.mark.asyncio
    async def test_no_hints(self, bot, ctx):
        """Test the response of the `no_hints` command."""
        cog = channel_manage.ChannelManageCog(bot)

        # Invoke the command.
        await cog.no_hints.callback(cog, ctx)

        args, kwargs = ctx.channel.send.call_args
        content = args[0]

        # Command should respond with an embed.
        assert isinstance(content, str)

        assert content.startswith("No hints are allowed")

    @pytest.mark.asyncio
    async def test_spoiler_without_url(self, bot, ctx):
        """Test the response of the `spoiler` command without url."""
        cog = channel_manage.ChannelManageCog(bot)

        # Invoke the command.
        await cog.spoiler.callback(cog, ctx, url="")

        args, kwargs = ctx.send.call_args
        content = args[0]

        # Command should respond with an embed.
        assert isinstance(content, str)

        assert content == "Please provide the spoiler URL."

    @pytest.mark.asyncio
    async def test_spoiler(self, bot, ctx):
        """Test the response of the `spoiler` command."""
        cog = channel_manage.ChannelManageCog(bot)
        mock_channel = MockTextChannel()

        with patch.object(bot, "get_channel", return_value=mock_channel):
            # Invoke the command.
            await cog.spoiler.callback(cog, ctx, "https://www.definitely-a-spoiler.com/")

        args, kwargs = ctx.respond.call_args
        content = args[0]
        ephemeral = kwargs.get("ephemeral")
        delete_after = kwargs.get("delete_after")

        # Command should respond with an embed.
        assert isinstance(content, str)
        assert isinstance(ephemeral, bool)
        assert isinstance(delete_after, int)

        assert content == "Thanks for the reporting the spoiler."
        assert ephemeral is True
        assert delete_after == 15

    @pytest.mark.asyncio
    @pytest.mark.parametrize("seconds", [10, str(10)])
    async def test_slowmode_success(self, bot, ctx, seconds):
        """Test `slowmode` command with valid seconds."""
        cog = channel_manage.ChannelManageCog(bot)

        channel = MockTextChannel(name="slow-mode")
        # Invoke the command.
        await cog.slowmode.callback(cog, ctx, channel=channel, seconds=seconds)

        args, kwargs = ctx.respond.call_args
        content = args[0]

        # Assert channel was edited
        channel.edit.assert_called_once_with(slowmode_delay=int(seconds))
        # Assert response was sent
        assert isinstance(content, str)
        assert content == f"Slow-mode set in {channel.name} to {seconds} seconds."
        ctx.respond.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "seconds, expected_seconds", [(300, 30), (-10, 0)]
    )
    async def test_slowmode_with_seconds_out_of_bounds(self, bot, ctx, seconds, expected_seconds):
        """Test `slowmode` command with out of bounds seconds."""
        cog = channel_manage.ChannelManageCog(bot)

        channel = MockTextChannel(name="slow-mode")
        # Invoke the command.
        await cog.slowmode.callback(cog, ctx, channel=channel, seconds=seconds)

        args, kwargs = ctx.respond.call_args
        content = args[0]

        # Assert channel was edited
        channel.edit.assert_called_once_with(slowmode_delay=expected_seconds)
        # Assert response was sent
        assert isinstance(content, str)
        assert content == f"Slow-mode set in {channel.name} to {expected_seconds} seconds."
        ctx.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_slowmode_seconds_as_invalid_string(self, bot, ctx):
        """Test the response of the `slowmode` command with invalid seconds string."""
        cog = channel_manage.ChannelManageCog(bot)

        seconds = "not seconds"
        # Invoke the command.
        await cog.slowmode.callback(cog, ctx, channel=MockTextChannel(), seconds=seconds)

        args, kwargs = ctx.respond.call_args
        content = args[0]

        # Command should respond with a string.
        assert isinstance(content, str)
        assert content == f"Malformed amount of seconds: {seconds}."
        ctx.respond.assert_called_once()

    def test_setup(self, bot):
        """Test the setup method of the cog."""
        # Invoke the command
        channel_manage.setup(bot)

        bot.add_cog.assert_called_once()
