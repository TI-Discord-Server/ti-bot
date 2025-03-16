import discord
from discord.ext import commands
from discord import app_commands
from cogs.confessions.confession_view import ConfessionView
from cogs.confessions.confession_tasks import ConfessionTasks


class ConfessionCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tasks = ConfessionTasks(bot)

    @app_commands.command(
        name="setup_confessions",
        description="Set up the confession button in the public channel.",
    )
    @app_commands.checks.has_role(1342591576764977223)
    async def setup_confessions(self, interaction: discord.Interaction):
        view = ConfessionView(self.bot)
        await interaction.response.send_message(
            "Click the button below to submit a confession:", view=view
        )

    @app_commands.command(
        name="force_review", description="Force the review of confessions."
    )
    @app_commands.checks.has_role(1342591576764977223)
    async def force_review(self, interaction: discord.Interaction):
        await self.tasks.daily_review()
        await interaction.response.send_message(
            "Confession review has been forced.", ephemeral=True
        )

    @app_commands.command(
        name="force_post", description="Forceer het posten van confessions."
    )
    @app_commands.checks.has_role(
        1342591576764977223
    )  # Vervang met jouw moderatorrol-ID
    async def force_post(self, interaction: discord.Interaction):
        """Forceert het onmiddellijk posten van goedgekeurde confessions."""
        await interaction.response.send_message(
            "Forceren van confession posting...", ephemeral=True
        )

        # Direct de functie aanroepen om confessions te posten
        await self.tasks.run_post_approved()

        await interaction.followup.send(
            "Beoordeling en posting van confessions is geforceerd.", ephemeral=True
        )

    @app_commands.command(
        name="set_confession_settings",
        description="Stel het aantal confessions per dag en de post/review-tijden in.",
    )
    @app_commands.checks.has_role(1342591576764977223)  # Vervang met je moderatorrol-ID
    async def set_confession_settings(
        self,
        interaction: discord.Interaction,
        review_time: str,
        post_times: str,
    ):
        """Werk de confession instellingen bij en update taken direct."""

        # ✅ Controleer of review_time correct geformatteerd is
        try:
            hour, minute = map(int, review_time.strip().split(":"))
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError
            formatted_review_time = f"{hour:02}:{minute:02}"
        except ValueError:
            await interaction.response.send_message(
                "❌ Ongeldige review tijdsnotatie. Gebruik **HH:MM (24-uur formaat)**.",
                ephemeral=True,
            )
            return

        # ✅ Controleer of de post-tijden correct zijn
        post_times_list = post_times.split(",")
        formatted_post_times = []

        for time in post_times_list:
            try:
                hour, minute = map(int, time.strip().split(":"))
                if not (0 <= hour < 24 and 0 <= minute < 60):
                    raise ValueError
                formatted_post_times.append(f"{hour:02}:{minute:02}")  # HH:MM formaat
            except ValueError:
                await interaction.response.send_message(
                    "❌ Ongeldige post-tijden. Gebruik **HH:MM (24-uur formaat) en scheid met komma's**.",
                    ephemeral=True,
                )
                return

        if not formatted_post_times:
            await interaction.response.send_message(
                "❌ Je moet minstens **één** post-tijd instellen.",
                ephemeral=True,
            )
            return

        # ✅ Update instellingen in de database
        new_settings = {
            "_id": "confession_settings",
            "daily_review_limit": len(formatted_post_times),
            "review_time": formatted_review_time,
            "post_times": formatted_post_times,
        }
        await self.bot.db.settings.update_one(
            {"_id": "confession_settings"}, {"$set": new_settings}, upsert=True
        )

        # ✅ Update de geplande taken direct zonder de bot te herstarten
        await self.tasks.update_review_schedule()
        await self.tasks.update_post_schedule()

        # ✅ Bevestiging naar de gebruiker sturen
        await interaction.response.send_message(
            f"✅ **Confession instellingen bijgewerkt:**\n"
            f"- **Review tijd:** `{formatted_review_time}` UTC\n"
            f"- **Aantal confessions per dag:** `{len(formatted_post_times)}`\n"
            f"- **Post-tijden:** `{', '.join(formatted_post_times)}` UTC",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(ConfessionCommands(bot))
