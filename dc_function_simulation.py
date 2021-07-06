from discord import file
from discord.ext.commands.errors import CommandError
from errors import *
from functions import *

def not_allowed(err: str):
    def raise_err(*args, **kwargs):
        raise FunctionNotAllowedError(err)
    return raise_err


def dc_open(filename, mode, encoding, **kwargs):
    if filename[-1] in ("/", "\\", "\\\\"):
        filename = filename[:-1]
    if filename.endswith("bot.json"):
        raise AccessError("You are not allowed to open the requested file", cause="output stream")
    elif mode not in ("r", "rb"):
        raise AccessError("You are only allowed to used read or binary read mode", cause="output stream")

    if kwargs.get("opener") is not None:
        kwargs.pop("opener")

    config.FILE_FP.append(open(filename, mode, encoding=encoding, **kwargs))

    return config.FILE_FP[-1]