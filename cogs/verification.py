import re
import random
import string
import asyncio
import time
import hashlib
import imaplib
import email
import uuid
import smtplib
from typing import Dict, Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction
from motor import motor_asyncio

from utils.email_sender import send_email
from env import ENCRYPTION_KEY, OLD_CONNECTION_STRING, SMTP_EMAIL, SMTP_PASSWORD, SMTP_SERVER
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

    @ui.button(label="Ik ben afgestudeerd", style=discord.ButtonStyle.secondary, custom_id="graduated", row=1)
    async def graduated(self, interaction: Interaction, button: ui.Button):
        embed = discord.Embed(
            title="Migratie voor Afgestudeerden",
            description="Deze optie is **alleen** voor studenten die:\n"
                       "• Al geverifieerd waren in het oude systeem\n"
                       "• Geen toegang meer hebben tot hun oude HoGent e-mail\n"
                       "• Hun verificatie willen overzetten naar het nieuwe systeem\n\n"
                       "⚠️ **Let op:** We controleren of je e-mailadres nog actief is. "
                       "Deze migratie werkt alleen als je e-mail niet meer bestaat.\n\n"
                       "💬 **Problemen?** DM de bot voor ondersteuning!",
            color=0x0076C5
        )
        await interaction.response.send_message(embed=embed, view=MigrationView(self.bot), ephemeral=True)

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

class MigrationView(ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=300)  # 5 minute timeout
        self.bot = bot

    @ui.button(label="Start Migratie", style=discord.ButtonStyle.primary, custom_id="start_migration")
    async def start_migration(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_modal(MigrationModal(self.bot))

class MigrationModal(ui.Modal, title="Migratie van Oude Verificatie"):
    old_email = ui.TextInput(
        label="Je oude HoGent e-mailadres",
        placeholder="voorbeeld@student.hogent.be",
        required=True
    )

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: Interaction):
        old_email = self.old_email.value.strip()
        user_id = interaction.user.id

        # Check if user is already verified in new system
        existing_record = await self.bot.db.verifications.find_one({"user_id": user_id})
        if existing_record:
            await interaction.response.send_message("❌ Je bent al geverifieerd in het nieuwe systeem.", ephemeral=True)
            return

        # Validate email format
        if not EMAIL_REGEX.match(old_email):
            await interaction.response.send_message("❌ Ongeldig e-mailadres. Gebruik je volledige HoGent e-mailadres.", ephemeral=True)
            return

        # Check if old database connection is available
        if not OLD_CONNECTION_STRING:
            await interaction.response.send_message("❌ Migratie is momenteel niet beschikbaar.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Connect to old database
            old_client = motor_asyncio.AsyncIOMotorClient(OLD_CONNECTION_STRING)
            old_db = old_client["TIBot"]
            old_email_data = old_db["emailData"]

            # Create hash of the provided email (same method as old system)
            email_hash = hashlib.sha256(old_email.encode()).hexdigest()

            # Check if this user was verified with this email in the old system
            old_record = await old_email_data.find_one({"_id": user_id, "emailHash": email_hash})
            
            if not old_record:
                await interaction.followup.send("❌ Geen verificatie gevonden voor dit e-mailadres in het oude systeem.", ephemeral=True)
                return

            # Check if email bounces (indicating user is no longer a student)
            await interaction.followup.send("🔄 Bezig met controleren of je e-mailadres nog actief is... Dit kan enkele minuten duren.", ephemeral=True)
            
            bounce_result = await self._check_email_bounce(old_email)
            
            if bounce_result == "bounced":
                # Email bounces - user is no longer a student, allow migration
                fernet = Fernet(ENCRYPTION_KEY.encode())
                encrypted_email = fernet.encrypt(old_email.encode()).decode()
                
                # Store in new system
                await self.bot.db.verifications.insert_one({
                    "user_id": user_id,
                    "encrypted_email": encrypted_email
                })
                
                # Assign verified role
                guild = interaction.guild
                role = discord.utils.get(guild.roles, name="Verified")
                if role:
                    await interaction.user.add_roles(role)
                
                await interaction.followup.send("✅ Migratie succesvol! Je verificatie is overgebracht naar het nieuwe systeem.", ephemeral=True)
                
            elif bounce_result == "delivered" or bounce_result == "no_bounce_yet":
                await interaction.followup.send("❌ Dit e-mailadres is nog actief. Migratie is alleen beschikbaar voor ex-studenten.\n\n💬 Heb je problemen? DM de bot voor ondersteuning!", ephemeral=True)
                
            else:  # delayed, unknown, send_failed
                await interaction.followup.send("❌ Kon de status van het e-mailadres niet bepalen. Probeer het later opnieuw.\n\n💬 Blijft dit probleem bestaan? DM de bot voor ondersteuning!", ephemeral=True)

        except Exception as e:
            await interaction.followup.send("❌ Er is een fout opgetreden tijdens de migratie. Probeer het later opnieuw.\n\n💬 Blijft dit probleem bestaan? DM de bot voor ondersteuning!", ephemeral=True)
            print(f"Migration error: {e}")

    async def _check_email_bounce(self, email_address: str) -> str:
        """Check if an email bounces by sending a test email and monitoring for bounce responses"""
        try:
            # Generate unique test ID
            test_id = str(uuid.uuid4())[:8]
            
            # Send test email
            if not await self._send_test_email(email_address, test_id):
                return "send_failed"
            
            # Wait and check for bounces
            result = await self._monitor_bounces({test_id: email_address}, wait_minutes=5)
            return result.get(email_address, "unknown")
            
        except Exception as e:
            print(f"Bounce check error: {e}")
            return "unknown"

    async def _send_test_email(self, recipient: str, test_id: str) -> bool:
        """Send a minimal test email with unique identifier"""
        try:
            msg = MIMEMultipart()
            msg['From'] = SMTP_EMAIL
            msg['To'] = recipient
            msg['Subject'] = f'Email verification test - {test_id}'
            msg['Message-ID'] = f'<{test_id}@verification.test>'

            body = f"""This is an automated email verification test.

If you received this by mistake, please ignore it.
Test ID: {test_id}

This test helps verify email deliverability without requiring any action from you."""

            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(SMTP_SERVER, 587) as server:
                server.starttls()
                server.login(SMTP_EMAIL, SMTP_PASSWORD)
                server.send_message(msg)

            return True

        except Exception as e:
            print(f"Failed to send test email to {recipient}: {e}")
            return False

    async def _monitor_bounces(self, test_ids: dict, wait_minutes: int = 5) -> dict:
        """Monitor for bounce responses using IMAP"""
        results = {email_addr: "no_bounce_yet" for email_addr in test_ids.values()}
        deadline = time.time() + wait_minutes * 60
        poll_interval = 30  # seconds

        # Determine IMAP server
        if 'gmail' in SMTP_SERVER.lower():
            imap_host = "imap.gmail.com"
        elif 'outlook' in SMTP_SERVER.lower() or 'office365' in SMTP_SERVER.lower():
            imap_host = "outlook.office365.com"
        else:
            imap_host = SMTP_SERVER.replace('smtp', 'imap')

        while time.time() < deadline and any(v == "no_bounce_yet" for v in results.values()):
            try:
                with imaplib.IMAP4_SSL(imap_host) as imap:
                    imap.login(SMTP_EMAIL, SMTP_PASSWORD)
                    imap.select("INBOX")

                    # Search recent messages
                    since_str = time.strftime("%d-%b-%Y", time.gmtime(time.time() - 86400))
                    typ, data = imap.search(None, 'SINCE', since_str)

                    if typ == 'OK' and data[0]:
                        for num in data[0].split():
                            typ2, msgdata = imap.fetch(num, '(RFC822)')
                            if typ2 != 'OK' or not msgdata or not msgdata[0]:
                                continue

                            msg = email.message_from_bytes(msgdata[0][1])

                            if not self._looks_like_dsn(msg):
                                continue

                            match = self._message_matches_test(msg, test_ids)
                            if not match:
                                continue

                            email_addr, matched_test_id = match
                            if results[email_addr] != "no_bounce_yet":
                                continue

                            # Parse DSN status
                            dsn_info = self._extract_dsn_status(msg)
                            if dsn_info:
                                results[email_addr] = self._classify_from_dsn(dsn_info)
                            else:
                                # Fallback text analysis
                                all_text = (msg.get('Subject', '') + " " + str(msg)).lower()
                                if "5.1.1" in all_text or "user unknown" in all_text or "recipient not found" in all_text:
                                    results[email_addr] = "bounced"
                                elif "4." in all_text or "temporar" in all_text:
                                    results[email_addr] = "delayed"
                                else:
                                    results[email_addr] = "unknown"

                    imap.logout()
            except Exception as e:
                print(f"Error checking bounces: {e}")

            await asyncio.sleep(poll_interval)

        return results

    def _looks_like_dsn(self, msg) -> bool:
        """Check if message looks like a delivery status notification"""
        rp = (msg.get('Return-Path') or "").strip()
        ctype = (msg.get_content_type() or "").lower()
        ctype_full = (msg.get('Content-Type') or "").lower()

        # RFC-compliant DSN markers
        if rp == "<>" and ctype == "multipart/report" and "report-type=delivery-status" in ctype_full:
            return True

        # Heuristic fallback for non-compliant DSNs
        subj = (msg.get('Subject') or "").lower()
        bounce_hints = ["undeliverable", "delivery status notification", "mail delivery failed",
                        "message not delivered", "delivery failure", "undelivered mail returned to sender"]
        if any(h in subj for h in bounce_hints):
            return True

        if (msg.get('Auto-Submitted') or "").lower().startswith("auto-"):
            return True

        return False

    def _extract_dsn_status(self, msg):
        """Extract DSN status information from message/delivery-status part"""
        if not msg.is_multipart():
            return None

        for part in msg.walk():
            if part.get_content_type() == "message/delivery-status":
                try:
                    payload = part.get_payload()
                    blocks = payload if isinstance(payload, list) else [part]

                    for blk in blocks:
                        text = blk.as_string()
                        action = re.search(r'(?im)^Action:\s*([^\r\n]+)', text)
                        status = re.search(r'(?im)^Status:\s*([0-9]\.[0-9]\.[0-9])', text)
                        diag = re.search(r'(?im)^Diagnostic-Code:\s*([^\r\n]+)', text)
                        recip = re.search(r'(?im)^Final-Recipient:\s*rfc822;\s*([^\r\n\s]+)', text)

                        if action or status or diag or recip:
                            return {
                                "action": (action.group(1).strip().lower() if action else None),
                                "status": (status.group(1).strip() if status else None),
                                "diagnostic": (diag.group(1).strip() if diag else None),
                                "final_recipient": (recip.group(1).strip() if recip else None),
                            }
                except Exception:
                    pass
        return None

    def _message_matches_test(self, msg, test_id_to_email: dict):
        """Match received message to one of our sent tests"""
        subject = msg.get('Subject', '')

        # Get body text
        body_text = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body_text += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except Exception:
                        pass
        else:
            try:
                body_text = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except Exception:
                pass

        text = (subject + "\n" + body_text)

        # Match via test_id token
        for test_id, email_addr in test_id_to_email.items():
            if test_id in text:
                return (email_addr, test_id)

        # If DSN, try to pull Final-Recipient
        dsn = self._extract_dsn_status(msg)
        if dsn and dsn.get("final_recipient"):
            for test_id, email_addr in test_id_to_email.items():
                if dsn["final_recipient"].lower() == email_addr.lower():
                    return (email_addr, test_id)

        # Heuristic: look for any of the emails in message
        for test_id, email_addr in test_id_to_email.items():
            if email_addr.lower() in text.lower():
                return (email_addr, test_id)

        return None

    def _classify_from_dsn(self, dsn_info):
        """Classify bounce type from DSN information"""
        action = (dsn_info.get("action") or "").lower()
        status = (dsn_info.get("status") or "")
        if action == "failed" or status.startswith("5."):
            return "bounced"
        if action == "delayed" or status.startswith("4."):
            return "delayed"
        if action in ("delivered", "relayed", "expanded"):
            return "delivered"
        return "unknown"

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
