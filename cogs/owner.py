import discord
from discord.ext import commands

import os


class owner(commands.Cog, name="owner"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.command(hidden=True, brief="Python")
    @commands.is_owner()
    async def py(self, ctx):
        """Python"""
        code = ctx.message.content[4:]
        code = "    " + code.replace("\n", "\n    ")
        code = "async def __eval_function__():\n" + code

        additional = {}
        additional["self"] = self
        additional["ctx"] = ctx

        try:
            exec(code, {**globals(), **additional}, locals())

            await locals()["__eval_function__"]()
        except Exception as e:
            em = discord.Embed(description=str(e), colour=0xFFFFFE)
            try:
                await ctx.send(embed=em)
            except Exception:
                return

    @commands.command(name="say")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def say(self, ctx, *, message=None):
        """Let the bot send a message. You can attach a file too!"""
        files = []
        for file in ctx.message.attachments:
            files.append(await file.to_file())
        if message:
            await ctx.send(message, files=files)
        else:
            await ctx.send(files=files)
        await ctx.message.delete()

    @commands.command(hidden=True, brief="Shows all parts of the bot.")
    @commands.is_owner()
    async def cogs(self, ctx):
        """Shows all parts of the bot."""
        cogs = [x.replace(".py", "") for x in os.listdir("cogs") if ".py" in x]
        loaded = [
            "`{}`".format(c.__module__.split(".")[-1]) for c in self.bot.cogs.values()
        ]
        unloaded = [
            "`{}`".format(c.split(".")[-1])
            for c in cogs
            if "`{}`".format(c.split(".")[-1]) not in loaded
        ]
        total_cogs = len(cogs)
        embed = discord.Embed(title=f"Cogs ({total_cogs})", colour=0x000000)
        embed.add_field(
            name=f"✅ Geladen ({len(loaded)})",
            value=", ".join(loaded) if loaded != [] else "`None`",
            inline=False,
        )
        embed.add_field(
            name=f"⛔ Ontladen ({len(unloaded)})",
            value=", ".join(unloaded) if unloaded != [] else "`None`",
            inline=False,
        )
        try:
            await ctx.send(embed=embed)
        except Exception:
            return

    @commands.command(hidden=True, brief="Load a cog.")
    @commands.is_owner()
    async def load(self, ctx, *, module: str):
        """Load a cog."""
        modules = [x.replace(".py", "") for x in os.listdir("cogs") if ".py" in x]
        loaded_modules = [c.__module__.split(".")[-1] for c in self.bot.cogs.values()]
        if module.lower() == "all":
            failed_to_load = []
            msg_to_send = ""
            i = 0
            for m in modules:
                if m not in loaded_modules:
                    try:
                        self.bot.load_extension("cogs." + m)
                    except Exception:
                        i += 1
                        failed_to_load.append(m)
            if i == 0:
                em = discord.Embed(title="All Cogs Have Been Loaded", colour=0x000000)
                try:
                    await ctx.send(embed=em)
                except Exception:
                    return
            else:
                msg_to_send += "Successfully loaded **{}/{}** cogs.\n".format(
                    len(modules) - i, len(modules)
                )

            if failed_to_load:
                msg_to_send += "Failed to load ``{}``".format(", ".join(failed_to_load))

            if msg_to_send != "":
                try:
                    await ctx.send(msg_to_send)
                except Exception:
                    return
            return

        else:
            m = "cogs." + module
            try:
                if module in modules:
                    if module in loaded_modules:
                        em = discord.Embed(
                            title="Already Loaded",
                            description=f"`{module}`",
                            colour=0x000000,
                        )
                        try:
                            await ctx.send(embed=em)
                        except Exception:
                            return
                        return
                    self.bot.load_extension(m)
                    em = discord.Embed(
                        title="Loaded", description=f"`{module}`", colour=0x000000
                    )
                    try:
                        await ctx.send(embed=em)
                    except Exception:
                        return
                    return
                else:
                    em = discord.Embed(
                        title="Not Found", description=f"`{module}`", colour=0x000000
                    )
                    try:
                        await ctx.send(embed=em)
                    except Exception:
                        return
                    return
            except Exception as e:
                em = discord.Embed(title="Error", description=str(e), colour=0x000000)
                try:
                    await ctx.send(embed=em)
                except Exception:
                    return

    @commands.command(hidden=True, brief="Unloads a cog.")
    @commands.is_owner()
    async def unload(self, ctx, *, module: str):
        """Unloads a cog."""
        loaded_modules = [c.__module__.split(".")[-1] for c in self.bot.cogs.values()]
        modules = [x.replace(".py", "") for x in os.listdir("cogs") if ".py" in x]
        failed_to_load = []
        msg_to_send = ""
        if module.lower() == "all":
            i = 0
            for m in modules:
                if m == "owner":
                    pass
                else:
                    try:
                        self.bot.unload_extension("cogs." + m)
                    except Exception:
                        i += 1
                        failed_to_load.append(m)
            if i == 0:
                em = discord.Embed(title="All Cogs Have Been Unloaded", colour=0x000000)
                try:
                    await ctx.send(embed=em)
                except Exception:
                    return
            else:
                msg_to_send += "Successfully unloaded **{}/{}** cogs.\n".format(
                    len(modules) - i, len(modules)
                )

            if failed_to_load:
                msg_to_send += "``{}`` were already unloaded.".format(
                    ", ".join(failed_to_load)
                )

            if msg_to_send != "":
                try:
                    await ctx.send(msg_to_send)
                except Exception:
                    return
            return

        else:
            m = "cogs." + module
            try:
                if module in modules:
                    if module == "general":
                        em = discord.Embed(
                            title="Can't Unload",
                            description=f"`{module}`",
                            colour=0x000000,
                        )
                        try:
                            await ctx.send(embed=em)
                        except Exception:
                            return
                        return
                    if module not in loaded_modules:
                        em = discord.Embed(
                            title="Already Unloaded",
                            description=f"`{module}`",
                            colour=0x000000,
                        )
                        try:
                            await ctx.send(embed=em)
                        except Exception:
                            return
                        return
                    self.bot.unload_extension(m)
                    em = discord.Embed(
                        title="Unloaded", description=f"`{module}`", colour=0x000000
                    )
                    try:
                        await ctx.send(embed=em)
                    except Exception:
                        return
                    return
                else:
                    try:
                        self.bot.unload_extension(m)
                    except Exception:
                        em = discord.Embed(
                            title="Not Found",
                            description=f"`{module}`",
                            colour=0x000000,
                        )
                        try:
                            await ctx.send(embed=em)
                        except Exception:
                            return
                        return
                    em = discord.Embed(
                        title="Unloaded", description=f"`{module}`", colour=0x000000
                    )
                    try:
                        await ctx.send(embed=em)
                    except Exception:
                        return
                    return
            except Exception as e:
                em = discord.Embed(title="Error", description=str(e), colour=0x000000)
                try:
                    await ctx.send(embed=em)
                except Exception:
                    return

    @commands.command(hidden=True, brief="Reloads a cog.")
    @commands.is_owner()
    async def reload(self, ctx, *, module: str):
        """Reloads a cog."""
        modules = [x.replace(".py", "") for x in os.listdir("cogs") if ".py" in x]
        loaded_modules = [c.__module__.split(".")[-1] for c in self.bot.cogs.values()]
        failed_to_load = []
        msg_to_send = ""
        if module.lower() == "all":
            i = 0
            for m in modules:
                if m in loaded_modules:
                    try:
                        self.bot.unload_extension("cogs." + m)
                    except Exception:
                        pass
                try:
                    self.bot.load_extension("cogs." + m)
                except Exception:
                    i += 1
                    failed_to_load.append(module)
            if i == 0:
                em = discord.Embed(title="All Cogs Have Been Reloaded", colour=0x000000)
                try:
                    await ctx.send(embed=em)
                except Exception:
                    return
                return
            else:
                msg_to_send += "Successfully reloaded **{}/{}** cogs.\n".format(
                    len(modules) - i, len(modules)
                )

            if failed_to_load:
                msg_to_send += "Failed to reload ``{}``".format(
                    ", ".join(failed_to_load)
                )

            if msg_to_send != "":
                try:
                    await ctx.send(msg_to_send)
                except Exception:
                    return
            return

        else:
            m = "cogs." + module
            try:
                if module in modules:
                    if module in loaded_modules:
                        self.bot.unload_extension(m)
                        self.bot.load_extension(m)
                    else:
                        self.bot.load_extension(m)
                    em = discord.Embed(
                        title="Reloaded", description=f"`{module}`", colour=0x000000
                    )
                    try:
                        await ctx.send(embed=em)
                    except Exception:
                        return
                    return
                else:
                    em = discord.Embed(
                        title="Not Found", description=f"`{module}`", colour=0x000000
                    )
                    try:
                        await ctx.send(embed=em)
                    except Exception:
                        return
                    return
            except Exception as e:
                em = discord.Embed(title="Error", description=str(e), colour=0x000000)
                try:
                    await ctx.send(embed=em)
                except Exception:
                    return


def setup(bot):
    c = owner(bot)
    bot.add_cog(c)
