import discord
import json
from discord.ext import commands

# Laad reaction roles JSON
with open("reactionroles.json", "r", encoding="utf-8") as file:
    reactionroles = json.load(file)


class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rr_message_id = None  # Hier wordt het ID van het bericht opgeslagen

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if self.rr_message_id and payload.message_id == self.rr_message_id:
            emoji = str(payload.emoji)
            role_id = reactionroles.get(emoji)

            if role_id:
                guild = self.bot.get_guild(payload.guild_id)
                member = await guild.fetch_member(payload.user_id)
                role = guild.get_role(int(role_id))
                if member and role:
                    await member.add_roles(role)
                    channel = guild.get_channel(payload.channel_id)
                    message = await channel.fetch_message(payload.message_id)
                    await message.remove_reaction(payload.emoji, member)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if self.rr_message_id and payload.message_id == self.rr_message_id:
            emoji = str(payload.emoji)
            role_id = reactionroles.get(emoji)

            if role_id:
                guild = self.bot.get_guild(payload.guild_id)
                member = await guild.fetch_member(payload.user_id)
                role = guild.get_role(int(role_id))
                if member and role:
                    await member.remove_roles(role)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def createRR(self, ctx, channel: discord.TextChannel):
        embed = discord.Embed(title="🎭 Kies je rollen!", color=0x0076C5)
        description = (
            "React met de juiste emoji om een rol te krijgen of te verwijderen."
        )

        for emoji, role_id in reactionroles.items():
            role = ctx.guild.get_role(role_id)
            if role:
                description += f"\n{emoji} → {role.mention}"

        embed.description = description
        message = await channel.send(embed=embed)
        self.rr_message_id = message.id  # Sla het message ID op

        for emoji in reactionroles.keys():
            await message.add_reaction(emoji)

        await ctx.send("✅ Reaction Role bericht aangemaakt!")


async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
