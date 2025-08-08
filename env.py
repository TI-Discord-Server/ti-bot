from os import getenv
from typing import Final, Tuple, cast

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: Final[str] = cast(str, getenv("BOT_TOKEN"))
MONGODB_PASSWORD: Final[str] = cast(str, getenv("MONGODB_PASSWORD"))
MONGODB_IP_ADDRESS: Final[str] = cast(str, getenv("MONGODB_IP_ADDRESS"))
MONGODB_PORT: Final[str] = cast(str, getenv("MONGODB_PORT", "27017"))
MONGODB_USERNAME: Final[str] = cast(str, getenv("MONGODB_USERNAME", "dev"))
WEBHOOK_URL: Final[str] = cast(str, getenv("WEBHOOK_URL"))
SMTP_PASSWORD: Final[str] = cast(str, getenv("SMTP_PASSWORD", ""))
SMTP_EMAIL: Final[str] = cast(str, getenv("SMTP_EMAIL", "toegepasteinformaticadiscord@gmail.com"))
SMTP_SERVER: Final[str] = cast(str, getenv("SMTP_SERVER", "smtp.gmail.com"))
ENCRYPTION_KEY: Final[str] = cast(str, getenv("ENCRYPTION_KEY"))
OLD_CONNECTION_STRING: Final[str] = cast(str, getenv("OLD_CONNECTION_STRING", ""))


__all__: Final[Tuple[str, ...]] = (
    "BOT_TOKEN",
    "MONGODB_PASSWORD",
    "MONGODB_IP_ADDRESS",
    "MONGODB_PORT",
    "MONGODB_USERNAME",
    "WEBHOOK_URL",
    "SMTP_PASSWORD",
    "SMTP_EMAIL",
    "SMTP_SERVER",
    "ENCRYPTION_KEY",
    "OLD_CONNECTION_STRING",
)