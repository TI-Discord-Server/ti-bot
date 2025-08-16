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
        await reports_channel.send(embed=embed)
        await reports_channel.send(f"<@&{self.moderator_role_id}>")

        await interaction.response.send_message(
            "Je rapport is ingediend. Bedankt!", ephemeral=True
        )

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


async def setup(bot):
    await bot.add_cog(Reports(bot))
