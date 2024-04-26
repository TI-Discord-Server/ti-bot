import asyncio
import discord, os, threading
from discord.ext import commands, ipc
from discord.ext.ipc.server import Server
from discord.ext.ipc.client import Client
from quart import Quart, render_template, request, send_from_directory, session, redirect, url_for
from quart_discord import DiscordOAuth2Session

import nest_asyncio
from discord import app_commands

from funcs import assignmessageID, getNewConfession


nest_asyncio.apply()

app = Quart(__name__)
ipc_client = Client(secret_key = "test123")

app.config["SECRET_KEY"] = "test123"
app.config["DISCORD_CLIENT_ID"] = 892157445223374949   # Discord client ID.
app.config["DISCORD_CLIENT_SECRET"] = "7Pa13_DLmfOvfOf5YRsNtcUQvq_U9mlr"   # Discord client secret.
app.config["DISCORD_REDIRECT_URI"] = "http://206.82.251.13:25581/callback" 
  

discordOath = DiscordOAuth2Session(app)


class MyBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.all()

        super().__init__(
            command_prefix=">",
            intents=intents,
        )

        self.ipc = ipc.Server(self, secret_key="test123")

    async def setup_hook(self) -> None:
        await self.ipc.start()

    @Server.route()
    async def isMod(self, data):
        print("AAAAAAAAAAAAAAAAAAAAAAA")
        guild = self.get_guild(771394209419624489)
        member = guild.get_member(data.userID)
        print("BBB")
        for role in member.roles:
            if role.name == "The Council":
                return {"isMod": True}
        return {"isMod": False}


bot = MyBot()

class ReportModal(discord.ui.Modal):
    def __init__(self, origMsg: discord.Message):
        self.origMsg = origMsg
        super().__init__(title="Bericht Rapporteren")

        self.add_item(
            discord.ui.TextInput(
                label="Waarom wil je dit bericht rapporteren?",
                style=discord.TextStyle.long,
            )
        )
        self.add_item(
            discord.ui.TextInput(
                label="Mogen we jou contacteren?",
                style=discord.TextStyle.short,
                placeholder="(Indien nee, laat dit leeg)",
                required=False
            )
        )
    
    async def on_submit(self, interaction: discord.Interaction):
        em = discord.Embed(title="Bericht Gerapporteerd", color=0x75101A)
        em.add_field(name="Origineel Bericht:", value=self.origMsg.content, inline=False)
        em.add_field(name="Originele Poster:", value=self.origMsg.author.mention)
        em.add_field(name="Jump URL:", value=f"[Jump]({self.origMsg.jump_url})")
        em.add_field(name="Reden:", value=self.children[0].value, inline=False)
        em.add_field(name="Contact:", value=self.children[1].value if self.children[1].value != "" else "Geen Contact", inline=False)

        em.set_footer(text=f"Gemaakt door: {interaction.user}")

        channel = discord.utils.get(interaction.guild.text_channels, name="reports")
        await channel.send(embed=em)
        await interaction.response.send_message("Bericht is gerapporteerd, bedankt!", ephemeral=True)

class MyHelp(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Help", color=0x5584F2)
        for cog, commands in mapping.items():
            filtered = await self.filter_commands(commands, sort=True)
            command_signatures = [f"`{c.name}`" for c in filtered]
            if command_signatures:
                cog_name = getattr(cog, "qualified_name", "No Category")
                embed.add_field(name=cog_name, value=", ".join(command_signatures), inline=False)
                embed.set_footer(text=bot.user.name, icon_url=bot.user.avatar.url)

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(title=self.get_command_signature(command), color=0x5584F2)
        embed.add_field(name="Help", value=command.help)
        alias = command.aliases
        if alias:
            embed.add_field(name="Aliases", value=", ".join(alias), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_error_message(self, error):
        embed = discord.Embed(title="Error", description=error, color=0x5584F2)
        channel = self.get_destination()
        await channel.send(embed=embed)

bot.help_command = MyHelp()




def read_token():
    with open('Bot.txt', 'r') as f:
            lines = f.readlines()
            return lines[0].strip()

token = read_token()



@bot.command()
@commands.has_role("The Council")
async def reload(ctx, cog = "All"):
    await ctx.message.delete()
    if cog == "All":
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await bot.unload_extension('cogs.%s' % (filename[:-3]))
                await bot.load_extension('cogs.%s' % (filename[:-3]))
        await ctx.send('Reloaded all cogs', delete_after=5)
    else:
        for filename in os.listdir('./cogs'):                      
            if filename.endswith('.py'):
                filename = filename[:-3] 
                if filename == cog:
                    await bot.unload_extension('cogs.%s' % (filename))
                    await bot.load_extension('cogs.%s' % (filename))
                    await ctx.send('Reloaded %s' % (filename), delete_after=5)
@bot.command()
@commands.has_role("The Council")
async def unload(ctx, arg):
    await bot.unload_extension(arg)
    await ctx.send('unloaded %s' % (arg), delete_after=5)

@bot.command()
@commands.has_role("The Council")
async def load(ctx, cog):
    for filename in os.listdir('./cogs'):                      
            if filename.endswith('.py'):
                filename = filename[:-3] 
                if filename == cog:
                    await bot.load_extension('cogs.%s' % (filename))
                    await ctx.send('loaded %s' % (filename), delete_after=5)


@bot.event
async def on_ready():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension('cogs.%s' % (filename[:-3]))
            print(filename)


    await bot.tree.sync(guild=discord.Object(id=771394209419624489))
            
    print(f'Logged in as {bot.user.name}')

@bot.tree.context_menu(name="Report Message")
@app_commands.guilds(discord.Object(id=771394209419624489))
async def report(interaction:discord.Interaction, msg : discord.Message):
    await interaction.response.send_modal(ReportModal(msg))




async def runSite(loop):
    app.run(debug=True, host="0.0.0.0", port=25581, loop=loop)

async def runBot():
    await bot.start(token)
    await bot.login(token)
    await bot.connect()

@app.route("/")
async def home():
	return await render_template("pages/index.html")

@app.route("/login")
async def login():
	return await discordOath.create_session()

@app.route("/modDashboard/loadNewConfession")
async def loadNewConfessionRoute():
    if not await discordOath.authorized:
        return redirect(url_for("login"))

    user = await discordOath.fetch_user()
    allowed = await ipc_client.request("isMod", userID = user.id)

    allowed = allowed["isMod"]


    if not allowed:
        return "Jij stoute poes, je mag hier niet zijn!"
    abc = await ipc_client.request("loadNewConfession")
    return abc

@app.route("/modDashboard/postConfession")
async def postConfessionRoute():
    if not await discordOath.authorized:
        return redirect(url_for("login"))

    user = await discordOath.fetch_user()
    allowed = await ipc_client.request("isMod", userID = user.id)

    allowed = allowed["isMod"]


    if not allowed:
        return "Jij stoute poes, je mag hier niet zijn!"
        
    abc = await ipc_client.request("postCheckingConfession")
    return abc

@app.route("/transcript/<id>")
async def log(id):
    return open(f"transcripts/{id}.html").read()

@app.route("/modDashboard")
async def modDashboard():
    if not await discordOath.authorized:
        return redirect(url_for("login"))

    user = await discordOath.fetch_user()
    allowed = await ipc_client.request("isMod", userID = user.id)

    allowed = allowed["isMod"]


    if not allowed:
        return "Jij stoute poes, je mag hier niet zijn!"


    return await render_template("pages/modDashboard.html")

@app.route("/callback")
async def callback():
	try:
		await discordOath.callback()
	except Exception:
		pass

	return redirect(url_for("modDashboard"))

@app.route("/logout")
async def logout():
    discordOath.revoke()
    return redirect(url_for("home"))








def init():
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(runBot())
    asyncio.ensure_future(runSite(loop))
    

    thread = threading.Thread(target=loop.run_forever())
    thread.start()
    thread.join()

init()



















    


        

        

      


    



        

      
    





   


        

