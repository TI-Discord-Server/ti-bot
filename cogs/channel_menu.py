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
        
        # Create a multi-select menu for the channels
        view = discord.ui.View(timeout=None)
        view.add_item(CourseSelect(channels, year))
        
        await interaction.response.send_message(
            f"Je hebt jaar {year} geselecteerd. Selecteer nu je vakken:",
            view=view,
            ephemeral=True
        )


class CourseSelect(discord.ui.Select):
    def __init__(self, channels, year):
        self.year = year
        
        # Create options from channels
        options = []
        for channel in channels:
            # Skip channels that start with certain prefixes (like general channels)
            if any(channel.name.startswith(prefix) for prefix in ["algemeen", "general", "announcements"]):
                continue
                
            options.append(
                discord.SelectOption(
                    label=channel.name,
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
        # Get the selected channel IDs
        selected_channel_ids = self.values
        
        # Get all channels in the guild
        all_channels = interaction.guild.channels
        
        # Get the channels the user selected
        selected_channels = [
            channel for channel in all_channels 
            if str(channel.id) in selected_channel_ids
        ]
        
        # Update user's permissions for these channels
        for channel in all_channels:
            if isinstance(channel, discord.TextChannel):
                # If channel is in the selected list, ensure user can see it
                if channel in selected_channels:
                    await channel.set_permissions(interaction.user, read_messages=True)
                # If channel is in the same year category but not selected, hide it
                elif (channel.category and 
                      f"{self.year}E JAAR" in channel.category.name and
                      not any(channel.name.startswith(prefix) for prefix in ["algemeen", "general", "announcements"])):
                    await channel.set_permissions(interaction.user, read_messages=False)
        
        # Send confirmation message
        if selected_channels:
            channel_names = ", ".join([channel.name for channel in selected_channels])
            await interaction.response.send_message(
                f"Je hebt toegang gekregen tot de volgende vakken: {channel_names}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Je hebt geen vakken geselecteerd. Je ziet nu alleen de algemene kanalen voor dit jaar.",
                ephemeral=True
            )


class YearSelectView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
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
        # Check if the required categories exist, create them if not
        await self.ensure_categories_exist(interaction.guild)
        
        # Create and send the year selection view
        view = YearSelectView(self.bot)
        
        await interaction.response.send_message(
            "# Kanaal Selectie\n"
            "Selecteer eerst je jaar, dan kun je kiezen welke vakken je wilt volgen.\n"
            "Je krijgt alleen toegang tot de kanalen die je selecteert.",
            view=view
        )
    
    async def ensure_categories_exist(self, guild):
        # Define the categories we need
        required_categories = [
            {"name": "━━━ 🟩 1E JAAR ━━━", "position": 0},
            {"name": "━━━ 🟨 2E JAAR ━━━", "position": 10},
            {"name": "━━━ 🟥 3E JAAR ━━━", "position": 20}
        ]
        
        # Check if each category exists, create if not
        for cat_info in required_categories:
            category = discord.utils.get(guild.categories, name=cat_info["name"])
            if not category:
                # Create the category
                await guild.create_category(
                    name=cat_info["name"],
                    position=cat_info["position"]
                )
                
                # Create a general channel in this category
                year = "1" if "1E" in cat_info["name"] else "2" if "2E" in cat_info["name"] else "3"
                await guild.create_text_channel(
                    name=f"algemeen-jaar-{year}",
                    category=discord.utils.get(guild.categories, name=cat_info["name"])
                )


async def setup(bot):
    await bot.add_cog(ChannelMenu(bot))