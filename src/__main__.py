import logging

from src.bot import bot
from src.core import settings
from src.utils.extensions import walk_extensions
from src.webhooks.server import server

log = logging.getLogger(__name__)

# Load all cogs extensions.
for ext in walk_extensions():
    bot.load_extension(ext)

if __name__ == "__main__":
    log.info("Starting bot & webhook server")
    bot.loop.create_task(server.serve())
    bot.loop.create_task(bot.run(settings.bot.TOKEN))
