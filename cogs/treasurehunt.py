import discord, json
from discord.ext import commands

data = json.load(open("hunt.json", "r"))

class TreasureHunt(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    async def cog_load(self):
        self.bot.add_view(RespondView())

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def treasure(self, ctx:commands.Context):
        curLvl = ctx.channel.name
        em = discord.Embed(title=f"Treasure Hunt - {curLvl}", color=0x75101A)
        em.add_field(name="Antwoord gevonden?", value="Druk op onderstaande knop om in te dienen!")
        em.set_footer(text=f"Treasure hunt - TI Discord")
        await ctx.send(embed=em, view=RespondView())




async def setup(bot):
    await bot.add_cog(TreasureHunt(bot))

class RespondView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RespondButton())

class RespondButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="Dien in", row=1, custom_id="persistent_view:respond")

    async def callback(self, interaction: discord.Interaction):
        curLvl = interaction.channel.name
        await interaction.response.send_modal(ResponseModal(curLvl)) 

class ResponseModal(discord.ui.Modal):
    def __init__(self, lvl):
        self.curlvl = lvl

        self.nxtlvl = int(lvl[-1]) + 1
        super().__init__(title=f"{lvl} antwoord indienen", custom_id="persistent_view:respondform")

        self.add_item(
            discord.ui.TextInput(
                label="Wat is het antwoord voor deze challenge?",
                style=discord.TextInputStyle.short,
            )
        )
    
    async def callback(self, interaction: discord.Interaction):
        correctAnswer = data["answers"][self.curlvl]
        if self.children[0].value == correctAnswer:
            channel = discord.utils.get(interaction.guild.text_channels, name=f'level-{self.nxtlvl}')

            overwrites = channel.overwrites
            overwrites[interaction.user] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            await channel.edit(overwrites=overwrites)
            await interaction.response.send_message("Dit antwoord is correct, je hebt toegang gekregen tot de volgende challenge!", ephemeral=True)

        else:
            await interaction.response.send_message("Dit antwoord was niet correct, probeer gerust opnieuw!", ephemeral=True)