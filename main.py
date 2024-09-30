import discord
from discord.ext import commands

import asyncio
import aiohttp
import traceback
import os
import datetime
import logging
from logging.handlers import RotatingFileHandler
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

from utils.errors import (
    ForbiddenAction,
    ResponseTimeout,
    UnknownMessage,
    UnknownUser,
    UnknownRole,
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD")
MONGODB_IP_ADDRESS = os.getenv("MONGODB_IP_ADDRESS")


class MakiContext(commands.Context):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Bot(commands.Bot):
    def __init__(self, **kwargs):
        motor = AsyncIOMotorClient(
            f"mongodb://bot:{MONGODB_PASSWORD}@{MONGODB_IP_ADDRESS}:27017/bot?authMechanism=SCRAM-SHA-256",
            connect=True,
        )
        motor.get_io_loop = asyncio.get_running_loop
        self.db = motor.bot

        self.token = BOT_TOKEN

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        intents = discord.Intents(
            guilds=True,
            members=True,
            bans=True,
            emojis=True,
            integrations=False,
            webhooks=True,
            invites=True,
            voice_states=True,
            presences=False,
            guild_messages=True,
            dm_messages=False,
            guild_reactions=True,
            dm_reactions=False,
            typing=False,
            guild_typing=False,
            dm_typing=False,
            scheduled_events=False,
            emojis_and_stickers=True,
            message_content=True,
            auto_moderation_configuration=True,
            auto_moderation_execution=True,
        )
        member_cache_flags = discord.MemberCacheFlags(
            voice=True, joined=False, interaction=True
        )  # discord.MemberCacheFlags.from_intents(intents)
        super().__init__(
            **kwargs,
            loop=loop,
            max_messages=10_000,
            command_prefix="!",
            chunk_guilds_at_startup=False,
            auto_sync_commands=False,
            member_cache_flags=member_cache_flags,
            intents=intents,
        )

        self.session = aiohttp.ClientSession(loop=loop)
        self.uptime = datetime.datetime.now()

        self.activity = discord.CustomActivity(self.presence)
        self.status = discord.Status.online

        self.cooldown_users = commands.CooldownMapping.from_cooldown(
            2, 1, commands.BucketType.user
        )
        self.cooldown_channels = commands.CooldownMapping.from_cooldown(
            7, 2, commands.BucketType.channel
        )
        self.cooldown_guilds = commands.CooldownMapping.from_cooldown(
            9, 1, commands.BucketType.guild
        )

        self.add_check(
            commands.bot_has_permissions(
                add_reactions=True,
                attach_files=True,
                embed_links=True,
                external_emojis=True,
                read_message_history=True,
                read_messages=True,
                send_messages=True,
                send_messages_in_threads=True,
            ).predicate
        )

        bot_log = logging.getLogger("Bot")
        bot_log.setLevel(logging.INFO)
        bot_log.addHandler(
            RotatingFileHandler(
                "Bot.log",
                encoding="utf-8",
                mode="a",
                maxBytes=1024 * 1024,
                backupCount=1,
            )
        )

        self.log = bot_log

        discord_log = logging.getLogger("discord")
        discord_log.setLevel(logging.WARNING)
        discord_log.addHandler(
            RotatingFileHandler(
                "Bot.log",
                encoding="utf-8",
                mode="a",
                maxBytes=1024 * 1024,
                backupCount=1,
            )
        )

        for m in [x.replace(".py", "") for x in os.listdir("cogs") if ".py" in x]:
            if m not in [c.__module__.split(".")[-1] for c in self.cogs.values()]:
                try:
                    self.load_extension("cogs." + m)
                except Exception as e:
                    self.log.critical(f"Couldn't load {m} cog : e")
                    raise Exception(e)
        self.loop.create_task(self.do_startup_tasks())
        self.run(self.token)

    async def do_startup_tasks(self):
        await self.wait_until_ready()
        self.ready = True
        self.log.debug(f"Logged in as {self.user}")

    async def on_ready(self):
        self.log.info("Ready called")

    async def on_connect(self):
        await self.sync_commands(method="bulk")
        self.log.info("Synchronized application commands")

    async def on_message(self, message):
        if message.author.id in self.owner_ids:
            return
        try:
            ctx = await self.get_context(message, cls=MakiContext)
            if ctx.valid:
                await self.invoke(ctx)
        except Exception:
            return

    async def on_application_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.respond(
                    ":x: | This command can't be used in private messages!",
                    ephemeral=True,
                )
            except Exception:
                return
            return

        elif isinstance(error, commands.MissingPermissions):
            try:
                await ctx.respond(
                    ":x: | You don't have the required permissions!", ephemeral=True
                )
            except Exception:
                return
            return

        elif isinstance(error, commands.BotMissingPermissions):
            try:
                await ctx.respond(
                    ":x: | I don't have the required permissions!", ephemeral=True
                )
            except Exception:
                return
            return

        elif isinstance(error, commands.CommandOnCooldown):
            try:
                await ctx.respond(
                    ":hourglass: | Nog even geduld, je heb en cooldown bereikt!",
                    ephemeral=True,
                )
            except Exception:
                return
            return

        elif isinstance(error, commands.CheckFailure):
            if str(error) == "Moderator":
                try:
                    await ctx.respond(
                        ":x: | Enkel server moderators kunnen dit commando gebruiken!",
                        ephemeral=True,
                    )
                except Exception:
                    return
            elif str(error) == "Administrator":
                try:
                    await ctx.respond(
                        ":x: | Enkel server administrators kunnen dit commando gebruiken!",
                        ephemeral=True,
                    )
                except Exception:
                    return
            return

        elif isinstance(error, discord.ApplicationCommandInvokeError):
            if isinstance(error.original, discord.Forbidden):
                try:
                    await ctx.respond(
                        ":x: | Ik ontbreek enkele permissies!", ephemeral=True
                    )
                except Exception:
                    return
                return

            if isinstance(error.original, discord.NotFound):
                try:
                    await ctx.respond(
                        ":x: | Een okbekende error is voorgekomen!", ephemeral=True
                    )
                except Exception:
                    return
                return

            elif isinstance(error.original, discord.HTTPException):
                try:
                    await ctx.respond(
                        ":x: | Een okbekende error is voorgekomen!", ephemeral=True
                    )
                except Exception:
                    return
                return

            elif isinstance(error.original, discord.DiscordServerError):
                try:
                    await ctx.respond(
                        ":x: | Een okbekende error is voorgekomen!", ephemeral=True
                    )
                except Exception:
                    return
                return

            elif isinstance(error.original, ForbiddenAction):
                try:
                    await ctx.respond(
                        ":x: | Je hebt geen toestemming om dit te doen!", ephemeral=True
                    )
                except Exception:
                    return
                return

            elif isinstance(error.original, ResponseTimeout):
                try:
                    await ctx.respond(
                        ":hourglass: | Probeer het later nogeens!", ephemeral=True
                    )
                except Exception:
                    return
                return

            elif isinstance(error.original, UnknownMessage):
                try:
                    await ctx.respond(":x: | Onbekend bericht!", ephemeral=True)
                except Exception:
                    return
                return

            elif isinstance(error.original, UnknownUser):
                try:
                    await ctx.respond(":x: | Onbekende gebruiker!", ephemeral=True)
                except Exception:
                    return
                return

            elif isinstance(error.original, UnknownRole):
                try:
                    await ctx.respond(":x: | Onbekende rol!", ephemeral=True)
                except Exception:
                    return
                return

            elif isinstance(error.original, aiohttp.client_exceptions.ClientOSError):
                try:
                    await ctx.respond(
                        ":x: | Een okbekende error is voorgekomen!", ephemeral=True
                    )
                except Exception:
                    return
                return

            else:
                print(
                    "".join(
                        traceback.format_exception(
                            type(error), error, error.__traceback__
                        )
                    )
                )
                em = discord.Embed(
                    title=ctx.command.qualified_name,
                    description=ctx.command.qualified_name,
                    colour=discord.Colour(0x000000),
                )
                em.set_author(
                    name=f"{self.user.name} | Error",
                    icon_url=ctx.author.display_avatar.url,
                )
                em.set_footer(text="Gelieve dit te melden aan het team!")
                try:
                    await ctx.respond(embed=em, ephemeral=True)
                except Exception:
                    pass

    async def on_error(self, *args, **kwargs):
        self.log.critical(traceback.format_exc())


if __name__ == "__main__":
    Bot()
