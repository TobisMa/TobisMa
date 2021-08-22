import ast
import asyncio
from re import fullmatch
from errors import NoFilterSetError
import json
import logging
import random
import traceback
from datetime import  datetime, timedelta
from types import MappingProxyType
from typing import Any, Iterable, Literal, Mapping, Optional, Union

import discord
from discord.embeds import _EmptyEmbed, EmptyEmbed
from discord.ext import commands

import config

LINK_DESTROYER = list(" \n\\<>'\"")

async def report_error(bot: commands.Bot, e: BaseException, 
    log_level=logging.WARN, console: bool=True, channel_id: int = config.LOG_CHANNEL_ID,
    **extra
) -> None:
    if console:
        logging.log(log_level, "Report error '%s' with value '%s'" % (type(e), str(e)), extra={"in_console": console})
        traceback.print_exception(
            etype=type(e),
            value=e,
            tb=e.__traceback__
        )
    
    channel = bot.get_channel(channel_id)
    if channel is None:
        logging.error("Failed to get channel with id %s" % channel_id)
        return
    await channel.send(embed=embed_error(e, bot=bot), **extra)
    

def embed_message(*,
    title: Union[str, _EmptyEmbed] = EmptyEmbed,
    description: Union[str, _EmptyEmbed] = EmptyEmbed,
    color: Optional[Union[discord.Color, str]] = None,
    author: Optional[Union[discord.User, discord.Member, str, tuple[str, str], list[str], discord.ClientUser]] = None,
    timestamp: Union[datetime, bool] = True,
    image: Optional[str] = None,
    thumbnail: Optional[str] = None,
    url: Optional[str] = None,
#    video: Optional[dict[str, Union[str, int]]] = None,
    fields: Iterable[Union[tuple[str, str], tuple[str, str, bool], list[Union[str, bool]], dict[str, Union[str, bool]]]] = ()
) -> discord.Embed:
    embed = discord.Embed()

    embed.title = str(title)
    embed.description = description
    
    # color
    if color:
        if isinstance(color, str):
            try:
                color = getattr(config.COLOR, color.upper())
            except AttributeError:
                raise ValueError("color key must be a color name string or a discord.Color")
        elif not isinstance(color, discord.Color):
            raise ValueError("color keyword needs to be a color name string or a discord.Color")
        
        embed.color = color

    # author
    if author:
        if isinstance(author, str):
            embed.set_footer(text=author)
        elif isinstance(author, (tuple, list)):
            if len(author) == 2:
                embed.set_footer(
                    text=author[0],
                    icon_url=author[1]
                )
            else:
                raise ValueError("Author list or tuple must be have the author name first and icon url as second item")
        
        elif isinstance(author, discord.User):
            embed.set_footer(
                text=author.name,
                icon_url=author.avatar_url
            )

    # timestamp
    if timestamp:
        if timestamp is True:
            timestamp = datetime.utcnow()
        
        if isinstance(timestamp, datetime):
            embed.timestamp = timestamp

    # image
    if image:
        embed.set_image(url=str(image))
    
    # thumbnail
    if thumbnail is not None:
        embed.set_thumbnail(url=thumbnail)

    # link in title
    if url:
        embed.url = str(url)

    # fields adding
    for f in fields:
        if isinstance(f, dict):
            embed.add_field(
                **f
            )
        elif len(f) == 2:
            embed.add_field(
                name=f[0],
                value=f[1],
                inline=False
            )

        elif len(f) == 3:
            embed.add_field(
                name=f[0],
                value=f[1],
                inline=f[2]
            )

        else:
            logging.warning("Field property '%s' was not added because of wrong structure" % f)

    return embed


def embed_command_error_msg(title: str, description: str, author: Optional[Union[discord.User]]=None, code=None, fields=[]) -> discord.Embed:
    return embed_message(
        title=title + " #%i" % code if code else title,
        description=description,
        timestamp=datetime.utcnow(),
        color=config.COLOR.ERROR,
        author=author,
        fields=fields
    )


def secure_link(link: str) -> str:
    """Converts special symbols in hexa code

    Args:
        link (str): the link

    Returns:
        str: the converted link
    """
    return "".join(
        "%" + hex(ord(l))[2:] if l in LINK_DESTROYER else l
        for l in link
    )


def html_to_dc_md(text: str) -> str:  # sourcery no-metrics
    """
    Removes html from an html tree code and parse it to an discord message format
    @param text: the html code
    @returns: the parsed html to an discord message format
    @rtype: str
    """
    text = escape_dc_chars(text)
    quoted = False
    tag_pos = []
    tag = False
    tag_name_active = False
    tag_name = ""
    last_sym = ""
    closing = False
    a_link_now = False
    a_tag = False
    a_link = ""
    a_link_text = ""
    li_count = 0
    out = ""

    for i, letter in enumerate(text, start=0):
        if a_tag:
            if letter == "<":
                tag = True
                a_tag = False
                tag_name_active = True

            elif text[i-4:i] == "href" and tag:
                a_link_now = True

            elif a_link_now:
                if letter == "\"" and a_link and last_sym != "\\":
                    a_link_now = False
                if letter != "\"" or last_sym == "\\":
                    a_link += letter

            elif letter == ">":
                tag = False

            elif not tag:
                a_link_text += letter

        elif letter == "\"" and last_sym != "\\":
            quoted = bool((int(quoted) + 1) & 1)  # toggler between True and False

        elif tag_name_active:
            if letter in (" ", ">", "/") and last_sym not in ("<", "/"):
                tag_name_active = False

                if tag_pos and tag_name == tag_pos[-1] and closing:
                    tag_pos.pop(-1)

                    # tag_name is the same as in the else
                    if tag_name in {"b", "strong"}:
                        out += "**"
                    elif tag_name in {"em", "i"}:
                        out += "*"

                    elif tag_name == "a":
                        if not a_link_text:
                            a_link_text = a_link
                        out += "[{}]({})".format(a_link_text, secure_link(a_link))

                else:
                    tag_pos.append(tag_name)

                    if tag_name in {"b", "strong"}:
                        out += "**"
                    elif tag_name in {"em", "i"}:
                        out += "*"
                    elif tag_name == "a":
                        a_tag = True

                    elif tag_name == "li":
                        if tag_pos[-2] == "ol":
                            li_count += 1
                            out += "\n %s. " % li_count
                        else:
                            out += "\n - "

                tag_name = ""
                closing = False
            elif letter == "/":
                closing = True
            else:
                tag_name += letter

        elif letter == "<" and not quoted:
            tag = True
            tag_name_active = True

        elif not tag:
            out += letter

        if tag and letter == ">" and not quoted:
            if last_sym == "/":
                poped = tag_pos.pop(-1)
                if poped == "br":
                    out += "\n"
                elif poped == "hr":
                    out += "-----------------------"
            tag = False

        last_sym = letter

    return out


def has_role(member: discord.Member, role: Union[str, int]) -> bool:
    if isinstance(role, str):
        return role in [role.name for role in member.roles]
    else:
        return role in [role.id for role in member.roles]


def has_any_role(member: discord.Member, roles: Iterable[Union[str, int]]) -> bool:
    return any(has_role(member, r) for r in roles)


def has_all_roles(member: discord.Member, roles: Iterable[Union[str, int]]) -> bool:
    return all(has_role(member, r) for r in roles)


def save_json_on_path(*, file: str, path: str, value: Any) -> None:
    jsn = json.load(open(file, "r", encoding='utf-8'))

    tree_part = jsn

    if path.startswith("/"):
        path = path[1:]
    if path.endswith("/"):
        path = path[:-1]

    for f in path.split("/")[:-1]:
        if isinstance(tree_part, list) and f.isdecimal():
            tree_part = tree_part[int(f)]
        elif isinstance(tree_part, dict):
            tree_part = tree_part[f]
        else:
            raise ValueError("Key '%s' can't be used because of wrong data type or it does not exist" % f)

    if isinstance(tree_part, list) and path.split("/")[-1].isdecimal():
        tree_part[int(path.split("/")[-1])] = value
    elif isinstance(tree_part, dict):
        if isinstance(tree_part[path.split("/")[-1]], list):
            tree_part[path.split("/")[-1]].append(value)
        else:
            tree_part[path.split("/")[-1]] = value
    else:
        raise ValueError("Key '%s' can't be used because of wrong data type or it does not exist" % path.split("/"))

    with open(file, "w", encoding='utf-8') as f:
        f.write(json.dumps(jsn, indent=4, sort_keys=True))


def escape_dc_chars(text: str) -> str:
    """Puts `\\` before symbols `*` and `_`

    Args:
        text (str): the text which is to escape

    Returns:
        str: the escaped text
    """
    return text.replace("\\", "\\\\").replace("*", "\\").replace("_", "\\")


def skip(text: str, length: int = 2000) -> str:
    if len(text) >= 3 and len(text) >= length - 3:
        return text[:-length + 3] + "..."
    return text


def embed_error(error: BaseException, *, color: discord.Color = config.COLOR.RED, bot=None, **extra) -> discord.Embed:
    return embed_message(
        title="An '%s'-exception occured" % type(error),
        description=("```py\n" + ''.join(
            traceback.format_exception(
                etype=type(error),
                value=error,
                tb=error.__traceback__
            )
        ) + "\n\n" + pythonize_json(json.dumps(extra, indent=2)) + "```")[-2000:],
        color=color,
        author=getattr(bot, "user", "TobisMa"),
    )


def pyformat(pyt, type = str) -> str:
    ret = None
    if isinstance(pyt, str) and isinstance(type, str):
        ret = pyt

    elif isinstance(pyt, list) or isinstance(type, list):
        pyt = str(repr(pyt))[1:-1].split(", ")
        pyt = ',\n  '.join(pyt)

        ret = "[\n  " + pyt + "\n]"

    elif isinstance(pyt, dict) or isinstance(type, dict) or isinstance(pyt, Mapping):
        ret = json.dumps(make_json_serializable(pyt, func=lambda x: str(repr(x))), indent=2)
        ret = convert_json_kwds_to_py_kywd(ret)

    elif isinstance(pyt, MappingProxyType):
        ret = json.dumps(make_json_serializable(dict(pyt), func=lambda x: str(repr(x))), indent=2)
        ret = convert_json_kwds_to_py_kywd(ret)

    else:
        ret = repr(pyt)
    
    return ret


def make_json_serializable(d, func = lambda x: str(repr(x))) -> dict[str, Any]:
    """
    Takes in a dict and converts all values which are not defined in json in strings using func(value). If this raises an exception it will try
    not catch the error. Keys are converted like values in strings if they are not already strings
    @param d: any dict
    @param func: the functions used to convert not serializable_objects. Needs to return something
    @return: the json serializable dict
    @rtype: dict
    """
    def convert_value_of_list(v: Any) -> Union[float, int, str, bool, list, dict, None]:
        if not isinstance(v, (float, int, str, bool, list, dict, type(None))):
            v = func(v)

        elif isinstance(v, dict):
            return make_json_serializable(v, func=func)

        elif isinstance(v, list):
            return [convert_value_of_list(sub_v) for sub_v in v]

        return v

    for key, value in d.items():
        if not isinstance(key, str):
            func(key)

        if isinstance(value, dict):
            d[key] = make_json_serializable(value, func=func)

        elif isinstance(value, list):
            d[key] = [convert_value_of_list(v) for v in value]

        elif not isinstance(value, (float, int, str, bool, list, dict, type(None))):
            d[key] = func(value)
    
    return d


def convert_json_kwds_to_py_kywd(json_str: str) -> str:
    """
    Converts the json keywords in the string to python keywords. This function always assumes your input is a valid json string
    @param json_str: the string which is assumed it has a valid json format
    @return: the json string but using python keywords insetad of json keywords
    @rtype: str
    """
    for json_kw, py_kw in config.JSON_AND_PY_KWDS:
        json_str = json_str.replace(json_kw, py_kw)

    return json_str


def create_console_message(msg: str) -> discord.Embed:
    return embed_message(
        title="Console Output",
        description="```" + msg.replace("```", "­`­`­`") + "```",  # second argument of replace has empty chars between them
        color=config.COLOR.INFO
    )


def functions_reload() -> Literal['Reloaded functions successfully']:
    import importlib
    importlib.reload(__import__(__name__))

    return "Reloaded functions successfully"


def parse_prgm(pycode: str) -> str:
    """
    Formats str with `"` in python code to `'`
    @param pycode: the valid syntax python code as str
    @return: the formatted pycode
    @rtype: str
    """
    quoted = False
    fpycode = ""
    last_sym = ""

    for letter in pycode:
        if letter == "\"":
            if not quoted and last_sym == "\\":
                fpycode += "\\"  # `'` will be added in the end of the if block
            else:
                letter += ""
                quoted = bool(int(quoted) + 1 % 2)

            fpycode += "\'"

        else:
            fpycode += letter

    return fpycode


def insert_ast_returns(body) -> None:
    # insert return stmt if the last expression is a expression statement
    if isinstance(body[-1], ast.Expr):
        body[-1] = ast.Return(body[-1].value)
        ast.fix_missing_locations(body[-1])

    # for if statements, we insert returns into the body and the orelse
    if isinstance(body[-1], ast.If):
        insert_ast_returns(body[-1].body)
        insert_ast_returns(body[-1].orelse)

    # for with blocks, again we insert returns into the body
    if isinstance(body[-1], ast.With):
        insert_ast_returns(body[-1].body)


def get_random_pfp(bot: commands.Bot) -> Union[str, None]:
    u: Optional[discord.User] = bot.get_user(random.choice(config.OWNER_IDS))
    if u is None:
        return "https://discord.com/assets/847541504914fd33810e70a0ea73177e.ico"
    return u.avatar_url._url


def color_embeds(embeds: Union[list[discord.Embed], tuple[discord.Embed]], *, color):
    for e in embeds:
        e.color = color
    return embeds


async def ask_by_reaction(bot: commands.Bot, channel: discord.abc.Messageable, reactions: list[Union[discord.Emoji, str]],
    *, 
    embed: discord.Embed = None, 
    content: str = None, 
    user: Optional[discord.User] = None
) -> list[bool]:
    def check_reaction(reaction: discord.Reaction, _user: discord.User) -> bool:
        if reaction.message.id != msg.id: return False
        if reaction.emoji in reactions or reaction.emoji == config.CHECK_MARK:
            if user is None:
                return True
            if user.id == _user.id:
                return True
        return False
    msg: discord.Message = await channel.send(
        content=content,
        embed=embed
    )

    for emoji in reactions:
        await msg.add_reaction(emoji)
    await msg.add_reaction(config.CHECK_MARK)
    
    pressed: list[bool] = [False] * len(reactions)
    confirmed = False
    reaction_adds: list[tuple[discord.Reaction, discord.User]] = []

    reaction: discord.Reaction
    intern_user: discord.User

    while not confirmed:
        try:
            reaction, intern_user = await bot.wait_for("reaction_add", timeout=60, check=check_reaction)
            reaction_adds.append((reaction, intern_user))
        except asyncio.TimeoutError:
            # TODO info message
            return pressed
        else:
            if reaction.emoji == config.CHECK_MARK:
                confirmed = True
            else:
                for i, emoji in enumerate(reactions, start=0):
                    if emoji == reaction.emoji:
                        pressed[i] = True

    for r in reversed(reaction_adds):
        await r[0].remove(r[1])

    return pressed


def pythonize_json(jsn: str) -> str:
    return jsn.replace(": true,", ": True,").replace(": false,", ": False,").replace(": null,", ": None,")


async def ask_for_message(bot: commands.Bot, channel: discord.abc.Messageable,
    *,
    embed: discord.Embed = None,
    content: str = None,
    user: Optional[Union[discord.User, discord.Member]] = None
) -> Optional[discord.Message]:
    def check_message(msg: discord.Message) -> bool:
        if msg.author.id == bot.user.id: return False  # type:ignore
        
        if msg.channel == channel \
        and (
            user is None 
            or user == msg.author
        ): 
            return True
        return False

    await channel.send(
        content=content,
        embed=embed
    )
    try:
        msg = await bot.wait_for("message", timeout=120)
    except asyncio.TimeoutError:
        ... # TODO info message
        return None
    else:
        return msg


def get_category(categories: Iterable[discord.CategoryChannel], *, name=None, id=None) -> Optional[discord.CategoryChannel]:
    if name is None and id is None:
        raise NoFilterSetError("You need to set at least one filter (id or name)")

    for category in categories:
        if (category.name == name or name is None) and (
            category.id == id or id is None
        ):
            return category
    return None


async def remove_member_role(role: discord.Role, member: discord.Member) -> None:
    new_roles = [r for r in member.roles if r.id != role.id]
    await member.edit(
        roles=new_roles
    )


async def add_member_role(role: discord.Role, member: discord.Member, reason: str=None) -> None:
    await member.add_roles(role, reason=reason)


async def get_role(guild: discord.Guild, *, id=None, name=None) -> Optional[discord.Role]:
    if id is None and name is None:
        return None
    for r in await guild.fetch_roles():
        if r.id == id or r.name == name:
            return r
    return None


def get_timedelta(timedelta_str: str) -> timedelta:
    if fullmatch(r"[\.a-zA-Z]+\(((days|seconds|microseconds)=[0-9]+(, )?)+\)", timedelta_str):
        time_specifics = timedelta_str.split("(")[1]
        time_specifics = time_specifics.replace("=", "': ")
        dict_str = "{'" + time_specifics[:-1] + "}"
        dict_str = dict_str.replace(", ", ", '")
        return timedelta(**eval(dict_str))

    raise ValueError("Invalid timedelta str")

def convert_to_human_time(time: datetime) -> str:
    return "on {.day}.{.month}.{.year} at {.hour}:{.minute}:~30".format(time)


def convert_to_human_timedelta(time: timedelta, format_string: str = "%s days %s hours and %s minutes") -> str:
    minutes = time.seconds // 60
    hours = minutes // 60
    minutes -= hours

    days = hours // 24
    hours -= days
    days += time.days
    return format_string % (days, hours, minutes)


def get_timedelta_from_time(time: str) -> timedelta:
    if not fullmatch("([0-9]+d)?([0-9]+h)?[0-9]+m(in)?", time):
        raise ValueError("Invalid relative time format")

    days = 0
    hours = 0
    minutes = 0

    temp_num = ""

    for l in time:
        if l.isdigit():
            temp_num += l
        elif l == "d":
            days = int(temp_num)
        elif l == "h":
            hours = int(temp_num)
        elif l in ["m", "min"]:
            minutes = int(temp_num)

        if l in ("d", "h", "m", "min"):
            temp_num = ""

    return timedelta(days=days, hours=hours, minutes=minutes)
            

def get_datetime_from_str(time: str) -> datetime:
    if not fullmatch(r"[0-9]?[0-9]\.[0-2][0-9]\.[0-9]{4,4} [0-2]?[0-9]:[0-5][0-9](:[0-5][0-9])?", time):
        raise ValueError("Invalid absolute time format")

    date, daytime = time.split(" ")
    day, month, year = date.split(".")
    hour, minute, *_ = daytime.split(":")
    return datetime(
        int(year), 
        int(month), 
        int(day), 
        int(hour), 
        int(minute)
    )


async def send_simple_error_message(self, ctx, error_msg: str, color=config.COLOR.RED) -> None:
    await ctx.send(embed=embed_message(
        title=error_msg,
        color=color
    ))  

INF = float("inf")

logging.info("functions was loaded successfully")


if __name__ == "__main__":
    print(html_to_dc_md("<em><p color=\"#8f6a7b\">h<strong>a<br/></strong>llo</p></em>"))
    print(html_to_dc_md("<p>lol<ol><li><em>hal</em>lo</li><li>32io320</li></ol>lol</p>"))
    print(html_to_dc_md("<a href=\"https://gymnasium-oberstadt.de/fdfddf\">lol</a>"))
    # save_json_on_path(file="data/news.json", path="h1/h4/2/h6", value="hello")
    print(INF)
