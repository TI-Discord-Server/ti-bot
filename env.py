from os import getenv
from typing import Final, Tuple, cast

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: Final[str] = cast(str, getenv("BOT_TOKEN"))
MONGODB_PASSWORD: Final[str] = cast(str, getenv("MONGODB_PASSWORD"))
MONGODB_IP_ADDRESS: Final[str] = cast(str, getenv("MONGODB_IP_ADDRESS"))

__all__: Final[Tuple[str, ...]] = (
    "BOT_TOKEN",
    "MONGODB_PASSWORD",
    "MONGODB_IP_ADDRESS",
)