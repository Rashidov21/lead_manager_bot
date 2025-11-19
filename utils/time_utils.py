"""
Time utility functions for handling timezone conversions and time calculations.
All timestamps are stored and processed in UTC.
"""
from datetime import datetime, timedelta
from typing import Optional
import pytz

UTC = pytz.UTC


def now_utc() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(UTC)


def parse_datetime(dt_string: Optional[str]) -> Optional[datetime]:
    """
    Parse datetime string from Google Sheets.
    Handles various formats that Google Sheets might return.
    """
    if not dt_string or dt_string.strip() == "":
        return None

    # Common formats from Google Sheets
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
    ]

    dt_string = dt_string.strip()

    for fmt in formats:
        try:
            dt = datetime.strptime(dt_string, fmt)
            # Assume UTC if no timezone info
            if dt.tzinfo is None:
                dt = UTC.localize(dt)
            return dt
        except ValueError:
            continue

    # Try parsing as ISO format
    try:
        dt = datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = UTC.localize(dt)
        return dt
    except (ValueError, AttributeError):
        pass

    return None


def format_datetime(dt: Optional[datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string for Google Sheets."""
    if dt is None:
        return ""

    # Convert to UTC if not already
    if dt.tzinfo is None:
        dt = UTC.localize(dt)
    else:
        dt = dt.astimezone(UTC)

    return dt.strftime(format_str)


def add_hours(dt: datetime, hours: float) -> datetime:
    """Add hours to a datetime."""
    return dt + timedelta(hours=hours)


def add_seconds(dt: datetime, seconds: float) -> datetime:
    """Add seconds to a datetime."""
    return dt + timedelta(seconds=seconds)


def time_until(dt: datetime) -> timedelta:
    """Calculate time difference from now until given datetime."""
    return dt - now_utc()


def is_past(dt: datetime) -> bool:
    """Check if datetime is in the past."""
    return dt < now_utc()


def is_future(dt: datetime) -> bool:
    """Check if datetime is in the future."""
    return dt > now_utc()


def hours_between(dt1: datetime, dt2: datetime) -> float:
    """Calculate hours between two datetimes."""
    delta = dt2 - dt1
    return delta.total_seconds() / 3600


def days_between(dt1: datetime, dt2: datetime) -> float:
    """Calculate days between two datetimes."""
    delta = dt2 - dt1
    return delta.total_seconds() / 86400


def round_to_minute(dt: datetime) -> datetime:
    """Round datetime to the nearest minute."""
    return dt.replace(second=0, microsecond=0)

