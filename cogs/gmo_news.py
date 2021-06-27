import logging
import sys
from datetime import datetime
from typing import Coroutine

import aiohttp
import config
import discord
from bs4 import BeautifulSoup, Tag
from discord.embeds import EmptyEmbed
from discord.ext import commands, tasks
from errors import ElementNotFound
from functions import *


class GMO_News(commands.Cog):

    NO_TEXT_TAG = ["img", "video"]

    def __init__(self, bot: commands.Bot):
        commands.Cog.__init__(self)
        self.bot = bot
        self.gmo_news_loop.start()

    @tasks.loop(seconds=config.INTERVAL)
    async def gmo_news_loop(self):
        await self.bot.wait_until_ready()

        logging.info("Checking gmo news")
        articles: list[list[discord.Embed]] = await self.get_articles()
        logging.info("Checked gmo news")

        news_channel = self.bot.get_channel(config.NEWS_CHANNEL_ID)

        if news_channel is None:
            logging.error("Getting channel with id '%s' failed" % config.NEWS_CHANNEL_ID)
            return

        for article in articles:
            for e in article:
                await news_channel.send(embed=e)

            logging.info("Sent gmo news article '%s'" % article[0].title)
            
            await self.save_article(article)

            logging.info("Saved article successfully")

    async def save_article(self, article: list[discord.Embed]) -> None:
        version = article[0].description
        link = article[0].url

        saved_article = json.load(open(config.NEWS_DATA_FILE_PATH))["gmo"]

        if link in [d["link"] for d in saved_article]:
            save_json_on_path(
                file=config.NEWS_DATA_FILE_PATH,
                path="gmo/%i/version" % [d["link"] for d in saved_article].index(link),
                value=version
            )
        else:
            save_json_on_path(
                file=config.NEWS_DATA_FILE_PATH,
                path="gmo",
                value={
                    "version": version,
                    "link": link
                }
            )

    async def get_articles(self) -> list[list[discord.Embed]]:
        async with aiohttp.ClientSession() as session:
            async with session.get(config.GMO_NEWS_URL) as r:
                gmo_html = await r.text()

        soup = BeautifulSoup(gmo_html, "html.parser")
        formatted_articles: list[list[discord.Embed]] = []
        
        for article in soup.find_all(class_="newseintrag"):
            if not await self.article_was_sent(repr(article)):
                formatted_articles.append(
                    await self.format_article(repr(article))
                )

        return formatted_articles

    async def article_was_sent(self, article: str) -> bool:
        soup = BeautifulSoup(article, "html.parser")
        ps = soup.find_all("p")
        link = soup.find(class_="titel").find("a", href=True)["href"]  # type: ignore

        jsn = json.load(open(config.NEWS_DATA_FILE_PATH, "r", encoding="utf-8"))["gmo"]

        for element in jsn:
            if element["link"] == link:
                if element["version"] == html_to_dc_md(repr(ps[1])):
                    return True
        return False

    async def format_article(self, html: str) -> list[discord.Embed]:
        soup = BeautifulSoup(html, "html.parser")
        article_div = soup.find("div")

        if article_div is None:
            raise ElementNotFound("div element from gmo article was not found")
        
        embeds: list[discord.Embed] = []
        at_embed: int = 0
        child: Tag
        for i, child in enumerate(article_div.children, start=0):
            if i <= 1 or child.name is None:
                continue
            
            if at_embed == len(embeds):
                embeds.append(discord.Embed(title=config.EMPTY_CHAR))

            if child.name in GMO_News.NO_TEXT_TAG:
                ...
            else:
                fp = html_to_dc_md(repr(child)) 
                if not fp.strip():
                    continue

                elif embeds[at_embed].description == EmptyEmbed:
                    embeds[at_embed].description = fp
                else:
                    embeds[at_embed].add_field(name=config.EMPTY_CHAR, value=fp, inline=False)

        embeds[0].title = article_div.find("p", class_="titel").find("a", text=True).text
        embeds[0].url = article_div.find("p", class_="titel").find("a", href=True)["href"]
        embeds[-1].set_footer(
            text=config.GMO_NEWS_AUTHOR[0],
            icon_url=config.GMO_NEWS_AUTHOR[1],
        )
        embeds[-1].timestamp = datetime.utcnow()
        return embeds


def setup(bot: commands.Bot):
    bot.add_cog(GMO_News(bot))
