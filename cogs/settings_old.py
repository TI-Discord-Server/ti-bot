import discord
from discord import app_commands
from discord.ext import commands
import datetime
import re
from typing import Optional
import pymongo
import time
import pytz
from utils.checks import developer

# Definieer de gewenste timezone (GMT+1)
TIMEZONE = pytz.timezone('Europe/Amsterdam')


def is_moderator():
    """
    Controleert of de gebruiker een moderator is. Een moderator is de bot owner of iemand met 'manage_guild' permissies.
    """

    async def predicate(interaction: discord.Interaction):
        """Predicate om te controleren of de user een moderator is."""
        settings = await interaction.client.db.settings.find_one({"_id": "mod_settings"})
        if not settings:
            print("Geen mod settings gevonden in de database! De 'is_moderator' check zal falen.")
            return False
        moderator_id = settings.get("moderator_id")
        return (
            interaction.user.id == moderator_id
            or interaction.user.guild_permissions.manage_guild
        )

    return commands.check(predicate)


class SettingsCommands(commands.Cog, name="SettingsCommands"):
    """
    Commands voor bot instellingen en setup.
    """

    def __init__(self, bot):
        """Initialiseert de SettingsCommands cog."""
        self.bot = bot
        self.settings_collection = self.bot.db["settings"]



    @app_commands.command(name="setup", description="Stel verschillende bot componenten in.")
    @developer()
    @app_commands.describe(
        component="Het component om in te stellen",
        channel="Het kanaal waar het component moet worden ingesteld (optioneel, gebruikt huidige kanaal als niet opgegeven)"
    )
    @app_commands.choices(component=[
        app_commands.Choice(name="Confessions - Confession button", value="confessions"),
        app_commands.Choice(name="Role Menu - Role selection menu", value="role_menu"),
        app_commands.Choice(name="Channel Menu - Year/course selection", value="channel_menu"),
        app_commands.Choice(name="Verification - Verification message", value="verification"),
        app_commands.Choice(name="Unban Request - Unban request button", value="unban_request"),
    ])
    async def setup_command(self, interaction: discord.Interaction,
                           component: str,
                           channel: discord.TextChannel = None):
        """Unified setup command for all bot components."""
        target_channel = channel or interaction.channel
        
        if component == "confessions":
            # Setup confessions
            confession_cog = self.bot.get_cog("ConfessionCommands")
            if not confession_cog:
                await interaction.response.send_message(
                    "❌ Confession systeem is niet geladen.", ephemeral=True)
                return
            
            # Import the ConfessionView here to avoid circular imports
            try:
                from cogs.confessions.confession_view import ConfessionView
                view = ConfessionView(self.bot)
                
                if target_channel == interaction.channel:
                    await target_channel.send(
                        "Klik op de knop hieronder om een bekentenis in te dienen:", view=view)
                    await interaction.response.send_message("✅ Confession button is aangemaakt!", ephemeral=True)
                else:
                    await target_channel.send(
                        "Klik op de knop hieronder om een bekentenis in te dienen:", view=view)
                    await interaction.response.send_message(
                        f"✅ Confession button ingesteld in {target_channel.mention}", ephemeral=True)
                
                self.bot.log.info(f"{interaction.user} heeft confessions setup uitgevoerd in {target_channel.name}.")
                
            except ImportError:
                await interaction.response.send_message(
                    "❌ Kon confession view niet laden.", ephemeral=True)
                return
        
        elif component == "role_menu":
            # Setup role menu overview
            role_selector_cog = self.bot.get_cog("RoleSelector")
            if not role_selector_cog:
                await interaction.response.send_message(
                    "❌ Role selector systeem is niet geladen.", ephemeral=True)
                return
            
            # Get categories
            categories = await role_selector_cog.get_categories()
            if not categories:
                await interaction.response.send_message(
                    "❌ Geen rolcategorieën gevonden. Voeg eerst categorieën toe met `/add_role_category`.", 
                    ephemeral=True)
                return
            
            # Create the overview embed (like update_role_menu_message does)
            embed = discord.Embed(
                title="🎭 Kies je rollen!",
                description="Selecteer een categorie in het dropdown menu hieronder om rollen te kiezen.",
                color=discord.Color.blue()
            )
            
            for category in categories:
                role_list = []
                for role in category.roles:
                    role_list.append(f"{role['emoji']} → @{role['role_name']}")
                
                embed.add_field(
                    name=f"**{category.name}**",
                    value="\n".join(role_list) if role_list else "Geen rollen",
                    inline=True
                )
            
            # Create the view with category select
            from cogs.role_selector import CategorySelect, RoleSelectorView
            view = RoleSelectorView(role_selector_cog)
            view.add_item(CategorySelect(role_selector_cog, categories))
            
            if target_channel == interaction.channel:
                await interaction.response.send_message(embed=embed, view=view)
            else:
                await target_channel.send(embed=embed, view=view)
                await interaction.response.send_message(
                    f"✅ Role menu ingesteld in {target_channel.mention}", ephemeral=True)
        
        elif component == "channel_menu":
            # Setup channel menu
            channel_menu_cog = self.bot.get_cog("ChannelMenu")
            if not channel_menu_cog:
                await interaction.response.send_message(
                    "❌ Channel menu systeem is niet geladen.", ephemeral=True)
                return
            
            # Create embed for channel menu (same as in setup_channel_menu)
            embed = discord.Embed(
                title="📚 Kanaal Selectie",
                description="Selecteer eerst je jaar, dan kun je kiezen welke vakken je wilt volgen.\n"
                           "Je krijgt alleen toegang tot de kanalen die je selecteert.",
                color=discord.Color.purple()
            )
            embed.add_field(
                name="📋 Instructies",
                value="1️⃣ Kies je studiejaar uit het dropdown menu\n"
                      "2️⃣ Selecteer de vakken die je wilt volgen\n"
                      "3️⃣ Je krijgt automatisch toegang tot de geselecteerde kanalen",
                inline=False
            )
            embed.set_footer(text="Gebruik het dropdown menu om je jaar te selecteren")
            
            # Import and create the view
            try:
                from cogs.channel_menu import YearSelectView
                view = YearSelectView(self.bot)
                
                if target_channel == interaction.channel:
                    await interaction.response.defer(ephemeral=True)
                    await target_channel.send(embed=embed, view=view)
                    await interaction.followup.send("✅ Channel menu is aangemaakt!", ephemeral=True)
                else:
                    await interaction.response.defer(ephemeral=True)
                    await target_channel.send(embed=embed, view=view)
                    await interaction.followup.send(
                        f"✅ Channel menu ingesteld in {target_channel.mention}", ephemeral=True)
                
                # Ensure categories exist in the background
                await channel_menu_cog.ensure_categories_exist(interaction.guild)
                
            except ImportError:
                await interaction.response.send_message(
                    "❌ Kon channel menu view niet laden.", ephemeral=True)
                return
        
        elif component == "verification":
            # Setup verification message
            embed = discord.Embed(
                title="Verificatie vereist",
                description=(
                    "Om toegang te krijgen tot deze server moet je een student zijn van HOGENT.\n"
                    "Je moet verifiëren met een geldig studentenmailadres. Je ontvangt een code per mail, "
                    "die je hieronder moet invullen om toegang te krijgen.\n"
                    "**Je e-mailadres wordt opgeslagen in onze database zolang je op de server blijft.** "
                    "Wil je het laten verwijderen, verlaat dan de server of maak een ticket aan. Je toegang wordt dan ingetrokken."
                ),
                color=discord.Color.blue()
            )
            
            # Import VerificationView
            try:
                from cogs.verification import VerificationView
                view = VerificationView(self.bot)
                
                if target_channel == interaction.channel:
                    await target_channel.send(embed=embed, view=view)
                    await interaction.response.send_message("✅ Verificatiebericht is verzonden", ephemeral=True)
                else:
                    await target_channel.send(embed=embed, view=view)
                    await interaction.response.send_message(
                        f"✅ Verificatiebericht verzonden naar {target_channel.mention}", ephemeral=True)
                        
            except ImportError:
                await interaction.response.send_message(
                    "❌ Kon verification view niet laden.", ephemeral=True)
                return
        
        elif component == "unban_request":
            # Setup unban request message
            unban_cog = self.bot.get_cog("UnbanRequest")
            if not unban_cog:
                await interaction.response.send_message(
                    "❌ Unban request systeem is niet geladen.", ephemeral=True)
                return
            
            # Check if required settings are configured (archive channel is optional)
            if not (unban_cog.unban_request_kanaal_id and unban_cog.aanvragen_log_kanaal_id_1):
                await interaction.response.send_message(
                    "❌ De unban aanvraag instellingen zijn nog niet volledig ingesteld. Gebruik `/configure` en selecteer 'Unban Requests' om ze in te stellen.", 
                    ephemeral=True)
                return
            
            # Create the unban request embed and view
            embed = discord.Embed(
                title="Unban Aanvragen", 
                description="Klik op de knop hieronder om een unban aan te vragen.", 
                color=discord.Color.blue()
            )
            
            if target_channel == interaction.channel:
                await target_channel.send(embed=embed, view=unban_cog.unban_view)
                await interaction.response.send_message("✅ Unban aanvraag bericht verzonden!", ephemeral=True)
            else:
                await target_channel.send(embed=embed, view=unban_cog.unban_view)
                await interaction.response.send_message(
                    f"✅ Unban aanvraag bericht verzonden naar {target_channel.mention}.", ephemeral=True)
            
            self.bot.log.info(f"{interaction.user} heeft unban request setup uitgevoerd in {target_channel.name}.")


async def setup(bot):
    await bot.add_cog(SettingsCommands(bot))