"""Clock / time helper for the agent's get_current_time tool."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def now(tz_name: str = "UTC") -> dict:
    """Return current time in the requested timezone."""
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = timezone.utc
    now_utc = datetime.now(timezone.utc)
    local = now_utc.astimezone(tz)
    offset = local.utcoffset() or timedelta(0)
    return {
        "timezone": tz_name,
        "iso": local.isoformat(),
        "date": local.date().isoformat(),
        "time": local.time().isoformat(),
        "weekday": local.strftime("%A"),
        "utc_offset_minutes": int(offset.total_seconds() // 60),
        "unix": int(local.timestamp()),
    }
