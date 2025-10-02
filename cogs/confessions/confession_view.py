import discord
from discord.ui import Button, View

from .rules_modal import RulesView  # nieuw bestand met RulesView


class ConfessionView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Submit Confession", style=discord.ButtonStyle.primary, custom_id="submit_confession"
    )
    async def submit_confession(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="📝 Submit a Confession",
            description="Klik op de knop hieronder om een anonieme confession in te zenden.",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="ℹ️ Hoe werkt het?",
            value=(
                "• Je confession wordt nagekeken door moderators\n"
                "• Indien goedgekeurd, wordt deze anoniem geplaatst\n"
                "• Alle inzendingen zijn volledig anoniem"
            ),
            inline=False,
        )
        await interaction.response.send_message(
            embed=embed, view=RulesView(self.bot), ephemeral=True  # enkel zichtbaar voor de user
        )
