import asyncio
import os
import sys

from discord.ext import commands

from utils.checks import developer  # jouw eigen check-decorator


class AdminCommands(commands.Cog, name="AdminCommands"):
    """Admin-only prefix commands zoals sync en restart."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sync", help="Synchroniseer de slash commands met Discord.")
    @commands.guild_only()
    @developer()
    async def sync(self, ctx: commands.Context):
        """Sync alle (slash) app-commands. Uit te voeren via prefix (bijv. !sync)."""
        msg = await ctx.send("🔄 Bezig met synchroniseren…")
        try:
            synced = await self.bot.tree.sync()  # global sync
            await msg.edit(content=f"✅ Gesynchroniseerd: {len(synced)} commando's.")
            self.bot.log.info(
                f"!sync uitgevoerd door {ctx.author} in {ctx.guild} - {len(synced)} commands gesynchroniseerd."
            )
        except Exception as e:
            self.bot.log.error(f"Sync mislukt: {e}", exc_info=True)
            await msg.edit(content=f"❌ Sync mislukt: {e}")

    @commands.command(name="restart", help="Herstart de bot.")
    @commands.guild_only()
    @developer()
    async def restart(self, ctx: commands.Context):
        """Herstart de bot-proces (werkt best onder een procesmanager zoals systemd/Docker)."""
        await ctx.send("♻️ Bot wordt herstart…")
        self.bot.log.info(
            f"!restart uitgevoerd door {ctx.author} in {ctx.guild} - bot gaat herstarten."
        )
        await asyncio.sleep(2)  # laat het bericht even zichtbaar zijn
        # Start hetzelfde Python-proces opnieuw met dezelfde argv
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @commands.command(name="shutdown", help="Zet de bot uit.")
    @commands.guild_only()
    @developer()
    async def shutdown(self, ctx: commands.Context):
        """Sluit de bot netjes af."""
        await ctx.send("⏹️ Bot wordt afgesloten…")
        self.bot.log.info(
            f"!shutdown uitgevoerd door {ctx.author} in {ctx.guild} - bot gaat afsluiten."
        )
        await asyncio.sleep(2)
        await self.bot.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCommands(bot))
