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


class TimeoutFallbackView(discord.ui.View):
    """View for confirming fallback to muted role when timeout exceeds 28 days."""
    
    def __init__(self, original_user: discord.Member, target_member: discord.Member, 
                 duration: str, reason: str, mute_callback=None):
        super().__init__(timeout=60.0)
        self.original_user = original_user
        self.target_member = target_member
        self.duration = duration
        self.reason = reason
        self.mute_callback = mute_callback
        self.responded = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the original command user to interact with the buttons."""
        if interaction.user.id != self.original_user.id:
            await interaction.response.send_message(
                "Only the person who ran the command can interact with these buttons.", 
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Yes, Use Muted Role", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_mute_fallback(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm using muted role as fallback."""
        if self.responded:
            return
        self.responded = True
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        # Update the message to show it's being processed
        embed = discord.Embed(
            title="Processing...",
            description=f"Using muted role for {self.target_member.mention} for {self.duration}...",
            color=discord.Color.yellow()
        )
        await interaction.response.edit_message(embed=embed, view=self)
        
        # Execute the mute callback with scheduled unmute
        if self.mute_callback:
            await self.mute_callback(interaction, self.target_member, self.reason, self.duration, scheduled=True)

    @discord.ui.button(label="No, Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_fallback(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the fallback operation."""
        if self.responded:
            return
        self.responded = True
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        embed = discord.Embed(
            title="Cancelled",
            description=f"The timeout operation for {self.target_member.mention} has been cancelled.",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        """Handle view timeout."""
        if not self.responded:
            # Disable all buttons
            for item in self.children:
                item.disabled = True


class OverwriteConfirmationView(discord.ui.View):
    """View for confirming overwrite of existing timeout/mute."""
    
    def __init__(self, original_user: discord.Member, target_member: discord.Member, 
                 action_type: str, new_duration: str = None, reason: str = None, 
                 timeout_callback=None, mute_callback=None):
        super().__init__(timeout=60.0)
        self.original_user = original_user
        self.target_member = target_member
        self.action_type = action_type
        self.new_duration = new_duration
        self.reason = reason
        self.timeout_callback = timeout_callback
        self.mute_callback = mute_callback
        self.responded = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the original command user to interact with the buttons."""
        if interaction.user.id != self.original_user.id:
            await interaction.response.send_message(
                "Only the person who ran the command can interact with these buttons.", 
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Yes, Overwrite", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm_overwrite(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm overwriting the existing timeout/mute."""
        if self.responded:
            return
        self.responded = True
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        # Update the message to show it's being processed
        embed = discord.Embed(
            title="Processing...",
            description=f"Overwriting existing {self.action_type} for {self.target_member.mention}...",
            color=discord.Color.yellow()
        )
        await interaction.response.edit_message(embed=embed, view=self)
        
        # Execute the appropriate callback
        if self.action_type == "timeout" and self.timeout_callback:
            await self.timeout_callback(interaction, self.target_member, self.new_duration, self.reason, overwrite=True)
        elif self.action_type == "mute" and self.mute_callback:
            await self.mute_callback(interaction, self.target_member, self.reason, overwrite=True)

    @discord.ui.button(label="No, Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_overwrite(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the overwrite operation."""
        if self.responded:
            return
        self.responded = True
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        embed = discord.Embed(
            title="Cancelled",
            description=f"The {self.action_type} operation for {self.target_member.mention} has been cancelled.",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        """Handle view timeout."""
        if not self.responded:
            # Disable all buttons
            for item in self.children:
                item.disabled = True





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
        
        # Start the unmute checker task
        self.unmute_task = None
        self.start_unmute_checker()

    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        if self.unmute_task and not self.unmute_task.done():
            self.unmute_task.cancel()

    def start_unmute_checker(self):
        """Start the background task to check for scheduled unmutes."""
        if self.unmute_task is None or self.unmute_task.done():
            self.unmute_task = asyncio.create_task(self.check_scheduled_unmutes())

    async def check_scheduled_unmutes(self):
        """Background task to check and process scheduled unmutes."""
        while True:
            try:
                current_time = datetime.datetime.utcnow()
                
                # Find all unmutes that should be processed
                expired_unmutes = await self.scheduled_unmutes_collection.find({
                    "unmute_at": {"$lte": current_time}
                }).to_list(length=None)
                
                for unmute_data in expired_unmutes:
                    try:
                        guild = self.bot.get_guild(unmute_data["guild_id"])
                        if not guild:
                            # Guild not found, remove the scheduled unmute
                            await self.scheduled_unmutes_collection.delete_one({"_id": unmute_data["_id"]})
                            continue
                        
                        member = guild.get_member(unmute_data["user_id"])
                        if not member:
                            # Member not found, remove the scheduled unmute
                            await self.scheduled_unmutes_collection.delete_one({"_id": unmute_data["_id"]})
                            continue
                        
                        # Get muted role
                        muted_role = discord.utils.get(guild.roles, name="Muted")
                        if muted_role and muted_role in member.roles:
                            # Remove muted role
                            await member.remove_roles(muted_role, reason="Scheduled unmute expired")
                            
                            # Send DM to user
                            try:
                                dm_embed = discord.Embed(
                                    title="🔓 | Je bent automatisch geunmute.",
                                    description=f"Je scheduled mute in {guild.name} is verlopen.",
                                    color=discord.Color.green(),
                                )
                                await member.send(embed=dm_embed)
                            except (discord.errors.Forbidden, discord.errors.HTTPException):
                                pass  # Couldn't send DM, but that's okay
                            
                            # Log the automatic unmute
                            try:
                                await self.log_infraction(
                                    guild.id, member.id, self.bot.user.id, "auto_unmute", 
                                    f"Scheduled unmute after {unmute_data.get('original_duration', 'unknown duration')}"
                                )
                            except Exception as e:
                                self.bot.log.error(f"Failed to log auto unmute infraction: {e}")
                        
                        # Remove the scheduled unmute from database
                        await self.scheduled_unmutes_collection.delete_one({"_id": unmute_data["_id"]})
                        
                    except Exception as e:
                        self.bot.log.error(f"Error processing scheduled unmute for user {unmute_data.get('user_id')}: {e}")
                        # Don't remove from database if there was an error, try again later
                
                # Wait 60 seconds before checking again
                await asyncio.sleep(60)
                
            except Exception as e:
                self.bot.log.error(f"Error in scheduled unmute checker: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def schedule_unmute(self, guild_id: int, user_id: int, unmute_at: datetime.datetime, 
                             original_duration: str, reason: str):
        """Schedule an unmute for a specific time."""
        unmute_data = {
            "guild_id": guild_id,
            "user_id": user_id,
            "unmute_at": unmute_at,
            "original_duration": original_duration,
            "reason": reason,
            "created_at": datetime.datetime.utcnow()
        }
        
        # Remove any existing scheduled unmute for this user in this guild
        await self.scheduled_unmutes_collection.delete_many({
            "guild_id": guild_id,
            "user_id": user_id
        })
        
        # Insert the new scheduled unmute
        await self.scheduled_unmutes_collection.insert_one(unmute_data)

    async def cancel_scheduled_unmute(self, guild_id: int, user_id: int):
        """Cancel a scheduled unmute for a user."""
        result = await self.scheduled_unmutes_collection.delete_many({
            "guild_id": guild_id,
            "user_id": user_id
        })
        return result.deleted_count > 0

    async def _execute_scheduled_mute(self, interaction: discord.Interaction, member: discord.Member,
                                     reason: str, duration: str, scheduled: bool = True):
        """Execute a mute operation with optional scheduled unmute."""
        guild = interaction.guild
        muted_role = discord.utils.get(guild.roles, name="Muted")

        if not muted_role:
            muted_role = await guild.create_role(
                name="Muted", reason="Muted role aangemaakt voor muting"
            )
            # Set up permissions for the muted role
            for channel in guild.channels:
                await channel.set_permissions(
                    muted_role,
                    send_messages=False,
                    speak=False,
                    add_reactions=False,
                    send_messages_in_threads=False,
                    create_public_threads=False,
                    create_private_threads=False,
                )

        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        timestamp = now_utc()
        
        # Calculate unmute time if scheduled
        unmute_at = None
        if scheduled:
            duration_timedelta = self.parse_duration(duration)
            if duration_timedelta:
                unmute_at = datetime.datetime.utcnow() + duration_timedelta

        dm_embed = discord.Embed(
            title=f"⚠️| Je bent gemute.",
            description=f"Reden: {reason}" + (f"\nDuration: {duration}" if scheduled else ""),
            color=discord.Color.dark_orange(),
        )
        dm_embed.set_footer(text=f"Tijd: {format_local_time(timestamp)}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)
        dm_sent = await self.send_dm_embed(member, dm_embed)

        try:
            await member.add_roles(muted_role, reason=reason)
            
            # Schedule unmute if requested
            if scheduled and unmute_at:
                await self.schedule_unmute(guild.id, member.id, unmute_at, duration, reason)
            
            embed = discord.Embed(
                title="Member gemute" + (" (Scheduled)" if scheduled else ""),
                description=f"{member.mention} is gemute" + (f" voor {duration}" if scheduled else "") + f". Reden: {reason}",
                color=discord.Color.green(),
            )
            
            if scheduled and unmute_at:
                embed.add_field(
                    name="Automatische Unmute",
                    value=f"{discord.utils.format_dt(unmute_at, 'F')} ({discord.utils.format_dt(unmute_at, 'R')})",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
            try:
                await self.log_infraction(
                    interaction.guild.id, member.id, interaction.user.id, 
                    "scheduled_mute" if scheduled else "mute", reason
                )
            except Exception as e:
                self.bot.log.error(f"Failed to log mute infraction for {member.name} ({member.id}): {e}")

        except discord.errors.Forbidden as e:
            self.bot.log.error(f"Permission denied when trying to mute {member.name} ({member.id}): {e}")
            embed = discord.Embed(
                title="Permissie Fout",
                description="Ik heb geen permissie om deze member te muten.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            self.bot.log.error(f"Unexpected error when trying to mute {member.name} ({member.id}): {e}", exc_info=True)
            embed = discord.Embed(
                title="Onverwachte Fout",
                description="Muten mislukt.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

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

        # Check if member is already muted
        if muted_role and muted_role in member.roles:
            # Get the mute infraction from database to show when they were muted
            try:
                mute_infraction = await self.infractions_collection.find_one({
                    "guild_id": guild.id,
                    "user_id": member.id,
                    "type": "mute"
                }, sort=[("timestamp", -1)])  # Get the most recent mute
                
                if mute_infraction:
                    mute_time = datetime.datetime.fromisoformat(mute_infraction["timestamp"])
                    mute_time_formatted = discord.utils.format_dt(mute_time, 'F')
                    mute_time_relative = discord.utils.format_dt(mute_time, 'R')
                    time_info = f"sinds {mute_time_formatted} ({mute_time_relative})"
                else:
                    time_info = "voor een onbekende tijd"
            except Exception:
                time_info = "voor een onbekende tijd"
            
            # Create confirmation embed
            embed = discord.Embed(
                title="⚠️ Member is al gemute",
                description=(
                    f"{member.mention} is al gemute {time_info}.\n\n"
                    f"Wil je de mute overschrijven met een nieuwe reden?"
                ),
                color=discord.Color.orange()
            )
            
            # Create view with confirmation buttons
            view = OverwriteConfirmationView(
                original_user=interaction.user,
                target_member=member,
                action_type="mute",
                reason=reason,
                mute_callback=self._execute_mute
            )
            
            await interaction.response.send_message(embed=embed, view=view)
            return
        
        # If not already muted, proceed with normal mute
        await self._execute_mute(interaction, member, reason)

    async def _execute_mute(self, interaction: discord.Interaction, member: discord.Member, 
                           reason: str, overwrite: bool = False):
        """Execute the mute operation."""
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
            
            if overwrite:
                await interaction.followup.send(embed=embed)
            else:
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
            if overwrite:
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.HTTPException:
            embed = discord.Embed(
                title="Fout",
                description="Muten mislukt.",
                color=discord.Color.red(),
            )
            if overwrite:
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
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
            
            # Cancel any scheduled unmute for this user
            cancelled = await self.cancel_scheduled_unmute(guild.id, member.id)
            
            embed = discord.Embed(
                title="Member geunmute",
                description=f"{member.mention} is geunmute. Reden: {reason}",
                color=discord.Color.green(),
            )
            
            if cancelled:
                embed.add_field(
                    name="Scheduled Unmute Cancelled",
                    value="Any scheduled automatic unmute has been cancelled.",
                    inline=False
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
        # Check if member is already timed out
        if member.timed_out_until and member.timed_out_until > discord.utils.utcnow():
            # Calculate remaining time
            remaining_time = member.timed_out_until - discord.utils.utcnow()
            
            # Format the remaining time in a human-readable way
            days = remaining_time.days
            hours, remainder = divmod(remaining_time.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            time_parts = []
            if days > 0:
                time_parts.append(f"{days} dag{'en' if days != 1 else ''}")
            if hours > 0:
                time_parts.append(f"{hours} uur")
            if minutes > 0:
                time_parts.append(f"{minutes} minuten")
            
            remaining_str = ", ".join(time_parts) if time_parts else "minder dan een minuut"
            
            # Create confirmation embed
            embed = discord.Embed(
                title="⚠️ Member is al getimed out",
                description=(
                    f"{member.mention} is al getimed out voor **{remaining_str}** "
                    f"en blijft getimed out tot {discord.utils.format_dt(member.timed_out_until, 'F')} "
                    f"({discord.utils.format_dt(member.timed_out_until, 'R')}).\n\n"
                    f"Wil je dit overschrijven met een nieuwe timeout van **{duration}**?"
                ),
                color=discord.Color.orange()
            )
            
            # Create view with confirmation buttons
            view = OverwriteConfirmationView(
                original_user=interaction.user,
                target_member=member,
                action_type="timeout",
                new_duration=duration,
                reason=reason,
                timeout_callback=self._execute_timeout
            )
            
            await interaction.response.send_message(embed=embed, view=view)
            return
        
        # If not already timed out, proceed with normal timeout
        await self._execute_timeout(interaction, member, duration, reason)

    async def _execute_timeout(self, interaction: discord.Interaction, member: discord.Member, 
                              duration: str, reason: str, overwrite: bool = False):
        """Execute the timeout operation."""
        duration_timedelta = self.parse_duration(duration)
        if not duration_timedelta:
            embed = discord.Embed(
                title="Fout",
                description="Invalid duration format. Gebruik voorbeelden zoals 1m, 5h, 1d, 1w, 1mo, 1y.",
                color=discord.Color.red(),
            )
            if overwrite:
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        timeout_until = discord.utils.utcnow() + duration_timedelta

        # Check if duration exceeds Discord's 28-day limit
        if duration_timedelta > datetime.timedelta(days=28):
            # Offer fallback to muted role
            embed = discord.Embed(
                title="⚠️ Timeout Duration Too Long",
                description=(
                    f"The requested timeout duration of **{duration}** exceeds Discord's maximum limit of 28 days.\n\n"
                    f"Would you like to use the **Muted role** instead? This will mute {member.mention} "
                    f"for the full duration of **{duration}** and automatically unmute them when the time expires."
                ),
                color=discord.Color.orange()
            )
            
            # Create view with fallback confirmation buttons
            view = TimeoutFallbackView(
                original_user=interaction.user,
                target_member=member,
                duration=duration,
                reason=reason,
                mute_callback=self._execute_scheduled_mute
            )
            
            if overwrite:
                await interaction.followup.send(embed=embed, view=view)
            else:
                await interaction.response.send_message(embed=embed, view=view)
            return

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
            
            if overwrite:
                await interaction.followup.send(embed=embed)
            else:
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
            if overwrite:
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)

    def parse_duration(self, duration_str: str) -> Optional[datetime.timedelta]:
        """Parse duration string and return timedelta. Supports m, h, d, w, mo, y units."""
        units = {
            "m": "minutes", 
            "h": "hours", 
            "d": "days",
            "w": "weeks",
            "mo": "months",
            "y": "years"
        }
        
        # Match pattern like 1m, 5h, 1d, 2w, 1mo, 1y
        match = re.match(r"(\d+)(m|h|d|w|mo|y)$", duration_str.lower())
        if not match:
            return None

        amount, unit = match.groups()
        amount = int(amount)
        
        # Handle months and years separately since timedelta doesn't support them directly
        if unit == "mo":
            # Approximate 1 month = 30 days
            return datetime.timedelta(days=amount * 30)
        elif unit == "y":
            # Approximate 1 year = 365 days
            return datetime.timedelta(days=amount * 365)
        else:
            unit_name = units[unit]
            return datetime.timedelta(**{unit_name: amount})

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
        infractions = await self.infractions_collection.find(
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