import asyncio
import logging
from datetime import datetime

import aiohttp
import config
import discord
from bs4 import BeautifulSoup
from bs4 import Tag as HTMLTag
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

        logging.info("Checking gmo news...")
        articles = await self.get_articles()
        logging.info("Checked gmo news")

        news_channel = self.bot.get_channel(config.NEWS_CHANNEL_ID)

        if news_channel is None:
            logging.error("Getting channel with id '%s' failed" % config.NEWS_CHANNEL_ID)
            return

        for article in articles:
            try:
                for e in article:
                    if isinstance(e, discord.Embed):
                        await news_channel.send(embed=e)
                    else:
                        await news_channel.send(embed=e[0], file=e[1])
            except Exception as e:
                await report_error(self.bot, e, logging.ERROR)
                await news_channel.send(article[0].url)

            logging.info("Sent gmo news article '%s'" % article[0].title)
            
            await self.save_article(article)

            logging.info("Saved article successfully")

    @gmo_news_loop.before_loop
    async def before_gmo_news_loop(self):
        await self.bot.wait_until_ready()
        logging.info("Started gmo_news_loop")

    @gmo_news_loop.after_loop
    async def after_gmo_news_loop(self):
        logging.info("Finished gmo_news_loop")

    @gmo_news_loop.error
    async def gmo_news_loop_error(self, error: BaseException):
        await report_error(self.bot, error, logging.ERROR)

        while not self.gmo_news_loop.is_running():
            logging.info("Trying to restart the loop")
            try:
                self.gmo_news_loop.restart()
            except Exception as error:
                await report_error(self.bot, error, logging.ERROR)
            
            await asyncio.sleep(10)

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

    async def get_articles(self) -> list:
        async with aiohttp.ClientSession() as session:
            async with session.get(config.GMO_NEWS_URL) as r:
                gmo_html = await r.text()

        soup = BeautifulSoup(gmo_html, "html.parser")
        formatted_articles: list = []
        
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

    async def format_article(self, html: str) -> list:
        soup = BeautifulSoup(html, "html.parser")
        article_div = soup.find("div")

        if article_div is None:
            raise ElementNotFound("div element from gmo article was not found")
        
        embeds: list = []
        at_embed: int = 0
        child: HTMLTag
        for i, child in enumerate(article_div.children, start=0):
            if i <= 1 or child.name is None:
                continue
            
            if at_embed == len(embeds):
                embeds.append(discord.Embed(title=config.EMPTY_CHAR))
            
            in_child = [x for x in child.children if x.name]
            
            inner_child = ""  # type: ignore
            if len(in_child) == 1:
                inner_child: HTMLTag = in_child[0]

            if getattr(inner_child, "name", "") in GMO_News.NO_TEXT_TAG:
                if inner_child.name == "img":
                    embeds.append(discord.Embed(
                        title=v if (v := inner_child.attrs.get("alt")) else inner_child.attrs["src"],
                    ).set_image(url=inner_child.attrs["src"]))
                elif inner_child.name == "video":
                    embeds[-1].add_field(
                        name=config.EMPTY_CHAR,
                        value="[Video](%s)" % inner_child.attrs["src"],
                        inline=False
                    )

            else:
                fp = html_to_dc_md(repr(child)) 
                if not fp.strip():
                    continue

                elif embeds[at_embed].description == EmptyEmbed:
                    embeds[at_embed].description = skip(fp, 2000)
                else:
                    embeds[at_embed].add_field(name=config.EMPTY_CHAR, value=skip(fp, 1024), inline=False)
        try:
            embeds[0].title = article_div.find("p", class_="titel").find("a", text=True).text
        except Exception as e:
            embeds[0].title = "Error: " + str(e)

        embeds[0].url = article_div.find("p", class_="titel").find("a", href=True)["href"]
        if isinstance(embeds[-1], list):
            embeds[-1][0].set_footer(
                text=config.GMO_NEWS_AUTHOR[0],
                icon_url=config.GMO_NEWS_AUTHOR[1],
            )
            embeds[-1][0].timestamp = datetime.utcnow()
        else:            
            embeds[-1].set_footer(
                text=config.GMO_NEWS_AUTHOR[0],
                icon_url=config.GMO_NEWS_AUTHOR[1],
            )
            embeds[-1].timestamp = datetime.utcnow()

        # add color
        for e in embeds:
            if isinstance(e, list):
                e[0].color = config.COLOR.GREEN
            else:
                e.color = config.COLOR.GREEN
            
        return embeds


def setup(bot: commands.Bot):
    bot.add_cog(GMO_News(bot))
