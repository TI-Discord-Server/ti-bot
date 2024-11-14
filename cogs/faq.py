import discord
from discord.app_commands import (
    Choice,
    Group,
    AppCommandContext,
    command,
    describe,
    guild_only,
    autocomplete,
)
from discord.app_commands.checks import cooldown
from discord.ext import commands
from discord.interactions import Interaction

from typing import List

import random
from fuzzywuzzy import fuzz


class faq(commands.Cog, name="faq"):
    def __init__(self, bot):
        self.bot = bot

    async def get_faq_entries(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[Choice[str]]:
        # If the current input is less than 2 characters, return a random selection of entries.
        entries = []
        if len(current) <= 1:
            async for entry in self.bot.extra.faq.find(
                {}
            ):  # {"_id": {"$regex": "{}".format(current)}}
                entries.append(Choice(name=entry["_id"], value=entry["_id"]))
            random.shuffle(entries)
            entries = entries[:25]
            return entries

        # Initial base threshold, increasing with length of current.
        base_threshold = 5
        threshold = min(base_threshold + len(current) * 2, 70)
        # Score and filter entries based on similarity
        async for entry in self.bot.extra.faq.find(
            {}
        ):  # {"_id": {"$regex": "{}".format(current)}}
            entry_id = entry["_id"]
            score = fuzz.ratio(current.lower(), entry_id.lower())
            if score >= threshold:
                entries.append((Choice(name=entry_id, value=entry_id), score))
        # Sort by score in descending order and take the top results.
        sorted_entries = [
            choice for choice, _ in sorted(entries, key=lambda x: x[1], reverse=True)
        ]
        return sorted_entries[:25]

    faq = Group(
        name="faq",
        description="Frequently asked questions.",
        allowed_contexts=AppCommandContext(guild=True),
    )

    @faq.command(
        name="view",
        description="Display one of the frequently asked questions.",
    )
    @describe(query="Enter something to search for a question.")
    @autocomplete(query=get_faq_entries)
    @cooldown(1, 2, key=lambda i: (i.guild_id, i.user.id))
    async def view(self, interaction: Interaction, query: str):
        question = await self.bot.extra.faq.find_one({"_id": query})
        if not question:
            return await interaction.response.send_message(
                ":x: | I couldn't find the question you're looking for!", ephemeral=True
            )

        embed = discord.Embed(
            title=question["_id"], description=question["description"], color=0xFFFFFF
        )
        if "image" in question:
            embed.set_image(url=question["image"])
        return await interaction.response.send_message(embed=embed)

    @faq.command(
        name="add",
        description="Add a frequently asked question.",
    )
    @describe(
        title="The new question/title.",
        description="The content of the FAQ.",
        image="The URL to a relevant image to go with the FAQ.",
    )
    @cooldown(1, 2, key=lambda i: (i.guild_id, i.user.id))
    async def add(
        self, interaction: Interaction, title: str, description: str, image: str = None
    ):
        question = await self.bot.extra.faq.find_one({"_id": title})
        if question:
            return await interaction.response.send_message(
                ":x: | A question with this title already exists!", ephemeral=True
            )

        await self.bot.extra.faq.insert_one(
            {"_id": title, "description": description, "image": image}
        )
        return await interaction.response.send_message(
            ":white_check_mark: | The question has been added.", ephemeral=True
        )

    @faq.command(name="remove", description="Remove a frequently asked question.")
    @describe(query="The question/title you want to remove.")
    @autocomplete(query=get_faq_entries)
    @cooldown(1, 2, key=lambda i: (i.guild_id, i.user.id))
    async def remove(self, interaction: Interaction, query: str):
        question = await self.bot.extra.faq.find_one({"_id": query})
        if not question:
            return await interaction.response.send_message(
                ":x: | I couldn't find the question you're looking for!", ephemeral=True
            )

        await self.bot.extra.faq.delete_one({"_id": query})
        return await interaction.response.send_message(
            ":white_check_mark: | The question has been removed.", ephemeral=True
        )


async def setup(bot):
    n = faq(bot)
    await bot.add_cog(n)
