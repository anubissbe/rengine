from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from shared.definitions.changes import ChangeTone


class ChangeItem(BaseModel):
    id: str
    at: datetime
    kind: str
    label: str
    value: str
    detail: str | None = None
    source: str | None = None
    source_label: str | None = None
    tone: str = ChangeTone.NEUTRAL.value
    target_id: uuid.UUID | None = None
    target_value: str | None = None
    scan_id: uuid.UUID | None = None
    watch_id: uuid.UUID | None = None
    platform: str | None = None
    handle: str | None = None
    program_name: str | None = None


class ChangeFeed(BaseModel):
    since: datetime
    basis: str
    marked_at: datetime | None = None
    window: str | None = None
    counts: dict[str, int] = Field(default_factory=dict)
    items: list[ChangeItem] = Field(default_factory=list)
    truncated: bool = False


class ChangeMark(BaseModel):
    marked_at: datetime
