import discord
from discord import app_commands
from discord.ext import commands


class Help(commands.Cog, name="help"):
    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command("help")  # Removes the built-in help command

    @app_commands.command(name="help", description="Get a list of all available commands.")
    async def help_command(self, interaction: discord.Interaction):
        """Displays a help menu with all available slash commands."""
        
        try:
            # Log that the help command was called
            self.bot.log.info(f"Help command called by {interaction.user} in {interaction.guild}")
            
            # Get all commands from the command tree
            commands = self.bot.tree.get_commands()
            self.bot.log.info(f"Found {len(commands)} commands in tree")
            
            embed = discord.Embed(
                title="📋 Help Menu",
                description="Here are all the available commands:",
                color=discord.Color.blue(),
            )

            # Check if we have any commands
            if not commands:
                embed.add_field(
                    name="No Commands Found",
                    value="No slash commands are currently registered.",
                    inline=False,
                )
            else:
                # Loop through all registered slash commands
                for c in commands:
                    embed.add_field(
                        name=f"/{c.name}",
                        value=c.description or "No description",
                        inline=False,
                    )

            embed.set_footer(text="Gebruik een commando door / te typen gevolgd door de commandonaam.")

            await interaction.response.send_message(
                embed=embed, ephemeral=True
            )
            
        except Exception as e:
            # Fallback response if there's any error
            try:
                await interaction.response.send_message(
                    f"❌ Error loading help menu: {str(e)}", 
                    ephemeral=True
                )
            except:
                # If even the error response fails, try a followup
                try:
                    await interaction.followup.send(
                        f"❌ Error loading help menu: {str(e)}", 
                        ephemeral=True
                    )
                except:
                    pass  # Give up if everything fails


async def setup(bot):
    help_cog = Help(bot)
    await bot.add_cog(help_cog)
    bot.log.info("Help cog loaded successfully")
