import logging

import discord
from discord.ext import commands
from discord.ext.commands.errors import ExtensionError

import config
#from help_command import HelpCommand

# set other loggers on error
dc_logger = logging.getLogger(name="discord")
dc_logger.setLevel(level=logging.CRITICAL)

aiohttp_logger = logging.getLogger(name="aiohttp")
aiohttp_logger.setLevel(level=logging.CRITICAL)

urllib3_logger = logging.getLogger(name="urllib3")
urllib3_logger.setLevel(level=logging.CRITICAL)

asyncio_logger = logging.getLogger(name="asyncio")
asyncio_logger.setLevel(level=logging.CRITICAL)

logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s | %(levelname)s: %(filename)s - %(lineno)s: %(msg)s', 
    force=True
)

logging.info("All modules imported")
logging.info("Status: %s" % config.STATUS)
logging.info("Prefix: %s" % config.PREFIX)

bot = commands.Bot(
    command_prefix=config.PREFIX,
    status=getattr(discord.Status, config.STATUS),
    activity=config.ACTIVITY,
    owner_ids=config.OWNER_IDS,
#    help_command=HelpCommand()
)


@bot.event
async def on_ready():
    logging.info("Bot has been started and is active")


@bot.event
async def on_message(msg: discord.Message):
    if msg.author == bot.user or msg.content.startswith("~"): return
    await bot.process_commands(msg)

# loading extensions
logging.info("Loading extensions")

for ext_name in config.EXTENSIONS:
    try:
        bot.load_extension("cogs.%s" % ext_name)
    except ExtensionError as err:
        logging.warning("failed to load extension '%s' beacuse of '%s'" % (ext_name, str(err)))
    else:
        logging.info("Extension '%s' loaded" % ext_name)


logging.info("Loaded extensions")

bot.run(config.TOKEN)
