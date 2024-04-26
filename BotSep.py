import asyncio
import json
import discord, os, threading
from discord.ext import commands, ipc
from quart import Quart, render_template, request, send_from_directory, session, redirect, url_for
from quart_discord import DiscordOAuth2Session


from discord import app_commands


app = Quart(__name__)


app.config["SECRET_KEY"] = "test123"
app.config["DISCORD_CLIENT_ID"] = 1161274501972107394   # Discord client ID.
app.config["DISCORD_CLIENT_SECRET"] = "QBvOx3DvLN08MLMnRvf1yRmnw1mjNhpa"   # Discord client secret.
app.config["DISCORD_REDIRECT_URI"] = "http://klipperpi.local:25567/callback" 
  

discordOath = DiscordOAuth2Session(app)


class MyBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.all()

        super().__init__(
            command_prefix=">",
            intents=intents,
        )

        self.ipc = ipc.Server(self, secret_key="test123")

    




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

    


    #await bot.tree.sync(guild=discord.Object(id=771394209419624489))
            
    print(f'Logged in as {bot.user.name}')

@bot.tree.context_menu(name="Report Message")
@app_commands.guilds(discord.Object(id=771394209419624489))
async def report(interaction:discord.Interaction, msg : discord.Message):
    await interaction.response.send_modal(ReportModal(msg))

@bot.tree.context_menu(name="Open TIBot Dashboard")
@app_commands.guilds(discord.Object(id=771394209419624489))
async def opendashboard(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(f"http://pterodactyl.lamdev.be:25567/modDashboard/user/{member.id}", ephemeral=True)












bot.run(token)




















    


        

        

      


    



        

      
    





   


        

