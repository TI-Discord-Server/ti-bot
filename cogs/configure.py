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
        embed = await self.create_main_embed()
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def create_main_embed(self):
        """Create the main configuration embed."""
        embed = discord.Embed(
            title="🔧 Bot Configuratie",
            description="Selecteer een categorie om de instellingen te bekijken en aan te passen.",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
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
        return embed


class ServerConfigView(BaseConfigView):
    """Server configuration view."""
    
    async def create_embed(self):
        """Create server configuration embed."""
        settings = await self.bot.db.settings.find_one({"_id": "server_settings"}) or {}
        
        embed = discord.Embed(
            title="🏠 Server Instellingen",
            description="Basis server configuratie instellingen",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        
        # Show current guild (auto-detected or configured)
        current_guild = self.bot.guild
        configured_guild_id = settings.get("guild_id", None)
        
        if current_guild:
            if configured_guild_id:
                guild_status = f"**Geconfigureerd:** {current_guild.name} (`{current_guild.id}`)"
            else:
                guild_status = f"**Auto-gedetecteerd:** {current_guild.name} (`{current_guild.id}`)"
        else:
            guild_status = "Geen server gevonden"
            
        embed.add_field(
            name="🏠 Huidige Server",
            value=guild_status,
            inline=False
        )
        
        # Show multi-guild info if applicable
        if len(self.bot.guilds) > 1:
            embed.add_field(
                name="ℹ️ Multi-Server Info",
                value=f"Bot is in {len(self.bot.guilds)} servers. Configureer een specifieke server ID als de auto-detectie niet correct is.",
                inline=False
            )
        
        # Developer IDs
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
        
        embed.set_footer(text="Gebruik de knoppen hieronder om instellingen aan te passen")
        return embed
    
    @discord.ui.button(label="Server ID overschrijven", style=discord.ButtonStyle.secondary, emoji="🏠")
    async def set_guild_id(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Override auto-detected guild ID."""
        modal = GuildIdModal(self.bot, self.user_id, self.visible)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Ontwikkelaars beheren", style=discord.ButtonStyle.primary, emoji="👨‍💻")
    async def manage_developers(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Manage developer IDs."""
        modal = DeveloperIdsModal(self.bot, self.user_id, self.visible)
        await interaction.response.send_modal(modal)


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
        
        # Unverified role
        unverified_role_id = settings.get("unverified_role_id", "Niet ingesteld")
        if unverified_role_id != "Niet ingesteld":
            unverified_role_name = f"<@&{unverified_role_id}>"
        else:
            unverified_role_name = "Niet ingesteld"
            
        embed.add_field(
            name="❌ Niet-geverifieerde Rol",
            value=f"`{unverified_role_id}`\n**Rol:** {unverified_role_name}",
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
    
    @discord.ui.button(label="Niet-geverifieerde Rol", style=discord.ButtonStyle.danger, emoji="❌")
    async def set_unverified_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set unverified role."""
        view = RoleSelectView(self.bot, self.user_id, "verification_settings", "unverified_role_id")
        embed = discord.Embed(
            title="❌ Niet-geverifieerde Rol Selecteren",
            description="Selecteer de rol die niet-geverifieerde gebruikers krijgen.",
            color=discord.Color.red()
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
        
        # Moderator ID (single user)
        moderator_id = settings.get("moderator_id", "Niet ingesteld")
        if moderator_id != "Niet ingesteld":
            moderator = self.bot.get_user(moderator_id)
            moderator_name = moderator.mention if moderator else f"Onbekende gebruiker ({moderator_id})"
        else:
            moderator_name = "Niet ingesteld"
            
        embed.add_field(
            name="👤 Hoofd Moderator",
            value=f"`{moderator_id}`\n**Gebruiker:** {moderator_name}",
            inline=True
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
    
    @discord.ui.button(label="Hoofd Moderator", style=discord.ButtonStyle.primary, emoji="👤")
    async def set_moderator(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set main moderator."""
        modal = ModeratorIdModal(self.bot, self.user_id, self.visible)
        await interaction.response.send_modal(modal)
    
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
        
        embed.add_field(
            name="ℹ️ Informatie",
            value=(
                "Deze instellingen worden automatisch beheerd door de rol en kanaal menu systemen.\n"
                "Gebruik de setup commando's om deze systemen in te stellen:\n"
                "• `/setup component:Role Menu`\n"
                "• `/setup component:Channel Menu`"
            ),
            inline=False
        )
        
        embed.set_footer(text="Deze categorie heeft momenteel geen configureerbare instellingen")
        return embed


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


class DeveloperIdsModal(discord.ui.Modal):
    """Modal for setting developer IDs."""
    
    def __init__(self, bot, user_id: int, visible: bool):
        super().__init__(title="Ontwikkelaars Beheren")
        self.bot = bot
        self.user_id = user_id
        self.visible = visible
        
        self.dev_ids_input = discord.ui.TextInput(
            label="Ontwikkelaar IDs",
            placeholder="Voer gebruiker IDs in, gescheiden door komma's...",
            required=True,
            style=discord.TextStyle.paragraph,
            max_length=1000
        )
        self.add_item(self.dev_ids_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            id_strings = [id_str.strip() for id_str in self.dev_ids_input.value.split(",")]
            dev_ids = [int(id_str) for id_str in id_strings if id_str]
            
            await self.bot.db.settings.update_one(
                {"_id": "server_settings"},
                {"$set": {"developer_ids": dev_ids}},
                upsert=True
            )
            
            view = ServerConfigView(self.bot, self.user_id, self.visible)
            embed = await view.create_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            
        except ValueError:
            await interaction.response.send_message("❌ Ongeldige gebruiker IDs. Voer geldige nummers in, gescheiden door komma's.", ephemeral=True)


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


class ModeratorIdModal(discord.ui.Modal):
    """Modal for setting moderator ID."""
    
    def __init__(self, bot, user_id: int, visible: bool):
        super().__init__(title="Hoofd Moderator Instellen")
        self.bot = bot
        self.user_id = user_id
        self.visible = visible
        
        self.moderator_id_input = discord.ui.TextInput(
            label="Moderator Gebruiker ID",
            placeholder="Voer de gebruiker ID van de hoofd moderator in...",
            required=True,
            max_length=20
        )
        self.add_item(self.moderator_id_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            moderator_id = int(self.moderator_id_input.value)
            
            await self.bot.db.settings.update_one(
                {"_id": "mod_settings"},
                {"$set": {"moderator_id": moderator_id}},
                upsert=True
            )
            
            view = ModerationConfigView(self.bot, self.user_id, self.visible)
            embed = await view.create_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            
        except ValueError:
            await interaction.response.send_message("❌ Ongeldige gebruiker ID. Voer een geldig nummer in.", ephemeral=True)


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
        view = ConfigurationView(self.bot, interaction.user.id, visible)
        embed = await view.create_main_embed()
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=not visible)





async def setup(bot):
    await bot.add_cog(Configure(bot))