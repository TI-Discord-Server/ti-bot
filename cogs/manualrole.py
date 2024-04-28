import discord
from discord.ext import commands

class ManualRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_any_role("IT Lab Helper", "The Council")
    async def labhelper(self, ctx:commands.Context, member: discord.Member):
        role = discord.utils.get(ctx.guild.roles, name="IT Lab Helper")
        if role in member.roles:
            await member.remove_roles(role)
            await ctx.send(f"{member.mention} is niet meer IT Lab Helper!")
        else:
            await member.add_roles(role)
            await ctx.send(f"{member.mention} is nu IT Lab Helper!")

async def setup(bot):
    await bot.add_cog(ManualRoles(bot))