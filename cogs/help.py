import discord
from discord.ext import commands, tasks

import random


class help(commands.Cog, name="help"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.bot.remove_command("help")  # Removes the built-in help command
        self.change_status.start()

    @tasks.loop(minutes=10)
    async def change_status(self):
        print("Changing status...")
        choice = random.choice(
            [
                "Python is en slang",
                "Java is en eiland",
                "Java is en Minecraft versie",
                "Rust is oranje stof op metaal",
                "Ruby is en steen",
                "C# is een muzieksleutel",
                "Swift is een vogel",
                "Perl is een sieraad",
                "Go is een bordspel",
                "Kotlin is een eiland",
                "Elixir is een magisch drankje",
            ]
        )
        await self.bot.change_presence(
            activity=discord.CustomActivity(name=choice), status=discord.Status.online
        )

    @change_status.before_loop
    async def before_change_status(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.change_status.cancel()


async def setup(bot):
    n = help(bot)
    await bot.add_cog(n)
