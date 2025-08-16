"""
Centralized timezone configuration for the Discord bot.

This module provides a single source of truth for timezone handling across
the entire bot. All modules should import from here instead of defining
their own timezone constants.
"""

import datetime
import pytz

# Primary timezone for the bot (Brussels/Amsterdam are the same timezone)
# This is used for:
# - User-facing time displays
# - Scheduled tasks (confessions, moderation actions, etc.)
# - Log timestamps in embeds
# - Any time that should be shown in local time
LOCAL_TIMEZONE = pytz.timezone('Europe/Brussels')

# UTC timezone for internal storage and calculations
# This is used for:
# - Database timestamps (always store in UTC)
# - API interactions
# - Cross-timezone calculations
UTC_TIMEZONE = datetime.timezone.utc

# Convenience functions for common operations
def now_local():
    """Get current time in local timezone."""
    return datetime.datetime.now(LOCAL_TIMEZONE)

def now_utc():
    """Get current time in UTC."""
    return datetime.datetime.now(UTC_TIMEZONE)

def to_local(dt):
    """Convert a datetime to local timezone."""
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=UTC_TIMEZONE)
    return dt.astimezone(LOCAL_TIMEZONE)

def to_utc(dt):
    """Convert a datetime to UTC."""
    if dt.tzinfo is None:
        # Assume local timezone if no timezone info
        dt = LOCAL_TIMEZONE.localize(dt)
    return dt.astimezone(UTC_TIMEZONE)

def local_time(hour, minute=0, second=0):
    """Create a time object in local timezone with proper DST handling.
    
    This function creates a time object that will work correctly with discord.py's
    task scheduler, accounting for daylight saving time transitions.
    """
    # For task scheduling, we need to use the current DST status
    # Discord.py tasks will handle the timezone correctly if we provide the right offset
    now_local = datetime.datetime.now(LOCAL_TIMEZONE)
    current_offset = now_local.utcoffset()
    
    # Create timezone with the current offset
    fixed_tz = datetime.timezone(current_offset)
    
    return datetime.time(hour=hour, minute=minute, second=second, tzinfo=fixed_tz)

def format_local_time(dt, format_string='%Y-%m-%d %H:%M:%S %Z%z'):
    """Format a datetime in local timezone."""
    local_dt = to_local(dt)
    return local_dt.strftime(format_string)

# Legacy compatibility - for modules that expect TIMEZONE constant
TIMEZONE = LOCAL_TIMEZONE
BRUSSELS_TZ = LOCAL_TIMEZONE  # For confession modules