import asyncio
import json
import logging
from typing import Any, Optional

import aiohttp
from discord.errors import HTTPException, NotFound
import config
import discord
from discord.ext import commands, tasks
from functions import *
from bs4 import BeautifulSoup, element


class TS_News(commands.Cog):

    """
    Checks news from the [tagesschau](https://www.tagesschau.de/) using their api2
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.external_ids: list[str] = self.load_external_ids()
        self.important_news_ids: set[str] = set()
        self.ts_news_loop.start()

    @tasks.loop(seconds=config.INTERVAL)
    async def ts_news_loop(self):
        await self.bot.wait_until_ready()

        logging.info("Chcking ts news...")
        articles = await self.get_articles()
        logging.info("Checked ts news")

        news_channel = self.bot.get_channel(config.NEWS_CHANNEL_ID)

        if news_channel is None:
            logging.warn("Failed to get chnnel with id '%s'" % config.NEWS_CHANNEL_ID)
            return

        for article in reversed(articles):
            await news_channel.send(embed=article)

        if len(articles):
            logging.info("Sent %i ts atricles" % len(articles))

        await self.check_important_news()
    
    @ts_news_loop.before_loop
    async def before_ts_news_loop(self):
        await self.bot.wait_until_ready()
        logging.info("ts news loop has been started")

    @ts_news_loop.after_loop
    async def after_ts_news_loop(self):
        logging.info("ts news loop has been stopped")

    @ts_news_loop.error
    async def ts_news_loop_error(self, error):
        await report_error(self.bot, error)

        while not self.ts_news_loop.is_running():
            logging.info("Trying to restart ts news loop")
            try:
                self.ts_news_loop.restart()
            except Exception as error:
                await report_error(self.bot, error)
            
            asyncio.sleep(10)

        logging.info("Restarted ts news loop")

    async def get_articles(self) -> list[discord.Embed]:
        async with aiohttp.ClientSession() as session:
            async with session.get(config.TS_NEWS_URL) as r:
                jsn: list[dict[str, Any]] = (await r.json())["news"]
        
        embeds: list[discord.Embed] = []

        for article in jsn:
            if not await self.already_sent(article):
                embeds.append(embed_message(
                    title=article["title"],
                    description=article["firstSentence"],
                    url=await self.get_link(article),
                    image=await self.get_image(article),
                    color=config.COLOR.ORANGE,
                    timestamp=datetime.fromisoformat(article["date"])
                ))
                await self.save_article(article["externalId"])

        return embeds

    async def already_sent(self, article: dict[str, Any]) -> bool:
        return article["externalId"] in self.external_ids

    async def get_image(self, article: dict[str, Any]) -> Optional[str]:
        try:
            images = article["teaserImage"]
        except KeyError:
            return None
            
        try:
            return images["videowebl"]["imageurl"]
        except KeyError:
            try:
                return images["videowebm"]["imageurl"]
            except KeyError:
                try:
                    return images["videowebs"]["imageurl"]
                except KeyError:
                    logging.info("No image in ts article '%s'" % article["externalId"])
                    return None

    async def get_link(self, article: dict[str, Any]) -> str:
        if article["shareURL"]:
            return article["shareURL"]
        else:
            return article["detailsweb"]

    async def save_article(self, id: str) -> None:
        save_json_on_path(
            file=config.NEWS_DATA_FILE_PATH, 
            path="ts",
            value=id
        )
        self.external_ids = self.load_external_ids()

    async def check_important_news(self) -> None:
        # NOTE: was never tested
        async with aiohttp.ClientSession() as session:
            async with session.get(config.TS_NEWS_BASE_URL) as r:
                if not r.ok:
                    try:
                        channel = self.bot.get_channel(config.LOG_CHANNEL_ID)
                        if channel is not None:
                            await channel.send(
                                embed=embed_message(
                                    title="Eilmeldungscheck failed",
                                    description="Something went wrong checking whether new important news were announced or not",
                                    color=config.COLOR.ERROR
                                )
                            )
                    except HTTPException:
                        logging.error("Could not report error")
                    return

                html = await r.text()
        
        soup = BeautifulSoup(html, "html.parser")
        important_news = soup.find_all("div", class_="eilmeldung")

        for n in important_news:
            logging.debug("Found important news")
            nsoup = BeautifulSoup(repr(n), "html.parser")
            link = nsoup.find("a")
            id = repr(link)
            if id in self.important_news_ids:
                continue

            channel = self.bot.get_channel(config.NEWS_CHANNEL_ID)
            if channel is None:
                await report_error(
                    self.bot, NotFound(404, "channel with id '%s' not found" % config.NEWS_CHANNEL_ID),
                    console=False
                )
                return
            if isinstance(link, element.Tag):
                await channel.send(embed=embed_message(
                    title="Eilmeldung",
                    description=link.text,
                    color=config.COLOR.RED
                ))
                logging.info("Sent important news by text")
            else:
                await channel.send(embed=embed_message(
                    title="Eilmeldung",
                    description="Eine Eilmeldung ist auf der (Tagesschauseite)[%s] zu finden" % config.TS_NEWS_BASE_URL,
                    color=config.COLOR.RED
                ))
                logging.info("Send important news with link to homepage")
        
            self.important_news_ids.add(id)

    @classmethod
    def load_external_ids(cls) -> list[str]:
        return json.load(open(config.NEWS_DATA_FILE_PATH))["ts"]


def setup(bot):
    bot.add_cog(TS_News(bot))
