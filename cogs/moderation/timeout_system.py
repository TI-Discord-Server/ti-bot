import datetime
import discord
from discord import app_commands
from discord.ext import commands
from utils.has_role import has_role
from utils.timezone import now_utc, format_local_time
from .moderation_utils import send_dm_embed, parse_duration, log_infraction, create_dm_embed
from .moderation_views import OverwriteConfirmationView, TimeoutFallbackView


class TimeoutSystem:
    """Handles timeout and untimeout operations."""
    
    def __init__(self, bot, infractions_collection, mute_system):
        self.bot = bot
        self.infractions_collection = infractions_collection
        self.mute_system = mute_system

    async def execute_timeout(self, interaction: discord.Interaction, member: discord.Member, 
                             duration: str, reason: str, overwrite: bool = False):
        """Execute the timeout operation."""
        duration_timedelta = parse_duration(duration)
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
                mute_callback=self.mute_system.execute_scheduled_mute
            )
            
            if overwrite:
                await interaction.followup.send(embed=embed, view=view)
            else:
                await interaction.response.send_message(embed=embed, view=view)
            return

        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        dm_embed = create_dm_embed(
            "⚠️ | Je bent getimed out.",
            f"Reden: {reason}\nDuration: {duration}",
            discord.Color.dark_orange(),
            bot_icon_url
        )
        dm_sent = await send_dm_embed(member, dm_embed)
        
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
                
            try:
                await log_infraction(
                    self.infractions_collection,
                    interaction.guild.id, member.id, interaction.user.id, "timeout", reason
                )
            except Exception as e:
                self.bot.log.error(f"Failed to log timeout infraction for {member.name} ({member.id}): {e}")

        except discord.errors.Forbidden as e:
            self.bot.log.error(f"Permission denied when trying to timeout {member.name} ({member.id}): {e}")
            embed = discord.Embed(
                title="Permissie Fout",
                description="Ik heb geen permissie om deze member te timeouten.",
                color=discord.Color.red(),
            )
            if overwrite:
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.HTTPException as e:
            self.bot.log.error(f"HTTP error when trying to timeout {member.name} ({member.id}): {e}")
            embed = discord.Embed(
                title="Discord API Fout",
                description=f"Timeout mislukt door Discord API fout: {str(e)}",
                color=discord.Color.red(),
            )
            if overwrite:
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            self.bot.log.error(f"Unexpected error when trying to timeout {member.name} ({member.id}): {e}", exc_info=True)
            embed = discord.Embed(
                title="Onverwachte Fout",
                description=f"Er is een onverwachte fout opgetreden bij het timeouten: {str(e)}",
                color=discord.Color.red(),
            )
            if overwrite:
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)

    async def handle_timeout_command(self, interaction: discord.Interaction, member: discord.Member, 
                                   duration: str, reason: str):
        """Handle the timeout command with overwrite confirmation."""
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
                timeout_callback=self.execute_timeout
            )
            
            await interaction.response.send_message(embed=embed, view=view)
            return
        
        # If not already timed out, proceed with normal timeout
        await self.execute_timeout(interaction, member, duration, reason)

    async def handle_untimeout_command(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        """Handle the untimeout command."""
        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        dm_embed = create_dm_embed(
            f"Je timeout is verwijderd in {interaction.guild.name}",
            f"Reden: {reason}",
            discord.Color.green(),
            bot_icon_url
        )

        dm_sent = await send_dm_embed(member, dm_embed)
        try:
            await member.timeout(None, reason=reason)
            embed = discord.Embed(
                title="Member untimeout",
                description=f"{member.mention} is geuntimeout. Reden: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
            await log_infraction(
                self.infractions_collection,
                interaction.guild.id, member.id, interaction.user.id, "untimeout", reason
            )
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permissie Fout",
                description="Ik heb geen permissie om deze member te untimeouten.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)