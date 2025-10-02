import asyncio
import datetime
import re
import time

import discord
import pymongo
from discord import app_commands
from discord.ext import commands

from utils.has_admin import has_admin
from utils.has_role import has_role
from utils.timezone import to_local

from .moderation_tasks import ModerationTasks
from .moderation_utils import create_dm_embed, log_infraction, send_dm_embed
from .mute_system import MuteSystem
from .timeout_system import TimeoutSystem

MAX_PURGE = 100  # Discord limit


class ModCommands(commands.Cog, name="ModCommands"):
    """
    Commands voor server moderatie.
    """

    def __init__(self, bot):
        """Initialiseert de ModCommands cog."""
        self.bot = bot
        self.infractions_collection = self.bot.db["infractions"]
        self.settings_collection = self.bot.db["settings"]
        self.scheduled_unmutes_collection = self.bot.db["scheduled_unmutes"]

        # Initialize subsystems
        self.tasks = ModerationTasks(
            bot, self.scheduled_unmutes_collection, self.infractions_collection
        )
        self.mute_system = MuteSystem(bot, self.infractions_collection, self.tasks)
        self.timeout_system = TimeoutSystem(bot, self.infractions_collection, self.mute_system)

        # Start background tasks
        self.tasks.start_unmute_checker()

    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        self.tasks.stop_unmute_checker()

    @app_commands.command(name="kick", description="Kick een member van de server.")
    @has_role("The Council")
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Geen reden opgegeven.",
    ):
        """Kickt een member van de server met een optionele reden."""
        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        dm_embed = create_dm_embed(
            "⚠️ | Je bent gekickt.", f"Reden: {reason}", discord.Color.orange(), bot_icon_url
        )

        await send_dm_embed(member, dm_embed)

        try:
            await member.kick(reason=reason)
            self.bot.log.info(
                f"User {member.name} ({member.id}) kicked by {interaction.user.name} ({interaction.user.id}). Reason: {reason}"
            )

            embed = discord.Embed(
                title="Member gekickt",
                description=f"{member.mention} is gekickt. Reden: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)

            try:
                await log_infraction(
                    self.infractions_collection,
                    interaction.guild.id,
                    member.id,
                    interaction.user.id,
                    "kick",
                    reason,
                )
            except Exception as e:
                self.bot.log.error(
                    f"Failed to log kick infraction for {member.name} ({member.id}): {e}"
                )

        except discord.errors.Forbidden as e:
            self.bot.log.error(
                f"Permission denied when trying to kick {member.name} ({member.id}): {e}"
            )
            embed = discord.Embed(
                title="Permissie Fout",
                description="Ik heb geen permissie om deze member te kicken.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.HTTPException as e:
            self.bot.log.error(f"HTTP error when trying to kick {member.name} ({member.id}): {e}")
            embed = discord.Embed(
                title="Discord API Fout",
                description=f"Kicken mislukt door Discord API fout: {str(e)}",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            self.bot.log.error(
                f"Unexpected error when trying to kick {member.name} ({member.id}): {e}",
                exc_info=True,
            )
            embed = discord.Embed(
                title="Onverwachte Fout",
                description=f"Er is een onverwachte fout opgetreden bij het kicken: {str(e)}",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ban", description="Ban een member van de server.")
    @has_admin()
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Geen reden opgegeven.",
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            # Try to send DM with unban request link
            dm_success = False
            try:
                channel = await member.create_dm()
                view = discord.ui.View()
                settings = await self.settings_collection.find_one({"_id": "mod_settings"})
                unban_request_url = (
                    settings.get("unban_request_url", "https://example.com/unban_request")
                    if settings
                    else "https://example.com/unban_request"
                )
                button = discord.ui.Button(
                    label="Unban Aanvragen", style=discord.ButtonStyle.link, url=unban_request_url
                )
                view.add_item(button)

                await channel.send(
                    embed=discord.Embed(
                        title="⚠️ | Je bent gebanned.",
                        description=f"Je bent gebanned van {interaction.guild.name} met reden: {reason} \n\n Als je een unban wilt aanvragen, klik dan op de link hieronder.",
                        color=discord.Color.gold(),
                    ),
                    view=view,
                )
                dm_success = True
                self.bot.log.debug(
                    f"DM sent successfully to {member.name} ({member.id}) for ban notification"
                )
            except discord.errors.Forbidden:
                self.bot.log.info(
                    f"Could not send DM to {member.name} ({member.id}) - DMs disabled or blocked"
                )
                dm_success = False
            except Exception as e:
                self.bot.log.warning(f"Failed to send DM to {member.name} ({member.id}): {e}")
                dm_success = False

            # Perform the ban
            await member.ban(reason=reason)
            self.bot.log.info(
                f"User {member.name} ({member.id}) banned by {interaction.user.name} ({interaction.user.id}). Reason: {reason}"
            )

            # Send success message
            embed = discord.Embed(
                title="Member gebanned",
                description=f"{member.mention} is gebanned. Reden: {reason}",
                color=discord.Color.green(),
            )

            if dm_success:
                embed.set_footer(text="Gebruiker is via DM geïnformeerd.")
            else:
                embed.set_footer(text="Kon gebruiker niet via DM informeren.")

            await interaction.followup.send(embed=embed, ephemeral=False)

            # Log the infraction
            try:
                await log_infraction(
                    self.infractions_collection,
                    interaction.guild.id,
                    member.id,
                    interaction.user.id,
                    "ban",
                    reason,
                )
            except Exception as e:
                self.bot.log.error(
                    f"Failed to log ban infraction for {member.name} ({member.id}): {e}"
                )

        except discord.errors.Forbidden as e:
            self.bot.log.error(
                f"Permission denied when trying to ban {member.name} ({member.id}): {e}"
            )
            embed = discord.Embed(
                title="Permissie Fout",
                description="Ik heb geen permissie om deze member te bannen.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.errors.HTTPException as e:
            self.bot.log.error(f"HTTP error when trying to ban {member.name} ({member.id}): {e}")
            embed = discord.Embed(
                title="Discord API Fout",
                description=f"Bannen mislukt door Discord API fout: {str(e)}",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            self.bot.log.error(
                f"Unexpected error when trying to ban {member.name} ({member.id}): {e}",
                exc_info=True,
            )
            embed = discord.Embed(
                title="Onverwachte Fout",
                description=f"Er is een onverwachte fout opgetreden bij het bannen: {str(e)}",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="unban", description="Unban een gebruiker van de server.")
    @has_admin()
    @app_commands.describe(
        user_id="Het Discord ID van de gebruiker om te unbannen",
        reason="De reden voor het unbannen",
    )
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str,
        reason: str = "Geen reden opgegeven",
    ):
        try:
            # Convert string to int
            user_id_int = int(user_id)

            # Try to get the user object
            user = await self.bot.fetch_user(user_id_int)

            # Check if user is actually banned
            try:
                await interaction.guild.fetch_ban(user)
            except discord.NotFound:
                embed = discord.Embed(
                    title="Gebruiker Niet Gebanned",
                    description=f"Gebruiker {user.mention} ({user_id}) is niet gebanned.",
                    color=discord.Color.orange(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Unban the user
            await interaction.guild.unban(user, reason=reason)
            self.bot.log.info(
                f"User {user.name} ({user.id}) unbanned by {interaction.user.name} ({interaction.user.id}). Reason: {reason}"
            )

            embed = discord.Embed(
                title="Gebruiker Ongebanned",
                description=f"{user.mention} ({user_id}) is ongebanned. Reden: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)

            # Log the infraction
            try:
                await log_infraction(
                    self.infractions_collection,
                    interaction.guild.id,
                    user.id,
                    interaction.user.id,
                    "unban",
                    reason,
                )
            except Exception as e:
                self.bot.log.error(
                    f"Failed to log unban infraction for {user.name} ({user.id}): {e}"
                )

        except ValueError:
            self.bot.log.warning(
                f"Invalid user ID provided for unban: {user_id} by {interaction.user.name} ({interaction.user.id})"
            )
            embed = discord.Embed(
                title="Ongeldig ID",
                description="Het opgegeven gebruikers-ID is niet geldig.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.NotFound as e:
            self.bot.log.warning(
                f"User not found for unban: {user_id} by {interaction.user.name} ({interaction.user.id}): {e}"
            )
            embed = discord.Embed(
                title="Gebruiker Niet Gevonden",
                description=f"Geen gebruiker gevonden met ID: {user_id}",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.Forbidden as e:
            self.bot.log.error(f"Permission denied when trying to unban user {user_id}: {e}")
            embed = discord.Embed(
                title="Permissie Fout",
                description="Ik heb geen permissie om gebruikers te unbannen.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.HTTPException as e:
            self.bot.log.error(f"HTTP error when trying to unban user {user_id}: {e}")
            embed = discord.Embed(
                title="Discord API Fout",
                description=f"Unbannen mislukt door Discord API fout: {str(e)}",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            self.bot.log.error(
                f"Unexpected error when trying to unban user {user_id}: {e}", exc_info=True
            )
            embed = discord.Embed(
                title="Onverwachte Fout",
                description=f"Er is een onverwachte fout opgetreden bij het unbannen: {str(e)}",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="warn", description="Waarschuw een user")
    @has_role("The Council")
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Geen reden opgegeven.",
    ):
        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        dm_embed = create_dm_embed(
            "⚠️ | Je bent gewaarschuwd.", f"Reden: {reason}", discord.Color.yellow(), bot_icon_url
        )

        await send_dm_embed(member, dm_embed)
        embed = discord.Embed(
            title="Member gewaarschuwd",
            description=f"{member.mention} is gewaarschuwd. Reden: {reason}",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)
        await log_infraction(
            self.infractions_collection,
            interaction.guild.id,
            member.id,
            interaction.user.id,
            "warn",
            reason,
        )

    # Timeout commands
    @app_commands.command(name="timeout", description="Timeout een member in de server")
    @has_role("The Council")
    @app_commands.describe(
        member="De member om te timeouten",
        duration="De duration van de timeout (bijv. 1m, 5h, 1d, 1w, 1mo, 1y). Max 28 dagen voor timeout, longer durations use muted role.",
        reason="De reden voor de timeout",
    )
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: str = "Geen reden opgegeven",
    ):
        await self.timeout_system.handle_timeout_command(interaction, member, duration, reason)

    @app_commands.command(name="untimeout", description="Verwijdert timeout van een member")
    @has_role("The Council")
    @app_commands.describe(
        member="De member om de timeout van te verwijderen",
        reason="De reden voor het verwijderen van de timeout",
    )
    async def untimeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Geen reden opgegeven.",
    ):
        await self.timeout_system.handle_untimeout_command(interaction, member, reason)

    # Mute commands
    @app_commands.command(name="mute", description="Mute een member in de server")
    @has_role("The Council")
    async def mute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Geen reden opgegeven.",
    ):
        await self.mute_system.handle_mute_command(interaction, member, reason)

    @app_commands.command(name="unmute", description="Unmute een member in de server.")
    @has_role("The Council")
    async def unmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Geen reden opgegeven.",
    ):
        await self.mute_system.handle_unmute_command(interaction, member, reason)

    @app_commands.command(
        name="history", description="Laat de recente straffen van een gebruiker zien."
    )
    @has_role("The Council")
    @app_commands.describe(user="De gebruiker om de voorgaande straffen van te bekijken")
    async def history(self, interaction: discord.Interaction, user: discord.User):
        infractions = (
            await self.infractions_collection.find(
                {"guild_id": interaction.guild.id, "user_id": user.id}
            )
            .sort("timestamp", pymongo.DESCENDING)
            .limit(10)
            .to_list(length=None)
        )

        # Dutch translations for infraction types
        infraction_translations = {
            "kick": "Kick",
            "ban": "Ban",
            "unban": "Unban",
            "warn": "Waarschuwing",
            "mute": "Mute",
            "unmute": "Unmute",
            "timeout": "Timeout",
            "untimeout": "Untimeout",
            "auto_unmute": "Automatische Unmute",
        }

        infraction_list = ""
        for infraction in infractions:
            # Parse timestamp - handle both datetime objects and ISO strings
            timestamp = infraction["timestamp"]
            if isinstance(timestamp, str):
                timestamp = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

            localized_timestamp = to_local(timestamp)
            infraction_type = infraction_translations.get(
                infraction["type"], infraction["type"].capitalize()
            )
            reason = infraction.get("reason", "Geen reden opgegeven")

            # Extract duration information if present in reason
            duration_info = ""
            if "(duur:" in reason:
                duration_match = re.search(r"\(duur: ([^)]+)\)", reason)
                if duration_match:
                    duration_info = f" **({duration_match.group(1)})**"
                    reason = re.sub(r"\s*\(duur: [^)]+\)", "", reason)

            # Get moderator info if available
            moderator_info = ""
            if "moderator_id" in infraction:
                try:
                    moderator = interaction.guild.get_member(infraction["moderator_id"])
                    if moderator:
                        moderator_info = f" door {moderator.mention}"
                    else:
                        moderator_info = f" door <@{infraction['moderator_id']}>"
                except Exception:
                    moderator_info = ""

            infraction_list += (
                f"<t:{int(time.mktime(localized_timestamp.timetuple()))}:f> "
                f"- **{infraction_type}**{duration_info}{moderator_info}\n"
                f"**Reden:** {reason}\n\n"
            )

        if not infraction_list:
            infraction_list = "Geen voorgaande straffen gevonden voor deze gebruiker."

        # Check of user nog lid is
        member = interaction.guild.get_member(user.id)

        embed = discord.Embed(
            title=f"Strafgeschiedenis voor {user.name}",
            color=discord.Color.blue(),
            description=infraction_list,
        )

        if member and member.joined_at:
            embed.add_field(
                name="Lid Sinds",
                value=f"<t:{int(time.mktime(to_local(member.joined_at).timetuple()))}:D>",
                inline=False,
            )

        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="purge", description="Purge messages from the channel.")
    @app_commands.describe(
        count="Number of messages to purge (max 100)",
        bots="Include messages from bots",
        bot_only="Purge only messages from bots",
    )
    async def purge(
        self,
        interaction: discord.Interaction,
        count: int,
        bots: bool = False,
        bot_only: bool = False,
    ):
        await interaction.response.defer(ephemeral=True)

        if count > MAX_PURGE:
            await interaction.followup.send(
                f"⚠️ Maximaal {MAX_PURGE} berichten per purge toegestaan door Discord.",
                ephemeral=True,
            )
            return

        def check(message: discord.Message):
            if bot_only:
                return message.author.bot
            elif bots:
                return True
            else:
                return not message.author.bot

        try:
            deleted = await interaction.channel.purge(limit=count, check=check, bulk=True)
            embed = discord.Embed(
                title="Messages Purged",
                description=f"✅ {len(deleted)} berichten verwijderd.",
                color=discord.Color.green(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Ik heb geen permissies om berichten te verwijderen.",
                ephemeral=True,
            )

        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Purge mislukt: {e}", ephemeral=True)

    @app_commands.command(
        name="purge_below", description="Verwijder alle berichten onder een specifiek bericht."
    )
    @app_commands.describe(
        message_link="De link of ID van het bericht waarboven niet verwijderd wordt"
    )
    async def purge_below(self, interaction: discord.Interaction, message_link: str):
        await interaction.response.defer(ephemeral=True)

        try:
            message_id = None
            channel_id = interaction.channel.id

            # Kijk of het een bericht-link is
            match = re.search(r"channels/\d+/(\d+)/(\d+)", message_link)
            if match:
                channel_id = int(match.group(1))
                message_id = int(match.group(2))
            else:
                # Probeer gewoon een ID
                message_id = int(message_link)

            channel = interaction.guild.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                await interaction.followup.send(
                    "❌ Ongeldige channel of berichtlink.", ephemeral=True
                )
                return

            # Haal het bericht op
            target_message = await channel.fetch_message(message_id)

            # Verzamel alle berichten onder het doelbericht
            messages_to_delete = []
            async for msg in channel.history(limit=None, oldest_first=False):
                if msg.id == target_message.id:
                    break
                messages_to_delete.append(msg)

            if not messages_to_delete:
                await interaction.followup.send(
                    "⚠️ Geen berichten gevonden om te verwijderen.", ephemeral=True
                )
                return

            # Chunk delete
            MAX_PURGE = 100
            while messages_to_delete:
                chunk = messages_to_delete[:MAX_PURGE]
                del messages_to_delete[:MAX_PURGE]

                await channel.delete_messages(chunk)
                await asyncio.sleep(1)  # rate limit bescherming

            await interaction.followup.send(
                f"✅ {len(messages_to_delete)} berichten verwijderd onder het geselecteerde bericht.",
                ephemeral=True,
            )

        except Exception as e:
            await interaction.followup.send(f"❌ Fout bij verwijderen: {e}", ephemeral=True)

    @app_commands.command(
        name="lockdown",
        description="Prevent sending messages in a channel.",
    )
    @has_role("The Council")
    @app_commands.describe(channel="The channel to lockdown", reason="The reason for the lockdown")
    async def lockdown(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        reason: str = "No reason provided.",
    ):
        try:
            await channel.set_permissions(interaction.guild.default_role, send_messages=False)

            embed = discord.Embed(
                title="Channel Locked Down",
                description=f"{channel.mention} has been locked down. Reason: {reason}",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed)

        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I do not have permission to lockdown this channel.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="unlockdown",
        description="Unlock a locked channel.",
    )
    @has_role("The Council")
    @app_commands.describe(channel="The channel to unlock", reason="The reason for the unlockdown")
    async def unlockdown(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        reason: str = "No reason provided.",
    ):
        try:
            await channel.set_permissions(interaction.guild.default_role, send_messages=True)

            embed = discord.Embed(
                title="Channel Unlocked",
                description=f"{channel.mention} has been unlocked. Reason: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I do not have permission to unlock this channel.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ModCommands(bot))
