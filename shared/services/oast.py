"""The instance's out-of-band settings, resolved into what a scanner is handed."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from shared.definitions.oast import (
    DEFAULT_WAIT_SECONDS,
    OastConfig,
    OastMode,
    normalize_server,
    off_reason,
)
from shared.enums.api_key import APIProvider
from shared.logging import get_logger
from shared.models.instance_settings import SINGLETON_KEY, InstanceSettings

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = get_logger(__name__)


def settings_row(session: Session | None) -> InstanceSettings | None:
    if session is None:
        return None
    return (
        session.execute(
            select(InstanceSettings).where(
                InstanceSettings.singleton_key == SINGLETON_KEY
            )
        )
        .scalars()
        .first()
    )


def config(session: Session | None) -> OastConfig:
    """The effective configuration. Off whenever the mode cannot be used."""
    row = settings_row(session)
    if row is None:
        return OastConfig(
            reason=off_reason(OastMode.OFF.value, server=None, acknowledged=False)
        )
    server = normalize_server(row.oast_server)
    reason = off_reason(
        row.oast_mode, server=server, acknowledged=row.oast_public_acknowledged
    )
    if reason is not None:
        return OastConfig(
            wait_seconds=row.oast_wait_seconds or DEFAULT_WAIT_SECONDS, reason=reason
        )
    token = None
    if row.oast_mode == OastMode.SELF_HOSTED.value:
        token = _token(session)
    return OastConfig(
        mode=row.oast_mode,
        server=server if row.oast_mode == OastMode.SELF_HOSTED.value else None,
        token=token,
        wait_seconds=row.oast_wait_seconds or DEFAULT_WAIT_SECONDS,
    )


def _token(session: Session) -> str | None:
    from shared.services.api_key.sync_api_key import SyncAPIKeyService  # noqa: PLC0415

    try:
        return SyncAPIKeyService(session).get_key_for_provider(APIProvider.INTERACTSH)
    except Exception:
        logger.warning("could not read the out-of-band token", exc_info=True)
        return None


__all__ = ["config", "settings_row"]
