import logging
import traceback

import discord
from discord.ext import commands
from discord.ext.commands.errors import ExtensionError

import config
from functions import *

# set other loggers on error
dc_logger = logging.getLogger(name="discord")
dc_logger.setLevel(level=logging.ERROR)

aiohttp_logger = logging.getLogger(name="aiohttp")
aiohttp_logger.setLevel(level=logging.ERROR)

urllib3_logger = logging.getLogger(name="urllib3")
urllib3_logger.setLevel(level=logging.ERROR)

asyncio_logger = logging.getLogger(name="asyncio")
asyncio_logger.setLevel(level=logging.ERROR)

logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s | %(levelname)s: %(filename)s - %(lineno)s: %(msg)s', 
    force=True
)

logging.info("All modules imported")


bot = commands.Bot(
    command_prefix=".",
    status=getattr(discord.Status, config.STATUS, "offline")
)


# loading extensions
for ext_name in config.EXTENSIONS:
    try:
        bot.load_extension(ext_name)
    except ExtensionError as e:
        logging.warning("Extension '%s' not loaded" % ext_name)

bot.run(config.TOKEN)
