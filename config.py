import json as __json

from typing_extensions import Literal

file_path = "./data/bot.json"

data = __json.load(open(file_path, "r"))


# default config
STATUS: str = data["status"]
TOKEN: str = data["token"]
EXTENSIONS: list[str] = data["load_extensions"]
LOG_CHANNEL_ID: int = data["log_channel_id"]


def reload():
    import importlib
    importlib.reload(__import__(__name__))

    return "Reloaded condig successfully"
