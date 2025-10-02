import datetime
import re
from typing import Optional

import discord

from utils.timezone import format_local_time, now_utc


async def send_dm_embed(member: discord.Member, embed: discord.Embed) -> bool:
    """
    Stuurt een DM naar een gebruiker met een embedded message.
    Retourneert True als de DM succesvol is verzonden, False anders.
    """
    try:
        await member.send(embed=embed)
        return True
    except (discord.errors.Forbidden, discord.errors.HTTPException):
        return False


def parse_duration(duration_str: str) -> Optional[datetime.timedelta]:
    """Parse duration string and return timedelta. Supports m, h, d, w, mo, y units."""
    units = {"m": "minutes", "h": "hours", "d": "days", "w": "weeks", "mo": "months", "y": "years"}

    # Match pattern like 1m, 5h, 1d, 2w, 1mo, 1y
    match = re.match(r"(\d+)(m|h|d|w|mo|y)$", duration_str.lower())
    if not match:
        return None

    amount, unit = match.groups()
    amount = int(amount)

    # Handle months and years separately since timedelta doesn't support them directly
    if unit == "mo":
        # Approximate 1 month = 30 days
        return datetime.timedelta(days=amount * 30)
    elif unit == "y":
        # Approximate 1 year = 365 days
        return datetime.timedelta(days=amount * 365)
    else:
        unit_name = units[unit]
        return datetime.timedelta(**{unit_name: amount})


async def log_infraction(
    infractions_collection,
    guild_id: int,
    user_id: int,
    moderator_id: int,
    infraction_type: str,
    reason: str,
):
    """Log an infraction to the database."""
    infraction_data = {
        "guild_id": guild_id,
        "user_id": user_id,
        "moderator_id": moderator_id,
        "type": infraction_type,
        "reason": reason,
        "timestamp": now_utc().isoformat(),
    }
    await infractions_collection.insert_one(infraction_data)


def create_dm_embed(
    title: str, description: str, color: discord.Color, bot_icon_url: str = None
) -> discord.Embed:
    """Create a standardized DM embed."""
    timestamp = now_utc()
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
    )
    embed.set_footer(text=f"Tijd: {format_local_time(timestamp)}")
    if bot_icon_url:
        embed.set_thumbnail(url=bot_icon_url)
    return embed


def format_duration(duration: datetime.timedelta) -> str:
    """Format a timedelta into a human-readable Dutch string."""
    days = duration.days
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    time_parts = []
    if days > 0:
        time_parts.append(f"{days} dag{'en' if days != 1 else ''}")
    if hours > 0:
        time_parts.append(f"{hours} uur")
    if minutes > 0:
        time_parts.append(f"{minutes} minuten")

    return ", ".join(time_parts) if time_parts else "minder dan een minuut"
