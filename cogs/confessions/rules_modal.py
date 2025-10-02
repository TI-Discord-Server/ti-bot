import discord
from discord.ui import Button, View

from .confession_modal import ConfessionModal


class RulesView(View):
    def __init__(self, bot):
        super().__init__(timeout=60)  # sluit na 60 sec
        self.bot = bot

    @discord.ui.button(label="✅ Ik ga akkoord", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        # Als de user akkoord gaat, open de echte confession modal
        await interaction.response.send_modal(ConfessionModal(self.bot))
        self.stop()
