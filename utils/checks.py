from discord.app_commands import check
from discord.interactions import Interaction
from main import DEVELOPER_IDS__THIS_WILL_GIVE_OWNER_COG_PERMS as developer_ids
from discord.ext import commands


def developer():
    async def predicate(ctx: Interaction):
        return ctx.user.id in developer_ids
    return check(predicate)


def thread_only():
    """
    A decorator that checks if the command
    is being ran within a Modmail thread.
    """

    async def predicate(ctx):
        """
        Parameters
        ----------
        ctx : Context
            The current discord.py `Context`.

        Returns
        -------
        Bool
            `True` if the current `Context` is within a Modmail thread.
            Otherwise, `False`.
        """
        return ctx.thread is not None

    predicate.fail_msg = "This is not a Modmail thread."
    return commands.check(predicate)
