import discord
from discord.ui import Modal, TextInput
import datetime
import pytz

# Define Brussels timezone
BRUSSELS_TZ = pytz.timezone('Europe/Brussels')


class ConfessionModal(Modal, title="Submit Confession"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.confession_input = TextInput(
            label="Your Confession",
            placeholder="Type your confession here...",
            style=discord.TextStyle.long,
            required=True,
            max_length=4000,
        )
        self.add_item(self.confession_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Saves the confession to the database."""
        confession = {
            "content": self.confession_input.value,
            "submitted_at": datetime.datetime.now(BRUSSELS_TZ),
            "status": "pending",
        }
        await self.bot.db.confessions.insert_one(confession)
        await interaction.response.send_message(
            "Je bekentenis is anoniem ingediend!", ephemeral=True
        )
