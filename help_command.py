import asyncio
import logging
from datetime import datetime
from os import times
from typing import Union

import discord
from discord.errors import DiscordException, HTTPException, NotFound
from discord.ext import commands
from discord.ext.commands.errors import CheckFailure

import config
from functions import *


class HelpCommand(commands.HelpCommand):

    CREATE_TIME = datetime.fromisocalendar(2021, 27, 1)

    def __init__(self):
        commands.HelpCommand.__init__(self)
        self.ctx: commands.Context
        self.description = ""
        self.command: str = ""
        self.channel: discord.abc.Messageable

    async def can_run(self, cmd: commands.Command) -> bool:
        try:
            await cmd.can_run(self.ctx)
        except CheckFailure:
            return False
        else:
            return True

    async def prepare_help_command(self, ctx, command):
        self.ctx = ctx
        self.command = command
        logging.info("Help command called by %s" % ctx.author)

    async def send_bot_help(self, mapping):
        cogs: list[commands.Cog] = await self.get_cogs(mapping)
        pages: list[discord.Embed] = []
        
        for cog in cogs:
            cmds: list[commands.Command] = await self.get_commands_from_cog(cog)

            embed = discord.Embed(
                title="Help on Extension `%s`" % cog.qualified_name,
                color=config.COLOR.HELP
            )
            embed.description = cog.description if cog.description else "_No extension explantion_"
            embed.set_footer(
                text="Tobias",
                icon_url=get_random_pfp(self.ctx.bot)  # type: ignore
            )
            embed.timestamp = HelpCommand.CREATE_TIME
            if cmds:
                for cmd in cmds:
                    if not await self.can_run(cmd):
                        continue
                    embed.add_field(
                        **(await self.get_field_for_cmd(cmd))
                    )
            else:
                embed.description += "\n\n_```No commands```_"
                
            pages.append(embed)
            logging.debug("Added cog %s to help command pages" % cog.qualified_name)

        first_pages = [
            embed_message(
                title="Help",
                description="Use the symbols below the message to navigate between the pages",
                author=("Tobias", get_random_pfp(self.ctx.bot)),  # type: ignore
                timestamp=HelpCommand.CREATE_TIME
            )
        ]

        if (await self.get_field_for_cmd([x for x in mapping[None] if x.name == "help"][0]))["value"]:
            first_pages.append(
                embed_message(
                    title="Help on Extension `None`",
                    description="Here are commands added directly using the bot",
                    author=("Tobias", get_random_pfp(self.ctx.bot)),  # type: ignore
                    timestamp=HelpCommand.CREATE_TIME,
                    fields=(
                        await self.get_field_for_cmd([x for x in mapping[None] if x.name == "help"][0]),
                    )
                )
            )
        
        await self.send_book(first_pages + pages)

    async def get_field_for_cmd(self, cmd: commands.Command) -> dict[str, Union[str, bool]]:
        return  {
            "inline": False,
            "name": cmd.qualified_name + " " + cmd.signature,
            "value": d if (d:=cmd.description) is not None else (h if (h:=cmd.help) is not None else "_No description_")
        }

    async def get_cogs(self, mapping) -> list[commands.Cog]:
        return sorted(
            [cog for cog in mapping.keys() if cog is not None], 
            key=lambda x: x.qualified_name
        )

    async def get_commands_from_cog(self, cog: commands.Cog) -> list[commands.Command]:
        return sorted(
            [cmd for cmd in cog.get_commands() if cmd is not None],
            key=lambda x: x.name
        )

    async def send_book(self, pages) -> None:
        def check_reaction(reaction: discord.Reaction, user: discord.Member):
            if user.id == self.ctx.author.id:  # type: ignore
                if str(reaction.emoji) in config.PAGE_EMOJIS:
                    return True
            return False

        page_index = 0
        pages = color_embeds(pages, color=config.COLOR.HELP)
        msg: discord.Message = await self.get_destination().send(embed=pages[page_index])  # type: ignore
        
        # add page navigator
        for s in config.PAGE_EMOJIS:
            try:
                await msg.add_reaction(s)
            except DiscordException:
                logging.error("Could not add reaction %s to help msg requested by %s" % (s, self.ctx.author))

        opened: bool = True
        while opened:
            try: 
                reaction, user = await self.ctx.bot.wait_for(  # type: ignore
                    "reaction_add", 
                    timeout=60.0, 
                    check=check_reaction
                )
            except asyncio.TimeoutError:
                return
            else:
                if reaction.emoji == config.NEXT_PAGE_EMOJI:
                    page_index = (page_index + 1) % len(pages)
                    await msg.edit(embed=pages[page_index])

                elif reaction.emoji == config.PREV_PAGE_EMOJI:
                    page_index = (page_index - 1) % len(pages)
                    await msg.edit(embed=pages[page_index])

                elif reaction.emoji == config.STOP_SIGN_EMOJI:
                    opened = False
                
                await reaction.remove(user)
        
        # remove page navigator
        for s in reversed(config.PAGE_EMOJIS):
            try:
                await msg.remove_reaction(s, self.ctx.bot.user)  # type: ignore
            except DiscordException:
                logging.info("Emoji %s could not be removed" % s)
        
        try:
            await msg.delete()
        except HTTPException:
            logging.info("Failed to delete help message for %s in channel '%s'" % (self.ctx.author, self.ctx.channel.name))  # type: ignore
        
        try:
            await self.ctx.message.delete()  # type: ignore
        except (HTTPException, NotFound):
            logging.info("Failed to delete help request message for %s in channel '%s'" % (self.ctx.author, self.ctx.channel.name)) # type: ignore

    async def send_cog_help(self, cog: commands.Cog):
        cmds = await self.get_commands_from_cog(cog)
        embed = discord.Embed(
            title="Help on Extension `%s`" % cog.qualified_name,
            description=d if (d:=cog.description) else "_`No description`_",
            color=config.COLOR.HELP            
        )
        for cmd in cmds:
            if not await self.can_run(cmd):
                continue
            embed.add_field(
                **(await self.get_field_for_cmd(cmd))
            )

        if not cmds:
            embed.description += "\n\n_```No commands```_"

        embed.set_footer(
            text="Tobias",
            icon_url=get_random_pfp(self.ctx.bot),  # type: ignore

        )
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command: commands.Command) -> None:
        embed = discord.Embed(
            title="Help on Command `%s`" % command.qualified_name,
            color=config.COLOR.HELP
        )
        embed.description = ""
        cmd_info = await self.get_cmd_info(command)
        embed.description += "**Extension**: " + cmd_info["extension"] + "\n"
        embed.description += "**Aliases**: " + cmd_info["aliases"] + "\n"
        embed.description += "**Arguments**: " + cmd_info["arguments"] + "\n"

        embed.add_field(
            name="Description",
            value=command.description if command.description else "_No description_",
            inline=False
        )
        embed.add_field(
            name="Detailed description",
            value=command.help if command.help else "_No detailed description_",
            inline=False
        )

        await self.get_destination().send(embed=embed)

    async def get_cmd_info(self, cmd: commands.Command) -> dict[str, str]:
        d = {
            "aliases": a if (a:='; '.join(cmd.aliases)) else "_No aliases_",
            "extension": cn if (cn:=getattr(cmd.cog, "qualified_name", None)) is not None else "_No extension_",  # type: ignore
            "arguments": "_None_" if not cmd.signature else cmd.signature
        }
        return d

    async def send_group_help(self, group):
        await self.get_destination().send("%s TODO" % self.ctx.author.id)  # type: ignore ; # TODO make group command help 
    
    async def send_error_message(self, error):
        await self.get_destination().send(embed=embed_message(
            title="HelpCommand Error",
            description=error,
            color=config.COLOR.ERROR,
            timestamp=True,
            author="TobisMa"
        ))


    async def command_not_found(self, cmd_name):
        return "The command '%s' does not exist" % cmd_name
