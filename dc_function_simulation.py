
import warnings

from discord.ext.commands.errors import *

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

def dc_print(channel, user: Union[discord.User, discord.Member]):
    def new_print(*values: Any, sep=" ", end="\n") -> None:
        import tracemalloc
        #tracemalloc.start()
        text =  sep.join([str(x) for x in values]) + end
        if not text:
            text = "\u200B"

        asyncio.run(channel.send(
            embed=embed_message(
                title="Console output",
                description = "```" + text + "```",
                author=user,
                timestamp=False,
                color=config.COLOR.INFO
            )
        ))
        
        #tracemalloc.stop()
        return None
    return new_print


def dc_function_reload():
    import importlib
    importlib.reload(__import__(__name__))
    return "Reloaded dc_function_simulation successfully"