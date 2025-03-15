import discord
import json
from discord.ext import commands

# Laad reaction roles JSON
with open("reactionroles.json", "r", encoding="utf-8") as file:
    reactionroles = json.load(file)


class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        message_id = str(payload.message_id)
        emoji = str(payload.emoji)
        role_id = get_role_id(emoji, message_id)

        if role_id:
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            role = guild.get_role(int(role_id))
            if member and role:
                await member.add_roles(role)
                channel = guild.get_channel(payload.channel_id)
                message = await channel.fetch_message(message_id)
                await message.remove_reaction(payload.emoji, member)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        message_id = str(payload.message_id)
        emoji = str(payload.emoji)
        role_id = get_role_id(emoji, message_id)

        if role_id:
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            role = guild.get_role(int(role_id))
            if member and role:
                await member.remove_roles(role)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def createRR(
        self,
        ctx,
        channel: discord.TextChannel,
        message_id: int,
        role: discord.Role,
        emoji,
    ):
        msg = await channel.fetch_message(message_id)
        await msg.add_reaction(emoji)

        if str(message_id) not in reactionroles:
            reactionroles[str(message_id)] = {}

        reactionroles[str(message_id)][str(emoji)] = role.id
        with open("reactionroles.json", "w", encoding="utf-8") as file:
            json.dump(reactionroles, file, indent=4)

        await ctx.send(f"✅ {emoji} is nu gekoppeld aan de rol {role.name}!")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def show_roles(self, ctx):
        embed = discord.Embed(title="🎭 Reaction Roles", color=0x0076C5)
        for message_id, reactions in reactionroles.items():
            embed.add_field(
                name=f"🔹 Message ID: {message_id}",
                value="\n".join(
                    [f"{emoji} → <@&{role_id}>" for emoji, role_id in reactions.items()]
                ),
                inline=False,
            )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))


def get_role_id(emoji, message_id):
    return reactionroles.get(str(message_id), {}).get(str(emoji))
