
import json
import string
from pymongo import MongoClient
from datetime import datetime, timedelta
import random, hashlib, bson

from motor import motor_asyncio


client = motor_asyncio.AsyncIOMotorClient("mongodb+srv://discbot:sAvfMDDiIrVL7kAM@db.nnij3ks.mongodb.net/")

db = client["TIBot"]

emailData = db["emailData"]
userCodes = db["userCodes"]
confessions = db["confessions"]
warnData = db["warnData"]
modmailData = db["modmailData"]
transcriptData = db["transcriptData"]


# ----------------------
# EMAIL
# ----------------------

async def getLinkedEmailHash(userID):
    user = await emailData.find_one({"_id": userID})
    return user["emailHash"] if user else None

async def storeUserEmail(userID, emailHash):
    try:
        await emailData.insert_one({"_id": userID, "emailHash": emailHash})
    except:
        await emailData.update_one({"_id": userID}, {"$set": {"emailHash": emailHash}})

async def genUserCode(userID, mailHash):
    code = random.randint(100000, 999999)
    if await getUserCode(userID):
        await userCodes.update_one({"_id": userID}, {"$set": {"code": code, "mailHash": mailHash}})
    else:
        await userCodes.insert_one({"_id": userID, "code": code, "mailHash": mailHash})
    return code

async def getUserCode(userID):
    user = await userCodes.find_one({"_id": userID})
    return user["code"] if user else None

async def getUserCodeHash(userID):
    user = await userCodes.find_one({"_id": userID})
    return user["mailHash"] if user else None

async def checkIfAlreadyUsed(mail, userID):
    data = await emailData.find_one({"emailHash": createHash(mail)})
    if data:
        if data["_id"] == userID:
            return False
    return True if data else False 

async def getLinkedUser(mailHash):
    data = await emailData.find_one({"emailHash": mailHash})
    return data

async def getVerifiedUsers():
    alls = []
    for d in await emailData.find().to_list(length=None):
        alls.append(d)
    return alls

def createHash(mail):
    return hashlib.sha256(mail.encode()).hexdigest()

# ----------------------
# CONFESSIONS BOT
# ----------------------

async def getNewConfession():
    if await getQueueLength() > 0:
        queue = await getQueue()
        confession = random.choice(list(queue))
        if confession:
            await confessions.update_one({"_id": confession["_id"]}, {"$set": {"status": "checking"}})
            return confession
    return None
    
async def insertConfession(confession):
    id = random.randint(100000000000000000, 999999999999999999)
    await confessions.insert_one({"_id": id, "confession": confession, "status": "waiting", "messageID": None})

async def assignmessageID(confessionID, messageID):
    await confessions.update_one({"_id": confessionID}, {"$set": {"messageID": messageID}})

async def getQueue():
    return await confessions.find({"status": "waiting"}).to_list(length=None)

async def getCheckingConfession():
    conf= await confessions.find_one({"status": "checking"})
    return conf if conf else None

async def setStatus(confessionID, status):
    await confessions.update_one({"_id": confessionID}, {"$set": {"status": status}})

async def GetSentCount():
    return await confessions.count_documents({"status": "sent"})

async def getQueueLength():
    return await confessions.count_documents({"status": "waiting"})

async def getConfession(confessionID):
    return await confessions.find_one({"_id": confessionID})

# ----------------------
# SITE DATA
# ----------------------
async def getCheckingConfessions():
    out = []
    for d in confessions.find({"status": "checking"}):
        out.append(d)
    return out

async def getAllConfessions():
    out = []
    for d in await confessions.find().to_list(length=None):
        out.append(d)
    return out

async def deleteConfession(id):
    await confessions.update_one({"_id": id}, {"$set": {"status": "removed"}})

async def restoreConfession(id):
    await confessions.update_one({"_id": id}, {"$set": {"status": "waiting"}})

async def getWarns(userID = None):
    data = None
    if userID:
        data = await warnData.find({"userID": userID})
    else:
        data = await warnData.find()

    out = []
    for d in data:
        out.append(d)
    return out

async def getUserServerInfo(userID):

    return {
        "warns": await getWarnings(userID)
    }

    

# ----------------------
# WARNS
# ----------------------

async def insertWarning(userID, reason, staffmember):
    id = random_string_generator(10)
    await warnData.insert_one({"_id": id,"userID": userID, "reason": reason, "timestamp": datetime.now(), "staffmember": staffmember})

async def getWarnings(userID):
    out = []
    for d in await warnData.find({"userID": userID}).to_list(length=None):
        out.append(d)
    return out

async def deleteWarning(warnID):
    if warnData.find_one({"_id": warnID}):
        return await warnData.find_one_and_delete({"_id": warnID})
    return False


# ----------------------
# MODMAIL FUNCTIONS
# ----------------------

async def insertModmail(userID, channelID, channelLink):
    await modmailData.insert_one({"_id": channelID, "userID": userID, "timestamp": datetime.now(), "link": channelLink})

async def linkTranscript(channelID, userID):
    await modmailData.delete_one({"_id": int(channelID)})
    await transcriptData.insert_one({"_id": int(channelID), "userID": userID})

async def getTranscripts(ID):
    data = await transcriptData.find({"userID": ID}).to_list(length=None)
    out = []
    for d in data:
        out.append(d)
    return out if out != [] else None

async def getModmail(ID):
    data = await modmailData.find_one({"_id": ID})
    if not data:
        data = await modmailData.find_one({"userID": ID})
    return data



# ----------------------
# RANDOM FUNCTIONS
# ----------------------


def random_string_generator(str_size):
    return ''.join(random.choice(string.ascii_letters) for x in range(str_size))

