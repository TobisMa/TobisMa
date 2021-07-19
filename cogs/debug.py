import ast
import logging
from typing import Optional

import config
from classes import *
from dc_function_simulation import *
from discord.errors import *
from discord.ext import commands
from discord.ext.commands.errors import *
from functions import *


class Debug(commands.Cog):
    def __init__(self, bot):
        commands.Cog.__init__(self)
        self.bot: commands.Bot = bot

    async def cog_check(self, ctx) -> bool:
        log = (ctx.invoked_with != "help")
        r = True
        if log:
            logging.debug("Checking debug access from %s" % ctx.author)
        r = has_role(ctx.author, config.ROLES["developer"]["id"])
        if log:
            logging.debug("debug access result: %s" % r)

        if r and log:
            logging.info("debug command '%s' executed by %s" % (ctx.invoked_with, ctx.author))

        return r
        
    @commands.command(
        name="delete",
        aliases=["del"],
        description="Deletes [amount=**\u221E**] messages"
    )
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def delete(self, ctx, amount: Optional[int]) -> None:
        if amount is None:
            await ctx.channel.purge(limit=None)
        else:
            await ctx.channel.purge(limit=amount + 1)

    @commands.command(
        name="reload_extension",
        aliases=["rext"],
        description="Reloads the given extension(s)"
    )
    async def reload_extension(self, ctx, *ext_names):
        successfully = []

        for name in ext_names:
            try:
                self.bot.reload_extension("cogs.%s" % name)
            except (ExtensionError, ModuleNotFoundError) as e:
                await ctx.send(embed=embed_error(
                    error=e,
                    bot=self.bot.user,
                ))
            else:
                successfully.append(name)
                logging.log(25, "Reloaded extension %s" % name)

        if successfully:
            await ctx.send(
                embed=create_console_message(">> Extension(s) %s was successfully reloaded" % ', '.join(successfully))
            )

    @commands.command(
        name="unload_extension",
        aliases=["uext"],
        description="Unloads the given extension(s)"
    )
    async def unload_extension(self, ctx, *ext_names):
        successfully = []
        for name in ext_names:
            try:
                self.bot.unload_extension("cogs.%s" % name)
            except (ExtensionError, ModuleNotFoundError) as e:
                await ctx.send(embed=embed_error(
                    error=e,
                    bot=self.bot.user
                ))
            else:
                successfully.append(name)
                logging.log(25, "Unloaded extension %s" % name)

        if successfully:
            await ctx.send(
                embed=create_console_message(">> Extension(s) %s was successfully unloaded" % ', '.join(successfully))
            )
    
    @commands.command(
        name="load_extension",
        aliases=["lext"],
        description="Loads the given extension(s)"
    )
    async def load_extension(self, ctx, *ext_names):
        successfully = []
        for name in ext_names:
            try:
                self.bot.load_extension("cogs.%s" % name)
            except (ExtensionError, ModuleNotFoundError) as e:
                await ctx.send(embed=embed_error(
                    error=e,
                    bot=self.bot.user
                ))
            else:
                successfully.append(name)
                logging.log(25, "Laded extension %s" % name)

        if successfully:
            await ctx.send(
                embed=create_console_message(">> Extension(s) %s was successfully loaded" % ', '.join(successfully))
            )


    @commands.command(
        name="debug",
        aliases=["d", "e", "cmd", "run"],
        description="Runs a in discord written program",
        help="A in discord written python program will be executed within the bot. Access to global variables are allowed " \
            "except the bot TOKEN. This is restricted to the bot owner(s). Possible functions to debug the command are \n" \
            "config.reload to reaload the config once\n" \
            "To see more variables look at the project on https://github.com/TobisMa/discordbot"
    )
    async def execute(self, ctx, prgm: str) -> Any:
        """Executes the program"""
        prgm = parse_prgm(prgm)
        prgm = CodeString(prgm)

        # prevents using the TOKEN in your code if you are not owner
        # importing the token with `import config.TOKEN` and `from config import TOKEN` are restricted as well
        if (prgm.contains("import builtins", in_string=False) or prgm.contains("from builtins", in_string=False)
            and ctx.author.id not in config.OWNER_IDS
            ):
            await ctx.send(embed=embed_message(
                title="Warning",
                description="Due to saftey from the bot token which is restricted to bot owner there are functions restricted.\n" \
                            "That's why you don't need to import the builtins module. You are sooooooo ein Idiot <@%s>\n" % ctx.author.id,
                color=config.COLOR.WARNING,
                author=self.bot.user
            ))
            return

        # all imports which can result in problems for token safety
        if ((prgm.contains("config.TOKEN", in_string=False) 
                or prgm.contains(config.file_path, in_string=True)
                or prgm.contains("from config", in_string=False)
                or prgm.contains("config.config_file_path")
                or prgm.contains("import config")
                or prgm.contains("token", lower=True, in_string=True)
                or prgm.contains("import os", in_string=False)
                or prgm.contains("os import")
            )
            and ctx.author.id not in config.OWNER_IDS
            ):
            await ctx.send(embed=embed_message(
                title="Warning",
                description="Due to saftey from the bot token which is restricted to bot owner there are functions restricted.\n" \
                            "Please don't import the json library, config vars or call the open functions",
                color=config.COLOR.WARNING,
                author=self.bot.user
            ))
            return

        fn_name = "_user_expr"
        prgm = prgm.strip("` ")

        # removes discord syntax highlighting if it exists
        if prgm.split("\n")[0] == "py" or prgm.split("\n")[0] == "python":
            prgm = "\n".join(prgm.split("\n")[1:])

        # add a layer of indentation
        prgm = "\n".join(f"    {i}" for i in prgm.splitlines())

        # wrap in async def body
        body = f"async def {fn_name}():\n{prgm}"

        try:
            parsed = ast.parse(body, mode="exec")
        except Exception as e:
            await ctx.send(embed=embed_error(error=e))
            return
      
        body = parsed.body[0].body  # type: ignore

        insert_ast_returns(body)

        class ModuleRepresenter:

            """Class used to represent a module with missing or more attributes for saftey"""

            def __init__(self, name, repr):
                self.name: str = name
                self.__repr = repr

            def __repr__(self) -> str:
                return self.__repr

        if ctx.author.id not in config.OWNER_IDS:
            # overwrite modules
            config_ = ModuleRepresenter("config", repr(config))

            # remove values
            for key in dir(config):
                if key not in ("TOKEN", "OWNER_IDS"):
                    setattr(config_, key, getattr(config, key))
    
        # defining globals
        vars = dict(globals().copy(), **locals().copy())
        vars["bot"] = self.bot
        vars["ctx"] = ctx
        vars["debug"] = self
        vars["cogs"] = self.bot.cogs

        # add global variables named with extension name in lowercase for easier debugging use
        for cog_name in list(self.bot.cogs):
            vars[cog_name.lower()] = self.bot.cogs[cog_name]
        
        if ctx.author.id not in config.OWNER_IDS:
            # overwrite problematic built-in functions
            #vars["eval"] = not_allowed("eval(...) cannot be used in discord")
            #vars["exec"] = not_allowed("exec(...) cannot be used in discord")
            #vars["quit"] = not_allowed("You are not allowed to stop the bot")
            #vars["exit"] = not_allowed("You are not allowed to stop the bot")
            vars["open"] = dc_open
        
            for var in config.RESTRICTED_DEBUG_VARS:
                vars.pop(var)

            vars["config"] = config_   # type: ignore for pylance
        
        vars["help"] = not_allowed("you do not need to use help(...). You are an developer. you are such a ばか <@%s>" % ctx.author.id)
        vars["print"] = not_allowed("Use `await ctx.send('Your message')` instead of `print(...)`")
        
        exec(compile(parsed, filename="<ast>", mode="exec"), vars)

        # run the functiion defined with exec
        try:
            result = await eval(f"{fn_name}()", vars)
        except AccessError as e:
            await ctx.send(embed=embed_message(
                title="Warning",
                description=str(e) + "\n" + e.cause,
                color=config.COLOR.WARNING,
                author=ctx.bot.user,
                timestamp=True
            ))
            return

        except Exception as e:
            # send error if occurred
            await ctx.send(embed=embed_error(error=e))
            return
        finally:
            for f in config.FILE_FP:
                if callable(f.close):
                    f.close()

        # if result is discord message item; it doesn't send it beacaus probably a message was send pr
        if isinstance(result, (discord.Message, discord.abc.Messageable)):
            return 

        elif isinstance(result, ModuleRepresenter) and ctx.author.id not in config.OWNER_IDS:
            if result.name == "config":
                result = config
        
        answer = pyformat(result)[:1991]
        try:
            # send result in embed in an code block with python highlighting
            await ctx.send(embed=embed_message(
                title="Console output",
                description="```py\n" + answer + "```",
                color="teal",
                author=self.bot.user
            ))
        except HTTPException as e:
            traceback.print_exception(type(e), e, e.__traceback__)


def get_category(categories: list[discord.CategoryChannel], *, id=None, name=None) -> Optional[discord.CategoryChannel]:
    for category in categories:
        if category.name == name or name is None:
            if category.id == id or id is None:
                return category

    return None

def setup(bot):
    bot.add_cog(Debug(bot))
