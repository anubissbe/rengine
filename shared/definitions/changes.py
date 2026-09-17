"""What the project change feed reports."""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum

from shared.definitions.bounty_programs import BountyEvent


class ChangeKind(StrEnum):
    WEB_ASSET = "web_asset"
    HOST = "host"
    SCOPE_ADDED = "scope_added"
    SCOPE_REMOVED = "scope_removed"
    PROGRAM = "program"
    TARGET = "target"


KIND_ORDER: tuple[str, ...] = tuple(k.value for k in ChangeKind)

KIND_LABELS: dict[str, str] = {
    ChangeKind.WEB_ASSET.value: "New web asset",
    ChangeKind.HOST.value: "New in-scope host",
    ChangeKind.SCOPE_ADDED.value: "Came into scope",
    ChangeKind.SCOPE_REMOVED.value: "Left scope",
    ChangeKind.PROGRAM.value: "Program update",
    ChangeKind.TARGET.value: "New target",
}


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
    "user": "Manual",
    "api": "Platform API",
    "feed": "Public feed",
    "imported": "Imported",
    "target": "Target seed",
}

CHANGE_WINDOWS: dict[str, timedelta] = {
    "24h": timedelta(days=1),
    "7d": timedelta(days=7),
    "14d": timedelta(days=14),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}
DEFAULT_CHANGE_WINDOW = "7d"
CHANGE_FEED_LIMIT = 300

SCOPE_IN_EVENTS: frozenset[str] = frozenset(
    {BountyEvent.SCOPE_ADDED.value, BountyEvent.CAME_INTO_SCOPE.value}
)
SCOPE_OUT_EVENTS: frozenset[str] = frozenset(
    {BountyEvent.SCOPE_REMOVED.value, BountyEvent.WENT_OUT_OF_SCOPE.value}
)


def change_kind_of_event(kind: str) -> str:
    if kind in SCOPE_IN_EVENTS:
        return ChangeKind.SCOPE_ADDED.value
    if kind in SCOPE_OUT_EVENTS:
        return ChangeKind.SCOPE_REMOVED.value
    return ChangeKind.PROGRAM.value


def mark_key(project_id) -> str:
    return f"changes:{project_id}"
