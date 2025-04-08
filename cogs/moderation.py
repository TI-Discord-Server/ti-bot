import discord
from discord import app_commands
from discord.ext import commands
import datetime
import re
from typing import Optional
import pymongo

MOD_ID = 1348716664333795398
UNBAN_REQUEST_URL = "https://discord.gg/98swM2fgjW"

def is_moderator():
    async def predicate(interaction: discord.Interaction):
        return (
            interaction.user.id == MOD_ID
            or interaction.user.guild_permissions.manage_guild
        )

    return commands.check(predicate)


class ModCommands(commands.Cog, name="ModCommands"):
    def __init__(self, bot):
        self.bot = bot
        self.infractions_collection = self.bot.db["infractions"]

    async def send_dm_embed(self, member: discord.Member, embed: discord.Embed):
        try:
            await member.send(embed=embed)
            return True
        except (discord.errors.Forbidden, discord.errors.HTTPException):
            return False

    @app_commands.command(name="kick", description="Kick a member from the server.")
    @is_moderator()
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided.",
    ):
        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        dm_embed = discord.Embed(
            title=f"You have been kicked from {interaction.guild.name}",
            description=f"Reason: {reason}",
            color=discord.Color.orange(),
        )
        dm_embed.set_footer(text=f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)

        dm_sent = await self.send_dm_embed(member, dm_embed)

        try:
            await member.kick(reason=reason)
            embed = discord.Embed(
                title="Member Kicked",
                description=f"{member.mention} has been kicked. Reason: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
            await self.log_infraction(interaction.guild.id, member.id, interaction.user.id, "kick", reason)

        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I do not have permission to kick this member.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.HTTPException:
            embed = discord.Embed(
                title="Error",
                description="Kick failed.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ban", description="Ban a member from the server.")
    @is_moderator()
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided.",
    ):
        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        dm_embed = discord.Embed(
            title=f"You have been banned from {interaction.guild.name}",
            description=f"Reason: {reason}",
            color=discord.Color.dark_red(),
        )
        dm_embed.set_footer(text=f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)

        await interaction.response.defer(ephemeral=True)

        try:
            try:
                channel = await member.create_dm()
                view = discord.ui.View()
                button = discord.ui.Button(
                    label="Request Unban", style=discord.ButtonStyle.link, url=UNBAN_REQUEST_URL
                )
                view.add_item(button)

                await channel.send(
                    embed=discord.Embed(
                        title="Unban Request",
                        description=f"You have been banned from {interaction.guild.name} with reason: {reason} \n\n If you would like to request an unban, please click the link below.",
                        color=discord.Color.gold(),
                    ),
                    view=view,
                )

                dm_success = True
            except discord.errors.Forbidden:
                print(f"Could not send DM to {member.name}.")
                dm_success = False

            await member.ban(reason=reason)

            embed = discord.Embed(
                title="Member Banned",
                description=f"{member.mention} has been banned. Reason: {reason}",
                color=discord.Color.green(),
            )

            if dm_success:
                embed.set_footer(text="User was notified via DM.")
            else:
                embed.set_footer(text="Failed to notify user via DM.")

            await interaction.followup.send(embed=embed, ephemeral=False)
            await self.log_infraction(interaction.guild.id, member.id, interaction.user.id, "ban", reason)

        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I do not have permission to ban this member.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.errors.HTTPException:
            embed = discord.Embed(
                title="Error",
                description="Ban failed.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="mute", description="Mute a member in the server")
    @is_moderator()
    async def mute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ):
        guild = interaction.guild
        muted_role = discord.utils.get(guild.roles, name="Muted")

        if not muted_role:
            muted_role = await guild.create_role(
                name="Muted", reason="Created Muted role for muting"
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
            title=f"You have been muted in {interaction.guild.name}",
            description=f"Reason: {reason}",
            color=discord.Color.dark_gray(),
        )
        dm_embed.set_footer(text=f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)

        dm_sent = await self.send_dm_embed(member, dm_embed)
        try:
            await member.add_roles(muted_role, reason=reason)
            embed = discord.Embed(
                title="Member Muted",
                description=f"{member.mention} has been muted. Reason: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
            await self.log_infraction(interaction.guild.id, member.id, interaction.user.id, "mute", reason)

        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I do not have permission to manage roles for this member.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.HTTPException:
            embed = discord.Embed(
                title="Error",
                description="Mute failed.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="unmute", description="Unmute a member in the server."
    )
    @is_moderator()
    async def unmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided.",
    ):
        guild = interaction.guild
        muted_role = discord.utils.get(guild.roles, name="Muted")

        if not muted_role:
            embed = discord.Embed(
                title="Error",
                description="No 'Muted' role found.  Cannot unmute.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        dm_embed = discord.Embed(
            title=f"You have been unmuted in {interaction.guild.name}",
            description=f"Reason: {reason}",
            color=discord.Color.green(),
        )
        dm_embed.set_footer(text=f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)

        dm_sent = await self.send_dm_embed(member, dm_embed)
        try:
            await member.remove_roles(muted_role, reason=reason)
            embed = discord.Embed(
                title="Member Unmuted",
                description=f"{member.mention} has been unmuted. Reason: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
            await self.log_infraction(interaction.guild.id, member.id, interaction.user.id, "unmute", reason)
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I do not have permission to manage roles for this member.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.HTTPException:
            embed = discord.Embed(
                title="Error",
                description="Unmute failed.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="warn", description="Warn a user")
    @is_moderator()
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided.",
    ):
        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        dm_embed = discord.Embed(
            title=f"You have been warned in {interaction.guild.name}",
            description=f"Reason: {reason}",
            color=discord.Color.yellow(),
        )
        dm_embed.set_footer(text=f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)

        dm_sent = await self.send_dm_embed(member, dm_embed)
        if not dm_sent:
            embed = discord.Embed(
                title="Warning",
                description=f"Could not send warning to {member.mention}.",
                color=discord.Color.orange(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = discord.Embed(
            title="Member Warned",
            description=f"{member.mention} has been warned and notified via DM.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)
        await self.log_infraction(interaction.guild.id, member.id, interaction.user.id, "warn", reason)

    @app_commands.command(
        name="purge", description="Purge messages from the channel."
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
                title="Messages Purged",
                description=f"Purged {len(deleted)} messages in this channel.",
                color=discord.Color.green(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I do not have permission to purge messages in this channel.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.errors.HTTPException as e:
            embed = discord.Embed(
                title="Error",
                description=f"Purge failed: {e}",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="timeout", description="Timeout a member in the server"
    )
    @is_moderator()
    @app_commands.describe(
        member="The member to timeout",
        duration="The duration of the timeout (e.g., 1m, 5h, 1d). Max 28 days.",
        reason="The reason for the timeout",
    )
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: str = "No reason provided",
    ):
        duration_timedelta = self.parse_duration(duration)
        if not duration_timedelta:
            embed = discord.Embed(
                title="Error",
                description="Invalid duration format. Use examples like 1m, 5h, 1d.",
                color=discord.Color.red(),
            )
            return await interaction.response.send_message(
                embed=embed, ephemeral=True
            )

        timeout_until = discord.utils.utcnow() + duration_timedelta

        if duration_timedelta > datetime.timedelta(days=28):
            embed = discord.Embed(
                title="Error",
                description="Maximum timeout duration is 28 days.",
                color=discord.Color.red(),
            )
            return await interaction.response.send_message(
                embed=embed, ephemeral=True
            )

        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        dm_embed = discord.Embed(
            title=f"You have been timed out in {interaction.guild.name}",
            description=f"Reason: {reason}\nDuration: {duration}",
            color=discord.Color.dark_orange(),
        )
        dm_embed.set_footer(text=f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)
        dm_sent = await self.send_dm_embed(member, dm_embed)
        try:
            await member.timeout(timeout_until, reason=reason)
            embed = discord.Embed(
                title="Member Timeout",
                description=f"{member.mention} has been timed out for {duration}. Reason: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
            await self.log_infraction(interaction.guild.id, member.id, interaction.user.id, "timeout", reason)
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I do not have permission to timeout this member.",
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
        name="untimeout", description="Remove timeout from a member"
    )
    @is_moderator()
    @app_commands.describe(
        member="The member to remove timeout from",
        reason="The reason for removing timeout",
    )
    async def untimeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided.",
    ):
        bot_icon_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        dm_embed = discord.Embed(
            title=f"Your timeout has been removed in {interaction.guild.name}",
            description=f"Reason: {reason}",
            color=discord.Color.green(),
        )
        dm_embed.set_footer(text=f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if bot_icon_url:
            dm_embed.set_thumbnail(url=bot_icon_url)

        dm_sent = await self.send_dm_embed(member, dm_embed)
        try:
            await member.timeout(None, reason=reason)
            embed = discord.Embed(
                title="Member Untimeout",
                description=f"{member.mention} has been untimedout. Reason: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
            await self.log_infraction(interaction.guild.id, member.id, interaction.user.id, "untimeout", reason)
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I do not have permission to untimeout this member.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="history", description="Display a member's recent history."
    )
    @is_moderator()
    @app_commands.describe(member="The member to view history for")
    async def history(self, interaction: discord.Interaction, member: discord.Member):
        infractions = await self.bot.db.infractions.find({"guild_id": interaction.guild.id, "user_id": member.id}).sort("timestamp", pymongo.DESCENDING).limit(10).to_list(length=None)
        infraction_list = ""
        for infraction in infractions:
            infraction_list += f"`{infraction['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}` - **{infraction['type'].capitalize()}**: {infraction['reason']}\n"

        if not infraction_list:
            infraction_list = "No history found for this user."

        embed = discord.Embed(
            title=f"History for {member.name}", color=discord.Color.blue(),
            description=infraction_list
        )
        embed.add_field(
            name="Join Date",
            value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            inline=False,
        )
        embed.add_field(
            name="Account Creation Date",
            value=member.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="lockdown",
        description="Prevent sending messages in a channel.",
    )
    @is_moderator()
    @app_commands.describe(
        channel="The channel to lockdown", reason="The reason for the lockdown"
    )
    async def lockdown(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        reason: str = "No reason provided.",
    ):
        try:
            await channel.set_permissions(
                interaction.guild.default_role, send_messages=False
            )
            embed = discord.Embed(
                title="Channel Locked Down",
                description=f"{channel.mention} has been locked down. Reason: {reason}",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed)
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I do not have permission to lockdown this channel.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="unlockdown",
        description="Unlock a locked channel.",
    )
    @is_moderator()
    @app_commands.describe(
        channel="The channel to unlock", reason="The reason for the unlockdown"
    )
    async def unlockdown(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        reason: str = "No reason provided.",
    ):
        try:
            await channel.set_permissions(
                interaction.guild.default_role, send_messages=True
            )
            embed = discord.Embed(
                title="Channel Unlocked",
                description=f"{channel.mention} has been unlocked. Reason: {reason}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I do not have permission to unlock this channel.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="slowmode", description="Set slowmode in a channel."
    )
    @is_moderator()
    @app_commands.describe(
        channel="The channel to set slowmode in",
        seconds="The slowmode delay in seconds",
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
                title="Slowmode Set",
                description=f"Slowmode set to {seconds} seconds in {channel.mention}.",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I do not have permission to set slowmode in this channel.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.HTTPException:
            embed = discord.Embed(
                title="Error",
                description="Failed to set slowmode.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def log_infraction(self, guild_id, user_id, moderator_id, infraction_type, reason):
        infraction = {
            "guild_id": guild_id,
            "user_id": user_id,
            "moderator_id": moderator_id,
            "type": infraction_type,
            "reason": reason,
            "timestamp": datetime.datetime.utcnow()
        }
        await self.bot.db.infractions.insert_one(infraction)

@app_commands.context_menu(name="Purge Below")
@is_moderator()
async def purge_below(interaction: discord.Interaction, message: discord.Message):
    try:
        await interaction.response.defer(ephemeral=True)
        messages_to_delete = []
        async for msg in interaction.channel.history(limit=None, oldest_first=False):
            if msg.id == message.id:
                break
            messages_to_delete.append(msg)

        if messages_to_delete:
            await interaction.channel.delete_messages(
                messages_to_delete
            )

        embed = discord.Embed(
            title="Messages Purged Below",
            description=f"Purged {len(messages_to_delete)} messages below the selected message.",
            color=discord.Color.green(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    except discord.errors.Forbidden:
        embed = discord.Embed(
            title="Permission Error",
            description="I do not have permission to purge messages in this channel.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except discord.errors.HTTPException as e:
        embed = discord.Embed(
            title="Error",
            description=f"Purge failed: {e}",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ModCommands(bot))
    bot.tree.add_command(purge_below)