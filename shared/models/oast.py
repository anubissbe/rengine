"""Out-of-band settings as the API reads and writes them."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField

from shared.definitions.oast import (
    MAX_SERVER_LENGTH,
    MAX_WAIT_SECONDS,
    MIN_WAIT_SECONDS,
    OastMode,
)


class OastRead(BaseModel):
    mode: str = OastMode.OFF.value
    server: str | None = None
    wait_seconds: int = 0
    public_acknowledged: bool = False
    token_set: bool = False
    public_servers: list[str] = PydanticField(default_factory=list)
    checks: int = 0
    reason: str | None = None
    last_interaction_at: datetime | None = None
    interactions: int = 0


class OastUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: OastMode | None = None
    server: str | None = PydanticField(default=None, max_length=MAX_SERVER_LENGTH)
    wait_seconds: int | None = PydanticField(
        default=None, ge=MIN_WAIT_SECONDS, le=MAX_WAIT_SECONDS
    )
    public_acknowledged: bool | None = None


class OastTest(BaseModel):
    ok: bool = False
    detail: str = ""
    address: str | None = None
    status_code: int | None = None


__all__ = ["OastRead", "OastTest", "OastUpdate"]
