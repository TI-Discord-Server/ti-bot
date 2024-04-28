import asyncio, re
from unittest import async_case
from venv import create
import discord, smtplib, threading
from discord.ext import commands
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from funcs import checkIfAlreadyUsed, getLinkedUser, getUserCode, getLinkedEmailHash, genUserCode, getUserCodeHash, getVerifiedUsers, storeUserEmail, createHash

import hashlib


schoolEmail = "@student.hogent.be"
mainServerID = 771394209419624489


class EmailVerification(commands.Cog):
    def __init__(self, bot):
        self.bot : commands.Bot = bot

    
    async def cog_load(self):
        self.bot.add_view(VerificationView())

    @commands.command()
    @commands.has_role("The Council")
    async def verMsg(self, ctx:commands.Context):
        em = discord.Embed(title="Welkom!", description="Om spam te voorkomen vragen wij om te verifiëren dat jij wel degelijk een HoGent student bent.", color=0x0076C5)
        em.add_field(name="Wat te doen?", value='Druk simpelweg op onderstaande knop "Email Invoeren", voer dan in het kleine formulier je email in.\n Je ontvangt dan een code in je mailbox. (Door de spam filters zal die waarschijnlijk daar staan)\n\nEens je deze code hebt, druk dan op onderstaande knop "Ik heb een code" en voer daar je code in!', inline=False)
        em.add_field(name="Problemen?", value="DM mij (de bot) en we helpen je zo snel mogelijk!", inline=False)
        await ctx.send(embed=em, view=VerificationView())

    @commands.command()
    @commands.has_role("The Council")
    async def verifyMails(self, ctx: commands.Context):

        role = discord.utils.get(ctx.guild.roles, name="Email Verified")
        afgestudeerd = discord.utils.get(ctx.guild.roles, name="Afgestudeerd")
        alls = await getVerifiedUsers()

        verifiedIds = set([x["_id"] for x in alls])

        verified = 0
        notVerified = 0
        purged = 0

        for i, member in enumerate(ctx.guild.members):
            print(f"{i}/{len(ctx.guild.members)}")
            if member.id in verifiedIds:
                if role not in member.roles:
                    await member.add_roles(role)
                verified += 1
            else:
                notVerified += 1
                if afgestudeerd not in member.roles:
                    try:
                        await member.edit(roles=[])
                    except Exception as e:
                        print(e)
                        
                        
                    purged += 1
        
        await ctx.send("Done! Stats:\n" + f"Verified: {verified}\nNot Verified: {notVerified} (Purged: {purged})")

    @commands.command()
    @commands.has_role("Moderator")
    async def checkMail(self, ctx: commands.Context, *, email):
        hash = createHash(email)
        linkedUser = await getLinkedUser(hash)

        if not linkedUser:
            await ctx.send("No luck, deze email zit niet in onze DB")
            return 
        
        member = ctx.guild.get_member(linkedUser["_id"])
        if member:
            await ctx.send(f"{member.mention}\n---------\n{member.name}\n{member.id}")
        else:
            await ctx.send("No luck, deze user is niet in onze server")

    
    
async def worker(mailTo, discordID):
    sender_address = 'verificatie@mail.rmerens.com'
    receiver_address = mailTo
    
    
    token = await genUserCode(int(discordID), createHash(mailTo))
    email_content = open("email.txt", "r", encoding="utf-8").read() % (token)

    message = MIMEMultipart()
    message['From'] = sender_address
    message['To'] = receiver_address
    message['Subject'] = 'HoGent Discord Verificatie'   #The subject line
    message.attach(MIMEText(email_content, 'html'))


    session = smtplib.SMTP('email-smtp.eu-west-1.amazonaws.com', 587) #use gmail with port
    session.ehlo()
    session.starttls() #enable security
    session.login("AKIA4EZBBVR3FBQEP35U", "BCGc+/ouijrYQS00gEijOWE/t00HQWmNzsmBgG1wcHX3") #login with mail_id and password
    text = message.as_string()
    session.sendmail(sender_address, receiver_address, text)
    session.quit()

    
    return

async def setup(bot):
    await bot.add_cog(EmailVerification(bot))


class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(EmailButton())
        self.add_item(CodeButton())

class EmailButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="Email Invoeren", row=1, custom_id="persistent_view:email")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EmailModal())

class CodeButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="Ik heb een code", row=1, custom_id="persistent_view:code")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(CodeModal())

def getrealemail(mail):
    return re.sub(r'\+[^)]*@', '@', mail)

class EmailModal(discord.ui.Modal):
    inp = discord.ui.TextInput(
                label="Wat is jouw hogent email?",
                style=discord.TextStyle.short,
            )
    def __init__(self):
        super().__init__(title="Discord Verificatie", custom_id="persistent_view:emailform")
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        mail = getrealemail(self.inp.value)
        nowHash = createHash(mail)
        savedHash = await getLinkedEmailHash(interaction.user.id)

        print("met re:", mail)
        print("zonder re:", self.inp.value)

        if not schoolEmail in mail:
            await interaction.followup.send("Dit is geen HoGent email!", ephemeral=True)
            return
        

        check = await checkIfAlreadyUsed(mail, interaction.user.id)

        
        if nowHash != savedHash and savedHash is not None:
            await interaction.followup.send("Je hebt al een email geregistreerd!", ephemeral=True)
            return 

        if check:
            await interaction.followup.send("Deze email is al in gebruik!", ephemeral=True)
            return
        
        em = discord.Embed(title="De email wordt verzonden, controleer zeker je spam folder! Dit kan maximaal 5 minuten duren.", color=0x0076C5)
        await interaction.followup.send(embed=em, ephemeral=True)

        try:
            await worker(mail, interaction.user.id)
        except:
            await interaction.followup.send("Er is iets misgelopen, probeer het later opnieuw!", ephemeral=True)
            return
        
        
        

        

        

        



class CodeModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Discord Verificatie", custom_id="persistent_view:codeform")

        self.add_item(
            discord.ui.TextInput(
                label="Welke code heb je ontvangen?",
                style=discord.TextStyle.short,
            )
        )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        discordID = interaction.user.id
        token = await getUserCode(discordID)
        hash = await getUserCodeHash(discordID)
        if not self.children[0].value == str(token):
            em = discord.Embed(title="Deze code is niet juist, controleer deze en probeer opnieuw!", color=discord.Colour.brand_red())
            await interaction.followup.send(embed=em, ephemeral=True)
            return

        await storeUserEmail(int(discordID), hash)

        role = discord.utils.get(interaction.guild.roles, name="Verified")
        await interaction.user.add_roles(role)
        em = discord.Embed(title="Je bent successvol geverifieerd!", color=0x0076C5)
        await interaction.followup.send(embed=em, ephemeral=True)


