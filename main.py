import os, urllib, requests
from quart import Quart, render_template, request, send_from_directory, session, redirect, url_for
from quart_discord import DiscordOAuth2Session
from discord.ext import ipc
import urllib3
from funcs import *


app = Quart(__name__)
ipc_client = ipc.Client(secret_key = "test123")

app.config["SECRET_KEY"] = "test123"
app.config["DISCORD_CLIENT_ID"] = 928776060647133224   # Discord client ID.
app.config["DISCORD_CLIENT_SECRET"] = "3mLzT-L7Fwo9gZB7sZFH59Zg4fpg3igt"   # Discord client secret.
app.config["DISCORD_REDIRECT_URI"] = "https://nftracker.me/callback"   

discord = DiscordOAuth2Session(app)

@app.route("/")
async def home():
	if await discord.authorized:
		user = await discord.fetch_user()
	else:
		user = None
	return await render_template("pages/index.html", authorized = await discord.authorized, user = user)

@app.route("/pricing")
async def pricing():
	if await discord.authorized:
		user = await discord.fetch_user()
	else:
		user = None
	return await render_template("pages/pricing.html", authorized = await discord.authorized, user = user)

@app.route("/contact")
async def contact():
	if await discord.authorized:
		user = await discord.fetch_user()
	else:
		user = None
	return await render_template("pages/contact.html", authorized = await discord.authorized, user = user)

@app.route("/login")
async def login():
	return await discord.create_session()

@app.route("/callback")
async def callback():
	try:
		await discord.callback()
	except Exception:
		pass

	return redirect(url_for("home"))

@app.route("/dashboard")
async def dashboard():
	if not await discord.authorized:
		return redirect(url_for("login")) 

	guild_count = await ipc_client.request("get_guild_count")
	guild_ids = await ipc_client.request("get_guild_ids")

	user_guilds = await discord.fetch_guilds()

	guilds = []

	for guild in user_guilds:
		if guild.permissions.administrator:			
			guild.class_color = "green-border" if guild.id in guild_ids else "red-border"
			guilds.append(guild)

	guilds.sort(key = lambda x: x.class_color == "red-border")
	name = (await discord.fetch_user()).name
	return await render_template("pages/dashboard.html", guild_count = guild_count, guilds = guilds, username=name, authorized = await discord.authorized, user = await discord.fetch_user())

@app.route("/dashboard/<int:guild_id>")
async def dashboard_server(guild_id):

	if not await discord.authorized:
		return redirect(url_for("login")) 

	guild = await ipc_client.request("get_guild", guild_id = guild_id)
	channels = await ipc_client.request("get_channels", guild_id = guild_id)
	channelData = GetGuildChannelData(guild_id)
	if channelData:
		channelType = channelData["data"]["channelType"]


		if channelType == "combined":
			channelID = channelData["data"]["channelID"]
			channel = None
			for c in channels:
				if c.id == channelID:
					channel = c
					break
			setChannels = {
				"name": channel.name,
				"id": channel.id
			}
		else:
			channelID = channelData["data"]["channels"]
			setChannels = {}
			for blockchain, setChannelID in channelID.items():
				for c in channels:
					if c["id"] == setChannelID:
						setChannels[blockchain] = {"name": c["name"], "id": c["id"]}
		
		out ={
		"guild": guild,
		"channels": setChannels,
		"authorized": await discord.authorized,
		"user": await discord.fetch_user(),
		"allchannels": channels,
		"setup": True
		}
	else:
		out ={
		"guild": guild,
		"authorized": await discord.authorized,
		"user": await discord.fetch_user(),
		"setup" : False
		}
		




	if guild is None:
		return redirect(f'https://discord.com/oauth2/authorize?client_id=928776060647133224&permissions=313360&scope=bot%20applications.commands&guild_id={guild_id}&response_type=code&redirect_uri={app.config["DISCORD_REDIRECT_URI"]}')
	
	
	return await render_template("pages/serverdashboard.html", **out)

@app.route("/logout")
async def logout():
	discord.revoke()
	return redirect(url_for("home"))

@app.route("/invite")
async def invite():
	return redirect("https://discord.com/oauth2/authorize?client_id=928776060647133224&permissions=313360&scope=bot%20applications.commands")

@app.route("/dashboard/<int:guild_id>/updatechannels", methods = ["POST"])
async def updateguildchannels(guild_id):
	if not await discord.authorized:
		return redirect(url_for("login")) 
	
	dictt = await request.form
	dbout = {}
	for blockchain, channelID in dictt.items():
		dbout[blockchain] = int(channelID)
	insertServer(guild_id, "seperate", dbout)
	
	return redirect(url_for("dashboard_server", guild_id = guild_id))

@app.route("/ipncallback", methods = ["POST"])
async def ipncallback():
	values = await request.get_json()
	print(values)
	
	return "ok"


# @app.route("/test2546")
# async def test():
# 	await ipc_client.request("sendMsg")
# 	return "test"

if __name__ == "__main__":
	app.run(debug=True, host="0.0.0.0", port=443, certfile=os.path.abspath("nftracker_me.crt"), keyfile=os.path.abspath("nftracker.me.key"))