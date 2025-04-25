import discord
from discord import app_commands
from discord.ext import commands
import datetime
import re
from typing import Optional
import pymongo
import time
import pytz  # Importeer de pytz library

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


class ModCommands(commands.Cog, name="ModCommands"):
    """
    Commands voor server moderatie.
    """

    def __init__(self, bot):
        """Initialiseert de ModCommands cog."""
        self.bot = bot
        self.infractions_collection = self.bot.db["infractions"]
        self.settings_collection = self.bot.db["settings"]

    async def send_dm_embed(self, member: discord.Member, embed: discord.Embed):
        """
        Stuurt een DM naar een gebruiker met een embedded message.
        Retourneert True als de DM succesvol is verzonden, False anders.
        """
        try:
            await member.send(embed=embed)
            return True
        except (discord.errors.Forbidden, discord.errors.HTTPException):
            return False

    @app_commands.command(name="kick", description="Kick een member van de server.")
    @is_moderator()
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Geen reden opgegeven.",
    ):
        """Kickt een member van de server met een optionele reden."""
        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        dm_embed = discord.Embed(
            title=f"⚠️ | Je bent gekickt.",
            description=f"Reden: {reason}",
            color=discord.Color.orange(),
        )
        # Gebruik de timezone bij het formatteren van de tijd
        dm_embed.set_footer(text=f"Tijd: {timestamp.astimezone(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)

        dm_sent = await self.send_dm_embed(member, dm_embed)

        try:
            await member.kick(reason=reason)
            embed = discord.Embed(
                title="Member gekickt",
                description=f"{member.mention} is gekickt. Reden: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
            await self.log_infraction(
                interaction.guild.id, member.id, interaction.user.id, "kick", reason
            )

        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="Ik heb geen permissie om deze member te kicken.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.HTTPException:
            embed = discord.Embed(
                title="Error",
                description="Kicken mislukt.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ban", description="Ban een member van de server.")
    @is_moderator()
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Geen reden opgegeven.",
    ):
        """Bant een member van de server met een optionele reden."""
        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        dm_embed = discord.Embed(
            title=f"⚠️ | Je bent gebanned.",
            description=f"Reden: {reason}",
            color=discord.Color.dark_red(),
        )
        # Gebruik de timezone bij het formatteren van de tijd
        dm_embed.set_footer(text=f"Tijd: {timestamp.astimezone(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)

        await interaction.response.defer(ephemeral=True)

        try:
            try:
                channel = await member.create_dm()
                view = discord.ui.View()
                settings = await self.settings_collection.find_one({"_id": "mod_settings"})
                unban_request_url = settings.get("unban_request_url", "https://example.com/unban_request")
                button = discord.ui.Button(
                    label="Request Unban", style=discord.ButtonStyle.link, url=unban_request_url
                )
                view.add_item(button)

                await channel.send(
                    embed=discord.Embed(
                        title="⚠️ | Je bent gebanned.",
                        description=f"Je bent gebanned van {interaction.guild.name} met reden: {reason} \n\n Als je een unban wilt aanvragen, klik dan op de link hieronder.",
                        color=discord.Color.gold(),
                    ),
                    view=view,
                )

                dm_success = True
            except discord.errors.Forbidden:
                print(f"Kon geen DM sturen naar {member.name}.")
                dm_success = False

            await member.ban(reason=reason)

            embed = discord.Embed(
                title="Member gebanned",
                description=f"{member.mention} is gebanned. Reden: {reason}",
                color=discord.Color.green(),
            )

            if dm_success:
                embed.set_footer(text="Gebruiker is via DM geïnformeerd.")
            else:
                embed.set_footer(text="Kon gebruiker niet via DM informeren.")

            await interaction.followup.send(embed=embed, ephemeral=False)
            await self.log_infraction(
                interaction.guild.id, member.id, interaction.user.id, "ban", reason
            )

        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="Ik heb geen permissie om deze member te bannen.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.errors.HTTPException:
            embed = discord.Embed(
                title="Error",
                description="Bannen mislukt.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="mute", description="Mute een member in de server")
    @is_moderator()
    async def mute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Geen reden opgegeven",
    ):
        guild = interaction.guild
        muted_role = discord.utils.get(guild.roles, name="Muted")

        if not muted_role:
            muted_role = await guild.create_role(
                name="Muted", reason="Muted role aangemaakt voor muting"
            )

            for channel in guild.channels:
                try:
                    await channel.set_permissions(
                        muted_role,
                        speak=False,
                        send_messages=False,
                        read_message_history=True,
                    )
                except discord.errors.Forbidden:
                    pass

        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        dm_embed = discord.Embed(
            title=f"⚠️| Je bent gemute.",
            description=f"Reden: {reason}",
            color=discord.Color.dark_gray(),
        )
        # Gebruik de timezone bij het formatteren van de tijd
        dm_embed.set_footer(text=f"Tijd: {timestamp.astimezone(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)

        dm_sent = await self.send_dm_embed(member, dm_embed)
        try:
            await member.add_roles(muted_role, reason=reason)
            embed = discord.Embed(
                title="Member gemute",
                description=f"{member.mention} is gemute. Reden: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
            await self.log_infraction(
                interaction.guild.id, member.id, interaction.user.id, "mute", reason
            )

        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="Ik heb geen permissie om rollen te beheren voor deze member.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.HTTPException:
            embed = discord.Embed(
                title="Error",
                description="Muten mislukt.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="unmute", description="Unmute een member in de server."
    )
    @is_moderator()
    async def unmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Geen reden opgegeven.",
    ):
        guild = interaction.guild
        muted_role = discord.utils.get(guild.roles, name="Muted")

        if not muted_role:
            embed = discord.Embed(
                title="Error",
                description="Geen 'Muted' role gevonden. Kan niet unmuten.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        dm_embed = discord.Embed(
            title=f"⚠️ | Je bent geunmute.",
            description=f"Reden: {reason}",
            color=discord.Color.green(),
        )
        # Gebruik de timezone bij het formatteren van de tijd
        dm_embed.set_footer(text=f"Tijd: {timestamp.astimezone(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)

        dm_sent = await self.send_dm_embed(member, dm_embed)
        try:
            await member.remove_roles(muted_role, reason=reason)
            embed = discord.Embed(
                title="Member geunmute",
                description=f"{member.mention} is geunmute. Reden: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
            await self.log_infraction(
                interaction.guild.id, member.id, interaction.user.id, "unmute", reason
            )
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="Ik heb geen permissie om rollen te beheren voor deze member.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.HTTPException:
            embed = discord.Embed(
                title="Error",
                description="Unmuten mislukt.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="warn", description="Waarschuw een user")
    @is_moderator()
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Geen reden opgegeven.",
    ):
        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        dm_embed = discord.Embed(
            title=f"⚠️ | Je bent gewaarschuwd.",
            description=f"Reden: {reason}",
            color=discord.Color.yellow(),
        )
        # Gebruik de timezone bij het formatteren van de tijd
        dm_embed.set_footer(text=f"Tijd: {timestamp.astimezone(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)

        dm_sent = await self.send_dm_embed(member, dm_embed)
        if not dm_sent:
            embed = discord.Embed(
                title="Waarschuwing",
                description=f"Kon geen waarschuwing sturen naar {member.mention}.",
                color=discord.Color.orange(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = discord.Embed(
            title="Member gewaarschuwd",
            description=f"{member.mention} is gewaarschuwd en via DM geïnformeerd.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)
        await self.log_infraction(
            interaction.guild.id, member.id, interaction.user.id, "warn", reason
        )

    @app_commands.command(
        name="purge", description="Verwijdert messages uit het kanaal."
    )
    @is_moderator()
    async def purge(
        self,
        interaction: discord.Interaction,
        count: int,
        bots: bool = False,
        bot_only: bool = False,
    ):
        def check(message):
            if bot_only:
                return message.author.bot
            elif bots:
                return True
            else:
                return not message.author.bot

        await interaction.response.defer(ephemeral=True)

        try:
            deleted = await interaction.channel.purge(limit=count, check=check)
            embed = discord.Embed(
                title="Messages verwijderd",
                description=f"{len(deleted)} messages verwijderd in dit kanaal.",
                color=discord.Color.green(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="Ik heb geen permissie om messages in dit kanaal te verwijderen.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.errors.HTTPException as e:
            embed = discord.Embed(
                title="Error",
                description=f"Verwijderen mislukt: {e}",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="timeout", description="Timeout een member in de server"
    )
    @is_moderator()
    @app_commands.describe(
        member="De member om te timeouten",
        duration="De duration van de timeout (bijv. 1m, 5h, 1d). Max 28 dagen.",
        reason="De reden voor de timeout",
    )
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: str = "Geen reden opgegeven",
    ):
        duration_timedelta = self.parse_duration(duration)
        if not duration_timedelta:
            embed = discord.Embed(
                title="Error",
                description="Invalid duration format. Gebruik voorbeelden zoals 1m, 5h, 1d.",
                color=discord.Color.red(),
            )
            return await interaction.response.send_message(
                embed=embed, ephemeral=True
            )

        timeout_until = discord.utils.utcnow() + duration_timedelta

        if duration_timedelta > datetime.timedelta(days=28):
            embed = discord.Embed(
                title="Error",
                description="Maximale timeout duration is 28 dagen.",
                color=discord.Color.red(),
            )
            return await interaction.response.send_message(
                embed=embed, ephemeral=True
            )

        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        dm_embed = discord.Embed(
            title=f"⚠️ | Je bent getimed out.",
            description=f"Reden: {reason}\nDuration: {duration}",
            color=discord.Color.dark_orange(),
        )
        # Gebruik de timezone bij het formatteren van de tijd
        dm_embed.set_footer(text=f"Tijd: {timestamp.astimezone(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)
        dm_sent = await self.send_dm_embed(member, dm_embed)
        try:
            await member.timeout(timeout_until, reason=reason)
            embed = discord.Embed(
                title="Member Timeout",
                description=f"{member.mention} is getimed out voor {duration}. Reden: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
            await self.log_infraction(
                interaction.guild.id, member.id, interaction.user.id, "timeout", reason
            )
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="Ik heb geen permissie om deze member te timeouten.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    def parse_duration(self, duration_str: str) -> Optional[datetime.timedelta]:
        units = {"m": "minutes", "h": "hours", "d": "days"}
        match = re.match(r"(\d+)([mhd])", duration_str)
        if not match:
            return None

        amount, unit = match.groups()
        amount = int(amount)
        unit = units[unit]
        return datetime.timedelta(**{unit: amount})

    @app_commands.command(
        name="untimeout", description="Verwijdert timeout van een member"
    )
    @is_moderator()
    @app_commands.describe(
        member="De member om de timeout van te verwijderen",
        reason="De reden voor het verwijderen van de timeout",
    )
    async def untimeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Geen reden opgegeven.",
    ):
        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        dm_embed = discord.Embed(
            title=f"Je timeout is verwijderd in {interaction.guild.name}",
            description=f"Reden: {reason}",
            color=discord.Color.green(),
        )
        # Gebruik de timezone bij het formatteren van de tijd
        dm_embed.set_footer(text=f"Tijd: {timestamp.astimezone(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)

        dm_sent = await self.send_dm_embed(member, dm_embed)
        try:
            await member.timeout(None, reason=reason)
            embed = discord.Embed(
                title="Member untimeout",
                description=f"{member.mention} is geuntimeout. Reden: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
            await self.log_infraction(
                interaction.guild.id, member.id, interaction.user.id, "untimeout", reason
            )
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="Ik heb geen permissie om deze member te untimeouten.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="history", description="Laat de recente straffen van een member zien."
    )
    @is_moderator()
    @app_commands.describe(member="De gebruiker om de voorgaande straffen van te bekijken")
    async def history(self, interaction: discord.Interaction, member: discord.Member):
        infractions = await self.bot.db.infractions.find(
            {"guild_id": interaction.guild.id, "user_id": member.id}
        ).sort("timestamp", pymongo.DESCENDING).limit(
            10
        ).to_list(
            length=None
        )
        infraction_list = ""
        for infraction in infractions:
            localized_timestamp = infraction['timestamp'].astimezone(TIMEZONE)
            infraction_list += f"<t:{int(time.mktime(localized_timestamp.timetuple()))}:f> - **{infraction['type'].capitalize()}**: {infraction['reason']}\n"

        if not infraction_list:
            infraction_list = "Geen voorgaande straffen gevonden voor deze gebruiker."

        embed = discord.Embed(
            title=f"History voor {member.name}",
            color=discord.Color.blue(),
            description=infraction_list,
        )
        embed.add_field(
            name="Join Date",
            value=f"<t:{int(time.mktime(member.joined_at.astimezone(TIMEZONE).timetuple()))}:D>",
            inline=False,
        )
        embed.add_field(
            name="Account Creation Date",
            value=f"<t:{int(time.mktime(member.created_at.astimezone(TIMEZONE).timetuple()))}:D>",
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(
        name="lockdown",
        description="Voorkom het versturen van berichten in een channel.",
    )
    @is_moderator()
    @app_commands.describe(
        channel="De channel om te lockdownen", reason="De reden voor de lockdown"
    )
    async def lockdown(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        reason: str = "Geen reden opgegeven.",
    ):
        try:
            await channel.set_permissions(
                interaction.guild.default_role, send_messages=False
            )
            embed = discord.Embed(
                title="Channel Gelockdown",
                description=f"{channel.mention} is gelockdown. Reden: {reason}",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed)
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="Ik heb geen permissie om dit channel te lockdownen.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="unlockdown",
        description="Unlock een gelockdown channel.",
    )
    @is_moderator()
    @app_commands.describe(
        channel="De channel om te unlocken", reason="De reden voor het unlocken"
    )
    async def unlockdown(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        reason: str = "Geen reden opgegeven.",
    ):
        try:
            await channel.set_permissions(
                interaction.guild.default_role, send_messages=True
            )
            embed = discord.Embed(
                title="Channel Geunlockt",
                description=f"{channel.mention} is geunlockt. Reden: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="Ik heb geen permissie om dit channel te unlocken.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="slowmode", description="Stel slowmode in een channel in."
    )
    @is_moderator()
    @app_commands.describe(
        channel="De channel om slowmode in te stellen",
        seconds="De slowmode delay in seconden",
    )
    async def slowmode(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        seconds: int,
    ):
        try:
            await channel.edit(slowmode_delay=seconds)
            embed = discord.Embed(
                title="Slowmode Ingesteld",
                description=f"Slowmode ingesteld op {seconds} seconden in {channel.mention}.",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="Ik heb geen permissie om slowmode in dit channel in te stellen.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.HTTPException:
            embed = discord.Embed(
                title="Error",
                description="Kon slowmode niet instellen.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def log_infraction(
        self, guild_id, user_id, moderator_id, infraction_type, reason
    ):
        infraction = {
            "guild_id": guild_id,
            "user_id": user_id,
            "moderator_id": moderator_id,
            "type": infraction_type,
            "reason": reason,
            "timestamp": datetime.datetime.utcnow(),
        }
        await self.infractions_collection.insert_one(infraction)
    @app_commands.command(name="set_mod_setting", description="Stel een moderator setting in.")
    @is_moderator()
    @app_commands.describe(
        setting_name="De setting om aan te passen",
        setting_value="De waarde voor de setting."
    )
    @app_commands.choices(setting_name=[
        app_commands.Choice(name="moderator_id", value="moderator_id"),
        app_commands.Choice(name="unban_request_url", value="unban_request_url"),
        app_commands.Choice(name="unban_request_kanaal_id", value="unban_request_kanaal_id"),
        app_commands.Choice(name="aanvragen_log_kanaal_id_1", value="aanvragen_log_kanaal_id_1"),
        app_commands.Choice(name="aanvragen_log_kanaal_id_2", value="aanvragen_log_kanaal_id_2"),
    ])
    async def set_mod_setting(self, interaction: discord.Interaction,
                                setting_name: str,
                                setting_value: str):
        """Stelt een moderator setting in."""
        valid_settings = {
            "moderator_id": "moderator_id",
            "unban_request_url": "unban_request_url",
            "unban_request_kanaal_id": "unban_request_kanaal_id",
            "aanvragen_log_kanaal_id_1": "aanvragen_log_kanaal_id_1",
            "aanvragen_log_kanaal_id_2": "aanvragen_log_kanaal_id_2",
        }

        if setting_name not in valid_settings:
            return await interaction.response.send_message(
                f"Ongeldige setting naam. Geldige settings zijn: {', '.join(valid_settings.keys())}",
                ephemeral=True)

        try:
            if setting_name in ("moderator_id", "unban_request_kanaal_id", "aanvragen_log_kanaal_id_1", "aanvragen_log_kanaal_id_2"):
                setting_value = int(setting_value)
        except ValueError:
            return await interaction.response.send_message(f"De '{setting_name}' moet een getal zijn.", ephemeral=True)

        await self.settings_collection.update_one(
            {"_id": "mod_settings"},
            {"$set": {setting_name: setting_value}},
            upsert=True,
        )

        await interaction.response.send_message(
            f"Setting '{setting_name}' is ingesteld op '{setting_value}'.",
            ephemeral=True)

@app_commands.context_menu(name="Verwijder Hieronder")
@is_moderator()
async def purge_below(interaction: discord.Interaction, message: discord.Message):
    try:
        await interaction.response.defer(ephemeral=True)
        messages_to_delete = []
        async for msg in interaction.channel.history(
            limit=None, oldest_first=False
        ):
            if msg.id == message.id:
                break
            messages_to_delete.append(msg)

        if messages_to_delete:
            await interaction.channel.delete_messages(messages_to_delete)

        embed = discord.Embed(
            title="Messages verwijderd Hieronder",
            description=f"{len(messages_to_delete)} messages verwijderd onder de geselecteerde message.",
            color=discord.Color.green(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    except discord.errors.Forbidden:
        embed = discord.Embed(
            title="Permission Error",
            description="Ik heb geen permissie om messages in dit channel te verwijderen.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except discord.errors.HTTPException as e:
            embed = discord.Embed(
                title="Error",
                description=f"Verwijderen mislukt: {e}",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ModCommands(bot))
    bot.tree.add_command(purge_below)