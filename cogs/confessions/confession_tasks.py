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
        """Post confessions voor review."""
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

            # Sla de Message-ID op in de database
            await self.bot.db.confessions.update_one(
                {"_id": confession["_id"]},
                {"$set": {"status": "under_review", "message_id": message.id}},
            )

    async def run_post_approved(self):
        """Verwerkt en post confessions die in review staan."""
        review_channel = self.bot.get_channel(self.review_channel_id)
        public_channel = self.bot.get_channel(self.public_channel_id)

        if not review_channel or not public_channel:
            print("Error: Review of public channel niet gevonden.")
            return

        # Haal alle berichten op uit het reviewkanaal
        messages = [msg async for msg in review_channel.history(limit=100)]

        # Maak een dictionary met Message-ID als sleutel voor snellere lookup (O(1))
        message_dict = {str(msg.id): msg for msg in messages}

        # Haal alle confessions op die in review staan
        confessions = await self.bot.db.confessions.find(
            {"status": "under_review"}
        ).to_list(None)

        # Tel hoeveel confessions al gepost zijn
        posted_count = await self.bot.db.confessions.count_documents(
            {"status": "posted"}
        )

        for confession in confessions:
            message_id = str(
                confession.get("message_id")
            )  # Haal de message-ID op uit de database
            matching_message = message_dict.get(
                message_id, None
            )  # Zoek de bijbehorende message

            if not matching_message:
                print(f"Geen match gevonden voor confession {confession['_id']}")
                continue  # Skip als de message niet gevonden wordt

            # Tel de stemmen correct
            allow_votes = 0
            deny_votes = 0

            for reaction in matching_message.reactions:
                users = [user async for user in reaction.users()]
                non_bot_users = [
                    user for user in users if not user.bot
                ]  # Filter bots eruit
                if reaction.emoji == "✅":
                    allow_votes = len(non_bot_users)
                elif reaction.emoji == "❌":
                    deny_votes = len(non_bot_users)

            print(
                f"Confession {confession['_id']} heeft {allow_votes} stemmen voor en {deny_votes} stemmen tegen."
            )

            if allow_votes > deny_votes:
                # Verhoog het confession nummer
                posted_count += 1

                # Post de confession in het public_channel met nummer
                embed = discord.Embed(
                    title=f"Confession #{posted_count}",
                    description=confession["content"],
                    color=discord.Color.green(),
                )
                await public_channel.send(embed=embed)

                # Update de confession naar "posted"
                await self.bot.db.confessions.update_one(
                    {"_id": confession["_id"]},
                    {"$set": {"status": "posted", "confession_number": posted_count}},
                )

                # Verwijder het review bericht
                await matching_message.delete()

            elif allow_votes < deny_votes:
                # Confession wordt afgekeurd
                await self.bot.db.confessions.update_one(
                    {"_id": confession["_id"]}, {"$set": {"status": "rejected"}}
                )

                # Verwijder het review bericht
                await matching_message.delete()

            else:
                # Als stemmen gelijk zijn, reset de confession naar "pending"
                print(
                    f"Confession {confession['_id']} blijft onder review vanwege gelijke stemmen. Opnieuw in review gezet."
                )

                await self.bot.db.confessions.update_one(
                    {"_id": confession["_id"]},
                    {"$set": {"status": "pending", "message_id": None}},
                )

                # Verwijder het oude review bericht
                await matching_message.delete()

    @tasks.loop(time=datetime.time(hour=18, minute=0, tzinfo=datetime.UTC))
    async def post_approved(self):
        """Task loop for posting approved confessions."""
        await self.run_post_approved()
