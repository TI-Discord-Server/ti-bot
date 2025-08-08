from discord.app_commands import check
from discord.interactions import Interaction
from discord.ext import commands


def developer():
    async def predicate(ctx: Interaction):
        # Get developer IDs from database
        settings = await ctx.client.db.settings.find_one({"_id": "server_settings"})
        if not settings or "developer_ids" not in settings:
            return False
        developer_ids = settings["developer_ids"]
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
