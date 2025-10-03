import datetime

import discord
from discord import ui
from discord.ext import commands


class JobInfoModal(ui.Modal, title="💼 Deel je job ervaring"):
    """Modal waarin een gebruiker zijn job info kan insturen."""

    content = ui.TextInput(
        label="Je ervaring / job info",
        style=discord.TextStyle.paragraph,
        placeholder="Schrijf hier je ervaring of job info...",
        required=True,
        max_length=4000,
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        # Haal het ingestelde kanaal op uit de database
        settings = await self.bot.db.settings.find_one({"_id": "job_info_settings"}) or {}
        channel_id = settings.get("job_info_channel_id")
        if not channel_id:
            await interaction.response.send_message(
                "❌ Het job info systeem is nog niet geconfigureerd.",
                ephemeral=True,
            )
            return

        channel = interaction.guild.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message(
                "❌ Het ingestelde kanaal bestaat niet (meer).",
                ephemeral=True,
            )
            return

        # Maak de embed voor de nieuwe inzending
        embed = discord.Embed(
            title="📩 Nieuwe inzending!",
            description=f"```\n{self.content.value}\n```",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now(),
        )

        embed.set_footer(
            text="**Wil je zelf ook anoniem je ervaring delen?**\nKlik dan op de knop bij het gepinde bericht!"
        )

        # Stuur bericht met dezelfde knop als het setup bericht
        view = JobInfoView(self.bot)

        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            "✅ Je inzending is anoniem doorgestuurd!", ephemeral=True
        )


class JobInfoView(ui.View):
    """View met knop om anonieme job info in te sturen."""

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(
        label="Stuur anoniem in", style=discord.ButtonStyle.primary, custom_id="job_info_submit"
    )
    async def submit(self, interaction: discord.Interaction, button: ui.Button):
        """Open de modal om job info in te sturen."""
        await interaction.response.send_modal(JobInfoModal(self.bot))


class JobInfo(commands.Cog):
    """Cog voor job info feature."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def send_setup_message(self, channel: discord.TextChannel):
        """Stuur het setup bericht naar het gekozen kanaal."""
        embed = discord.Embed(
            title="💼 Job info – Insturen!",
            description=(
                "Ben je (net) afgestudeerd en wil je je ervaring delen met mensen uit deze server "
                "zodat anderen beter weten wat te verwachten?\n\n"
                "**Anoniem / Niet anoniem;**\n"
                "Indien je deze informatie **anoniem** wilt delen, kan dat via de onderstaande knop. "
                "Je naam wordt dan niet getoond.\n\n"
                "Indien dit geen probleem is, kan je ook een normaal bericht sturen in dit kanaal."
            ),
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now(),
        )
        view = JobInfoView(self.bot)
        await channel.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(JobInfo(bot))
