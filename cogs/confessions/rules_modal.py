import discord
from discord.ui import Modal, TextInput
from .confession_modal import ConfessionModal

class RulesModal(Modal, title="Regels voor Confessions"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.rules = TextInput(
            label="Lees deze regels",
            style=discord.TextStyle.paragraph,
            default=(
                "1. Geen namen of persoonlijke info\n"
                "2. Geen haatspraak of pesten\n"
                "3. Max 4000 tekens\n"
                "4. Respecteer anderen"
            ),
            required=False
        )
        self.rules.disabled = True  # Alleen lezen
        self.add_item(self.rules)

    async def on_submit(self, interaction: discord.Interaction):
        # Na akkoord opent de echte confession modal
        await interaction.response.send_modal(ConfessionModal(self.bot))
