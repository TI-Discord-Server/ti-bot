import discord
from discord import app_commands
from discord.ext import commands
from utils.has_admin import has_admin


class YearSelect(discord.ui.Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            discord.SelectOption(
                label="1e Jaar", 
                description="Eerste jaar vakken", 
                emoji="🟩",
                value="1"
            ),
            discord.SelectOption(
                label="2e Jaar", 
                description="Tweede jaar vakken", 
                emoji="🟨",
                value="2"
            ),
            discord.SelectOption(
                label="3e Jaar", 
                description="Derde jaar vakken", 
                emoji="🟥",
                value="3"
            ),
        ]
        super().__init__(
            placeholder="Selecteer je jaar...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="year_select"
        )

    async def callback(self, interaction: discord.Interaction):
        # Get the selected year
        year = self.values[0]
        
        # Get all channels in the selected year category
        year_emoji_map = {"1": "🟩", "2": "🟨", "3": "🟥"}
        category_name = f"━━━ {year_emoji_map[year]} {year}E JAAR ━━━"
        
        category = discord.utils.get(interaction.guild.categories, name=category_name)
        if not category:
            await interaction.response.send_message(
                f"Category {category_name} not found. Please contact an administrator.",
                ephemeral=True
            )
            return
        
        # Get all text channels in this category
        channels = [channel for channel in category.channels if isinstance(channel, discord.TextChannel)]
        
        if not channels:
            await interaction.response.send_message(
                f"No channels found in {category_name}. Please contact an administrator.",
                ephemeral=True
            )
            return
        
        # Get the user's current roles for this year's channels
        user_roles = interaction.user.roles
        user_channel_roles = []
        
        # Check which channels the user already has access to
        for channel in channels:
            # Format the channel name with spaces and proper capitalization
            formatted_name = ' '.join(word.capitalize() for word in channel.name.replace('-', ' ').split())
            
            # Check if the user has a role with this name
            if discord.utils.get(user_roles, name=formatted_name):
                user_channel_roles.append(formatted_name)
            
            # Also check for other naming patterns
            access_role_name = f"access-{channel.name}"
            if discord.utils.get(user_roles, name=access_role_name):
                user_channel_roles.append(formatted_name)
                
            # Check for exact match with channel name
            if discord.utils.get(user_roles, name=channel.name):
                user_channel_roles.append(formatted_name)
                
            # Check for custom roles containing the channel name
            for role in user_roles:
                if channel.name.lower() in role.name.lower() and role.name not in ["Admin", "Moderator", "Bot", "everyone"]:
                    user_channel_roles.append(formatted_name)
                    break
        
        # Create a multi-select menu for the channels
        view = discord.ui.View(timeout=None)
        view.bot = self.bot  # Pass the bot reference to the view
        view.add_item(CourseSelect(channels, year, self.bot))
        
        # Create the message with current selections
        message = f"Je hebt jaar {year} geselecteerd. Selecteer nu je vakken:"
        
        if user_channel_roles:
            message += f"\n\n**Je huidige selecties:** {', '.join(user_channel_roles)}"
        
        await interaction.response.send_message(
            message,
            view=view,
            ephemeral=True
        )


class CourseSelect(discord.ui.Select):
    def __init__(self, channels, year, bot):
        self.year = year
        self.bot = bot
        
        # Create options from channels
        options = []
        for channel in channels:
            # Skip channels that start with certain prefixes (like general channels)
            if any(channel.name.startswith(prefix) for prefix in ["algemeen", "general", "announcements"]):
                continue
            
            # Format the channel name with spaces and proper capitalization
            # Convert "programmeren-1" to "Programmeren 1"
            formatted_name = ' '.join(word.capitalize() for word in channel.name.replace('-', ' ').split())
                
            options.append(
                discord.SelectOption(
                    label=formatted_name,
                    description=channel.name,  # Show original name as description
                    value=str(channel.id)
                )
            )
        
        super().__init__(
            placeholder="Selecteer je vakken...",
            min_values=0,
            max_values=min(len(options), 25),  # Discord has a max of 25 options that can be selected
            options=options,
            custom_id=f"course_select_{year}"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Get the selected channel IDs
        selected_channel_ids = self.values
        
        # Get all channels in the guild
        all_channels = interaction.guild.channels
        
        # Get the channels the user selected
        selected_channels = [
            channel for channel in all_channels 
            if str(channel.id) in selected_channel_ids
        ]
        
        try:
            # Get all channels in the year category
            year_emoji_map = {"1": "🟩", "2": "🟨", "3": "🟥"}
            category_name = f"━━━ {year_emoji_map[self.year]} {self.year}E JAAR ━━━"
            category = discord.utils.get(interaction.guild.categories, name=category_name)
            
            if not category:
                await interaction.followup.send(
                    f"Category {category_name} not found. Please contact an administrator.",
                    ephemeral=True
                )
                return
            
            year_channels = [
                channel for channel in category.channels 
                if isinstance(channel, discord.TextChannel) and
                not any(channel.name.startswith(prefix) for prefix in ["algemeen", "general", "announcements"])
            ]
            
            # Process each channel in the year category
            added_roles = []
            removed_roles = []
            
            for channel in year_channels:
                # First, try to find an existing role that has access to this channel
                existing_role = None
                
                # Get all roles that have explicit permissions for this channel
                overwrites = channel.overwrites
                
                # First, check if there's a role named after the channel (with proper capitalization)
                formatted_name = ' '.join(word.capitalize() for word in channel.name.replace('-', ' ').split())
                channel_specific_role = discord.utils.get(interaction.guild.roles, name=formatted_name)
                
                # Also check for common naming patterns for channel access roles
                access_role_name = f"access-{channel.name}"
                access_role = discord.utils.get(interaction.guild.roles, name=access_role_name)
                
                # Check for other common naming patterns
                channel_role_name = channel.name  # Exact match with channel name
                channel_role = discord.utils.get(interaction.guild.roles, name=channel_role_name)
                
                # Check for any role that contains the channel name (for custom roles)
                custom_role = None
                for role in interaction.guild.roles:
                    # Skip default roles and roles with common names
                    if role == interaction.guild.default_role or role.name in ["Admin", "Moderator", "Bot", "everyone"]:
                        continue
                    
                    # Check if the role name contains the channel name (case insensitive)
                    if channel.name.lower() in role.name.lower():
                        custom_role = role
                        break
                
                # If we found a role with the channel's name or a related naming pattern, use it
                if channel_specific_role:
                    existing_role = channel_specific_role
                elif access_role:
                    existing_role = access_role
                elif channel_role:
                    existing_role = channel_role
                elif custom_role:
                    existing_role = custom_role
                else:
                    # Look for roles that have explicit read_messages=True for this channel
                    for role_or_member, permissions in overwrites.items():
                        # Skip @everyone role and members
                        if role_or_member == interaction.guild.default_role or not isinstance(role_or_member, discord.Role):
                            continue
                        
                        # Check if this role has read_messages permission
                        if permissions.read_messages:
                            # Use this role
                            existing_role = role_or_member
                            break
                
                # If we found an existing role with the right permissions, use it
                if existing_role:
                    role = existing_role
                    # Make sure the role has the correct permissions
                    await channel.set_permissions(role, read_messages=True)
                else:
                    # Format the role name with spaces and proper capitalization
                    # Convert "programmeren-1" to "Programmeren 1"
                    formatted_name = ' '.join(word.capitalize() for word in channel.name.replace('-', ' ').split())
                    role_name = formatted_name
                    
                    # Find or create a role for this channel
                    role = discord.utils.get(interaction.guild.roles, name=role_name)
                    
                    # If role doesn't exist, create it
                    if not role:
                        # Create a role with the same color as the category
                        role_color = discord.Color.green() if self.year == "1" else discord.Color.gold() if self.year == "2" else discord.Color.red()
                        role = await interaction.guild.create_role(
                            name=role_name,
                            color=role_color,
                            mentionable=False,
                            reason=f"Created for channel access to {channel.name}"
                        )
                        
                        # Set permissions for this role on the channel
                        await channel.set_permissions(role, read_messages=True)
                        
                        # Hide the channel from @everyone
                        everyone_role = interaction.guild.default_role
                        await channel.set_permissions(everyone_role, read_messages=False)
                
                # Add or remove the role from the user
                if channel in selected_channels:
                    if role not in interaction.user.roles:
                        await interaction.user.add_roles(role, reason=f"User selected {channel.name} in channel menu")
                        added_roles.append(role)
                else:
                    if role in interaction.user.roles:
                        await interaction.user.remove_roles(role, reason=f"User deselected {channel.name} in channel menu")
                        removed_roles.append(role)
            
            # Send confirmation message
            if added_roles:
                added_channels = ", ".join([role.name for role in added_roles])
                if removed_roles:
                    removed_channels = ", ".join([role.name for role in removed_roles])
                    await interaction.followup.send(
                        f"Je hebt toegang gekregen tot: {added_channels}\n"
                        f"Je hebt geen toegang meer tot: {removed_channels}",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"Je hebt toegang gekregen tot: {added_channels}",
                        ephemeral=True
                    )
            elif removed_roles:
                removed_channels = ", ".join([role.name for role in removed_roles])
                await interaction.followup.send(
                    f"Je hebt geen toegang meer tot: {removed_channels}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "Er zijn geen wijzigingen aangebracht in je toegang tot vakken.",
                    ephemeral=True
                )
                
            # Add a message about how to manage roles
            await interaction.followup.send(
                "**Tip:** Om je toegang te beheren, gebruik dit menu opnieuw. "
                "Selecteer vakken om toegang te krijgen, deselecteer om toegang te verwijderen.",
                ephemeral=True
            )
                
        except discord.Forbidden:
            await interaction.followup.send(
                "Er is een fout opgetreden bij het instellen van de rollen. Neem contact op met een beheerder.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"Er is een onverwachte fout opgetreden: {str(e)}. Neem contact op met een beheerder.",
                ephemeral=True
            )


class YearSelectView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(YearSelect(bot))


class ChannelMenu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(
        name="setup_channel_menu",
        description="Setup the year and course selection menu"
    )
    @has_admin()
    async def setup_channel_menu(self, interaction: discord.Interaction):
        # First respond to the interaction to prevent timeout
        await interaction.response.defer(ephemeral=True)
        
        # Send the menu immediately
        view = YearSelectView(self.bot)
        menu_message = await interaction.channel.send(
            "# Kanaal Selectie\n"
            "Selecteer eerst je jaar, dan kun je kiezen welke vakken je wilt volgen.\n"
            "Je krijgt alleen toegang tot de kanalen die je selecteert.",
            view=view
        )
        
        # Now check and create categories in the background
        await interaction.followup.send("Menu is aangemaakt! Nu worden de categorieën gecontroleerd...", ephemeral=True)
        
        # Check if the required categories exist, create if not
        await self.ensure_categories_exist(interaction.guild)
        
        # Send a final confirmation
        await interaction.followup.send("Categorieën en kanalen zijn gecontroleerd en aangemaakt indien nodig.", ephemeral=True)
    
    async def ensure_categories_exist(self, guild):
        # Define the categories we need with test subjects
        required_categories = [
            {
                "name": "━━━ 🟩 1E JAAR ━━━", 
                "position": 0,
                "subjects": ["programmeren-1", "wiskunde-basis", "computernetwerken", "webdevelopment", "databases-intro"]
            },
            {
                "name": "━━━ 🟨 2E JAAR ━━━", 
                "position": 10,
                "subjects": ["programmeren-2", "algoritmen", "software-engineering", "databases-advanced", "operating-systems"]
            },
            {
                "name": "━━━ 🟥 3E JAAR ━━━", 
                "position": 20,
                "subjects": ["machine-learning", "security", "stage", "afstudeerproject", "web-frameworks"]
            }
        ]
        
        # Check if each category exists, create if not
        for cat_info in required_categories:
            category = discord.utils.get(guild.categories, name=cat_info["name"])
            if not category:
                # Create the category
                category = await guild.create_category(
                    name=cat_info["name"],
                    position=cat_info["position"]
                )
                
                # Only add test subjects to newly created categories
                for subject in cat_info["subjects"]:
                    await guild.create_text_channel(
                        name=subject,
                        category=category
                    )


async def setup(bot):
    await bot.add_cog(ChannelMenu(bot))