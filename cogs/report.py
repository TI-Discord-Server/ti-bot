import discord
from discord.app_commands import (
    command,
)
from discord.ext import commands
import datetime


class Reports(commands.Cog, name="reports"):
    def __init__(self, bot):
        self.bot = bot
        self.reports_channel_id = 1348653872767307816  # Replace with reports channel ID
        self.moderator_role_id = 1342591576764977223  # Replace with council role ID

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
        # Get the reports channel
        reports_channel = self.bot.get_channel(self.reports_channel_id)
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
            timestamp=datetime.datetime.now(datetime.UTC),
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


async def setup(bot):
    await bot.add_cog(Reports(bot))
