import discord
from discord import app_commands
from discord.ext import commands
import pymongo
import time
import datetime
from utils.timezone import to_local


class UnbanView(discord.ui.View):
    def __init__(self, bot, unban_request_kanaal_id, aanvragen_log_kanaal_id_1, aanvragen_log_kanaal_id_2):
        super().__init__(timeout=None)
        self.bot = bot
        self.unban_request_kanaal_id = unban_request_kanaal_id
        self.aanvragen_log_kanaal_id_1 = aanvragen_log_kanaal_id_1
        self.aanvragen_log_kanaal_id_2 = aanvragen_log_kanaal_id_2
        self.persistent = True


    @discord.ui.button(label="Unban Aanvragen", style=discord.ButtonStyle.green, custom_id="unban_aanvraag_knop")
    async def unban_knop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(UnbanAanvraagModal(self.bot, self.aanvragen_log_kanaal_id_1, self.aanvragen_log_kanaal_id_2, interaction.user))


class UnbanAanvraagModal(discord.ui.Modal, title="Unban Aanvraag"):
    def __init__(self, bot, aanvragen_log_kanaal_id_1, aanvragen_log_kanaal_id_2, user):
        super().__init__()
        self.bot = bot
        self.aanvragen_log_kanaal_id_1 = aanvragen_log_kanaal_id_1
        self.aanvragen_log_kanaal_id_2 = aanvragen_log_kanaal_id_2
        self.user = user

    banreden = discord.ui.TextInput(label="Waarom was je geband?", style=discord.TextStyle.long, required=True, placeholder="Geef de reden van je ban.")
    ban_datum = discord.ui.TextInput(label="Wanneer was je geband?", style=discord.TextStyle.short, required=True, placeholder="Geef de datum van je ban in DD/MM/YYYY formaat.")
    reden = discord.ui.TextInput(label="Waarom denk je dat je een unban verdient?", style=discord.TextStyle.long, required=True, placeholder="Geef een duidelijke uitleg.")
    berouw = discord.ui.TextInput(label="Wat heb je geleerd van de ban?", style=discord.TextStyle.long, required=True, placeholder="Beschrijf hoe je gedrag zal veranderen.")
    toevoeg = discord.ui.TextInput(label="Wil je nog iets toevoegen?", style=discord.TextStyle.long, required=False, placeholder="Schrijf hier een opmerking of vraag.")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        reden_antwoord = self.reden.value
        berouw_antwoord = self.berouw.value

        infractions = await self.bot.db.infractions.find(
            {"guild_id": interaction.guild.id, "user_id": self.user.id}
        ).sort("timestamp", pymongo.DESCENDING).limit(5).to_list(length=None)
        infraction_list = ""
        for infraction in infractions:
            localized_timestamp = to_local(infraction['timestamp'])
            infraction_list += f"<t:{int(time.mktime(localized_timestamp.timetuple()))}:f> - **{infraction['type'].capitalize()}**: {infraction['reason']}\n"

        if not infraction_list:
            infraction_list = "Geen voorgaande straffen gevonden."

        embed = discord.Embed(title="Nieuwe Unban Aanvraag", color=discord.Color.orange())
        embed.add_field(name="Gebruiker", value=self.user.mention, inline=False)
        embed.add_field(name="Ban Reden", value=self.banreden.value, inline=False)
        embed.add_field(name="Ban Datum", value=self.ban_datum.value, inline=False)
        embed.add_field(name="Waarom denk je dat je een unban verdient?", value=reden_antwoord, inline=False)
        embed.add_field(name="Wat heb je geleerd van de ban?", value=berouw_antwoord, inline=False)
        if self.toevoeg.value:
            embed.add_field(name="Toevoeging", value=self.toevoeg.value, inline=False)
        embed.add_field(name="Recente Straffen", value=infraction_list, inline=False)

        kanaal1 = self.bot.get_channel(int(self.aanvragen_log_kanaal_id_1))
        kanaal2 = self.bot.get_channel(int(self.aanvragen_log_kanaal_id_2)) if self.aanvragen_log_kanaal_id_2 else None

        if kanaal1:
            # view = UnbanApprovalView(self.bot, self.user, interaction.guild)
            message1 = await kanaal1.send(embed=embed)
            await message1.add_reaction("✅")
            await message1.add_reaction("❌")
        else:
            print(f"Kanaal met ID {self.aanvragen_log_kanaal_id_1} niet gevonden.")

        # Archive channel is optional
        if kanaal2:
            message2 = await kanaal2.send(embed=embed)
        elif self.aanvragen_log_kanaal_id_2:
            print(f"Archive kanaal met ID {self.aanvragen_log_kanaal_id_2} niet gevonden.")

        await interaction.followup.send("Je unban aanvraag is succesvol verzonden.  We zullen je aanvraag zo snel mogelijk beoordelen.", ephemeral=True)


class UnbanRequest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings_collection = self.bot.db["settings"]
        self.unban_view = None
        self.bot.loop.create_task(self.load_unban_settings())

    async def load_unban_settings(self):
        settings = await self.settings_collection.find_one({"_id": "mod_settings"})
        if settings:
            self.unban_request_kanaal_id = str(settings.get("unban_request_kanaal_id")) if settings.get("unban_request_kanaal_id") else None
            self.aanvragen_log_kanaal_id_1 = str(settings.get("aanvragen_log_kanaal_id_1")) if settings.get("aanvragen_log_kanaal_id_1") else None
            self.aanvragen_log_kanaal_id_2 = str(settings.get("aanvragen_log_kanaal_id_2")) if settings.get("aanvragen_log_kanaal_id_2") else None

        else:
            self.unban_request_kanaal_id = None
            self.aanvragen_log_kanaal_id_1 = None
            self.aanvragen_log_kanaal_id_2 = None

        # Only require the first two channels, archive channel is optional
        if self.unban_request_kanaal_id and self.aanvragen_log_kanaal_id_1:
            if self.unban_view:
                self.bot.remove_view(self.unban_view)

            self.unban_view = UnbanView(self.bot, self.unban_request_kanaal_id, self.aanvragen_log_kanaal_id_1, self.aanvragen_log_kanaal_id_2)
            self.bot.add_view(self.unban_view)



async def setup(bot):
    await bot.add_cog(UnbanRequest(bot))