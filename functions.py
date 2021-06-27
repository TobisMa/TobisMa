import json
import logging
import sys
import traceback
from datetime import datetime
from typing import Annotated, Any, Iterable, Optional, Union

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

    await c.send(embed=embed_error(e))
    

def embed_message(*,
    title: str,
    description: str,
    color: Optional[Union[discord.Color, str]] = None,
    author: Optional[Union[discord.User, discord.Member, str, Annotated[Iterable[str], 2]]] = None,
    timestamp: Union[datetime, bool] = True,
    image: Optional[str] = None,
    url: Optional[str] = None,
#    video: Optional[dict[str, Union[str, int]]] = None,
    fields: Iterable[Union[tuple[str, str], tuple[str, str, bool], Annotated[list[str], 2]]] = ()
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
        if len(f) == 2:
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


def embed_error(err: BaseException) -> discord.Embed:
    embed = discord.Embed()

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


logging.info("functions was loaded successfully")


if __name__ == "__main__":
    #print(html_to_dc_md("<em><p color=\"#8f6a7b\">h<strong>a<br/></strong>llo</p></em>"))
    #print(html_to_dc_md("<p>lol<ol><li><em>hal</em>lo</li><li>32io320</li></ol>lol</p>"))
    #print(html_to_dc_md("<a href=\"https://gymnasium-oberstadt.de/fdfddf\">lol</a>"))
    save_json_on_path(file="data/news.json", path="h1/h4/2/h6", value="hello")
