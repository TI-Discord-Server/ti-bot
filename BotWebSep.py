import asyncio
from functools import wraps
import discord, os, threading
from discord.ext import commands, ipc
from discord.ext.ipc.server import Server
from discord.ext.ipc.client import Client
from quart import Quart, render_template, request, send_from_directory, session, redirect, url_for
from quart_discord import DiscordOAuth2Session


from discord import app_commands
from funcs import deleteConfession, deleteWarning, getCheckingConfessions, getAllConfessions, getModmail, getTranscripts, getUserServerInfo, getWarns, restoreConfession



app = Quart(__name__)
ipc_client = Client(secret_key = "test123")

app.config["SECRET_KEY"] = "test123"
app.config["DISCORD_CLIENT_ID"] = 1161274501972107394   # Discord client ID.
app.config["DISCORD_CLIENT_SECRET"] = "QBvOx3DvLN08MLMnRvf1yRmnw1mjNhpa"   # Discord client secret.
app.config["DISCORD_REDIRECT_URI"] = "http://klipperpi.local:25567/callback" 
#app.config["DISCORD_REDIRECT_URI"] = "http://127.0.0.1:25567/callback" 
  

discordOath = DiscordOAuth2Session(app)





def isMod(fn):
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        if request.remote_addr == "127.0.0.1":
            return await fn(*args, **kwargs)

        if not await discordOath.authorized:
            return redirect(url_for("login"))

        user = await discordOath.fetch_user()
        allowed = await ipc_client.request("isMod", userID = user.id)
        allowed = allowed["isMod"]


        if not allowed:
            return "Jij stoute poes, je mag hier niet zijn!"
        else:
            return await fn(*args, **kwargs)

    return wrapper


@app.route("/")
async def home():
	return await render_template("index.html")

@app.route("/login")
async def login():
	return await discordOath.create_session()

@app.route("/modDashboard/loadNewConfession")
@isMod
async def loadNewConfessionRoute():
    await ipc_client.request("loadNewConfession")
    return redirect(url_for("modDashboardConfs"))

@app.route("/modDashboard/postConfession")
@isMod
async def postConfessionRoute():
    await ipc_client.request("postCheckingConfession")
    return redirect(url_for("modDashboardConfs"))

@app.route("/api/checkConfession/<id>")
@isMod
async def checkConfession(id):
    await ipc_client.request("checkConfession", confID = id)
    return redirect(url_for("modDashboardConfs"))

@app.route("/api/queueConfession/<id>")
@isMod
async def queueConfession(id):
    await ipc_client.request("queueConfession", confID = id)
    return redirect(url_for("modDashboardConfs"))

@app.route("/api/deleteConfession/<id>")
@isMod
async def deleteConfessionRoute(id):
    deleteConfession(int(id))
    return redirect(url_for("modDashboardConfs"))

@app.route("/api/deleteWarn/<id>")
@isMod
async def deleteWarnRoute(id):
    deleteWarning(id)
    return redirect(url_for("modDashboardWarns"))

@app.route("/api/restoreConfession/<id>")
@isMod
async def restoreConfessionRoute(id):
    restoreConfession(int(id))
    return redirect(url_for("modDashboardConfs"))

@app.route("/transcript/<id>")
async def log(id):
    return open(f"transcripts/{id}.html").read()

@app.route("/modDashboard")
@isMod
async def modDashboard():
    return await render_template("modDashboard.html")

@app.route("/modDashboard/user/<id>")
@isMod
async def modDashboardUserRoute(id):
    userID = int(id)
    userDiscInfo = await ipc_client.request("getUser", userID = userID)
    userServerInfo = getUserServerInfo(userID)
    user = await ipc_client.request("getUser", userID = userID)
    for warn in userServerInfo["warns"]:
        l = {
            "id": warn["_id"],
            "userID": warn["userID"],
            "user": user,
            "reason": warn["reason"],
            "warnedBy": await ipc_client.request("getUser", userID = warn["staffmember"]),
            "date": str(warn["timestamp"]),
        }
        userServerInfo["warns"][userServerInfo["warns"].index(warn)] = l
    modmail = getModmail(userID)
    transcript = getTranscripts(userID)

    return await render_template(
        "userInfo.html",
        userDiscordInfo = userDiscInfo,
        userServerInfo = userServerInfo,
        modmailData = modmail,
        transcriptData = transcript,
        user = user
        

    )

    
@app.route("/api/openModmail/<id>")
@isMod
async def openModmailRoute(id):
    await ipc_client.request("openModmail", userID = int(id))
    return redirect(url_for("modDashboardUserRoute", id = id))


@app.route("/modDashboard/confessions")
@isMod
async def modDashboardConfs():
    allConfs = getAllConfessions()
    checkingConfs, waitingConfs, sentConfs, deletedConfs = [], [], [], []
    for conf in allConfs:
        if conf["status"] == "checking":
            checkingConfs.append(conf)
        elif conf["status"] == "waiting":
            waitingConfs.append(conf)
        elif conf["status"] == "sent":
            sentConfs.append(conf)
        elif conf["status"] == "removed":
            deletedConfs.append(conf)
        
    return await render_template("confessions.html", 
        checkingConfessions = checkingConfs, 
        waitingConfessions = waitingConfs,
        sentConfessions = sentConfs,
        removedConfessions = deletedConfs
        )

@app.route("/modDashboard/warns")
@isMod
async def modDashboardWarns():
    warns = getWarns()
    out = []
    for warn in warns:
        l = {
            "id": warn["_id"],
            "userID": warn["userID"],
            "user": await ipc_client.request("getUser", userID = warn["userID"]),
            "reason": warn["reason"],
            "warnedBy": await ipc_client.request("getUser", userID = warn["staffmember"]),
            "date": warn["timestamp"],
        }
        out.append(l)

    return await render_template("warns.html", warns = out)


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










app.run(debug=True, host="0.0.0.0", port=25567)
















    


        

        

      


    



        

      
    





   


        

