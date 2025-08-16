import discord
from discord.ext import commands
import datetime


class AddDeveloperModal(discord.ui.Modal):
    """Modal for adding a developer by ID."""
    
    def __init__(self, bot, user_id: int):
        super().__init__(title="Ontwikkelaar Toevoegen")
        self.bot = bot
        self.user_id = user_id
        
    developer_id = discord.ui.TextInput(
        label="Ontwikkelaar ID",
        placeholder="Voer het Discord ID van de ontwikkelaar in...",
        required=True,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle the modal submission."""
        try:
            # Validate the ID
            try:
                dev_id = int(self.developer_id.value.strip())
            except ValueError:
                await interaction.response.send_message("❌ Ongeldig ID formaat. Voer een geldig Discord ID in.", ephemeral=True)
                return
            
            # Get current developer IDs
            settings = await self.bot.db.settings.find_one({"_id": "server_settings"}) or {}
            dev_ids = settings.get("developer_ids", [])
            
            if dev_id in dev_ids:
                await interaction.response.send_message(f"❌ Gebruiker met ID `{dev_id}` is al een ontwikkelaar.", ephemeral=True)
                return
            
            # Try to get user info
            user = self.bot.get_user(dev_id)
            if not user:
                try:
                    user = await self.bot.fetch_user(dev_id)
                except discord.NotFound:
                    await interaction.response.send_message(f"❌ Geen gebruiker gevonden met ID `{dev_id}`.", ephemeral=True)
                    return
            
            # Add the new developer
            dev_ids.append(dev_id)
            
            await self.bot.db.settings.update_one(
                {"_id": "server_settings"},
                {"$set": {"developer_ids": dev_ids}},
                upsert=True
            )
            
            embed = discord.Embed(
                title="✅ Ontwikkelaar Toegevoegd",
                description=f"**{user.display_name}** is toegevoegd als ontwikkelaar.",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(
                name="👨‍💻 Nieuwe Ontwikkelaar",
                value=f"**Naam:** {user.display_name}\n**ID:** `{user.id}`",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.bot.log.error(f"Error adding developer: {e}", exc_info=True)
            await interaction.response.send_message("❌ Er is een fout opgetreden bij het toevoegen van de ontwikkelaar.", ephemeral=True)


class RemoveDeveloperSelect(discord.ui.Select):
    """Select dropdown for removing developers."""
    
    def __init__(self, bot, dev_ids: list):
        self.bot = bot
        
        # Create options from developer IDs
        options = []
        for dev_id in dev_ids[:25]:  # Discord limit of 25 options
            user = bot.get_user(dev_id)
            if user:
                options.append(discord.SelectOption(
                    label=user.display_name,
                    value=str(dev_id),
                    description=f"ID: {dev_id}",
                    emoji="👨‍💻"
                ))
            else:
                options.append(discord.SelectOption(
                    label=f"Onbekende gebruiker",
                    value=str(dev_id),
                    description=f"ID: {dev_id}",
                    emoji="❓"
                ))
        
        super().__init__(
            placeholder="Selecteer ontwikkelaars om te verwijderen...",
            options=options,
            min_values=1,
            max_values=len(options)
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle developer removal."""
        try:
            # Get current developer IDs
            settings = await self.bot.db.settings.find_one({"_id": "server_settings"}) or {}
            dev_ids = settings.get("developer_ids", [])
            
            # Remove selected developers
            removed_devs = []
            for selected_id in self.values:
                dev_id = int(selected_id)
                if dev_id in dev_ids:
                    dev_ids.remove(dev_id)
                    user = self.bot.get_user(dev_id)
                    if user:
                        removed_devs.append(f"**{user.display_name}** (`{dev_id}`)")
                    else:
                        removed_devs.append(f"**Onbekende gebruiker** (`{dev_id}`)")
            
            if not removed_devs:
                await interaction.response.send_message("❌ Geen geldige ontwikkelaars geselecteerd.", ephemeral=True)
                return
            
            # Update database
            await self.bot.db.settings.update_one(
                {"_id": "server_settings"},
                {"$set": {"developer_ids": dev_ids}},
                upsert=True
            )
            
            embed = discord.Embed(
                title="✅ Ontwikkelaars Verwijderd",
                description=f"{len(removed_devs)} ontwikkelaar(s) verwijderd:",
                color=discord.Color.orange(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(
                name="👨‍💻 Verwijderde Ontwikkelaars",
                value="\n".join(removed_devs),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.bot.log.error(f"Error removing developers: {e}", exc_info=True)
            await interaction.response.send_message("❌ Er is een fout opgetreden bij het verwijderen van ontwikkelaars.", ephemeral=True)


class RemoveDeveloperView(discord.ui.View):
    """View for removing developers."""
    
    def __init__(self, bot, user_id: int, dev_ids: list):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        
        if dev_ids:
            self.add_item(RemoveDeveloperSelect(bot, dev_ids))
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user has permission to use this view."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Je hebt geen toestemming om deze actie uit te voeren.", ephemeral=True)
            return False
        return True


class DeveloperManagementView(discord.ui.View):
    """Main developer management view."""
    
    def __init__(self, bot, user_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user has permission to use this view."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Je hebt geen toestemming om deze configuratie te gebruiken.", ephemeral=True)
            return False
        return True
    
    async def create_embed(self):
        """Create the developer management embed."""
        try:
            settings = await self.bot.db.settings.find_one({"_id": "server_settings"}) or {}
            dev_ids = settings.get("developer_ids", [])
            
            embed = discord.Embed(
                title="👨‍💻 Ontwikkelaars Beheren",
                description="Beheer de ontwikkelaars van de bot",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            
            if dev_ids:
                dev_list = []
                for dev_id in dev_ids:
                    user = self.bot.get_user(dev_id)
                    if user:
                        dev_list.append(f"• **{user.display_name}** (`{user.id}`)")
                    else:
                        dev_list.append(f"• **Onbekende gebruiker** (`{dev_id}`)")
                
                embed.add_field(
                    name=f"📋 Huidige Ontwikkelaars ({len(dev_ids)})",
                    value="\n".join(dev_list),
                    inline=False
                )
            else:
                embed.add_field(
                    name="📋 Huidige Ontwikkelaars",
                    value="Geen ontwikkelaars ingesteld",
                    inline=False
                )
            
            embed.add_field(
                name="ℹ️ Instructies",
                value=(
                    "• Gebruik **Toevoegen** om een ontwikkelaar toe te voegen via ID\n"
                    "• Gebruik **Verwijderen** om ontwikkelaars te selecteren en verwijderen\n"
                    "• Alleen administrators kunnen ontwikkelaars beheren"
                ),
                inline=False
            )
            
            embed.set_footer(text="Gebruik de knoppen hieronder om ontwikkelaars te beheren")
            return embed
            
        except Exception as e:
            self.bot.log.error(f"Error creating developer management embed: {e}", exc_info=True)
            raise
    
    @discord.ui.button(label="Toevoegen", style=discord.ButtonStyle.success, emoji="➕")
    async def add_developer(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open modal to add a developer."""
        modal = AddDeveloperModal(self.bot, self.user_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Verwijderen", style=discord.ButtonStyle.danger, emoji="➖")
    async def remove_developer(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show dropdown to remove developers."""
        try:
            # Get current developer IDs
            settings = await self.bot.db.settings.find_one({"_id": "server_settings"}) or {}
            dev_ids = settings.get("developer_ids", [])
            
            if not dev_ids:
                await interaction.response.send_message("❌ Geen ontwikkelaars om te verwijderen.", ephemeral=True)
                return
            
            view = RemoveDeveloperView(self.bot, self.user_id, dev_ids)
            
            embed = discord.Embed(
                title="➖ Ontwikkelaars Verwijderen",
                description="Selecteer de ontwikkelaars die je wilt verwijderen uit de dropdown hieronder.",
                color=discord.Color.orange()
            )
            embed.set_footer(text="Je kunt meerdere ontwikkelaars tegelijk selecteren")
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            self.bot.log.error(f"Error showing remove developer menu: {e}", exc_info=True)
            await interaction.response.send_message("❌ Er is een fout opgetreden.", ephemeral=True)
    
    @discord.ui.button(label="Vernieuwen", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh the developer list."""
        try:
            embed = await self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        except Exception as e:
            self.bot.log.error(f"Error refreshing developer list: {e}", exc_info=True)
            await interaction.response.send_message("❌ Er is een fout opgetreden bij het vernieuwen.", ephemeral=True)


class DeveloperManagement(commands.Cog):
    """Developer management with interactive menus."""
    
    def __init__(self, bot):
        self.bot = bot


async def setup(bot):
    await bot.add_cog(DeveloperManagement(bot))