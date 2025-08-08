import discord
from discord.app_commands import command
from discord.ext import commands


class Help(commands.Cog, name="help"):
    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command("help")  # Removes the built-in help command

    @command(name="help", description="Get a list of all available commands.")
    async def help_command(self, interaction: discord.Interaction):
        """Displays a help menu with all available slash commands."""

        embed = discord.Embed(
            title="<:clipboard:1334552918367404072> Help Menu",
            description="Here are all the available commands:",
            color=discord.Color.blue(),
        )

        # Loop through all registered slash commands
        for c in self.bot.tree.get_commands():
            embed.add_field(
                name=f"/{c.name}",
                value=c.description or "No description",
                inline=False,
            )

        embed.set_footer(text="Gebruik een commando door / te typen gevolgd door de commandonaam.")

        await interaction.response.send_message(
            embed=embed, ephemeral=True
        )  # Sends only to the user


async def setup(bot):
    await bot.add_cog(Help(bot))
