import calendar
import discord, json
from discord.ext import commands
from discord import app_commands

from funcs import insertWarning, getWarnings, deleteWarning



class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.guilds(discord.Object(id=771394209419624489))
    @app_commands.checks.has_role("The Council")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, *, reason: str):
        await insertWarning(member.id, reason, interaction.user.id)
        em = discord.Embed(title="Warning", description=f"{member.mention} has been warned for {reason}", color=0xff0000)
        await interaction.response.send_message(embed=em)
        await member.send(f"Je hebt een waarschuwing gekregen in de TI discord met reden:  `{reason}`")



    
    @app_commands.command()
    @app_commands.guilds(discord.Object(id=771394209419624489))
    @app_commands.checks.has_role("The Council")
    async def removewarn(self, interaction: discord.Interaction, member: discord.Member, warnid: str):
        data = await deleteWarning(warnid)
        if data:
            em = discord.Embed(title="Remove Warning", description=f"Warning with ID `{warnid}`", color=0xff0000)
            member = interaction.guild.get_member(data["userID"])
            em.add_field(name="Member", value=f"{member.mention}")
            em.add_field(name="Reason", value=f"{data['reason']}")
            await interaction.response.send_message(embed=em)
        else:
            await interaction.response.send_message("Warning not found.")
        


    @app_commands.command()
    @app_commands.guilds(discord.Object(id=771394209419624489))
    @app_commands.checks.has_role("The Council")
    async def warns(self, interaction : discord.Interaction, member: discord.Member):
        data = await getWarnings(member.id)
        em = discord.Embed(title="Warnings", description=f"Warnings for {member.mention}\n\n", color=0x00ff00)
        em.description += "\n".join([f"**ID:** `{x['_id']}`\n **Reason:** {x['reason']}\n **Given By**: {interaction.guild.get_member(x['staffmember']).mention}\n **Timestamp**: <t:{calendar.timegm(x['timestamp'].timetuple())}:D>\n" for x in data])
        await interaction.response.send_message(embed=em)

        
            


async def setup(bot):
    await bot.add_cog(Moderation(bot))