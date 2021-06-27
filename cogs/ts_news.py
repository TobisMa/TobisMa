import discord
from discord.ext import commands, tasks
import json


import config

class TS_News:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.external_ids = json.load(open(config.NEWS_DATA_FILE_PATH))["news"]

    @tasks.loop(seconds=config.INTERVAL)
    async def ts_news_loop(self):
        ...


def setup(bot):
    bot.add_cog(TS_News(bot))