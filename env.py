from os import getenv
from typing import Final, Tuple, cast

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: Final[str] = cast(str, getenv("BOT_TOKEN"))
MONGODB_PASSWORD: Final[str] = cast(str, getenv("MONGODB_PASSWORD"))
MONGODB_IP_ADDRESS: Final[str] = cast(str, getenv("MONGODB_IP_ADDRESS"))
MONGODB_PORT: Final[str] = cast(str, getenv("MONGODB_PORT", "27017"))
MONGODB_USERNAME: Final[str] = cast(str, getenv("MONGODB_USERNAME", "dev"))
MONGODB_DB: Final[str] = cast(str, getenv("MONGODB_DB", MONGODB_USERNAME or "bot"))
WEBHOOK_URL: Final[str] = cast(str, getenv("WEBHOOK_URL"))
SMTP_PASSWORD: Final[str] = cast(str, getenv("SMTP_PASSWORD", ""))
SMTP_EMAIL: Final[str] = cast(str, getenv("SMTP_EMAIL", "toegepasteinformaticadiscord@gmail.com"))
SMTP_SERVER: Final[str] = cast(str, getenv("SMTP_SERVER", "smtp.gmail.com"))
SMTP_PORT: Final[int] = int(cast(str, getenv("SMTP_PORT", "587")))
IMAP_SERVER: Final[str] = cast(str, getenv("IMAP_SERVER", "imap.gmail.com"))
IMAP_PORT: Final[int] = int(cast(str, getenv("IMAP_PORT", "993")))
# Migration-specific email settings (for bounce checking with Gmail)
MIGRATION_SMTP_PASSWORD: Final[str] = cast(str, getenv("MIGRATION_SMTP_PASSWORD", ""))
MIGRATION_SMTP_EMAIL: Final[str] = cast(str, getenv("MIGRATION_SMTP_EMAIL", ""))
MIGRATION_SMTP_SERVER: Final[str] = cast(str, getenv("MIGRATION_SMTP_SERVER", "smtp.gmail.com"))
MIGRATION_SMTP_PORT: Final[int] = int(cast(str, getenv("MIGRATION_SMTP_PORT", "587")))
MIGRATION_IMAP_SERVER: Final[str] = cast(str, getenv("MIGRATION_IMAP_SERVER", "imap.gmail.com"))
MIGRATION_IMAP_PORT: Final[int] = int(cast(str, getenv("MIGRATION_IMAP_PORT", "993")))
ENCRYPTION_KEY: Final[str] = cast(str, getenv("ENCRYPTION_KEY"))
OLD_CONNECTION_STRING: Final[str] = cast(str, getenv("OLD_CONNECTION_STRING", ""))
POD_UID: Final[str] = cast(str, getenv("POD_UID", ""))
DISCORD_GUILD_ID_RAW = getenv("DISCORD_GUILD_ID", "").strip()
DISCORD_GUILD_ID: Final[int | None] = int(DISCORD_GUILD_ID_RAW) if DISCORD_GUILD_ID_RAW else None


__all__: Final[Tuple[str, ...]] = (
    "BOT_TOKEN",
    "MONGODB_PASSWORD",
    "MONGODB_IP_ADDRESS",
    "MONGODB_PORT",
    "MONGODB_USERNAME",
    "MONGODB_DB",
    "WEBHOOK_URL",
    "SMTP_PASSWORD",
    "SMTP_EMAIL",
    "SMTP_SERVER",
    "SMTP_PORT",
    "IMAP_SERVER",
    "IMAP_PORT",
    "MIGRATION_SMTP_PASSWORD",
    "MIGRATION_SMTP_EMAIL",
    "MIGRATION_SMTP_SERVER",
    "MIGRATION_SMTP_PORT",
    "MIGRATION_IMAP_SERVER",
    "MIGRATION_IMAP_PORT",
    "ENCRYPTION_KEY",
    "OLD_CONNECTION_STRING",
    "POD_UID",
    "DISCORD_GUILD_ID",
)
