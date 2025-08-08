import discord
from discord.ext import commands
from discord import app_commands
from utils.has_admin import has_admin


class DeveloperManagement(commands.Cog):
    """Developer management commands with user autocomplete."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="add_developer", description="Add a developer to the bot (Admin only)")
    @app_commands.describe(user="The user to add as a developer")
    async def add_developer(self, interaction: discord.Interaction, user: discord.Member):
        """Add a developer using Discord's user autocomplete."""
        # Check if user has admin permissions
        if not any(r.permissions.administrator for r in interaction.user.roles):
            await interaction.response.send_message("❌ Je hebt geen administrator rechten om deze command te gebruiken.", ephemeral=True)
            return
        
        try:
            # Get current developer IDs
            settings = await self.bot.db.settings.find_one({"_id": "server_settings"}) or {}
            dev_ids = settings.get("developer_ids", [])
            
            if user.id in dev_ids:
                await interaction.response.send_message(f"❌ {user.mention} is al een ontwikkelaar.", ephemeral=True)
                return
            
            # Add the new developer
            dev_ids.append(user.id)
            
            await self.bot.db.settings.update_one(
                {"_id": "server_settings"},
                {"$set": {"developer_ids": dev_ids}},
                upsert=True
            )
            
            embed = discord.Embed(
                title="✅ Ontwikkelaar Toegevoegd",
                description=f"{user.mention} is toegevoegd als ontwikkelaar.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="👨‍💻 Nieuwe Ontwikkelaar",
                value=f"**Naam:** {user.display_name}\n**ID:** `{user.id}`",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            self.bot.log.error(f"Error adding developer: {e}", exc_info=True)
            await interaction.response.send_message("❌ Er is een fout opgetreden bij het toevoegen van de ontwikkelaar.", ephemeral=True)
    
    @app_commands.command(name="remove_developer", description="Remove a developer from the bot (Admin only)")
    @app_commands.describe(user="The user to remove as a developer")
    async def remove_developer(self, interaction: discord.Interaction, user: discord.Member):
        """Remove a developer using Discord's user autocomplete."""
        # Check if user has admin permissions
        if not any(r.permissions.administrator for r in interaction.user.roles):
            await interaction.response.send_message("❌ Je hebt geen administrator rechten om deze command te gebruiken.", ephemeral=True)
            return
        
        try:
            # Get current developer IDs
            settings = await self.bot.db.settings.find_one({"_id": "server_settings"}) or {}
            dev_ids = settings.get("developer_ids", [])
            
            if user.id not in dev_ids:
                await interaction.response.send_message(f"❌ {user.mention} is geen ontwikkelaar.", ephemeral=True)
                return
            
            # Remove the developer
            dev_ids.remove(user.id)
            
            await self.bot.db.settings.update_one(
                {"_id": "server_settings"},
                {"$set": {"developer_ids": dev_ids}},
                upsert=True
            )
            
            embed = discord.Embed(
                title="✅ Ontwikkelaar Verwijderd",
                description=f"{user.mention} is verwijderd als ontwikkelaar.",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="👨‍💻 Verwijderde Ontwikkelaar",
                value=f"**Naam:** {user.display_name}\n**ID:** `{user.id}`",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            self.bot.log.error(f"Error removing developer: {e}", exc_info=True)
            await interaction.response.send_message("❌ Er is een fout opgetreden bij het verwijderen van de ontwikkelaar.", ephemeral=True)
    
    @app_commands.command(name="list_developers", description="List all current developers")
    async def list_developers(self, interaction: discord.Interaction):
        """List all current developers with names and IDs."""
        try:
            # Get current developer IDs
            settings = await self.bot.db.settings.find_one({"_id": "server_settings"}) or {}
            dev_ids = settings.get("developer_ids", [])
            
            if not dev_ids:
                embed = discord.Embed(
                    title="👨‍💻 Ontwikkelaars",
                    description="Geen ontwikkelaars ingesteld.",
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed)
                return
            
            embed = discord.Embed(
                title="👨‍💻 Huidige Ontwikkelaars",
                description=f"Er zijn {len(dev_ids)} ontwikkelaars ingesteld:",
                color=discord.Color.blue()
            )
            
            dev_list = []
            for dev_id in dev_ids:
                user = self.bot.get_user(dev_id)
                if user:
                    dev_list.append(f"• **{user.display_name}** (`{user.id}`)")
                else:
                    dev_list.append(f"• **Onbekende gebruiker** (`{dev_id}`)")
            
            embed.add_field(
                name="📋 Lijst",
                value="\n".join(dev_list),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            self.bot.log.error(f"Error listing developers: {e}", exc_info=True)
            await interaction.response.send_message("❌ Er is een fout opgetreden bij het ophalen van de ontwikkelaars.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(DeveloperManagement(bot))