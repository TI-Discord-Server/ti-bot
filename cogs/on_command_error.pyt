import discord, json
from discord.ext import commands


prefix = ">"
class OnCommandError(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.BadArgument) or isinstance(error, commands.ArgumentParsingError):
            em = discord.Embed(title="**An error occurred**", description="You badly used 1 or more arguments, use %shelp *command* to see correct usage!" % (prefix), color=discord.Colour.blurple())  
            em.set_footer(text=f"Use {prefix}help *command* for more info!")
            await ctx.send(embed=em, delete_after=10)           
        elif isinstance(error, commands.MissingRequiredArgument):
            em = discord.Embed(title="**An error occurred**", description="You are missing 1 or more arguments, use %shelp *command* to see correct usage!" % (prefix), color=discord.Colour.blurple())
            em.add_field(name="Missing argument", value=error.param.name)
            em.set_footer(text=f"Use {prefix}help *command* for more info!")
            await ctx.send(embed=em, delete_after=10)      
        elif isinstance(error, commands.MissingPermissions):
            em = discord.Embed(title="**An error occurred**", description="%s" % ("You don't have the correct role or permissions to do this!"), color=discord.Colour.blurple())
            out = ""
            for perm in error.missing_permissions:
                out += f":x: {perm}\n"
            em.add_field(name="Missing permissions", value=out)
            em.set_footer(text=f"Use {prefix}help *command* for more info!")
            await ctx.send(embed=em, delete_after=10)    
        elif isinstance(error, commands.CheckFailure):
            em = discord.Embed(title="**An error occurred**", description="%s" % ("You don't have the correct role to do this!"), color=discord.Colour.blurple())
            em.set_footer(text=f"Use {prefix}help *command* for more info!")
            await ctx.send(embed=em, delete_after=10)   
        elif isinstance(error, commands.BotMissingPermissions) or isinstance(error, discord.Forbidden):
            em = discord.Embed(title="**An error occurred**", description="%s" % ("It appears I am missing the right permissions to perform this command (on this user)."), color=discord.Colour.blurple())
            em.set_footer(text=f"Use {prefix}help *command* for more info!")
            await ctx.send(embed=em, delete_after=10)   

async def setup(bot):
    await bot.add_cog(OnCommandError(bot))

