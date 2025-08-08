import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Dict, Any, List
import datetime


class ConfigurationView(discord.ui.View):
    """Main configuration view with category selection."""
    
    def __init__(self, bot, user_id: int, visible: bool = True):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.visible = visible
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user has permission to use this view."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Je hebt geen toestemming om deze configuratie te gebruiken.", ephemeral=True)
            return False
        return True
    
    @discord.ui.select(
        placeholder="Selecteer een configuratie categorie...",
        options=[
            discord.SelectOption(
                label="Server Instellingen",
                value="server",
                description="Basis server configuratie",
                emoji="🏠"
            ),
            discord.SelectOption(
                label="Modmail",
                value="modmail", 
                description="Modmail systeem instellingen",
                emoji="📧"
            ),
            discord.SelectOption(
                label="Confessions",
                value="confessions",
                description="Confession systeem instellingen", 
                emoji="🤫"
            ),
            discord.SelectOption(
                label="Reports",
                value="reports",
                description="Report systeem instellingen",
                emoji="🚨"
            ),
            discord.SelectOption(
                label="Verificatie",
                value="verification",
                description="Verificatie systeem instellingen",
                emoji="✅"
            ),
            discord.SelectOption(
                label="Moderatie",
                value="moderation",
                description="Moderatie instellingen",
                emoji="🛡️"
            ),
            discord.SelectOption(
                label="Rollen & Kanalen",
                value="roles_channels",
                description="Rol en kanaal menu instellingen",
                emoji="🎭"
            )
        ]
    )
    async def category_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle category selection."""
        category = select.values[0]
        
        if category == "server":
            view = ServerConfigView(self.bot, self.user_id, self.visible)
        elif category == "modmail":
            view = ModmailConfigView(self.bot, self.user_id, self.visible)
        elif category == "confessions":
            view = ConfessionsConfigView(self.bot, self.user_id, self.visible)
        elif category == "reports":
            view = ReportsConfigView(self.bot, self.user_id, self.visible)
        elif category == "verification":
            view = VerificationConfigView(self.bot, self.user_id, self.visible)
        elif category == "moderation":
            view = ModerationConfigView(self.bot, self.user_id, self.visible)
        elif category == "roles_channels":
            view = RolesChannelsConfigView(self.bot, self.user_id, self.visible)
        
        embed = await view.create_embed()
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def create_main_embed(self):
        """Create the main configuration embed."""
        try:
            self.bot.log.debug("Creating main configuration embed...")
            embed = discord.Embed(
                title="🔧 Bot Configuratie",
                description="Selecteer een categorie om de instellingen te bekijken en aan te passen.",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            self.bot.log.debug("Embed created, adding fields...")
            embed.add_field(
                name="📋 Beschikbare Categorieën",
                value=(
                    "🏠 **Server Instellingen** - Basis server configuratie\n"
                    "📧 **Modmail** - Modmail systeem instellingen\n"
                    "🤫 **Confessions** - Confession systeem instellingen\n"
                    "🚨 **Reports** - Report systeem instellingen\n"
                    "✅ **Verificatie** - Verificatie systeem instellingen\n"
                    "🛡️ **Moderatie** - Moderatie instellingen\n"
                    "🎭 **Rollen & Kanalen** - Rol en kanaal menu instellingen"
                ),
                inline=False
            )
            embed.set_footer(text="Gebruik het dropdown menu om een categorie te selecteren")
            self.bot.log.debug("Main embed created successfully")
            return embed
        except Exception as e:
            self.bot.log.error(f"Error creating main embed: {e}", exc_info=True)
            raise


class BaseConfigView(discord.ui.View):
    """Base class for configuration views."""
    
    def __init__(self, bot, user_id: int, visible: bool = True):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.visible = visible
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user has permission to use this view."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Je hebt geen toestemming om deze configuratie te gebruiken.", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="← Terug", style=discord.ButtonStyle.secondary, row=4)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go back to main configuration menu."""
        view = ConfigurationView(self.bot, self.user_id, self.visible)
        embed = await view.create_main_embed()
        await interaction.response.edit_message(embed=embed, view=view)


class ServerConfigView(BaseConfigView):
    """Server configuration view."""
    
    async def create_embed(self):
        """Create server configuration embed."""
        try:
            self.bot.log.debug("Creating server configuration embed...")
            settings = await self.bot.db.settings.find_one({"_id": "server_settings"}) or {}
            self.bot.log.debug(f"Retrieved server settings: {settings}")
            
            embed = discord.Embed(
                title="🏠 Server Instellingen",
                description="Basis server configuratie instellingen",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            
            # Show current guild (auto-detected or configured)
            self.bot.log.debug("Getting current guild info...")
            current_guild = self.bot.guild
            configured_guild_id = settings.get("guild_id", None)
            self.bot.log.debug(f"Current guild: {current_guild}, Configured guild_id: {configured_guild_id}")
            
            if current_guild:
                if configured_guild_id:
                    guild_status = f"**Geconfigureerd:** {current_guild.name} (`{current_guild.id}`)"
                else:
                    guild_status = f"**Auto-gedetecteerd:** {current_guild.name} (`{current_guild.id}`)"
            else:
                # Fallback: show the guild_id even if guild object not found
                guild_id = self.bot.guild_id or 1334456602324897792
                guild_status = f"**Standaard:** Server ID `{guild_id}` (server niet gevonden)"
                self.bot.log.warning(f"Guild object not found, using fallback guild_id: {guild_id}")
                
            embed.add_field(
                name="🏠 Huidige Server",
                value=guild_status,
                inline=False
            )
            self.bot.log.debug("Added guild status field")
            
            # Show multi-guild info if applicable
            if len(self.bot.guilds) > 1:
                embed.add_field(
                    name="ℹ️ Multi-Server Info",
                    value=f"Bot is in {len(self.bot.guilds)} servers. Configureer een specifieke server ID als de auto-detectie niet correct is.",
                    inline=False
                )
                self.bot.log.debug("Added multi-guild info field")
            
            # Developer IDs
            self.bot.log.debug("Processing developer IDs...")
            dev_ids = settings.get("developer_ids", [])
            if dev_ids:
                dev_mentions = []
                for dev_id in dev_ids[:5]:  # Show max 5
                    user = self.bot.get_user(dev_id)
                    if user:
                        dev_mentions.append(f"<@{dev_id}> (`{dev_id}`)")
                    else:
                        dev_mentions.append(f"Onbekende gebruiker (`{dev_id}`)")
                
                dev_text = "\n".join(dev_mentions)
                if len(dev_ids) > 5:
                    dev_text += f"\n... en {len(dev_ids) - 5} meer"
            else:
                dev_text = "Geen ontwikkelaars ingesteld"
                
            embed.add_field(
                name="👨‍💻 Ontwikkelaars",
                value=dev_text,
                inline=False
            )
            self.bot.log.debug("Added developer IDs field")
            
            # Webhook logging format
            self.bot.log.debug("Processing webhook logging format...")
            webhook_format = settings.get("webhook_log_format", "embed")
            format_emoji = "📋" if webhook_format == "embed" else "📝"
            format_description = "Rich embeds met kleuren en velden" if webhook_format == "embed" else "Eenvoudige tekst met [LEVEL] [HH:MM:SS] format"
            
            embed.add_field(
                name=f"{format_emoji} Webhook Logging Format",
                value=f"**Huidige modus:** {webhook_format.title()}\n{format_description}",
                inline=False
            )
            self.bot.log.debug("Added webhook logging format field")
            
            embed.set_footer(text="Gebruik de knoppen hieronder om instellingen aan te passen")
            self.bot.log.debug("Server configuration embed created successfully")
            return embed
            
        except Exception as e:
            self.bot.log.error(f"Error creating server configuration embed: {e}", exc_info=True)
            raise
    
    @discord.ui.button(label="Server ID overschrijven", style=discord.ButtonStyle.secondary, emoji="🏠")
    async def set_guild_id(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Override auto-detected guild ID."""
        modal = GuildIdModal(self.bot, self.user_id, self.visible)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Ontwikkelaars beheren", style=discord.ButtonStyle.primary, emoji="👨‍💻")
    async def manage_developers(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Manage developer IDs."""
        embed = discord.Embed(
            title="👨‍💻 Ontwikkelaars Beheren",
            description=(
                "Gebruik de volgende slash commands om ontwikkelaars te beheren:\n\n"
                "• `/add_developer <user>` - Voeg een ontwikkelaar toe\n"
                "• `/remove_developer <user>` - Verwijder een ontwikkelaar\n"
                "• `/list_developers` - Toon alle ontwikkelaars\n\n"
                "Deze commands gebruiken Discord's gebruiker autocomplete voor een betere ervaring."
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Alleen administrators kunnen ontwikkelaars beheren")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Webhook Logging", style=discord.ButtonStyle.secondary, emoji="📝", row=1)
    async def toggle_webhook_format(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle webhook logging format between embed and plaintext."""
        try:
            # Get current settings
            settings = await self.bot.db.settings.find_one({"_id": "server_settings"}) or {}
            current_format = settings.get("webhook_log_format", "embed")
            
            # Toggle format
            new_format = "plaintext" if current_format == "embed" else "embed"
            
            # Update database
            await self.bot.db.settings.update_one(
                {"_id": "server_settings"},
                {"$set": {"webhook_log_format": new_format}},
                upsert=True
            )
            
            # Create confirmation embed
            format_emoji = "📝" if new_format == "plaintext" else "📋"
            format_description = "Eenvoudige tekst met [LEVEL] [HH:MM:SS] format" if new_format == "plaintext" else "Rich embeds met kleuren en velden"
            
            embed = discord.Embed(
                title=f"{format_emoji} Webhook Logging Format Gewijzigd",
                description=f"**Nieuwe modus:** {new_format.title()}\n{format_description}",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            
            if new_format == "plaintext":
                embed.add_field(
                    name="📝 Plaintext Voorbeeld",
                    value="```\n[INFO] [14:30:25] Bot successfully started\n[WARNING] [14:30:26] Rate limit approaching\n[ERROR] [14:30:27] Database connection failed\n```",
                    inline=False
                )
            else:
                embed.add_field(
                    name="📋 Embed Voorbeeld",
                    value="Rich embeds met kleuren, timestamps en gestructureerde velden zoals je nu ziet!",
                    inline=False
                )
            
            embed.set_footer(text="De wijziging is direct actief voor nieuwe log berichten")
            
            # Send confirmation and refresh the main view
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Refresh the main configuration view
            main_embed = await self.create_embed()
            await interaction.edit_original_response(embed=main_embed, view=self)
            
        except Exception as e:
            self.bot.log.error(f"Error toggling webhook format: {e}", exc_info=True)
            error_embed = discord.Embed(
                title="❌ Fout",
                description=f"Er is een fout opgetreden bij het wijzigen van de webhook logging format:\n```{str(e)}```",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
    
    @discord.ui.button(label="Test Webhook", style=discord.ButtonStyle.success, emoji="🧪", row=1)
    async def test_webhook_logging(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Send test messages to demonstrate current webhook logging format."""
        try:
            # Get current format
            settings = await self.bot.db.settings.find_one({"_id": "server_settings"}) or {}
            current_format = settings.get("webhook_log_format", "embed")
            
            # Send test log messages
            self.bot.log.info("🧪 Test INFO message - Webhook logging format test")
            self.bot.log.warning("🧪 Test WARNING message - Rate limit approaching")
            self.bot.log.error("🧪 Test ERROR message - Connection timeout")
            
            # Create confirmation embed
            format_emoji = "📝" if current_format == "plaintext" else "📋"
            embed = discord.Embed(
                title=f"{format_emoji} Webhook Test Berichten Verzonden",
                description=f"**Huidige format:** {current_format.title()}\n\nEr zijn 3 test berichten verzonden naar de webhook:\n• INFO bericht\n• WARNING bericht\n• ERROR bericht",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            
            if current_format == "plaintext":
                embed.add_field(
                    name="📝 Plaintext Format",
                    value="Berichten worden getoond als:\n```\n[INFO] [HH:MM:SS] 🧪 Test INFO message - Webhook logging format test\n```",
                    inline=False
                )
            else:
                embed.add_field(
                    name="📋 Embed Format", 
                    value="Berichten worden getoond als rich embeds met kleuren en velden (zoals deze!)",
                    inline=False
                )
            
            embed.set_footer(text="Controleer je webhook kanaal om de test berichten te zien")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.bot.log.error(f"Error testing webhook logging: {e}", exc_info=True)
            error_embed = discord.Embed(
                title="❌ Fout",
                description=f"Er is een fout opgetreden bij het testen van webhook logging:\n```{str(e)}```",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)


class ModmailConfigView(BaseConfigView):
    """Modmail configuration view."""
    
    async def create_embed(self):
        """Create modmail configuration embed."""
        settings = await self.bot.db.settings.find_one({"_id": "modmail_settings"}) or {}
        
        embed = discord.Embed(
            title="📧 Modmail Instellingen",
            description="Configuratie voor het modmail systeem",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        # Category
        category_id = settings.get("modmail_category_id", "Niet ingesteld")
        if category_id != "Niet ingesteld":
            category = self.bot.get_channel(category_id)
            category_name = category.name if category else f"Onbekende categorie ({category_id})"
        else:
            category_name = "Niet ingesteld"
            
        embed.add_field(
            name="📁 Modmail Categorie",
            value=f"`{category_id}`\n**Categorie:** {category_name}",
            inline=True
        )
        
        # Logs channel
        logs_id = settings.get("modmail_channel_id", "Niet ingesteld")
        if logs_id != "Niet ingesteld":
            logs_channel = self.bot.get_channel(logs_id)
            logs_name = logs_channel.mention if logs_channel else f"Onbekend kanaal ({logs_id})"
        else:
            logs_name = "Niet ingesteld"
            
        embed.add_field(
            name="📋 Logs Kanaal",
            value=f"`{logs_id}`\n**Kanaal:** {logs_name}",
            inline=True
        )
        
        embed.set_footer(text="Gebruik de knoppen hieronder om instellingen aan te passen")
        return embed
    
    @discord.ui.button(label="Categorie instellen", style=discord.ButtonStyle.primary, emoji="📁")
    async def set_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set modmail category."""
        view = ChannelSelectView(self.bot, self.user_id, "modmail_settings", "modmail_category_id", "category")
        embed = discord.Embed(
            title="📁 Modmail Categorie Selecteren",
            description="Selecteer de categorie waar modmail threads worden aangemaakt.",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Logs Kanaal instellen", style=discord.ButtonStyle.primary, emoji="📋")
    async def set_logs_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set modmail logs channel."""
        view = ChannelSelectView(self.bot, self.user_id, "modmail_settings", "modmail_channel_id", "text")
        embed = discord.Embed(
            title="📋 Modmail Logs Kanaal Selecteren",
            description="Selecteer het kanaal waar modmail logs worden opgeslagen.",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=view)


class ConfessionsConfigView(BaseConfigView):
    """Confessions configuration view."""
    
    async def create_embed(self):
        """Create confessions configuration embed."""
        settings = await self.bot.db.settings.find_one({"_id": "confession_settings"}) or {}
        
        embed = discord.Embed(
            title="🤫 Confessions Instellingen",
            description="Configuratie voor het confessions systeem",
            color=discord.Color.purple(),
            timestamp=datetime.datetime.now()
        )
        
        # Review channel
        review_id = settings.get("review_channel_id", "Niet ingesteld")
        if review_id != "Niet ingesteld":
            review_channel = self.bot.get_channel(review_id)
            review_name = review_channel.mention if review_channel else f"Onbekend kanaal ({review_id})"
        else:
            review_name = "Niet ingesteld"
            
        embed.add_field(
            name="🔍 Review Kanaal",
            value=f"`{review_id}`\n**Kanaal:** {review_name}",
            inline=True
        )
        
        # Public channel
        public_id = settings.get("public_channel_id", "Niet ingesteld")
        if public_id != "Niet ingesteld":
            public_channel = self.bot.get_channel(public_id)
            public_name = public_channel.mention if public_channel else f"Onbekend kanaal ({public_id})"
        else:
            public_name = "Niet ingesteld"
            
        embed.add_field(
            name="📢 Publiek Kanaal",
            value=f"`{public_id}`\n**Kanaal:** {public_name}",
            inline=True
        )
        
        # Timing settings
        review_time = settings.get("review_time", "17:00")
        post_times = settings.get("post_times", ["9:00", "12:00"])
        daily_limit = settings.get("daily_review_limit", len(post_times))
        
        embed.add_field(
            name="⏰ Tijdsinstellingen",
            value=(
                f"**Review tijd:** {review_time} UTC\n"
                f"**Post tijden:** {', '.join(post_times)} UTC\n"
                f"**Dagelijkse limiet:** {daily_limit}"
            ),
            inline=False
        )
        
        embed.set_footer(text="Gebruik de knoppen hieronder om instellingen aan te passen")
        return embed
    
    @discord.ui.button(label="Review Kanaal", style=discord.ButtonStyle.primary, emoji="🔍")
    async def set_review_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set review channel."""
        view = ChannelSelectView(self.bot, self.user_id, "confession_settings", "review_channel_id", "text")
        embed = discord.Embed(
            title="🔍 Review Kanaal Selecteren",
            description="Selecteer het kanaal waar confessions worden gereviewd.",
            color=discord.Color.purple()
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Publiek Kanaal", style=discord.ButtonStyle.primary, emoji="📢")
    async def set_public_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set public channel."""
        view = ChannelSelectView(self.bot, self.user_id, "confession_settings", "public_channel_id", "text")
        embed = discord.Embed(
            title="📢 Publiek Kanaal Selecteren", 
            description="Selecteer het kanaal waar goedgekeurde confessions worden gepost.",
            color=discord.Color.purple()
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Tijden instellen", style=discord.ButtonStyle.primary, emoji="⏰")
    async def set_times(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set confession times."""
        modal = ConfessionTimesModal(self.bot, self.user_id, self.visible)
        await interaction.response.send_modal(modal)


class ReportsConfigView(BaseConfigView):
    """Reports configuration view."""
    
    async def create_embed(self):
        """Create reports configuration embed."""
        settings = await self.bot.db.settings.find_one({"_id": "reports_settings"}) or {}
        
        embed = discord.Embed(
            title="🚨 Reports Instellingen",
            description="Configuratie voor het reports systeem",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        
        # Reports channel
        reports_id = settings.get("reports_channel_id", "Niet ingesteld")
        if reports_id != "Niet ingesteld":
            reports_channel = self.bot.get_channel(reports_id)
            reports_name = reports_channel.mention if reports_channel else f"Onbekend kanaal ({reports_id})"
        else:
            reports_name = "Niet ingesteld"
            
        embed.add_field(
            name="📋 Reports Kanaal",
            value=f"`{reports_id}`\n**Kanaal:** {reports_name}",
            inline=True
        )
        
        # Moderator role
        mod_role_id = settings.get("moderator_role_id", "Niet ingesteld")
        if mod_role_id != "Niet ingesteld":
            # We can't access guild from here, so just show the ID
            mod_role_name = f"<@&{mod_role_id}>"
        else:
            mod_role_name = "Niet ingesteld"
            
        embed.add_field(
            name="🛡️ Moderator Rol",
            value=f"`{mod_role_id}`\n**Rol:** {mod_role_name}",
            inline=True
        )
        
        embed.set_footer(text="Gebruik de knoppen hieronder om instellingen aan te passen")
        return embed
    
    @discord.ui.button(label="Reports Kanaal", style=discord.ButtonStyle.primary, emoji="📋")
    async def set_reports_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set reports channel."""
        view = ChannelSelectView(self.bot, self.user_id, "reports_settings", "reports_channel_id", "text")
        embed = discord.Embed(
            title="📋 Reports Kanaal Selecteren",
            description="Selecteer het kanaal waar reports worden verzonden.",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Moderator Rol", style=discord.ButtonStyle.primary, emoji="🛡️")
    async def set_moderator_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set moderator role."""
        view = RoleSelectView(self.bot, self.user_id, "reports_settings", "moderator_role_id")
        embed = discord.Embed(
            title="🛡️ Moderator Rol Selecteren",
            description="Selecteer de rol die reports kan beheren.",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=view)


class VerificationConfigView(BaseConfigView):
    """Verification configuration view."""
    
    async def create_embed(self):
        """Create verification configuration embed."""
        settings = await self.bot.db.settings.find_one({"_id": "verification_settings"}) or {}
        
        embed = discord.Embed(
            title="✅ Verificatie Instellingen",
            description="Configuratie voor het verificatie systeem",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        
        # Verified role
        verified_role_id = settings.get("verified_role_id", "Niet ingesteld")
        if verified_role_id != "Niet ingesteld":
            verified_role_name = f"<@&{verified_role_id}>"
        else:
            verified_role_name = "Niet ingesteld"
            
        embed.add_field(
            name="✅ Geverifieerde Rol",
            value=f"`{verified_role_id}`\n**Rol:** {verified_role_name}",
            inline=True
        )
        
        embed.set_footer(text="Gebruik de knoppen hieronder om instellingen aan te passen")
        return embed
    
    @discord.ui.button(label="Geverifieerde Rol", style=discord.ButtonStyle.success, emoji="✅")
    async def set_verified_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set verified role."""
        view = RoleSelectView(self.bot, self.user_id, "verification_settings", "verified_role_id")
        embed = discord.Embed(
            title="✅ Geverifieerde Rol Selecteren",
            description="Selecteer de rol die geverifieerde gebruikers krijgen.",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=view)
    



class ModerationConfigView(BaseConfigView):
    """Moderation configuration view."""
    
    async def create_embed(self):
        """Create moderation configuration embed."""
        settings = await self.bot.db.settings.find_one({"_id": "mod_settings"}) or {}
        
        embed = discord.Embed(
            title="🛡️ Moderatie Instellingen",
            description="Configuratie voor moderatie functies",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now()
        )
        
        # Unban request settings
        unban_url = settings.get("unban_request_url", "Niet ingesteld")
        unban_channel_id = settings.get("unban_request_kanaal_id", "Niet ingesteld")
        
        if unban_channel_id != "Niet ingesteld":
            unban_channel = self.bot.get_channel(unban_channel_id)
            unban_channel_name = unban_channel.mention if unban_channel else f"Onbekend kanaal ({unban_channel_id})"
        else:
            unban_channel_name = "Niet ingesteld"
        
        embed.add_field(
            name="🔓 Unban Verzoeken",
            value=(
                f"**URL:** {unban_url}\n"
                f"**Kanaal:** {unban_channel_name} (`{unban_channel_id}`)"
            ),
            inline=False
        )
        
        # Log channels
        log1_id = settings.get("aanvragen_log_kanaal_id_1", "Niet ingesteld")
        log2_id = settings.get("aanvragen_log_kanaal_id_2", "Niet ingesteld")
        
        log_text = ""
        if log1_id != "Niet ingesteld":
            log1_channel = self.bot.get_channel(log1_id)
            log1_name = log1_channel.mention if log1_channel else f"Onbekend kanaal ({log1_id})"
            log_text += f"**Log 1:** {log1_name} (`{log1_id}`)\n"
        
        if log2_id != "Niet ingesteld":
            log2_channel = self.bot.get_channel(log2_id)
            log2_name = log2_channel.mention if log2_channel else f"Onbekend kanaal ({log2_id})"
            log_text += f"**Log 2:** {log2_name} (`{log2_id}`)\n"
        
        if not log_text:
            log_text = "Geen log kanalen ingesteld"
        
        embed.add_field(
            name="📋 Log Kanalen",
            value=log_text,
            inline=False
        )
        
        embed.set_footer(text="Gebruik de knoppen hieronder om instellingen aan te passen")
        return embed
    

    
    @discord.ui.button(label="Unban Instellingen", style=discord.ButtonStyle.primary, emoji="🔓")
    async def set_unban_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set unban request settings."""
        modal = UnbanSettingsModal(self.bot, self.user_id, self.visible)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Log Kanalen", style=discord.ButtonStyle.primary, emoji="📋")
    async def set_log_channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set log channels."""
        modal = LogChannelsModal(self.bot, self.user_id, self.visible)
        await interaction.response.send_modal(modal)


class RolesChannelsConfigView(BaseConfigView):
    """Roles and channels configuration view."""
    
    async def create_embed(self):
        """Create roles and channels configuration embed."""
        embed = discord.Embed(
            title="🎭 Rollen & Kanalen Instellingen",
            description="Configuratie voor rol en kanaal menu systemen",
            color=discord.Color.gold(),
            timestamp=datetime.datetime.now()
        )
        
        # Get role selector configuration
        role_config = await self.bot.db.role_selector.find_one({"_id": "config"})
        categories_doc = await self.bot.db.role_selector.find_one({"_id": "categories"})
        
        # Role menu status
        if role_config and role_config.get("message_id"):
            channel_id = role_config.get("channel_id")
            channel_name = f"<#{channel_id}>" if channel_id else "Onbekend kanaal"
            embed.add_field(
                name="📋 Rol Menu Status",
                value=f"**Actief in:** {channel_name}\n**Message ID:** `{role_config.get('message_id')}`",
                inline=True
            )
        else:
            embed.add_field(
                name="📋 Rol Menu Status",
                value="Niet ingesteld",
                inline=True
            )
        
        # Categories count
        category_count = 0
        total_roles = 0
        if categories_doc:
            categories = categories_doc.get("categories", [])
            category_count = len(categories)
            total_roles = sum(len(cat.get("roles", [])) for cat in categories)
        
        embed.add_field(
            name="📊 Statistieken",
            value=f"**Categorieën:** {category_count}\n**Totaal rollen:** {total_roles}",
            inline=True
        )
        
        embed.add_field(
            name="🔧 Beheer Opties",
            value=(
                "Gebruik de knoppen hieronder om:\n"
                "• Rol categorieën beheren\n"
                "• Rollen toevoegen/verwijderen\n"
                "• Rol menu instellen"
            ),
            inline=False
        )
        
        embed.set_footer(text="Gebruik de knoppen hieronder om instellingen aan te passen")
        return embed
    
    @discord.ui.button(label="Categorieën Beheren", style=discord.ButtonStyle.primary, emoji="📁")
    async def manage_categories(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Manage role categories."""
        view = RoleCategoryManagementView(self.bot, self.user_id, self.visible)
        embed = await view.create_embed()
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Rollen Beheren", style=discord.ButtonStyle.secondary, emoji="🎭")
    async def manage_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Manage roles in categories."""
        view = RoleManagementView(self.bot, self.user_id, self.visible)
        embed = await view.create_embed()
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Menu Instellen", style=discord.ButtonStyle.success, emoji="📋")
    async def setup_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Setup role menu in a channel."""
        view = RoleMenuSetupView(self.bot, self.user_id, self.visible)
        embed = discord.Embed(
            title="📋 Rol Menu Instellen",
            description="Selecteer een kanaal waar het rol menu geplaatst moet worden.",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=view)


# Channel and Role Selection Views
class ChannelSelectView(discord.ui.View):
    """View for selecting channels."""
    
    def __init__(self, bot, user_id: int, settings_id: str, field_name: str, channel_type: str):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.settings_id = settings_id
        self.field_name = field_name
        self.channel_type = channel_type
        
        # Add channel select
        if channel_type == "text":
            select = discord.ui.ChannelSelect(
                placeholder="Selecteer een tekstkanaal...",
                channel_types=[discord.ChannelType.text]
            )
        elif channel_type == "category":
            select = discord.ui.ChannelSelect(
                placeholder="Selecteer een categorie...",
                channel_types=[discord.ChannelType.category]
            )
        
        select.callback = self.channel_select_callback
        self.add_item(select)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Je hebt geen toestemming om deze configuratie te gebruiken.", ephemeral=True)
            return False
        return True
    
    async def channel_select_callback(self, interaction: discord.Interaction):
        """Handle channel selection."""
        channel = interaction.data['values'][0]
        channel_id = int(channel)
        
        await self.bot.db.settings.update_one(
            {"_id": self.settings_id},
            {"$set": {self.field_name: channel_id}},
            upsert=True
        )
        
        # Return to appropriate config view
        if self.settings_id == "modmail_settings":
            config_view = ModmailConfigView(self.bot, self.user_id, True)
        elif self.settings_id == "confession_settings":
            config_view = ConfessionsConfigView(self.bot, self.user_id, True)
        elif self.settings_id == "reports_settings":
            config_view = ReportsConfigView(self.bot, self.user_id, True)
        else:
            config_view = ConfigurationView(self.bot, self.user_id, True)
        
        embed = await config_view.create_embed()
        await interaction.response.edit_message(embed=embed, view=config_view)
    
    @discord.ui.button(label="← Terug", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go back to the appropriate config view."""
        # Determine which config view to return to based on settings_id
        if self.settings_id == "modmail_settings":
            view = ModmailConfigView(self.bot, self.user_id, True)
        elif self.settings_id == "confession_settings":
            view = ConfessionsConfigView(self.bot, self.user_id, True)
        elif self.settings_id == "reports_settings":
            view = ReportsConfigView(self.bot, self.user_id, True)
        else:
            view = ConfigurationView(self.bot, self.user_id, True)
        
        embed = await view.create_embed()
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def on_timeout(self):
        """Handle timeout."""
        for item in self.children:
            item.disabled = True


class RoleSelectView(discord.ui.View):
    """View for selecting roles."""
    
    def __init__(self, bot, user_id: int, settings_id: str, field_name: str):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.settings_id = settings_id
        self.field_name = field_name
        
        # Add role select
        select = discord.ui.RoleSelect(
            placeholder="Selecteer een rol..."
        )
        select.callback = self.role_select_callback
        self.add_item(select)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Je hebt geen toestemming om deze configuratie te gebruiken.", ephemeral=True)
            return False
        return True
    
    async def role_select_callback(self, interaction: discord.Interaction):
        """Handle role selection."""
        role = interaction.data['values'][0]
        role_id = int(role)
        
        await self.bot.db.settings.update_one(
            {"_id": self.settings_id},
            {"$set": {self.field_name: role_id}},
            upsert=True
        )
        
        # Return to appropriate config view
        if self.settings_id == "reports_settings":
            config_view = ReportsConfigView(self.bot, self.user_id, True)
        elif self.settings_id == "verification_settings":
            config_view = VerificationConfigView(self.bot, self.user_id, True)
        else:
            config_view = ConfigurationView(self.bot, self.user_id, True)
        
        embed = await config_view.create_embed()
        await interaction.response.edit_message(embed=embed, view=config_view)
    
    @discord.ui.button(label="← Terug", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go back to the appropriate config view."""
        # Determine which config view to return to based on settings_id
        if self.settings_id == "reports_settings":
            view = ReportsConfigView(self.bot, self.user_id, True)
        elif self.settings_id == "verification_settings":
            view = VerificationConfigView(self.bot, self.user_id, True)
        else:
            view = ConfigurationView(self.bot, self.user_id, True)
        
        embed = await view.create_embed()
        await interaction.response.edit_message(embed=embed, view=view)


# Modal classes for text input
class GuildIdModal(discord.ui.Modal):
    """Modal for setting guild ID."""
    
    def __init__(self, bot, user_id: int, visible: bool):
        super().__init__(title="Server ID Overschrijven")
        self.bot = bot
        self.user_id = user_id
        self.visible = visible
        
        self.guild_id_input = discord.ui.TextInput(
            label="Server ID",
            placeholder="Alleen nodig bij meerdere servers...",
            required=True,
            max_length=20
        )
        self.add_item(self.guild_id_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild_id = int(self.guild_id_input.value)
            
            await self.bot.db.settings.update_one(
                {"_id": "server_settings"},
                {"$set": {"guild_id": guild_id}},
                upsert=True
            )
            
            view = ServerConfigView(self.bot, self.user_id, self.visible)
            embed = await view.create_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            
        except ValueError:
            await interaction.response.send_message("❌ Ongeldige server ID. Voer een geldig nummer in.", ephemeral=True)



class ConfessionTimesModal(discord.ui.Modal):
    """Modal for setting confession times."""
    
    def __init__(self, bot, user_id: int, visible: bool):
        super().__init__(title="Confession Tijden Instellen")
        self.bot = bot
        self.user_id = user_id
        self.visible = visible
        
        self.review_time_input = discord.ui.TextInput(
            label="Review Tijd (HH:MM)",
            placeholder="17:00",
            required=True,
            max_length=5
        )
        self.add_item(self.review_time_input)
        
        self.post_times_input = discord.ui.TextInput(
            label="Post Tijden (HH:MM, gescheiden door komma's)",
            placeholder="9:00, 12:00, 18:00",
            required=True,
            style=discord.TextStyle.paragraph,
            max_length=200
        )
        self.add_item(self.post_times_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate review time
            review_time = self.review_time_input.value.strip()
            hour, minute = map(int, review_time.split(":"))
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError("Invalid review time")
            formatted_review_time = f"{hour:02}:{minute:02}"
            
            # Validate post times
            post_times_list = [time.strip() for time in self.post_times_input.value.split(",")]
            formatted_post_times = []
            
            for time_str in post_times_list:
                if time_str:
                    hour, minute = map(int, time_str.split(":"))
                    if not (0 <= hour < 24 and 0 <= minute < 60):
                        raise ValueError("Invalid post time")
                    formatted_post_times.append(f"{hour:02}:{minute:02}")
            
            if not formatted_post_times:
                raise ValueError("At least one post time required")
            
            # Update database
            await self.bot.db.settings.update_one(
                {"_id": "confession_settings"},
                {"$set": {
                    "review_time": formatted_review_time,
                    "post_times": formatted_post_times,
                    "daily_review_limit": len(formatted_post_times)
                }},
                upsert=True
            )
            
            # Update schedules if confession tasks exist
            try:
                confession_cog = self.bot.get_cog("ConfessionCommands")
                if confession_cog and hasattr(confession_cog, 'tasks'):
                    await confession_cog.tasks.update_review_schedule()
                    await confession_cog.tasks.update_post_schedule()
            except Exception as e:
                self.bot.log.warning(f"Could not update confession schedules: {e}")
            
            view = ConfessionsConfigView(self.bot, self.user_id, self.visible)
            embed = await view.create_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            
        except ValueError:
            await interaction.response.send_message("❌ Ongeldige tijdsnotatie. Gebruik HH:MM formaat (24-uur).", ephemeral=True)



class UnbanSettingsModal(discord.ui.Modal):
    """Modal for setting unban request settings."""
    
    def __init__(self, bot, user_id: int, visible: bool):
        super().__init__(title="Unban Verzoek Instellingen")
        self.bot = bot
        self.user_id = user_id
        self.visible = visible
        
        self.url_input = discord.ui.TextInput(
            label="Unban Verzoek URL",
            placeholder="https://example.com/unban-request",
            required=False,
            max_length=500
        )
        self.add_item(self.url_input)
        
        self.channel_id_input = discord.ui.TextInput(
            label="Unban Verzoek Kanaal ID",
            placeholder="Voer het kanaal ID in...",
            required=False,
            max_length=20
        )
        self.add_item(self.channel_id_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            update_data = {}
            
            if self.url_input.value.strip():
                update_data["unban_request_url"] = self.url_input.value.strip()
            
            if self.channel_id_input.value.strip():
                channel_id = int(self.channel_id_input.value.strip())
                update_data["unban_request_kanaal_id"] = channel_id
            
            if update_data:
                await self.bot.db.settings.update_one(
                    {"_id": "mod_settings"},
                    {"$set": update_data},
                    upsert=True
                )
            
            view = ModerationConfigView(self.bot, self.user_id, self.visible)
            embed = await view.create_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            
        except ValueError:
            await interaction.response.send_message("❌ Ongeldige kanaal ID. Voer een geldig nummer in.", ephemeral=True)


class LogChannelsModal(discord.ui.Modal):
    """Modal for setting log channels."""
    
    def __init__(self, bot, user_id: int, visible: bool):
        super().__init__(title="Log Kanalen Instellen")
        self.bot = bot
        self.user_id = user_id
        self.visible = visible
        
        self.log1_input = discord.ui.TextInput(
            label="Log Kanaal 1 ID",
            placeholder="Voer het eerste log kanaal ID in...",
            required=False,
            max_length=20
        )
        self.add_item(self.log1_input)
        
        self.log2_input = discord.ui.TextInput(
            label="Log Kanaal 2 ID",
            placeholder="Voer het tweede log kanaal ID in...",
            required=False,
            max_length=20
        )
        self.add_item(self.log2_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            update_data = {}
            
            if self.log1_input.value.strip():
                log1_id = int(self.log1_input.value.strip())
                update_data["aanvragen_log_kanaal_id_1"] = log1_id
            
            if self.log2_input.value.strip():
                log2_id = int(self.log2_input.value.strip())
                update_data["aanvragen_log_kanaal_id_2"] = log2_id
            
            if update_data:
                await self.bot.db.settings.update_one(
                    {"_id": "mod_settings"},
                    {"$set": update_data},
                    upsert=True
                )
            
            view = ModerationConfigView(self.bot, self.user_id, self.visible)
            embed = await view.create_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            
        except ValueError:
            await interaction.response.send_message("❌ Ongeldige kanaal ID(s). Voer geldige nummers in.", ephemeral=True)


class Configure(commands.Cog):
    """Configuration management cog."""
    
    def __init__(self, bot):
        self.bot = bot
    
    def has_admin_permissions():
        """Check if user has admin permissions."""
        async def predicate(interaction: discord.Interaction):
            return (
                interaction.user.guild_permissions.manage_guild or
                interaction.user.guild_permissions.administrator or
                interaction.user.id in getattr(interaction.client, 'owner_ids', set())
            )
        return app_commands.check(predicate)
    
    @app_commands.command(name="configure", description="Open de bot configuratie interface")
    @app_commands.describe(visible="Of de configuratie zichtbaar moet zijn voor anderen (standaard: waar)")
    @has_admin_permissions()
    async def configure(self, interaction: discord.Interaction, visible: bool = True):
        """Open the configuration interface."""
        try:
            self.bot.log.info(f"Configure command called by {interaction.user} ({interaction.user.id}) in guild {interaction.guild_id}")
            
            # Defer the response immediately to prevent timeout
            await interaction.response.defer(ephemeral=not visible)
            self.bot.log.debug("Response deferred")
            
            self.bot.log.debug(f"Bot guild_id: {getattr(self.bot, 'guild_id', 'NOT_SET')}")
            self.bot.log.debug(f"Bot guild: {getattr(self.bot, 'guild', 'NOT_SET')}")
            
            self.bot.log.debug("Creating ConfigurationView...")
            view = ConfigurationView(self.bot, interaction.user.id, visible)
            
            self.bot.log.debug("Creating main embed...")
            embed = await view.create_main_embed()
            
            self.bot.log.debug("Sending followup...")
            await interaction.followup.send(embed=embed, view=view, ephemeral=not visible)
            self.bot.log.info("Configure command completed successfully")
            
        except Exception as e:
            self.bot.log.error(f"Error in configure command: {e}", exc_info=True)
            try:
                # Since we always defer the response, use followup
                await interaction.followup.send(
                    "❌ Er is een fout opgetreden bij het laden van de configuratie. Check de logs voor details.",
                    ephemeral=True
                )
            except Exception as followup_error:
                self.bot.log.error(f"Failed to send error message: {followup_error}")





# Role Management Views
class RoleCategoryManagementView(BaseConfigView):
    """View for managing role categories."""
    
    async def create_embed(self):
        """Create category management embed."""
        embed = discord.Embed(
            title="📁 Categorie Beheer",
            description="Beheer rol categorieën",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        # Get categories
        categories_doc = await self.bot.db.role_selector.find_one({"_id": "categories"})
        if categories_doc:
            categories = categories_doc.get("categories", [])
            if categories:
                category_list = []
                for i, category in enumerate(categories, 1):
                    role_count = len(category.get("roles", []))
                    category_list.append(f"{i}. **{category['name']}** ({role_count} rollen)")
                
                embed.add_field(
                    name="📋 Huidige Categorieën",
                    value="\n".join(category_list),
                    inline=False
                )
            else:
                embed.add_field(
                    name="📋 Huidige Categorieën",
                    value="Geen categorieën gevonden",
                    inline=False
                )
        else:
            embed.add_field(
                name="📋 Huidige Categorieën",
                value="Geen categorieën gevonden",
                inline=False
            )
        
        embed.set_footer(text="Gebruik de knoppen om categorieën toe te voegen of te verwijderen")
        return embed
    
    @discord.ui.button(label="Categorie Toevoegen", style=discord.ButtonStyle.success, emoji="➕")
    async def add_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Add a new category."""
        modal = AddCategoryModal(self.bot, self.user_id, self.visible)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Categorie Verwijderen", style=discord.ButtonStyle.danger, emoji="➖")
    async def remove_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Remove a category."""
        modal = RemoveCategoryModal(self.bot, self.user_id, self.visible)
        await interaction.response.send_modal(modal)


class RoleManagementView(BaseConfigView):
    """View for managing roles in categories."""
    
    async def create_embed(self):
        """Create role management embed."""
        embed = discord.Embed(
            title="🎭 Rol Beheer",
            description="Beheer rollen in categorieën",
            color=discord.Color.purple(),
            timestamp=datetime.datetime.now()
        )
        
        # Get categories and their roles
        categories_doc = await self.bot.db.role_selector.find_one({"_id": "categories"})
        if categories_doc:
            categories = categories_doc.get("categories", [])
            if categories:
                for category in categories:
                    roles = category.get("roles", [])
                    if roles:
                        role_list = []
                        for role in roles:
                            emoji = role.get("emoji", "")
                            name = role.get("name", "")
                            role_name = role.get("role_name", "")
                            role_list.append(f"{emoji} {name} → @{role_name}")
                        
                        embed.add_field(
                            name=f"📁 {category['name']}",
                            value="\n".join(role_list),
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name=f"📁 {category['name']}",
                            value="Geen rollen",
                            inline=False
                        )
            else:
                embed.add_field(
                    name="ℹ️ Geen Categorieën",
                    value="Voeg eerst categorieën toe voordat je rollen kunt beheren.",
                    inline=False
                )
        else:
            embed.add_field(
                name="ℹ️ Geen Categorieën",
                value="Voeg eerst categorieën toe voordat je rollen kunt beheren.",
                inline=False
            )
        
        embed.set_footer(text="Gebruik de knoppen om rollen toe te voegen of te verwijderen")
        return embed
    
    @discord.ui.button(label="Rol Toevoegen", style=discord.ButtonStyle.success, emoji="➕")
    async def add_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Add a role to a category."""
        modal = AddRoleModal(self.bot, self.user_id, self.visible)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Rol Verwijderen", style=discord.ButtonStyle.danger, emoji="➖")
    async def remove_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Remove a role from a category."""
        modal = RemoveRoleModal(self.bot, self.user_id, self.visible)
        await interaction.response.send_modal(modal)


class RoleMenuSetupView(discord.ui.View):
    """View for setting up role menu in a channel."""
    
    def __init__(self, bot, user_id: int, visible: bool):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.visible = visible
        
        # Add channel select
        select = discord.ui.ChannelSelect(
            placeholder="Selecteer een kanaal voor het rol menu...",
            channel_types=[discord.ChannelType.text]
        )
        select.callback = self.channel_select_callback
        self.add_item(select)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Je hebt geen toestemming om deze configuratie te gebruiken.", ephemeral=True)
            return False
        return True
    
    async def channel_select_callback(self, interaction: discord.Interaction):
        """Handle channel selection for role menu setup."""
        channel = interaction.data['values'][0]
        channel_id = int(channel)
        
        try:
            # Get the role selector cog
            role_selector_cog = self.bot.get_cog("RoleSelector")
            if not role_selector_cog:
                await interaction.response.send_message("❌ Rol selector systeem niet gevonden.", ephemeral=True)
                return
            
            # Update the role menu message
            message = await role_selector_cog.update_role_menu_message(channel_id)
            
            if message:
                embed = discord.Embed(
                    title="✅ Rol Menu Ingesteld",
                    description=f"Het rol menu is succesvol ingesteld in <#{channel_id}>",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="📋 Details",
                    value=f"**Kanaal:** <#{channel_id}>\n**Message ID:** `{message.id}`",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="❌ Fout",
                    description="Er is een fout opgetreden bij het instellen van het rol menu.",
                    color=discord.Color.red()
                )
            
            # Return to roles config
            view = RolesChannelsConfigView(self.bot, self.user_id, self.visible)
            config_embed = await view.create_embed()
            
            # Send confirmation message and update original message
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await interaction.edit_original_response(embed=config_embed, view=view)
            
        except Exception as e:
            self.bot.log.error(f"Error setting up role menu: {e}", exc_info=True)
            await interaction.response.send_message("❌ Er is een fout opgetreden bij het instellen van het rol menu.", ephemeral=True)


# Role Management Modals
class AddCategoryModal(discord.ui.Modal):
    """Modal for adding a new role category."""
    
    def __init__(self, bot, user_id: int, visible: bool):
        super().__init__(title="Categorie Toevoegen")
        self.bot = bot
        self.user_id = user_id
        self.visible = visible
        
        self.name_input = discord.ui.TextInput(
            label="Categorie Naam",
            placeholder="Bijv. Campussen, Studiejaren, etc.",
            required=True,
            max_length=50
        )
        self.add_item(self.name_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            category_name = self.name_input.value.strip()
            
            # Get existing categories
            categories_doc = await self.bot.db.role_selector.find_one({"_id": "categories"})
            categories = categories_doc.get("categories", []) if categories_doc else []
            
            # Check if category already exists
            if any(cat["name"].lower() == category_name.lower() for cat in categories):
                await interaction.response.send_message(f"❌ Categorie '{category_name}' bestaat al.", ephemeral=True)
                return
            
            # Add new category
            categories.append({"name": category_name, "roles": []})
            
            # Save to database
            await self.bot.db.role_selector.update_one(
                {"_id": "categories"},
                {"$set": {"categories": categories}},
                upsert=True
            )
            
            # Update role menu if it exists
            role_selector_cog = self.bot.get_cog("RoleSelector")
            if role_selector_cog and hasattr(role_selector_cog, 'role_menu_channel_id') and role_selector_cog.role_menu_channel_id:
                await role_selector_cog.update_role_menu_message(
                    role_selector_cog.role_menu_channel_id, 
                    role_selector_cog.role_menu_message_id
                )
            
            # Return to category management
            view = RoleCategoryManagementView(self.bot, self.user_id, self.visible)
            embed = await view.create_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            
        except Exception as e:
            self.bot.log.error(f"Error adding category: {e}", exc_info=True)
            await interaction.response.send_message("❌ Er is een fout opgetreden bij het toevoegen van de categorie.", ephemeral=True)


class RemoveCategoryModal(discord.ui.Modal):
    """Modal for removing a role category."""
    
    def __init__(self, bot, user_id: int, visible: bool):
        super().__init__(title="Categorie Verwijderen")
        self.bot = bot
        self.user_id = user_id
        self.visible = visible
        
        self.name_input = discord.ui.TextInput(
            label="Categorie Naam",
            placeholder="Exacte naam van de categorie om te verwijderen",
            required=True,
            max_length=50
        )
        self.add_item(self.name_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            category_name = self.name_input.value.strip()
            
            # Get existing categories
            categories_doc = await self.bot.db.role_selector.find_one({"_id": "categories"})
            if not categories_doc:
                await interaction.response.send_message("❌ Geen categorieën gevonden.", ephemeral=True)
                return
            
            categories = categories_doc.get("categories", [])
            
            # Find and remove category
            original_count = len(categories)
            categories = [cat for cat in categories if cat["name"].lower() != category_name.lower()]
            
            if len(categories) == original_count:
                await interaction.response.send_message(f"❌ Categorie '{category_name}' niet gevonden.", ephemeral=True)
                return
            
            # Save to database
            await self.bot.db.role_selector.update_one(
                {"_id": "categories"},
                {"$set": {"categories": categories}},
                upsert=True
            )
            
            # Update role menu if it exists
            role_selector_cog = self.bot.get_cog("RoleSelector")
            if role_selector_cog and hasattr(role_selector_cog, 'role_menu_channel_id') and role_selector_cog.role_menu_channel_id:
                await role_selector_cog.update_role_menu_message(
                    role_selector_cog.role_menu_channel_id, 
                    role_selector_cog.role_menu_message_id
                )
            
            # Return to category management
            view = RoleCategoryManagementView(self.bot, self.user_id, self.visible)
            embed = await view.create_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            
        except Exception as e:
            self.bot.log.error(f"Error removing category: {e}", exc_info=True)
            await interaction.response.send_message("❌ Er is een fout opgetreden bij het verwijderen van de categorie.", ephemeral=True)


class AddRoleModal(discord.ui.Modal):
    """Modal for adding a role to a category."""
    
    def __init__(self, bot, user_id: int, visible: bool):
        super().__init__(title="Rol Toevoegen")
        self.bot = bot
        self.user_id = user_id
        self.visible = visible
        
        self.category_input = discord.ui.TextInput(
            label="Categorie Naam",
            placeholder="Naam van de categorie",
            required=True,
            max_length=50
        )
        self.add_item(self.category_input)
        
        self.role_name_input = discord.ui.TextInput(
            label="Discord Rol Naam",
            placeholder="Exacte naam van de Discord rol",
            required=True,
            max_length=100
        )
        self.add_item(self.role_name_input)
        
        self.display_name_input = discord.ui.TextInput(
            label="Weergave Naam",
            placeholder="Naam zoals getoond in het menu (optioneel)",
            required=False,
            max_length=100
        )
        self.add_item(self.display_name_input)
        
        self.emoji_input = discord.ui.TextInput(
            label="Emoji",
            placeholder="Emoji voor de rol (bijv. 🎮)",
            required=True,
            max_length=10
        )
        self.add_item(self.emoji_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            category_name = self.category_input.value.strip()
            role_name = self.role_name_input.value.strip()
            display_name = self.display_name_input.value.strip() or role_name
            emoji = self.emoji_input.value.strip()
            
            # Verify the role exists
            guild = interaction.guild
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                await interaction.response.send_message(f"❌ Rol '{role_name}' niet gevonden in deze server.", ephemeral=True)
                return
            
            # Get existing categories
            categories_doc = await self.bot.db.role_selector.find_one({"_id": "categories"})
            if not categories_doc:
                await interaction.response.send_message("❌ Geen categorieën gevonden. Voeg eerst een categorie toe.", ephemeral=True)
                return
            
            categories = categories_doc.get("categories", [])
            
            # Find the category
            category_found = False
            for category in categories:
                if category["name"].lower() == category_name.lower():
                    category_found = True
                    
                    # Check if role already exists in this category
                    if any(r["role_name"] == role_name for r in category.get("roles", [])):
                        await interaction.response.send_message(f"❌ Rol '{role_name}' bestaat al in categorie '{category_name}'.", ephemeral=True)
                        return
                    
                    # Add the role
                    if "roles" not in category:
                        category["roles"] = []
                    
                    category["roles"].append({
                        "name": display_name,
                        "role_name": role_name,
                        "emoji": emoji
                    })
                    break
            
            if not category_found:
                await interaction.response.send_message(f"❌ Categorie '{category_name}' niet gevonden.", ephemeral=True)
                return
            
            # Save to database
            await self.bot.db.role_selector.update_one(
                {"_id": "categories"},
                {"$set": {"categories": categories}},
                upsert=True
            )
            
            # Update role menu if it exists
            role_selector_cog = self.bot.get_cog("RoleSelector")
            if role_selector_cog and hasattr(role_selector_cog, 'role_menu_channel_id') and role_selector_cog.role_menu_channel_id:
                await role_selector_cog.update_role_menu_message(
                    role_selector_cog.role_menu_channel_id, 
                    role_selector_cog.role_menu_message_id
                )
            
            # Return to role management
            view = RoleManagementView(self.bot, self.user_id, self.visible)
            embed = await view.create_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            
        except Exception as e:
            self.bot.log.error(f"Error adding role: {e}", exc_info=True)
            await interaction.response.send_message("❌ Er is een fout opgetreden bij het toevoegen van de rol.", ephemeral=True)


class RemoveRoleModal(discord.ui.Modal):
    """Modal for removing a role from a category."""
    
    def __init__(self, bot, user_id: int, visible: bool):
        super().__init__(title="Rol Verwijderen")
        self.bot = bot
        self.user_id = user_id
        self.visible = visible
        
        self.category_input = discord.ui.TextInput(
            label="Categorie Naam",
            placeholder="Naam van de categorie",
            required=True,
            max_length=50
        )
        self.add_item(self.category_input)
        
        self.role_name_input = discord.ui.TextInput(
            label="Rol Naam",
            placeholder="Exacte naam van de rol om te verwijderen",
            required=True,
            max_length=100
        )
        self.add_item(self.role_name_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            category_name = self.category_input.value.strip()
            role_name = self.role_name_input.value.strip()
            
            # Get existing categories
            categories_doc = await self.bot.db.role_selector.find_one({"_id": "categories"})
            if not categories_doc:
                await interaction.response.send_message("❌ Geen categorieën gevonden.", ephemeral=True)
                return
            
            categories = categories_doc.get("categories", [])
            
            # Find the category and remove the role
            role_removed = False
            for category in categories:
                if category["name"].lower() == category_name.lower():
                    original_count = len(category.get("roles", []))
                    category["roles"] = [r for r in category.get("roles", []) if r["role_name"] != role_name]
                    
                    if len(category["roles"]) < original_count:
                        role_removed = True
                    break
            
            if not role_removed:
                await interaction.response.send_message(f"❌ Rol '{role_name}' niet gevonden in categorie '{category_name}'.", ephemeral=True)
                return
            
            # Save to database
            await self.bot.db.role_selector.update_one(
                {"_id": "categories"},
                {"$set": {"categories": categories}},
                upsert=True
            )
            
            # Update role menu if it exists
            role_selector_cog = self.bot.get_cog("RoleSelector")
            if role_selector_cog and hasattr(role_selector_cog, 'role_menu_channel_id') and role_selector_cog.role_menu_channel_id:
                await role_selector_cog.update_role_menu_message(
                    role_selector_cog.role_menu_channel_id, 
                    role_selector_cog.role_menu_message_id
                )
            
            # Return to role management
            view = RoleManagementView(self.bot, self.user_id, self.visible)
            embed = await view.create_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            
        except Exception as e:
            self.bot.log.error(f"Error removing role: {e}", exc_info=True)
            await interaction.response.send_message("❌ Er is een fout opgetreden bij het verwijderen van de rol.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Configure(bot))