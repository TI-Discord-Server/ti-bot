import discord, json, random
from discord.ext import commands, tasks
from datetime import datetime



mainServerID = 771394209419624489
class JobShit(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def cog_load(self):
        self.bot.add_view(MainViewW())

    @commands.command()
    @commands.has_role("The Council")
    async def jobMsg(self, ctx:commands.Context):
        await ctx.message.delete()
        em = discord.Embed(title="Job info - Insturen!", description="Ben je (net) afstudeerd en wil je je ervaring delen met mensen uit deze server zodat mensen beter weten wat te verwachten? ", color=0x0076C5)
        em.add_field(name="Anoniem / Niet anoniem;", value="Indien je deze informatie anoniem wilt delen, dan kan dat via onderstaande knop. Je naam wordt dan niet getoond. Indien dit geen probleem is kan je een normaal bericht sturen in dit kanaal met je ervaring")
        await ctx.send(embed=em, view=MainViewW())
    
    




async def setup(bot):
    await bot.add_cog(JobShit(bot))


class MainViewW(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MakeButtonW())

class MakeButtonW(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="Stuur anoniem in", row=1, custom_id="persistent_view:maakjobsh")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(MakeModal()) 

class MakeModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Job Ervaring", custom_id="persistent_view:formjobshit")

        self.add_item(
            discord.ui.TextInput(
                label="Wat is jouw ervaring?",
                style=discord.TextStyle.long,
            )
        )
    
    async def on_submit(self, interaction: discord.Interaction):
        em = discord.Embed(title="Nieuwe inzending!", description=f"**Bericht:** ```{self.children[0].value}```", color=0x0076C5)
        em.add_field(name="Wil je zelf ook anoniem je ervaring delen?", value="Klik dan op de knop bij het gepinde bericht!")
        await interaction.response.send_message(embed=em)