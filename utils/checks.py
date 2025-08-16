from discord.app_commands import check
from discord.interactions import Interaction
from discord.ext import commands


def developer():
    async def predicate(ctx: Interaction):
        # Get developer IDs from database
        settings = await ctx.client.db.settings.find_one({"_id": "server_settings"})
        developer_ids = settings.get("developer_ids", []) if settings else []
        
        # If developers are configured, check if user is in the list
        if developer_ids:
            return ctx.user.id in developer_ids
        
        # If no developers are configured, fallback to server admins
        # Get the main guild (either from database or fallback)
        guild_id = None
        if hasattr(ctx.client, 'guild_id') and ctx.client.guild_id:
            guild_id = ctx.client.guild_id
        else:
            # Try to get from database
            guild_settings = await ctx.client.db.settings.find_one({"_id": "guild_settings"})
            if guild_settings and "guild_id" in guild_settings:
                guild_id = guild_settings["guild_id"]
            else:
                # Use fallback from main.py
                from main import DEFAULT_GUILD_ID
                guild_id = DEFAULT_GUILD_ID
        
        # Get the guild and check if user is admin
        if guild_id:
            guild = ctx.client.get_guild(guild_id)
            if guild:
                member = guild.get_member(ctx.user.id)
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
