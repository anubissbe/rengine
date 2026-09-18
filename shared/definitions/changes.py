"""What is new to hunt: surface the world added, never what the operator did."""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum

from shared.definitions.bounty_programs import BountyEvent


class ChangeKind(StrEnum):
    SCANNED_ASSET = "scanned_asset"
    SCOPE_ASSET = "scope_asset"
    PROGRAM = "program"
    WATCH_HOST = "watch_host"
    TARGET = "target"


KIND_ORDER: tuple[str, ...] = tuple(k.value for k in ChangeKind)

KIND_LABELS: dict[str, str] = {
    ChangeKind.SCANNED_ASSET.value: "New scanned asset",
    ChangeKind.SCOPE_ASSET.value: "New in-scope asset",
    ChangeKind.PROGRAM.value: "New program",
    ChangeKind.WATCH_HOST.value: "New watched host",
    ChangeKind.TARGET.value: "New target",
}

BOUNTY_KINDS: frozenset[str] = frozenset(
    {
        ChangeKind.SCOPE_ASSET.value,
        ChangeKind.PROGRAM.value,
        ChangeKind.WATCH_HOST.value,
        ChangeKind.TARGET.value,
    }
)


class ChangeBasis(StrEnum):
    MARK = "mark"
    WINDOW = "window"


class ChangeTone(StrEnum):
    NEW = "new"
    HOT = "hot"
    NEUTRAL = "neutral"


SOURCE_LABELS: dict[str, str] = {
    "ct_log": "Certificate log",
    "watch": "Program watch",
    "scope": "Program scope",
    "api": "Platform API",
    "feed": "Public feed",
}

CHANGE_WINDOWS: dict[str, timedelta] = {
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}
DEFAULT_CHANGE_WINDOW = "30d"
CHANGE_FEED_LIMIT = 300

EVENT_TONES: dict[str, str] = {
    "info": ChangeTone.NEW.value,
    "warning": ChangeTone.HOT.value,
    "muted": ChangeTone.NEUTRAL.value,
}

SCOPE_EVENTS: frozenset[str] = frozenset(
    {BountyEvent.SCOPE_ADDED.value, BountyEvent.CAME_INTO_SCOPE.value}
)
PROGRAM_EVENTS: frozenset[str] = frozenset(
    {
        BountyEvent.PROGRAM_ADDED.value,
        BountyEvent.PROGRAM_WENT_PUBLIC.value,
        BountyEvent.SUBMISSIONS_OPENED.value,
        BountyEvent.BOUNTIES_STARTED.value,
    }
)
NEW_EVENTS: frozenset[str] = SCOPE_EVENTS | PROGRAM_EVENTS


def event_kinds_for(kinds: set[str]) -> set[str]:
    out: set[str] = set()
    if ChangeKind.SCOPE_ASSET.value in kinds:
        out |= SCOPE_EVENTS
    if ChangeKind.PROGRAM.value in kinds:
        out |= PROGRAM_EVENTS
    return out


def change_kind_of_event(kind: str) -> str | None:
    if kind in SCOPE_EVENTS:
        return ChangeKind.SCOPE_ASSET.value
    if kind in PROGRAM_EVENTS:
        return ChangeKind.PROGRAM.value
    return None


def mark_key(project_id) -> str:
    return f"changes:{project_id}"
