import discord
from discord.app_commands import (
    command,
)
from discord.ext import commands


class examresults(commands.Cog, name="when_exam_results"):
    def __init__(self, bot):
        self.bot = bot

    @command(
        name="when_exam_results",
        description="When are the exam results published?",
    )
    async def examResults(self, interaction: discord.Interaction):
        await interaction.response.send_message("7 februari 2025 om 12:00 uur CET")


async def setup(bot):
    n = examresults(bot)
    await bot.add_cog(n)
