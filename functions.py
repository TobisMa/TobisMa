import ast
import json
import logging
import random
import traceback
from datetime import datetime
from types import MappingProxyType
from typing import Annotated, Any, Iterable, Literal, Mapping, Optional, Union

import discord
from discord.ext import commands

import config

LINK_DESTROYER = list(" \n\\<>'\"")

async def report_error(bot: commands.Bot, e: BaseException, log_level=logging.WARN) -> None:
    logging.log(level=log_level, msg="\n" + ''.join(
        traceback.format_exception(
            etype=type(e),
            value=e,
            tb=e.__traceback__
        )
    ))
    if (c := bot.get_channel(config.LOG_CHANNEL_ID)) is None:
        logging.error("Getting channel with id '%s' failed" % config.LOG_CHANNEL_ID)
        return

    await c.send(embed=embed_error(error=e))
    

def embed_message(*,
    title: str,
    description: str,
    color: Optional[Union[discord.Color, str]] = None,
    author: Optional[Union[discord.User, discord.Member, str, Annotated[Iterable[str], 2], discord.ClientUser]] = None,
    timestamp: Union[datetime, bool] = True,
    image: Optional[str] = None,
    url: Optional[str] = None,
#    video: Optional[dict[str, Union[str, int]]] = None,
    fields: Iterable[Union[tuple[str, str], tuple[str, str, bool], Annotated[list[str], 2], dict[str, Union[str, bool]]]] = ()
) -> discord.Embed:
    embed = discord.Embed()

    embed.title = str(title)
    embed.description = str(description)
    
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

    if image:
        embed.set_image(url=str(image))
    
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


def secure_link(link: str) -> str:
    """Converts special symbols in hexa code

    Args:
        link (str): the link

    Returns:
        str: the converted link
    """
    r = ""

    for l in link:
        if l in LINK_DESTROYER:
            r += "%" + hex(ord(l))[2:]
        else:
            r += l

    return r


def html_to_dc_md(text: str) -> str:
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
                else:
                    if not (letter == "\"" and last_sym != "\\"):
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
                
                if len(tag_pos) > 0 and tag_name == tag_pos[-1] and closing:
                    tag_pos.pop(-1)

                    # tag_name is the same as in the else
                    if tag_name in ("b", "strong"):
                        out += "**"
                    elif tag_name in ("em", "i"):
                        out += "*"

                    elif tag_name == "a":
                        if not a_link_text:
                            a_link_text = a_link
                        out += "[{}]({})".format(a_link_text, secure_link(a_link))

                else:
                    tag_pos.append(tag_name)

                    if tag_name in ("b", "strong"):
                        out += "**"
                    elif tag_name in ("em", "i"):
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
            else:
                if letter == "/":
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
    for r in roles:
        if has_role(member, r):
            return True
    return False


def has_all_roles(member: discord.Member, roles: Iterable[Union[str, int]]) -> bool:
    for r in roles:
        if not has_role(member, r):
            return False
    return True


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


def embed_error(*, error: BaseException, color: discord.Color = config.COLOR.RED, bot=None) -> discord.Embed:
    return embed_message(
        title="An '%s'-exception occured" % type(error),
        description=("```py\n" + ''.join(
            traceback.format_exception(
                etype=type(error),
                value=error,
                tb=error.__traceback__
            )
        ) + "```")[-2000:],
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


def reload_functions() -> Literal['Reloaded functions successfully']:
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


def get_random_pfp(bot: commands.Bot):
    u: Optional[discord.User] = bot.get_user(random.choice(config.OWNER_IDS))
    if u is None:
        return "https://discord.com/assets/847541504914fd33810e70a0ea73177e.ico"
    return u.avatar_url._url


logging.info("functions was loaded successfully")


if __name__ == "__main__":
    #print(html_to_dc_md("<em><p color=\"#8f6a7b\">h<strong>a<br/></strong>llo</p></em>"))
    #print(html_to_dc_md("<p>lol<ol><li><em>hal</em>lo</li><li>32io320</li></ol>lol</p>"))
    #print(html_to_dc_md("<a href=\"https://gymnasium-oberstadt.de/fdfddf\">lol</a>"))
    save_json_on_path(file="data/news.json", path="h1/h4/2/h6", value="hello")
