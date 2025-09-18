import discord
from discord.ext import tasks, commands
import datetime
from cogs.confessions.confession_view import ConfessionView
from utils.timezone import LOCAL_TIMEZONE, local_time


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
            review_time = local_time(hour, minute)

            if self.daily_review and self.daily_review.is_running():
                self.daily_review.cancel()
                self.bot.log.info(
                    f"Review-taak gestopt voor update naar {review_time} Brussels tijd."
                )

            @tasks.loop(time=[review_time])
            async def daily_review_task():
                await self._daily_review_task()

            self.daily_review = daily_review_task
            self.daily_review.start()
            self.bot.log.info(f"Review-taak gestart op tijdstip: {review_time} Brussels tijd.")

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
                local_time(
                    hour=int(t.split(":")[0]),
                    minute=int(t.split(":")[1])
                )
                for t in post_times
            ]

            if self.post_approved and self.post_approved.is_running():
                self.post_approved.cancel()
                self.bot.log.info(f"Post-taak gestopt voor update naar tijden: {times} (Brussels tijd)")

            @tasks.loop(time=times)
            async def post_approved_task():
                await self._post_approved_task()

            self.post_approved = post_approved_task
            self.post_approved.start()
            self.bot.log.info(f"Post-taak gestart met tijden: {times} (Brussels tijd)")

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

            # Post de confession
            embed = discord.Embed(
                title=f"Confession #{posted_count}",
                description=confession["content"],
                color=discord.Color.green(),
            )

            # Bepaal of dit de laatste van de dag is
            settings = await self.get_settings()
            post_times = settings.get("post_times", [])
            last_post_time = post_times[-1] if post_times else None

            is_last_confession = False
            if last_post_time:
                hour, minute = map(int, last_post_time.split(":"))
                now = datetime.datetime.now(LOCAL_TIMEZONE)
                is_last_confession = now.hour == hour and now.minute == minute

            if is_last_confession:
                from cogs.confessions.confession_view import ConfessionView
                await public_channel.send(embed=embed, view=ConfessionView(self.bot))
            else:
                await public_channel.send(embed=embed)

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

    async def _delete_previous_submit_message(self, public_channel):
        """Delete the previous submit confession message if it exists."""
        try:
            # Get the stored submit message ID from database
            settings = await self.bot.db.settings.find_one({"_id": "confession_settings"})
            if not settings or "submit_message_id" not in settings:
                return
            
            submit_message_id = settings["submit_message_id"]
            if not submit_message_id:
                return
            
            # Try to fetch and delete the message
            try:
                submit_message = await public_channel.fetch_message(submit_message_id)
                await submit_message.delete()
                self.bot.log.debug(f"Deleted previous submit message {submit_message_id}")
                
                # Remove from persistent views database
                if self.bot.persistent_view_manager:
                    await self.bot.persistent_view_manager.remove_view_message(public_channel.id, submit_message_id)
                
            except discord.NotFound:
                self.bot.log.debug(f"Previous submit message {submit_message_id} not found (already deleted)")
                # Still try to remove from persistent views database in case it's there
                if self.bot.persistent_view_manager:
                    await self.bot.persistent_view_manager.remove_view_message(public_channel.id, submit_message_id)
            except discord.Forbidden:
                self.bot.log.warning(f"No permission to delete submit message {submit_message_id}")
            except Exception as e:
                self.bot.log.error(f"Error deleting submit message {submit_message_id}: {e}")
                
        except Exception as e:
            self.bot.log.error(f"Error in _delete_previous_submit_message: {e}")

    async def _post_submit_message(self, public_channel):
        """Post a new submit confession message (eenmalig via command)."""
        self.bot.log.debug("Posting new submit confession message...")
        try:
            embed = discord.Embed(
                title="📝 Submit a Confession",
                description="Click the button below to submit an anonymous confession.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="ℹ️ How it works",
                value=(
                    "• Your confession will be reviewed by moderators\n"
                    "• If approved, it will be posted anonymously\n"
                    "• All submissions are completely anonymous"
                ),
                inline=False
            )

            # Post het bericht met de knop
            submit_message = await public_channel.send(embed=embed, view=ConfessionView(self.bot))

            # ⚠️ Geen opslag in de database meer!
            # Zo kan er nooit automatisch iets mee gedaan worden

            self.bot.log.debug(f"Posted one-time submit message {submit_message.id}")

        except Exception as e:
            self.bot.log.error(f"Error posting submit message: {e}")


async def setup(bot):
    await bot.add_cog(ConfessionTasks(bot))
