import discord
import json
import asyncio
from discord.ext import commands

# Laad reaction roles JSON
with open("reactionroles.json", "r", encoding="utf-8") as file:
    reactionroles = json.load(file)

# Groepeer rollen voor een overzichtelijkere embed
role_groups = {
    "Campussen": [
        775716812465373212,
        775714536459730944,
        893431633527595038,
        776164204537315378,
    ],
    "Studiejaren": [775720596498677812, 775724094166532117, 775724122147127327],
    "Studentenrollen": [
        776164549808226345,
        1325394574067236864,
        818440725989556235,
        891324061697835048,
    ],
    "Fun Rollen": [771401922841411624, 773957739922718720, 778298504606646312],
    "Updates": [860169723425194015],
}


class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rr_message_id = None  # Hier wordt het ID van het bericht opgeslagen

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if self.rr_message_id and payload.message_id == self.rr_message_id:
            if payload.user_id == self.bot.user.id:
                return  # Voorkomt dat de bot zijn eigen reacties verwijdert

            emoji = str(payload.emoji)
            role_id = reactionroles.get(emoji)

            if role_id:
                guild = self.bot.get_guild(payload.guild_id)
                member = await guild.fetch_member(payload.user_id)
                role = guild.get_role(int(role_id))
                if member and role:
                    if role in member.roles:
                        await member.remove_roles(
                            role
                        )  # Verwijder rol als gebruiker deze al heeft
                    else:
                        await member.add_roles(
                            role
                        )  # Voeg rol toe als gebruiker deze nog niet heeft

                    channel = guild.get_channel(payload.channel_id)
                    message = await channel.fetch_message(payload.message_id)
                    await message.remove_reaction(
                        payload.emoji, member
                    )  # Verwijder de reactie van de gebruiker

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def createRR(self, ctx, channel: discord.TextChannel):
        embed = discord.Embed(title="🎭 Kies je rollen!", color=0x0076C5)
        embed.description = (
            "React met de juiste emoji om een rol te krijgen of te verwijderen."
        )

        for category, roles in role_groups.items():
            group_text = ""
            for emoji, role_id in reactionroles.items():
                if role_id in roles:
                    role = ctx.guild.get_role(role_id)
                    if role:
                        group_text += f"\n{emoji} → {role.mention}"
            if group_text:
                embed.add_field(name=category, value=group_text, inline=False)

        message = await channel.send(embed=embed)
        self.rr_message_id = message.id  # Sla het message ID op

        for emoji in reactionroles.keys():
            try:
                await message.add_reaction(emoji)
                await asyncio.sleep(0.5)  # Prevent rate limits
            except discord.HTTPException:
                print(f"⚠️ Failed to add reaction: {emoji}")

        await ctx.send("✅ Reaction Role bericht aangemaakt!")


async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
