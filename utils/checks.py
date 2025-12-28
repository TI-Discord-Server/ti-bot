import logging

import discord
from discord.app_commands import check
from discord.ext import commands

logger = logging.getLogger(__name__)

# ===== Guild IDs =====
PROD_GUILD_ID = 771394209419624489  # main server
TEST_GUILD_ID = 1334456602324897792  # test server

# ===== Role IDs (PROD) =====
COUNCIL_ROLE_ID = 860195356493742100
MODERATOR_ROLE_ID = 777987142236241941
ADMIN_ROLE_ID = 771520361618472961


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


def is_council():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild.id == PROD_GUILD_ID:
            return _has_any_role(interaction, {COUNCIL_ROLE_ID, ADMIN_ROLE_ID})

        if interaction.guild.id == TEST_GUILD_ID:
            # In testserver: alles toelaten (of pas aan naar wens)
            return True

        # Log unexpected guild access attempt
        logger.warning(
            f"Council check failed: Command '{interaction.command.name if interaction.command else 'unknown'}' "
            f"used in unexpected guild (ID: {interaction.guild.id}, Name: {interaction.guild.name}) "
            f"by user {interaction.user.name} (ID: {interaction.user.id})"
        )
        return False

    return check(predicate)


def is_moderator():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild.id == PROD_GUILD_ID:
            return _has_any_role(interaction, {MODERATOR_ROLE_ID, COUNCIL_ROLE_ID, ADMIN_ROLE_ID})

        if interaction.guild.id == TEST_GUILD_ID:
            return True

        # Log unexpected guild access attempt
        logger.warning(
            f"Moderator check failed: Command '{interaction.command.name if interaction.command else 'unknown'}' "
            f"used in unexpected guild (ID: {interaction.guild.id}, Name: {interaction.guild.name}) "
            f"by user {interaction.user.name} (ID: {interaction.user.id})"
        )
        return False

    return check(predicate)


def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild.id == PROD_GUILD_ID:
            return _has_any_role(interaction, {ADMIN_ROLE_ID})

        if interaction.guild.id == TEST_GUILD_ID:
            return True

        # Log unexpected guild access attempt
        logger.warning(
            f"Admin check failed: Command '{interaction.command.name if interaction.command else 'unknown'}' "
            f"used in unexpected guild (ID: {interaction.guild.id}, Name: {interaction.guild.name}) "
            f"by user {interaction.user.name} (ID: {interaction.user.id})"
        )
        return False

    return check(predicate)


def _has_any_role(interaction: discord.Interaction, role_ids: set[int]) -> bool:
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        return False

    # Admin permission = altijd toegestaan
    if interaction.user.guild_permissions.administrator:
        return True

    return any(role.id in role_ids for role in interaction.user.roles)


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
