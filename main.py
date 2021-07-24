import json
import traceback
from functions import embed_message, pythonize_json, report_error
import logging

import discord
from discord.ext import commands
from discord.ext.commands.errors import ConversionError, ExpectedClosingQuoteError, ExtensionError, InvalidEndOfQuotedStringError, UnexpectedQuoteError

import config
from help_command import HelpCommand

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
logging.addLevelName(25, "BOTCODECHANGE")

logging.info("All modules imported")
logging.info("Status: %s" % config.STATUS)
logging.info("Prefix: %s" % config.PREFIX)

bot = commands.Bot(
    command_prefix=config.PREFIX,
    status=getattr(discord.Status, config.STATUS),
    activity=config.ACTIVITY,
    owner_ids=config.OWNER_IDS,
    help_command=HelpCommand()
)


@bot.event
async def on_ready():
    logging.info("Bot has been started and is active")


@bot.listen("on_message")
async def on_message_event_handler(msg: discord.Message):
    if msg.author == bot.user or msg.content.startswith("~"): return


@bot.event
async def on_disconnect():
    if config.CONNECTED:
        config.CONNECTED = False
        logging.error("The bot has been disconnected")

@bot.event
async def on_connect():
    if not config.CONNECTED:
        config.CONNECTED = True
        logging.info("The bot has been connected")

@bot.event
async def on_resumed():
    logging.info("Bot resumed session")

@bot.event
async def on_error(event, *args, **kwargs):
    logging.error("Error in event '%s' with args '%s' and kwargs '%s'" % (event, args, kwargs))
    channel =  bot.get_channel(config.LOG_CHANNEL_ID)

    if channel is None:
        logging.warning("Could not find channel with id %s" % config.LOG_CHANNEL_ID)
        return

    await channel.send(
        embed=embed_message(
            title="Error in event '%s'" % event,
            description="Args: \n" + '\n'.join(str(x) for x in args) + "\nKwargs: \n" + pythonize_json(json.dumps(kwargs)),
            color=config.COLOR.ERROR,
        )
    )

@bot.event
async def on_command_error(ctx, error: BaseException):
    if isinstance(error, ConversionError):
        await ctx.send(embed=embed_message(
            title="<@%s> Parse error" % ctx.author.id,
            description="Please try to use the command again. If that doesn't work use `-help %s` and show how to use the command" % ctx.invoked_with,
            color=config.COLOR.ERROR,
            thumbnail=ctx.author.avatar_url
        ))
    elif isinstance(error, (ExpectedClosingQuoteError, InvalidEndOfQuotedStringError, UnexpectedQuoteError)):
        await ctx.send(embed=embed_message(
            title="<@%s> Quotes",
            description="If you use quotes please be sure to have an start and end quote.",
            color=config.COLOR.ERROR,
            thumbnail=ctx.author.avatar_url
        ))
    
    else:
        await on_error(error)
        await ctx.send(embed=embed_message(
            title="Unforeseen error",
            description="An error occured as you used the command. Please try again. If it doesn't work either, contact me on dc'",
            color=config.COLOR.ERROR
        ))


@bot.command()
async def test():
    raise ConversionError("fjdk", 1234)


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
