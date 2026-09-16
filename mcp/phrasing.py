"""Short spellings for a chat screen."""

from __future__ import annotations

SHORT_ID = 8


def short_id(value: object) -> str:
    return str(value)[:SHORT_ID]


def elapsed(seconds: float | None) -> str:
    if seconds is None:
        return ""
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def stamp(value) -> str:
    """Date and minute, from a datetime or an ISO string."""
    text = "" if value is None else str(value)
    return text[:16].replace("T", " ")


def number(value: int | None) -> str:
    return "" if value is None else f"{value:,}"
