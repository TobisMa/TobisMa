import logging
from typing import Optional
from discord.ext import commands
from functions import *
import config


class Debug(commands.Cog):
    def __init__(self, bot):
        commands.Cog.__init__(self)
        self.bot: commands.Bot = bot

    def cog_check(self, ctx) -> bool:
        r = True
        logging.debug("Checking debug access")
        r = has_role(ctx.author, config.ROLES["developer"]["id"])
        logging.debug("debug access result: %s" % r)
        return r
        
    @commands.command(
        name="delete",
        aliases=["del"],
        description="Deletes [amount=**\u221E**] messages"
    )
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def delete(self, ctx, amount: Optional[int] = None) -> None:
        logging.debug("Executing command 'delete' from '%s' in '%s'" % (ctx.author, ctx.channel))
        if amount is None:
            await ctx.channel.purge(limit=None)
        else:
            await ctx.channel.purge(limit=amount + 1)

def setup(bot):
    bot.add_cog(Debug(bot))
