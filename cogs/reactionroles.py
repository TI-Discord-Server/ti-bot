import discord, json
from discord.ext import commands

reactionroles = json.load(open("reactionroles.json", "r+"))

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        messageID = payload.message_id
        emoji = payload.emoji

        roleID = get_roleID(emoji, messageID)
        if roleID != None:
            userID = payload.user_id

            guild = discord.utils.get(self.bot.guilds, id=payload.guild_id)
            member = await guild.fetch_member(userID)
            role = guild.get_role(int(roleID))

            await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        messageID = payload.message_id
        emoji = payload.emoji

        roleID = get_roleID(emoji, messageID)
        if roleID != None:
            userID = payload.user_id

            guild = discord.utils.get(self.bot.guilds, id=payload.guild_id)
            member = await guild.fetch_member(userID)
            role = guild.get_role(int(roleID))

            await member.remove_roles(role)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def createRR(self, ctx, channel: discord.TextChannel, messageID, role: discord.Role, emoji):
        msg = await channel.fetch_message(messageID)
        await msg.add_reaction(emoji)

        

        if not str(messageID) in reactionroles:
            reactionroles[str(messageID)] = {}

        reactionroles[str(messageID)][str(emoji)] = role.id

        json.dump(reactionroles, open("reactionroles.json", "w"), indent=4)

        
        await ctx.send("Done! %s will now give the %s role" % (emoji, role))

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))

def get_roleID(emoji, messageID):
    out = None
    if str(messageID) in reactionroles:
        if str(emoji) in reactionroles[str(messageID)]:
            out = reactionroles[str(messageID)][str(emoji)]
    else:
        out = None

    if out != None:
        return out
    else: 
        return None