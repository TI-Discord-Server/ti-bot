import discord
from discord import app_commands
from discord.ext import commands


class ping(commands.Cog, name="ping"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ping",
        description="Krijg de latentie van de bot.",
    )
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! {round(self.bot.latency * 1000)}ms")


async def setup(bot):
    n = ping(bot)
    await bot.add_cog(n)
