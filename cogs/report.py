import discord
from discord.app_commands import (
    command,
)
from discord.ext import commands
import datetime
from utils.has_role import has_role


class Reports(commands.Cog, name="reports"):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.settings_id = "reports_settings"
        self.moderator_role_id = 1342591576764977223  # Default moderator role ID
        self.reports_channel_id = 1348653872767307816  # Default reports channel ID

    async def get_reports_channel_id(self):
        settings = await self.db.settings.find_one({"_id": self.settings_id})
        if settings and "reports_channel_id" in settings:
            return settings["reports_channel_id"]
        return self.reports_channel_id  # Return default if not set in DB

    @command(name="report", description="Report a user or issue to the moderators.")
    async def report(
            self,
            interaction: discord.Interaction,
            user: discord.User = None,
            reason: str = "No reason provided.",
    ):
        """
        Report a user or issue.
        """
        # Get the reports channel ID from the database
        reports_channel_id = await self.get_reports_channel_id()

        # Get the reports channel
        reports_channel = await self.bot.fetch_channel(reports_channel_id)
        if not reports_channel:
            await interaction.response.send_message(
                "Reports channel not found. Please contact an admin.", ephemeral=True
            )
            return

        # Create an embed for the report
        embed = discord.Embed(
            title="New Report",
            description=f"Report submitted by {interaction.user.mention}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        if user:
            embed.add_field(name="Reported User", value=user.mention, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)

        # Send the report to the reports channel
        await reports_channel.send(embed=embed)
        await reports_channel.send(
            f"<@&{self.moderator_role_id}>"
        )  # Ping the moderator role

        # Confirm to the user that the report was submitted
        await interaction.response.send_message(
            "Your report has been submitted. Thank you!", ephemeral=True
        )

    @command(
        name="set_report_channel",
        description="Set the channel where reports should be sent (Moderators only).",
    )
    @has_role("Moderator")
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
            f"Reports channel has been set to {channel.mention}."
        )

    @set_report_channel.error
    async def set_report_channel_error(
            self, interaction: discord.Interaction, error
    ):
        if isinstance(error, commands.CheckFailure):
            await interaction.response.send_message(
                "You do not have permission to use this command.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"An error occurred: {str(error)}", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Reports(bot))
