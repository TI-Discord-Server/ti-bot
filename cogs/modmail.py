import asyncio
import re
from datetime import datetime, timezone
from itertools import zip_longest
from typing import Optional, Union, List, Tuple, Literal


import discord
from discord.ext import commands

from utils.thread import Thread
from utils.time import UserFriendlyTime, human_timedelta
from utils.utils import *
from utils.has_role import has_role
from utils import checks


class Modmail(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def send_scheduled_close_message(self, ctx, after, silent=False):
        human_delta = human_timedelta(after.dt)

        embed = discord.Embed(
            title="Scheduled close",
            description=f"This thread will{' silently' if silent else ''} close in {human_delta}.",
            color=discord.Color.red(),
        )

        if after.arg and not silent:
            embed.add_field(name="Message", value=after.arg)

        embed.set_footer(text="Closing will be cancelled if a thread message is sent.")
        embed.timestamp = after.dt

        await ctx.send(embed=embed)

    @commands.command(usage="[after] [close message]")
    @has_role("Moderator")
    @checks.thread_only()
    async def close(
            self,
            ctx,
            option: Optional[Literal["silent", "silently", "cancel"]] = "",
            *,
            after: UserFriendlyTime = None,
    ):
        """
        Close the current thread.

        Close after a period of time:
        - `{prefix}close in 5 hours`
        - `{prefix}close 2m30s`

        Custom close messages:
        - `{prefix}close 2 hours The issue has been resolved.`
        - `{prefix}close We will contact you once we find out more.`

        Silently close a thread (no message)
        - `{prefix}close silently`
        - `{prefix}close silently in 10m`

        Stop a thread from closing:
        - `{prefix}close cancel`
        """

        thread = ctx.thread

        close_after = (after.dt - after.now).total_seconds() if after else 0
        silent = any(x == option for x in {"silent", "silently"})
        cancel = option == "cancel"

        if cancel:
            if thread.close_task is not None or thread.auto_close_task is not None:
                await thread.cancel_closure(all=True)
                embed = discord.Embed(
                    color=discord.Color.red(), description="Scheduled close has been cancelled."
                )
            else:
                embed = discord.Embed(
                    color=discord.Color.red(),
                    description="This thread has not already been scheduled to close.",
                )

            return await ctx.send(embed=embed)

        message = after.arg if after else None

        if after and after.dt > after.now:
            await self.send_scheduled_close_message(ctx, after, silent)

        await thread.close(closer=ctx.author, after=close_after, message=message, silent=silent)

    @staticmethod
    def parse_user_or_role(ctx, user_or_role):
        mention = None
        if user_or_role is None:
            mention = ctx.author.mention
        elif hasattr(user_or_role, "mention"):
            mention = user_or_role.mention
        elif user_or_role in {"here", "everyone", "@here", "@everyone"}:
            mention = "@" + user_or_role.lstrip("@")
        return mention

    @commands.command()
    @has_role("Moderator")
    @checks.thread_only()
    async def nsfw(self, ctx):
        """Flags a Modmail thread as NSFW (not safe for work)."""
        await ctx.channel.edit(nsfw=True)
        await self.bot.add_reaction(ctx.message, "\N{WHITE HEAVY CHECK MARK}")

    @commands.command()
    @has_role("Moderator")
    @checks.thread_only()
    async def sfw(self, ctx):
        """Flags a Modmail thread as SFW (safe for work)."""
        await ctx.channel.edit(nsfw=False)
        await self.bot.add_reaction(ctx.message, "\N{WHITE HEAVY CHECK MARK}")

    @commands.command()
    @has_role("Moderator")
    @checks.thread_only()
    async def reply(self, ctx, *, msg: str = ""):
        """
        Reply to a Modmail thread.

        Supports attachments and images as well as
        automatically embedding image URLs.
        """

        ctx.message.content = msg

        async with ctx.typing():
            await ctx.thread.reply(ctx.message)

    @commands.command(aliases=["anonreply", "anonymousreply"])
    @has_role("Moderator")
    @checks.thread_only()
    async def areply(self, ctx, *, msg: str = ""):
        """
        Reply to a thread anonymously.

        You can edit the anonymous user's name,
        avatar and tag using the config command.

        Edit the `anon_username`, `anon_avatar_url`
        and `anon_tag` config variables to do so.
        """
        ctx.message.content = msg
        async with ctx.typing():
            await ctx.thread.reply(ctx.message, anonymous=True)

    @commands.group(invoke_without_command=True)
    @has_role("Moderator")
    @checks.thread_only()
    async def note(self, ctx, *, msg: str = ""):
        """
        Take a note about the current thread.

        Useful for noting context.
        """
        ctx.message.content = msg
        async with ctx.typing():
            msg = await ctx.thread.note(ctx.message)
            await msg.pin()

    @commands.command()
    @has_role("Moderator")
    @checks.thread_only()
    async def edit(self, ctx, message_id: Optional[int] = None, *, message: str):
        """
        Edit a message that was sent using the reply or anonreply command.

        If no `message_id` is provided,
        the last message sent by a staff will be edited.

        Note: attachments **cannot** be edited.
        """
        thread = ctx.thread

        try:
            await thread.edit_message(message_id, message)
        except ValueError:
            return await ctx.send(
                embed=discord.Embed(
                    title="Failed",
                    description="Cannot find a message to edit. Plain messages are not supported.",
                    color=discord.Color.red(),
                )
            )

        await self.bot.add_reaction(ctx.message, "\N{WHITE HEAVY CHECK MARK}")

    @commands.command(usage="<user> [category] [options]")
    @has_role("Moderator")
    async def contact(
            self,
            ctx,
            users: commands.Greedy[
                Union[Literal["silent", "silently"], discord.Member, discord.User, discord.Role]
            ],
            *,
            category: None,
            manual_trigger=True,
    ):
        """
        Create a thread with a specified member.

        If `category` is specified, the thread
        will be created in that specified category.

        `category`, if specified, may be a category ID, mention, or name.
        `users` may be a user ID, mention, or name. If multiple users are specified, a group thread will start.
        A maximum of 5 users are allowed.
        `options` can be `silent` or `silently`.
        """
        silent = any(x in users for x in ("silent", "silently"))
        if silent:
            try:
                users.remove("silent")
            except ValueError:
                pass

            try:
                users.remove("silently")
            except ValueError:
                pass

        if isinstance(category, str):
                category = None

        errors = []
        for u in list(users):
            if isinstance(u, discord.Role):
                users += u.members
                users.remove(u)

        for u in list(users):
            exists = await self.bot.threads.find(recipient=u)
            if exists:
                errors.append(f"A thread for {u} already exists.")
                if exists.channel:
                    errors[-1] += f" in {exists.channel.mention}"
                errors[-1] += "."
                users.remove(u)
            elif u.bot:
                errors.append(f"{u} is a bot, cannot add to thread.")
                users.remove(u)

        if len(users) > 5:
            errors.append("Group conversations only support 5 users.")
            users = []

        if errors or not users:
            if not users:
                # no users left
                title = "Thread not created"
            else:
                title = None

            if manual_trigger:  # not react to contact
                embed = discord.Embed(title=title, color=discord.Color.red(), description="\n".join(errors))
                await ctx.send(embed=embed, delete_after=10)

            if not users:
                # end
                return

        creator = ctx.author if manual_trigger else users[0]

        thread = await self.bot.threads.create(
            recipient=users[0],
            creator=creator,
            category=category,
            manual_trigger=manual_trigger,
        )

        if thread.cancelled:
            return

        if not silent:
            if creator.id == users[0].id:
                description = "\"You have opened a Modmail thread.\""
            else:
                description = "\"Staff have opened a Modmail thread.\""

            em = discord.Embed(
                title="\"New Thread\"",
                description=description,
                color=discord.Color.blurple(),
            )

            em.timestamp = discord.utils.utcnow()
            em.set_footer(text=f"{creator}", icon_url=creator.display_avatar.url)

            for u in users:
                await u.send(embed=em)

        embed = discord.Embed(
            title="Created Thread",
            description=f"Thread started by {creator.mention} for {', '.join(u.mention for u in users)}.",
            color=discord.Color.blurple(),
        )
        await thread.wait_until_ready()

        if users[1:]:
            await thread.add_users(users[1:])

        await thread.channel.send(embed=embed)

        if manual_trigger:
            await self.bot.add_reaction(ctx.message, "\N{WHITE HEAVY CHECK MARK}")
            await asyncio.sleep(5)
            await ctx.message.delete()

    @commands.command()
    @has_role("Moderator")
    @checks.thread_only()
    async def delete(self, ctx, message_id: int = None):
        """
        Delete a message that was sent using the reply command or a note.

        Deletes the previous message, unless a message ID is provided,
        which in that case, deletes the message with that message ID.

        Notes can only be deleted when a note ID is provided.
        """
        thread = ctx.thread

        try:
            await thread.delete_message(message_id, note=True)
        except ValueError as e:
            self.bot.log.warning("Failed to delete message: %s.", e)
            return await ctx.send(
                embed=discord.Embed(
                    title="Failed",
                    description="Cannot find a message to delete. Plain messages are not supported.",
                    color=discord.Color.red(),
                )
            )

        await self.bot.add_reaction(ctx.message, "\N{WHITE HEAVY CHECK MARK}")




async def setup(bot):
    await bot.add_cog(Modmail(bot))