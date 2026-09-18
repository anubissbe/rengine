"""What is new: surface that appeared since the operator last caught up."""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum

from shared.definitions.bounty_programs import BountyEvent
from shared.definitions.correlation import SCREENSHOT_DISTANCE
from shared.definitions.surface import SurfaceDimension


class NewKind(StrEnum):
    WEB_ASSET = "web_asset"
    SERVICE = "service"
    FINDING = "finding"
    SECRET = "secret"  # noqa: S105
    SCOPE = "scope"
    PROGRAM = "program"
    CERT_HOST = "cert_host"
    TARGET = "target"
    OUT_OF_SCOPE = "out_of_scope"
    RETIRED = "retired"


KIND_ORDER: tuple[str, ...] = tuple(k.value for k in NewKind)

KIND_LABELS: dict[str, str] = {
    NewKind.WEB_ASSET.value: "Web assets",
    NewKind.SERVICE.value: "Services",
    NewKind.FINDING.value: "Findings",
    NewKind.SECRET.value: "Secrets",
    NewKind.SCOPE.value: "In scope",
    NewKind.PROGRAM.value: "Programs",
    NewKind.CERT_HOST.value: "Certificate hosts",
    NewKind.TARGET.value: "Targets",
    NewKind.OUT_OF_SCOPE.value: "Out of scope",
    NewKind.RETIRED.value: "Retired",
}

SCAN_KINDS: tuple[str, ...] = (
    NewKind.WEB_ASSET.value,
    NewKind.SERVICE.value,
    NewKind.FINDING.value,
    NewKind.SECRET.value,
)
BOUNTY_KINDS: frozenset[str] = frozenset(
    {
        NewKind.SCOPE.value,
        NewKind.PROGRAM.value,
        NewKind.CERT_HOST.value,
        NewKind.TARGET.value,
        NewKind.OUT_OF_SCOPE.value,
    }
)
GONE_KINDS: frozenset[str] = frozenset(
    {NewKind.OUT_OF_SCOPE.value, NewKind.RETIRED.value}
)

KIND_DIMENSION: dict[str, str] = {
    NewKind.WEB_ASSET.value: SurfaceDimension.WEB_ASSETS.value,
    NewKind.SERVICE.value: SurfaceDimension.SERVICES.value,
    NewKind.FINDING.value: SurfaceDimension.VULNERABILITIES.value,
    NewKind.SECRET.value: SurfaceDimension.SECRETS.value,
}


class NewBasis(StrEnum):
    MARK = "mark"
    WINDOW = "window"
    DAYS = "days"


class SubjectKind(StrEnum):
    RUN = "run"
    PROGRAM = "program"
    LIBRARY = "library"
    TARGETS = "targets"


class ProgramRing(StrEnum):
    ENGAGED = "engaged"
    LIBRARY = "library"


class NewTone(StrEnum):
    NEW = "new"
    HOT = "hot"
    NEUTRAL = "neutral"


NEW_WINDOWS: dict[str, timedelta] = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}
DEFAULT_NEW_WINDOW = "7d"
GRID_DAYS = 91
ROWS_PER_SECTION = 5
BOUNTY_ROWS_PER_SECTION = 50
GROUP_LIMIT = 80
MAX_TEXT_FILTER = 200

SOURCE_LABELS: dict[str, str] = {
    "ct_log": "Certificate log",
    "watch": "Program watch",
    "scope": "Program scope",
    "api": "Platform API",
    "feed": "Public feed",
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
GONE_EVENTS: frozenset[str] = frozenset(
    {BountyEvent.SCOPE_REMOVED.value, BountyEvent.WENT_OUT_OF_SCOPE.value}
)

EVENT_KIND: dict[str, str] = {
    **dict.fromkeys(SCOPE_EVENTS, NewKind.SCOPE.value),
    **dict.fromkeys(PROGRAM_EVENTS, NewKind.PROGRAM.value),
    **dict.fromkeys(GONE_EVENTS, NewKind.OUT_OF_SCOPE.value),
}


class NewTab(StrEnum):
    NEW = "new"
    VISUAL = "visual"


VISUAL_DISTANCE = SCREENSHOT_DISTANCE
VISUAL_LIMIT = 300
VISUAL_FIELDS: tuple[str, ...] = ("http_status", "page_title", "tech", "webserver")
VISUAL_FIELD_LABELS: dict[str, str] = {
    "http_status": "Status",
    "page_title": "Title",
    "tech": "Technology",
    "webserver": "Server",
}


class Fact(StrEnum):
    SENSITIVE = "sensitive"
    CRITICAL = "critical"
    KEV = "kev"
    NOT_TARGET = "not_target"
    ANSWERING = "answering"
    NOT_SCANNED = "not_scanned"
    TARGETS = "targets"
    RUNS = "runs"


def mark_key(project_id) -> str:
    return f"whats_new:{project_id}"
