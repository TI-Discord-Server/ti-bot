import discord
from discord.app_commands import (
    command,
)
from discord.ext import commands
from utils.has_admin import has_admin


class examresults(commands.Cog, name="when_exam_results"):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.settings_id = "exam_results_settings"

    @command(
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

    @command(
        name="set_exam_results",
        description="Set a new exam result date (Moderators only).",
    )
    @has_admin()
    async def setExamResults(self, interaction: discord.Interaction, new_date: str):
        # Update the exam result date in the settings collection
        await self.db.settings.update_one(
            {"_id": self.settings_id},  # Filter by the specific ID
            {"$set": {"exam_result_date": new_date}},  # Update or set the field
            upsert=True,  # Create the document if it doesn't exist
        )

        await interaction.response.send_message(
            f"Datum voor examenresultaten bijgewerkt naar: {new_date}"
        )

    @setExamResults.error
    async def setExamResults_error(
        self, interaction: discord.Interaction, error: commands.MissingPermissions
    ):
        if isinstance(error, commands.CheckFailure):
            await interaction.response.send_message(
                "Je hebt geen toestemming om dit commando te gebruiken.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(examresults(bot))
