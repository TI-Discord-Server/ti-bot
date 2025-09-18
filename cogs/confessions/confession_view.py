import discord
from discord.ui import Button, View
from .rules_modal import Rulesmodal


class ConfessionView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Submit Confession", style=discord.ButtonStyle.primary, custom_id="submit_confession")
    async def submit_confession(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(Rulesmodal(self.bot))
