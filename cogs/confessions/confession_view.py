import discord
from discord.ui import Button, View
from .confession_modal import ConfessionModal


class ConfessionView(View):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @discord.ui.button(label="Submit Confession", style=discord.ButtonStyle.primary)
    async def submit_confession(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ConfessionModal(self.bot))
