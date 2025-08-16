import discord
from discord import app_commands
from discord.app_commands import command
from discord.ext import commands
import datetime
from utils.has_admin import has_admin


class Reports(commands.Cog, name="reports"):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.settings_id = "reports_settings"

    async def get_reports_channel_id(self):
        settings = await self.db.settings.find_one({"_id": self.settings_id})
        if settings and "reports_channel_id" in settings:
            return settings["reports_channel_id"]
        return None

    async def get_moderator_role_id(self):
        settings = await self.db.settings.find_one({"_id": self.settings_id})
        if settings and "moderator_role_id" in settings:
            return settings["moderator_role_id"]
        return None

    @command(name="report", description="Rapporteer een gebruiker of probleem aan de moderators.")
    @app_commands.describe(
        user="De gebruiker die je wilt rapporteren",
        reason="De reden van je melding",
        message_id="De ID van het bericht dat je wilt melden (optioneel)",
    )
    async def report(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        reason: str,
        message_id: str = None,
    ):
        """Report a user, issue, or specific message."""

        reports_channel_id = await self.get_reports_channel_id()
        
        if not reports_channel_id:
            await interaction.response.send_message(
                "❌ Geen rapportage kanaal geconfigureerd. Neem contact op met een beheerder.", ephemeral=True
            )
            return
            
        try:
            reports_channel = await self.bot.fetch_channel(reports_channel_id)
        except discord.NotFound:
            await interaction.response.send_message(
                "❌ Het geconfigureerde rapportage kanaal bestaat niet meer. Neem contact op met een beheerder.", ephemeral=True
            )
            return
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Geen toegang tot het rapportage kanaal. Neem contact op met een beheerder.", ephemeral=True
            )
            return
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Fout bij toegang tot rapportage kanaal: {str(e)}", ephemeral=True
            )
            return

        # Bouw het embed
        embed = discord.Embed(
            title="New Report",
            description=f"Report submitted by {interaction.user.mention}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(),
        )

        if user:
            embed.add_field(name="Reported User", value=user.mention, inline=False)

        embed.add_field(name="Reason", value=reason, inline=False)

        # Als message ID is opgegeven, probeer het bericht op te halen
        if message_id:
            try:
                # Probeer het bericht op te halen in het huidige kanaal waar het command is uitgevoerd
                reported_message = await interaction.channel.fetch_message(
                    int(message_id)
                )
                msg_link = f"https://discord.com/channels/{interaction.guild_id}/{interaction.channel_id}/{message_id}"
                embed.add_field(
                    name="Reported Message",
                    value=f"[Jump to message]({msg_link})",
                    inline=False,
                )
                embed.add_field(
                    name="Message Content",
                    value=reported_message.content[:1024],
                    inline=False,
                )
            except Exception as e:
                embed.add_field(
                    name="Message Error",
                    value=f"Kon bericht niet ophalen. Mogelijk fout ID of geen toegang.\n`{str(e)}`",
                    inline=False,
                )

        # Verstuur de report
        moderator_role_id = await self.get_moderator_role_id()
        await reports_channel.send(embed=embed)
        if moderator_role_id:
            await reports_channel.send(f"<@&{moderator_role_id}>")

        await interaction.response.send_message(
            "Je rapport is ingediend. Bedankt!", ephemeral=True
        )

    @command(name="report_anonymous", description="Rapporteer een gebruiker of probleem anoniem aan de moderators.")
    @app_commands.describe(
        user="De gebruiker die je wilt rapporteren",
        reason="De reden van je melding",
        message_id="De ID van het bericht dat je wilt melden (optioneel)",
    )
    async def report_anonymous(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        reason: str,
        message_id: str = None,
    ):
        """Report a user, issue, or specific message anonymously."""

        reports_channel_id = await self.get_reports_channel_id()
        
        if not reports_channel_id:
            await interaction.response.send_message(
                "❌ Geen rapportage kanaal geconfigureerd. Neem contact op met een beheerder.", ephemeral=True
            )
            return
            
        try:
            reports_channel = await self.bot.fetch_channel(reports_channel_id)
        except discord.NotFound:
            await interaction.response.send_message(
                "❌ Het geconfigureerde rapportage kanaal bestaat niet meer. Neem contact op met een beheerder.", ephemeral=True
            )
            return
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Geen toegang tot het rapportage kanaal. Neem contact op met een beheerder.", ephemeral=True
            )
            return
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Fout bij toegang tot rapportage kanaal: {str(e)}", ephemeral=True
            )
            return

        # Bouw het embed voor anonieme rapportage
        embed = discord.Embed(
            title="🕵️ Anonymous Report",
            description="Report submitted anonymously",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now(),
        )

        if user:
            embed.add_field(name="Reported User", value=user.mention, inline=False)

        embed.add_field(name="Reason", value=reason, inline=False)

        # Als message ID is opgegeven, probeer het bericht op te halen
        if message_id:
            try:
                # Probeer het bericht op te halen in het huidige kanaal waar het command is uitgevoerd
                reported_message = await interaction.channel.fetch_message(
                    int(message_id)
                )
                msg_link = f"https://discord.com/channels/{interaction.guild_id}/{interaction.channel_id}/{message_id}"
                embed.add_field(
                    name="Reported Message",
                    value=f"[Jump to message]({msg_link})",
                    inline=False,
                )
                embed.add_field(
                    name="Message Content",
                    value=reported_message.content[:1024],
                    inline=False,
                )
            except Exception as e:
                embed.add_field(
                    name="Message Error",
                    value=f"Kon bericht niet ophalen. Mogelijk fout ID of geen toegang.\n`{str(e)}`",
                    inline=False,
                )

        # Verstuur de anonieme report
        moderator_role_id = await self.get_moderator_role_id()
        await reports_channel.send(embed=embed)
        if moderator_role_id:
            await reports_channel.send(f"<@&{moderator_role_id}>")

        await interaction.response.send_message(
            "Je anonieme rapport is ingediend. Bedankt!", ephemeral=True
        )

    # Context Menu Commands (Discord Apps)
    @app_commands.context_menu(name="Report User")
    async def report_user_context(self, interaction: discord.Interaction, user: discord.User):
        """Report a user via context menu."""
        await interaction.response.send_modal(ReportUserModal(self, user))

    @app_commands.context_menu(name="Report Message")
    async def report_message_context(self, interaction: discord.Interaction, message: discord.Message):
        """Report a message via context menu."""
        await interaction.response.send_modal(ReportMessageModal(self, message))

    @command(
        name="set_report_channel",
        description="Stel het kanaal in waar rapporten naartoe gestuurd moeten worden (Alleen moderators).",
    )
    @has_admin()
    async def set_report_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        """
        Set the channel where reports should be sent.
        """
        # Update the reports channel ID in the settings collection
        await self.db.settings.update_one(
            {"_id": self.settings_id},  # Filter by the specific ID
            {"$set": {"reports_channel_id": channel.id}},  # Update or set the field
            upsert=True,  # Create the document if it doesn't exist
        )

        await interaction.response.send_message(
            f"Rapportage kanaal is ingesteld op {channel.mention}."
        )

    @command(
        name="set_moderator_role",
        description="Stel de moderator rol in die genotificeerd wordt bij rapporten (Alleen moderators).",
    )
    @has_admin()
    async def set_moderator_role(
        self, interaction: discord.Interaction, role: discord.Role
    ):
        """
        Set the moderator role that gets notified for reports.
        """
        # Update the moderator role ID in the settings collection
        await self.db.settings.update_one(
            {"_id": self.settings_id},  # Filter by the specific ID
            {"$set": {"moderator_role_id": role.id}},  # Update or set the field
            upsert=True,  # Create the document if it doesn't exist
        )

        await interaction.response.send_message(
            f"Moderator rol is ingesteld op {role.mention}."
        )

    @set_report_channel.error
    async def set_report_channel_error(self, interaction: discord.Interaction, error):
        if isinstance(error, commands.CheckFailure):
            await interaction.response.send_message(
                "Je hebt geen toestemming om dit commando te gebruiken.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Er is een fout opgetreden: {str(error)}", ephemeral=True
            )

    @set_moderator_role.error
    async def set_moderator_role_error(self, interaction: discord.Interaction, error):
        if isinstance(error, commands.CheckFailure):
            await interaction.response.send_message(
                "Je hebt geen toestemming om dit commando te gebruiken.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Er is een fout opgetreden: {str(error)}", ephemeral=True
            )


class ReportUserModal(discord.ui.Modal, title="Report User"):
    def __init__(self, reports_cog, user):
        super().__init__()
        self.reports_cog = reports_cog
        self.user = user

    reason = discord.ui.TextInput(
        label="Reason for reporting",
        placeholder="Describe why you're reporting this user...",
        style=discord.TextStyle.long,
        required=True,
        max_length=1000
    )

    anonymous = discord.ui.TextInput(
        label="Anonymous? (yes/no)",
        placeholder="Type 'yes' for anonymous report, 'no' for regular report",
        style=discord.TextStyle.short,
        required=False,
        default="no",
        max_length=3
    )

    async def on_submit(self, interaction: discord.Interaction):
        is_anonymous = self.anonymous.value.lower() in ['yes', 'y', 'true', '1']
        
        reports_channel_id = await self.reports_cog.get_reports_channel_id()
        
        if not reports_channel_id:
            await interaction.response.send_message(
                "❌ Geen rapportage kanaal geconfigureerd. Neem contact op met een beheerder.", ephemeral=True
            )
            return
            
        try:
            reports_channel = await self.reports_cog.bot.fetch_channel(reports_channel_id)
        except discord.NotFound:
            await interaction.response.send_message(
                "❌ Het geconfigureerde rapportage kanaal bestaat niet meer. Neem contact op met een beheerder.", ephemeral=True
            )
            return
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Geen toegang tot het rapportage kanaal. Neem contact op met een beheerder.", ephemeral=True
            )
            return
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Fout bij toegang tot rapportage kanaal: {str(e)}", ephemeral=True
            )
            return

        # Create embed
        if is_anonymous:
            embed = discord.Embed(
                title="🕵️ Anonymous User Report",
                description="User reported anonymously via context menu",
                color=discord.Color.orange(),
                timestamp=datetime.datetime.now(),
            )
        else:
            embed = discord.Embed(
                title="👤 User Report",
                description=f"User reported by {interaction.user.mention} via context menu",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now(),
            )

        embed.add_field(name="Reported User", value=self.user.mention, inline=False)
        embed.add_field(name="User ID", value=str(self.user.id), inline=True)
        embed.add_field(name="Reason", value=self.reason.value, inline=False)

        # Send report
        moderator_role_id = await self.reports_cog.get_moderator_role_id()
        await reports_channel.send(embed=embed)
        if moderator_role_id:
            await reports_channel.send(f"<@&{moderator_role_id}>")

        report_type = "anonieme" if is_anonymous else "normale"
        await interaction.response.send_message(
            f"Je {report_type} gebruiker rapport is ingediend. Bedankt!", ephemeral=True
        )


class ReportMessageModal(discord.ui.Modal, title="Report Message"):
    def __init__(self, reports_cog, message):
        super().__init__()
        self.reports_cog = reports_cog
        self.message = message

    reason = discord.ui.TextInput(
        label="Reason for reporting",
        placeholder="Describe why you're reporting this message...",
        style=discord.TextStyle.long,
        required=True,
        max_length=1000
    )

    anonymous = discord.ui.TextInput(
        label="Anonymous? (yes/no)",
        placeholder="Type 'yes' for anonymous report, 'no' for regular report",
        style=discord.TextStyle.short,
        required=False,
        default="no",
        max_length=3
    )

    async def on_submit(self, interaction: discord.Interaction):
        is_anonymous = self.anonymous.value.lower() in ['yes', 'y', 'true', '1']
        
        reports_channel_id = await self.reports_cog.get_reports_channel_id()
        
        if not reports_channel_id:
            await interaction.response.send_message(
                "❌ Geen rapportage kanaal geconfigureerd. Neem contact op met een beheerder.", ephemeral=True
            )
            return
            
        try:
            reports_channel = await self.reports_cog.bot.fetch_channel(reports_channel_id)
        except discord.NotFound:
            await interaction.response.send_message(
                "❌ Het geconfigureerde rapportage kanaal bestaat niet meer. Neem contact op met een beheerder.", ephemeral=True
            )
            return
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Geen toegang tot het rapportage kanaal. Neem contact op met een beheerder.", ephemeral=True
            )
            return
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Fout bij toegang tot rapportage kanaal: {str(e)}", ephemeral=True
            )
            return

        # Create embed
        if is_anonymous:
            embed = discord.Embed(
                title="🕵️ Anonymous Message Report",
                description="Message reported anonymously via context menu",
                color=discord.Color.orange(),
                timestamp=datetime.datetime.now(),
            )
        else:
            embed = discord.Embed(
                title="💬 Message Report",
                description=f"Message reported by {interaction.user.mention} via context menu",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now(),
            )

        embed.add_field(name="Reported User", value=self.message.author.mention, inline=False)
        embed.add_field(name="User ID", value=str(self.message.author.id), inline=True)
        embed.add_field(name="Channel", value=self.message.channel.mention, inline=True)
        
        # Create message link
        msg_link = f"https://discord.com/channels/{interaction.guild_id}/{self.message.channel.id}/{self.message.id}"
        embed.add_field(name="Message Link", value=f"[Jump to message]({msg_link})", inline=False)
        
        # Add message content (truncated if too long)
        content = self.message.content if self.message.content else "*No text content*"
        if len(content) > 1024:
            content = content[:1021] + "..."
        embed.add_field(name="Message Content", value=content, inline=False)
        
        embed.add_field(name="Reason", value=self.reason.value, inline=False)

        # Add attachment info if present
        if self.message.attachments:
            attachment_info = "\n".join([f"• {att.filename}" for att in self.message.attachments])
            embed.add_field(name="Attachments", value=attachment_info, inline=False)

        # Send report
        moderator_role_id = await self.reports_cog.get_moderator_role_id()
        await reports_channel.send(embed=embed)
        if moderator_role_id:
            await reports_channel.send(f"<@&{moderator_role_id}>")

        report_type = "anonieme" if is_anonymous else "normale"
        await interaction.response.send_message(
            f"Je {report_type} bericht rapport is ingediend. Bedankt!", ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Reports(bot))
