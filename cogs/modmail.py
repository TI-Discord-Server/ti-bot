import asyncio
from datetime import datetime
import discord
from discord.ext import commands

from funcs import insertModmail, linkTranscript

class Modmail(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        await self.bot.change_presence(activity=discord.Game(name="DM mij om ons te contacteren!"))

    # @Server.route()
    # async def openModmail(self, data):
    #     guild = self.bot.get_guild(771394209419624489)
    #     member = guild.get_member(data["userID"])
    #     category = discord.utils.get(guild.categories, name='━━━ 📫 ModMail ━━━')
    #     if category is None:
    #         category = await guild.create_category(name='━━━ 📫 ModMail ━━━')
    #     channel = await guild.create_text_channel(name=str(member), category=category, overwrites=category.overwrites, topic=str(member.id))
    #     insertModmail(member.id, channel.id, channel.jump_url)
    #     await channel.send("Geopend via dashboard")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild != None:
            return
        guild = self.bot.get_guild(771394209419624489)
        if message.channel.type == discord.ChannelType.private:
            channel = discord.utils.get(guild.text_channels, topic=str(message.author.id))
            if channel is None:
                category = discord.utils.get(guild.categories, name='━━━ 📫 ModMail ━━━')
                if category is None:
                    category = await guild.create_category(name='━━━ 📫 ModMail ━━━')
                msg = await message.author.send("Wens je de modmail te starten?")
                await msg.add_reaction("✅")
                await msg.add_reaction("❌")
                def check(reaction, user):
                    return user == message.author and str(reaction.emoji) in ["✅", "❌"]

                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                    if reaction.emoji == "❌":
                        await message.author.send("Oké, ik heb je verzoek geanulleerd!")
                        return
                    else:
                        await msg.delete()
                        emb = discord.Embed(title="Kanaal Geopend", description="Het team zal jou zo snel mogelijk helpen!", color=0x00ff00)
                        emb.timestamp = datetime.now()
                        await message.author.send(embed=emb)
                    channel = await guild.create_text_channel(name=str(message.author), category=category, overwrites=category.overwrites, topic=str(message.author.id))
                    await insertModmail(message.author.id, channel.id, channel.jump_url)

                except asyncio.TimeoutError:
                    await message.author.send("Je verzoek is verlopen, indien je het team wenst te contacteren gelieve nogmaals te sturen!")
                    return


            em = discord.Embed(color=discord.Colour.blurple())
            em.add_field(name="Bericht", value=message.content)
            em.set_author(name=f'{message.author}', icon_url=message.author.display_avatar)
            em.timestamp = datetime.now()
            em.set_footer(text=f"Message ID: {message.id}")
            if message.attachments:
                for attachment in message.attachments:
                    em.set_image(url=attachment.url)
                    if message.content == "":
                        em.clear_fields()
                        em.add_field(name="Bericht", value=f"[Bijlage]({attachment.url})")
            await channel.send(embed=em)
            await message.add_reaction('✅')
        await self.bot.process_commands(message)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def startchat(self, ctx: commands.Context, member: discord.Member):
        guild = self.bot.get_guild(771394209419624489)
        channel = discord.utils.get(guild.text_channels, topic=str(member.id))
        if channel is None:
            category = discord.utils.get(guild.categories, name='━━━ 📫 ModMail ━━━')
            if category is None:
                category = await guild.create_category(name='━━━ 📫 ModMail ━━━')
            channel = await guild.create_text_channel(name=str(member), category=category, overwrites=category.overwrites, topic=str(member.id))
        await ctx.send(f"Kanaal geopend: {channel.mention}")
        await insertModmail(member.id, channel.id, channel.jump_url)

    async def createTranscript(self, channel: discord.TextChannel):
        confMsg = await channel.send("Generating Transcript...")
        id = channel.id
        file = open(f"transcripts/{str(id)}.html", "w", encoding="utf-8")
        style = open('static/css/index.css', 'r').read()
        file.write(f"<style>{style}</style>")
        counter = 0
        
        async for msg in channel.history(limit=1000, oldest_first=True):
            counter += 1
            if counter % 100 == 0:
                await confMsg.edit(content="Generating Transcript... ({} Messages done)".format(counter))
            
            file.write(f"<div class='message'>")
            file.write(f"<div class='message-header'> <img src={msg.author.display_avatar}> <span class='message-author'>{msg.author}</span> <span class='message-timestamp'>{msg.created_at.strftime('%d-%m-%Y %H:%M')}</span> </div>")
            file.write(f"<div class='message-content'>{msg.content}")
            if msg.attachments:
                for attachment in msg.attachments:
                    if attachment.content_type == "image":
                        file.write(f"<div class='message-attachment'><img src={attachment.url}></div>")
                    else:
                        file.write(f"<div class='message-attachment'><a href={attachment.url}>{attachment.filename}</a></div>")

            if msg.embeds:
                for embed in msg.embeds:
                    
                    if embed.author:
                        if "reply" in embed.footer.text.lower():
                            if "anonymous" in embed.footer.text.lower():
                                file.write(f"<div class='message-embed border-red'><img src={embed.author.icon_url}>Anonymous Reply: {embed.author.name}")
                            else:
                                file.write(f"<div class='message-embed border-grey'><img src={embed.author.icon_url}>Reply: {embed.author.name}")
                        else:
                            file.write(f"<div class='message-embed'><img src={embed.author.icon_url}>{embed.author.name}")
                    else:
                        file.write(f"<div class='message-embed'><h3>{embed.title}</h3>")
                        file.write(f"<p>{embed.description}</p>")
                    
                    if embed.fields:
                        for field in embed.fields:
                            file.write(f"<p>{field.name}: {field.value}</p>")
                    file.write(f"</div>")
            file.write(f"</div></div>")

        
        file.close()
        await confMsg.edit(content="Transcript Generated!")
        return f"{id}.html"

    @commands.command()
    @commands.has_role("The Council")
    async def transcript(self, ctx: commands.Context):
        await self.createTranscript(ctx.channel)
        url = f"http://178.128.252.60:25581/transcript/{ctx.channel.id}"
        em = discord.Embed(title="Transcript", description=f"[Klik hier]({url}) om de transcript te bekijken!", color=0x00ff00)
        await ctx.send(embed=em)

    @commands.command()
    @commands.has_role("The Council")
    async def reply(self, ctx:commands.Context, *, response:str):
        await ctx.message.delete()
        targetMember = ctx.guild.get_member(int(ctx.channel.topic))
        em = discord.Embed(color=discord.Colour.blurple())
        toAttach = []
        if ctx.message.attachments:
            for attach in ctx.message.attachments:
                if attach.filename.endswith(".png") or attach.filename.endswith(".jpg"):
                    em.set_image(url=attach.url)
                else:
                    toAttach.append(attach)
        em.add_field(name="Bericht:", value=response)
        em.set_author(name=f'{ctx.author}', icon_url=ctx.author.display_avatar)
        em.timestamp = datetime.now()
        await targetMember.send(embed=em, files=toAttach)    
        em.color = discord.Colour.greyple()
        em.set_footer(text=f"Reply: {ctx.author}")
        await ctx.send(embed=em)


    @commands.command()
    @commands.has_role("The Council")
    async def areply(self, ctx:commands.Context, *, response:str):
        await ctx.message.delete()
        targetMember = ctx.guild.get_member(int(ctx.channel.topic))
        em = discord.Embed(color=discord.Colour.blurple())
        if ctx.message.attachments:
            for attach in ctx.message.attachments:
                if attach.filename.endswith(".png") or attach.filename.endswith(".jpg"):
                    em.set_image(url=attach.url)

        em.add_field(name="Bericht:", value=response)
        em.set_author(name=f'Staff Team', icon_url=self.bot.user.display_avatar)
        em.timestamp = datetime.now()
        await targetMember.send(embed=em)
        em.color = discord.Colour.brand_red()
        em.description = ""
        em.set_footer(text=f"Anonymous Reply: {ctx.author}")
        await ctx.send(embed=em)

    @commands.command()
    @commands.has_role("The Council")
    async def close(self, ctx:commands.Context):
        
        try:
            member = ctx.guild.get_member(int(ctx.channel.topic))
            em = discord.Embed(title="Gesprek Gesloten", description=f"Dit gesprek werd gesloten door het moderation team", color=discord.Colour.brand_red())
            em.add_field(name="Nog hulp nodig?", value="Open gerust terug een nieuw gesprek via de bot!")
            em.timestamp = datetime.now()
            await member.send(embed=em)

            await self.createTranscript(ctx.channel)
            url = f"https://discordbotti.ginsys.net/transcript/{ctx.channel.id}"
            em = discord.Embed(title=f"Transcript - {ctx.channel.name}", description=f"[Klik hier]({url}) om het transcript te bekijken!", color=0x00ff00)
            em.timestamp = datetime.now()
            channel = discord.utils.get(ctx.guild.channels, name="modmail-logs")
            await channel.send(embed=em)
            await ctx.channel.delete()
            await linkTranscript(ctx.channel.id, member.id)

        except Exception as e:
            print(e)
            await ctx.message.add_reaction('❌')
            return
        

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload:discord.RawMessageUpdateEvent):
        try:
            guild = self.bot.get_guild(771394209419624489)
            channel = discord.utils.get(guild.text_channels, topic=str(payload.data["author"]["id"]))
            if channel:
                async for message in channel.history():
                    if len(message.embeds) > 0:
                        em = message.embeds[0]
                        if em.footer:
                            if str(payload.message_id) in em.footer.text:
                                em.add_field(name="Message Edited:", value=payload.data["content"], inline=False)
                                await message.edit(embed=em)
                                break
        except:
            pass

                            


async def setup(bot):
    await bot.add_cog(Modmail(bot))