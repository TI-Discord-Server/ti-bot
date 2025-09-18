import discord
from discord.ui import Button, View
from .rules_modal import RulesView  # nieuw bestand met RulesView


class ConfessionView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Submit Confession", style=discord.ButtonStyle.primary, custom_id="submit_confession")
    async def submit_confession(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
                title="📝 Submit a Confession",
                description="Click the button below to submit an anonymous confession.",
                color=discord.Color.blue()
            )
        embed.add_field(
            name="ℹ️ How it works",
            value=(
                "• Your confession will be reviewed by moderators\n"
                "• If approved, it will be posted anonymously\n"
                "• All submissions are completely anonymous"
            ),
            inline=False
        )
        await interaction.response.send_message(
            embed=embed,
            view=RulesView(self.bot),
            ephemeral=True  # enkel zichtbaar voor de user
        )
