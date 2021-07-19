from cogs.debug import get_category
import json
import logging
from string import ascii_letters, punctuation
from typing import Union

import config
import discord
from discord.ext import commands
from errors import TeamCreationError
from functions import *


class Teamwork(commands.Cog):

    DESCRIPTION_EMOJI = "📝"

    MAX_GROUPS = 15
    COLOR = config.COLOR.PURPLE
    CATEGORY_ID = 866797990857670707

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

        try:
            await self.check_user_info(config.TEAMWORK_FILE, str(ctx.author.id))
        except TeamCreationError as e:
            if e.code == TeamCreationError.TOO_MANY:
                await ctx.send(embed=embed_message(
                    title="Error",
                    description="You are having already %s teams/groups. You cannot have more than %s" % (Teamwork.MAX_GROUPS, )*2,
                    color=config.COLOR.ERROR
                ))
                return

        embed = discord.Embed(
            title="Your groups/teams",
            description="",
            color=Teamwork.COLOR,
            author=(ctx.author.avatar_url, ctx.author.id)
        )

        if not self.group_data[str(ctx.author.id)]:
            embed.description = "At the moment you are in no groups/teams. Use `-tm create` to get into a group or accept an invite."
        else:
            embed.description = "Below you see your groups and teams:"

        for group in self.group_data[str(ctx.author.id)]:
            embed.add_field(
                name=group["name"],
                value=await self.get_group_summary(group),
                inline=False
            )

        await ctx.send(embed=embed)

    @tm.command(
        name="create",
        aliases=["new", "add"],
        description="Creates a new group/team",
        help="This subcommand of `tm` creates you new team where you are the owner. As first arguments you set the name " \
             "and as second the member you want to have in the group. You need to mention them. If they are not mentioned " \
             "they will be removed without notice"
    )
    async def tm_create(self, ctx, name: str, *who_as_mentions: str):
        if self.has_group(ctx.author.id, name):
            await ctx.send(embed=embed_message(
                title="Team '%s' does already exist" % name,
                description="<@%s> Please try another name or delete/edit the current team '%s'" % (ctx.author.id, name),
                color=config.COLOR.ERROR
            ))
            return

        group_members: list[str] = ["<@!%s>" % ctx.author.id]
        description: str = "_No description_"

        for member in who_as_mentions:
            member = member.strip()
            if member.strip(ascii_letters + punctuation).isdigit():
                group_members.append(member)

        reactions = await ask_by_reaction(
            self.bot,
            ctx.channel,
            [
                Teamwork.DESCRIPTION_EMOJI
            ],
            embed=embed_message(
                title="<@%s> Create group/team `%s`" % (ctx.author.id, name),
                description=f"Please select which parameter you want to specify:"
                        	f"{Teamwork.DESCRIPTION_EMOJI}: Edit description",
                fields=[
                    ("Current member of team", ', '.join(group_members), False),
                    ("Current description", description, False)
                ]
            ),
            user=ctx.author
        )

        if reactions[0] is True:
            reply = await ask_for_message(
                self.bot, ctx.channel,
                embed=embed_message(
                    title="Description of '%s'" % name,
                    description="<@%s> Please send the description of the team/group in this channel in your next message" % ctx.author.id,
                    color=Teamwork.COLOR
                )
            )
            if reply is None:
                await ctx.send(embed=embed_message(
                    title="<@%s> >> Info",
                    description="You did not enter the description of the team '%s' within 120s, so no description will be set. " \
                                "To change the description, use `-tm edit <what>`. `<what>` is in this case _`description`_",
                    color=config.COLOR.INFO
                ))

            elif not reply.content:
                await ctx.send(
                    content="<@%s>" % ctx.author.id, 
                    embed=embed_message(
                        title="Setting description failed",
                        description="Description of team cannot be empty",
                        color=config.COLOR.ERROR
                    )
                )
            else:
                description = reply.content

        guild: discord.Guild = ctx.guild

        role = await guild.create_role(name=(name + str(ctx.author.id)), reason="Command `-tm create ...` was called by %s" % ctx.author.id)

        channel = await guild.create_text_channel(
            name=name,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True),
                guild.get_role(role.id): discord.PermissionOverwrite(
                    view_channel=True,
                    read_message_history=True,
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    add_reactions=True 
                )
            },
            category=get_category(guild.categories, id=Teamwork.CATEGORY_ID),
        )

        for m_id in [int(x.strip(ascii_letters + punctuation)) for x in group_members]:
            m: Optional[discord.Member] = guild.get_member(m_id)
            if m is not None:
                await m.add_roles(role, reason="You were added to the team %s by %s" % (name, ctx.author))

        await self.add_group_in_file(
            name=name,
            members=group_members,
            description=description,
            owner_id=ctx.author.id,
            channel_id=channel.id
        )

        logging.debug("Added team %s" % name)

        await ctx.send(embed=embed_message(
            title="Team '%s'" % name,
            description="<@%s> Your team '%s' was successfully added.\nchannel: <#%s>" % (ctx.author.id, name, channel.id),
            color=Teamwork.COLOR
        ))

    async def cog_before_invoke(self, ctx):
        self.group_data = json.load(open(config.TEAMWORK_FILE, "r"))

        if self.group_data.get(str(ctx.author.id)) is None:
            self.group_data[str(ctx.author.id)] = []

    async def check_user_info(self, file: str, key: str) -> None:
        if self.group_data.get(key) is None:
            self.group_data[key] = []

            with open(file, "w") as f:
                f.write(json.dumps(self.group_data, indent=4, sort_keys=True))
        else:
            jsn = json.load(open(config.TEAMWORK_FILE, "r"))
            if len(jsn[key]) == Teamwork.MAX_GROUPS:
                raise TeamCreationError(TeamCreationError.TOO_MANY)


    async def get_group_summary(self, group: dict[str, Union[str, list, int]]) -> str:
        return "TODO"  # TODO this function

    async def add_group_in_file(self, *, 
        name: str, members: list[str], owner_id: int,  channel_id: int, description: str = "_No description_"
    ) -> None:
        group_json: dict = {
            "name": name,
            "members": members,
            "owner_id": owner_id,
            "description": description,
            "channel_id": channel_id
        }

        self.group_data[str(owner_id)].append(group_json)

        with open(config.TEAMWORK_FILE, "w") as f:
            f.write(json.dumps(self.group_data, indent=4, sort_keys=True))

        logging.debug("Added team %s in json file" % name)

    async def cog_after_invoke(self, ctx):
        self.group_data = json.load(open(config.TEAMWORK_FILE, "r"))

    def has_group(self, id: int, group_name: str) -> bool:
        ts: list[dict] = self.group_data[str(id)]
        for t in ts:
            if t["name"] == group_name:
                return True
        return False


def setup(bot):
    bot.add_cog(Teamwork(bot))
