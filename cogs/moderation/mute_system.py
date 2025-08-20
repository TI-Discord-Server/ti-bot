import datetime
import discord
from discord import app_commands
from discord.ext import commands
from utils.has_role import has_role
from utils.timezone import now_utc, format_local_time
from .moderation_utils import send_dm_embed, parse_duration, log_infraction, create_dm_embed
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

        dm_embed = create_dm_embed(
            "⚠️| Je bent gemute.",
            f"Reden: {reason}" + (f"\nDuration: {duration}" if scheduled else ""),
            discord.Color.dark_orange(),
            bot_icon_url
        )
        dm_sent = await send_dm_embed(member, dm_embed)

        try:
            await member.add_roles(muted_role, reason=reason)
            
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

        # Check if member is already muted
        if muted_role and muted_role in member.roles:
            # Get the mute infraction from database to show when they were muted
            try:
                mute_infraction = await self.infractions_collection.find_one({
                    "guild_id": guild.id,
                    "user_id": member.id,
                    "type": "mute"
                }, sort=[("timestamp", -1)])  # Get the most recent mute

                time_info = "for an unknown duration"
                if mute_infraction:
                    mute_time = datetime.datetime.fromisoformat(mute_infraction["timestamp"])
                    mute_time_formatted = discord.utils.format_dt(mute_time, 'F')
                    mute_time_relative = discord.utils.format_dt(mute_time, 'R')
                    time_info = f"sinds {mute_time_formatted} ({mute_time_relative})"
            except Exception as e:
                self.bot.log.error(f"Error fetching mute infraction: {e}")
                time_info = "for an unknown duration"

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
                mute_callback=self.execute_mute
            )
            
            await interaction.response.send_message(embed=embed, view=view)
            return
        
        # If not already muted, proceed with normal mute
        await self.execute_mute(interaction, member, reason)

    async def handle_unmute_command(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        """Handle the unmute command."""
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
        dm_embed = create_dm_embed(
            "⚠️ | Je bent geunmute.",
            f"Reden: {reason}",
            discord.Color.green(),
            bot_icon_url
        )

        dm_sent = await send_dm_embed(member, dm_embed)
        try:
            await member.remove_roles(muted_role, reason=reason)
            
            # Cancel any scheduled unmute for this user
            cancelled = await self.tasks.cancel_scheduled_unmute(guild.id, member.id)
            
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
            await log_infraction(
                self.infractions_collection,
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