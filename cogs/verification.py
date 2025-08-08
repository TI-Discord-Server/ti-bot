import re
import random
import string
import asyncio
import time
from typing import Dict, Optional

import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction

from utils.email_sender import send_email
from env import ENCRYPTION_KEY  # Add this to your env.py and .env
from cryptography.fernet import Fernet

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@student\.hogent\.be$")
CODE_LENGTH = 6
CODE_EXPIRY = 600  # 10 minutes

# In-memory store for codes: {user_id: (code, email, timestamp)}
pending_codes: Dict[int, tuple] = {}

# Encryption utility
fernet = Fernet(ENCRYPTION_KEY.encode())

class VerificationView(ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(label="Stuur code", style=discord.ButtonStyle.primary, custom_id="send_code")
    async def send_code(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_modal(EmailModal(self.bot))

    @ui.button(label="Ik heb een code", style=discord.ButtonStyle.success, custom_id="have_code")
    async def have_code(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_modal(CodeModal(self.bot))

class EmailModal(ui.Modal, title="Studentenmail verifiëren"):
    email = ui.TextInput(label="Studentenmail", placeholder="voorbeeld@student.hogent.be", required=True)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: Interaction):
        email = self.email.value.strip()
        user_id = interaction.user.id

        if not EMAIL_REGEX.match(email):
            await interaction.response.send_message(
                "❌ Dit is geen geldig HOGENT studentenmailadres.", ephemeral=True
            )
            return

        # Check if email is already used by checking all records and decrypting
        all_records = self.bot.db.verifications.find({})
        async for record in all_records:
            try:
                decrypted_email = fernet.decrypt(record['encrypted_email'].encode()).decode()
                if decrypted_email == email:
                    await interaction.response.send_message(
                        "❌ Dit e-mailadres is al gekoppeld aan een andere Discord-account.", ephemeral=True
                    )
                    return
            except Exception:
                # Skip invalid encrypted emails or corrupted records
                continue

        # Generate code and store in memory
        code = ''.join(random.choices(string.digits, k=CODE_LENGTH))
        pending_codes[user_id] = (code, email, time.time())
        try:
            send_email(
                [email],
                "Jouw verificatiecode voor de Discord-server",
                f"Jouw verificatiecode is: {code}\nDeze code is 10 minuten geldig."
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Er is een fout opgetreden bij het versturen van de e-mail: {e}", ephemeral=True
            )
            return

        await interaction.response.send_message(
            "✅ De code is verstuurd naar je studentenmail. Controleer je inbox (en spam). Gebruik de knop 'Ik heb een code' om je code in te voeren.",
            ephemeral=True
        )

class CodeModal(ui.Modal, title="Voer je verificatiecode in"):
    code = ui.TextInput(label="Code", placeholder="6-cijferige code", required=True)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: Interaction):
        user_id = interaction.user.id
        entry = pending_codes.get(user_id)
        if not entry:
            await interaction.response.send_message(
                "❌ Je hebt geen actieve verificatiecode aangevraagd. Gebruik eerst 'Stuur code'.", ephemeral=True
            )
            return

        code, email, timestamp = entry
        if time.time() - timestamp > CODE_EXPIRY:
            pending_codes.pop(user_id, None)
            await interaction.response.send_message(
                "❌ Je code is verlopen. Vraag een nieuwe code aan.", ephemeral=True
            )
            return

        if self.code.value.strip() != code:
            await interaction.response.send_message(
                "❌ Verkeerde code. Probeer het opnieuw.", ephemeral=True
            )
            return

        # Store in DB: user_id (plaintext), encrypted_email
        encrypted_email = fernet.encrypt(email.encode()).decode()
        await self.bot.db.verifications.insert_one({
            "user_id": user_id,
            "encrypted_email": encrypted_email
        })
        pending_codes.pop(user_id, None)

        # Assign verified role (replace 'Verified' with your role name)
        guild = interaction.guild
        role = discord.utils.get(guild.roles, name="Verified")
        if role:
            await interaction.user.add_roles(role)
        await interaction.response.send_message(
            "✅ Je bent succesvol geverifieerd! Je hebt nu toegang tot de server.",
            ephemeral=True
        )

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="get_email", description="Haal het e-mailadres van een gebruiker op (Moderator only)")
    @app_commands.describe(user="De gebruiker waarvan je het e-mailadres wilt opvragen")
    async def get_email(self, interaction: Interaction, user: discord.Member):
        # Check for Moderator role
        if not any(role.name == "Moderator" for role in interaction.user.roles):
            await interaction.response.send_message("❌ Je hebt geen toestemming om dit commando te gebruiken.", ephemeral=True)
            return

        record = await self.bot.db.verifications.find_one({"user_id": user.id})
        if not record:
            await interaction.response.send_message("❌ Geen e-mailadres gevonden voor deze gebruiker.", ephemeral=True)
            return

        try:
            decrypted_email = fernet.decrypt(record['encrypted_email'].encode()).decode()
            await interaction.response.send_message(f"E-mailadres: {decrypted_email}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message("❌ Fout bij het ophalen van het e-mailadres.", ephemeral=True)

    @app_commands.command(name="unverify", description="Verwijder een verificatie en kick de gebruiker")
    @app_commands.describe(
        email="Het e-mailadres om te verwijderen (optioneel)",
        user="De gebruiker om te unverifiëren (optioneel)"
    )
    async def unverify(self, interaction: Interaction, email: str = None, user: discord.Member = None):
        # Only moderators
        if not any(role.name == "Moderator" for role in interaction.user.roles):
            await interaction.response.send_message("❌ Je hebt geen toestemming om dit commando te gebruiken.", ephemeral=True)
            return

        # Must provide either email or user
        if not email and not user:
            await interaction.response.send_message("❌ Je moet een e-mailadres of gebruiker opgeven.", ephemeral=True)
            return

        # Find record
        record = None
        if user:
            # Search by user ID
            record = await self.bot.db.verifications.find_one({"user_id": user.id})
        else:
            # Search by email (decrypt all records)
            all_records = self.bot.db.verifications.find({})
            async for r in all_records:
                try:
                    decrypted_email = fernet.decrypt(r['encrypted_email'].encode()).decode()
                    if decrypted_email == email:
                        record = r
                        break
                except Exception:
                    # Skip invalid encrypted emails or corrupted records
                    continue
        
        if not record:
            search_term = f"gebruiker {user.mention}" if user else f"e-mailadres {email}"
            await interaction.response.send_message(f"❌ Geen verificatie gevonden voor {search_term}.", ephemeral=True)
            return
            
        guild = interaction.guild
        member = guild.get_member(record["user_id"])
        
        # Remove verification from database
        await self.bot.db.verifications.delete_one({"_id": record["_id"]})

        # Check if target is a moderator
        is_moderator = member and any(role.name == "Moderator" for role in member.roles)
        
        # Try to kick if not a moderator
        kicked = False
        if member and not is_moderator:
            try:
                # Create a permanent invite before kicking
                invite = None
                try:
                    # Try to create invite from the first available text channel
                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).create_instant_invite:
                            invite = await channel.create_invite(
                                max_age=0,  # Permanent invite
                                max_uses=0,  # Unlimited uses
                                reason="Invite voor gekickte gebruiker om terug te keren"
                            )
                            break
                except Exception:
                    # If invite creation fails, continue with kick anyway
                    pass
                
                # Send DM with invite before kicking
                try:
                    dm_message = "Je verificatie is ingetrokken door een moderator en je bent gekickt van de server."
                    if invite:
                        dm_message += f"\n\nJe kunt terugkeren via deze uitnodiging: {invite.url}\nJe kunt jezelf opnieuw verifiëren als je dat wilt."
                    else:
                        dm_message += "\n\nJe kunt jezelf opnieuw verifiëren als je dat wilt."
                    
                    await member.send(dm_message)
                except Exception:
                    # If DM fails, continue with kick anyway
                    pass
                
                # Kick the user
                await member.kick(reason="Verificatie ingetrokken door moderator.")
                kicked = True
            except Exception:
                pass

        # Send appropriate response
        if is_moderator:
            await interaction.response.send_message("✅ Verificatie ingetrokken. Moderator kon niet gekickt worden.", ephemeral=True)
        elif kicked:
            await interaction.response.send_message("✅ Gebruiker gekickt en verificatie ingetrokken.", ephemeral=True)
        elif member:
            await interaction.response.send_message("✅ Verificatie ingetrokken. Gebruiker kon niet gekickt worden.", ephemeral=True)
        else:
            await interaction.response.send_message("✅ Verificatie ingetrokken. Gebruiker niet meer in de server.", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # Remove verification record when user leaves
        await self.bot.db.verifications.delete_one({"user_id": member.id})

    async def cleanup_orphaned_records(self):
        """Periodically clean up verification records for users no longer in the server."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            guild = self.bot.guilds[0]  # Adjust if you have multiple guilds
            all_records = self.bot.db.verifications.find({})
            async for record in all_records:
                if not guild.get_member(record["user_id"]):
                    await self.bot.db.verifications.delete_one({"user_id": record["user_id"]})
            await asyncio.sleep(3600)  # Run every hour

async def setup(bot):
    cog = Verification(bot)
    bot.add_view(VerificationView(bot))
    bot.loop.create_task(cog.cleanup_orphaned_records())
    await bot.add_cog(cog)
