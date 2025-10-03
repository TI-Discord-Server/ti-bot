# Don't remove unused imports as they can be used in the py command.

import os

import discord
from discord import app_commands
from discord.ext import commands

from main import Bot
from utils.checks import developer


class owner(commands.Cog, name="owner"):
    def __init__(self, bot: "Bot") -> None:
        super().__init__()
        self.bot: "Bot" = bot

    @app_commands.command(hidden=True, brief="Executes code.")
    @developer()
    async def py(self, ctx: commands.Context[commands.AutoShardedBot]) -> None:
        """Executes code."""
        code = ctx.message.content[4:]
        code = "    " + code.replace("\n", "\n    ")
        code = "async def __eval_function__():\n" + code

        additional = {}
        additional["self"] = self
        additional["ctx"] = ctx
        additional["channel"] = ctx.channel
        additional["author"] = ctx.author
        additional["server"] = ctx.guild

        try:
            exec(code, {**globals(), **additional}, locals())

            await locals()["__eval_function__"]()
        except Exception as e:
            em = discord.Embed(description=str(e), color=0xFFFFFE)
            try:
                await ctx.send(embed=em)
            except Exception:
                return

    @app_commands.command(hidden=True, brief="Shows all parts of the bot.")
    @developer()
    async def cogs(self, ctx: commands.Context[commands.AutoShardedBot]) -> None:
        """Shows all parts of the bot."""
        cogs = [x.replace(".py", "") for x in os.listdir("cogs") if ".py" in x]
        loaded = ["`{}`".format(c.__module__.split(".")[-1]) for c in self.bot.cogs.values()]
        unloaded = [
            "`{}`".format(c.split(".")[-1])
            for c in cogs
            if "`{}`".format(c.split(".")[-1]) not in loaded
        ]
        total_cogs = len(cogs)
        embed = discord.Embed(title=f"TI dashboard | Cogs ({total_cogs})", color=self.bot.color)
        embed.add_field(
            name=f"✅ **Loaded** ({len(loaded)})",
            value=", ".join(loaded) if loaded != [] else "`None`",
            inline=False,
        )
        embed.add_field(
            name=f"⛔ **Unloaded** ({len(unloaded)})",
            value=", ".join(unloaded) if unloaded != [] else "`None`",
            inline=False,
        )
        try:
            await ctx.send(embed=embed)
        except Exception:
            return

    @app_commands.command(hidden=True, brief="Load a cog.")
    @developer()
    async def load(self, ctx: commands.Context[commands.AutoShardedBot], *, module: str) -> None:
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
                        await self.bot.load_extension("cogs." + m)
                    except Exception:
                        i += 1
                        failed_to_load.append(m)
            if i == 0:
                em = discord.Embed(title="All Cogs Have Been Loaded", color=self.bot.color)
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
                            color=self.bot.color,
                        )
                        try:
                            await ctx.send(embed=em)
                        except Exception:
                            return
                        return
                    await self.bot.load_extension(m)
                    em = discord.Embed(
                        title="Loaded", description=f"`{module}`", color=self.bot.color
                    )
                    try:
                        await ctx.send(embed=em)
                    except Exception:
                        return
                    return
                else:
                    em = discord.Embed(
                        title="Not Found",
                        description=f"`{module}`",
                        color=self.bot.color,
                    )
                    try:
                        await ctx.send(embed=em)
                    except Exception:
                        return
                    return
            except Exception as e:
                em = discord.Embed(title="Error", description=str(e), color=self.bot.color)
                try:
                    await ctx.send(embed=em)
                except Exception:
                    return

    @app_commands.command(hidden=True, brief="Unloads a cog.")
    @developer()
    async def unload(self, ctx: commands.Context[commands.AutoShardedBot], *, module: str) -> None:
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
                        await self.bot.unload_extension("cogs." + m)
                    except Exception:
                        i += 1
                        failed_to_load.append(m)
            if i == 0:
                em = discord.Embed(title="All Cogs Have Been Unloaded", color=self.bot.color)
                try:
                    await ctx.send(embed=em)
                except Exception:
                    return
            else:
                msg_to_send += "Successfully unloaded **{}/{}** cogs.\n".format(
                    len(modules) - i, len(modules)
                )

            if failed_to_load:
                msg_to_send += "``{}`` were already unloaded.".format(", ".join(failed_to_load))

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
                            color=self.bot.color,
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
                            color=self.bot.color,
                        )
                        try:
                            await ctx.send(embed=em)
                        except Exception:
                            return
                        return
                    await self.bot.unload_extension(m)
                    em = discord.Embed(
                        title="Unloaded",
                        description=f"`{module}`",
                        color=self.bot.color,
                    )
                    try:
                        await ctx.send(embed=em)
                    except Exception:
                        return
                    return
                else:
                    try:
                        await self.bot.unload_extension(m)
                    except Exception:
                        em = discord.Embed(
                            title="Not Found",
                            description=f"`{module}`",
                            color=self.bot.color,
                        )
                        try:
                            await ctx.send(embed=em)
                        except Exception:
                            return
                        return
                    em = discord.Embed(
                        title="Unloaded",
                        description=f"`{module}`",
                        color=self.bot.color,
                    )
                    try:
                        await ctx.send(embed=em)
                    except Exception:
                        return
                    return
            except Exception as e:
                em = discord.Embed(title="Error", description=str(e), color=self.bot.color)
                try:
                    await ctx.send(embed=em)
                except Exception:
                    return

    @app_commands.command(hidden=True, brief="Reloads a cog.")
    @developer()
    async def reload(self, ctx: commands.Context[commands.AutoShardedBot], *, module: str) -> None:
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
                        await self.bot.unload_extension("cogs." + m)
                    except Exception:
                        pass
                try:
                    await self.bot.load_extension("cogs." + m)
                except Exception:
                    i += 1
                    failed_to_load.append(module)
            if i == 0:
                em = discord.Embed(title="All Cogs Have Been Reloaded", color=self.bot.color)
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
                msg_to_send += "Failed to reload ``{}``".format(", ".join(failed_to_load))

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
                        await self.bot.reload_extension(m)
                    else:
                        await self.bot.load_extension(m)
                    em = discord.Embed(
                        title="Reloaded",
                        description=f"`{module}`",
                        color=self.bot.color,
                    )
                    try:
                        await ctx.send(embed=em)
                    except Exception:
                        return
                    return
                else:
                    em = discord.Embed(
                        title="Not Found",
                        description=f"`{module}`",
                        color=self.bot.color,
                    )
                    try:
                        await ctx.send(embed=em)
                    except Exception:
                        return
                    return
            except Exception as e:
                em = discord.Embed(title="Error", description=str(e), color=self.bot.color)
                try:
                    await ctx.send(embed=em)
                except Exception:
                    return


async def setup(bot):
    c = owner(bot)
    await bot.add_cog(c)
