import discord
from discord.ext import commands
from discord.commands import Option
from discord.commands import SlashCommandGroup

from fuzzywuzzy import fuzz

class faq(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_faq_entries(self, ctx: discord.AutocompleteContext):
        entries = self.bot.db.faq.find({"_id": {"$regex": "{}".format(ctx.value)}})
        return [x["_id"] for x in entries]

    faq = SlashCommandGroup("faq", "Frequently asked questions.")

    @faq.command(name="view", description="Bekijk een van de frequently asked questions.")
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def view(self, ctx, query: Option(str, "De vraag.", autocomplete=get_faq_entries, required=True)): # type: ignore
        question = self.bot.db.faq.find_one({"_id": query})
        if not question:
            return await ctx.respond(":x: | Deze kon ik niet vinden!", ephemeral=True)

        embed = discord.Embed(title=question["_id"], description=question["description"], color=0x000000)
        if "image" in question:
            embed.set_image(url=question["image"])
        return await ctx.respond(embed=embed)

    @faq.command(name="add", description="Voeg een frequently asked question toe.")
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def add(self, ctx, question: Option(str, "Vraag van de FAQ.", required=True), description: Option(str, "De content van de FAQ.", required=True), image: Option(str, "URL van een afbeelding voor de FAQ.", required=False)): # type: ignore
        question = self.bot.db.faq.find_one({"_id": question})
        if question:
            return await ctx.respond(":x: | Deze FAQ bestaat al!", ephemeral=True)

        self.bot.db.faq.insert_one({"_id": question, "description": description, "image": image})
        return await ctx.respond(":white_check_mark: | De FAQ is toegevoegd.", ephemeral=True)

    @faq.command(name="remove", description="Verwijder een FAQ.")
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def remove(self, ctx, query: Option(str, "De vraag.", autocomplete=get_faq_entries, required=True)): # type: ignore
        question = self.bot.db.faq.find_one({"_id": query})
        if not question:
            return await ctx.respond(":x: | Deze kon ik niet vinden!", ephemeral=True)

        self.bot.db.faq.delete_one({"_id": query})
        return await ctx.respond(":white_check_mark: | De FAQ is verwijderd.", ephemeral=True)

def setup(bot):
    n = faq(bot)
    bot.add_cog(n)