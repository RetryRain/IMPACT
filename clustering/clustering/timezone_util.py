from __future__ import annotations

from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def to_ist_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=IST)
    return value.astimezone(IST).replace(microsecond=0).isoformat()
