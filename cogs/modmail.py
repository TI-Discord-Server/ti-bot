import asyncio
from typing import Optional, Literal
import io

from discord.ext import commands
from discord.app_commands import (
    command,
)

from utils.thread import ThreadManager
from utils.utils import *
from utils.has_admin import has_admin
from utils import checks


class Modmail(commands.Cog, name="modmail"):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.settings_id = "modmail_settings"
        self.modmail_category_id = 1344777249991426078
        self.modmail_logs_channel_id = 1342592695540912199

    async def get_modmail_category_id(self):
        settings = await self.db.settings.find_one({"_id": self.settings_id})
        if settings and "modmail_category_id" in settings:
            return settings["modmail_category_id"]
        return self.modmail_category_id

    async def get_modmail_logs_channel_id(self):
        settings = await self.db.settings.find_one({"_id": self.settings_id})
        if settings and "modmail_channel_id" in settings:
            return settings["modmail_channel_id"]
        return self.modmail_logs_channel_id

    @command(
        name="set_modmail_settings",
        description="Set modmail category and / or logs channel",
    )
    @has_admin()
    async def set_modmail_settings(
            self, interaction: discord.Interaction, category: discord.CategoryChannel = None, channel: discord.TextChannel = None
    ):
        if category is not None:
            await self.db.settings.update_one(
                {"_id": self.settings_id},
                {"$set": {"modmail_category_id": category.id}},
                upsert=True,
            )
            await interaction.response.send_message(
                f"Modmail categorie is ingesteld op {category.mention}."
            )
        if channel is not None:
            await self.db.settings.update_one(
                {"_id": self.settings_id},
                {"$set": {"modmail_channel_id": channel.id}},
                upsert=True,
            )
            await interaction.response.send_message(
                f"Modmail-logs kanaal is ingesteld op {channel.mention}."
            )

    @set_modmail_settings.error
    async def set_modmail_settings_error(
        self, interaction: discord.Interaction, error
    ):
        if isinstance(error, commands.CheckFailure):
            await interaction.response.send_message(
                "Je hebt geen toestemming om dit commando te gebruiken.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Er is een fout opgetreden: {str(error)}", ephemeral=True
            )

    # @commands.command(usage="[after] [close message]")
    @command(name="close", description="Close the thread")
    @has_admin()
    @checks.thread_only()
    async def close(
            self,
            interaction: discord.Interaction,
            option: Optional[Literal["silent"]] = "",
            reason: str = None
    ):
        """
        Close the current thread.
        """
        thread = await ThreadManager.find(self.bot.threads, channel=interaction.channel)
        modmail_logs_channel = await self.bot.fetch_channel(await self.get_modmail_logs_channel_id())

        silent = any(x == option for x in {"silent"})

        await thread.close(closer=interaction.user, message=reason, silent=silent, log_channel=modmail_logs_channel)

    @command(name="generate_transcript", description="Makes a transcript and sends it in log_channel")
    @has_admin()
    @checks.thread_only()
    async def generate_transcript(
            self,
            interaction: discord.Interaction,
    ):
        await interaction.response.defer(thinking=False)

        thread = await ThreadManager.find(self.bot.threads, channel=interaction.channel)
        await thread.store_and_send_log(closer=interaction.user, log_channel=interaction.channel)

        confirmation = await interaction.followup.send("📝 Transcript gegenereerd", ephemeral=True)
        await asyncio.sleep(2)
        await confirmation.delete()

    @command(name="transcripts", description="Gives transcripts with certain person")
    @has_admin()
    @checks.thread_only()
    async def transcripts(
            self,
            interaction: discord.Interaction,
            recipient_id: str,
    ):
        await interaction.response.defer()  # Acknowledge command (avoids timeout)
        recipient_id = int(recipient_id)

        # Fetch files from MongoDB
        cursor = self.db.logs.find({"recipient_id": recipient_id})
        files_list = await cursor.to_list(length=None)  # Convert cursor to a list

        if not files_list:
            await interaction.followup.send(f"Geen transcripts gevonden voor ontvanger {recipient_id}.")
            return

        amount = len(files_list)
        file_batches = []
        current_batch = []

        counter = 0
        for file in files_list:
            counter += 1

            content = file.get('log_html', 'No content available')
            file_id = file['ticket_id']
            timestamp = file['timestamp']

            # Create a virtual file using io.BytesIO
            file_data = io.BytesIO(content.encode('utf-8'))
            file_data.seek(0)  # Reset pointer to start
            discord_file = discord.File(file_data, filename=f"{counter}_transcript_{file_id}_{timestamp.strftime('%Y-%m-%d_%H:%M')}.html")

            current_batch.append(discord_file)

            # Send in batches of 10 files
            if len(current_batch) == 10:
                file_batches.append(current_batch)
                current_batch = []

        if current_batch:
            file_batches.append(current_batch)  # Append any remaining files

        # Send each batch separately
        for batch in file_batches:
            await interaction.followup.send(f"{amount} transcripts gevonden voor ontvanger {recipient_id}:", files=batch)

    @staticmethod
    def parse_user_or_role(ctx, user_or_role):
        mention = None
        if user_or_role is None:
            mention = ctx.author.mention
        elif hasattr(user_or_role, "mention"):
            mention = user_or_role.mention
        elif user_or_role in {"here", "everyone", "@here", "@everyone"}:
            mention = "@" + user_or_role.lstrip("@")
        return mention

    @command(name="nsfw", description="Changes Modmail-thread to NSFW status")
    @has_admin()
    @checks.thread_only()
    async def nsfw(self, interaction: discord.Interaction):
        """Flags a Modmail thread as NSFW (not safe for work)."""
        await interaction.channel.edit(nsfw=True)
        await interaction.response.send_message("🔞 Kanaal ingesteld op NSFW")

    @command(name="sfw", description="Changes Modmail-thread to SFW status")
    @has_admin()
    @checks.thread_only()
    async def sfw(self, interaction: discord.Interaction):
        """Flags a Modmail thread as SFW (safe for work)."""
        await interaction.channel.edit(nsfw=False)
        await interaction.response.send_message("⚠️ Kanaal ingesteld op SFW")

    @command(name="reply", description="Replies to a Modmail-message")
    @has_admin()
    @checks.thread_only()
    async def reply(self, interaction: discord.Interaction, msg: str):
        """
        Reply to a Modmail thread.
        Supports attachments and images as well as
        automatically embedding image URLs.
        """
        await interaction.response.defer(thinking=False)

        thread = await ThreadManager.find(self.bot.threads, channel=interaction.channel)
        sent_message = await interaction.channel.send(msg)
        sent_message.author = interaction.user

        async with interaction.channel.typing():
            await thread.reply(sent_message)

        confirmation = await interaction.followup.send("📤 Bericht verzonden!", ephemeral=True)
        await asyncio.sleep(3)
        await confirmation.delete()

    @command(name="areply", description="Replies anonymous to a Modmail-message")
    @has_admin()
    @checks.thread_only()
    async def areply(self, interaction: discord.Interaction, msg: str):
        """
        Reply to a thread anonymously.
        """
        await interaction.response.defer(thinking=False)

        thread = await ThreadManager.find(self.bot.threads, channel=interaction.channel)
        sent_message = await interaction.channel.send(msg)
        sent_message.author = interaction.user

        async with interaction.channel.typing():
            await thread.reply(sent_message, anonymous=True)

        confirmation = await interaction.followup.send("📤 Bericht verzonden!", ephemeral=True)
        await asyncio.sleep(3)
        await confirmation.delete()

    # @commands.group(invoke_without_command=True)
    @command(name="note", description="Clarification of modmail")
    @has_admin()
    @checks.thread_only()
    async def note(self, interaction: discord.Interaction, msg: str):
        """
        Take a note about the current thread.
        Useful for noting context.
        """
        await interaction.response.defer(thinking=False)

        thread = await ThreadManager.find(self.bot.threads, channel=interaction.channel)
        sent_message = await interaction.channel.send(msg)
        sent_message.author = interaction.user

        async with interaction.channel.typing():
            msg = await thread.note(sent_message)
            await msg.pin()

        confirmation = await interaction.followup.send("📝 Genoteerd", ephemeral=True)
        await asyncio.sleep(3)
        await confirmation.delete()

    @command(name="edit", description="Edits a Modmail-message")
    @has_admin()
    @checks.thread_only()
    async def edit(self, interaction: discord.Interaction, message: str, message_id: Optional[str] = "" ):
        """
        Edit a message that was sent using the reply or anonreply command.

        If no `message_id` is provided,
        the last message sent by a staff will be edited.

        Note: attachments **cannot** be edited.
        """
        thread = await ThreadManager.find(self.bot.threads, channel=interaction.channel)

        message_id = int(message_id) if message_id.isdigit() and 17 <= len(message_id) <= 19 else None


        try:
            await thread.edit_message(message_id, message)
        except ValueError:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="Failed",
                    description="Cannot find a message to edit. Plain messages are not supported.",
                    color=discord.Color.red(),
                )
            )

        await interaction.response.send_message("📝 Bericht succesvol bewerkt")
        # await asyncio.sleep(5)
        # await interaction.delete_original_response()

    # @commands.command(usage="<user> [category] [options]")
    @command(name="contact", description="Opens a modmail ticket")
    @has_admin()
    async def contact(
            self,
            interaction: discord.Interaction,
            user: discord.Member | discord.User
    ):
        """
        Create a thread with a specified member.
        """
        manual_trigger = True
        category = discord.utils.get(self.bot.guild.categories, id=await self.get_modmail_category_id())
        errors = []


        exists = await self.bot.threads.find(recipient=user)
        if exists:
            errors.append(f"A thread for {user} already exists.")
            if exists.channel:
                errors[-1] += f" in {exists.channel.mention}"
            errors[-1] += "."
        elif user.bot:
            errors.append(f"{user} is a bot, cannot add to thread.")


        if errors or not user:
            if not user:
                # no users left
                title = "Thread not created"
            else:
                title = None

            if manual_trigger:  # not react to contact
                embed = discord.Embed(title=title, color=discord.Color.red(), description="\n".join(errors))
                await interaction.response.send_message(embed=embed, delete_after=10)
                return

            if not user:
                # end
                return

        creator = interaction.user

        thread = await self.bot.threads.create(
            recipient=user,
            creator=creator,
            category=category,
            manual_trigger=manual_trigger,
        )

        if thread.cancelled:
            return

        if creator.id == user.id:
            description = "You have opened a Modmail chat."
        else:
            description = "Staff have opened a Modmail thread."

        em = discord.Embed(
            title="New Modmail",
            description=description,
            color=discord.Color.blurple(),
        )

        em.timestamp = discord.utils.utcnow()
        em.set_footer(icon_url=self.bot.user.avatar.url)

        await user.send(embed=em)

        embed = discord.Embed(
            title="Created Modmail",
            description=f"Modmail started by {creator.mention} for {user.mention}.",
            color=discord.Color.blurple(),
        )
        await thread.wait_until_ready()

        await thread.channel.send(embed=embed)

        if manual_trigger:
            await interaction.response.send_message("✅ Modmail kanaal aangemaakt!")
            await asyncio.sleep(5)
            await interaction.delete_original_response()

    @command(name="delete", description="Deletes a modmail message.")
    @has_admin()
    @checks.thread_only()
    async def delete(self, interaction: discord.Interaction, message_id: Optional[str] = ""):
        """
        Delete a message that was sent using the reply command
        Deletes the previous message
        """
        thread = await ThreadManager.find(self.bot.threads, channel=interaction.channel)

        message_id = int(message_id) if message_id.isdigit() and 17 <= len(message_id) <= 19 else None

        try:
            await thread.delete_message(message=message_id)
        except ValueError as e:
            self.bot.log.warning("Failed to delete message: %s.", e)
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="Failed",
                    description="Cannot find a message to delete. Plain messages are not supported.",
                    color=discord.Color.red(),
                )
            )

        await interaction.response.send_message("🗑️ Bericht verwijderd!")

async def setup(bot):
    await bot.add_cog(Modmail(bot))