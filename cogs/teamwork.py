import json
import logging
from re import fullmatch
from string import ascii_letters, ascii_lowercase, digits, punctuation
from typing import Union

from discord.errors import HTTPException

import config
import discord
from discord.ext import commands
from errors import *
from functions import *


class Teamwork(commands.Cog):

    DESCRIPTION_EMOJI = "📝"
    MEMBERS_EMOJI = "👨‍👩‍👧‍👦"
    NAME_EMOJI = "✏️"

    MAX_GROUPS = 15
    COLOR = config.COLOR.PURPLE
    CATEGORY_ID = 866797990857670707

    def __init__(self, bot: commands.Bot) -> None:
        commands.Cog.__init__(self)
        self.bot = bot
        self.group_data: dict[str, list[dict[str, Any]]] = {}

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
        name = self.transform_to_dc_channel_name(name)
        if self.has_group(ctx.author.id, name):
            await ctx.send(embed=embed_message(
                title="Team '%s' does already exist" % name,
                description="<@%i> Please try another name or delete/edit the current team '%s'" % (ctx.author.id, name),
                color=config.COLOR.WARNING
            ))
            return

        if fullmatch(r"<@[0-9]+>", name):
            await ctx.send(embed=embed_message(
                title="No name given",
                description="You need to give a name to your team",
                color=config.COLOR.ERROR
            ))
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
                title="Create group/team `%s`" % name,
                description=f"Please select which parameter you want to specify:"
                        	f"\n{Teamwork.DESCRIPTION_EMOJI}: Edit description"
                            f"\n\nIf no is selected the group will be added using the shown values",
                fields=[
                    ("Current member of team", ', '.join(group_members), False),
                    ("Current description", description, False)
                ],
                color=Teamwork.COLOR,
                author=ctx.author
            ),
            user=ctx.author
        )

        if reactions[0] is True:
            reply = await ask_for_message(
                self.bot, ctx.channel,
                embed=embed_message(
                    title="Description of '%s'" % name,
                    description="<@%i> Please send the description of the team/group in this channel in your next message" % ctx.author.id,
                    color=Teamwork.COLOR
                )
            )
            if reply is None:
                await ctx.send(embed=embed_message(
                    title="<@%i> >> Info",
                    description="You did not enter the description of the team '%s' within 120s, so no description will be set. " \
                                "To change the description, use `-tm edit <what>`. `<what>` is in this case _`description`_",
                    color=config.COLOR.INFO
                ))

            elif not reply.content:
                await ctx.send(
                    content="<@%i>" % ctx.author.id, 
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
                guild.me: discord.PermissionOverwrite(
                    view_channel=True, 
                    send_messages=True,
                    read_messages=True,
                    add_reactions=True
                ),
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
            topic=description
        )

        for m_id in [int(x.strip(ascii_letters + punctuation)) for x in group_members]:
            m: Optional[discord.Member] = await guild.fetch_member(m_id)
            if m is not None:
                await m.add_roles(role, reason="You were added to the team %s by %s" % (name, ctx.author))
            else:
                logging.debug("Member with id %s was not found" % m_id)

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
            description="<@%i> Your team '%s' was successfully added.\nchannel: <#%s>" % (ctx.author.id, name, channel.id),
            color=Teamwork.COLOR
        ))

    @tm.command(
        name="delete",
        aliases=["del", "remove"],
        description="Deletes a team/group"
    )
    async def tm_delete(self, ctx, name: str):
        name = self.transform_to_dc_channel_name(name)
        if not self.has_group(ctx.author.id, name):
            await ctx.send(embed=embed_message(
                title="Team not found",
                description="The team '%s' was not found. Please check that you spelled it correctly." % name,  
                color=config.COLOR.ERROR
            ))
            return
        
        guild: discord.Guild = ctx.guild
        role = await guild.fetch_roles()
        for r in role:
            if r.name == (name + str(ctx.author.id)):
                await r.delete()
                break
        else:
            await ctx.send(embed=embed_message(
                title="Internal error",
                description="Deleting team '%s' failed. Please contact <@%i>" % (name, config.OWNER_IDS[0]),
                color=config.COLOR.ERROR
            ))
            return
        
        channels = await guild.fetch_channels()
        team_json = await self.get_json_from_team(ctx.author.id, name)

        if team_json is None:
            await ctx.send(embed=embed_message(
                title="Internal error",
                description="Deleting team '%s' failed. Please contact <@%i>" % (name, config.OWNER_IDS[0]),
                color=config.COLOR.ERROR
            ))
            return

        for c in channels:
            if c.id == team_json["channel_id"] and isinstance(c, discord.TextChannel):
                await c.delete()

        await self.remove_team_from_json(ctx.author.id, name)

        logging.debug("Deleted team '%s' from json" % name)
        try:
            await ctx.send(embed=embed_message(
                title="Deleted team",
                description="The team '%s' was deleted successfully" % name,
                color=Teamwork.COLOR
            ))
        except HTTPException:
            pass

        logging.debug("Deleted team '%s' successfully" % name)

    @tm.command(
        name="edit",
        aliases=["change"],
        description="Edits the team/group",
        help="This function allows you to change the members, description and name of the team/group"
    )
    async def tm_edit(self, ctx, name: str):
        name = self.transform_to_dc_channel_name(name)
        if not self.has_group(ctx.author.id, name):
            await ctx.send(embed=embed_message(
                title="Team not accessible",
                description="Either you are not the owner of the team/group or it does not exist",
                color=config.COLOR.WARNING
            ))
            return
        
        reactions = await ask_by_reaction(
            self.bot, 
            ctx.channel, 
            reactions=[
                Teamwork.NAME_EMOJI,
                Teamwork.DESCRIPTION_EMOJI,
                Teamwork.MEMBERS_EMOJI
            ],
            embed=embed_message(
                title="Edit team '%s'" % name,
                description=f"React with the emojis to select what you want to change (order does not matter):"
                            f"\n{Teamwork.NAME_EMOJI}: Change the name of the team"
                            f"\n{Teamwork.DESCRIPTION_EMOJI}: Change the description of the team/group"
                            f"\n{Teamwork.MEMBERS_EMOJI}: Change the members of the team/group"
                            f"\n\n{config.CHECK_MARK}: Hit if all was selected",
                color=Teamwork.COLOR
            ),
            user=ctx.author
        )
        if reactions[0]:
            msg = await ask_for_message(self.bot, ctx.channel, 
                embed=embed_message(
                    title="New name for current team '%s'" % name,
                    description="Please type the new name for the team in your next message",
                    color=Teamwork.COLOR
                )
            )
            if msg is None or not msg.content:
                await ctx.send("<@%i>" % ctx.author.id, embed=embed_message(
                    title="TimeoutError",
                    description="The editing of team '%s' was cancelled due to a missing reaction within 120sec or empty text" % name,
                    color=config.COLOR.ERROR
                ))
                return

            try:
                await self.change_name(ctx.author.id, name, self.transform_to_dc_channel_name(msg.content), ctx.guild)
            except TeamEditError:
                await ctx.send(embed=embed_message(
                    title="Editing name of team '%s'" % name,
                    description="The editing of the team '%s' failed because you are already owner of another team with the requested name. " \
                                "Either delete that or type another name" % name, 
                    color=config.COLOR.ERROR,
                ))
            else:
                await ctx.send(embed=embed_message(
                    title="Editing name of team '%s'" % name,
                    description="The name of the team was successfully changed to '%s'" % self.transform_to_dc_channel_name(msg.content),
                    color=Teamwork.COLOR
                ))

                name = self.transform_to_dc_channel_name(msg.content)
        
        if reactions[1]:
            msg = await ask_for_message(self.bot, ctx.channel,
                embed=embed_message(
                    title="New description",
                    description="Please type the new description of the team '%s' in your next message" % name,
                    color=Teamwork.COLOR
                )
            )
            if msg is None or not msg.content:
                await ctx.send("<@%i>" % ctx.author.id, embed=embed_message(
                    title="TimeoutError",
                    description="The editing of team '%s' was cancelled due to a missing reaction within 120sec or empty text" % name,
                    color=config.COLOR.ERROR
                ))
                return

            await self.change_description(ctx.author.id, name, ctx.guild, msg.content)
            await ctx.send(embed=embed_message(
                title="Edtiting description of team '%s'" % name,
                description="The description of team '%s' was successfully changed" % name,
                color=Teamwork.COLOR
            ))

        if reactions[2]:
            team = await self.get_json_from_team(ctx.author.id, name)

            if team is None:
                await ctx.send(embed=embed_message(
                    title="Error",
                    description="Team '%s' was not found or you are not the owner" % name,
                    color=config.COLOR.RED
                ))
                return

            msg = await ask_for_message(self.bot, ctx.channel, embed=embed_message(
                title="Editing team member",
                description="Mention in your next message all member you want to add or remove from the team '%s'" % name,
                fields=[
                    (
                        "How to?", 
                        "Mention members to add them. If you mention members, which are already in the team, you will remove them",
                        False
                    ),
                    (
                        "Current members",
                        '\u0020'.join(team["members"]),
                        False
                    )
                ],
                color=Teamwork.COLOR
            ))
            if msg is None or not msg.content:
                await ctx.send(embed=embed_message(
                    title="TimeoutError",
                    description="The editing of team '%s' was cancelled due to a missing reaction within 120sec or empty text" % name,
                    color=config.COLOR.ERROR
                ))
                return
            
            await ctx.send(embed=embed_message(
                title="Editing team member",
                description="This could take a while, so do not panic if a while does nothing happen",
                color=config.COLOR.INFO
            ))
            
            formatted_member_str = msg.content.replace(" ", "")
            members_to_edit = []
            member_str = ""
            for c in formatted_member_str:
                member_str += c
                if c == ">":
                    if member_str.startswith("<@!"):
                        members_to_edit.append(member_str)
                    
                    member_str = ""
            
            removed = []
            added = []
            guild: discord.Guild = ctx.guild
            role = await get_role(guild, name=team["name"] + str(ctx.author.id))

            if role is None:
                ... # TODO error message
                return 

            for m in members_to_edit:
                # TODO adding and removeing the role
                member = await ctx.guild.fetch_member(m.strip(punctuation))

                if str(ctx.author.id) in m:
                    await ctx.send(embed=embed_message(
                        title="ERROR: You are owner",
                        description="You cannot remove yourself of your team.",
                        color=config.COLOR.ERROR
                    ))
                elif m in team["members"]:
                    removed.append(
                        team["members"].pop(team["members"].index(m))
                    )
                    await remove_member_role(role, member)
                else:
                    team["members"].append(m)
                    added.append(m)
                    await add_member_role(role, member, reason="You were invited to the team '%s'" % name)
            
            with open(config.TEAMWORK_FILE, "w") as f:
                f.write(json.dumps(self.group_data, indent=4, sort_keys=True))

            fields = []
            sadded = ' '.join(added)
            if sadded.strip():
                fields.append(("Added", sadded, False))

            sremoved = ' '.join(removed)
            if sremoved.strip():
                fields.append(("Removed", sremoved, False))

            elif not sadded.strip() and not sremoved.strip():
                fields.append(("No change", "There wer"))
 
            await ctx.send(embed=embed_message(
                title="Editing members of team '%s'" % name,
                description="Here are listed the successfully added and removed members",
                fields=fields,
                color=Teamwork.COLOR
            ))
        
        if not any(reactions):
            await ctx.send(embed=embed_message(
                title="INFO",
                description=f"<@{ctx.author.id}> You used the command to edit the settings of team {name}, but you did not select one. "
                            f"So please try again to select one or more of the options. The program does not notice a selection, "
                            f"before the check mark appears, so, wait until then and then select the options you want to change",
                color=config.COLOR.INFO
            ))

    async def change_description(self, user_id: int, name: str, guild: discord.Guild, new_description: str):
        teams = self.group_data[str(user_id)]
        for team in teams:
            if team["name"] == name:
                team["description"] = new_description
                channels = await guild.fetch_channels()

                for channel in channels:
                    if isinstance(channel, discord.TextChannel):
                        if channel.id == team["channel_id"]:
                            await channel.edit(topic=new_description)
                            break

                break

        with open(config.TEAMWORK_FILE, "w") as f:
            f.write(json.dumps(self.group_data, indent=4, sort_keys=True))

        logging.info("Changed description of team '%s' to \"%s\"" % (name, new_description))
            
    async def change_name(self, user_id: int, old_name: str, new_name: str, guild: discord.Guild):
        teams = self.group_data[str(user_id)]
        for team in teams:
            if team["name"] == new_name:
                raise TeamEditError("Cannot change name of team '%s' to '%s', because name already used in one of your teams" % (old_name, new_name))
        for team in teams:
            if team["name"] == old_name:
                team["name"] = new_name

                channels = await guild.fetch_channels()

                for channel in channels:
                    if isinstance(channel, discord.TextChannel):
                        if channel.id == team["channel_id"]:
                            await channel.edit(
                                name=new_name
                            )
                            break

                roles = await guild.fetch_roles()
                for r in roles:
                    if r.name == (old_name + str(user_id)):
                        await r.edit(
                            name=(new_name + str(user_id))
                        )
                        break

                break
        with open(config.TEAMWORK_FILE, "w") as f:
            f.write(json.dumps(self.group_data, indent=4, sort_keys=True))
        
        logging.info("Changed name from team '%s' to '%s'" % (old_name, new_name))

    async def cog_check(self, ctx) -> bool:
        if ctx.invoked_with == "tm":
            if ctx.guild is None:
                return False
        return True

    async def cog_before_invoke(self, ctx):
        self.group_data = json.load(open(config.TEAMWORK_FILE, "r"))

        if self.group_data.get(str(ctx.author.id)) is None:
            self.group_data[str(ctx.author.id)] = []

        with open(config.TEAMWORK_FILE, "w", encoding="utf-8") as f:
            f.write(json.dumps(self.group_data, indent=4, sort_keys=True))

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

    def has_group(self, user_id: int, group_name: str) -> bool:
        ts: list[dict] = self.group_data[str(user_id)]
        for t in ts:
            if t["name"] == group_name:
                return True
        return False

    def transform_to_dc_channel_name(self, name: str) -> str:
        nname = ""
        name = name.lower()
        for sym in name:
            if sym in ascii_lowercase + digits + config.ALLOWED_SYMBOLS_IN_CHANNEL_NAME:
                nname += sym

        return nname.strip(punctuation)

    async def get_json_from_team(self, user_id: int, name: str) -> Optional[dict[str, Any]]:
        teams = self.group_data[str(user_id)]
        for tj in teams:
            if tj["name"] == name:
                return tj
        return None

    async def remove_team_from_json(self, user_id: int, name: str) -> None:
        user_teams = self.group_data[str(user_id)]
        new_user_teams = []
        for team in user_teams:
            if team["name"] != name:
                new_user_teams.append(team)
        
        self.group_data[str(user_id)] = new_user_teams

        with open(config.TEAMWORK_FILE, "w") as f:
            f.write(json.dumps(self.group_data, indent=4, sort_keys=True))

def setup(bot):
    bot.add_cog(Teamwork(bot))
