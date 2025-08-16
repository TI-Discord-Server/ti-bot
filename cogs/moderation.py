import discord
from discord import app_commands
from discord.ext import commands
import datetime
import re
from typing import Optional
import pymongo
import time
import asyncio
from utils.has_role import has_role
from utils.has_admin import has_admin
from utils.timezone import TIMEZONE, now_utc, format_local_time, to_local





class ModCommands(commands.Cog, name="ModCommands"):
    """
    Commands voor server moderatie.
    """

    def __init__(self, bot):
        """Initialiseert de ModCommands cog."""
        self.bot = bot
        self.infractions_collection = self.bot.db["infractions"]
        self.settings_collection = self.bot.db["settings"]

    async def send_dm_embed(self, member: discord.Member, embed: discord.Embed):
        """
        Stuurt een DM naar een gebruiker met een embedded message.
        Retourneert True als de DM succesvol is verzonden, False anders.
        """
        try:
            await member.send(embed=embed)
            return True
        except (discord.errors.Forbidden, discord.errors.HTTPException):
            return False

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
        timestamp = now_utc()
        dm_embed = discord.Embed(
            title=f"⚠️ | Je bent gekickt.",
            description=f"Reden: {reason}",
            color=discord.Color.orange(),
        )
        # Gebruik de timezone bij het formatteren van de tijd
        dm_embed.set_footer(text=f"Tijd: {format_local_time(timestamp)}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)

        dm_sent = await self.send_dm_embed(member, dm_embed)

        try:
            await member.kick(reason=reason)
            self.bot.log.info(f"User {member.name} ({member.id}) kicked by {interaction.user.name} ({interaction.user.id}). Reason: {reason}")
            
            embed = discord.Embed(
                title="Member gekickt",
                description=f"{member.mention} is gekickt. Reden: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
            
            try:
                await self.log_infraction(
                    interaction.guild.id, member.id, interaction.user.id, "kick", reason
                )
            except Exception as e:
                self.bot.log.error(f"Failed to log kick infraction for {member.name} ({member.id}): {e}")

        except discord.errors.Forbidden as e:
            self.bot.log.error(f"Permission denied when trying to kick {member.name} ({member.id}): {e}")
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
            self.bot.log.error(f"Unexpected error when trying to kick {member.name} ({member.id}): {e}", exc_info=True)
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
        """Bant een member van de server met een optionele reden."""
        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        timestamp = now_utc()
        dm_embed = discord.Embed(
            title=f"⚠️ | Je bent gebanned.",
            description=f"Reden: {reason}",
            color=discord.Color.dark_red(),
        )
        # Gebruik de timezone bij het formatteren van de tijd
        dm_embed.set_footer(text=f"Tijd: {format_local_time(timestamp)}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)

        await interaction.response.defer(ephemeral=True)

        try:
            # Try to send DM with unban request link
            dm_success = False
            try:
                channel = await member.create_dm()
                view = discord.ui.View()
                settings = await self.settings_collection.find_one({"_id": "mod_settings"})
                unban_request_url = settings.get("unban_request_url", "https://example.com/unban_request") if settings else "https://example.com/unban_request"
                button = discord.ui.Button(
                    label="Request Unban", style=discord.ButtonStyle.link, url=unban_request_url
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
                self.bot.log.debug(f"DM sent successfully to {member.name} ({member.id}) for ban notification")
            except discord.errors.Forbidden:
                self.bot.log.info(f"Could not send DM to {member.name} ({member.id}) - DMs disabled or blocked")
                dm_success = False
            except Exception as e:
                self.bot.log.warning(f"Failed to send DM to {member.name} ({member.id}): {e}")
                dm_success = False

            # Perform the ban
            await member.ban(reason=reason)
            self.bot.log.info(f"User {member.name} ({member.id}) banned by {interaction.user.name} ({interaction.user.id}). Reason: {reason}")

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
                await self.log_infraction(
                    interaction.guild.id, member.id, interaction.user.id, "ban", reason
                )
            except Exception as e:
                self.bot.log.error(f"Failed to log ban infraction for {member.name} ({member.id}): {e}")

        except discord.errors.Forbidden as e:
            self.bot.log.error(f"Permission denied when trying to ban {member.name} ({member.id}): {e}")
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
            self.bot.log.error(f"Unexpected error when trying to ban {member.name} ({member.id}): {e}", exc_info=True)
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
        reason="De reden voor het unbannen"
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
                ban_entry = await interaction.guild.fetch_ban(user)
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
            self.bot.log.info(f"User {user.name} ({user.id}) unbanned by {interaction.user.name} ({interaction.user.id}). Reason: {reason}")
            
            embed = discord.Embed(
                title="Gebruiker Ongebanned",
                description=f"{user.mention} ({user_id}) is ongebanned. Reden: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
            
            # Log the infraction
            try:
                await self.log_infraction(
                    interaction.guild.id, user.id, interaction.user.id, "unban", reason
                )
            except Exception as e:
                self.bot.log.error(f"Failed to log unban infraction for {user.name} ({user.id}): {e}")
            
        except ValueError as e:
            self.bot.log.warning(f"Invalid user ID provided for unban: {user_id} by {interaction.user.name} ({interaction.user.id})")
            embed = discord.Embed(
                title="Ongeldig ID",
                description="Het opgegeven gebruikers-ID is niet geldig.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.NotFound as e:
            self.bot.log.warning(f"User not found for unban: {user_id} by {interaction.user.name} ({interaction.user.id}): {e}")
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
            self.bot.log.error(f"Unexpected error when trying to unban user {user_id}: {e}", exc_info=True)
            embed = discord.Embed(
                title="Onverwachte Fout",
                description=f"Er is een onverwachte fout opgetreden bij het unbannen: {str(e)}",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="mute", description="Mute een member in de server")
    @has_role("The Council")
    async def mute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Geen reden opgegeven",
    ):
        guild = interaction.guild
        muted_role = discord.utils.get(guild.roles, name="Muted")

        if not muted_role:
            muted_role = await guild.create_role(
                name="Muted", reason="Muted role aangemaakt voor muting"
            )

            for channel in guild.channels:
                try:
                    await channel.set_permissions(
                        muted_role,
                        speak=False,
                        send_messages=False,
                        read_message_history=True,
                    )
                except discord.errors.Forbidden:
                    pass

        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        timestamp = now_utc()
        dm_embed = discord.Embed(
            title=f"⚠️| Je bent gemute.",
            description=f"Reden: {reason}",
            color=discord.Color.dark_gray(),
        )
        # Gebruik de timezone bij het formatteren van de tijd
        dm_embed.set_footer(text=f"Tijd: {format_local_time(timestamp)}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)

        dm_sent = await self.send_dm_embed(member, dm_embed)
        try:
            await member.add_roles(muted_role, reason=reason)
            embed = discord.Embed(
                title="Member gemute",
                description=f"{member.mention} is gemute. Reden: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
            await self.log_infraction(
                interaction.guild.id, member.id, interaction.user.id, "mute", reason
            )

        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permissie Fout",
                description="Ik heb geen permissie om rollen te beheren voor deze member.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.HTTPException:
            embed = discord.Embed(
                title="Fout",
                description="Muten mislukt.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="unmute", description="Unmute een member in de server."
    )
    @has_role("The Council")
    async def unmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Geen reden opgegeven.",
    ):
        guild = interaction.guild
        muted_role = discord.utils.get(guild.roles, name="Muted")

        if not muted_role:
            embed = discord.Embed(
                title="Fout",
                description="Geen 'Muted' role gevonden. Kan niet unmuten.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        timestamp = now_utc()
        dm_embed = discord.Embed(
            title=f"⚠️ | Je bent geunmute.",
            description=f"Reden: {reason}",
            color=discord.Color.green(),
        )
        # Gebruik de timezone bij het formatteren van de tijd
        dm_embed.set_footer(text=f"Tijd: {format_local_time(timestamp)}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)

        dm_sent = await self.send_dm_embed(member, dm_embed)
        try:
            await member.remove_roles(muted_role, reason=reason)
            embed = discord.Embed(
                title="Member geunmute",
                description=f"{member.mention} is geunmute. Reden: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
            await self.log_infraction(
                interaction.guild.id, member.id, interaction.user.id, "unmute", reason
            )
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permissie Fout",
                description="Ik heb geen permissie om rollen te beheren voor deze member.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.HTTPException:
            embed = discord.Embed(
                title="Fout",
                description="Unmuten mislukt.",
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
        timestamp = now_utc()
        dm_embed = discord.Embed(
            title=f"⚠️ | Je bent gewaarschuwd.",
            description=f"Reden: {reason}",
            color=discord.Color.yellow(),
        )
        # Gebruik de timezone bij het formatteren van de tijd
        dm_embed.set_footer(text=f"Tijd: {format_local_time(timestamp)}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)

        dm_sent = await self.send_dm_embed(member, dm_embed)
        if not dm_sent:
            embed = discord.Embed(
                title="Waarschuwing",
                description=f"Kon geen waarschuwing sturen naar {member.mention}.",
                color=discord.Color.orange(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = discord.Embed(
            title="Member gewaarschuwd",
            description=f"{member.mention} is gewaarschuwd en via DM geïnformeerd.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)
        await self.log_infraction(
            interaction.guild.id, member.id, interaction.user.id, "warn", reason
        )

    async def _purge_with_backoff(self, channel, limit, check=None, max_retries=5):
        """
        Custom purge function with exponential backoff for rate limiting.
        
        Args:
            channel: The channel to purge messages from
            limit: Maximum number of messages to delete
            check: Optional function to filter messages
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of deleted messages
        """
        deleted_messages = []
        base_delay = 1.0  # Start with 1 second delay
        max_delay = 60.0  # Maximum delay of 60 seconds
        start_time = time.time()
        
        self.bot.log.info(f"Starting purge operation in channel {channel.id} (limit: {limit}, max_retries: {max_retries})")
        
        for attempt in range(max_retries + 1):
            try:
                # Try to purge messages
                attempt_start = time.time()
                deleted = await channel.purge(limit=limit, check=check)
                deleted_messages.extend(deleted)
                
                total_time = time.time() - start_time
                if attempt > 0:
                    self.bot.log.info(f"Purge successful after {attempt} retries. Deleted {len(deleted)} messages in {total_time:.2f}s total")
                else:
                    self.bot.log.info(f"Purge successful on first attempt. Deleted {len(deleted)} messages in {total_time:.2f}s")
                
                return deleted_messages
                
            except discord.errors.HTTPException as e:
                if e.status == 429:  # Rate limited
                    if attempt < max_retries:
                        # Calculate exponential backoff delay
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        retry_after = e.response.headers.get('Retry-After')
                        
                        self.bot.log.warning(f"Purge rate limited (HTTP 429) on attempt {attempt + 1}/{max_retries + 1}. "
                                           f"Discord Retry-After: {retry_after}s, Using exponential backoff: {delay:.1f}s")
                        
                        await asyncio.sleep(delay)
                        
                        elapsed_time = time.time() - start_time
                        self.bot.log.info(f"Resuming purge attempt {attempt + 2}/{max_retries + 1} after {elapsed_time:.2f}s total elapsed")
                        continue
                    else:
                        total_time = time.time() - start_time
                        self.bot.log.error(f"Purge max retries ({max_retries}) exceeded after {total_time:.2f}s. "
                                         f"Rate limiting prevented completion. HTTP status: {e.status}")
                        raise e
                else:
                    # Other HTTP error, don't retry
                    self.bot.log.error(f"Purge failed with HTTP error {e.status}: {e.text}")
                    raise e
                    
            except Exception as e:
                # Other error, don't retry
                self.bot.log.error(f"Purge failed with unexpected error: {type(e).__name__}: {e}")
                raise e
        
        return deleted_messages

    async def _delete_messages_with_backoff(self, channel, messages, max_retries=3):
        """
        Delete messages with exponential backoff for rate limiting.
        
        Args:
            channel: The channel to delete messages from
            messages: List of messages to delete
            max_retries: Maximum number of retry attempts
            
        Returns:
            Number of messages successfully deleted
        """
        if not messages:
            return 0
            
        base_delay = 1.0  # Start with 1 second delay
        max_delay = 30.0  # Maximum delay of 30 seconds
        start_time = time.time()
        message_count = len(messages)
        deletion_type = "single" if message_count == 1 else "bulk"
        
        self.bot.log.info(f"Starting {deletion_type} message deletion in channel {channel.id} "
                         f"({message_count} messages, max_retries: {max_retries})")
        
        for attempt in range(max_retries + 1):
            try:
                if len(messages) == 1:
                    # Single message deletion
                    await messages[0].delete()
                    total_time = time.time() - start_time
                    if attempt > 0:
                        self.bot.log.info(f"Single message deletion successful after {attempt} retries in {total_time:.2f}s")
                    else:
                        self.bot.log.info(f"Single message deletion successful on first attempt in {total_time:.2f}s")
                    return 1
                else:
                    # Bulk delete for multiple messages
                    await channel.delete_messages(messages)
                    total_time = time.time() - start_time
                    if attempt > 0:
                        self.bot.log.info(f"Bulk deletion of {message_count} messages successful after {attempt} retries in {total_time:.2f}s")
                    else:
                        self.bot.log.info(f"Bulk deletion of {message_count} messages successful on first attempt in {total_time:.2f}s")
                    return len(messages)
                    
            except discord.errors.HTTPException as e:
                if e.status == 429:  # Rate limited
                    if attempt < max_retries:
                        # Calculate exponential backoff delay
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        retry_after = e.response.headers.get('Retry-After')
                        
                        self.bot.log.warning(f"Message deletion rate limited (HTTP 429) on attempt {attempt + 1}/{max_retries + 1}. "
                                           f"Discord Retry-After: {retry_after}s, Using exponential backoff: {delay:.1f}s "
                                           f"({deletion_type} deletion of {message_count} messages)")
                        
                        await asyncio.sleep(delay)
                        
                        elapsed_time = time.time() - start_time
                        self.bot.log.info(f"Resuming message deletion attempt {attempt + 2}/{max_retries + 1} "
                                        f"after {elapsed_time:.2f}s total elapsed")
                        continue
                    else:
                        total_time = time.time() - start_time
                        self.bot.log.error(f"Message deletion max retries ({max_retries}) exceeded after {total_time:.2f}s. "
                                         f"Skipping {deletion_type} deletion of {message_count} messages. HTTP status: {e.status}")
                        return 0  # Return 0 to indicate failure
                else:
                    # Other HTTP error, don't retry
                    self.bot.log.error(f"Message deletion failed with HTTP error {e.status}: {e.text} "
                                     f"({deletion_type} deletion of {message_count} messages)")
                    raise e
                    
            except Exception as e:
                # Other error, don't retry
                self.bot.log.error(f"Message deletion failed with unexpected error: {type(e).__name__}: {e} "
                                 f"({deletion_type} deletion of {message_count} messages)")
                raise e
        
        return 0

    @app_commands.command(
        name="purge", description="Verwijdert messages uit het kanaal."
    )
    @has_role("The Council")
    async def purge(
        self,
        interaction: discord.Interaction,
        count: int,
        bots: bool = False,
        bot_only: bool = False,
    ):
        def check(message):
            if bot_only:
                return message.author.bot
            elif bots:
                return True
            else:
                return not message.author.bot

        await interaction.response.defer(ephemeral=True)

        # Add reasonable limit to prevent abuse
        if count > 1000:
            embed = discord.Embed(
                title="Limiet Overschreden",
                description="Je kunt maximaal 1000 messages tegelijk verwijderen.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            # Use custom purge with exponential backoff for rate limiting
            deleted = await self._purge_with_backoff(interaction.channel, count, check)
            embed = discord.Embed(
                title="Messages verwijderd",
                description=f"{len(deleted)} messages verwijderd in dit kanaal.",
                color=discord.Color.green(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Log the purge action
            self.bot.log.info(f"Purge command used by {interaction.user.name} ({interaction.user.id}) in channel {interaction.channel.id}. Deleted {len(deleted)} messages. Filters: bots={bots}, bot_only={bot_only}")

        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permissie Fout",
                description="Ik heb geen permissie om messages in dit kanaal te verwijderen.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.errors.HTTPException as e:
            if e.status == 429:
                embed = discord.Embed(
                    title="Rate Limited",
                    description="Discord rate limiting verhindert het verwijderen van messages. Probeer het later opnieuw.",
                    color=discord.Color.orange(),
                )
            else:
                embed = discord.Embed(
                    title="HTTP Fout",
                    description=f"Verwijderen mislukt: {e}",
                    color=discord.Color.red(),
                )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="Timeout",
                description="Het verwijderen van messages duurde te lang. Sommige messages zijn mogelijk wel verwijderd.",
                color=discord.Color.orange(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            self.bot.log.error(f"Unexpected error in purge command: {e}", exc_info=True)
            embed = discord.Embed(
                title="Onverwachte Fout",
                description=f"Er is een onverwachte fout opgetreden: {str(e)}",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="timeout", description="Timeout een member in de server"
    )
    @has_role("The Council")
    @app_commands.describe(
        member="De member om te timeouten",
        duration="De duration van de timeout (bijv. 1m, 5h, 1d). Max 28 dagen.",
        reason="De reden voor de timeout",
    )
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: str = "Geen reden opgegeven",
    ):
        duration_timedelta = self.parse_duration(duration)
        if not duration_timedelta:
            embed = discord.Embed(
                title="Fout",
                description="Invalid duration format. Gebruik voorbeelden zoals 1m, 5h, 1d.",
                color=discord.Color.red(),
            )
            return await interaction.response.send_message(
                embed=embed, ephemeral=True
            )

        timeout_until = discord.utils.utcnow() + duration_timedelta

        if duration_timedelta > datetime.timedelta(days=28):
            embed = discord.Embed(
                title="Fout",
                description="Maximale timeout duration is 28 dagen.",
                color=discord.Color.red(),
            )
            return await interaction.response.send_message(
                embed=embed, ephemeral=True
            )

        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        timestamp = now_utc()
        dm_embed = discord.Embed(
            title=f"⚠️ | Je bent getimed out.",
            description=f"Reden: {reason}\nDuration: {duration}",
            color=discord.Color.dark_orange(),
        )
        # Gebruik de timezone bij het formatteren van de tijd
        dm_embed.set_footer(text=f"Tijd: {format_local_time(timestamp)}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)
        dm_sent = await self.send_dm_embed(member, dm_embed)
        try:
            await member.timeout(timeout_until, reason=reason)
            embed = discord.Embed(
                title="Member Timeout",
                description=f"{member.mention} is getimed out voor {duration}. Reden: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
            await self.log_infraction(
                interaction.guild.id, member.id, interaction.user.id, "timeout", reason
            )
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permissie Fout",
                description="Ik heb geen permissie om deze member te timeouten.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    def parse_duration(self, duration_str: str) -> Optional[datetime.timedelta]:
        units = {"m": "minutes", "h": "hours", "d": "days"}
        match = re.match(r"(\d+)([mhd])", duration_str)
        if not match:
            return None

        amount, unit = match.groups()
        amount = int(amount)
        unit = units[unit]
        return datetime.timedelta(**{unit: amount})

    @app_commands.command(
        name="untimeout", description="Verwijdert timeout van een member"
    )
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
        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        timestamp = now_utc()
        dm_embed = discord.Embed(
            title=f"Je timeout is verwijderd in {interaction.guild.name}",
            description=f"Reden: {reason}",
            color=discord.Color.green(),
        )
        # Gebruik de timezone bij het formatteren van de tijd
        dm_embed.set_footer(text=f"Tijd: {format_local_time(timestamp)}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)

        dm_sent = await self.send_dm_embed(member, dm_embed)
        try:
            await member.timeout(None, reason=reason)
            embed = discord.Embed(
                title="Member untimeout",
                description=f"{member.mention} is geuntimeout. Reden: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
            await self.log_infraction(
                interaction.guild.id, member.id, interaction.user.id, "untimeout", reason
            )
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permissie Fout",
                description="Ik heb geen permissie om deze member te untimeouten.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="history", description="Laat de recente straffen van een member zien."
    )
    @has_role("The Council")
    @app_commands.describe(member="De gebruiker om de voorgaande straffen van te bekijken")
    async def history(self, interaction: discord.Interaction, member: discord.Member):
        infractions = await self.bot.db.infractions.find(
            {"guild_id": interaction.guild.id, "user_id": member.id}
        ).sort("timestamp", pymongo.DESCENDING).limit(
            10
        ).to_list(
            length=None
        )
        infraction_list = ""
        for infraction in infractions:
            localized_timestamp = to_local(infraction['timestamp'])
            infraction_list += f"<t:{int(time.mktime(localized_timestamp.timetuple()))}:f> - **{infraction['type'].capitalize()}**: {infraction['reason']}\n"

        if not infraction_list:
            infraction_list = "Geen voorgaande straffen gevonden voor deze gebruiker."

        embed = discord.Embed(
            title=f"History voor {member.name}",
            color=discord.Color.blue(),
            description=infraction_list,
        )
        embed.add_field(
            name="Join Date",
            value=f"<t:{int(time.mktime(to_local(member.joined_at).timetuple()))}:D>",
            inline=False,
        )
        embed.add_field(
            name="Account Creation Date",
            value=f"<t:{int(time.mktime(to_local(member.created_at).timetuple()))}:D>",
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(
        name="lockdown",
        description="Voorkom het versturen van berichten in een channel.",
    )
    @has_role("The Council")
    @app_commands.describe(
        channel="De channel om te lockdownen", reason="De reden voor de lockdown"
    )
    async def lockdown(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        reason: str = "Geen reden opgegeven.",
    ):
        try:
            await channel.set_permissions(
                interaction.guild.default_role, send_messages=False
            )
            embed = discord.Embed(
                title="Channel Gelockdown",
                description=f"{channel.mention} is gelockdown. Reden: {reason}",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed)
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permissie Fout",
                description="Ik heb geen permissie om dit channel te lockdownen.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="unlockdown",
        description="Unlock een gelockdown channel.",
    )
    @has_role("The Council")
    @app_commands.describe(
        channel="De channel om te unlocken", reason="De reden voor het unlocken"
    )
    async def unlockdown(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        reason: str = "Geen reden opgegeven.",
    ):
        try:
            await channel.set_permissions(
                interaction.guild.default_role, send_messages=True
            )
            embed = discord.Embed(
                title="Channel Geunlockt",
                description=f"{channel.mention} is geunlockt. Reden: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permissie Fout",
                description="Ik heb geen permissie om dit channel te unlocken.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="slowmode", description="Stel slowmode in een channel in."
    )
    @has_role("The Council")
    @app_commands.describe(
        channel="De channel om slowmode in te stellen",
        seconds="De slowmode delay in seconden",
    )
    async def slowmode(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        seconds: int,
    ):
        try:
            await channel.edit(slowmode_delay=seconds)
            embed = discord.Embed(
                title="Slowmode Ingesteld",
                description=f"Slowmode ingesteld op {seconds} seconden in {channel.mention}.",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permissie Fout",
                description="Ik heb geen permissie om slowmode in dit channel in te stellen.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.HTTPException:
            embed = discord.Embed(
                title="Fout",
                description="Kon slowmode niet instellen.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def log_infraction(
        self, guild_id, user_id, moderator_id, infraction_type, reason
    ):
        infraction = {
            "guild_id": guild_id,
            "user_id": user_id,
            "moderator_id": moderator_id,
            "type": infraction_type,
            "reason": reason,
            "timestamp": datetime.datetime.utcnow(),
        }
        await self.infractions_collection.insert_one(infraction)

async def _delete_batch_with_backoff(channel, messages, max_retries=3):
    """
    Standalone function to delete a batch of messages with exponential backoff.
    
    Args:
        channel: The channel to delete messages from
        messages: List of messages to delete
        max_retries: Maximum number of retry attempts
        
    Returns:
        Number of messages successfully deleted
    """
    if not messages:
        return 0
        
    base_delay = 1.0  # Start with 1 second delay
    max_delay = 30.0  # Maximum delay of 30 seconds
    
    for attempt in range(max_retries + 1):
        try:
            if len(messages) == 1:
                # Single message deletion
                await messages[0].delete()
                return 1
            else:
                # Bulk delete for multiple messages
                await channel.delete_messages(messages)
                return len(messages)
                
        except discord.errors.HTTPException as e:
            if e.status == 429:  # Rate limited
                if attempt < max_retries:
                    # Calculate exponential backoff delay
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    print(f"Message deletion rate limited (attempt {attempt + 1}/{max_retries + 1}). Waiting {delay:.1f}s before retry...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    print(f"Message deletion max retries ({max_retries}) exceeded. Skipping batch of {len(messages)} messages.")
                    return 0  # Return 0 to indicate failure
            else:
                # Other HTTP error, don't retry
                raise e
                
        except Exception as e:
            # Other error, don't retry
            raise e
    
    return 0

@app_commands.context_menu(name="Verwijder Hieronder")
@has_role("The Council")
async def purge_below(interaction: discord.Interaction, message: discord.Message):
    try:
        await interaction.response.defer(ephemeral=True)
        messages_to_delete = []
        async for msg in interaction.channel.history(
            limit=None, oldest_first=False
        ):
            if msg.id == message.id:
                break
            messages_to_delete.append(msg)

        total_deleted = 0
        if messages_to_delete:
            # Batch delete messages in chunks of 100 with exponential backoff
            for i in range(0, len(messages_to_delete), 100):
                batch = messages_to_delete[i:i + 100]
                
                # Try to delete this batch with exponential backoff
                batch_deleted = await _delete_batch_with_backoff(interaction.channel, batch)
                total_deleted += batch_deleted
                
                # Add a small delay between batches to avoid rate limits
                if i + 100 < len(messages_to_delete):
                    await asyncio.sleep(1)

        embed = discord.Embed(
            title="Messages verwijderd Hieronder",
            description=f"{total_deleted} messages verwijderd onder de geselecteerde message.",
            color=discord.Color.green(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Log the action (need to access bot instance through interaction)
        if hasattr(interaction, 'client') and hasattr(interaction.client, 'log'):
            interaction.client.log.info(f"Purge below command used by {interaction.user.name} ({interaction.user.id}) in channel {interaction.channel.id}. Deleted {total_deleted} messages below message {message.id}")

    except discord.errors.Forbidden:
        embed = discord.Embed(
            title="Permissie Fout",
            description="Ik heb geen permissie om messages in dit channel te verwijderen.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except discord.errors.HTTPException as e:
        embed = discord.Embed(
            title="Fout",
            description=f"Verwijderen mislukt: {e}",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        embed = discord.Embed(
            title="Onverwachte Fout",
            description=f"Er is een onverwachte fout opgetreden: {e}",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ModCommands(bot))
    bot.tree.add_command(purge_below)