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

    async def get_modmail_category_id(self):
        settings = await self.db.settings.find_one({"_id": self.settings_id})
        if settings and "modmail_category_id" in settings:
            return settings["modmail_category_id"]
        return None

    async def get_modmail_logs_channel_id(self):
        settings = await self.db.settings.find_one({"_id": self.settings_id})
        if settings and "modmail_channel_id" in settings:
            return settings["modmail_channel_id"]
        return None



    # @commands.command(usage="[after] [close message]")
    @command(name="close", description="Sluit het ticket")
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
        # Check if this is actually a ticket channel by looking for thread
        thread = await self.bot.threads.find(channel=interaction.channel)
        
        if thread is None:
            await interaction.response.send_message("❌ Dit is geen actief ticket kanaal.", ephemeral=True)
            return
            
        # Respond immediately before closing (since channel will be deleted)
        silent = any(x == option for x in {"silent"})
        close_msg = "🔒 Ticket wordt gesloten..."
        if silent:
            close_msg += " (stil)"
        if reason:
            close_msg += f"\nReden: {reason}"
            
        await interaction.response.send_message(close_msg, ephemeral=True)
        
        # Close the thread
        try:
            modmail_logs_channel_id = await self.get_modmail_logs_channel_id()
            modmail_logs_channel = None
            
            if modmail_logs_channel_id is None:
                # No log channel configured - warn but still allow closing
                await interaction.followup.send("⚠️ Waarschuwing: Geen modmail log kanaal geconfigureerd. Ticket wordt gesloten maar transcript wordt niet gelogd.", ephemeral=True)
            else:
                try:
                    modmail_logs_channel = await self.bot.fetch_channel(modmail_logs_channel_id)
                except discord.NotFound:
                    await interaction.followup.send("⚠️ Waarschuwing: Het geconfigureerde modmail log kanaal bestaat niet meer. Ticket wordt gesloten maar transcript wordt niet gelogd.", ephemeral=True)
                except discord.Forbidden:
                    await interaction.followup.send("⚠️ Waarschuwing: Geen toegang tot het modmail log kanaal. Ticket wordt gesloten maar transcript wordt niet gelogd.", ephemeral=True)
            
            await thread.close(closer=interaction.user, message=reason, silent=silent, log_channel=modmail_logs_channel)
            self.bot.log.info(f"Modmail ticket closed successfully by {interaction.user.name} ({interaction.user.id}) in channel {interaction.channel.id}. Reason: {reason or 'No reason provided'}")
        except discord.Forbidden as e:
            error_msg = f"❌ Geen toestemming om ticket te sluiten: {str(e)}"
            self.bot.log.error(f"Permission denied when closing modmail ticket in channel {interaction.channel.id}: {e}")
            await interaction.followup.send(error_msg, ephemeral=True)
            return
        except discord.NotFound as e:
            error_msg = f"❌ Ticket kanaal of gebruiker niet gevonden: {str(e)}"
            self.bot.log.error(f"Channel or user not found when closing modmail ticket in channel {interaction.channel.id}: {e}")
            await interaction.followup.send(error_msg, ephemeral=True)
            return
        except discord.HTTPException as e:
            error_msg = f"❌ Discord API fout bij sluiten ticket: {str(e)}"
            self.bot.log.error(f"Discord API error when closing modmail ticket in channel {interaction.channel.id}: {e}")
            await interaction.followup.send(error_msg, ephemeral=True)
            return
        except Exception as e:
            error_msg = f"❌ Onverwachte fout bij sluiten ticket: {str(e)}"
            self.bot.log.error(f"Unexpected error when closing modmail ticket in channel {interaction.channel.id}: {e}", exc_info=True)
            await interaction.followup.send(error_msg, ephemeral=True)
            return

    @command(name="generate_transcript", description="Maakt een transcript en stuurt het naar het log kanaal")
    @has_admin()
    @checks.thread_only()
    async def generate_transcript(
            self,
            interaction: discord.Interaction,
    ):
        await interaction.response.defer(thinking=False)

        thread = await self.bot.threads.find(channel=interaction.channel)
        if thread is None:
            await interaction.followup.send("❌ Dit is geen actief ticket kanaal.", ephemeral=True)
            return
            
        try:
            await thread.store_and_send_log(closer=interaction.user, log_channel=interaction.channel)
            confirmation = await interaction.followup.send("📝 Transcript gegenereerd", ephemeral=True)
            await asyncio.sleep(2)
            await confirmation.delete()
        except Exception as e:
            await interaction.followup.send(f"❌ Fout bij genereren transcript: {str(e)}", ephemeral=True)

    @command(name="transcripts", description="Geeft transcripts van een bepaalde persoon")
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

    @command(name="nsfw", description="Verandert Modmail-ticket naar NSFW status")
    @has_admin()
    @checks.thread_only()
    async def nsfw(self, interaction: discord.Interaction):
        """Markeert een Modmail ticket als NSFW (niet veilig voor werk)."""
        await interaction.channel.edit(nsfw=True)
        await interaction.response.send_message("🔞 Kanaal ingesteld op NSFW")

    @command(name="sfw", description="Verandert Modmail-ticket naar SFW status")
    @has_admin()
    @checks.thread_only()
    async def sfw(self, interaction: discord.Interaction):
        """Markeert een Modmail ticket als SFW (veilig voor werk)."""
        await interaction.channel.edit(nsfw=False)
        await interaction.response.send_message("⚠️ Kanaal ingesteld op SFW")

    @command(name="reply", description="Antwoordt op een Modmail-bericht")
    @has_admin()
    @checks.thread_only()
    async def reply(self, interaction: discord.Interaction, msg: str):
        """
        Reply to a Modmail thread.
        Supports attachments and images as well as
        automatically embedding image URLs.
        """
        await interaction.response.defer(thinking=False)

        thread = await self.bot.threads.find(channel=interaction.channel)
        if thread is None:
            await interaction.followup.send("❌ Dit is geen actief ticket kanaal.", ephemeral=True)
            return
            
        sent_message = await interaction.channel.send(msg)
        sent_message.author = interaction.user

        try:
            async with interaction.channel.typing():
                await thread.reply(sent_message)
            confirmation = await interaction.followup.send("📤 Bericht verzonden!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Fout bij verzenden bericht: {str(e)}", ephemeral=True)
            return
        await asyncio.sleep(3)
        await confirmation.delete()

    @command(name="areply", description="Antwoordt anoniem op een Modmail-bericht")
    @has_admin()
    @checks.thread_only()
    async def areply(self, interaction: discord.Interaction, msg: str):
        """
        Reply to a thread anonymously.
        """
        await interaction.response.defer(thinking=False)

        thread = await self.bot.threads.find(channel=interaction.channel)
        if thread is None:
            await interaction.followup.send("❌ Dit is geen actief ticket kanaal.", ephemeral=True)
            return
            
        sent_message = await interaction.channel.send(msg)
        sent_message.author = interaction.user

        try:
            async with interaction.channel.typing():
                await thread.reply(sent_message, anonymous=True)
            confirmation = await interaction.followup.send("📤 Bericht verzonden!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Fout bij verzenden bericht: {str(e)}", ephemeral=True)
            return
        await asyncio.sleep(3)
        await confirmation.delete()

    # @commands.group(invoke_without_command=True)
    @command(name="note", description="Verduidelijking van modmail")
    @has_admin()
    @checks.thread_only()
    async def note(self, interaction: discord.Interaction, msg: str):
        """
        Take a note about the current thread.
        Useful for noting context.
        """
        await interaction.response.defer(thinking=False)

        thread = await self.bot.threads.find(channel=interaction.channel)
        if thread is None:
            await interaction.followup.send("❌ Dit is geen actief ticket kanaal.", ephemeral=True)
            return
            
        sent_message = await interaction.channel.send(msg)
        sent_message.author = interaction.user

        try:
            async with interaction.channel.typing():
                msg = await thread.note(sent_message)
                await msg.pin()
        except Exception as e:
            await interaction.followup.send(f"❌ Fout bij maken notitie: {str(e)}", ephemeral=True)
            return

        confirmation = await interaction.followup.send("📝 Genoteerd", ephemeral=True)
        await asyncio.sleep(3)
        await confirmation.delete()

    @command(name="edit", description="Bewerkt een Modmail-bericht")
    @has_admin()
    @checks.thread_only()
    async def edit(self, interaction: discord.Interaction, message: str, message_id: Optional[str] = "" ):
        """
        Edit a message that was sent using the reply or anonreply command.

        If no `message_id` is provided,
        the last message sent by a staff will be edited.

        Note: attachments **cannot** be edited.
        """
        thread = await self.bot.threads.find(channel=interaction.channel)
        if thread is None:
            await interaction.response.send_message("❌ Dit is geen actief ticket kanaal.", ephemeral=True)
            return

        message_id = int(message_id) if message_id.isdigit() and 17 <= len(message_id) <= 19 else None


        try:
            await thread.edit_message(message_id, message)
        except ValueError:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="Mislukt",
                    description="Kan het bericht niet vinden om te bewerken. Gewone berichten worden niet ondersteund.",
                    color=discord.Color.red(),
                )
            )

        await interaction.response.send_message("📝 Bericht succesvol bewerkt")
        # await asyncio.sleep(5)
        # await interaction.delete_original_response()

    # @commands.command(usage="<user> [category] [options]")
    @command(name="contact", description="Opent een modmail ticket")
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
            errors.append(f"Een ticket voor {user} bestaat al.")
            if exists.channel:
                errors[-1] += f" in {exists.channel.mention}"
            errors[-1] += "."
        elif user.bot:
            errors.append(f"{user} is een bot, kan niet aan ticket toevoegen.")


        if errors or not user:
            if not user:
                # no users left
                title = "Ticket niet aangemaakt"
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
            description = "Je hebt een Modmail gesprek geopend."
        else:
            description = "Staff heeft een Modmail ticket geopend."

        em = discord.Embed(
            title="Nieuwe Modmail",
            description=description,
            color=discord.Color.blurple(),
        )

        em.timestamp = discord.utils.utcnow()
        bot_avatar_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        em.set_footer(icon_url=bot_avatar_url)

        await user.send(embed=em)

        embed = discord.Embed(
            title="Modmail Aangemaakt",
            description=f"Modmail gestart door {creator.mention} voor {user.mention}.",
            color=discord.Color.blurple(),
        )
        await thread.wait_until_ready()

        await thread.channel.send(embed=embed)

        if manual_trigger:
            await interaction.response.send_message("✅ Modmail kanaal aangemaakt!")
            await asyncio.sleep(5)
            await interaction.delete_original_response()

    @command(name="delete", description="Verwijdert een modmail bericht.")
    @has_admin()
    @checks.thread_only()
    async def delete(self, interaction: discord.Interaction, message_id: Optional[str] = ""):
        """
        Delete a message that was sent using the reply command
        Deletes the previous message
        """
        thread = await self.bot.threads.find(channel=interaction.channel)
        if thread is None:
            await interaction.response.send_message("❌ Dit is geen actief ticket kanaal.", ephemeral=True)
            return

        message_id = int(message_id) if message_id.isdigit() and 17 <= len(message_id) <= 19 else None

        try:
            await thread.delete_message(message=message_id)
        except ValueError as e:
            self.bot.log.warning("Failed to delete message: %s.", e)
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="Mislukt",
                    description="Kan het bericht niet vinden om te verwijderen. Gewone berichten worden niet ondersteund.",
                    color=discord.Color.red(),
                )
            )

        await interaction.response.send_message("🗑️ Bericht verwijderd!")

async def setup(bot):
    await bot.add_cog(Modmail(bot))