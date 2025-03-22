import discord
from discord.ext import tasks, commands
import datetime
from cogs.confessions import ConfessionView


class ConfessionTasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.review_channel_id = 1348669180840251465
        self.public_channel_id = 1342592622224605345
        self.daily_review = None  # De taak wordt pas later geïnitialiseerd
        self.post_approved = None  # Zelfde voor post_approved

        self.bot.loop.create_task(
            self.init_tasks()
        )  # Start taken pas na database-initialisatie

    async def init_tasks(self):
        """Laadt de instellingen en start taken."""
        await self.update_review_schedule()
        await self.update_post_schedule()

    async def get_settings(self):
        """Haalt de confession settings op uit de database."""
        settings = await self.bot.db.settings.find_one({"_id": "confession_settings"})
        if not settings:
            settings = {
                "daily_review_limit": 2,
                "review_time": "17:00",  # Standaard review tijd
                "post_times": ["9:00", "12:00"],  # Standaard 1 post tijd
            }
            await self.bot.db.settings.insert_one(
                {"_id": "confession_settings", **settings}
            )
        return settings

    async def update_review_schedule(self):
        """Update het tijdstip waarop confessions naar het reviewkanaal worden gestuurd."""
        settings = await self.get_settings()
        review_time_str = settings["review_time"]

        try:
            hour, minute = map(int, review_time_str.split(":"))
            review_time = datetime.time(hour=hour, minute=minute, tzinfo=datetime.UTC)

            # ✅ Stop de oude taak als deze draait
            if self.daily_review and self.daily_review.is_running():
                self.daily_review.cancel()
                print(f"🔄 Review taak gestopt, update naar {review_time}")

            # ✅ Start de taak opnieuw met de nieuwe tijd
            @tasks.loop(time=[review_time])
            async def daily_review_task():
                await self._daily_review_task()

            self.daily_review = daily_review_task
            self.daily_review.start()
            print(f"✅ Review taak gestart met nieuwe tijd: {review_time}")

        except ValueError:
            print("❌ Error: Ongeldige review-tijd in de settings.")

    async def _daily_review_task(self):
        """Taak die confessions in het reviewkanaal plaatst."""
        settings = await self.get_settings()
        confessions = await self.bot.db.confessions.find({"status": "pending"}).to_list(
            settings["daily_review_limit"]
        )

        review_channel = self.bot.get_channel(self.review_channel_id)
        if not review_channel:
            print("Review channel niet gevonden.")
            return

        for confession in confessions:
            embed = discord.Embed(
                description=confession["content"], color=discord.Color.blue()
            )
            message = await review_channel.send(embed=embed)
            await message.add_reaction("✅")
            await message.add_reaction("❌")

            await self.bot.db.confessions.update_one(
                {"_id": confession["_id"]},
                {"$set": {"status": "under_review", "message_id": message.id}},
            )

    async def update_post_schedule(self):
        """Update de post-tijden voor goedgekeurde confessions."""
        settings = await self.get_settings()
        post_times = settings["post_times"]

        if not post_times:
            print("⚠️ Geen post-tijden ingesteld. Post-taak wordt niet gestart.")
            return

        try:
            times = [
                datetime.time(
                    hour=int(t.split(":")[0]),
                    minute=int(t.split(":")[1]),
                    tzinfo=datetime.UTC,
                )
                for t in post_times
            ]

            # ✅ Stop de oude taak als deze draait
            if self.post_approved and self.post_approved.is_running():
                self.post_approved.cancel()
                print(f"🔄 Post-taak gestopt, update naar {times}")

            # ✅ Start de taak opnieuw met de nieuwe tijden
            @tasks.loop(time=times)
            async def post_approved_task():
                await self._post_approved_task()

            self.post_approved = post_approved_task
            self.post_approved.start()
            print(f"✅ Post-taak gestart met nieuwe tijden: {times}")

        except ValueError:
            print("❌ Error: Ongeldige post-tijden in de settings.")

    async def _post_approved_task(self):
        """Achtergrondtaak die goedgekeurde confessions post."""
        await self.run_post_approved()

    async def run_post_approved(self):
        """Verwerkt en post exact **één** confession per geplande post-tijd."""
        review_channel = self.bot.get_channel(self.review_channel_id)
        public_channel = self.bot.get_channel(self.public_channel_id)

        if not review_channel or not public_channel:
            print("Error: Review of public channel niet gevonden.")
            return

        messages = [msg async for msg in review_channel.history(limit=100)]
        message_dict = {str(msg.id): msg for msg in messages}

        # ✅ Haal **slechts 1 confession** op die nog in review staat
        confession = await self.bot.db.confessions.find_one({"status": "under_review"})

        if not confession:
            print("⚠️ Geen confessions beschikbaar om te posten.")
            return

        message_id = str(confession.get("message_id"))
        matching_message = message_dict.get(message_id, None)

        if not matching_message:
            print(f"Geen match gevonden voor confession {confession['_id']}")
            return

        allow_votes = 0
        deny_votes = 0

        for reaction in matching_message.reactions:
            users = [user async for user in reaction.users()]
            non_bot_users = [user for user in users if not user.bot]
            if reaction.emoji == "✅":
                allow_votes = len(non_bot_users)
            elif reaction.emoji == "❌":
                deny_votes = len(non_bot_users)

        print(
            f"Confession {confession['_id']} heeft {allow_votes} stemmen voor en {deny_votes} stemmen tegen."
        )

        if allow_votes > deny_votes:
            posted_count = (
                await self.bot.db.confessions.count_documents({"status": "posted"}) + 1
            )

            embed = discord.Embed(
                title=f"Confession #{posted_count}",
                description=confession["content"],
                color=discord.Color.green(),
            )
            await public_channel.send(embed=embed, view=ConfessionView(self.bot))

            await self.bot.db.confessions.update_one(
                {"_id": confession["_id"]},
                {"$set": {"status": "posted", "confession_number": posted_count}},
            )

            await matching_message.delete()

        elif allow_votes < deny_votes:
            await self.bot.db.confessions.update_one(
                {"_id": confession["_id"]}, {"$set": {"status": "rejected"}}
            )
            await matching_message.delete()

        else:
            print(
                f"Confession {confession['_id']} blijft onder review vanwege gelijke stemmen."
            )
            await self.bot.db.confessions.update_one(
                {"_id": confession["_id"]},
                {"$set": {"status": "pending", "message_id": None}},
            )
            await matching_message.delete()


async def setup(bot):
    await bot.add_cog(ConfessionTasks(bot))
