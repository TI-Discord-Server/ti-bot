import discord, json, random
from discord.ext import commands, tasks, ipc
from datetime import datetime

from funcs import *


mainServerID = 771394209419624489
class Confessions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if not hasattr(bot, "ipc"):
            bot.ipc = ipc.Server(self.bot, secret_key="test123")
    
    async def cog_load(self):
        self.mainLoop.start()
        self.bot.add_view(ConfessionsView())

    @commands.command()
    @commands.has_role("The Council")
    async def confMsg(self, ctx:commands.Context):
        em = discord.Embed(title="TI Confessions - Insturen!", color=0x0076C5)
        await ctx.send(embed=em, view=ConfessionsView())
    
    @commands.command()
    @commands.has_role("The Council")
    async def reloadData(self, ctx:commands.Context):
        data = json.load(open("confessions.json", "r", encoding="utf-8"))
        await ctx.send("Data reloaded")

    @tasks.loop(seconds=60)
    async def mainLoop(self):

        guild = self.bot.get_guild(771394209419624489)

        time = (datetime.now()).strftime("%H:%M")
        checkChannel = discord.utils.get(guild.channels, name="confessions-check")
        mainChannel = discord.utils.get(guild.channels, name="confessions")

        if time == "15:00":
            chosen = []

            amount = 2 if await getQueueLength() >= 2 else await getQueueLength()

            for i in range(amount):
                rand = await getNewConfession()
                chosen.append(rand)
            
            
            for confession in chosen:
                em = discord.Embed(title="Confession Check", description=confession["confession"], color=0x1ab015)
                em.add_field(name="Confession Check", value="Gelieve te reageren met :white_check_mark:, :x: of :recycle:")
                msg = await checkChannel.send(embed=em)
                await msg.add_reaction("✅")
                await msg.add_reaction("❌")
                await msg.add_reaction("♻️")
                await assignmessageID(confession["_id"], msg.id)


            await mainChannel.send("\U0000200b", view=ConfessionsView())
        
        if time == "15:00" or time == "10:41" or time == "08:36":
            await self.handleConfession()


    # @Server.route()
    # async def loadNewConfession(self, data):
    #     confession = getNewConfession()

    #     guild = self.bot.get_guild(771394209419624489)

    #     checkChannel = discord.utils.get(guild.channels, name="confessions-check")


    #     em = discord.Embed(title="Confession Check", description=confession["confession"], color=0x1ab015)
    #     em.add_field(name="Confession Check", value="Gelieve te reageren met :white_check_mark:, :x: of :recycle:")
    #     msg = await checkChannel.send(embed=em)
    #     await msg.add_reaction("✅")
    #     await msg.add_reaction("❌")
    #     await msg.add_reaction("♻️")



    #     assignmessageID(confession["_id"], msg.id)
    #     return {"status": "success"}

    # @Server.route()
    # async def postCheckingConfession(self, data):
    #     await self.handleConfession()
    #     return {"status": "success"}
    
    # @Server.route()
    # async def checkConfession(self, data):
    #     await self.handleConfession(int(data["confID"]))
    #     return {"status": "success"}
    
    # @Server.route()
    # async def queueConfession(self, data):
    #     try:
    #         confession = getConfession(int(data["confID"]))

    #         guild = self.bot.get_guild(771394209419624489)

    #         checkChannel = discord.utils.get(guild.channels, name="confessions-check")


    #         em = discord.Embed(title="Confession Check", description=confession["confession"], color=0x1ab015)
    #         em.add_field(name="Confession Check", value="Gelieve te reageren met :white_check_mark:, :x: of :recycle:")
    #         msg = await checkChannel.send(embed=em)
    #         await msg.add_reaction("✅")
    #         await msg.add_reaction("❌")
    #         await msg.add_reaction("♻️")



    #         assignmessageID(confession["_id"], msg.id)
    #         setStatus(confession["_id"], "checking")
    #         return {"status": "success"}
    #     except:
    #         return {"status": "error"}
        
        

                
                


    
    async def handleConfession(self, confID = None):
        guild = self.bot.get_guild(771394209419624489)
        checkChannel = discord.utils.get(guild.channels, name="confessions-check")
        mainChannel = discord.utils.get(guild.channels, name="confessions")

        confession = await getCheckingConfession() if confID == None else await getConfession(confID)
        if confession:
            msgID = int(confession["messageID"])
            conf = confession["confession"]


            checkMsg = await checkChannel.fetch_message(msgID)

            good = 0
            bad = 0
            recycle = 0

            for reaction in checkMsg.reactions:
                if reaction.emoji == "✅": good = reaction.count
                elif reaction.emoji == "❌": bad += reaction.count
                elif reaction.emoji == "♻️": recycle += reaction.count
            

            
            async def Recycle():
                await setStatus(confession["_id"], "waiting")
                await checkMsg.delete()

            
            async def Remove():
                await setStatus(confession["_id"], "removed")
                await checkMsg.delete()


            async def Send():
                await mainChannel.send(f"#{await GetSentCount()+350}\n{conf}")
                await setStatus(confession["_id"], "sent")
                await checkMsg.delete()

            if good > bad and good > recycle:
                await Send()
            elif bad >= good:
                if bad > recycle:
                    await Remove()
                else:
                    await Recycle() #recycle
            else:
                await Recycle() #recycle







async def setup(bot):
    await bot.add_cog(Confessions(bot))


class MakeModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="TI Confession", custom_id="persistent_view:form")

        self.add_item(
            discord.ui.TextInput(
                label="Wat is jouw confession?",
                style=discord.TextStyle.long,
            )
        )
    
    async def on_submit(self, interaction: discord.Interaction):
 
        

        await insertConfession(self.children[0].value)
        em = discord.Embed(title="Jouw confession is successvol toegevoegd aan de lijst!", color=0x0076C5)
        await interaction.response.send_message(embed=em, ephemeral=True)

class ConfessionsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ConfessionButton())
        

class ConfessionButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Maak Confession", style=discord.ButtonStyle.primary, custom_id="persistent_view:maak")

    async def callback(self, interaction):
        view = RulesView()
        embed = discord.Embed(title="Confessions Disclaimer", color=0x0076C5, description="` 1. ` De form is volledig anoniem.**\n- Pestgedrag wordt niet getolereerd.\n` 2. ` Hou je confessions safe for work. *(Dit betekent dat er wel eens iets naughty in mag zitten maar niet extreem)*\n` 3. ` Malicious links worden niet getolereerd.\n` 4. ` Zorg ervoor dat je een confession stuurt, niet een verhaaltje of een advertentie.")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()

class RulesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)
        self.add_item(MakeButton())

    async def on_timeout(self):
        self.stop()
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass

class MakeButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Maak Confession", style=discord.ButtonStyle.primary, custom_id="persistent_view:maakEcht")

    async def callback(self, interaction):
        await interaction.response.send_modal(MakeModal())
