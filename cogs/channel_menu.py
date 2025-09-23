import discord
from discord import app_commands
from discord.ext import commands
import datetime
import re
from typing import List, Tuple


class YearButton(discord.ui.Button):
    def __init__(self, bot, year: str, label: str, emoji: str, color: discord.Color):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.primary,
            emoji=emoji,
            custom_id=f"year_button_{year}"
        )
        self.bot = bot
        self.year = year
        self.color = color

    async def callback(self, interaction: discord.Interaction):
        # Tracks dynamisch ophalen uit kanaalbeschrijvingen
        channel_menu_cog = self.bot.get_cog("ChannelMenu")
        tracks = await channel_menu_cog.get_tracks_for_year(interaction.guild, self.year)

        if not tracks:
            await interaction.response.send_message(
                f"❌ Geen afstudeerrichtingen gevonden voor jaar {self.year}.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"📘 Jaar {self.year}",
            description="Selecteer je afstudeerrichting.",
            color=self.color,
            timestamp=datetime.datetime.now()
        )
        view = TrackSelectView(self.bot, self.year, tracks, self.color)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class TrackSelect(discord.ui.Select):
    def __init__(self, bot, year: str, options: List[discord.SelectOption], color: discord.Color):
        self.bot = bot
        self.year = year
        self.color = color
        super().__init__(
            placeholder="Selecteer je afstudeerrichting...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"track_select_{year}"
        )

    async def callback(self, interaction: discord.Interaction):
        selected_track = self.values[0]

        # Rollen dynamisch ophalen
        channel_menu_cog = self.bot.get_cog("ChannelMenu")
        roles = await channel_menu_cog.get_roles_for_track(interaction.guild, self.year, selected_track)

        if not roles:
            await interaction.response.send_message(
                f"❌ Geen rollen gevonden voor {selected_track} ({self.year}).",
                ephemeral=True
            )
            return

        options = [
            discord.SelectOption(
                label=role.name,
                value=str(role.id),
                default=role in interaction.user.roles
            )
            for role in roles
        ]

        embed = discord.Embed(
            title=f"🎓 {selected_track} ({self.year})",
            description="Selecteer of deselecteer de rollen die je wilt hebben.",
            color=self.color,
            timestamp=datetime.datetime.now()
        )
        view = RoleSelectView(self.bot, self.year, selected_track, options, self.color)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class CourseSelect(discord.ui.Select):
    def __init__(self, bot, year: str, track: str, options: List[discord.SelectOption]):
        self.bot = bot
        self.year = year
        self.track = track
        super().__init__(
            placeholder="Selecteer/deselecteer je vakrollen...",
            min_values=0,
            max_values=len(options),
            options=options,
            custom_id=f"course_select_{year}_{track}"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        selected_ids = set(int(v) for v in self.values)
        added, removed = [], []

        for opt in self.options:
            role_id = int(opt.value)
            role = interaction.guild.get_role(role_id)
            if not role:
                continue
            if role_id in selected_ids and role not in interaction.user.roles:
                await interaction.user.add_roles(role)
                added.append(role.name)
            elif role_id not in selected_ids and role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                removed.append(role.name)

        msg = []
        if added:
            msg.append(f"✅ Toegevoegd: {', '.join(added)}")
        if removed:
            msg.append(f"❌ Verwijderd: {', '.join(removed)}")
        if not msg:
            msg.append("ℹ️ Geen wijzigingen.")

        await interaction.followup.send("\n".join(msg), ephemeral=True)


class YearButtonsView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(YearButton(bot, "1", "1e Jaar", "🟩", discord.Color.green()))
        self.add_item(YearButton(bot, "2", "2e Jaar", "🟨", discord.Color.gold()))
        self.add_item(YearButton(bot, "3", "3e Jaar", "🟥", discord.Color.red()))


class TrackSelectView(discord.ui.View):
    def __init__(self, bot, year: str, tracks: List[str], color: discord.Color):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(TrackSelect(bot, year, [discord.SelectOption(label=t, value=t) for t in tracks], color))


class RoleSelectView(discord.ui.View):
    def __init__(self, bot, year: str, track: str, options: List[discord.SelectOption], color: discord.Color):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(CourseSelect(bot, year, track, options))
        self.add_item(BackToTracksButton(bot, year, color))


class BackToTracksButton(discord.ui.Button):
    def __init__(self, bot, year: str, color: discord.Color):
        super().__init__(label="⬅️ Terug naar tracks", style=discord.ButtonStyle.secondary)
        self.bot = bot
        self.year = year
        self.color = color

    async def callback(self, interaction: discord.Interaction):
        channel_menu_cog = self.bot.get_cog("ChannelMenu")
        tracks = await channel_menu_cog.get_tracks_for_year(interaction.guild, self.year)

        embed = discord.Embed(
            title=f"📘 Jaar {self.year}",
            description="Selecteer je afstudeerrichting.",
            color=self.color,
            timestamp=datetime.datetime.now()
        )
        view = TrackSelectView(self.bot, self.year, tracks, self.color)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ChannelMenu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def parse_channel_topic(self, channel: discord.TextChannel) -> Tuple[str, List[str]]:
        """Gebruik altijd de kanaalnaam als rolnaam, en haal tracks uit de laatste regel van het topic."""
        # Rolnaam = kanaalnaam → mooi geformatteerd (Spaties ipv - en hoofdletters)
        role_name = " ".join(word.capitalize() for word in channel.name.replace("-", " ").split())

        tracks: List[str] = []
        if channel.topic:
            # Laatste niet-lege regel pakken
            lines = [l.strip("• ").strip() for l in channel.topic.splitlines() if l.strip()]
            if lines:
                track_line = lines[-1]
                tracks = [t.strip() for t in track_line.split(",")]

        return role_name, tracks

    async def get_tracks_for_year(self, guild: discord.Guild, year: str) -> List[str]:
        """Geef unieke tracks terug voor een studiejaar."""
        tracks_set = set()
        for category in guild.categories:
            if f"{year}E JAAR" in category.name.upper():
                for channel in category.channels:
                    if isinstance(channel, discord.TextChannel):
                        _, tracks = await self.parse_channel_topic(channel)
                        for t in tracks:
                            if t:
                                tracks_set.add(t)
        return sorted(list(tracks_set))

    async def get_roles_for_track(self, guild: discord.Guild, year: str, track: str) -> List[discord.Role]:
        """Geef alle rollen terug die gekoppeld zijn aan een bepaalde track in een jaar."""
        roles = []

        for category in guild.categories:
            if f"{year}E JAAR" not in category.name.upper():
                continue

            for channel in category.channels:
                if not isinstance(channel, discord.TextChannel):
                    continue

                role_name, tracks = await self.parse_channel_topic(channel)
                if not role_name:
                    continue

                if track in tracks:
                    role = await self.ensure_role_for_channel(channel.guild, channel, role_name)
                    roles.append(role)

        return roles

    async def ensure_role_for_channel(self, guild: discord.Guild, channel: discord.TextChannel, role_name: str) -> discord.Role:
        """Maak rol aan als die nog niet bestaat en stel permissions in voor dit kanaal."""
        role = discord.utils.get(guild.roles, name=role_name)

        if not role:
            role = await guild.create_role(
                name=role_name,
                reason=f"Auto-created from channel topic in #{channel.name}"
            )
            self.bot.log.info(f"✅ Rol '{role.name}' aangemaakt in guild '{guild.name}'")

        # Permissions instellen
        await channel.set_permissions(role, read_messages=True)
        everyone = guild.default_role
        if channel.overwrites_for(everyone).read_messages is not False:
            await channel.set_permissions(everyone, read_messages=False)

        return role

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """Wanneer een nieuw kanaal wordt aangemaakt in een jaarcategorie → rol aanmaken."""
        if not isinstance(channel, discord.TextChannel):
            return

        # Check of de category een jaar bevat
        if channel.category and any(x in channel.category.name.upper() for x in ["1E JAAR", "2E JAAR", "3E JAAR"]):
            role_name, tracks = await self.parse_channel_topic(channel)
            if role_name:
                await self.ensure_role_for_channel(channel.guild, channel, role_name)
                self.bot.log.info(f"📘 Rol en permissions ingesteld voor #{channel.name} in {channel.category.name}")

async def setup(bot):
    await bot.add_cog(ChannelMenu(bot))
