import asyncio
import email
import hashlib
import imaplib
import random
import re
import smtplib
import string
import time
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict

import discord
from cryptography.fernet import Fernet
from discord import Interaction, app_commands, ui
from discord.ext import commands

from env import (
    ENCRYPTION_KEY,
    MIGRATION_IMAP_PORT,
    MIGRATION_IMAP_SERVER,
    MIGRATION_SMTP_EMAIL,
    MIGRATION_SMTP_PASSWORD,
    MIGRATION_SMTP_PORT,
    MIGRATION_SMTP_SERVER,
    SMTP_EMAIL,
    SMTP_PASSWORD,
    SMTP_SERVER,
)
from utils.crypto import make_email_index
from utils.email_sender import send_email
from utils.verification_check import ensure_verified_role

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%]+@student\.hogent\.be$")
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
        # Check if user is already verified
        existing_record = await self.bot.db.verifications.find_one({"user_id": interaction.user.id})
        if existing_record:
            await interaction.response.send_message(
                "✅ Je bent al geverifieerd! Je hebt al toegang tot de server.", ephemeral=True
            )
            await ensure_verified_role(self.bot, interaction)
            return

        await interaction.response.send_modal(EmailModal(self.bot))

    @ui.button(label="Ik heb een code", style=discord.ButtonStyle.success, custom_id="have_code")
    async def have_code(self, interaction: Interaction, button: ui.Button):
        # Check if user is already verified
        existing_record = await self.bot.db.verifications.find_one({"user_id": interaction.user.id})
        if existing_record:
            await interaction.response.send_message(
                "✅ Je bent al geverifieerd! Je hebt al toegang tot de server.", ephemeral=True
            )
            await ensure_verified_role(self.bot, interaction)
            return

        await interaction.response.send_modal(CodeModal(self.bot))

    @ui.button(
        label="Ik ben afgestudeerd",
        style=discord.ButtonStyle.secondary,
        custom_id="graduated",
        row=1,
    )
    async def graduated(self, interaction: Interaction, button: ui.Button):
        # Check if user is already verified
        existing_record = await self.bot.db.verifications.find_one({"user_id": interaction.user.id})
        if existing_record:
            await interaction.response.send_message(
                "✅ Je bent al geverifieerd! Je hebt al toegang tot de server.", ephemeral=True
            )
            await ensure_verified_role(self.bot, interaction)
            return

        embed = discord.Embed(
            title="Migratie voor Afgestudeerden",
            description="Deze optie is **alleen** voor studenten die:\n"
            "• Al geverifieerd waren in het oude systeem\n"
            "• Geen toegang meer hebben tot hun oude HOGENT e-mail\n"
            "• Hun verificatie willen overzetten naar het nieuwe systeem\n\n"
            "⚠️ **Let op:** We controleren of je e-mailadres nog actief is. "
            "Deze migratie werkt alleen als je e-mail niet meer bestaat.\n\n"
            "💬 **Problemen?** DM de bot voor ondersteuning!",
            color=0x0076C5,
        )
        await interaction.response.send_message(
            embed=embed, view=MigrationView(self.bot), ephemeral=True
        )


class EmailModal(ui.Modal, title="Studentenmail verifiëren"):
    email = ui.TextInput(
        label="Studentenmail", placeholder="voorbeeld@student.hogent.be", required=True
    )

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        email = self.email.value.lower().strip()
        user_id = interaction.user.id

        await interaction.followup.send(
            "📨 Je e-mailadres wordt gecontroleerd en de code wordt verstuurd...", ephemeral=True
        )
        # Check if user is already verified
        existing_record = await self.bot.db.verifications.find_one({"user_id": user_id})
        if existing_record:
            await interaction.followup.send(
                "✅ Je bent al geverifieerd! Je hebt al toegang tot de server.", ephemeral=True
            )
            await ensure_verified_role(self.bot, interaction)
            return

        if not EMAIL_REGEX.match(email):
            await interaction.followup.send(
                "❌ Dit is geen geldig HOGENT studentenmailadres.", ephemeral=True
            )
            return

        try:
            # Bereken blind index met HMAC
            email_index = make_email_index(email)

            # Check if email already exists via blind index
            exists = await self.bot.db.verifications.find_one({"email_index": email_index})
            if exists:
                await interaction.followup.send(
                    "❌ Dit e-mailadres is al gekoppeld aan een andere Discord-account.",
                    ephemeral=True,
                )
                return
        except Exception as e:
            self.bot.log.error(f"Error checking email existence for {email}: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ Er is een fout opgetreden bij het verwerken van je e-mailadres. Probeer het later opnieuw.",
                ephemeral=True,
            )
            return

        # Generate code and store
        code = "".join(random.choices(string.digits, k=CODE_LENGTH))
        pending_codes[user_id] = (code, email, time.time())

        async def send_email_background():
            try:
                send_email(
                    [email],
                    "Jouw verificatiecode voor de Discord-server",
                    f"Jouw verificatiecode is: {code}\nDeze code is 10 minuten geldig.",
                )
                await interaction.followup.send(
                    "✅ De code is verstuurd naar je studentenmail. Controleer je inbox (en spam). Gebruik de knop 'Ik heb een code' om je code in te voeren.",
                    ephemeral=True,
                )
            except Exception as e:
                pending_codes.pop(user_id, None)
                await interaction.followup.send(
                    f"❌ Er is een fout opgetreden bij het versturen van de e-mail: {e}",
                    ephemeral=True,
                )

        asyncio.create_task(send_email_background())


class CodeModal(ui.Modal, title="Voer je verificatiecode in"):
    code = ui.TextInput(label="Code", placeholder="6-cijferige code", required=True)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: Interaction):
        user_id = interaction.user.id

        # Check if user is already verified
        existing_record = await self.bot.db.verifications.find_one({"user_id": user_id})
        if existing_record:
            await interaction.response.send_message(
                "✅ Je bent al geverifieerd! Je hebt al toegang tot de server.", ephemeral=True
            )
            await ensure_verified_role(self.bot, interaction)
            return

        entry = pending_codes.get(user_id)
        if not entry:
            await interaction.response.send_message(
                "❌ Je hebt geen actieve verificatiecode aangevraagd. Gebruik eerst 'Stuur code'.",
                ephemeral=True,
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
        email_index = make_email_index(email)
        try:
            await self.bot.db.verifications.insert_one(
                {"user_id": user_id, "encrypted_email": encrypted_email, "email_index": email_index}
            )
            # Verification success logging disabled per user request
            # self.bot.log.info(f"Successfully verified user {interaction.user} ({user_id}) with email {email}")
        except Exception as e:
            self.bot.log.error(
                f"Failed to store verification record for user {interaction.user} ({user_id}): {e}",
                exc_info=True,
            )
            await interaction.response.send_message(
                "❌ Er is een fout opgetreden bij het opslaan van je verificatie. Probeer het opnieuw.",
                ephemeral=True,
            )
            return

        pending_codes.pop(user_id, None)

        # Assign verified role (replace 'Verified' with your role name)
        guild = interaction.guild
        settings = await self.bot.db.settings.find_one({"_id": "verification_settings"})
        verified_role_id = settings.get("verified_role_id")
        role = guild.get_role(verified_role_id) if verified_role_id else None
        if role:
            try:
                await interaction.user.add_roles(role)
                # Role assignment success logging disabled per user request
                # self.bot.log.info(f"Assigned Verified role to user {interaction.user} ({user_id})")
            except Exception as e:
                self.bot.log.error(
                    f"Failed to assign Verified role to user {interaction.user} ({user_id}): {e}",
                    exc_info=True,
                )
        else:
            self.bot.log.warning("Verified role not found in guild")

        await interaction.response.send_message(
            "✅ Je bent succesvol geverifieerd! Je hebt nu toegang tot de server.", ephemeral=True
        )


class MigrationView(ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=300)  # 5 minute timeout
        self.bot = bot

    @ui.button(
        label="Start Migratie", style=discord.ButtonStyle.primary, custom_id="start_migration"
    )
    async def start_migration(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_modal(MigrationModal(self.bot))


class MigrationModal(ui.Modal, title="Migratie van Oude Verificatie"):
    old_email = ui.TextInput(
        label="Je oude HOGENT e-mailadres", placeholder="voorbeeld@student.hogent.be", required=True
    )

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        old_email = self.old_email.value.lower().strip()
        user_id = interaction.user.id

        await interaction.followup.send(
            "🔄 Bezig met migreren van je verificatie...", ephemeral=True
        )

        existing_record = await self.bot.db.verifications.find_one({"user_id": user_id})
        if existing_record:
            await interaction.followup.send(
                "❌ Je bent al geverifieerd in het nieuwe systeem.", ephemeral=True
            )
            return

        if not EMAIL_REGEX.match(old_email):
            await interaction.followup.send(
                "❌ Ongeldig e-mailadres. Gebruik je volledige HOGENT e-mailadres.", ephemeral=True
            )
            return

        try:
            # Check if email already used via HMAC index
            email_index = make_email_index(old_email)
            exists = await self.bot.db.verifications.find_one({"email_index": email_index})
            if exists:
                await interaction.followup.send(
                    "❌ Dit e-mailadres is al gekoppeld aan een andere Discord-account.",
                    ephemeral=True,
                )
                return
        except Exception as e:
            self.bot.log.error(
                f"Error checking email existence for migration {old_email}: {e}", exc_info=True
            )
            await interaction.followup.send(
                "❌ Er is een fout opgetreden bij het verwerken van je e-mailadres. Probeer het later opnieuw.",
                ephemeral=True,
            )
            return

        try:
            email_hash = hashlib.sha256(old_email.encode()).hexdigest()
            old_record = await self.bot.db["oldEmails"].find_one(
                {"user_id": user_id, "email_hash": email_hash}
            )

            if not old_record:
                await interaction.followup.send(
                    "❌ Geen verificatie gevonden voor dit e-mailadres in het oude systeem.",
                    ephemeral=True,
                )
                return

            await interaction.followup.send(
                "🔄 Bezig met controleren of je e-mailadres nog actief is... Dit kan enkele minuten duren.",
                ephemeral=True,
            )

            bounce_result = await self._check_email_bounce(old_email)

            if bounce_result == "bounced":
                encrypted_email = fernet.encrypt(old_email.encode()).decode()

                await self.bot.db.verifications.insert_one(
                    {
                        "user_id": user_id,
                        "encrypted_email": encrypted_email,
                        "email_index": make_email_index(old_email),
                        "migrated": True,
                    }
                )

                guild = interaction.guild
                settings = await self.bot.db.settings.find_one({"_id": "verification_settings"})
                verified_role_id = settings.get("verified_role_id")
                role = guild.get_role(verified_role_id) if verified_role_id else None

                if role:
                    try:
                        await interaction.user.add_roles(role)
                    except Exception as e:
                        self.bot.log.error(
                            f"Failed to assign role during migration: {e}", exc_info=True
                        )

                await interaction.followup.send(
                    "✅ Migratie succesvol! Je verificatie is overgebracht naar het nieuwe systeem.",
                    ephemeral=True,
                )

            elif bounce_result in ("delivered", "no_bounce_yet"):
                await interaction.followup.send(
                    "❌ Dit e-mailadres is nog actief. Migratie is alleen beschikbaar voor ex-studenten.",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "❌ Kon de status van het e-mailadres niet bepalen. Probeer het later opnieuw.",
                    ephemeral=True,
                )

        except Exception as e:
            self.bot.log.error(f"Migration error: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ Er is een fout opgetreden tijdens de migratie. Probeer het later opnieuw.",
                ephemeral=True,
            )

    def _validate_migration_credentials(self) -> bool:
        """Validate that migration email credentials are properly configured"""
        required_vars = [
            MIGRATION_SMTP_EMAIL,
            MIGRATION_SMTP_PASSWORD,
            MIGRATION_SMTP_SERVER,
            MIGRATION_IMAP_SERVER,
        ]

        if not all(required_vars):
            return False

        # Check if migration credentials are different from regular credentials
        # This ensures we're using separate accounts for migration vs normal verification
        if (
            MIGRATION_SMTP_EMAIL == SMTP_EMAIL
            and MIGRATION_SMTP_PASSWORD == SMTP_PASSWORD
            and MIGRATION_SMTP_SERVER == SMTP_SERVER
        ):
            self.bot.log.warning("Migration credentials are identical to regular SMTP credentials")

        return True

    async def _check_email_bounce(self, email_address: str) -> str:
        """Check if an email bounces by sending a test email and monitoring for bounce responses"""
        try:
            # Validate migration credentials first
            if not self._validate_migration_credentials():
                self.bot.log.error("Migration email credentials not properly configured")
                return "send_failed"

            # Generate unique test ID
            test_id = str(uuid.uuid4())[:8]

            # Send test email
            if not await self._send_test_email(email_address, test_id):
                return "send_failed"

            # Wait and check for bounces
            result = await self._monitor_bounces({test_id: email_address}, wait_minutes=5)
            return result.get(email_address, "unknown")

        except Exception as e:
            self.bot.log.error(f"Bounce check error: {e}", exc_info=True)
            return "unknown"

    async def _send_test_email(self, recipient: str, test_id: str) -> bool:
        """Send a minimal test email with unique identifier using migration credentials"""
        try:
            msg = MIMEMultipart()
            msg["From"] = MIGRATION_SMTP_EMAIL
            msg["To"] = recipient
            msg["Subject"] = f"E-mail verificatie test - {test_id}"
            msg["Message-ID"] = f"<{test_id}@verification.test>"

            body = f"""Dit is een geautomatiseerde e-mail verificatie test.

Als je deze e-mail per ongeluk hebt ontvangen, kun je deze negeren.
Test ID: {test_id}

Deze test helpt bij het verifiëren van e-mail bezorgbaarheid zonder dat je actie hoeft te ondernemen."""

            msg.attach(MIMEText(body, "plain"))

            # Use SSL if port 465, otherwise use STARTTLS
            if MIGRATION_SMTP_PORT == 465:
                with smtplib.SMTP_SSL(MIGRATION_SMTP_SERVER, MIGRATION_SMTP_PORT) as server:
                    server.login(MIGRATION_SMTP_EMAIL, MIGRATION_SMTP_PASSWORD)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(MIGRATION_SMTP_SERVER, MIGRATION_SMTP_PORT) as server:
                    server.starttls()
                    server.login(MIGRATION_SMTP_EMAIL, MIGRATION_SMTP_PASSWORD)
                    server.send_message(msg)

            return True

        except Exception as e:
            self.bot.log.error(f"Failed to send test email to {recipient}: {e}", exc_info=True)
            return False

    async def _monitor_bounces(self, test_ids: dict, wait_minutes: int = 5) -> dict:
        """Monitor for bounce responses using IMAP"""
        results = {email_addr: "no_bounce_yet" for email_addr in test_ids.values()}
        deadline = time.time() + wait_minutes * 60
        poll_interval = 30  # seconds

        # Use migration-specific IMAP server and port
        imap_host = MIGRATION_IMAP_SERVER
        imap_port = MIGRATION_IMAP_PORT

        while time.time() < deadline and any(v == "no_bounce_yet" for v in results.values()):
            try:
                with imaplib.IMAP4_SSL(imap_host, imap_port) as imap:
                    imap.login(MIGRATION_SMTP_EMAIL, MIGRATION_SMTP_PASSWORD)
                    imap.select("INBOX")

                    # Search recent messages
                    since_str = time.strftime("%d-%b-%Y", time.gmtime(time.time() - 86400))
                    typ, data = imap.search(None, "SINCE", since_str)

                    if typ == "OK" and data[0]:
                        for num in data[0].split():
                            typ2, msgdata = imap.fetch(num, "(RFC822)")
                            if typ2 != "OK" or not msgdata or not msgdata[0]:
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
                                all_text = (msg.get("Subject", "") + " " + str(msg)).lower()
                                if (
                                    "5.1.1" in all_text
                                    or "user unknown" in all_text
                                    or "recipient not found" in all_text
                                ):
                                    results[email_addr] = "bounced"
                                elif "4." in all_text or "temporar" in all_text:
                                    results[email_addr] = "delayed"
                                else:
                                    results[email_addr] = "unknown"

                    imap.logout()
            except Exception as e:
                self.bot.log.error(f"Error checking bounces: {e}", exc_info=True)

            await asyncio.sleep(poll_interval)

        return results

    def _looks_like_dsn(self, msg) -> bool:
        """Check if message looks like a delivery status notification"""
        rp = (msg.get("Return-Path") or "").strip()
        ctype = (msg.get_content_type() or "").lower()
        ctype_full = (msg.get("Content-Type") or "").lower()

        # RFC-compliant DSN markers
        if (
            rp == "<>"
            and ctype == "multipart/report"
            and "report-type=delivery-status" in ctype_full
        ):
            return True

        # Heuristic fallback for non-compliant DSNs
        subj = (msg.get("Subject") or "").lower()
        bounce_hints = [
            "undeliverable",
            "delivery status notification",
            "mail delivery failed",
            "message not delivered",
            "delivery failure",
            "undelivered mail returned to sender",
        ]
        if any(h in subj for h in bounce_hints):
            return True

        if (msg.get("Auto-Submitted") or "").lower().startswith("auto-"):
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
                        action = re.search(r"(?im)^Action:\s*([^\r\n]+)", text)
                        status = re.search(r"(?im)^Status:\s*([0-9]\.[0-9]\.[0-9])", text)
                        diag = re.search(r"(?im)^Diagnostic-Code:\s*([^\r\n]+)", text)
                        recip = re.search(r"(?im)^Final-Recipient:\s*rfc822;\s*([^\r\n\s]+)", text)

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
        subject = msg.get("Subject", "")

        # Get body text
        body_text = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body_text += part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    except Exception:
                        pass
        else:
            try:
                body_text = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
            except Exception:
                pass

        text = subject + "\n" + body_text

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
        status = dsn_info.get("status") or ""
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

    @app_commands.command(
        name="get_email", description="Haal het e-mailadres van een gebruiker op (Moderator only)"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.has_role(860195356493742100)
    @app_commands.describe(user="De gebruiker waarvan je het e-mailadres wilt opvragen")
    async def get_email(self, interaction: Interaction, user: discord.Member):
        record = await self.bot.db.verifications.find_one({"user_id": user.id})
        if not record:
            self.bot.log.info(
                f"No email found for user {user.name} ({user.id}) when requested by {interaction.user.name} ({interaction.user.id})"
            )
            await interaction.response.send_message(
                "❌ Geen e-mailadres gevonden voor deze gebruiker.", ephemeral=True
            )
            return

        try:
            decrypted_email = fernet.decrypt(record["encrypted_email"].encode()).decode()

            # Check if this is a migrated account
            is_migrated = record.get("migrated", False)

            if is_migrated:
                message = (
                    f"📧 E-mailadres: {decrypted_email}\n🔄 **Gemigreerd** van het oude systeem"
                )
            else:
                message = f"📧 E-mailadres: {decrypted_email}\n✅ Nieuw verificatiesysteem"

            await interaction.response.send_message(message, ephemeral=True)
            self.bot.log.info(
                f"Email retrieved for user {user.name} ({user.id}) by {interaction.user.name} ({interaction.user.id})"
            )
        except Exception as e:
            self.bot.log.error(
                f"Error retrieving email for user {user.name} ({user.id}) by {interaction.user.name} ({interaction.user.id}): {e}"
            )
            await interaction.response.send_message(
                "❌ Fout bij het ophalen van het e-mailadres.", ephemeral=True
            )

    @app_commands.command(
        name="check_email",
        description="Check of een e-mailadres al gebruikt wordt (Moderator only)",
    )
    # @app_commands.checks.has_permissions(manage_messages=True)
    # @app_commands.checks.has_role(860195356493742100)
    @app_commands.describe(email="Het e-mailadres dat je wil controleren")
    async def check_email(self, interaction: Interaction, email: str):
        # Antwoord altijd ephemeral (privacy)
        await interaction.response.defer(ephemeral=True)

        email_norm = email.strip()
        if not EMAIL_REGEX.match(email_norm):
            await interaction.followup.send("❌ Ongeldig e-mailadres.", ephemeral=True)
            return

        try:
            idx = make_email_index(email_norm)

            record = await self.bot.db.verifications.find_one(
                {"email_index": idx},
                {"user_id": 1, "migrated": 1},  # project enkel wat je nodig hebt
            )

            if not record:
                await interaction.followup.send(
                    "✅ Dit e-mailadres is **nog niet** in gebruik.", ephemeral=True
                )
                self.bot.log.info(
                    f"check_email: email not in use (requested by {interaction.user.id})"
                )
                return

            user_id = record.get("user_id")
            migrated = record.get("migrated", False)

            # Probeer member te resolven (kan None zijn als niet in guild cache)
            member = interaction.guild.get_member(user_id) if interaction.guild else None
            user_label = member.mention if member else f"`{user_id}`"

            extra = " 🔄 (gemigreerd)" if migrated else ""
            await interaction.followup.send(
                f"⚠️ Dit e-mailadres is **al in gebruik** door: {user_label}{extra}", ephemeral=True
            )

            self.bot.log.info(
                f"check_email: email in use by {user_id} (requested by {interaction.user.id})"
            )

        except Exception as e:
            self.bot.log.error(f"check_email error (requested by {interaction.user.id}): {e}")
            await interaction.followup.send(
                "❌ Er liep iets mis bij het controleren.", ephemeral=True
            )

    @app_commands.command(
        name="unverify", description="Verwijder een verificatie en kick de gebruiker"
    )
    # @app_commands.checks.has_permissions(manage_messages=True)
    # @app_commands.checks.has_role(860195356493742100)
    @app_commands.describe(
        email="Het e-mailadres om te verwijderen (optioneel)",
        user="De gebruiker om te unverifiëren (optioneel)",
    )
    async def unverify(
        self, interaction: Interaction, email: str = None, user: discord.Member = None
    ):
        # Must provide either email or user
        if not email and not user:
            self.bot.log.warning(
                f"User {interaction.user.name} ({interaction.user.id}) used unverify without providing email or user"
            )
            await interaction.response.send_message(
                "❌ Je moet een e-mailadres of gebruiker opgeven.", ephemeral=True
            )
            return

        # Find record
        record = None
        if user:
            # Search by user ID
            record = await self.bot.db.verifications.find_one({"user_id": user.id})
        else:
            try:
                # Search by email using HMAC index
                email_index = make_email_index(email)
                record = await self.bot.db.verifications.find_one({"email_index": email_index})
            except Exception as e:
                self.bot.log.error(
                    f"Error checking email existence for unverify {email}: {e}", exc_info=True
                )
                await interaction.response.send_message(
                    "❌ Er is een fout opgetreden bij het verwerken van het e-mailadres. Probeer het later opnieuw.",
                    ephemeral=True,
                )
                return

        if not record:
            search_term = f"gebruiker {user.mention}" if user else f"e-mailadres {email}"
            self.bot.log.info(
                f"No verification record found for {search_term} when unverify requested by {interaction.user.name} ({interaction.user.id})"
            )
            await interaction.response.send_message(
                f"❌ Geen verificatie gevonden voor {search_term}.", ephemeral=True
            )
            return

        guild = interaction.guild
        member = guild.get_member(record["user_id"])

        # Check if target has admin permissions
        has_admin_permission = False
        if member:
            has_admin_permission = any(r.permissions.administrator for r in member.roles)

        # Send initial response immediately
        if has_admin_permission:
            await interaction.response.send_message(
                "✅ Verificatie ingetrokken. Administrator kon niet gekickt worden.", ephemeral=True
            )
        elif not member:
            await interaction.response.send_message(
                "✅ Verificatie ingetrokken. Gebruiker niet meer in de server.", ephemeral=True
            )
        else:
            # User exists and is not an admin - will attempt kick
            await interaction.response.send_message(
                "🔄 Verificatie wordt ingetrokken en gebruiker wordt gekickt...", ephemeral=True
            )

        # Remove verification from database

        try:
            result = await self.bot.db.verifications.delete_one({"_id": record["_id"]})

            if result.deleted_count > 0:
                target_info = (
                    f"user {member} ({record['user_id']})"
                    if member
                    else f"user ID {record['user_id']}"
                )
                self.bot.log.info(
                    f"Manually revoked verification for {target_info} by admin {interaction.user} ({interaction.user.id})"
                )
            else:
                self.bot.log.warning(
                    f"Failed to delete verification record for user ID {record['user_id']} during manual revocation"
                )

        except Exception as e:
            self.bot.log.error(
                f"Error removing verification record during manual revocation for user ID {record['user_id']}: {e}",
                exc_info=True,
            )

        # Try to kick if not an admin and member exists
        if member and not has_admin_permission:
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
                                reason="Invite voor gekickte gebruiker om terug te keren",
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

                # Send followup message about successful kick
                try:
                    await interaction.followup.send(
                        "✅ Gebruiker succesvol gekickt en verificatie ingetrokken.", ephemeral=True
                    )
                except discord.HTTPException as e:
                    if e.code == 10062:
                        self.bot.log.warning(
                            f"Revoke verification success followup expired (10062) for user {interaction.user}"
                        )
                    else:
                        self.bot.log.error(f"Failed to send kick success message: {e}")

            except Exception:
                # Send followup message about failed kick
                try:
                    await interaction.followup.send(
                        "✅ Verificatie ingetrokken, maar gebruiker kon niet gekickt worden.",
                        ephemeral=True,
                    )
                except discord.HTTPException as follow_e:
                    if follow_e.code == 10062:
                        self.bot.log.warning(
                            f"Revoke verification failed-kick followup expired (10062) for user {interaction.user}"
                        )
                    else:
                        self.bot.log.error(f"Failed to send kick failure message: {follow_e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Remove verification record when user leaves the server."""
        try:
            # Check if user had a verification record before removing
            existing_record = await self.bot.db.verifications.find_one({"user_id": member.id})

            if existing_record:
                # Remove verification record
                result = await self.bot.db.verifications.delete_one({"user_id": member.id})

                if result.deleted_count > 0:
                    self.bot.log.info(
                        f"Removed verification record for user {member} ({member.id}) who left the server"
                    )
                else:
                    self.bot.log.warning(
                        f"Failed to remove verification record for user {member} ({member.id}) who left the server"
                    )
            else:
                self.bot.log.debug(
                    f"User {member} ({member.id}) left the server but had no verification record"
                )

        except Exception as e:
            self.bot.log.error(
                f"Error removing verification record for user {member} ({member.id}) who left the server: {e}",
                exc_info=True,
            )

    async def cleanup_orphaned_records(self):
        """Periodically clean up verification records for users no longer in the server."""
        await self.bot.wait_until_ready()

        # Wait a bit more to ensure guild configuration is loaded
        await asyncio.sleep(5)

        self.bot.log.info(
            f"Starting periodic verification records cleanup task (configured guild_id: {self.bot.guild_id})"
        )

        # Verify guild configuration is available
        if not self.bot.guild_id:
            self.bot.log.error(
                "No guild_id configured for verification cleanup. Please configure the server in /configure"
            )
            return

        while not self.bot.is_closed():
            try:
                self.bot.log.debug("Running verification records cleanup check")

                # Get the configured guild from bot settings
                guild = self.bot.guild
                if not guild:
                    self.bot.log.warning(
                        f"Configured guild not found (guild_id: {self.bot.guild_id}), skipping verification cleanup"
                    )
                    await asyncio.sleep(3600)
                    continue

                self.bot.log.debug(
                    f"Checking verification records for configured guild: {guild.name} ({guild.id})"
                )

                cleanup_count = 0
                total_records = 0

                all_records = self.bot.db.verifications.find({})
                async for record in all_records:
                    total_records += 1
                    user_id = record["user_id"]

                    # Check if user is still in the server
                    member = guild.get_member(user_id)
                    if not member:
                        # User is no longer in the server, remove their verification record
                        try:
                            # Remove the record
                            result = await self.bot.db.verifications.delete_one(
                                {"user_id": user_id}
                            )

                            if result.deleted_count > 0:
                                cleanup_count += 1
                                self.bot.log.info(
                                    f"Cleaned up orphaned verification record for user ID {user_id} (no longer in server)"
                                )
                            else:
                                self.bot.log.warning(
                                    f"Failed to delete orphaned verification record for user ID {user_id}"
                                )

                        except Exception as e:
                            self.bot.log.error(
                                f"Error cleaning up verification record for user ID {user_id}: {e}",
                                exc_info=True,
                            )

                if cleanup_count > 0:
                    self.bot.log.info(
                        f"Verification cleanup completed: removed {cleanup_count} orphaned records out of {total_records} total records"
                    )
                else:
                    self.bot.log.debug(
                        f"Verification cleanup completed: no orphaned records found ({total_records} total records checked)"
                    )

            except Exception as e:
                self.bot.log.error(f"Error during verification records cleanup: {e}", exc_info=True)

            # Wait 1 hour before next cleanup
            await asyncio.sleep(3600)

    @app_commands.command(
        name="migrate_email_index", description="Voeg email_index toe aan alle oude verificaties"
    )
    @app_commands.default_permissions(administrator=True)
    async def migrate_email_index(self, interaction: Interaction):
        await interaction.response.send_message(
            "🔄 Start migratie van email_index...", ephemeral=True
        )

        updated = 0
        failed = 0

        async for record in self.bot.db.verifications.find({}):
            if "email_index" in record:
                continue  # al gemigreerd

            try:
                decrypted_email = fernet.decrypt(record["encrypted_email"].encode()).decode()
                email_index = make_email_index(decrypted_email)

                await self.bot.db.verifications.update_one(
                    {"_id": record["_id"]}, {"$set": {"email_index": email_index}}
                )
                updated += 1
            except Exception as e:
                failed += 1
                self.bot.log.error(f"Failed to migrate record {record['_id']}: {e}")

        await interaction.followup.send(
            f"✅ Migratie voltooid! {updated} records bijgewerkt. ⚠️ {failed} mislukt.",
            ephemeral=True,
        )

    @app_commands.command(
        name="cleanup_unverified",
        description="Verwijder alle rollen van leden die niet verified zijn.",
    )
    @app_commands.default_permissions(administrator=True)
    async def cleanup_unverified(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        # Haal de verified rol uit de database
        settings = await self.bot.db.settings.find_one({"_id": "verification_settings"})
        verified_role_id = settings.get("verified_role_id")
        verified_role = guild.get_role(verified_role_id) if verified_role_id else None

        if not verified_role:
            await interaction.followup.send(
                "❌ Verified rol niet gevonden in de instellingen.", ephemeral=True
            )
            return

        cleaned = []
        skipped = []

        for member in guild.members:
            if member.bot:
                continue

            if verified_role not in member.roles:
                roles_to_remove = [r for r in member.roles if r != guild.default_role]
                if roles_to_remove:
                    try:
                        await member.remove_roles(
                            *roles_to_remove, reason="Niet verified, opgeschoond"
                        )
                        cleaned.append(member.display_name)

                        # Kleine delay om rate limit te vermijden
                        await asyncio.sleep(1.2)

                    except discord.Forbidden:
                        skipped.append(member.display_name)
                    except discord.HTTPException as e:
                        skipped.append(f"{member.display_name} (HTTP fout: {e})")

        msg = f"✅ {len(cleaned)} leden opgeschoond."
        if skipped:
            msg += f"\n⚠️ {len(skipped)} leden konden niet opgeschoond worden."

        await interaction.followup.send(msg, ephemeral=True)

    @app_commands.command(
        name="manual_verify",
        description="Verifieer een gebruiker handmatig met een studentenmail (zonder code).",
    )
    @app_commands.describe(
        user="De gebruiker die je wil verifiëren", email="Het HOGENT studentenmailadres"
    )
    # @app_commands.checks.has_permissions(manage_messages=True)
    # @app_commands.checks.has_role(777987142236241941)
    async def manual_verify(self, interaction: Interaction, user: discord.Member, email: str):
        await interaction.response.defer(ephemeral=True)

        email = email.lower().strip()

        # Validatie emailadres
        if not EMAIL_REGEX.match(email):
            await interaction.followup.send(
                "❌ Ongeldig e-mailadres. Gebruik een volledig HOGENT studentenmailadres.",
                ephemeral=True,
            )
            return

        # Bestaat de gebruiker al in de DB?
        existing = await self.bot.db.verifications.find_one({"user_id": user.id})
        if existing:
            await interaction.followup.send(f"⚠️ {user.mention} is al geverifieerd.", ephemeral=True)
            return

        try:
            # Bereken blind index
            email_index = make_email_index(email)

            # Controleer of dit mailadres al gebruikt wordt
            exists = await self.bot.db.verifications.find_one({"email_index": email_index})
            if exists:
                await interaction.followup.send(
                    "❌ Dit e-mailadres is al gekoppeld aan een andere gebruiker.", ephemeral=True
                )
                return

            # Encrypt en opslaan
            encrypted_email = fernet.encrypt(email.encode()).decode()
            await self.bot.db.verifications.insert_one(
                {
                    "user_id": user.id,
                    "encrypted_email": encrypted_email,
                    "email_index": email_index,
                    "manual": True,  # flag dat dit manueel gebeurd is
                    "verified_by": interaction.user.id,
                    "timestamp": int(time.time()),
                }
            )

            # Rol toekennen
            settings = await self.bot.db.settings.find_one({"_id": "verification_settings"})
            verified_role_id = settings.get("verified_role_id")
            role = interaction.guild.get_role(verified_role_id) if verified_role_id else None
            if role:
                await user.add_roles(role, reason="Handmatig geverifieerd door moderator")

            await interaction.followup.send(
                f"✅ {user.mention} is succesvol handmatig geverifieerd met e-mail `{email}`.",
                ephemeral=True,
            )
            try:
                await user.send(
                    f"✅ Je bent handmatig geverifieerd in **{interaction.guild.name}**.\n"
                    f"Je gekoppelde studentenmail: `{email}`"
                )
            except discord.Forbidden:
                pass

            self.bot.log.info(
                f"User {user} ({user.id}) handmatig geverifieerd door {interaction.user} ({interaction.user.id}) met email {email}"
            )

        except Exception as e:
            self.bot.log.error(
                f"Fout bij handmatige verificatie van {user} ({user.id}): {e}", exc_info=True
            )
            await interaction.followup.send(
                "❌ Er is een fout opgetreden bij de handmatige verificatie. Probeer opnieuw.",
                ephemeral=True,
            )


async def setup(bot):
    cog = Verification(bot)
    await bot.add_cog(cog)

    # Index maken in de achtergrond (niet blokkeren bij load)
    async def ensure_index():
        try:
            await bot.wait_until_ready()
            await bot.db.verifications.create_index(
                "email_index",
                unique=True,
                partialFilterExpression={"email_index": {"$exists": True, "$type": "string"}},
            )
            bot.log.info("✅ email_index ensured on verifications collection")
        except Exception as e:
            bot.log.error(f"Failed to ensure email_index: {e}", exc_info=True)

    bot.loop.create_task(ensure_index())

    # Start cleanup taak
    bot.loop.create_task(cog.cleanup_orphaned_records())
