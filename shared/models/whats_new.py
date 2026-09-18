from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from shared.definitions.whats_new import NewTone


class NewItem(BaseModel):
    id: str
    kind: str
    at: datetime
    value: str
    detail: str | None = None
    tone: str = NewTone.NEW.value
    status: int | None = None
    title: str | None = None
    tech: list[str] = Field(default_factory=list)
    ips: list[str] = Field(default_factory=list)
    source: str | None = None
    source_label: str | None = None
    screenshot_path: str | None = None
    severity: str | None = None
    is_kev: bool = False
    sensitive: bool = False
    asset_type: str | None = None
    query: str | None = None
    target_id: uuid.UUID | None = None
    target_value: str | None = None
    target_type: str | None = None
    scan_id: uuid.UUID | None = None
    watch_id: uuid.UUID | None = None
    host_id: uuid.UUID | None = None
    scope_id: uuid.UUID | None = None
    platform: str | None = None
    handle: str | None = None
    program_name: str | None = None
    program_url: str | None = None
    importable: bool = False
    target_exists: bool | None = None
    scanned: bool | None = None
    muted: bool = False


class NewSection(BaseModel):
    kind: str
    total: int
    items: list[NewItem] = Field(default_factory=list)


class NewSubject(BaseModel):
    kind: str
    id: str | None = None
    label: str
    target_id: uuid.UUID | None = None
    target_value: str | None = None
    target_type: str | None = None
    platform: str | None = None
    handle: str | None = None
    watched: bool = False
    watch_id: uuid.UUID | None = None


class NewGroup(BaseModel):
    id: str
    subject: NewSubject
    at: datetime
    counts: dict[str, int] = Field(default_factory=dict)
    sections: list[NewSection] = Field(default_factory=list)
    scan_id: uuid.UUID | None = None
    scan_started_at: datetime | None = None
    scan_status: str | None = None
    previous_scan_id: uuid.UUID | None = None
    retired: int = 0


class NewDay(BaseModel):
    date: str
    counts: dict[str, int] = Field(default_factory=dict)


class NewFeed(BaseModel):
    since: datetime
    until: datetime | None = None
    basis: str
    marked_at: datetime | None = None
    window: str | None = None
    counts: dict[str, int] = Field(default_factory=dict)
    facts: dict[str, dict[str, int]] = Field(default_factory=dict)
    daily: list[NewDay] = Field(default_factory=list)
    groups: list[NewGroup] = Field(default_factory=list)
    truncated: bool = False
    first_runs: int = 0


class NewMark(BaseModel):
    marked_at: datetime


class NewUnseen(BaseModel):
    count: int
    since: datetime | None = None
