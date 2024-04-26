import discord, requests
from discord.ext import commands


key = "84f89b9d-6691-5016-72ad-a41319f3adde:fx"

class Translation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def translate(self, ctx, lang, *, text):
        data = {
            "text": text,
            "target_lang": lang
        }
        req = requests.post(f"https://api-free.deepl.com/v2/translate?auth_key={key}", data=data)
        if req.status_code == 200:
            em = discord.Embed(title="Translation", color=0x00aa99)
            em.add_field(name="⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼", value="**Input**", inline=False)
            em.add_field(name="Text", value=text)
            em.add_field(name="Language", value=req.json()["translations"][0]["detected_source_language"])

            em.add_field(name="⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼", value="**Translation**", inline=False)
            em.add_field(name="Text", value=req.json()["translations"][0]["text"])
            em.add_field(name="Language", value=lang)

            stats = requests.post(f"https://api-free.deepl.com/v2/usage?auth_key={key}")
            stats = stats.json()

            em.set_footer(text=f"{stats['character_count']}/{stats['character_limit']} tekens over deze maand")

            await ctx.send(embed=em)
        else:
            await ctx.send(req.json()["message"])


async def setup(bot):
    await bot.add_cog(Translation(bot))