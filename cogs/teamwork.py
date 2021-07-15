import json
import discord
from discord.ext import commands

import config


class Teamwork(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        commands.Cog.__init__(self)
        self.bot = bot
        self.group_data = {}

    @commands.group(
        name="tm",
        aliases=["team", "teamwork", "tw", "group"],
        description="Command for managing own groups for teamwork",
        help="This command is used to loook at your groups/teams. It also has subcommands for deleting, creating and editing " \
             "groups you belong too.\n*NOTE*: Editing is restricted to owner of the group/team. " \
             "Also notcie that you can *not* have more than 15 group/teams at the same time"
    )
    async def tm(self, ctx):
        if ctx.subcommand_passed is not None:
            return

        await ctx.send("1")

    @tm.command(
        name="create",
        aliases=["new", "add"],
        description="Creates a new group/team",
        help="This subcommand of `tm` creates you new team where you are the owner"
    )
    async def tm_create(self, ctx):
        await ctx.send("2")

    async def cog_before_invoke(self, ctx):
        self.group_data = json.load(open(config.TEAMWORK_FILE, "r"))



def setup(bot):
    bot.add_cog(Teamwork(bot))