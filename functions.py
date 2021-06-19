import discord
from discord.ext import commands

import config


async def report_error(bot: commands.Bot, e):
    await bot.get_channel(config.LOG_CHANNEL_ID).send(e)


def embed_message():
    ...
