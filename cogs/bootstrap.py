import discord
from discord import app_commands
from discord.ext import commands


class Bootstrap(commands.Cog):
    """Bootstrap commands for initial setup."""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @app_commands.command(name="bootstrap_developer", description="Add first developer (only works if no developers exist)")
    @app_commands.describe(user="The user to make a developer")
    async def bootstrap_developer(self, interaction: discord.Interaction, user: discord.User):
        """Bootstrap the first developer - only works if no developers exist."""
        
        # Check if any developers already exist
        settings = await self.db.settings.find_one({"_id": "server_settings"}) or {}
        existing_devs = settings.get("developer_ids", [])
        
        if existing_devs:
            await interaction.response.send_message(
                "❌ Er zijn al ontwikkelaars geconfigureerd. Gebruik `/configure` om ontwikkelaars te beheren.", 
                ephemeral=True
            )
            return
        
        # Add the first developer
        await self.db.settings.update_one(
            {"_id": "server_settings"},
            {"$set": {"developer_ids": [user.id]}},
            upsert=True
        )
        
        # Reload developer IDs in the bot
        await self.bot.load_developer_ids()
        
        await interaction.response.send_message(
            f"✅ {user.mention} is nu de eerste ontwikkelaar! Ze kunnen nu `/configure` gebruiken om andere ontwikkelaars toe te voegen.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Bootstrap(bot))