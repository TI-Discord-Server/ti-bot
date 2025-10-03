import discord
from discord import app_commands
from discord.ext import commands

from cogs.confessions.confession_tasks import ConfessionTasks


class ConfessionCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tasks = ConfessionTasks(bot)

    async def has_moderator_role(self, interaction: discord.Interaction) -> bool:
        """Check if user has moderator role."""
        settings = await self.bot.db.settings.find_one({"_id": "reports_settings"})
        if not settings or "moderator_role_id" not in settings:
            return interaction.user.guild_permissions.manage_guild

        moderator_role_id = settings["moderator_role_id"]
        return any(role.id == moderator_role_id for role in interaction.user.roles)

    @app_commands.command(name="force_review", description="Forceer de review van confessions.")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.has_role(760195356493742100)
    async def force_review(self, interaction: discord.Interaction):
        await self.tasks.daily_review()
        await interaction.response.send_message(
            "Confession beoordeling is geforceerd.", ephemeral=True
        )
        self.bot.log.info(f"{interaction.user} heeft handmatig een confession review getriggerd.")

    @app_commands.command(name="force_post", description="Forceer het posten van confessions.")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.has_role(760195356493742100)
    async def force_post(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Forceren van confession posting...", ephemeral=True
        )
        await self.tasks.run_post_approved()
        await interaction.followup.send(
            "Beoordeling en posting van confessions is geforceerd.", ephemeral=True
        )
        self.bot.log.info(f"{interaction.user} heeft handmatig een confession post getriggerd.")

    @app_commands.command(
        name="setup_submit_message",
        description="Post het submit confession bericht in het publieke kanaal.",
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.has_role(760195356493742100)
    async def setup_submit_message(self, interaction: discord.Interaction):
        public_channel_id = await self.tasks.get_public_channel_id()
        if not public_channel_id:
            self.bot.log.warning(
                f"Public channel not configured when {interaction.user.name} ({interaction.user.id}) tried to setup submit message"
            )
            await interaction.response.send_message(
                "❌ Publiek kanaal niet geconfigureerd. Gebruik `/configure` om het in te stellen.",
                ephemeral=True,
            )
            return

        public_channel = self.bot.get_channel(public_channel_id)
        if not public_channel:
            self.bot.log.error(
                f"Public channel {public_channel_id} not found when {interaction.user.name} ({interaction.user.id}) tried to setup submit message"
            )
            await interaction.response.send_message(
                "❌ Publiek kanaal niet gevonden.", ephemeral=True
            )
            return

        await interaction.response.send_message("Submit bericht wordt geplaatst...", ephemeral=True)

        try:
            await self.tasks._post_submit_message(public_channel)

            await interaction.followup.send(
                f"✅ Submit bericht succesvol geplaatst in {public_channel.mention}!",
                ephemeral=True,
            )
            self.bot.log.info(
                f"{interaction.user} heeft handmatig een submit bericht geplaatst in {public_channel.name}."
            )

        except Exception as e:
            self.bot.log.error(f"Error setting up submit message: {e}")
            await interaction.followup.send(
                f"❌ Er is een fout opgetreden bij het plaatsen van het submit bericht: {str(e)}",
                ephemeral=True,
            )


async def setup(bot):
    await bot.add_cog(ConfessionCommands(bot))
