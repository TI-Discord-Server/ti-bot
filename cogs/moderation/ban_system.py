import datetime

import discord

from utils.timezone import LOCAL_TIMEZONE

from .moderation_utils import (
    log_infraction,
    parse_duration,
)


class BanSystem:
    """Handles ban and unban operations."""

    def __init__(self, bot, infractions_collection, tasks):
        self.bot = bot
        self.infractions_collection = infractions_collection
        self.tasks = tasks

    async def execute_ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
        duration: str = None,
    ):
        """Execute a ban, permanent of tijdelijk."""

        # 1️⃣ DM versturen met reden + duur
        dm_success = False
        try:
            channel = await member.create_dm()

            # Mogelijke unban aanvraag knop
            view = discord.ui.View()
            settings = await self.bot.db.settings.find_one({"_id": "mod_settings"})
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
                    description=f"Je bent gebanned van **{interaction.guild.name}**.\n"
                    f"Reden: {reason}\n" + (f"⏳ Duur: {duration}" if duration else "🛑 Permanent"),
                    color=discord.Color.gold(),
                ),
                view=view,
            )
            dm_success = True
        except Exception as e:
            self.bot.log.warning(f"Kon geen DM sturen naar {member.name}: {e}")

        # 2️⃣ Duration checken → plan unban indien tijdelijk
        unban_at = None
        if duration:
            td = parse_duration(duration)
            if td:
                unban_at = datetime.datetime.now(LOCAL_TIMEZONE) + td
                await self.tasks.schedule_unban(
                    guild_id=interaction.guild.id,
                    user_id=member.id,
                    unban_at=unban_at,
                    original_duration=duration,
                    reason=f"Automatisch einde tijdelijke ban ({duration})",
                )
            else:
                await interaction.followup.send(
                    "❌ Ongeldige duur opgegeven. Gebruik bijv. `1d`, `2w`, `3mo`.",
                    ephemeral=True,
                )
                return

        # 3️⃣ Ban uitvoeren
        try:
            await member.ban(reason=reason)
            self.bot.log.info(
                f"User {member} ({member.id}) banned door {interaction.user} ({interaction.user.id}). Reden: {reason}"
            )

            embed = discord.Embed(
                title="✅ Member gebanned",
                description=f"{member.mention} is gebanned.\nReden: {reason}\n"
                + (f"⏳ Duur: {duration}" if duration else "🛑 Permanent"),
                color=discord.Color.green(),
            )
            embed.set_footer(
                text=(
                    "Gebruiker geïnformeerd via DM."
                    if dm_success
                    else "Kon gebruiker niet via DM informeren."
                )
            )
            await interaction.followup.send(embed=embed)

            # Loggen in DB
            await log_infraction(
                self.infractions_collection,
                interaction.guild.id,
                member.id,
                interaction.user.id,
                "ban",
                reason + (f" (duur: {duration})" if duration else " (permanent)"),
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Geen permissies om deze gebruiker te bannen.",
                ephemeral=True,
            )
        except Exception as e:
            self.bot.log.error(f"Fout bij bannen: {e}", exc_info=True)
            await interaction.followup.send("❌ Bannen mislukt door een fout.", ephemeral=True)

    async def execute_unban(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        reason: str,
    ):
        """Unban een gebruiker en log de actie."""
        try:
            await interaction.guild.unban(user, reason=reason)
            self.bot.log.info(
                f"User {user} ({user.id}) unbanned door {interaction.user} ({interaction.user.id}). Reden: {reason}"
            )

            embed = discord.Embed(
                title="Gebruiker unbanned",
                description=f"{user.mention} is unbanned. Reden: {reason}",
                color=discord.Color.green(),
            )
            await interaction.followup.send(embed=embed)

            await log_infraction(
                self.infractions_collection,
                interaction.guild.id,
                user.id,
                interaction.user.id,
                "unban",
                reason,
            )

            # Eventuele geplande unban verwijderen
            cancelled = await self.tasks.cancel_scheduled_unban(interaction.guild.id, user.id)
            if cancelled:
                self.bot.log.info(f"Geplande unban voor {user} ({user.id}) geannuleerd.")

        except discord.NotFound:
            await interaction.followup.send(
                f"❌ Gebruiker {user.mention} is niet gebanned.",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Ik heb geen permissie om deze gebruiker te unbannen.",
                ephemeral=True,
            )
        except Exception as e:
            self.bot.log.error(f"Fout bij unbannen: {e}", exc_info=True)
            await interaction.followup.send("❌ Unbannen mislukt door een fout.", ephemeral=True)
