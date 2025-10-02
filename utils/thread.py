"""
thread by modmail-dev
Source:
https://github.com/modmail-dev/Modmail/blob/master/core/thread.py

Note: "Thread" in this context refers to a modmail conversation thread,
which is implemented using Discord channels (not Discord's thread feature).
Each modmail conversation creates a dedicated Discord channel.
"""
import asyncio
import base64
import copy
import functools
import io
import re
import traceback
import typing
import warnings
from datetime import timedelta, datetime

import isodate

import discord
from discord.ext.commands import MissingRequiredArgument, CommandError
from lottie.importers import importers as l_importers
from lottie.exporters import exporters as l_exporters

from .timezone import LOCAL_TIMEZONE
from .models import DummyMessage
from .utils import (
    is_image_url,
    parse_channel_topic,
    match_user_id,
    create_thread_channel,
    AcceptButton,
    DenyButton,
    ConfirmThreadCreationView,
    DummyParam,
)

class Thread:
    """Represents a discord Modmail channel thread."""

    def __init__(
        self,
        manager: "ThreadManager",
        recipient: typing.Union[discord.Member, discord.User, int],
        channel: typing.Union[discord.DMChannel, discord.TextChannel] = None,
    ):
        self.manager = manager
        self.bot = manager.bot
        if isinstance(recipient, int):
            self._id = recipient
            self._recipient = None
        else:
            if recipient.bot:
                raise CommandError("Recipient cannot be a bot.")
            self._id = recipient.id
            self._recipient = recipient
        self._channel = channel
        self._genesis_message = None
        self._ready_event = asyncio.Event()
        self.wait_tasks = []
        self.close_task = None
        self.auto_close_task = None
        self._cancelled = False

    def __repr__(self):
        return f'Thread(recipient="{self.recipient or self.id}", channel={self.channel.id})'

    def __eq__(self, other):
        if isinstance(other, Thread):
            return self.id == other.id
        return super().__eq__(other)

    async def wait_until_ready(self) -> None:
        """Blocks execution until the thread is fully set up."""
        # timeout after 30 seconds
        task = self.bot.loop.create_task(asyncio.wait_for(self._ready_event.wait(), timeout=25))
        self.wait_tasks.append(task)
        try:
            await task
        except asyncio.TimeoutError:
            pass

        self.wait_tasks.remove(task)

    @property
    def id(self) -> int:
        return self._id

    @property
    def channel(self) -> typing.Union[discord.TextChannel, discord.DMChannel]:
        return self._channel

    @property
    def recipient(self) -> typing.Optional[typing.Union[discord.User, discord.Member]]:
        return self._recipient

    @property
    def ready(self) -> bool:
        return self._ready_event.is_set()

    @ready.setter
    def ready(self, flag: bool):
        if flag:
            self._ready_event.set()
            self.bot.dispatch("thread_create", self)
        else:
            self._ready_event.clear()

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @cancelled.setter
    def cancelled(self, flag: bool):
        self._cancelled = flag
        if flag:
            for i in self.wait_tasks:
                i.cancel()

    @classmethod
    async def from_channel(cls, manager: "ThreadManager", channel: discord.TextChannel) -> "Thread":
        # there is a chance it grabs from another recipient's main thread
        _, recipient_id = parse_channel_topic(channel.topic)

        if recipient_id in manager.cache:
            thread = manager.cache[recipient_id]
        else:
            recipient = manager.bot.get_user(recipient_id) or await manager.bot.fetch_user(recipient_id)

            thread = cls(manager, recipient or recipient_id, channel)

        return thread

    async def get_genesis_message(self) -> discord.Message:
        if self._genesis_message is None:
            async for m in self.channel.history(limit=5, oldest_first=True):
                if m.author == self.bot.user:
                    if m.embeds and m.embeds[0].fields and m.embeds[0].fields[0].name == "Roles":
                        self._genesis_message = m

        return self._genesis_message

    async def setup(self, *, creator=None, category=None, initial_message=None):
        """Create the thread channel and other io related initialisation tasks"""
        self.bot.dispatch("thread_initiate", self, creator, category, initial_message)
        recipient = self.recipient

        # in case it creates a channel outside of category
        overwrites = {self.bot.guild.default_role: discord.PermissionOverwrite(read_messages=False)}

        if category is None:
            # Get modmail category from database
            settings = await self.bot.db.settings.find_one({"_id": "modmail_settings"})
            if settings and "modmail_category_id" in settings:
                category = discord.utils.get(self.bot.guild.categories, id=settings["modmail_category_id"])
            else:
                self.bot.log.warning("No modmail category configured in database")

        if category is not None:
            overwrites = {}

        try:
            channel = await create_thread_channel(self.bot, recipient, category, overwrites)
        except discord.HTTPException as e:  # Failed to create due to missing perms.
            self.bot.log.error("An error occurred while creating a thread.")
            self.manager.cache.pop(self.id)

            embed = discord.Embed(color=self.bot.error_color)
            embed.title = "Fout bij het aanmaken van een ticket."
            embed.description = str(e)
            embed.add_field(name="Recipient", value=recipient.mention)

            if self.bot.log_channel is not None:
                await self.bot.log_channel.send(embed=embed)
            return

        self._channel = channel

        self.ready = True

        if creator is not None and creator != recipient:
            mention = None
        else:
            mention = "@here"

        async def send_genesis_message():
            info_embed = self._format_info_embed(recipient, discord.Color.blurple(),)
            try:
                msg = await channel.send(mention, embed=info_embed)
                self.bot.loop.create_task(msg.pin())
                self._genesis_message = msg
            except Exception:
                self.bot.log.error("Failed unexpectedly")

        async def send_recipient_genesis_message():
            # Once thread is ready, tell the recipient (don't send if using contact on others)
            thread_creation_response = "Het staff team zal zo snel mogelijk reageren."

            embed = discord.Embed(
                color=discord.Color.blurple(),
                description=thread_creation_response,
                timestamp=channel.created_at,
            )

            embed.set_footer(
                text="Je bericht is verzonden", icon_url=self.bot.get_guild_icon(guild=self.bot.guild, size=128)
            )
            embed.title = "Modmail Aangemaakt"

            if creator is None or creator == recipient:
                msg = await recipient.send(embed=embed)

        await asyncio.gather(
            send_genesis_message(),
            send_recipient_genesis_message(),
        )
        self.bot.dispatch("thread_ready", self, creator, category, initial_message)

    def _format_info_embed(self, user,color, log_url=None, log_count=None, ):
        """Get information about a member of a server
        supports users from the guild or not."""
        member = self.bot.guild.get_member(user.id)
        time = discord.utils.utcnow()

        role_names = ""
        if member is not None:
            sep_server = False
            separator = ", " if sep_server else " "

            roles = []

            for role in sorted(member.roles, key=lambda r: r.position):
                if role.is_default():
                    # @everyone
                    continue

                fmt = role.name if sep_server else role.mention
                roles.append(fmt)

                if len(separator.join(roles)) > 1024:
                    roles.append("...")
                    while len(separator.join(roles)) > 1024:
                        roles.pop(-2)
                    break

            role_names = separator.join(roles)

        user_info = []

        created = discord.utils.format_dt(user.created_at, "R")
        user_info.append(f" was created {created}")

        embed = discord.Embed(color=color, description=user.mention, timestamp=time)

        if user.dm_channel:
            footer = f"User ID: {user.id} • DM ID: {user.dm_channel.id}"
        else:
            footer = f"User ID: {user.id}"

        if member is not None:
            avatar_url = member.display_avatar.url if member.display_avatar else None
            embed.set_author(name=str(user), icon_url=avatar_url, url=log_url)

            joined = discord.utils.format_dt(member.joined_at, "R")
            user_info.append(f"joined {joined}")

            if member.nick:
                embed.add_field(name="Bijnaam", value=member.nick, inline=True)
            if role_names:
                embed.add_field(name="Rollen", value=role_names, inline=True)
            embed.set_footer(text=footer)
        else:
            avatar_url = user.display_avatar.url if user.display_avatar else None
            embed.set_author(name=str(user), icon_url=avatar_url, url=log_url)
            embed.set_footer(text=f"{footer} • (niet in hoofdserver)")

        embed.description += ", ".join(user_info)

        if log_count is not None:
            connector = "met" if user_info else "heeft"
            thread = "ticket" if log_count == 1 else "tickets"
            embed.description += f" {connector} **{log_count or 'geen'}** eerdere {thread}."
        else:
            embed.description += "."

        mutual_guilds = [g for g in self.bot.guilds if user in g.members]
        if member is None or len(mutual_guilds) > 1:
            embed.add_field(name="Gedeelde Server(s)", value=", ".join(g.name for g in mutual_guilds))

        return embed

    async def _close_after(self, after, closer, silent, delete_channel, message):
        await asyncio.sleep(after)
        return self.bot.loop.create_task(self._close(closer, silent, delete_channel, message, True))

    async def store_and_send_log(self,
                                 closer: typing.Union[discord.Member, discord.User],
                                 log_channel: discord.TextChannel):

        def format_discord_timestamp(text):
            """Convert Discord timestamps (<t:1234567890:R>) into human-readable format."""
            matches = re.findall(r"<t:(\d+):R>", text)
            for match in matches:
                timestamp = datetime.utcfromtimestamp(int(match)).strftime('%Y-%m-%d %H:%M:%S')
                text = text.replace(f"<t:{match}:R>", f"<span class='timestamp'>{timestamp}</span>")
            return text

        def replace_mentions(text, guild):
            """ Replaces user, role, and channel mentions with readable names. """
            if not text:
                return ""

            # Replace role mentions
            if "<@&" in text:  # Only process if a role mention exists
                role_mention_pattern = re.compile(r"<@&(\d+)>")
                text = role_mention_pattern.sub(
                    lambda m: f"@{guild.get_role(int(m.group(1))).name if guild.get_role(int(m.group(1))) else 'Unknown Role'}",
                    text
                )

            # Replace channel mentions
            if "<#" in text:  # Only process if a channel mention exists
                channel_mention_pattern = re.compile(r"<#(\d+)>")
                text = channel_mention_pattern.sub(
                    lambda m: f"#{guild.get_channel(int(m.group(1))).name if guild.get_channel(int(m.group(1))) else 'Unknown Channel'}",
                    text
                )

            # Replace user mentions
            if "<@" in text:  # Only process if a user mention exists
                user_mention_pattern = re.compile(r"<@(\d+)>")
                text = user_mention_pattern.sub(
                    lambda m: f"@{guild.get_member(int(m.group(1))).display_name if guild.get_member(int(m.group(1))) else 'Unknown User'}",
                    text
                )

            return text

        # Determine NSFW status
        nsfw = "NSFW-" if self.channel.nsfw else ""

        channel = self.channel
        messages = []

        async for msg in channel.history(limit=None, oldest_first=True):
            timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
            author_name = msg.author.display_name
            content = msg.content or ""

            # Replace mentions with actual names
            for mention in msg.mentions:
                content = content.replace(f"<@{mention.id}>", f"<span class='mention'>@{mention.display_name}</span>")
            for role in msg.role_mentions:
                content = content.replace(f"<@&{role.id}>", f"<span class='role'>@{role.name}</span>")
            for channel_mention in msg.channel_mentions:
                content = content.replace(f"<#{channel_mention.id}>", f"<span class='channel'>#{channel_mention.name}</span>")

            # Convert timestamps
            content = format_discord_timestamp(content)

            message_html = (
                f"<div class='message'>"
                f"<span class='author'>{author_name}</span> <span class='timestamp'>{timestamp}</span><br>"
                f"<p class='content'>{content}</p>"
            )

            # Process embeds
            if msg.embeds:
                for embed in msg.embeds:
                    embed_content = f"<div class='embed' style='border-left: 5px solid {embed.color}; padding: 10px;'>"

                    if embed.author:
                        embed_content += f"<div class='embed-author'><img src='{embed.author.icon_url}' class='embed-author-icon'> {embed.author.name}</div>"

                    if embed.title:
                        embed_content += f"<h3>{replace_mentions(embed.title, msg.guild)}</h3>"

                    if embed.description:
                        desc = embed.description

                        desc = replace_mentions(desc, msg.guild)
                        desc = format_discord_timestamp(desc)

                        embed_content += f"<p>{desc}</p>"

                    if embed.fields:
                        for field in embed.fields:
                            embed_content += f"<p><strong>{replace_mentions(field.name, msg.guild)}:</strong> {replace_mentions(field.value, msg.guild)}</p>"

                    if embed.thumbnail:
                        embed_content += f'<img src="{embed.thumbnail.url}" class="embed-thumbnail">'

                    if embed.image:
                        embed_content += f'<img src="{embed.image.url}" class="embed-image">'

                    if embed.footer:
                        embed_content += f"<p class='footer'>"
                        timestamp_str = embed.timestamp.strftime('%Y-%m-%d %H:%M') if embed.timestamp else ""
                        if embed.footer.text:
                            embed_content += f"{embed.footer.text} "
                        embed_content += f"{timestamp_str}</p>"

                    embed_content += "</div>"
                    message_html += embed_content

            message_html += "</div>"
            messages.append(message_html)

            # Create the HTML log
        log_html = f"""<html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #36393F; color: #DCDDDE; padding: 20px; }}
            .container {{ max-width: 800px; margin: auto; background: #2F3136; padding: 20px; border-radius: 5px; }}
            .user-info {{ padding: 10px; background: #23272A; border-radius: 5px; margin-bottom: 10px; }}
            .message {{ padding: 10px; margin: 5px 0; border-radius: 5px; background: #40444B; }}
            .author {{ font-weight: bold; color: #FFFFFF; }}
            .timestamp {{ font-size: 0.8em; color: #B9BBBE; }}
            .mention {{ color: #7289DA; font-weight: bold; }}
            .role {{ color: #FAA61A; font-weight: bold; }}
            .channel {{ color: #43B581; font-weight: bold; }}
            .embed {{ background: #202225; padding: 10px; margin-top: 10px; border-radius: 5px; }}
            .embed-author {{ font-weight: bold; margin-bottom: 5px; }}
            .embed-author-icon {{ width: 20px; height: 20px; vertical-align: middle; margin-right: 5px; }}
            .embed-thumbnail {{ max-width: 100px; float: right; }}
            .embed-image {{ max-width: 100%; margin-top: 5px; }}
            .footer {{ font-size: 0.9em; color: #B9BBBE; }}
        </style>
    </head>
    <body>
        <div class='container'>
            <h2>Modmail Log - {channel.name}</h2>
                {' '.join(messages)}
        </div>
    </body>
</html>"""

        # Create an HTML file
        file = discord.File(io.BytesIO(log_html.encode()), filename=f"modmail_{channel.id}.html")

        # Send to log channel
        if log_channel:
            try:
                await log_channel.send(f"{nsfw}Transcript for {channel.name} (closed by {closer.mention}):", file=file)
            except discord.NotFound:
                self.bot.log.error(f"Modmail log channel {log_channel.id} not found when trying to send transcript for ticket {channel.id}")
                raise Exception(f"Het geconfigureerde modmail log kanaal (ID: {log_channel.id}) bestaat niet meer.")
            except discord.Forbidden:
                self.bot.log.error(f"No permission to send to modmail log channel {log_channel.id} when trying to send transcript for ticket {channel.id}")
                raise Exception(f"Geen toestemming om berichten te sturen naar het modmail log kanaal (ID: {log_channel.id}).")
            except discord.HTTPException as e:
                self.bot.log.error(f"HTTP error when sending transcript to modmail log channel {log_channel.id} for ticket {channel.id}: {e}")
                raise Exception(f"Discord API fout bij versturen transcript naar log kanaal: {str(e)}")
            except Exception as e:
                self.bot.log.error(f"Unexpected error when sending transcript to modmail log channel {log_channel.id} for ticket {channel.id}: {e}", exc_info=True)
                raise Exception(f"Onverwachte fout bij versturen transcript naar log kanaal: {str(e)}")

        # Store in MongoDB
        _, recipient_id = parse_channel_topic(channel.topic)
        log_entry = {
            "recipient_id": recipient_id,
            "ticket_id": channel.id,
            "closed_by": closer.id,
            "timestamp": datetime.now(LOCAL_TIMEZONE),
            "log_html": log_html
        }
        await self.bot.db.modmail_logs.insert_one(log_entry)


    async def close(
        self,
        *,
        closer: typing.Union[discord.Member, discord.User],
        silent: bool = False,
        message: str = None,
        log_channel: typing.Optional[discord.TextChannel] = None,
    ) -> None:
        """Close a thread now or after a set time in seconds"""
        try:
            self.manager.cache.pop(self.id)
        except KeyError as e:
            self.bot.log.error("Thread already closed: %s",e)
            return

        #Logging
        await self.store_and_send_log(closer, log_channel)

        #No notification to user
        if not silent:
            embed = discord.Embed(
                title="Modmail Gesloten",
                color=discord.Color.red(),
            )
            embed.timestamp = discord.utils.utcnow()
            if not message:
                message = "Staff heeft deze Modmail chat gesloten"
            embed.description = message
            embed.set_footer(text="Reageren zal een nieuwe modmail chat aanmaken", icon_url=self.bot.get_guild_icon(guild=self.bot.guild, size=128))

            try:
                # Create DM channel if it doesn't exist, then send
                if self.recipient.dm_channel is None:
                    await self.recipient.create_dm()
                await self.recipient.dm_channel.send(embed=embed)
            except Exception as e:
                self.bot.log.warning(f"Could not send close notification to user {self.recipient.id}: {e}")

        await self.channel.delete()
        self.bot.dispatch("thread_close", self, closer, silent, message)

    async def cancel_closure(self, auto_close: bool = False, all: bool = False) -> None:
        if self.close_task is not None and (not auto_close or all):
            self.close_task.cancel()
            self.close_task = None
        if self.auto_close_task is not None and (auto_close or all):
            self.auto_close_task.cancel()
            self.auto_close_task = None

    async def _restart_close_timer(self):
        """
        This will create or restart a timer to automatically close this
        thread.
        """
        timeout = isodate.Duration()

        # Exit if timeout was not set
        if timeout == isodate.Duration():
            return

        # Set timeout seconds
        seconds = timeout.total_seconds()
        # seconds = 20  # Uncomment to debug with just 20 seconds
        reset_time = discord.utils.utcnow() + timedelta(seconds=seconds)
        human_time = discord.utils.format_dt(reset_time)

        # Grab message
        close_message = self.bot.formatter.format(
            "This thread has been closed automatically due to inactivity after {timeout}.", timeout=human_time
        )

        time_marker_regex = "%t"
        if len(re.findall(time_marker_regex, close_message)) == 1:
            close_message = re.sub(time_marker_regex, str(human_time), close_message)
        elif len(re.findall(time_marker_regex, close_message)) > 1:\
            self.bot.log.warning("The thread_auto_close_response should only contain one '%s' to specify time.", time_marker_regex)

        await self.close(closer=self.bot.user, after=int(seconds), message=close_message, auto_close=True)

    async def find_linked_messages(
        self,
        message_id: typing.Optional[int] = None,
        message1: discord.Message = None,
        note: bool = True,
    ) -> typing.Tuple[discord.Message, typing.List[typing.Optional[discord.Message]]]:
        if message1 is not None:
            if not message1.embeds or not message1.embeds[0].author.url or message1.author != self.bot.user:
                self.bot.log.warning("1")
                raise ValueError("Malformed thread message. 1")

        elif message_id is not None:
            try:
                message1 = await self.channel.fetch_message(message_id)
            except discord.NotFound:
                self.bot.log.warning("2")
                raise ValueError("Thread message not found. 1")

            if not (
                message1.embeds
                # and message1.embeds[0].color
                and message1.author == self.bot.user
            ):
                self.bot.log.warning("3")
                raise ValueError("Thread message not found. 2")

            if message1.embeds[0].color and (
                message1.embeds[0].author.name.startswith("Note")
                or message1.embeds[0].author.name.startswith("Persistent Note")
            ):
                if not note:
                    self.bot.log.warning("4")
                    raise ValueError("Thread message not found. 3")
                return message1, None
        else:
            async for message1 in self.channel.history():
                if (
                    message1.embeds
                    and message1.embeds[0].color
                    and message1.author == self.bot.user
                ):
                    break
            else:
                self.bot.log.warning("6")
                raise ValueError("Thread message not found. 5")

        try:
            sender = message1.embeds[0].author
            desc = message1.embeds[0].description
            time = message1.embeds[0].timestamp
        except ValueError:
            raise ValueError("Malformed thread message.")

        messages = [message1]
        async for msg in self.recipient.history():
            if not (msg.embeds and msg.embeds[0].author):
                continue
            try:
                if msg.embeds[0].author == sender and msg.embeds[0].description == desc and msg.embeds[0].timestamp == time :
                    messages.append(msg)
                    break
            except ValueError:
                continue

        if len(messages) > 1:
            return messages

        raise ValueError("DM message not found.")

    async def edit_message(self, message_id: typing.Optional[int], message: str) -> None:
        try:
            message1, *message2 = await self.find_linked_messages(message_id)
        except ValueError:
            self.bot.log.warning("Failed to edit message.")
            raise

        embed1 = message1.embeds[0]
        embed1.description = message

        tasks = [message1.edit(embed=embed1)]

        for m2 in message2:
            if m2 is not None:
                embed2 = m2.embeds[0]
                embed2.description = message
                tasks += [m2.edit(embed=embed2)]

        await asyncio.gather(*tasks)

    async def delete_message(
        self, message = None, note: bool = True
    ) -> None:

        message1, *message2 = await self.find_linked_messages(message_id=message, note=note)
        tasks = []

        if not isinstance(message, discord.Message):
            tasks += [message1.delete()]

        for m2 in message2:
            if m2 is not None:
                tasks += [m2.delete()]

        if tasks:
            await asyncio.gather(*tasks)

    async def find_linked_message_from_dm(
        self, message: discord.Message, either_direction=False, get_thread_channel=False
    ) -> typing.List[discord.Message]:
        try:
            sender = message.author
            desc = message.content
        except ValueError:
            raise ValueError("Malformed thread message.")

        linked_messages = []
        if self.channel is not None:
            async for msg in self.channel.history():
                if not msg.embeds:
                    continue
                try:
                    if msg.channel.name == sender.name and msg.embeds[0].description == desc:
                        linked_messages.append(msg)
                        break
                except ValueError:
                    continue
            else:
                raise ValueError("Thread channel message not found.")
        else:
            raise ValueError("Thread channel message not found.")

        if get_thread_channel:
            # end early as we only want the main message from thread channel
            return linked_messages

        return linked_messages

    async def edit_dm_message(self, message: discord.Message, content: str) -> None:
        try:
            linked_messages = await self.find_linked_message_from_dm(message)
        except ValueError:
            self.bot.log.warning("Failed to edit message.")
            raise

        for msg in linked_messages:
            embed = msg.embeds[0]
            if isinstance(msg.channel, discord.TextChannel):
                # just for thread channel, we put the old message in embed field
                embed.add_field(name="**Bewerkt, vorig bericht:**", value=embed.description)
            embed.description = content
            await asyncio.gather(msg.edit(embed=embed))

    async def note(
        self, message: discord.Message, persistent=False, thread_creation=False
    ) -> discord.Message:
        if not message.content and not message.attachments and not message.stickers:
            raise MissingRequiredArgument(DummyParam("msg"))

        msg = await self.send(
            message,
            self.channel,
            note=True,
            persistent_note=persistent,
            thread_creation=thread_creation,
        )

        return msg

    async def reply(
        self, message: discord.Message, anonymous: bool = False, plain: bool = False
    ) -> typing.Tuple[typing.List[discord.Message], discord.Message]:
        """Returns List[user_dm_msg] and thread_channel_msg"""
        if not message.content and not message.attachments and not message.stickers:
            raise MissingRequiredArgument(DummyParam("msg"))

        if not any(g.get_member(self.id) for g in self.bot.guilds):
            return await message.channel.send(
                embed=discord.Embed(
                    color=discord.Color.red(),
                    description="Je bericht kon niet worden bezorgd omdat "
                    "de ontvanger geen servers deelt met de bot.",
                )
            )

        user_msg_tasks = []
        tasks = []

        user_msg_tasks.append(
            self.send(
                message,
                destination=self.recipient,
                from_mod=True,
                anonymous=anonymous,
                plain=plain,
        ))

        try:
            user_msg = await asyncio.gather(*user_msg_tasks)
        except Exception as e:
            self.bot.log.error(f"Message delivery failed: {e}")
            user_msg = None
            if isinstance(e, discord.Forbidden):
                description = (
                    "Je bericht kon niet worden bezorgd omdat "
                    "de ontvanger alleen directe berichten "
                    "van vrienden accepteert, of de bot werd "
                    "geblokkeerd door de ontvanger."
                )
            else:
                description = (
                    "Je bericht kon niet worden bezorgd door "
                    "een onbekende fout."
                )
            msg = await message.channel.send(
                embed=discord.Embed(
                    color=discord.Color.red(),
                    description=description,
                )
            )
        else:
            # Send the same thing in the thread channel.
            msg = await self.send(
                message, destination=self.channel, from_mod=True, anonymous=anonymous, plain=plain
            )

        await asyncio.gather(*tasks)
        self.bot.dispatch("thread_reply", self, True, message, anonymous, plain)
        return (user_msg, msg)  # sent_to_user, sent_to_thread_channel

    async def send(
        self,
        message: discord.Message,
        destination: typing.Union[
            discord.TextChannel, discord.DMChannel, discord.User, discord.Member
        ] = None,
        from_mod: bool = False,
        note: bool = False,
        anonymous: bool = False,
        plain: bool = False,
        persistent_note: bool = False,
        thread_creation: bool = False,
    ) -> None:
        if not self.ready:
            await self.wait_until_ready()

        destination = destination or self.channel

        author = message.author
        if anonymous:
            avatar_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        else:
            avatar_url = author.display_avatar.url if author.display_avatar else None

        embed = discord.Embed(description=message.content)
        embed.timestamp = message.created_at

        if not note:
            if anonymous and from_mod:
                # Anonymously sending to the user.
                embed.set_author(
                    name="Staff Team",
                    icon_url=avatar_url,
                )
            else:
                # Normal message
                embed.set_author(
                    name=str(author),
                    icon_url=avatar_url,
                )
        else:
            #Notes
            bot_avatar_url = self.bot.user.avatar.url if self.bot.user.avatar else None
            embed.set_author(
                name=f"{'Permanente' if persistent_note else ''} Notitie door {author.name}",
                icon_url=bot_avatar_url
            )

        ext = [(a.url, a.filename, False) for a in message.attachments]

        images = []
        attachments = []
        for attachment in ext:
            if is_image_url(attachment[0]):
                images.append(attachment)
            else:
                attachments.append(attachment)

        image_urls = re.findall(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|%[0-9a-fA-F][0-9a-fA-F])+",
            message.content,
        )

        image_urls = [
            (is_image_url(url, convert_size=False), None, False)
            for url in image_urls
            if is_image_url(url, convert_size=False)
        ]
        images.extend(image_urls)

        def lottie_to_png(data):
            importer = l_importers.get("lottie")
            exporter = l_exporters.get("png")
            with io.BytesIO() as stream:
                stream.write(data)
                stream.seek(0)
                an = importer.process(stream)

            with io.BytesIO() as stream:
                exporter.process(an, stream)
                stream.seek(0)
                return stream.read()

        for i in message.stickers:
            if i.format in (
                discord.StickerFormatType.png,
                discord.StickerFormatType.apng,
                discord.StickerFormatType.gif,
            ):
                images.append(
                    (f"https://media.discordapp.net/stickers/{i.id}.{i.format.file_extension}", i.name, True)
                )
            elif i.format == discord.StickerFormatType.lottie:
                # save the json lottie representation
                try:
                    async with self.bot.session.get(i.url) as resp:
                        data = await resp.read()

                    # convert to a png
                    img_data = await self.bot.loop.run_in_executor(
                        None, functools.partial(lottie_to_png, data)
                    )
                    b64_data = base64.b64encode(img_data).decode()

                    # upload to imgur
                    async with self.bot.session.post(
                        "https://api.imgur.com/3/image",
                        headers={"Authorization": "Client-ID 50e96145ac5e085"},
                        data={"image": b64_data},
                    ) as resp:
                        result = await resp.json()
                        url = result["data"]["link"]

                except Exception:
                    traceback.print_exc()
                    images.append((None, i.name, True))
                else:
                    images.append((url, i.name, True))
            else:
                images.append((None, i.name, True))

        embedded_image = False

        prioritize_uploads = any(i[1] is not None for i in images)

        additional_images = []
        additional_count = 1

        for url, filename, is_sticker in images:
            if (
                not prioritize_uploads or ((url is None or is_image_url(url)) and filename)
            ) and not embedded_image:
                if url is not None:
                    embed.set_image(url=url)
                if filename:
                    if is_sticker:
                        if url is None:
                            description = f"{filename}: Unable to retrieve sticker image"
                        else:
                            description = f"[{filename}]({url})"
                        embed.add_field(name="Sticker", value=description)
                    else:
                        embed.add_field(name="Afbeelding", value=f"[{filename}]({url})")
                embedded_image = True
            else:
                if note:
                    color = discord.Color.blurple()
                elif from_mod:
                    color = discord.Color.yellow()
                else:
                    color = discord.Color.green()

                img_embed = discord.Embed(color=color)

                if url is not None:
                    img_embed.set_image(url=url)
                    img_embed.url = url
                if filename is not None:
                    img_embed.title = filename
                img_embed.set_footer(text=f"Extra Afbeelding Upload ({additional_count})")
                img_embed.timestamp = message.created_at
                additional_images.append(destination.send(embed=img_embed))
                additional_count += 1

        file_upload_count = 1

        for url, filename, _ in attachments:
            embed.add_field(name=f"Bestand upload ({file_upload_count})", value=f"[{filename}]({url})")
            file_upload_count += 1

        if from_mod:
            embed.colour = discord.Color.yellow()
            if anonymous and isinstance(destination, discord.TextChannel):
                footer = f"Anonieme Reactie: {message.author}"
                embed.set_footer(text=footer)
            else:
                embed.set_footer(text="Reactie")
            embed.colour = discord.Color.blurple()
        else:
            embed.colour = discord.Colour.green()

        if (from_mod or note) and not thread_creation:
            delete_message = not bool(message.attachments)
            if delete_message and destination == self.channel:
                try:
                    await message.delete()
                except Exception as e:
                    self.bot.log.warning("Cannot delete message: %s.", e)

        try:
            await destination.typing()
        except discord.NotFound:
            self.bot.log.warning("Channel not found.")
            raise

        if plain:
            if from_mod and not isinstance(destination, discord.TextChannel):
                # Plain to user
                with warnings.catch_warnings():
                    # Catch coroutines not awaited warning
                    warnings.simplefilter("ignore")
                    additional_images = []

                if embed.footer.text:
                    plain_message = f"**{embed.footer.text} "
                else:
                    plain_message = "**"
                plain_message += f"{embed.author.name}:** {embed.description}"
                files = []
                for i in message.attachments:
                    files.append(await i.to_file())

                msg = await destination.send(plain_message, files=files)
            else:
                # Plain to mods
                embed.set_footer(text="[PLAIN] " + embed.footer.text)
                msg = await destination.send(embed=embed)

        else:
            msg = await destination.send(embed=embed)

        if additional_images:
            self.ready = False
            await asyncio.gather(*additional_images)
            self.ready = True

        return msg

    async def set_title(self, title: str) -> None:
        topic = f"Title: {title}\n"

        user_id = match_user_id(self.channel.topic)
        topic += f"User ID: {user_id}"

        await self.channel.edit(topic=topic)

    async def _update_users_genesis(self):
        genesis_message = await self.get_genesis_message()
        embed = genesis_message.embeds[0]
        value = " ".join(x.mention for x in self._other_recipients)
        index = None
        for n, field in enumerate(embed.fields):
            if field.name == "Andere Ontvangers":
                index = n
                break

        if index is None and value:
            embed.add_field(name="Andere Ontvangers", value=value, inline=False)
        else:
            if value:
                embed.set_field_at(index, name="Andere Ontvangers", value=value, inline=False)
            else:
                embed.remove_field(index)

        await genesis_message.edit(embed=embed)


class ThreadManager:
    """Class that handles storing, finding and creating Modmail threads."""

    def __init__(self, bot):
        self.bot = bot
        self.cache = {}

    async def populate_cache(self) -> None:
        for channel in self.bot.guild.text_channels:
            await self.find(channel=channel)

    def __len__(self):
        return len(self.cache)

    def __iter__(self):
        return iter(self.cache.values())

    def __getitem__(self, item: str) -> Thread:
        return self.cache[item]

    async def find(
        self,
        *,
        recipient: typing.Union[discord.Member, discord.User] = None,
        channel: discord.TextChannel = None,
        recipient_id: int = None,
    ) -> typing.Optional[Thread]:
        """Finds a thread from cache or from discord channel topics."""
        if recipient is None and channel is not None and isinstance(channel, discord.TextChannel):
            thread = await self._find_from_channel(channel)
            if thread is None:
                user_id, thread = next(
                    ((k, v) for k, v in self.cache.items() if v.channel == channel), (-1, None)
                )
                if thread is not None:
                    self.bot.log.debug("Found thread with tempered ID.")
                    await channel.edit(topic=f"User ID: {user_id}")
            return thread


        if recipient:
            recipient_id = recipient.id

        thread = self.cache.get(recipient_id)
        if thread is not None:
            try:
                await thread.wait_until_ready()
            except asyncio.CancelledError:
                self.bot.log.warning("Thread for %s cancelled.", recipient)
                return thread
            else:
                if not thread.cancelled and (
                    not thread.channel or not self.bot.get_channel(thread.channel.id)
                ):
                    self.bot.log.warning("Found existing thread for %s but the channel is invalid.", recipient_id)
                    # Just remove from cache and set cancelled, don't try to close invalid channel
                    thread.cancelled = True
                    try:
                        self.cache.pop(thread.id, None)
                    except KeyError:
                        pass
                    thread = None
        else:

            def check(topic):
                _, user_id = parse_channel_topic(topic)
                return recipient_id == user_id

            channel = next(
                (x for x in self.bot.guild.text_channels if x.topic and check(x.topic)),
                None
            )

            if channel:
                thread = await Thread.from_channel(self, channel)
                if thread.recipient:
                    # only save if data is valid.
                    # also the recipient_id here could belong to other recipient,
                    # it would be wrong if we set it as the dict key,
                    # so we use the thread id instead
                    self.cache[thread.id] = thread
                thread.ready = True

        if thread and recipient_id != recipient.id:
            self.cache.pop(recipient_id)
            thread = None

        return thread

    async def _find_from_channel(self, channel):
        """
        Tries to find a thread from a channel channel topic,
        if channel topic doesnt exist for some reason, falls back to
        searching channel history for genesis embed and
        extracts user_id from that.
        """
        if not channel.topic:
            return None

        _, user_id = parse_channel_topic(channel.topic)

        if user_id == -1:
            return None

        if user_id in self.cache:
            return self.cache[user_id]

        try:
            recipient = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
        except discord.NotFound:
            recipient = None

        if recipient is None:
            thread = Thread(self, user_id, channel)
        else:
            self.cache[user_id] = thread = Thread(self, recipient, channel)
        thread.ready = True

        return thread

    async def create(
        self,
        recipient: typing.Union[discord.Member, discord.User],
        *,
        message: discord.Message = None,
        creator: typing.Union[discord.Member, discord.User] = None,
        category: discord.CategoryChannel = None,
        manual_trigger: bool = True,
    ) -> Thread:
        """Creates a Modmail thread"""
        # checks for existing thread in cache
        thread = self.cache.get(recipient.id)
        if thread:
            try:
                await thread.wait_until_ready()
            except asyncio.CancelledError:
                self.bot.log.warning("Thread for %s cancelled, abort creating.", recipient)
                return thread
            else:
                if thread.channel and self.bot.get_channel(thread.channel.id):
                    self.bot.log.warning("Found an existing thread for %s, abort creating.", recipient)
                    return thread
                self.bot.log.warning("Found an existing thread for %s, closing previous thread.", recipient)
                self.bot.loop.create_task(
                    thread.close(closer=self.bot.user, silent=True, delete_channel=False)
                )

        thread = Thread(self, recipient)

        self.cache[recipient.id] = thread

        if message or not manual_trigger:
            if not manual_trigger:
                destination = recipient
            else:
                destination = message.channel
            view = ConfirmThreadCreationView()
            view.add_item(AcceptButton("\u2705"))
            view.add_item(DenyButton("\uD83D\uDEAB"))
            confirm = await destination.send(
                embed=discord.Embed(
                    title="Bevestig modmail aanmaak",
                    description="Klik op de knop om modmail aanmaak te bevestigen wat direct contact opneemt met onze Staff.",
                    color=discord.Color.blurple(),
                ),
                view=view,
            )
            await view.wait()
            if view.value is None:
                thread.cancelled = True
                self.bot.loop.create_task(
                    destination.send(
                        embed=discord.Embed(
                            title="Geannuleerd",
                            description="Time-out",
                            color=discord.Color.red(),
                        )
                    )
                )
                await confirm.edit(view=None)
            if view.value is False:
                thread.cancelled = True
                self.bot.loop.create_task(
                    destination.send(
                        embed=discord.Embed(
                            title="Geannuleerd", color=discord.Color.red()
                        )
                    )
                )
            if thread.cancelled:
                del self.cache[recipient.id]
                return thread

        self.bot.loop.create_task(thread.setup(creator=creator, category=category, initial_message=message))
        return thread

    async def find_or_create(self, recipient) -> Thread:
        return await self.find(recipient=recipient) or await self.create(recipient)
