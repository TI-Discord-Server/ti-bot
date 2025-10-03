import asyncio
import os
import sys

import discord
from discord import app_commands
from discord.ext import commands

from utils.has_admin import has_admin


class AdminCommands(commands.Cog, name="AdminCommands"):
    """Admin-only commands zoals sync en restart."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sync", description="Synchroniseer de slash commands met Discord.")
    @has_admin()
    async def sync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            synced = await self.bot.tree.sync()
            await interaction.followup.send(
                f"✅ Gesynchroniseerd: {len(synced)} commando's.", ephemeral=True
            )
            self.bot.log.info(
                f"/sync uitgevoerd door {interaction.user} - {len(synced)} commands gesynchroniseerd."
            )
        except Exception as e:
            self.bot.log.error(f"Sync mislukt: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Sync mislukt: {e}", ephemeral=True)

    @app_commands.command(name="restart", description="Herstart de bot.")
    @has_admin()
    async def restart(self, interaction: discord.Interaction):
        await interaction.response.send_message("♻️ Bot wordt herstart...", ephemeral=True)
        self.bot.log.info(f"/restart uitgevoerd door {interaction.user} - bot gaat herstarten.")

        # Kleine delay zodat Discord het antwoord nog kan tonen
        await asyncio.sleep(2)

        # Herstart via exec
        os.execv(sys.executable, ["python"] + sys.argv)


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
