import discord
from discord.ext import tasks
import datetime


class ConfessionTasks:
    def __init__(self, bot):
        self.bot = bot
        self.review_channel_id = 1348669180840251465
        self.public_channel_id = 1342592622224605345
        self.daily_review.start()
        self.post_approved.start()

    async def get_settings(self):
        """Fetch confession settings from the database."""
        settings = await self.bot.db.settings.find_one({"_id": "confession_settings"})
        if not settings:
            settings = {
                "daily_review_limit": 5,
                "post_time": "18:00",
                "required_votes": 3,
            }
            await self.bot.db.settings.insert_one(
                {"_id": "confession_settings", **settings}
            )
        return settings

    @tasks.loop(time=datetime.time(hour=18, minute=0, tzinfo=datetime.UTC))
    async def daily_review(self):
        """Posts confessions for review."""
        settings = await self.get_settings()
        confessions = await self.bot.db.confessions.find({"status": "pending"}).to_list(
            settings["daily_review_limit"]
        )

        review_channel = self.bot.get_channel(self.review_channel_id)
        if not review_channel:
            return

        for confession in confessions:
            embed = discord.Embed(
                description=confession["content"], color=discord.Color.blue()
            )
            embed.set_footer(text=f"Confession ID: {confession['_id']}")
            message = await review_channel.send(embed=embed)
            await message.add_reaction("✅")
            await message.add_reaction("❌")

            await self.bot.db.confessions.update_one(
                {"_id": confession["_id"]}, {"$set": {"status": "under_review"}}
            )

    async def run_post_approved(self):
        """Handles confession posting manually or via the task loop."""
        settings = await self.get_settings()
        review_channel = self.bot.get_channel(self.review_channel_id)
        public_channel = self.bot.get_channel(self.public_channel_id)

        if not review_channel or not public_channel:
            print("Error: Review or public channel not found.")
            return

        messages = [msg async for msg in review_channel.history(limit=100)]
        confessions = await self.bot.db.confessions.find(
            {"status": "under_review"}
        ).to_list(None)

        for confession in confessions:
            matching_message = next(
                (
                    msg
                    for msg in messages
                    if msg.embeds
                    and msg.embeds[0].footer.text
                    == f"Confession ID: {confession['_id']}"
                ),
                None,
            )

            if not matching_message:
                continue

            allow_votes = sum(1 for r in matching_message.reactions if r.emoji == "✅")
            deny_votes = sum(1 for r in matching_message.reactions if r.emoji == "❌")

            if allow_votes + deny_votes >= settings["required_votes"]:
                embed = discord.Embed(
                    description=confession["content"], color=discord.Color.green()
                )
                await public_channel.send(embed=embed)

                await self.bot.db.confessions.update_one(
                    {"_id": confession["_id"]}, {"$set": {"status": "approved"}}
                )

            await matching_message.delete()

    @tasks.loop(time=datetime.time(hour=18, minute=0, tzinfo=datetime.UTC))
    async def post_approved(self):
        """Task loop for posting approved confessions."""
        await self.run_post_approved()
