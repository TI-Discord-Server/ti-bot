# import discord
# from discord.ext import commands

# class NormalRoles(commands.Cog):
#     def __init__(self, bot):
#         self.bot = bot

#     @commands.command()
#     @commands.has_permissions(administrator=True)
#     async def normalR(self, ctx):
#         em1 = discord.Embed(title="School Rollen", color=0x0076C5)
#         em1.description = """<:Gent:775719708309585960> - Campus Gent
# <:Aalst:775720105488285697> - Campus Aalst
# 💻 - Virtual campus
# =======================
# 1️⃣ - 1e jaar
# 2️⃣ - 2e jaar
# 3️⃣ - 3e jaar
# =======================
# <a:hackerman:860201371655340072> - TIAO student
# <:peeposhy:773835107521003541> - IOEM student
# ✈️ - Buitenlandse Stage
# 🛫 - Erasmus
# <:frogshys:853749867867406346> - Graduaat student"""

#         em2 = discord.Embed(title="Fun Rollen", color=0x0076C5)
#         em2.description = """<:peepoGamer:892191595934384159> - Gamer
# <:Senpai:773958048024625213> - Anime
# <:pepelaugh:773835108431953922> - Fun"""

#         em3 = discord.Embed(title="Server Update Rol", color=0x0076C5)
#         em3.description = "<:check:853789642712809483> - Low priority"
#         await ctx.send(embed=em1)
#         await ctx.send(embed=em2)
#         await ctx.send(embed=em3)


# async def setup(bot):
#     await bot.add_cog(NormalRoles(bot))
