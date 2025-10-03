import discord
from discord import app_commands
from discord.ext import commands


class examresults(commands.Cog, name="when_exam_results"):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.settings_id = "exam_results_settings"

    @app_commands.command(
        name="when_exam_results",
        description="When are the exam results published?",
    )
    async def examResults(self, interaction: discord.Interaction):
        settings = await self.db.settings.find_one({"_id": self.settings_id})
        if settings and "exam_result_date" in settings:
            exam_result_date = settings["exam_result_date"]
        else:
            exam_result_date = False

        if not exam_result_date:
            await interaction.response.send_message(
                "De datum voor examenresultaten is nog niet ingesteld. Vraag het aan een moderator."
            )
        else:
            await interaction.response.send_message(
                f"De examenresultaten worden gepubliceerd op: {exam_result_date}"
            )


async def setup(bot):
    await bot.add_cog(examresults(bot))
