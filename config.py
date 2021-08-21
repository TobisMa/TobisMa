import json as __json
import logging
from datetime import datetime
from typing import Union

import discord
from typing_extensions import Literal

file_path = "./data/bot.json"

data = __json.load(open(file_path, "r"))


# default config from bot.json
STATUS: str = data["status"]
TOKEN: str = data["token"]
PREFIX: str = data["prefix"]
RESTRICTED_DEBUG_VARS: str = data["restricted_debug_vars"]

EXTENSIONS: list[str] = data["load_extensions"]
LOG_CHANNEL_ID: int = data["log_channel_id"]
OWNER_IDS: list[int] = data["owner_ids"]
ACTIVITY: discord.Activity = discord.Activity(
    name=data["activity"]["name"],
    type=getattr(discord.ActivityType, data["activity"]["type"]),
    #details=data["activity"]["details"],
    start=datetime.utcnow()
)

NEWS_DATA_FILE_PATH: str = data["news"]["file_path"]

GMO_NEWS_URL: str = data["news"]["url"]["gmo"]
GMO_NEWS_FILE: str = data["news"]["file"]["gmo"]
GMO_NEWS_AUTHOR: list[str] = data["news"]["author"]["gmo"]

TS_NEWS_URL_RLP: str = data["news"]["url"]["ts-rlp"]
TS_NEWS_BASE_URL: str = data["news"]["url"]["base_ts"]
TS_NEWS_FILE: str = data["news"]["file"]["ts"]

TS_NEWS_URL_BW: str = data["news"]["url"]["ts-bw"]

TS_AUTHOR: str = data["news"]["author"]["ts"]

NEWS_CHANNEL_ID: int = data["news"]["channel_id"]
INTERVAL: int = data["news"]["check_interval"]

ROLES: dict[str, dict[str, Union[int, str]]] = data["roles"]

TEAMWORK_FILE: str = data["teamwork_file"]
REMINDER_FILE: str = data["reminder_file"]

# for discord
EMPTY_CHAR = "\u200B"  # symbol: "­"

# never changing because of discord or user wished for it
JSON_AND_PY_KWDS: list[tuple[str, str]] = [
    ("false", "False"),
    ("true", "True"),
    ("Infinity", "inf"),
    ("null", "None")
]
DAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
ALLOWED_SYMBOLS_IN_CHANNEL_NAME = "-$`´µ"

# runtime
FILE_FP: list = []
CONNECTED: bool = True

# emojis
PREV_PAGE_EMOJI: str = chr(9664)  # left arrow
NEXT_PAGE_EMOJI: str = chr(9654)  # right arrow
STOP_SIGN_EMOJI: str = chr(128721)  # octagonal sign
REPEAT_EMOJI: str = chr(128257)  # :repeat:
REPEAT_ONCE_EMOJI: str = chr(128258)  # :repeat_one:
CANCEL_EMOJI: str = chr(10060)  # :x:  just a red x
CHECK_MARK = chr(9989)  # discord's white heavy check mark
PAGE_EMOJIS: list[str] = [PREV_PAGE_EMOJI, STOP_SIGN_EMOJI, NEXT_PAGE_EMOJI]

# colors
class COLOR(object):

    """Stores all results from color function from discord.Color as variable"""

    RED = discord.Color.red()
    DARK_RED = discord.Color.dark_red()
    BLUE = discord.Color.blue()
    DARK_BLUE = discord.Color.dark_blue()
    PURPLE = discord.Color.purple()
    DARK_PURPLE = discord.Color.dark_purple()
    GREEN = discord.Color.green()
    DARK_GREEN = discord.Color.dark_green()
    MAGENTA = discord.Color.dark_magenta()
    DARK_MAGENTA = discord.Color.dark_magenta()
    ORANGE = discord.Color.orange()
    DARK_ORANGE = discord.Color.dark_orange()
    LIGHT_GREY = discord.Color.light_grey()
    LIGHTER_GREY = discord.Color.lighter_grey()
    DARKER_GREY = discord.Color.darker_grey()
    DARK_GREY = discord.Color.dark_grey()
    GOLD = discord.Color.gold()
    DARK_GOLD = discord.Color.dark_gold()
    TEAL = discord.Color.teal()
    DARK_TEAL = discord.Color.dark_teal()
    BLURPLE = discord.Color.blurple()
    WHITE = discord.Color.from_rgb(254, 254, 254)
    get_custom_from_rgb = discord.Color.from_rgb
    
    HELP = discord.Color.from_rgb(255, 201, 14)

    INFO = discord.Color.from_rgb(30, 200, 255)
    WARNING = discord.Color.dark_orange()
    ERROR = discord.Color.red()


def reload() -> Literal['Reloaded config successfully']:
    import importlib
    importlib.reload(__import__(__name__))

    return "Reloaded config successfully"


logging.info("config was loaded successfully")
