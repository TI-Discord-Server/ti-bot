import discord
from discord.ext import commands

blacklist = []
file = open("Blacklist.txt", "r")
lines = file.readlines()
for line in lines:
    line = line.rstrip()
    blacklist.append(line)


class Blacklist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        for word in blacklist:
            if word in message.content:
                await message.delete()
                await message.channel.send("Please refrain from using that language here %s!" % (message.author.mention), delete_after=10)


async def setup(bot):
    await bot.add_cog(Blacklist(bot))