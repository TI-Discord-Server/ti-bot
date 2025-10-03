from discord.app_commands import check
from discord.ext import commands


def developer():
    async def predicate(ctx):
        # Detecteer of dit een Interaction (slash) of Context (prefix) is
        client = getattr(ctx, "client", None) or getattr(ctx, "bot", None)
        user = getattr(ctx, "user", None) or getattr(ctx, "author", None)

        if not client or not user:
            return False

        # Haal developer IDs op uit DB
        settings = await client.db.settings.find_one({"_id": "server_settings"})
        developer_ids = settings.get("developer_ids", []) if settings else []

        # Als er expliciet developer IDs zijn ingesteld
        if developer_ids and user.id in developer_ids:
            return True

        # Anders: fallback naar admin permissies
        guild_id = None

        if hasattr(client, "guild_id") and client.guild_id:
            guild_id = client.guild_id
        else:
            guild_settings = await client.db.settings.find_one({"_id": "guild_settings"})
            if guild_settings and "guild_id" in guild_settings:
                guild_id = guild_settings["guild_id"]
            else:
                from main import DEFAULT_GUILD_ID

                guild_id = DEFAULT_GUILD_ID

        guild = client.get_guild(guild_id)
        if guild:
            member = guild.get_member(user.id)
            if member and member.guild_permissions.administrator:
                return True

        return False

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
