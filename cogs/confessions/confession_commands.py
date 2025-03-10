import discord
from discord.ext import commands
from discord import app_commands
from cogs.confessions.confession_view import ConfessionView
from cogs.confessions.confession_tasks import ConfessionTasks


class ConfessionCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tasks = ConfessionTasks(bot)

    @app_commands.command(
        name="setup_confessions",
        description="Set up the confession button in the public channel.",
    )
    @app_commands.checks.has_role(1342591576764977223)
    async def setup_confessions(self, interaction: discord.Interaction):
        view = ConfessionView(self.bot)
        await interaction.response.send_message(
            "Click the button below to submit a confession:", view=view
        )

    @app_commands.command(
        name="force_review", description="Force the review of confessions."
    )
    @app_commands.checks.has_role(1342591576764977223)
    async def force_review(self, interaction: discord.Interaction):
        await self.tasks.daily_review()
        await interaction.response.send_message(
            "Confession review has been forced.", ephemeral=True
        )

    @app_commands.command(
        name="force_post", description="Force the posting of reviewed confessions."
    )
    @app_commands.checks.has_role(1342591576764977223)
    async def force_post(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Forcing confession posting...", ephemeral=True
        )
        await self.tasks.run_post_approved()
        await interaction.followup.send("Confessions have been posted.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ConfessionCommands(bot))
