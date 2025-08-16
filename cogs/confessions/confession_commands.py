import discord
from discord.ext import commands
from discord import app_commands
from cogs.confessions.confession_view import ConfessionView
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

    @app_commands.command(
        name="force_review", description="Forceer de review van confessions."
    )
    async def force_review(self, interaction: discord.Interaction):
        if not await self.has_moderator_role(interaction):
            await interaction.response.send_message(
                "Je hebt geen toestemming om dit commando te gebruiken.", ephemeral=True
            )
            return
            
        await self.tasks.daily_review()
        await interaction.response.send_message(
            "Confession beoordeling is geforceerd.", ephemeral=True
        )
        self.bot.log.info(
            f"{interaction.user} heeft handmatig een confession review getriggerd."
        )

    @app_commands.command(
        name="force_post", description="Forceer het posten van confessions."
    )
    async def force_post(self, interaction: discord.Interaction):
        if not await self.has_moderator_role(interaction):
            await interaction.response.send_message(
                "Je hebt geen toestemming om dit commando te gebruiken.", ephemeral=True
            )
            return
            
        await interaction.response.send_message(
            "Forceren van confession posting...", ephemeral=True
        )
        await self.tasks.run_post_approved()
        await interaction.followup.send(
            "Beoordeling en posting van confessions is geforceerd.", ephemeral=True
        )
        self.bot.log.info(
            f"{interaction.user} heeft handmatig een confession post getriggerd."
        )




async def setup(bot):
    await bot.add_cog(ConfessionCommands(bot))
