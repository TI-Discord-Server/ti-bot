import asyncio
import contextlib
import datetime
import logging
import os
import sys
import traceback
from logging.handlers import RotatingFileHandler
from typing import Awaitable, Final, Protocol

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from discord.interactions import Interaction
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from env import (
    BOT_TOKEN,
    MONGODB_PASSWORD,
    MONGODB_IP_ADDRESS,
    WEBHOOK_URL,
)
from utils.errors import (
    ForbiddenAction,
    ResponseTimeout,
    UnknownEmoji,
    UnknownInvite,
    UnknownMessage,
    UnknownRole,
    UnknownUser,
)

load_dotenv()

DEVELOPER_IDS__THIS_WILL_GIVE_OWNER_COG_PERMS: Final[frozenset[int]] = frozenset(
    [
        123468845749895170,  # Quinten - @quintenvw
        406131690742743050,  # Amber - @annanas
        402102269509894144,  # Kobe - @k0be_
        329293977494880257,  # Arthur - @arthurvg
        925002667502239784,  # Jaak - @princessakina
        251334912576192513,  # Maxime - @tailstm
        203245885608558592,  # Roan - @littlebladed
        304989265518133249,  # Sterre - @clustarz
        337521371414396928,  # Warre - @warru
    ]
)


class Responder(Protocol):
    def __call__(self, content: str, *, ephemeral: bool) -> Awaitable[None]: ...


class DiscordWebhookHandler(logging.Handler):
    def __init__(self, webhook_url):
        super().__init__()
        self.webhook_url = webhook_url
        # Do not create a ClientSession here—set it to None; it will be lazily created.
        self.session = None

    async def _ensure_session(self):
        # Create the ClientSession only when needed and within an async context.
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    def emit(self, record):
        try:
            # Schedule the asynchronous sending of the log record.
            asyncio.create_task(self._async_emit(record))
        except Exception:
            self.handleError(record)

    async def _async_emit(self, record):
        await self._ensure_session()
        try:
            # Create a Discord webhook using the asynchronously created session.
            webhook = discord.Webhook.from_url(self.webhook_url, session=self.session)
            msg = self.format(record)
            embed = discord.Embed(
                title="Log Entry",
                description=f"```{msg}```",
                color=self._get_color(record.levelname),
                timestamp=datetime.datetime.utcnow(),
            )
            embed.add_field(name="Level", value=record.levelname, inline=True)
            embed.add_field(name="Logger", value=record.name, inline=True)
            await webhook.send(embed=embed)
        except Exception:
            self.handleError(record)

    def _get_color(self, levelname):
        # Map log level names to Discord color objects.
        colors = {
            "DEBUG": discord.Color.light_grey(),
            "INFO": discord.Color.green(),
            "WARNING": discord.Color.yellow(),
            "ERROR": discord.Color.red(),
            "CRITICAL": discord.Color.dark_red(),
        }
        return colors.get(levelname, discord.Color.default())

    def close(self):
        # If the session was created, schedule its closure.
        if self.session is not None and not self.session.closed:
            try:
                # Try to fetch the running loop; if there isn’t one, skip closing.
                loop = asyncio.get_running_loop()
                # Schedule the asynchronous close
                loop.create_task(self.session.close())
            except RuntimeError:
                # No running event loop available; session may be cleaned up on process exit.
                pass
        super().close()

    def _get_color(self, level_name):
        colors = {
            "DEBUG": discord.Color.light_grey(),
            "INFO": discord.Color.green(),
            "WARNING": discord.Color.yellow(),
            "ERROR": discord.Color.red(),
            "CRITICAL": discord.Color.dark_red(),
        }
        return colors.get(level_name, discord.Color.default())


class Bot(commands.Bot):
    def __init__(self, **kwargs):
        # Connect to te MongoDB database with the async version of pymongo. Change IP address if needed.
        motor = AsyncIOMotorClient(
            f"mongodb://bot:{MONGODB_PASSWORD}@{MONGODB_IP_ADDRESS}:27017/bot?authMechanism=SCRAM-SHA-256",
            connect=True,
        )
        motor.get_io_loop = asyncio.get_running_loop
        self.db = motor.bot
        self.color = discord.Color.blurple()
        self.token = BOT_TOKEN

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # Select whatever we need here and make sure we have the correct things enabled on the Discord Developer Portal.
        intents = discord.Intents(
            guilds=True,
            members=True,
            bans=True,
            emojis=True,
            integrations=False,
            webhooks=True,
            invites=True,
            voice_states=True,
            presences=True,
            guild_messages=True,
            dm_messages=False,
            guild_reactions=True,
            dm_reactions=False,
            typing=False,
            guild_typing=False,
            dm_typing=False,
            guild_scheduled_events=False,
            emojis_and_stickers=True,
            message_content=True,
            auto_moderation_configuration=True,
            auto_moderation_execution=True,
        )
        super().__init__(
            **kwargs,  # type: ignore
            loop=loop,
            max_messages=10_000,
            command_prefix="?",
            chunk_guilds_at_startup=True,
            auto_sync_commands=True,
            intents=intents,
        )

        self.session = aiohttp.ClientSession(loop=loop)
        self.uptime = datetime.datetime.now()

        self.activity = discord.CustomActivity("Oil up Warre")
        self.status = discord.Status.online

        # DEBUG = 10, INFO = 20, WARNING = 30, ERROR = 40, CRITICAL = 50
        bot_log = logging.getLogger("bot")
        bot_log.setLevel(logging.INFO)
        bot_log.addHandler(
            RotatingFileHandler(
                "bot.log",
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
                "bot.log",
                encoding="utf-8",
                mode="a",
                maxBytes=1024 * 1024,
                backupCount=1,
            )
        )

        # Add a console handler to log to the console as well.
        console_handler = logging.StreamHandler()
        bot_log.addHandler(console_handler)
        discord_log.addHandler(console_handler)

        # Add a webhook handler to log to a Discord webhook.
        if WEBHOOK_URL:
            discord_webhook_handler = DiscordWebhookHandler(WEBHOOK_URL)
            discord_webhook_handler.setLevel(logging.INFO)
            bot_log.addHandler(discord_webhook_handler)
            discord_log.addHandler(discord_webhook_handler)
        else:
            self.log.warning(
                "No webhook URL provided; logging to Discord webhook disabled."
            )

        self.__started = False
        self.owner_ids: frozenset[int] = (  # type: ignore
            DEVELOPER_IDS__THIS_WILL_GIVE_OWNER_COG_PERMS
        )

        self.tree.error(self.on_application_command_error)

        # fix: we don't use self.run() as it uses asyncio.run, which replaces our event loop created above.
        #      as a result, we can't make aiohttp requests with self.session because requests are technically made
        #      between two different event loops, and it doesn't like that :(
        loop.run_until_complete(self.__init())

    async def __init(self):
        async with self:
            try:
                await self.start(self.token, reconnect=True)
            except KeyboardInterrupt:
                return

    async def __load_cogs(self) -> None:
        await self.load_extension("jishaku")
        for m in [x.replace(".py", "") for x in os.listdir("cogs") if ".py" in x]:
            if m not in [c.__module__.split(".")[-1] for c in self.cogs.values()]:
                try:
                    await self.load_extension("cogs." + m)
                except Exception:
                    self.log.critical(f"Couldn't load {m} cog", exc_info=True)

    async def setup_hook(self) -> None:
        await self.__load_cogs()

        # Check if the database connection is working
        await self.check_db_connection()

        # We have auto sync commands enabled, so we don't need to manually sync them.
        # with contextlib.suppress(Exception):
        #     await self.tree.sync()
        #     self.log.info("Synchronized application commands")

    async def on_ready(self) -> None:
        self.log.info("Ready called")

        if not self.__started:
            self.__started = True
            self.log.debug(f"Logged in as {self.user}")

    async def on_message(self, message: discord.Message) -> None:
        if message.author.id not in self.owner_ids:
            return

        with contextlib.suppress(Exception):
            ctx = await self.get_context(message)

            if ctx.valid:
                await self.invoke(ctx)

    def _format_cooldown(self, retry_after: float) -> str:
        m, s = divmod(retry_after, 60)
        h, m = divmod(m, 60)

        if h != 0:
            return "{} hour" + ("s" if h != 1 else "").format(int(h))
        elif m != 0:
            return "{} minute" + ("s" if m != 1 else "").format(int(m))
        else:
            return "{} second" + ("s" if s != 1 else "").format(max(int(s), 1))

    async def __handle_application_error(
        self,
        interaction: Interaction,
        error: app_commands.AppCommandError,
        respond: Responder,
    ) -> bool:
        original: BaseException

        if isinstance(error, app_commands.CommandInvokeError):
            original = error.original
        elif (
            isinstance(error, app_commands.TransformerError)
            and error.__cause__ is not None
        ):
            original = error.__cause__
        else:
            return False

        if isinstance(original, UnknownMessage):
            with contextlib.suppress(Exception):
                await respond(":x: | I couldn't find that message!", ephemeral=True)
        elif isinstance(original, UnknownUser):
            with contextlib.suppress(Exception):
                await respond(":x: | I couldn't find that user!", ephemeral=True)
        elif isinstance(original, UnknownRole):
            with contextlib.suppress(Exception):
                await respond(":x: | I couldn't find that role!", ephemeral=True)
        elif isinstance(original, UnknownEmoji):
            with contextlib.suppress(Exception):
                await respond(":x: | I couldn't find that emoji!", ephemeral=True)
        elif isinstance(original, UnknownInvite):
            with contextlib.suppress(Exception):
                await respond(":x: | I couldn't find that invite!", ephemeral=True)
        else:
            return False

        return True

    async def on_application_command_error(
        self, interaction: Interaction, error: app_commands.AppCommandError
    ):
        respond = (
            interaction.response.send_message
            if not interaction.response.is_done()
            else interaction.followup.send
        )

        if await self.__handle_application_error(interaction, error, respond):
            return

        if isinstance(
            error,
            (
                app_commands.CommandNotFound,
                app_commands.NoPrivateMessage,
                app_commands.MissingPermissions,
            ),
        ):
            return
        elif isinstance(error, app_commands.BotMissingPermissions):
            with contextlib.suppress(Exception):
                await respond(
                    ":x: | I don't have the required permissions!", ephemeral=True
                )

            return
        elif isinstance(error, app_commands.CommandOnCooldown):
            time = self._format_cooldown(error.retry_after)

            with contextlib.suppress(Exception):
                await respond(
                    ":hourglass: **| Cooldown:** {}".format(time), ephemeral=True
                )

            return
        elif isinstance(error, app_commands.CheckFailure) or (
            hasattr(error, "original")
            and isinstance(error.original, app_commands.CheckFailure)  # type: ignore
        ):
            message = str(getattr(error, "original", error))

            if message == "Moderator":
                with contextlib.suppress(Exception):
                    await respond(
                        ":x: | Only server moderators can use this command!",
                        ephemeral=True,
                    )
            elif message == "Administrator":
                with contextlib.suppress(Exception):
                    await respond(
                        ":x: | Only server administrators can use this command!",
                        ephemeral=True,
                    )

            return
        elif isinstance(error, app_commands.CommandInvokeError):
            if isinstance(error.original, discord.Forbidden):
                with contextlib.suppress(Exception):
                    await respond(
                        ":x: | I don't have the required permissions!",
                        ephemeral=True,
                    )

                return
            elif isinstance(
                error.original,
                (discord.NotFound, discord.HTTPException, discord.DiscordServerError),
            ):
                with contextlib.suppress(Exception):
                    await respond(":x: | An unknown error occurred!", ephemeral=True)

                return
            elif isinstance(error.original, ForbiddenAction):
                with contextlib.suppress(Exception):
                    await respond(":x: | You can't do that!", ephemeral=True)

                return
            elif isinstance(error.original, ResponseTimeout):
                with contextlib.suppress(Exception):
                    await respond(":hourglass: | Try again later!", ephemeral=True)

                return

                return
            elif isinstance(error.original, aiohttp.ClientOSError):
                with contextlib.suppress(Exception):
                    await respond(":x: | An unknown error occurred!", ephemeral=True)

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
                    title=interaction.command.qualified_name,  # type: ignore
                    description=interaction.command.qualified_name,  # type: ignore
                    colour=discord.Colour(0xFFFFFF),
                )
                em.set_author(
                    name="Critical Error",
                    icon_url=interaction.user.display_avatar.url,
                )
                em.set_footer(text="Please report this error to a developer!")

                try:
                    await respond(embed=em, ephemeral=True)
                except Exception:
                    pass

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        command: commands.Command = ctx.command  # type: ignore

        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(
            error,
            (
                commands.BadArgument,
                commands.MissingRequiredArgument,
                commands.UserInputError,
            ),
        ):
            msg = ""

            if not command.usage:
                for x in command.params:
                    if x != "ctx" and x != "self":
                        if "None" in str(command.params[x]):
                            msg += " [{}]".format(x)
                        else:
                            msg += " <{}>".format(x)
            else:
                msg += f" {command.usage}"

            em = discord.Embed(colour=discord.Colour(0xFFFFFF))
            em.set_author(
                name=f"{command.full_parent_name} {command.name}",
                icon_url=ctx.author.display_avatar.url,
            )
            em.add_field(
                name="Usage",
                value="`{}{}{}`".format(ctx.prefix, ctx.command, msg),
                inline=False,
            )
            em.set_footer(text=command.help)

            with contextlib.suppress(Exception):
                await ctx.send(embed=em)
            return

        elif isinstance(error, (discord.Forbidden, commands.BotMissingPermissions)):
            with contextlib.suppress(Exception):
                await ctx.send(":x: | I don't have the required permissions!")

            return
        elif hasattr(error, "original") and isinstance(
            error.original,
            discord.HTTPException,  # type: ignore
        ):
            with contextlib.suppress(Exception):
                await ctx.send(":x: | An unknown error occurred!")

            return
        elif isinstance(error, commands.CommandInvokeError):
            print(
                "".join(
                    traceback.format_exception(type(error), error, error.__traceback__)
                )
            )
            e = discord.Embed(
                description=ctx.message.content, colour=discord.Colour(0xFFFFFF)
            )
            e.set_author(
                name="Critical Error",
                icon_url=ctx.author.display_avatar.url,
            )
            e.set_footer(text="Please report this error to a developer!")

            with contextlib.suppress(Exception):
                await ctx.send(embed=e)

    async def on_error(self, *args, **kwargs):
        self.log.critical(traceback.format_exc())

    async def check_db_connection(self) -> None:
        try:
            # Force a connection by pinging the MongoDB server
            await self.db.client.admin.command("ping")
            self.log.info("Successfully connected to the MongoDB database.")
        except Exception as e:
            self.log.critical("Database connection error: %s", e)
            # Exit the bot if the connection check fails
            await asyncio.sleep(1)
            sys.exit(1)


if __name__ == "__main__":
    Bot()
