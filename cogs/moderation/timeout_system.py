import datetime

import discord

from .moderation_utils import (
    create_dm_embed,
    format_duration,
    log_infraction,
    parse_duration,
    send_dm_embed,
)
from .moderation_views import OverwriteConfirmationView, TimeoutFallbackView


class TimeoutSystem:
    """Handles timeout and untimeout operations."""

    def __init__(self, bot, infractions_collection, mute_system):
        self.bot = bot
        self.infractions_collection = infractions_collection
        self.mute_system = mute_system

    async def execute_timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: str,
        overwrite: bool = False,
    ):
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
                title="⚠️ Timeout Duur Te Lang",
                description=(
                    f"De gevraagde timeout duur van **{duration}** overschrijdt Discord's maximum limiet van 28 dagen.\n\n"
                    f"Wil je in plaats daarvan de **Muted role** gebruiken? Dit zal {member.mention} "
                    f"muten voor de volledige duur van **{duration}** en automatisch unmuten wanneer de tijd verloopt."
                ),
                color=discord.Color.orange(),
            )

            # Create view with fallback confirmation buttons
            view = TimeoutFallbackView(
                original_user=interaction.user,
                target_member=member,
                duration=duration,
                reason=reason,
                mute_callback=self.mute_system.execute_scheduled_mute,
            )

            if overwrite:
                await interaction.followup.send(embed=embed, view=view)
            else:
                await interaction.response.send_message(embed=embed, view=view)
            return

        try:
            await member.timeout(timeout_until, reason=reason)

            # Use the original requested duration for consistency
            # (member.timed_out_until may contain stale/expired data)
            duration_str = format_duration(duration_timedelta)
            actual_timeout_until = timeout_until

            # Send DM with actual timeout information
            bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
            dm_embed = create_dm_embed(
                "⚠️ | Je bent getimed out.",
                f"Reden: {reason}\nDuration: {duration_str}\nEindigt: {discord.utils.format_dt(actual_timeout_until, 'F')} ({discord.utils.format_dt(actual_timeout_until, 'R')})",
                discord.Color.dark_orange(),
                bot_icon_url,
            )
            await send_dm_embed(member, dm_embed)

            embed = discord.Embed(
                title="Member Timeout",
                description=f"{member.mention} is getimed out voor **{duration_str}**. Reden: {reason}",
                color=discord.Color.green(),
            )

            # Add precise timeout end time
            embed.add_field(
                name="Timeout Eindigt",
                value=f"{discord.utils.format_dt(actual_timeout_until, 'F')} ({discord.utils.format_dt(actual_timeout_until, 'R')})",
                inline=False,
            )

            if overwrite:
                await interaction.followup.send(embed=embed)
            else:
                await interaction.response.send_message(embed=embed)

            try:
                await log_infraction(
                    self.infractions_collection,
                    interaction.guild.id,
                    member.id,
                    interaction.user.id,
                    "timeout",
                    f"{reason} (duur: {duration_str})",
                )
            except Exception as e:
                self.bot.log.error(
                    f"Failed to log timeout infraction for {member.name} ({member.id}): {e}"
                )

        except discord.errors.Forbidden as e:
            self.bot.log.error(
                f"Permission denied when trying to timeout {member.name} ({member.id}): {e}"
            )
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
            self.bot.log.error(
                f"HTTP error when trying to timeout {member.name} ({member.id}): {e}"
            )
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
            self.bot.log.error(
                f"Unexpected error when trying to timeout {member.name} ({member.id}): {e}",
                exc_info=True,
            )
            embed = discord.Embed(
                title="Onverwachte Fout",
                description=f"Er is een onverwachte fout opgetreden bij het timeouten: {str(e)}",
                color=discord.Color.red(),
            )
            if overwrite:
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)

    async def handle_timeout_command(
        self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: str
    ):
        """Handle the timeout command with overwrite confirmation."""
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
                current_punishment_info.append(
                    f"**Discord Timeout** voor {remaining_str} (tot {discord.utils.format_dt(member.timed_out_until, 'F')})"
                )

            if has_muted_role:
                # Check if there's a scheduled unmute
                try:
                    scheduled_unmute = (
                        await self.mute_system.tasks.scheduled_unmutes_collection.find_one(
                            {"guild_id": guild.id, "user_id": member.id}
                        )
                    )

                    if scheduled_unmute:
                        unmute_time = scheduled_unmute["unmute_at"]
                        current_punishment_info.append(
                            f"**Muted Role** (scheduled unmute: {discord.utils.format_dt(unmute_time, 'F')} - {discord.utils.format_dt(unmute_time, 'R')})"
                        )
                    else:
                        current_punishment_info.append(
                            "**Muted Role** (permanent/manual unmute required)"
                        )
                except Exception as e:
                    self.bot.log.error(f"Error checking scheduled unmute: {e}")
                    current_punishment_info.append("**Muted Role** (status unknown)")

            punishment_description = "\n".join(current_punishment_info)

            # Create confirmation embed
            embed = discord.Embed(
                title="⚠️ Member heeft al een straf",
                description=(
                    f"{member.mention} heeft momenteel:\n{punishment_description}\n\n"
                    f"Wil je dit overschrijven met een nieuwe timeout van **{duration}**?\n\n"
                    f"**Note:** Dit zal alle huidige straffen verwijderen en vervangen door de nieuwe timeout."
                ),
                color=discord.Color.orange(),
            )

            # Create view with confirmation buttons
            view = OverwriteConfirmationView(
                original_user=interaction.user,
                target_member=member,
                action_type="timeout",
                new_duration=duration,
                reason=reason,
                timeout_callback=self.execute_timeout_with_cleanup,
            )

            await interaction.response.send_message(embed=embed, view=view)
            return

        # If no existing punishment, proceed with normal timeout
        await self.execute_timeout(interaction, member, duration, reason)

    async def execute_timeout_with_cleanup(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: str,
        overwrite: bool = False,
    ):
        """Execute timeout after cleaning up any existing punishments."""
        guild = interaction.guild
        muted_role = discord.utils.get(guild.roles, name="Muted")

        # Clean up existing punishments
        cleanup_actions = []

        # Remove muted role if present
        if muted_role and muted_role in member.roles:
            try:
                await member.remove_roles(muted_role, reason=f"Replacing with timeout: {reason}")
                cleanup_actions.append("Removed muted role")
            except Exception as e:
                self.bot.log.error(
                    f"Failed to remove muted role from {member.name} ({member.id}): {e}"
                )

        # Cancel any scheduled unmute
        try:
            cancelled = await self.mute_system.tasks.cancel_scheduled_unmute(guild.id, member.id)
            if cancelled:
                cleanup_actions.append("Geplande unmute geannuleerd")
        except Exception as e:
            self.bot.log.error(
                f"Failed to cancel scheduled unmute for {member.name} ({member.id}): {e}"
            )

        # Remove existing timeout (this will be replaced by the new one)
        if member.timed_out_until and member.timed_out_until > discord.utils.utcnow():
            try:
                await member.timeout(None, reason=f"Clearing for new timeout: {reason}")
                cleanup_actions.append("Cleared existing timeout")
            except Exception as e:
                self.bot.log.error(
                    f"Failed to clear existing timeout for {member.name} ({member.id}): {e}"
                )

        # Log cleanup actions
        if cleanup_actions:
            self.bot.log.info(
                f"Cleaned up existing punishments for {member.name} ({member.id}): {', '.join(cleanup_actions)}"
            )

        # Now apply the new timeout
        await self.execute_timeout(interaction, member, duration, reason, overwrite=True)

    async def handle_untimeout_command(
        self, interaction: discord.Interaction, member: discord.Member, reason: str
    ):
        """Handle the untimeout command - removes both timeout and muted role if present."""
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
            # Remove timeout if present
            if has_timeout:
                await member.timeout(None, reason=reason)
                removed_punishments.append("timeout")

            # Remove muted role if present
            if has_muted_role:
                await member.remove_roles(muted_role, reason=reason)
                removed_punishments.append("muted role")

            # Cancel any scheduled unmute
            cancelled = await self.mute_system.tasks.cancel_scheduled_unmute(guild.id, member.id)
            if cancelled:
                removed_punishments.append("geplande unmute")

            punishment_text = " en ".join(removed_punishments)

            # Send DM only after successful removal
            bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
            dm_embed = create_dm_embed(
                f"Je straffen zijn verwijderd in {interaction.guild.name}",
                f"Reden: {reason}",
                discord.Color.green(),
                bot_icon_url,
            )
            await send_dm_embed(member, dm_embed)

            embed = discord.Embed(
                title="Straffen Verwijderd",
                description=f"{member.mention} - {punishment_text} verwijderd. Reden: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)

            # Log the action
            await log_infraction(
                self.infractions_collection,
                interaction.guild.id,
                member.id,
                interaction.user.id,
                "untimeout",
                f"{reason} (verwijderd: {punishment_text})",
            )

        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permissie Fout",
                description="Ik heb geen permissie om straffen van deze member te verwijderen.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            self.bot.log.error(f"Error removing punishments from {member.name} ({member.id}): {e}")
            embed = discord.Embed(
                title="Fout",
                description="Er is een fout opgetreden bij het verwijderen van de straffen.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
