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
        name="force_review", description="Force the review of confessions."
    )
    @app_commands.checks.has_role(1342591576764977223)
    async def force_review(self, interaction: discord.Interaction):
        await self.tasks.daily_review()
        await interaction.response.send_message(
            "Confession review has been forced.", ephemeral=True
        )
        self.bot.log.info(
            f"{interaction.user} heeft handmatig een confession review getriggerd."
        )

    @app_commands.command(
        name="force_post", description="Forceer het posten van confessions."
    )
    @app_commands.checks.has_role(1342591576764977223)
    async def force_post(self, interaction: discord.Interaction):
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

    @app_commands.command(
        name="get_confession_settings",
        description="Bekijk de huidige confession-instellingen (moderators only).",
    )
    @app_commands.checks.has_role(1342591576764977223)
    async def get_confession_settings(self, interaction: discord.Interaction):
        settings = await self.bot.db.settings.find_one({"_id": "confession_settings"})

        if not settings:
            await interaction.response.send_message(
                "⚠️ Er zijn nog geen confession instellingen opgeslagen.", ephemeral=True
            )
            self.bot.log.warning(
                "get_confession_settings werd opgevraagd, maar er zijn geen settings."
            )
            return

        post_times = settings.get("post_times", [])
        review_time = settings.get("review_time", "Niet ingesteld")
        limit = settings.get("daily_review_limit", "Niet ingesteld")

        embed = discord.Embed(
            title="📋 Huidige Confession Instellingen", color=discord.Color.blurple()
        )
        embed.add_field(
            name="📆 Review Tijd", value=f"`{review_time}` UTC", inline=False
        )
        embed.add_field(
            name="🕒 Post Tijd(en)",
            value=", ".join(f"`{t}`" for t in post_times) or "Geen tijden ingesteld",
            inline=False,
        )
        embed.add_field(
            name="📤 Aantal confessions per dag", value=f"`{limit}`", inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.bot.log.debug(
            f"{interaction.user} heeft get_confession_settings opgevraagd."
        )


async def setup(bot):
    await bot.add_cog(ConfessionCommands(bot))
