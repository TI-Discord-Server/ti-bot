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
                "❌ Dit is geen geldig HoGent studentenmailadres.", ephemeral=True
            )
            return

        # Check if email is already used
        existing = await self.bot.db.verifications.find_one({"email": email})
        if existing:
            await interaction.response.send_message(
                "❌ Dit e-mailadres is al gekoppeld aan een andere Discord-account.", ephemeral=True
            )
            return

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
            "✅ De code is verstuurd naar je studentenmail. Controleer je inbox (en spam). Gebruik de knop 'I have a code' om je code in te voeren.",
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

        # Store in DB: email, encrypted user_id
        encrypted_id = fernet.encrypt(str(user_id).encode()).decode()
        await self.bot.db.verifications.insert_one({
            "user_id": user_id,
            "email": email,
            "encrypted_id": encrypted_id
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

    @app_commands.command(name="verify_message", description="Stuur het verificatiebericht")
    async def verify_message(self, interaction: Interaction):
        embed = discord.Embed(
            title="Verificatie vereist",
            description=(
                "Om toegang te krijgen tot deze server moet je een student zijn van HoGent.\n"
                "Je moet verifiëren met een geldig studentenmailadres. Je ontvangt een code per mail, "
                "die je hieronder moet invullen om toegang te krijgen.\n"
                "Je e-mailadres wordt opgeslagen in onze database zolang je op de server blijft. "
                "Wil je het laten verwijderen, verlaat dan de server of maak een ticket aan. Je toegang wordt dan ingetrokken."
            ),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=VerificationView(self.bot))

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

        await interaction.response.send_message(f"E-mailadres: {record['email']}", ephemeral=True)

    @app_commands.command(name="unverify", description="Verwijder een verificatie en kick de gebruiker")
    @app_commands.describe(email="Het e-mailadres om te verwijderen")
    async def unverify(self, interaction: Interaction, email: str):
        # Only moderators
        if not any(role.name == "Moderator" for role in interaction.user.roles):
            await interaction.response.send_message("❌ Je hebt geen toestemming om dit commando te gebruiken.", ephemeral=True)
            return

        record = await self.bot.db.verifications.find_one({"email": email})
        if not record:
            await interaction.response.send_message("❌ Geen gebruiker gevonden met dit e-mailadres.", ephemeral=True)
            return
        guild = interaction.guild
        member = guild.get_member(record["user_id"])
        await self.bot.db.verifications.delete_one({"email": email})
        if member:
            try:
                await member.kick(reason="Verificatie ingetrokken door moderator.")
            except Exception:
                pass
        await interaction.response.send_message("✅ Gebruiker verwijderd en verificatie ingetrokken.", ephemeral=True)

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
