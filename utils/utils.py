import re
import typing
from typing import Literal
from urllib import parse

import discord




def truncate(text: str, max: int = 50) -> str:  # pylint: disable=redefined-builtin
    """
    Reduces the string to `max` length, by trimming the message into "...".

    Parameters
    ----------
    text : str
        The text to trim.
    max : int, optional
        The max length of the text.
        Defaults to 50.

    Returns
    -------
    str
        The truncated text.
    """
    text = text.strip()
    return text[: max - 3].strip() + "..." if len(text) > max else text

def is_image_url(url: str, **kwargs) -> Literal[b""] | str:
    """
    Check if the URL is pointing to an image.

    Parameters
    ----------
    url : str
        The URL to check.

    Returns
    -------
    bool
        Whether the URL is a valid image URL.
    """
    try:
        result = parse.urlparse(url)
        if result.netloc == "gyazo.com" and result.scheme in ["http", "https"]:
            # gyazo support
            url = re.sub(
                r"(https?://)((?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|%[0-9a-fA-F][0-9a-fA-F])+)",
                r"\1i.\2.png",
                url,
            )
    except ValueError:
        pass

    return parse_image_url(url, **kwargs)


def parse_image_url(url: str, *, convert_size=True) -> Literal[b""] | str:
    """
    Convert the image URL into a sized Discord avatar.

    Parameters
    ----------
    url : str
        The URL to convert.

    Returns
    -------
    str
        The converted URL, or '' if the URL isn't in the proper format.
    """
    types = [".png", ".jpg", ".gif", ".jpeg", ".webp"]
    url = parse.urlsplit(url)

    if any(url.path.lower().endswith(i) for i in types):
        if convert_size:
            return parse.urlunsplit((*url[:3], "size=128", url[-1]))
        else:
            return parse.urlunsplit(url)
    return ""

def human_join(seq: typing.Sequence[str], delim: str = ", ", final: str = "or") -> str:
    """https://github.com/Rapptz/RoboDanny/blob/bf7d4226350dff26df4981dd53134eeb2aceeb87/cogs/utils/formats.py#L21-L32"""
    size = len(seq)
    if size == 0:
        return ""

    if size == 1:
        return seq[0]

    if size == 2:
        return f"{seq[0]} {final} {seq[1]}"

    return delim.join(seq[:-1]) + f" {final} {seq[-1]}"

TOPIC_REGEX = re.compile(
    r"(?:\bTitle:\s*(?P<title>.*)\n)?"
    r"\bUser ID:\s*(?P<user_id>\d{17,21})\b",
    flags=re.IGNORECASE | re.DOTALL,
)
UID_REGEX = re.compile(r"\bUser ID:\s*(\d{17,21})\b", flags=re.IGNORECASE)


def parse_channel_topic(text: str) -> typing.Tuple[typing.Optional[str], int]:
    """
    A helper to parse channel topics and respectivefully returns all the required values
    at once.

    Parameters
    ----------
    text : str
        The text of channel topic.

    Returns
    -------
    Tuple[Optional[str], int, List[int]]
        A tuple of title, user ID, and other recipients IDs.
    """
    title, user_id = None, -1
    if isinstance(text, str):
        match = TOPIC_REGEX.search(text)
    else:
        match = None

    if match is not None:
        groupdict = match.groupdict()
        title = groupdict["title"]

        # user ID string is the required one in regex, so if match is found
        # the value of this won't be None
        user_id = int(groupdict["user_id"])

    return title, user_id


def match_title(text: str) -> str:
    """
    Matches a title in the format of "Title: XXXX"

    Parameters
    ----------
    text : str
        The text of the user ID.

    Returns
    -------
    Optional[str]
        The title if found.
    """
    return parse_channel_topic(text)[0]


def match_user_id(text: str, any_string: bool = False) -> int:
    """
    Matches a user ID in the format of "User ID: 12345".

    Parameters
    ----------
    text : str
        The text of the user ID.
    any_string: bool
        Whether to search any string that matches the UID_REGEX, e.g. not from channel topic.
        Defaults to False.

    Returns
    -------
    int
        The user ID if found. Otherwise, -1.
    """
    user_id = -1
    if any_string:
        match = UID_REGEX.search(text)
        if match is not None:
            user_id = int(match.group(1))
    else:
        user_id = parse_channel_topic(text)[1]

    return user_id

def get_top_role(member: discord.Member, hoisted=True):
    roles = sorted(member.roles, key=lambda r: r.position, reverse=True)
    for role in roles:
        if not hoisted:
            return role
        if role.hoist:
            return role
        return None
    return None


async def create_thread_channel(bot, recipient, category, overwrites, *, name=None, errors_raised=None):
    name = name or recipient.name
    errors_raised = errors_raised or []

    try:
        channel = await bot.guild.create_text_channel(
            name=name,
            category=category,
            overwrites=overwrites,
            topic=f"User ID: {recipient.id}",
            reason="Creating a thread channel.",
        )
    except discord.HTTPException as e:
        if (e.text, (category, name)) in errors_raised:
            # Just raise the error to prevent infinite recursion after retrying
            raise

        errors_raised.append((e.text, (category, name)))

        if "Maximum number of channels in category reached" in e.text:
            fallback = None
            fallback_id = bot.config["fallback_category_id"]
            if fallback_id:
                fallback = discord.utils.get(category.guild.categories, id=int(fallback_id))
                if fallback and len(fallback.channels) >= 49:
                    fallback = None

            if not fallback:
                fallback = await category.clone(name="Fallback Modmail")
                await bot.config.set("fallback_category_id", str(fallback.id))
                await bot.config.update()

            return await create_thread_channel(
                bot, recipient, fallback, overwrites, errors_raised=errors_raised
            )

        if "Contains words not allowed" in e.text:
            # try again but null-discrim (name could be banned)
            return await create_thread_channel(
                bot,
                recipient,
                category,
                overwrites,
                name=bot.format_channel_name(recipient, force_null=True),
                errors_raised=errors_raised,
            )

        raise

    return channel

def get_joint_id(message: discord.Message) -> typing.Optional[int]:
    """
    Get the joint ID from `discord.Embed().author.url`.
    Parameters
    -----------
    message : discord.Message
        The discord.Message object.
    Returns
    -------
    int
        The joint ID if found. Otherwise, None.
    """
    if message.embeds:
        try:
            url = getattr(message.embeds[0].author, "url", "")
            if url:
                return int(url.split("#")[-1])
        except ValueError:
            raise ValueError
    return None

class AcceptButton(discord.ui.Button):
    def __init__(self, emoji):
        super().__init__(style=discord.ButtonStyle.gray, emoji=emoji)

    async def callback(self, interaction: discord.Interaction):
        self.view.value = True
        await interaction.response.edit_message(view=None)
        self.view.stop()

class DenyButton(discord.ui.Button):
    def __init__(self, emoji):
        super().__init__(style=discord.ButtonStyle.gray, emoji=emoji)

    async def callback(self, interaction: discord.Interaction):
        self.view.value = False
        await interaction.response.edit_message(view=None)
        self.view.stop()

class ConfirmThreadCreationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=20)
        self.value = None

class DummyParam:
    """
    A dummy parameter that can be used for MissingRequiredArgument.
    """

    def __init__(self, name):
        self.name = name
        self.displayed_name = name