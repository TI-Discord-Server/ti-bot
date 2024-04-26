import discord, json
from discord.ext import commands
from funcs import getQueueLength



class ConfessionCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_role("The Council")
    async def cqueue(self, ctx:commands.Context):
        await ctx.send(f"{await getQueueLength()} confessions in queue")

async def setup(bot):
    await bot.add_cog(ConfessionCommands(bot))