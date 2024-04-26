import discord, json
from discord.ext import commands

data = json.load(open('roles.json', "r"))

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    async def cog_load(self):
        self.bot.add_view(MainView())
        self.bot.add_view(ITLabView())
        
    @commands.command()
    @commands.has_role("The Council")
    async def roleMsg(self, ctx: commands.Context):
        em = discord.Embed(title="Vak-Gerelateerde Roles", color=0x0076C5)
        em.add_field(name="Hoe neem ik vakken op?", value="Je kan vakken opnemen door onder dit bericht je jaar te selecteren. \nDaarna zal de bot je vragen voor welk semester / specialisaties je vakken wilt opnemen", inline=False)
        em.add_field(name="Hoe kan ik vakken verwijderen?", value="Om vak roles te verwijderen, doe je simpelweg exact hetzelfde als toen je ze opnam!", inline=False)
        em.set_footer(text="Vak-Gerelateerde Roles | TI-Bot")
        await ctx.send(embed=em, view=MainView())


    @commands.command()
    @commands.has_role("The Council")
    async def tilabbericht(self, ctx: commands.Context):
        em = discord.Embed(title="IT-Lab Pings", description="Indien je pings wenst omtrent het IT-lab, gelieve dan op onderstaande knop te duwen!", color=0x0076C5)
        em.set_footer(text="IT-Lab Pings | TI-Bot")
        await ctx.send(embed=em, view=ITLabView())

async def setup(bot):
    await bot.add_cog(Roles(bot))


class MainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(JaarKeuzeSelect())

class ITLabView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ITLabButton())

class ITLabButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.gray, label="Klik hier!", custom_id="persistent_view:ITLabButton")
    
    async def callback(self, interaction: discord.Interaction):
        role = discord.utils.get(interaction.guild.roles, name="IT-Lab Pings")
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            em = discord.Embed(title="IT-Lab Pings", description="Je zult niet langer pings over het IT-lab ontvangen!", color=0x0076C5)
        else:
            await interaction.user.add_roles(role)
            em = discord.Embed(title="IT-Lab Pings", description="Je zult pings over het IT-lab ontvangen!", color=0x0076C5)
        await interaction.response.send_message(embed=em, ephemeral=True)

class SemesterView(discord.ui.View):
    def __init__(self, jaarkeuze):
        super().__init__(timeout=None)
        self.add_item(SemesterSelect(jaarkeuze))
    


class SpecialisatieView(discord.ui.View):
    def __init__(self, jaarkeuze, semester):
        super().__init__(timeout=None)
        self.add_item(specialisatieSelect(jaarkeuze, semester))

class VakkenView(discord.ui.View):
    def __init__(self, jaarkeuze, semester, specialisatie, user):
        super().__init__(timeout=None)
        self.add_item(VakkenSelect(jaarkeuze, semester, specialisatie, user))



class JaarKeuzeSelect(discord.ui.Select):
    def __init__(self):

        options = []
        for key, value in data.items():
            options.append(discord.SelectOption(label=key))
        super().__init__(placeholder="Gelieve het jaar te kiezen waarvoor je roles wilt opnemen", min_values=1, max_values=1, options=options, custom_id="persistent_view:jaarkeuze")

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "3de Jaar":
            em = discord.Embed(title=f"{self.values[0]} Rollen", description="Gelieve te selecteren welke specialisatie je volgt!", color=0x0076C5)

            await interaction.response.send_message(embed=em, view=SpecialisatieView(self.values[0], None), ephemeral=True)
        elif self.values[0] == "Afgestudeerd" or self.values[0] == "Graduaat":
            role = discord.utils.get(interaction.guild.roles, name=data[self.values[0]])
            if not role in interaction.user.roles:
                await interaction.user.add_roles(role)
                em = discord.Embed(title=f"{self.values[0]} Rol", description="Je hebt de rol gekregen!", color=0x0076C5)
            else:
                await interaction.user.remove_roles(role)
                em = discord.Embed(title=f"{self.values[0]} Rol", description="Je hebt de rol verwijdert!", color=0x0076C5)
            
            await interaction.response.send_message(embed=em, ephemeral=True)
        else:
            em = discord.Embed(title=f"{self.values[0]} Rollen", description="Gelieve nu het semester te kiezen voor de rollen dat je wenst op te nemen!", color=0x0076C5)
            await interaction.response.send_message(embed=em, view=SemesterView(self.values[0]), ephemeral=True)
        
        await interaction.message.edit(embed=interaction.message.embeds[0])


class SemesterSelect(discord.ui.Select):
    def __init__(self, jaarkeuze):
        self.jaarkeuze = jaarkeuze
        options = []
        for key, value in data[jaarkeuze].items():
            options.append(discord.SelectOption(label=key))
        super().__init__(placeholder="Gelieve het semester te kiezen waarvoor je roles wilt opnemen", min_values=1, max_values=1, options=options, custom_id="persistent_view:semesterkeuze")

    async def callback(self, interaction: discord.Interaction):
        if self.jaarkeuze == "1ste Jaar":
            em = discord.Embed(title=f"{self.jaarkeuze} Rollen", description="Gelieve nu de vakken te kiezen dat je wilt opnemen!", color=0x0076C5)
            await interaction.response.edit_message(embed=em, view=VakkenView(self.jaarkeuze, self.values[0], None, interaction.user))

        else:
            em = discord.Embed(title=f"{self.jaarkeuze} Rollen", description="Gelieve te selecteren welke specialisatie je volgt!", color=0x0076C5)
            await interaction.response.edit_message(embed=em, view=SpecialisatieView(self.jaarkeuze, self.values[0]))

class specialisatieSelect(discord.ui.Select):
    def __init__(self, jaarkeuze, semester):
        self.jaarkeuze = jaarkeuze
        self.semester = semester
        options = []
        if jaarkeuze == "3de Jaar":
            for key, value in data[jaarkeuze].items():
               options.append(discord.SelectOption(label=key))
        else:
            for key, value in data[jaarkeuze][semester].items():
                options.append(discord.SelectOption(label=key))
        super().__init__(placeholder="Gelieve jouw specialisatie te kiezen", min_values=1, max_values=1, options=options, custom_id="persistent_view:specialisatiekeuze")

    async def callback(self, interaction: discord.Interaction):
        em = discord.Embed(title=f"{self.jaarkeuze} Rollen", description="Gelieve nu de vakken te kiezen dat je wilt opnemen!", color=0x0076C5)
        await interaction.response.edit_message(embed=em, view=VakkenView(self.jaarkeuze, self.semester, self.values[0], interaction.user))

class VakkenSelect(discord.ui.Select):
    def __init__(self, jaarkeuze, semester, specialisatie, user):
        self.jaarkeuze = jaarkeuze
        self.semester = semester
        self.specialisatie = specialisatie
        options = []
        if not semester:
            for roleName in data[jaarkeuze][specialisatie]:
                role = discord.utils.get(user.guild.roles, name=roleName)
                emoji = "✅" if role in user.roles else "❌"
                options.append(discord.SelectOption(label=roleName, emoji=emoji))
        elif specialisatie:
            for roleName in data[jaarkeuze][semester][specialisatie]:
                role = discord.utils.get(user.guild.roles, name=roleName)
                emoji = "✅" if role in user.roles else "❌"
                options.append(discord.SelectOption(label=roleName, emoji=emoji))
        else:
            for roleName in data[jaarkeuze][semester]:
                role = discord.utils.get(user.guild.roles, name=roleName)
                emoji = "✅" if role in user.roles else "❌"
                options.append(discord.SelectOption(label=roleName, emoji=emoji))


        super().__init__(placeholder="Gelieve jouw vakken te kiezen", min_values=1, max_values=len(options), options=options, custom_id="persistent_view:vakkenselect")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        added, removed = [], []
        for value in self.values:
            role = discord.utils.get(interaction.guild.roles, name=value)
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                removed.append(role)
            else:
                await interaction.user.add_roles(role)
                added.append(role)
        em = discord.Embed(title=f"{self.jaarkeuze} Rollen", description="Je rol(len) zijn geupdate!", color=0x0076C5)
        if added != []:
            em.add_field(name="Toegevoegd", value="\n".join([role.mention for role in added]), inline=False)
        if removed != []:
            em.add_field(name="Verwijderd", value="\n".join([role.mention for role in removed]), inline=False)
        await interaction.edit_original_response(embed=em, view=None)
