import datetime
import discord
from discord import app_commands
from discord.ext import commands
from utils.has_role import has_role
from utils.timezone import now_utc, format_local_time
from .moderation_utils import send_dm_embed, parse_duration, log_infraction, create_dm_embed, format_duration
from .moderation_views import OverwriteConfirmationView


class MuteSystem:
    """Handles mute and unmute operations."""
    
    def __init__(self, bot, infractions_collection, tasks):
        self.bot = bot
        self.infractions_collection = infractions_collection
        self.tasks = tasks

    async def execute_mute(self, interaction: discord.Interaction, member: discord.Member,
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
        dm_embed = create_dm_embed(
            "⚠️| Je bent gemute.",
            f"Reden: {reason}",
            discord.Color.dark_gray(),
            bot_icon_url
        )

        dm_sent = await send_dm_embed(member, dm_embed)
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
                
            await log_infraction(
                self.infractions_collection,
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

    async def execute_scheduled_mute(self, interaction: discord.Interaction, member: discord.Member,
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
        
        # Calculate unmute time if scheduled
        unmute_at = None
        if scheduled:
            duration_timedelta = parse_duration(duration)
            if duration_timedelta:
                unmute_at = datetime.datetime.utcnow() + duration_timedelta

        try:
            await member.add_roles(muted_role, reason=reason)
            
            # Send DM only after successful mute
            dm_embed = create_dm_embed(
                "⚠️| Je bent gemute.",
                f"Reden: {reason}" + (f"\nDuration: {duration}" if scheduled else ""),
                discord.Color.dark_orange(),
                bot_icon_url
            )
            dm_sent = await send_dm_embed(member, dm_embed)
            
            # Schedule unmute if requested
            if scheduled and unmute_at:
                await self.tasks.schedule_unmute(guild.id, member.id, unmute_at, duration, reason)
            
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
                await log_infraction(
                    self.infractions_collection,
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

    async def handle_mute_command(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        """Handle the mute command with overwrite confirmation."""
        guild = interaction.guild
        muted_role = discord.utils.get(guild.roles, name="Muted")
        
        # Check if member has any existing punishment (timeout or muted role)
        has_timeout = member.timed_out_until and member.timed_out_until > discord.utils.utcnow()
        has_muted_role = muted_role and muted_role in member.roles

        if has_timeout or has_muted_role:
            # Determine what type of punishment they currently have
            current_punishment_info = []
            
            if has_timeout:
                # Calculate remaining timeout time
                remaining_time = member.timed_out_until - discord.utils.utcnow()
                remaining_str = format_duration(remaining_time)
                current_punishment_info.append(f"**Discord Timeout** voor {remaining_str} (tot {discord.utils.format_dt(member.timed_out_until, 'F')})")
            
            if has_muted_role:
                # Get the mute infraction from database to show when they were muted
                try:
                    mute_infraction = await self.infractions_collection.find_one({
                        "guild_id": guild.id,
                        "user_id": member.id,
                        "type": {"$in": ["mute", "scheduled_mute"]}
                    }, sort=[("timestamp", -1)])  # Get the most recent mute

                    if mute_infraction:
                        mute_time = datetime.datetime.fromisoformat(mute_infraction["timestamp"])
                        mute_time_formatted = discord.utils.format_dt(mute_time, 'F')
                        mute_time_relative = discord.utils.format_dt(mute_time, 'R')
                        time_info = f"sinds {mute_time_formatted} ({mute_time_relative})"
                    else:
                        time_info = "for an unknown duration"
                        
                    # Check if there's a scheduled unmute
                    scheduled_unmute = await self.tasks.scheduled_unmutes_collection.find_one({
                        "guild_id": guild.id,
                        "user_id": member.id
                    })
                    
                    if scheduled_unmute:
                        unmute_time = scheduled_unmute["unmute_at"]
                        current_punishment_info.append(f"**Muted Role** {time_info} (scheduled unmute: {discord.utils.format_dt(unmute_time, 'F')} - {discord.utils.format_dt(unmute_time, 'R')})")
                    else:
                        current_punishment_info.append(f"**Muted Role** {time_info} (permanent/manual unmute required)")
                        
                except Exception as e:
                    self.bot.log.error(f"Error fetching mute infraction: {e}")
                    current_punishment_info.append("**Muted Role** (status unknown)")
            
            punishment_description = "\n".join(current_punishment_info)

            # Create confirmation embed
            embed = discord.Embed(
                title="⚠️ Member heeft al een straf",
                description=(
                    f"{member.mention} heeft momenteel:\n{punishment_description}\n\n"
                    f"Wil je dit overschrijven met een nieuwe mute?\n\n"
                    f"**Note:** Dit zal alle huidige straffen verwijderen en vervangen door de nieuwe mute."
                ),
                color=discord.Color.orange()
            )
            
            # Create view with confirmation buttons
            view = OverwriteConfirmationView(
                original_user=interaction.user,
                target_member=member,
                action_type="mute",
                reason=reason,
                mute_callback=self.execute_mute_with_cleanup
            )
            
            await interaction.response.send_message(embed=embed, view=view)
            return
        
        # If no existing punishment, proceed with normal mute
        await self.execute_mute(interaction, member, reason)

    async def execute_mute_with_cleanup(self, interaction: discord.Interaction, member: discord.Member,
                                      reason: str, overwrite: bool = False):
        """Execute mute after cleaning up any existing punishments."""
        guild = interaction.guild
        
        # Clean up existing punishments
        cleanup_actions = []
        
        # Remove existing timeout if present
        if member.timed_out_until and member.timed_out_until > discord.utils.utcnow():
            try:
                await member.timeout(None, reason=f"Replacing with mute: {reason}")
                cleanup_actions.append("Removed existing timeout")
            except Exception as e:
                self.bot.log.error(f"Failed to remove timeout from {member.name} ({member.id}): {e}")
        
        # Cancel any scheduled unmute (will be replaced if this is a scheduled mute)
        try:
            cancelled = await self.tasks.cancel_scheduled_unmute(guild.id, member.id)
            if cancelled:
                cleanup_actions.append("Cancelled scheduled unmute")
        except Exception as e:
            self.bot.log.error(f"Failed to cancel scheduled unmute for {member.name} ({member.id}): {e}")
        
        # Log cleanup actions
        if cleanup_actions:
            self.bot.log.info(f"Cleaned up existing punishments for {member.name} ({member.id}): {', '.join(cleanup_actions)}")
        
        # Now apply the new mute
        await self.execute_mute(interaction, member, reason, overwrite=True)

    async def handle_unmute_command(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        """Handle the unmute command - removes both muted role and timeout if present."""
        guild = interaction.guild
        muted_role = discord.utils.get(guild.roles, name="Muted")
        
        # Check what punishments the member currently has
        has_timeout = member.timed_out_until and member.timed_out_until > discord.utils.utcnow()
        has_muted_role = muted_role and muted_role in member.roles
        
        if not has_timeout and not has_muted_role:
            embed = discord.Embed(
                title="Geen Straf Actief",
                description=f"{member.mention} heeft geen actieve timeout of mute.",
                color=discord.Color.orange(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Track what we're removing
        removed_punishments = []
        
        try:
            # Remove muted role if present
            if has_muted_role:
                await member.remove_roles(muted_role, reason=reason)
                removed_punishments.append("muted role")
            
            # Remove timeout if present
            if has_timeout:
                await member.timeout(None, reason=reason)
                removed_punishments.append("timeout")
            
            # Cancel any scheduled unmute for this user
            cancelled = await self.tasks.cancel_scheduled_unmute(guild.id, member.id)
            if cancelled:
                removed_punishments.append("scheduled unmute")
            
            punishment_text = " and ".join(removed_punishments)
            
            # Send DM only after successful removal
            bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
            dm_embed = create_dm_embed(
                "⚠️ | Je straffen zijn verwijderd.",
                f"Reden: {reason}",
                discord.Color.green(),
                bot_icon_url
            )
            dm_sent = await send_dm_embed(member, dm_embed)
            
            embed = discord.Embed(
                title="Straffen Verwijderd",
                description=f"{member.mention} - {punishment_text} verwijderd. Reden: {reason}",
                color=discord.Color.green(),
            )
            
            await interaction.response.send_message(embed=embed)
            await log_infraction(
                self.infractions_collection,
                interaction.guild.id, member.id, interaction.user.id, "unmute", 
                f"{reason} (removed: {punishment_text})"
            )
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permissie Fout",
                description="Ik heb geen permissie om straffen van deze member te verwijderen.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.HTTPException:
            embed = discord.Embed(
                title="Fout",
                description="Straffen verwijderen mislukt.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            self.bot.log.error(f"Error removing punishments from {member.name} ({member.id}): {e}")
            embed = discord.Embed(
                title="Onverwachte Fout",
                description="Er is een onverwachte fout opgetreden bij het verwijderen van de straffen.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)