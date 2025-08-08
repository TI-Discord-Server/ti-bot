import discord
from discord.ext import tasks, commands
import datetime
from cogs.confessions.confession_view import ConfessionView


class ConfessionTasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_review = None
        self.post_approved = None

        self.bot.loop.create_task(self.init_tasks())

    async def get_review_channel_id(self):
        settings = await self.bot.db.settings.find_one({"_id": "confession_settings"})
        if settings and "review_channel_id" in settings:
            return settings["review_channel_id"]
        return None

    async def get_public_channel_id(self):
        settings = await self.bot.db.settings.find_one({"_id": "confession_settings"})
        if settings and "public_channel_id" in settings:
            return settings["public_channel_id"]
        return None

    async def init_tasks(self):
        await self.update_review_schedule()
        await self.update_post_schedule()

    async def get_settings(self):
        settings = await self.bot.db.settings.find_one({"_id": "confession_settings"})
        if not settings:
            settings = {
                "daily_review_limit": 2,
                "review_time": "17:00",
                "post_times": ["9:00", "12:00"],
            }
            await self.bot.db.settings.insert_one(
                {"_id": "confession_settings", **settings}
            )
            self.bot.log.info(
                "Standaard confession instellingen aangemaakt in de database."
            )
        return settings

    async def update_review_schedule(self):
        settings = await self.get_settings()
        review_time_str = settings["review_time"]

        try:
            hour, minute = map(int, review_time_str.split(":"))
            review_time = datetime.time(hour=hour, minute=minute, tzinfo=datetime.UTC)

            if self.daily_review and self.daily_review.is_running():
                self.daily_review.cancel()
                self.bot.log.info(
                    f"Review-taak gestopt voor update naar {review_time} UTC."
                )

            @tasks.loop(time=[review_time])
            async def daily_review_task():
                await self._daily_review_task()

            self.daily_review = daily_review_task
            self.daily_review.start()
            self.bot.log.info(f"Review-taak gestart op tijdstip: {review_time} UTC.")

        except ValueError:
            self.bot.log.error("Ongeldige review-tijd opgegeven in settings.")

    async def _daily_review_task(self):
        settings = await self.get_settings()
        confessions = await self.bot.db.confessions.find({"status": "pending"}).to_list(
            settings["daily_review_limit"]
        )

        review_channel_id = await self.get_review_channel_id()
        if not review_channel_id:
            self.bot.log.error("Review kanaal ID niet geconfigureerd.")
            return
            
        review_channel = self.bot.get_channel(review_channel_id)
        if not review_channel:
            self.bot.log.error("Reviewkanaal niet gevonden.")
            return

        if not confessions:
            self.bot.log.info("Geen nieuwe confessions om te reviewen.")
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
            self.bot.log.debug(f"Confession {confession['_id']} geplaatst voor review.")

    async def update_post_schedule(self):
        settings = await self.get_settings()
        post_times = settings["post_times"]

        if not post_times:
            self.bot.log.warning(
                "Geen post-tijden ingesteld. Post-taak wordt niet gestart."
            )
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

            if self.post_approved and self.post_approved.is_running():
                self.post_approved.cancel()
                self.bot.log.info(f"Post-taak gestopt voor update naar tijden: {times}")

            @tasks.loop(time=times)
            async def post_approved_task():
                await self._post_approved_task()

            self.post_approved = post_approved_task
            self.post_approved.start()
            self.bot.log.info(f"Post-taak gestart met tijden: {times}")

        except ValueError:
            self.bot.log.error("Ongeldige post-tijden in de settings.")

    async def _post_approved_task(self):
        await self.run_post_approved()

    async def run_post_approved(self):
        review_channel_id = await self.get_review_channel_id()
        public_channel_id = await self.get_public_channel_id()
        
        if not review_channel_id or not public_channel_id:
            self.bot.log.error("Review of public kanaal ID niet geconfigureerd.")
            return
            
        review_channel = self.bot.get_channel(review_channel_id)
        public_channel = self.bot.get_channel(public_channel_id)

        if not review_channel or not public_channel:
            self.bot.log.error("Review- of public-channel niet gevonden.")
            return

        messages = [msg async for msg in review_channel.history(limit=100)]
        message_dict = {str(msg.id): msg for msg in messages}

        confession = await self.bot.db.confessions.find_one({"status": "under_review"})
        if not confession:
            self.bot.log.info("Geen confessions beschikbaar om te posten.")
            return

        message_id = str(confession.get("message_id"))
        matching_message = message_dict.get(message_id)

        if not matching_message:
            self.bot.log.warning(
                f"Geen matching message gevonden voor confession {confession['_id']}"
            )
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

        self.bot.log.debug(
            f"Confession {confession['_id']} - ✅ {allow_votes}, ❌ {deny_votes}"
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

            self.bot.log.info(f"Confession #{posted_count} gepost.")

        elif allow_votes < deny_votes:
            await self.bot.db.confessions.update_one(
                {"_id": confession["_id"]}, {"$set": {"status": "rejected"}}
            )
            await matching_message.delete()
            self.bot.log.info(f"Confession {confession['_id']} werd verworpen.")

        else:
            await self.bot.db.confessions.update_one(
                {"_id": confession["_id"]},
                {"$set": {"status": "pending", "message_id": None}},
            )
            await matching_message.delete()
            self.bot.log.info(
                f"Confession {confession['_id']} blijft onder review vanwege gelijke stemmen."
            )


async def setup(bot):
    await bot.add_cog(ConfessionTasks(bot))
