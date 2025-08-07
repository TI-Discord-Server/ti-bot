import discord
from discord import app_commands
from discord.ext import commands
from typing import List, Dict, Optional, Union, Any
import asyncio

from utils.has_role import has_role

class RoleCategory:
    def __init__(self, name: str, roles: List[Dict[str, Union[str, int]]] = None):
        self.name = name
        self.roles = roles or []
    
    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            name=data.get("name", ""),
            roles=data.get("roles", [])
        )
    
    def to_dict(self):
        return {
            "name": self.name,
            "roles": self.roles
        }

class CategorySelect(discord.ui.Select):
    def __init__(self, role_selector, categories):
        options = [
            discord.SelectOption(label=category.name, value=category.name)
            for category in categories
        ]
        super().__init__(
            placeholder="Kies een categorie...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="category_select"
        )
        self.role_selector = role_selector
    
    async def callback(self, interaction: discord.Interaction):
        # Get the selected category
        selected_category = self.values[0]
        
        # Create a role select menu for the selected category
        await self.role_selector.show_role_select(interaction, selected_category)

class RoleSelect(discord.ui.Select):
    def __init__(self, role_selector, category_name, roles, user_roles):
        self.role_selector = role_selector
        self.category_name = category_name
        
        # Create options for each role
        options = []
        for role_data in roles:
            # Check if the user has this role
            has_role = any(role.name == role_data["role_name"] for role in user_roles)
            
            # Create the option
            option = discord.SelectOption(
                label=role_data["name"],
                value=role_data["role_name"],
                emoji=role_data["emoji"] if not role_data["emoji"].startswith(":") else None,
                default=has_role  # Pre-select roles the user already has
            )
            options.append(option)
        
        super().__init__(
            placeholder=f"Selecteer rollen voor {category_name}...",
            min_values=0,
            max_values=len(options),
            options=options,
            custom_id=f"role_select_{category_name}"
        )
    
    async def callback(self, interaction: discord.Interaction):
        # Get the guild and member
        guild = interaction.guild
        member = interaction.user
        
        # Get all roles in this category
        categories = await self.role_selector.get_categories()
        category = next((c for c in categories if c.name == self.category_name), None)
        if not category:
            await interaction.response.send_message("Deze categorie bestaat niet meer.", ephemeral=True)
            return
        
        # Get all role names in this category
        category_role_names = [role_data["role_name"] for role_data in category.roles]
        
        # Get the roles the user selected
        selected_role_names = self.values
        
        # Get the actual role objects
        roles_to_add = []
        roles_to_remove = []
        
        for role_name in category_role_names:
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                continue
            
            if role_name in selected_role_names and role not in member.roles:
                roles_to_add.append(role)
            elif role_name not in selected_role_names and role in member.roles:
                roles_to_remove.append(role)
        
        # Add and remove roles
        added_roles = []
        removed_roles = []
        
        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add, reason="Role selector")
                added_roles = [role.name for role in roles_to_add]
            except discord.Forbidden:
                await interaction.response.send_message("Ik heb geen toestemming om rollen toe te voegen.", ephemeral=True)
                return
        
        if roles_to_remove:
            try:
                await member.remove_roles(*roles_to_remove, reason="Role selector")
                removed_roles = [role.name for role in roles_to_remove]
            except discord.Forbidden:
                await interaction.response.send_message("Ik heb geen toestemming om rollen te verwijderen.", ephemeral=True)
                return
        
        # Send a confirmation message
        message = ""
        if added_roles:
            message += f"Toegevoegde rollen: {', '.join(added_roles)}\n"
        if removed_roles:
            message += f"Verwijderde rollen: {', '.join(removed_roles)}\n"
        
        if not message:
            message = "Geen wijzigingen aangebracht."
        
        # Update the view with the new role selections
        await self.role_selector.show_role_select(interaction, self.category_name, message)

class RoleSelectorView(discord.ui.View):
    def __init__(self, role_selector):
        super().__init__(timeout=None)
        self.role_selector = role_selector
    
    async def refresh(self, categories):
        # Clear existing items
        self.clear_items()
        
        # Add the category select
        self.add_item(CategorySelect(self.role_selector, categories))
        
        return self

class RoleSelector(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_menu_message_id = None
        self.role_menu_channel_id = None
        self.views = {}  # Store views by message ID
        self.default_categories = [
            RoleCategory("Campussen", [
                {"name": "Gent", "emoji": "🏙️", "role_name": "Gent"},
                {"name": "Aalst", "emoji": "🏢", "role_name": "Aalst"},
                {"name": "Virtual Class", "emoji": "💻", "role_name": "Virtual Class"},
                {"name": "TIAO", "emoji": "🧠", "role_name": "TIAO"}
            ]),
            RoleCategory("Studiejaren", [
                {"name": "1e jaar", "emoji": "1️⃣", "role_name": "1e jaar"},
                {"name": "2e jaar", "emoji": "2️⃣", "role_name": "2e jaar"},
                {"name": "3e jaar", "emoji": "3️⃣", "role_name": "3e jaar"}
            ]),
            RoleCategory("Studentenrollen", [
                {"name": "IOEM", "emoji": "🤓", "role_name": "IOEM"},
                {"name": "Buitenlandse Stage", "emoji": "✈️", "role_name": "Buitenlandse Stage"},
                {"name": "Erasmus", "emoji": "🛫", "role_name": "Erasmus"},
                {"name": "Graduaat", "emoji": "🎓", "role_name": "Graduaat"}
            ]),
            RoleCategory("Fun Rollen", [
                {"name": "Gamer", "emoji": "🎮", "role_name": "Gamer"},
                {"name": "Anime", "emoji": "🇯🇵", "role_name": "Anime"},
                {"name": "Fun", "emoji": "😂", "role_name": "Fun"}
            ]),
            RoleCategory("Updates", [
                {"name": "Low Priority", "emoji": "✅", "role_name": "Low Priority"}
            ])
        ]
    
    async def cog_load(self):
        """Initialize the role selector when the cog is loaded."""
        # Create the collection if it doesn't exist
        collections = await self.bot.db.list_collection_names()
        if "role_selector" not in collections:
            await self.bot.db.create_collection("role_selector")
        
        # Load the role menu message ID and channel ID from the database
        config = await self.bot.db.role_selector.find_one({"_id": "config"})
        if config:
            self.role_menu_message_id = config.get("message_id")
            self.role_menu_channel_id = config.get("channel_id")
        
        # Load or initialize categories
        categories = await self.bot.db.role_selector.find_one({"_id": "categories"})
        if not categories:
            # Initialize with default categories
            await self.bot.db.role_selector.insert_one({
                "_id": "categories",
                "categories": [category.to_dict() for category in self.default_categories]
            })
        
        # Setup persistent view
        self.bot.add_view(RoleSelectorView(self))
    
    # Using the has_role decorator instead of a separate method
    
    async def get_categories(self) -> List[RoleCategory]:
        """Get all role categories from the database."""
        categories_doc = await self.bot.db.role_selector.find_one({"_id": "categories"})
        if not categories_doc:
            return self.default_categories
        
        return [RoleCategory.from_dict(category) for category in categories_doc.get("categories", [])]
    
    async def save_categories(self, categories: List[RoleCategory]):
        """Save categories to the database."""
        await self.bot.db.role_selector.update_one(
            {"_id": "categories"},
            {"$set": {"categories": [category.to_dict() for category in categories]}},
            upsert=True
        )
    
    async def update_role_menu_message(self, channel_id: int, message_id: int = None):
        """Update or create the role menu message."""
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return None
        
        # Create the embed
        embed = discord.Embed(
            title="🎭 Kies je rollen!",
            description="Selecteer een categorie in het dropdown menu hieronder om rollen te kiezen.",
            color=discord.Color.blue()
        )
        
        categories = await self.get_categories()
        for category in categories:
            role_list = []
            for role in category.roles:
                role_list.append(f"{role['emoji']} → @{role['role_name']}")
            
            embed.add_field(
                name=f"**{category.name}**",
                value="\n".join(role_list) if role_list else "Geen rollen beschikbaar",
                inline=False
            )
        
        embed.set_footer(text="Gebruik het dropdown menu om een categorie te selecteren")
        
        # Create the view
        view = await RoleSelectorView(self).refresh(categories)
        
        # Update existing message or create a new one
        if message_id:
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(embed=embed, view=view)
                return message
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
        
        # Create a new message if we couldn't edit the existing one
        message = await channel.send(embed=embed, view=view)
        
        # Save the message ID and channel ID
        await self.bot.db.role_selector.update_one(
            {"_id": "config"},
            {"$set": {"message_id": message.id, "channel_id": channel.id}},
            upsert=True
        )
        
        self.role_menu_message_id = message.id
        self.role_menu_channel_id = channel.id
        self.views[message.id] = view
        
        return message
    
    async def show_role_select(self, interaction: discord.Interaction, category_name: str, message: str = None):
        """Show the role select menu for a category."""
        # Get the categories
        categories = await self.get_categories()
        
        # Find the selected category
        category = next((c for c in categories if c.name == category_name), None)
        if not category:
            await interaction.response.send_message("Deze categorie bestaat niet.", ephemeral=True)
            return
        
        # Create a new view
        view = discord.ui.View(timeout=180)
        
        # Add a back button to return to category selection
        back_button = discord.ui.Button(label="Terug naar categorieën", style=discord.ButtonStyle.secondary, custom_id="back_button")
        
        async def back_button_callback(back_interaction: discord.Interaction):
            # Create a new view with the category select
            category_view = discord.ui.View(timeout=180)
            category_view.add_item(CategorySelect(self, categories))
            
            # Create embed for category selection
            embed = discord.Embed(
                title="🎭 Rolselectie",
                description="Kies een categorie om rollen te beheren.",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Selecteer een categorie uit het dropdown menu")
            
            await back_interaction.response.edit_message(
                embed=embed,
                view=category_view
            )
        
        back_button.callback = back_button_callback
        view.add_item(back_button)
        
        # Add the role select menu
        view.add_item(RoleSelect(self, category_name, category.roles, interaction.user.roles))
        
        # Create embed for role selection
        embed = discord.Embed(
            title=f"🎭 Rolselectie - {category_name}",
            description="Selecteer de rollen die je wilt hebben. Deselecteer rollen die je wilt verwijderen.",
            color=discord.Color.green()
        )
        
        if message:
            embed.add_field(name="Status", value=message, inline=False)
        
        # Add available roles to the embed
        role_list = []
        for role in category.roles:
            user_has_role = any(user_role.name == role["role_name"] for user_role in interaction.user.roles)
            status = "✅" if user_has_role else "❌"
            role_list.append(f"{status} {role['emoji']} {role['name']}")
        
        if role_list:
            embed.add_field(
                name="Beschikbare Rollen",
                value="\n".join(role_list),
                inline=False
            )
        
        embed.set_footer(text="Gebruik het dropdown menu om rollen te selecteren/deselecteren")
        
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="setup_role_menu", description="Maak het rolselectie menu")
    async def setup_role_menu(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Setup the role selection menu in the specified channel."""
        # Check if the user has the required role
        council_role = discord.utils.get(interaction.guild.roles, name="The Council")
        if council_role not in interaction.user.roles:
            await interaction.response.send_message("Je hebt de 'The Council' rol nodig om dit commando te gebruiken.", ephemeral=True)
            return
        
        # Use the current channel if none is specified
        if not channel:
            channel = interaction.channel
        
        await interaction.response.defer(ephemeral=True)
        
        # Create or update the role menu message
        message = await self.update_role_menu_message(channel.id, self.role_menu_message_id)
        
        if message:
            await interaction.followup.send(f"Rolselectie menu is aangemaakt in {channel.mention}!", ephemeral=True)
        else:
            await interaction.followup.send("Kon het rolselectie menu niet aanmaken.", ephemeral=True)
    
    @app_commands.command(name="add_role_category", description="Voeg een nieuwe rolcategorie toe")
    @has_role("The Council", "Je hebt de 'The Council' rol nodig om dit commando te gebruiken.")
    async def add_role_category(self, interaction: discord.Interaction, name: str):
        """Add a new role category."""
        
        # Get existing categories
        categories = await self.get_categories()
        
        # Check if the category already exists
        if any(category.name.lower() == name.lower() for category in categories):
            await interaction.response.send_message(f"Categorie '{name}' bestaat al.", ephemeral=True)
            return
        
        # Add the new category
        categories.append(RoleCategory(name))
        await self.save_categories(categories)
        
        # Update the role menu message
        if self.role_menu_channel_id:
            await self.update_role_menu_message(self.role_menu_channel_id, self.role_menu_message_id)
        
        await interaction.response.send_message(f"Categorie '{name}' is toegevoegd.", ephemeral=True)
    
    @app_commands.command(name="remove_role_category", description="Verwijder een rolcategorie")
    @has_role("The Council", "Je hebt de 'The Council' rol nodig om dit commando te gebruiken.")
    async def remove_role_category(self, interaction: discord.Interaction, name: str):
        """Remove a role category."""
        
        # Get existing categories
        categories = await self.get_categories()
        
        # Find the category to remove
        category_index = None
        for i, category in enumerate(categories):
            if category.name.lower() == name.lower():
                category_index = i
                break
        
        if category_index is None:
            await interaction.response.send_message(f"Categorie '{name}' niet gevonden.", ephemeral=True)
            return
        
        # Remove the category
        categories.pop(category_index)
        await self.save_categories(categories)
        
        # Update the role menu message
        if self.role_menu_channel_id:
            await self.update_role_menu_message(self.role_menu_channel_id, self.role_menu_message_id)
        
        await interaction.response.send_message(f"Categorie '{name}' is verwijderd.", ephemeral=True)
    
    @app_commands.command(name="add_role", description="Voeg een rol toe aan een categorie")
    @has_role("The Council", "Je hebt de 'The Council' rol nodig om dit commando te gebruiken.")
    async def add_role(self, interaction: discord.Interaction, category_name: str, role: discord.Role, emoji: str, display_name: str = None):
        """Add a role to a category."""
        
        # Get existing categories
        categories = await self.get_categories()
        
        # Find the category
        category = None
        for c in categories:
            if c.name.lower() == category_name.lower():
                category = c
                break
        
        if not category:
            await interaction.response.send_message(f"Categorie '{category_name}' niet gevonden.", ephemeral=True)
            return
        
        # Check if the role is already in the category
        if any(r['role_name'] == role.name for r in category.roles):
            await interaction.response.send_message(f"Rol '{role.name}' zit al in categorie '{category_name}'.", ephemeral=True)
            return
        
        # Add the role to the category
        category.roles.append({
            "name": display_name or role.name,
            "emoji": emoji,
            "role_name": role.name
        })
        
        await self.save_categories(categories)
        
        # Update the role menu message
        if self.role_menu_channel_id:
            await self.update_role_menu_message(self.role_menu_channel_id, self.role_menu_message_id)
        
        await interaction.response.send_message(f"Rol '{role.name}' is toegevoegd aan categorie '{category_name}'.", ephemeral=True)
    
    @app_commands.command(name="remove_role", description="Verwijder een rol uit een categorie")
    @has_role("The Council", "Je hebt de 'The Council' rol nodig om dit commando te gebruiken.")
    async def remove_role(self, interaction: discord.Interaction, category_name: str, role_name: str):
        """Remove a role from a category."""
        
        # Get existing categories
        categories = await self.get_categories()
        
        # Find the category
        category = None
        for c in categories:
            if c.name.lower() == category_name.lower():
                category = c
                break
        
        if not category:
            await interaction.response.send_message(f"Categorie '{category_name}' niet gevonden.", ephemeral=True)
            return
        
        # Find the role to remove
        role_index = None
        for i, role in enumerate(category.roles):
            if role['role_name'].lower() == role_name.lower():
                role_index = i
                break
        
        if role_index is None:
            await interaction.response.send_message(f"Rol '{role_name}' niet gevonden in categorie '{category_name}'.", ephemeral=True)
            return
        
        # Remove the role
        category.roles.pop(role_index)
        await self.save_categories(categories)
        
        # Update the role menu message
        if self.role_menu_channel_id:
            await self.update_role_menu_message(self.role_menu_channel_id, self.role_menu_message_id)
        
        await interaction.response.send_message(f"Rol '{role_name}' is verwijderd uit categorie '{category_name}'.", ephemeral=True)
    
    @app_commands.command(name="list_role_categories", description="Toon alle rolcategorieën")
    @has_role("The Council", "Je hebt de 'The Council' rol nodig om dit commando te gebruiken.")
    async def list_role_categories(self, interaction: discord.Interaction):
        """List all role categories."""
        
        # Get existing categories
        categories = await self.get_categories()
        
        if not categories:
            await interaction.response.send_message("Er zijn geen rolcategorieën.", ephemeral=True)
            return
        
        # Create a message with all categories and their roles
        message = "# Rolcategorieën\n\n"
        
        for category in categories:
            message += f"## {category.name}\n"
            
            if not category.roles:
                message += "Geen rollen in deze categorie.\n\n"
                continue
            
            for role in category.roles:
                message += f"{role['emoji']} **{role['name']}** → @{role['role_name']}\n"
            
            message += "\n"
        
        await interaction.response.send_message(message, ephemeral=True)

async def setup(bot):
    bot.log.info("Setting up RoleSelector cog")
    cog = RoleSelector(bot)
    await bot.add_cog(cog)
    bot.log.info("RoleSelector cog added successfully")
    
    # Log the commands that are registered
    commands = [cmd.name for cmd in cog.__cog_app_commands__]
    bot.log.info(f"Registered commands in RoleSelector: {commands}")