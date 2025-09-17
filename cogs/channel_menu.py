import discord
from discord import app_commands
from discord.ext import commands
from utils.has_admin import has_admin
from typing import Dict, List, Optional
import asyncio


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
        try:
            # Defer the interaction immediately to prevent timeout
            await interaction.response.defer(ephemeral=True)
        except discord.HTTPException as e:
            if e.code == 10062:  # Unknown interaction
                self.bot.log.warning(f"Interaction expired (10062) in YearSelect, cannot respond")
                return
            else:
                self.bot.log.error(f"Failed to defer interaction in YearSelect: {e}")
                return
        
        try:
            # Get the selected year
            year = self.values[0]
            
            # Get all channels in the selected year category
            year_emoji_map = {"1": "🟩", "2": "🟨", "3": "🟥"}
            category_name = f"━━━ {year_emoji_map[year]} {year}E JAAR ━━━"
            
            category = discord.utils.get(interaction.guild.categories, name=category_name)
            if not category:
                try:
                    await interaction.followup.send(
                        f"Categorie {category_name} niet gevonden. Neem contact op met een beheerder.",
                        ephemeral=True
                    )
                except discord.HTTPException as e:
                    if e.code == 10062:  # Unknown interaction
                        self.bot.log.warning(f"Interaction expired (10062) in YearSelect, cannot send error message")
                    else:
                        self.bot.log.error(f"Failed to send error message in YearSelect: {e}")
                return
            
            # Get all text channels in this category
            channels = [channel for channel in category.channels if isinstance(channel, discord.TextChannel)]
            
            if not channels:
                try:
                    await interaction.followup.send(
                        f"Geen kanalen gevonden in {category_name}. Neem contact op met een beheerder.",
                        ephemeral=True
                    )
                except discord.HTTPException as e:
                    if e.code == 10062:  # Unknown interaction
                        self.bot.log.warning(f"Interaction expired (10062) in YearSelect, cannot send error message")
                    else:
                        self.bot.log.error(f"Failed to send error message in YearSelect: {e}")
                return
            
            # Get the user's current roles for this year's channels using the cache
            channel_menu_cog = self.bot.get_cog('ChannelMenu')
        if channel_menu_cog:
            user_channel_roles = await channel_menu_cog.get_user_channel_roles(interaction.guild, interaction.user, channels)
        else:
            user_channel_roles = []
        
        # Create a paginated multi-select menu for the channels
        view = discord.ui.View(timeout=None)
        view.bot = self.bot  # Pass the bot reference to the view
        
        # Filter out general channels first
        filtered_channels = [
            channel for channel in channels 
            if not any(channel.name.startswith(prefix) for prefix in ["algemeen", "general", "announcements"])
        ]
        
        # Calculate pagination
        channels_per_page = 25
        total_pages = (len(filtered_channels) + channels_per_page - 1) // channels_per_page
        
        if total_pages <= 1:
            # No pagination needed
            view.add_item(CourseSelect(filtered_channels, year, self.bot, user_channel_roles, 0, 1))
        else:
            # Add pagination - start with first page
            page_channels = filtered_channels[:channels_per_page]
            view.add_item(CourseSelect(page_channels, year, self.bot, user_channel_roles, 0, total_pages))
            
            # Add navigation buttons
            view.add_item(PaginationButton("◀️", "prev", year, filtered_channels, user_channel_roles, 0, total_pages, disabled=True))
            view.add_item(PaginationButton("▶️", "next", year, filtered_channels, user_channel_roles, 0, total_pages, disabled=(total_pages <= 1)))
        
        # Create embed for course selection
        year_colors = {"1": discord.Color.green(), "2": discord.Color.gold(), "3": discord.Color.red()}
        year_emojis = {"1": "🟩", "2": "🟨", "3": "🟥"}
        
        # Update title to show pagination info if needed
        title = f"{year_emojis[year]} Jaar {year} - Vakselectie"
        if total_pages > 1:
            title += f" (Pagina 1/{total_pages})"
        
        embed = discord.Embed(
            title=title,
            description="Selecteer de vakken die je wilt volgen uit het dropdown menu hieronder.",
            color=year_colors[year]
        )
        
        if user_channel_roles:
            embed.add_field(
                name="✅ Je huidige selecties",
                value=", ".join(user_channel_roles),
                inline=False
            )
        else:
            embed.add_field(
                name="ℹ️ Info",
                value="Je hebt nog geen vakken geselecteerd.",
                inline=False
            )
        
        # Add pagination info if multiple pages
        if total_pages > 1:
            page_channels = filtered_channels[:channels_per_page]
            embed.add_field(
                name="📄 Paginatie",
                value=f"Pagina 1 van {total_pages} ({len(page_channels)} vakken op deze pagina)\nGebruik de ◀️ ▶️ knoppen om tussen pagina's te navigeren.",
                inline=False
            )
        
        embed.set_footer(text="Selecteer vakken om toegang te krijgen, deselecteer om toegang te verwijderen")
        
        try:
            await interaction.followup.send(
                embed=embed,
                view=view,
                ephemeral=True
            )
        except discord.HTTPException as e:
            if e.code == 10062:  # Unknown interaction
                self.bot.log.warning(f"Interaction expired (10062) in YearSelect, cannot send final response")
                # Interaction expired, try to send as regular message to user via DM
                try:
                    await interaction.user.send(
                        content="Je jaar selectie kon niet worden verwerkt omdat de interactie verlopen is. Probeer het opnieuw.",
                        embed=embed,
                        view=view
                    )
                except Exception as dm_error:
                    self.bot.log.error(f"Failed to send DM fallback message: {dm_error}")
            else:
                self.bot.log.error(f"Failed to send response in YearSelect: {e}")
        
        except Exception as e:
            self.bot.log.error(f"Unexpected error in YearSelect callback: {e}")
            try:
                await interaction.followup.send("Er is een onverwachte fout opgetreden. Probeer het opnieuw.", ephemeral=True)
            except Exception:
                pass  # If we can't send error message, just log it


class CourseSelect(discord.ui.Select):
    def __init__(self, channels, year, bot, user_channel_roles: List[str] = None, page: int = 0, total_pages: int = 1):
        self.year = year
        self.bot = bot
        self.channels = channels
        self.user_channel_roles = user_channel_roles or []
        self.page = page
        self.total_pages = total_pages
        
        # Create options from channels
        options = []
        for channel in channels:
            # Skip channels that start with certain prefixes (like general channels)
            if any(channel.name.startswith(prefix) for prefix in ["algemeen", "general", "announcements"]):
                continue
            
            # Format the channel name with spaces and proper capitalization
            # Convert "programmeren-1" to "Programmeren 1"
            formatted_name = ' '.join(word.capitalize() for word in channel.name.replace('-', ' ').split())
            
            # Check if user currently has access to this channel
            has_access = formatted_name in self.user_channel_roles
                
            options.append(
                discord.SelectOption(
                    label=formatted_name,
                    description=f"{channel.name} {'✅' if has_access else '❌'}",  # Show status in description
                    value=str(channel.id),
                    default=has_access  # Pre-select if user has access
                )
            )
        
        # Update placeholder to show page info if multiple pages
        placeholder = "Selecteer/deselecteer je vakken..."
        if total_pages > 1:
            placeholder = f"Pagina {page + 1}/{total_pages} - Selecteer/deselecteer je vakken..."
        
        super().__init__(
            placeholder=placeholder,
            min_values=0,
            max_values=len(options),  # Allow selecting all options on this page
            options=options,
            custom_id=f"course_select_{year}_page_{page}"
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
        except discord.HTTPException as e:
            if e.code == 10062:  # Unknown interaction
                self.bot.log.warning(f"Interaction expired (10062) in CourseSelect, cannot respond")
                return
            else:
                self.bot.log.error(f"Failed to defer interaction in CourseSelect: {e}")
                return
        
        try:
            # Get the channel menu cog for cache access
            channel_menu_cog = self.bot.get_cog('ChannelMenu')
            if not channel_menu_cog:
                try:
                    await interaction.followup.send("Kanaal menu systeem niet beschikbaar.", ephemeral=True)
                except discord.HTTPException as e:
                    if e.code == 10062:  # Unknown interaction
                        self.bot.log.warning(f"Interaction expired (10062) in CourseSelect, cannot send error message")
                    else:
                        self.bot.log.error(f"Failed to send error message in CourseSelect: {e}")
                return
            
            # Get the channel-role mapping from cache
            mapping = await channel_menu_cog.get_channel_role_mapping(interaction.guild)
            
            # Get the selected channel IDs
            selected_channel_ids = set(self.values)
            
            # Process each channel in this year's category
            added_roles = []
            removed_roles = []
            
            for channel in self.channels:
                # Skip general channels
                if any(channel.name.startswith(prefix) for prefix in ["algemeen", "general", "announcements"]):
                    continue
                
                channel_id = str(channel.id)
                if channel_id not in mapping:
                    continue
                
                role_name = mapping[channel_id]
                role = discord.utils.get(interaction.guild.roles, name=role_name)
                
                # If role doesn't exist, create it
                if not role:
                    role_color = discord.Color.green() if self.year == "1" else discord.Color.gold() if self.year == "2" else discord.Color.red()
                    role = await interaction.guild.create_role(
                        name=role_name,
                        color=role_color,
                        mentionable=False,
                        reason=f"Created for channel access to {channel.name}"
                    )
                    
                    # Set permissions for this role on the channel
                    await channel.set_permissions(role, read_messages=True)
                    
                    # Hide the channel from @everyone if not already hidden
                    everyone_role = interaction.guild.default_role
                    current_perms = channel.overwrites_for(everyone_role)
                    if current_perms.read_messages is not False:
                        await channel.set_permissions(everyone_role, read_messages=False)
                    
                    # Update cache since we created a new role
                    await channel_menu_cog.get_channel_role_mapping(interaction.guild, force_refresh=True)
                else:
                    # Role exists, ensure it has proper permissions (in case they were changed)
                    current_perms = channel.overwrites_for(role)
                    if current_perms.read_messages is not True:
                        await channel.set_permissions(role, read_messages=True)
                
                # Determine if user wants this role (selected in dropdown)
                user_wants_role = channel_id in selected_channel_ids
                user_has_role = role in interaction.user.roles
                
                # Add or remove role based on selection
                if user_wants_role and not user_has_role:
                    await interaction.user.add_roles(role, reason=f"User selected {channel.name} in channel menu")
                    added_roles.append(role)
                elif not user_wants_role and user_has_role:
                    await interaction.user.remove_roles(role, reason=f"User deselected {channel.name} in channel menu")
                    removed_roles.append(role)
            
            # Send confirmation message
            messages = []
            if added_roles:
                added_channels = ", ".join([role.name for role in added_roles])
                messages.append(f"✅ **Toegang gekregen tot:** {added_channels}")
            
            if removed_roles:
                removed_channels = ", ".join([role.name for role in removed_roles])
                messages.append(f"❌ **Toegang verwijderd van:** {removed_channels}")
            
            if not messages:
                messages.append("ℹ️ Geen wijzigingen aangebracht in je toegang tot vakken.")
            
            # Create embed for response
            embed = discord.Embed(
                title="🔄 Vakselectie Bijgewerkt",
                description="\n".join(messages),
                color=discord.Color.blue()
            )
            embed.set_footer(text="Gebruik het menu opnieuw om je selecties te wijzigen")
            
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except discord.HTTPException as e:
                if e.code == 10062:  # Unknown interaction
                    self.bot.log.warning(f"Interaction expired (10062) in CourseSelect, cannot send final response")
                    # Interaction expired, try to send as regular message to user via DM
                    try:
                        await interaction.user.send(
                            content="Je vakselectie is bijgewerkt maar de bevestiging kon niet worden getoond omdat de interactie verlopen is.",
                            embed=embed
                        )
                    except Exception as dm_error:
                        self.bot.log.error(f"Failed to send DM fallback message: {dm_error}")
                else:
                    self.bot.log.error(f"Failed to send response in CourseSelect: {e}")
                
        except discord.Forbidden:
            try:
                await interaction.followup.send(
                    "❌ Ik heb geen toestemming om rollen te beheren. Neem contact op met een beheerder.",
                    ephemeral=True
                )
            except discord.HTTPException as e:
                if e.code == 10062:  # Unknown interaction
                    self.bot.log.warning(f"Interaction expired (10062) in CourseSelect, cannot send forbidden error")
                else:
                    self.bot.log.error(f"Failed to send forbidden error in CourseSelect: {e}")
        except Exception as e:
            self.bot.log.error(f"Error in CourseSelect callback: {e}", exc_info=True)
            try:
                await interaction.followup.send(
                    f"❌ Er is een onverwachte fout opgetreden: {str(e)}. Neem contact op met een beheerder.",
                    ephemeral=True
                )
            except discord.HTTPException as e:
                if e.code == 10062:  # Unknown interaction
                    self.bot.log.warning(f"Interaction expired (10062) in CourseSelect, cannot send general error")
                else:
                    self.bot.log.error(f"Failed to send general error in CourseSelect: {e}")


class PaginationButton(discord.ui.Button):
    def __init__(self, emoji: str, action: str, year: str, all_channels: List, user_channel_roles: List[str], current_page: int, total_pages: int, disabled: bool = False):
        self.action = action
        self.year = year
        self.all_channels = all_channels
        self.user_channel_roles = user_channel_roles
        self.current_page = current_page
        self.total_pages = total_pages
        
        super().__init__(
            emoji=emoji,
            style=discord.ButtonStyle.secondary,
            disabled=disabled,
            custom_id=f"pagination_{action}_{year}_{current_page}"
        )
    
    async def callback(self, interaction: discord.Interaction):
        try:
            # Defer the interaction immediately to prevent timeout
            await interaction.response.defer()
        except discord.HTTPException as e:
            if e.code == 10062:  # Unknown interaction
                self.bot.log.warning(f"Interaction expired (10062) in PaginationButton, cannot respond")
                return
            else:
                self.bot.log.error(f"Failed to defer interaction in PaginationButton: {e}")
                return
        
        # Calculate new page
        if self.action == "prev":
            new_page = max(0, self.current_page - 1)
        else:  # next
            new_page = min(self.total_pages - 1, self.current_page + 1)
        
        # Get channels for the new page
        channels_per_page = 25
        start_idx = new_page * channels_per_page
        end_idx = start_idx + channels_per_page
        page_channels = self.all_channels[start_idx:end_idx]
        
        # Get the user's current roles for all channels (not just this page)
        channel_menu_cog = self.view.bot.get_cog('ChannelMenu')
        if channel_menu_cog:
            # We need to get all channels to check user roles properly
            year_emoji_map = {"1": "🟩", "2": "🟨", "3": "🟥"}
            category_name = f"━━━ {year_emoji_map[self.year]} {self.year}E JAAR ━━━"
            category = discord.utils.get(interaction.guild.categories, name=category_name)
            if category:
                all_channels_in_category = [channel for channel in category.channels if isinstance(channel, discord.TextChannel)]
                user_channel_roles = await channel_menu_cog.get_user_channel_roles(interaction.guild, interaction.user, all_channels_in_category)
            else:
                user_channel_roles = self.user_channel_roles
        else:
            user_channel_roles = self.user_channel_roles
        
        # Create new view with updated page
        view = discord.ui.View(timeout=None)
        view.bot = self.view.bot
        view.add_item(CourseSelect(page_channels, self.year, self.view.bot, user_channel_roles, new_page, self.total_pages))
        
        # Add navigation buttons
        view.add_item(PaginationButton("◀️", "prev", self.year, self.all_channels, user_channel_roles, new_page, self.total_pages, disabled=(new_page == 0)))
        view.add_item(PaginationButton("▶️", "next", self.year, self.all_channels, user_channel_roles, new_page, self.total_pages, disabled=(new_page == self.total_pages - 1)))
        
        # Update embed
        year_colors = {"1": discord.Color.green(), "2": discord.Color.gold(), "3": discord.Color.red()}
        year_emojis = {"1": "🟩", "2": "🟨", "3": "🟥"}
        
        embed = discord.Embed(
            title=f"{year_emojis[self.year]} Jaar {self.year} - Vakselectie (Pagina {new_page + 1}/{self.total_pages})",
            description="Selecteer de vakken die je wilt volgen uit het dropdown menu hieronder.",
            color=year_colors[self.year]
        )
        
        if user_channel_roles:
            embed.add_field(
                name="✅ Je huidige selecties",
                value=", ".join(user_channel_roles),
                inline=False
            )
        else:
            embed.add_field(
                name="ℹ️ Info",
                value="Je hebt nog geen vakken geselecteerd.",
                inline=False
            )
        
        embed.add_field(
            name="📄 Paginatie",
            value=f"Pagina {new_page + 1} van {self.total_pages} ({len(page_channels)} vakken op deze pagina)",
            inline=False
        )
        
        embed.set_footer(text="Selecteer vakken om toegang te krijgen, deselecteer om toegang te verwijderen")
        
        try:
            await interaction.edit_original_response(embed=embed, view=view)
        except discord.HTTPException as e:
            if e.code == 10062:  # Unknown interaction
                self.bot.log.warning(f"Interaction expired (10062) in PaginationButton, cannot edit response")
            else:
                self.bot.log.error(f"Failed to edit response in PaginationButton: {e}")
        except Exception as e:
            self.bot.log.error(f"Unexpected error in PaginationButton callback: {e}")
            try:
                await interaction.followup.send("Er is een fout opgetreden bij het wijzigen van de pagina.", ephemeral=True)
            except Exception:
                pass  # If we can't send error message, just log it


class YearSelectView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(YearSelect(bot))


class ChannelMenu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_role_cache: Dict[int, Dict[str, str]] = {}  # guild_id -> {channel_id: role_name}
        self.cache_last_updated: Dict[int, float] = {}  # guild_id -> timestamp
        self.cache_lock = asyncio.Lock()
    
    async def get_channel_role_mapping(self, guild: discord.Guild, force_refresh: bool = False) -> Dict[str, str]:
        """Get or build the channel to role mapping for a guild. Returns {channel_id: role_name}"""
        import time
        
        async with self.cache_lock:
            guild_id = guild.id
            current_time = time.time()
            
            # Check if we need to refresh the cache (older than 5 minutes or forced)
            if (force_refresh or 
                guild_id not in self.channel_role_cache or 
                current_time - self.cache_last_updated.get(guild_id, 0) > 300):
                
                self.bot.log.debug(f"Building/refreshing channel-role cache for guild {guild.name}")
                mapping = {}
                
                # Get all year categories
                year_categories = []
                for year in ["1", "2", "3"]:
                    year_emoji_map = {"1": "🟩", "2": "🟨", "3": "🟥"}
                    category_name = f"━━━ {year_emoji_map[year]} {year}E JAAR ━━━"
                    category = discord.utils.get(guild.categories, name=category_name)
                    if category:
                        year_categories.append(category)
                
                # For each channel in year categories, find its associated role
                for category in year_categories:
                    for channel in category.channels:
                        if not isinstance(channel, discord.TextChannel):
                            continue
                        
                        # Skip general channels
                        if any(channel.name.startswith(prefix) for prefix in ["algemeen", "general", "announcements"]):
                            continue
                        
                        # Try to find the role associated with this channel
                        role_name = await self._find_channel_role(guild, channel)
                        if role_name:
                            mapping[str(channel.id)] = role_name
                
                self.channel_role_cache[guild_id] = mapping
                self.cache_last_updated[guild_id] = current_time
                self.bot.log.debug(f"Cache updated with {len(mapping)} channel-role mappings")
            
            return self.channel_role_cache.get(guild_id, {})
    
    async def _find_channel_role(self, guild: discord.Guild, channel: discord.TextChannel) -> Optional[str]:
        """Find the role name associated with a channel using standard name resolver (simplified)"""
        # Format the channel name with spaces and proper capitalization
        # Convert "programmeren-1" to "Programmeren 1"
        formatted_name = ' '.join(word.capitalize() for word in channel.name.replace('-', ' ').split())
        
        # TEMPORARILY DISABLED: Complex role detection logic
        # Just use the standard formatted name for role generation
        # This ensures consistent role naming and avoids conflicts
        
        # Check if there's already a role with the formatted name
        existing_role = discord.utils.get(guild.roles, name=formatted_name)
        if existing_role:
            # Ensure this role has proper permissions for the channel
            await channel.set_permissions(existing_role, read_messages=True)
            return existing_role.name
        
        # If no existing role found, return the formatted name (will be created later)
        return formatted_name
    
    async def get_user_channel_roles(self, guild: discord.Guild, user: discord.Member, channels: List[discord.TextChannel]) -> List[str]:
        """Get the list of channel roles the user currently has"""
        mapping = await self.get_channel_role_mapping(guild)
        user_roles = [role.name for role in user.roles]
        user_channel_roles = []
        
        for channel in channels:
            channel_id = str(channel.id)
            if channel_id in mapping:
                role_name = mapping[channel_id]
                if role_name in user_roles:
                    formatted_name = ' '.join(word.capitalize() for word in channel.name.replace('-', ' ').split())
                    user_channel_roles.append(formatted_name)
        
        return user_channel_roles
    
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
    
    @app_commands.command(
        name="refresh_channel_cache",
        description="Refresh the channel-role mapping cache (Admin only)"
    )
    @has_admin()
    async def refresh_channel_cache(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Force refresh the cache
        mapping = await self.get_channel_role_mapping(interaction.guild, force_refresh=True)
        
        embed = discord.Embed(
            title="🔄 Cache Vernieuwd",
            description=f"Channel-role mapping cache is vernieuwd!\n\n"
                       f"**Gevonden mappings:** {len(mapping)}\n"
                       f"**Server:** {interaction.guild.name}",
            color=discord.Color.green()
        )
        
        if mapping:
            # Show some examples of the mappings
            examples = []
            for i, (channel_id, role_name) in enumerate(mapping.items()):
                if i >= 5:  # Show max 5 examples
                    examples.append(f"... en {len(mapping) - 5} meer")
                    break
                channel = interaction.guild.get_channel(int(channel_id))
                if channel:
                    examples.append(f"#{channel.name} → {role_name}")
            
            embed.add_field(
                name="📋 Voorbeelden",
                value="\n".join(examples) if examples else "Geen mappings gevonden",
                inline=False
            )
        
        embed.set_footer(text="Cache wordt automatisch elke 5 minuten vernieuwd")
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        self.bot.log.info(f"Channel cache refreshed by {interaction.user.name} ({interaction.user.id}) - {len(mapping)} mappings found")
    
    @app_commands.command(
        name="show_channel_cache",
        description="Show current channel-role mapping cache status (Admin only)"
    )
    @has_admin()
    async def show_channel_cache(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        import time
        guild_id = interaction.guild.id
        
        # Get current cache info
        mapping = self.channel_role_cache.get(guild_id, {})
        last_updated = self.cache_last_updated.get(guild_id, 0)
        current_time = time.time()
        
        # Calculate time since last update
        if last_updated > 0:
            time_diff = current_time - last_updated
            if time_diff < 60:
                time_str = f"{int(time_diff)} seconden geleden"
            elif time_diff < 3600:
                time_str = f"{int(time_diff/60)} minuten geleden"
            else:
                time_str = f"{int(time_diff/3600)} uur geleden"
        else:
            time_str = "Nog nooit bijgewerkt"
        
        embed = discord.Embed(
            title="📊 Cache Status",
            description=f"**Server:** {interaction.guild.name}\n"
                       f"**Mappings:** {len(mapping)}\n"
                       f"**Laatst bijgewerkt:** {time_str}",
            color=discord.Color.blue()
        )
        
        if mapping:
            # Show all mappings
            mapping_list = []
            for channel_id, role_name in mapping.items():
                channel = interaction.guild.get_channel(int(channel_id))
                if channel:
                    mapping_list.append(f"#{channel.name} → {role_name}")
            
            # Split into chunks if too long
            if len(mapping_list) <= 10:
                embed.add_field(
                    name="📋 Alle Mappings",
                    value="\n".join(mapping_list) if mapping_list else "Geen mappings gevonden",
                    inline=False
                )
            else:
                # Show first 10 and indicate there are more
                embed.add_field(
                    name="📋 Mappings (eerste 10)",
                    value="\n".join(mapping_list[:10]) + f"\n... en {len(mapping_list) - 10} meer",
                    inline=False
                )
        else:
            embed.add_field(
                name="ℹ️ Info",
                value="Geen mappings in cache. Gebruik `/refresh_channel_cache` om de cache te vullen.",
                inline=False
            )
        
        embed.set_footer(text="Cache wordt automatisch elke 5 minuten vernieuwd")
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        self.bot.log.info(f"Channel cache status viewed by {interaction.user.name} ({interaction.user.id}) - {len(mapping)} mappings in cache")


async def setup(bot):
    await bot.add_cog(ChannelMenu(bot))