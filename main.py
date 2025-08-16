import asyncio
import argparse
import contextlib
import datetime
import logging
import os
import signal
import sys
import traceback
import typing
from logging.handlers import RotatingFileHandler
from typing import Awaitable, Final, Protocol
import urllib.parse

import aiohttp
from aiohttp import web
import discord
from discord import app_commands
from discord.ext import commands
from discord.interactions import Interaction
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from utils.thread import ThreadManager

from env import (
    BOT_TOKEN,
    MONGODB_PASSWORD,
    MONGODB_IP_ADDRESS,
    MONGODB_PORT,
    MONGODB_USERNAME,
    WEBHOOK_URL,

    POD_UID,
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

# Constants
DEFAULT_GUILD_ID = 1334456602324897792  # Default guild ID fallback

# Parse command line arguments
def str_to_bool(v):
    """Convert string to boolean for argument parsing."""
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

parser = argparse.ArgumentParser(description='TI Discord Bot')
parser.add_argument('--tls', type=str_to_bool, nargs='?', const=True, default=False, 
                   help='Enable TLS for MongoDB connection. Use --tls, --tls=true, or --tls=false')
args = parser.parse_args()

MONGODB_PASSWORD = urllib.parse.quote_plus(MONGODB_PASSWORD)
MONGODB_USERNAME = urllib.parse.quote_plus(MONGODB_USERNAME)
load_dotenv()

# Developer IDs are now managed through the /configure command


class PodUidFormatter(logging.Formatter):
    """Custom formatter that adds POD_UID prefix to log messages when available."""
    
    def format(self, record):
        # Get the original formatted message
        original_message = super().format(record)
        
        # Add POD_UID prefix if available (first 5 characters only)
        if POD_UID:
            pod_prefix = f"[{POD_UID[:5]}] "
            return pod_prefix + original_message
        
        return original_message


class Responder(Protocol):
    def __call__(self, content: str, *, ephemeral: bool) -> Awaitable[None]: ...


class DiscordWebhookHandler(logging.Handler):
    def __init__(self, webhook_url, bot=None):
        super().__init__()
        self.webhook_url = webhook_url
        self.bot = bot
        # Do not create a ClientSession here—set it to None; it will be lazily created.
        self.session = None
        # Rate limiting and retry configuration
        self.max_retries = 3
        self.base_delay = 2.0  # Base delay in seconds
        self.max_delay = 60.0  # Maximum delay in seconds
        self.failed_attempts = 0
        self.last_failure_time = 0

        
        # Create a file-only logger for webhook status messages
        self._file_logger = logging.getLogger('webhook_status')
        self._file_logger.setLevel(logging.INFO)
        # Only add file handler if it doesn't already exist
        if not self._file_logger.handlers:
            file_handler = RotatingFileHandler(
                "webhook_status.log",
                encoding="utf-8",
                mode="a",
                maxBytes=1024 * 1024,
                backupCount=1,
            )
            file_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s'))
            self._file_logger.addHandler(file_handler)
            # Prevent propagation to avoid webhook loops
            self._file_logger.propagate = False

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

    async def _get_webhook_format(self):
        """Get the webhook logging format from database settings."""
        if self.bot:
            try:
                settings = await self.bot.db.settings.find_one({"_id": "server_settings"}) or {}
                return settings.get("webhook_log_format", "embed")  # Default to embed
            except Exception:
                return "embed"  # Fallback to embed on error
        return "embed"

    async def _async_emit(self, record):
        import time
        
        # Check if we should skip due to too many recent failures
        current_time = time.time()
        if self.failed_attempts >= self.max_retries:
            # If it's been more than max_delay since last failure, reset counter
            if current_time - self.last_failure_time > self.max_delay:
                self.failed_attempts = 0
            else:
                # Skip this log message to prevent infinite loops
                return
        
        await self._ensure_session()
        
        for attempt in range(self.max_retries + 1):
            try:
                webhook = discord.Webhook.from_url(self.webhook_url, session=self.session)
                msg = self.format(record)
                
                # Add POD_UID prefix if available (first 5 characters only)
                if POD_UID:
                    pod_prefix = f"[{POD_UID[:5]}] "
                    msg = pod_prefix + msg
                
                # Get the current webhook format setting
                format_type = await self._get_webhook_format()
                
                if format_type == "plaintext":
                    # Plaintext format with square brackets
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    plaintext_msg = f"[{record.levelname}] [{timestamp}] {msg}"
                    await webhook.send(content=f"```\n{plaintext_msg}\n```")
                else:
                    # Default embed format
                    embed = discord.Embed(
                        title="Log Entry",
                        description=f"```{msg}```",
                        color=self._get_color(record.levelname),
                        timestamp=datetime.datetime.now(datetime.UTC),
                    )
                    embed.add_field(name="Level", value=record.levelname, inline=True)
                    embed.add_field(name="Logger", value=record.name, inline=True)
                    await webhook.send(embed=embed)
                
                # Success! Reset failure counter
                self.failed_attempts = 0
                return
                
            except discord.HTTPException as e:
                if e.status == 429:  # Rate limited
                    self.failed_attempts += 1
                    self.last_failure_time = current_time
                    
                    if attempt < self.max_retries:
                        # Calculate exponential backoff delay
                        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                        # Use file-only logger to avoid webhook loops
                        self._file_logger.warning(f"WEBHOOK Rate limited (attempt {attempt + 1}/{self.max_retries + 1}). Waiting {delay:.1f}s before retry...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        self._file_logger.error(f"WEBHOOK Max retries ({self.max_retries}) exceeded for webhook {webhook.id}. Dropping log message.")
                        return
                else:
                    # Other HTTP error, don't retry
                    self.failed_attempts += 1
                    self.last_failure_time = current_time
                    self._file_logger.error(f"WEBHOOK HTTP error {e.status}: {e.text}")
                    return
                    
            except Exception as e:
                # Other error, don't retry
                self.failed_attempts += 1
                self.last_failure_time = current_time
                self._file_logger.error(f"WEBHOOK Unexpected error: {e}")
                return

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

    async def async_close(self):
        """Async close method for proper cleanup."""
        if self.session is not None and not self.session.closed:
            await self.session.close()
        super().close()

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


class Bot(commands.Bot):
    def __init__(self, **kwargs):
        # Connect to the MongoDB database with the async version of pymongo
        connection_string = f"mongodb://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@{MONGODB_IP_ADDRESS}:{MONGODB_PORT}/{MONGODB_USERNAME}?authMechanism=SCRAM-SHA-256"
        
        # Add TLS parameters if TLS is enabled
        if args.tls:
            connection_string += "&tls=true&tlsInsecure=true"
            
        motor = AsyncIOMotorClient(
            connection_string,
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
            dm_messages=True,
            guild_reactions=True,
            dm_reactions=True,
            typing=False,
            guild_typing=False,
            dm_typing=True,
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

        self.activity = discord.CustomActivity("DM mij om de staff te contacteren")
        self.status = discord.Status.online

        self.threads = ThreadManager(self)

        # DEBUG = 10, INFO = 20, WARNING = 30, ERROR = 40, CRITICAL = 50
        bot_log = logging.getLogger("bot")
        bot_log.setLevel(logging.INFO)
        
        # Create file handler with custom formatter
        file_handler = RotatingFileHandler(
            "bot.log",
            encoding="utf-8",
            mode="a",
            maxBytes=1024 * 1024,
            backupCount=1,
        )
        file_handler.setFormatter(PodUidFormatter())
        bot_log.addHandler(file_handler)

        self.log = bot_log

        discord_log = logging.getLogger("discord")
        discord_log.setLevel(logging.WARNING)
        
        # Create file handler with custom formatter for discord logs
        discord_file_handler = RotatingFileHandler(
            "bot.log",
            encoding="utf-8",
            mode="a",
            maxBytes=1024 * 1024,
            backupCount=1,
        )
        discord_file_handler.setFormatter(PodUidFormatter())
        discord_log.addHandler(discord_file_handler)

        # Add a console handler to log to the console as well.
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(PodUidFormatter())
        bot_log.addHandler(console_handler)
        discord_log.addHandler(console_handler)

        # Add a webhook handler to log to a Discord webhook.
        if WEBHOOK_URL:
            discord_webhook_handler = DiscordWebhookHandler(WEBHOOK_URL, self)
            discord_webhook_handler.setLevel(logging.INFO)
            bot_log.addHandler(discord_webhook_handler)
            discord_log.addHandler(discord_webhook_handler)
        else:
            self.log.warning(
                "No webhook URL provided; logging to Discord webhook disabled."
            )

        self.__started = False
        self.owner_ids: frozenset[int] = frozenset()  # Will be loaded from database
        self._guild_id: typing.Optional[int] = None  # Cached guild ID
        self._shutdown_event = asyncio.Event()

        self.tree.error(self.on_application_command_error)

        # fix: we don't use self.run() as it uses asyncio.run, which replaces our event loop created above.
        #      as a result, we can't make aiohttp requests with self.session because requests are technically made
        #      between two different event loops, and it doesn't like that :(
        
        # Set up signal handlers for graceful shutdown
        def signal_handler():
            self.log.info("Received SIGTERM, initiating graceful shutdown...")
            loop.create_task(self.graceful_shutdown())
        
        # Register signal handlers (SIGTERM for Kubernetes, SIGINT for Ctrl+C)
        if hasattr(signal, 'SIGTERM'):
            loop.add_signal_handler(signal.SIGTERM, signal_handler)
        if hasattr(signal, 'SIGINT'):
            loop.add_signal_handler(signal.SIGINT, signal_handler)
        
        loop.run_until_complete(self.__init())

    async def __init(self):
        async with self:
            try:
                # Start the bot
                await self.start(self.token, reconnect=True)
            except KeyboardInterrupt:
                self.log.info("Received KeyboardInterrupt, shutting down...")
                await self.graceful_shutdown()
                return

    async def __load_cogs(self) -> None:
        # Configure jishaku to use database developers only
        os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
        os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
        await self.load_extension("jishaku")
        for m in [x.replace(".py", "") for x in os.listdir("cogs") if ".py" in x]:
            if m not in [c.__module__.split(".")[-1] for c in self.cogs.values()]:
                try:
                    await self.load_extension("cogs." + m)
                except Exception:
                    self.log.critical(f"Couldn't load {m} cog", exc_info=True)

    async def setup_hook(self) -> None:
        await self.load_extension("cogs.confessions.confession_commands")
        await self.__load_cogs()
        await self.check_db_connection()
        await self.load_developer_ids()
        await self.setup_health_check()

        # We have auto sync commands enabled, so we don't need to manually sync them.
        # with contextlib.suppress(Exception):
        #     await self.tree.sync()
        #     self.log.info("Synchronized application commands")

    async def on_ready(self) -> None:
        self.log.info("Ready called")

        if not self.__started:
            self.__started = True
            self.log.debug(f"Logged in as {self.user}")
            
            # Load guild ID and developer IDs from database
            await self.load_guild_id()
            await self.load_developer_ids()
            
            # Populate thread cache on startup
            try:
                await self.threads.populate_cache()
                self.log.info("Thread cache populated successfully")
            except Exception as e:
                self.log.error(f"Failed to populate thread cache: {e}")

    @property
    def guild(self) -> typing.Optional[discord.Guild]:
        """
        The guild that the bot is serving
        (the server where users message it from)
        """
        return discord.utils.get(self.guilds, id=self.guild_id)

    async def get_guild_id(self) -> typing.Optional[int]:
        """Get guild ID from database configuration."""
        settings = await self.db.settings.find_one({"_id": "server_settings"})
        if settings and "guild_id" in settings:
            return settings["guild_id"]
        return None

    async def load_guild_id(self):
        """Auto-detect guild ID from the guilds the bot is in."""
        # First try to get from database (for backward compatibility)
        db_guild_id = await self.get_guild_id()
        
        if db_guild_id:
            self._guild_id = db_guild_id
            self.log.info(f"Using configured guild ID {self._guild_id} from database")
        elif len(self.guilds) == 1:
            # Auto-detect: bot is in exactly one guild
            self._guild_id = self.guilds[0].id
            self.log.info(f"Auto-detected guild ID {self._guild_id} (bot is in 1 guild)")
        elif len(self.guilds) > 1:
            # Bot is in multiple guilds - use default as fallback
            self._guild_id = DEFAULT_GUILD_ID
            self.log.warning(f"Bot is in {len(self.guilds)} guilds, using default guild ID {self._guild_id}. Use /configure to change if needed.")
        else:
            # Bot is in no guilds - use default as fallback
            self._guild_id = DEFAULT_GUILD_ID
            self.log.warning(f"Bot is not in any guilds, using default guild ID {self._guild_id}")

    async def load_developer_ids(self):
        """Load developer IDs from database configuration."""
        settings = await self.db.settings.find_one({"_id": "server_settings"})
        if settings and "developer_ids" in settings:
            self.owner_ids = frozenset(settings["developer_ids"])
            self.log.info(f"Loaded {len(self.owner_ids)} developer IDs from database")
        else:
            self.log.info("No developer IDs configured in database")

    async def is_owner(self, user: discord.abc.User) -> bool:
        """Check if a user is a developer/owner of the bot."""
        # First check if developer IDs are configured in database
        settings = await self.db.settings.find_one({"_id": "server_settings"})
        developer_ids = settings.get("developer_ids", []) if settings else []
        
        if developer_ids:
            return user.id in developer_ids
        
        # If no developers configured, fallback to server admins
        guild_id = await self.get_guild_id()
        if guild_id:
            guild = self.get_guild(guild_id)
            if guild:
                member = guild.get_member(user.id)
                if member and member.guild_permissions.administrator:
                    return True
        
        return False

    @property
    def guild_id(self) -> typing.Optional[int]:
        """Synchronous property that returns cached guild ID."""
        return self._guild_id

    def get_guild_icon(
            self, guild: typing.Optional[discord.Guild], *, size: typing.Optional[int] = None
    ) -> str:
        if guild is None:
            guild = self.guild
        if guild.icon is None:
            return "https://cdn.discordapp.com/embed/avatars/0.png"
        if size is None:
            return guild.icon.url
        return guild.icon.with_size(size).url

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if isinstance(message.channel, discord.DMChannel):
            return await self.process_dm_modmail(message)

        with contextlib.suppress(Exception):
            ctx = await self.get_context(message)
            if ctx.valid:
                await self.invoke(ctx)
            elif ctx.invoked_with:
                exc = commands.CommandNotFound('Command "{}" is not found'.format(ctx.invoked_with))
                self.dispatch("command_error", ctx, exc)

    @staticmethod
    async def add_reaction(self,
            msg, reaction: typing.Union[discord.Emoji, discord.Reaction, discord.PartialEmoji, str]
    ) -> bool:
        if reaction != "disable":
            try:
                await msg.add_reaction(reaction)
            except (discord.HTTPException, TypeError) as e:
                self.bot.log.warning(f"Failed to add reaction to {reaction}: {e}") #TODO
                return False
        return True

    async def process_dm_modmail(self, message: discord.Message) -> None:
        """Processes messages sent to the bot."""
        if message.type not in [discord.MessageType.default, discord.MessageType.reply]:
            return

        thread = await self.threads.find(recipient=message.author)
        if thread is None:
            thread = await self.threads.create(message.author, message=message)

        if not thread.cancelled:
            try:
                await thread.send(message)
            except Exception as e:
                self.log.info(f"Failed to send message ({message.content}) to thread ({thread.channel}): {e}", exc_info=True)
                # logger.error("Failed to send message:", exc_info=True)
                await self.add_reaction(self, message, "❌")
            else:

                # send to all other recipients
                if thread.recipient != message.author:
                    try:
                        await thread.send(message, thread.recipient)
                    except Exception:
                        # silently ignore
                        self.log.error("Failed to send message:", exc_info=True)
                        # logger.error("Failed to send message:", exc_info=True)

                await self.add_reaction(self, message, "✅")
                self.dispatch("thread_reply", thread, False, message, False, False)

    async def on_message_delete(self, message):
        """Support for deleting linked messages"""

        if message.is_system():
            return

        if isinstance(message.channel, discord.DMChannel):
            if message.author == self.user:
                return
            thread = await self.threads.find(recipient=message.author)
            if not thread:
                return
            try:
                message = await thread.find_linked_message_from_dm(message, get_thread_channel=True)
            except ValueError as e:
                if str(e) != "Thread channel message not found.":
                    self.log.info(f"Failed to find linked message to delete: {e}")
                return
            message = message[0]
            embed = message.embeds[0]

            if embed.footer.icon:
                icon_url = embed.footer.icon.url
            else:
                icon_url = None

            embed.set_footer(text="(deleted)", icon_url=icon_url)
            await message.edit(embed=embed)
            return

        if message.author != self.user:
            return

        thread = await self.threads.find(channel=message.channel)
        if not thread:
            return

        # try:
        #     await thread.delete_message(message, note=False)
        #     embed = discord.Embed(description="Successfully deleted message.", color=discord.Color.blurple())
        # except ValueError as e:
        #     if str(e) not in {"DM message not found.", "Malformed thread message."}:
        #         self.log.info(f"Failed to delete linked message to delete: {e}")
        #         embed = discord.Embed(description="Failed to delete message.", color=discord.Color.red())
        #     else:
        #         return
        # except discord.NotFound:
        #     return
        # embed.set_footer(text=f"Message ID: {message.id} from {message.author}.")
        # return await message.channel.send(embed=embed)

    async def on_message_edit(self, before, after):
        if after.author.bot:
            return
        if before.content == after.content:
            return

        if isinstance(after.channel, discord.DMChannel):
            thread = await self.threads.find(recipient=before.author)
            if not thread:
                return

            try:
                await thread.edit_dm_message(before, after.content)
            except ValueError:
                await self.add_reaction(self, after, "❌")
            else:
                embed = discord.Embed(description="Successfully Edited Message", color=discord.Color.blurple())
                embed.set_footer(text=f"Message ID: {after.id}")
                await after.channel.send(embed=embed)



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
            elif isinstance(error.original, aiohttp.ClientOSError):
                with contextlib.suppress(Exception):
                    await respond(":x: | An unknown error occurred!", ephemeral=True)

                return
            else:
                self.log.error(
                    "Unhandled application command error",
                    exc_info=(type(error), error, error.__traceback__)
                )
                em = discord.Embed(
                    title=interaction.command.qualified_name,  # type: ignore
                    description=interaction.command.qualified_name,  # type: ignore
                    colour=discord.Colour(0xFFFFFF),
                )
                avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None
                em.set_author(
                    name="Critical Error",
                    icon_url=avatar_url,
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
            avatar_url = ctx.author.display_avatar.url if ctx.author.display_avatar else None
            em.set_author(
                name=f"{command.full_parent_name} {command.name}",
                icon_url=avatar_url,
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
            self.log.error(
                "Command invoke error",
                exc_info=(type(error), error, error.__traceback__)
            )
            e = discord.Embed(
                description=ctx.message.content, colour=discord.Colour(0xFFFFFF)
            )
            avatar_url = ctx.author.display_avatar.url if ctx.author.display_avatar else None
            e.set_author(
                name="Critical Error",
                icon_url=avatar_url,
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

    async def graceful_shutdown(self):
        """Gracefully shutdown the bot and close all connections."""
        self.log.info("Received shutdown signal, starting graceful shutdown...")
        
        try:
            # Step 1: Set shutdown event to mark health check as unhealthy
            # This signals Kubernetes to stop routing traffic to this pod
            self._shutdown_event.set()
            self.log.info("Health check marked as unhealthy - Kubernetes will stop routing traffic")
            
            # Give Kubernetes a moment to detect unhealthy status and stop routing traffic
            await asyncio.sleep(2.0)
            
            # Step 2: Close Discord connection to stop accepting new requests
            await asyncio.wait_for(self.close(), timeout=10.0)
            self.log.info("Discord connection closed - no new requests will be processed")
            
            # Step 3: Send shutdown progress logs (webhook logging still available)
            self.log.info("Beginning final service cleanup...")
            
            # Step 4: Close other services (but keep webhook logging available)
            # Close database connection
            if hasattr(self, 'db') and self.db is not None:
                self.db.client.close()
                self.log.info("Database connection closed")
            
            # Close bot's main aiohttp session (webhook handler has its own session)
            if hasattr(self, 'session') and self.session is not None and not self.session.closed:
                await asyncio.wait_for(self.session.close(), timeout=5.0)
                self.log.info("Bot HTTP session closed")
            
            # Send final log message before closing webhook sessions
            self.log.info("All services closed - shutting down webhook logging...")
            
            # Give time for final webhook logs to be sent
            await asyncio.sleep(2.0)
            
            # Close webhook handler sessions
            for handler in self.log.handlers:
                if isinstance(handler, DiscordWebhookHandler):
                    try:
                        await handler.async_close()
                        self.log.info("Webhook handler session closed")
                    except Exception as e:
                        print(f"Error closing webhook handler: {e}")  # Use print since logging might not work
            
            # Step 6: Finally close health check server completely
            if hasattr(self, 'site') and self.site is not None:
                await asyncio.wait_for(self.site.stop(), timeout=5.0)
                self.log.info("Health check server stopped completely")
            
        except asyncio.TimeoutError:
            self.log.warning("Graceful shutdown timed out, forcing exit")
        except Exception as e:
            self.log.error(f"Error during graceful shutdown: {e}")
        
        self.log.info("Graceful shutdown completed")

    async def setup_health_check(self):
        async def health_handler(request):
            is_ready = self.is_ready()
            data = {
                "status": "healthy" if is_ready else "starting",
                "discord_connection": "connected" if is_ready else "disconnected",
                "discord_heartbeat_latency": f"{round(self.latency * 1000)} ms" if is_ready else "N/A",
                "uptime": str(datetime.datetime.now() - self.uptime)
            }
            # Return 200 for healthy, 503 for starting (Kubernetes will wait for 200)
            status_code = 200 if is_ready else 503
            return web.json_response(data, status=status_code)

        app = web.Application()
        app.router.add_get('/health', health_handler)

        runner = web.AppRunner(app)
        await runner.setup()
        self.site = web.TCPSite(runner, '0.0.0.0', 3000)

        await self.site.start()
        self.log.info("Health check endpoint started on http://0.0.0.0:3000/health")


def main():
    """Main entry point for the bot."""
    try:
        bot = Bot()
    except KeyboardInterrupt:
        print("Bot startup interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Failed to start bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
