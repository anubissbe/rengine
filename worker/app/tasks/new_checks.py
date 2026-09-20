"""Follow-up runs with the checks the library gained."""

from __future__ import annotations

from celery import shared_task

from app.config import settings
from app.database import get_sync_session
from shared.definitions.notifications import NewChecksSweep, new_checks_started
from shared.logging import get_logger
from shared.services import new_checks
from shared.services.notification_sync import SyncNotificationPublisher

logger = get_logger(__name__)


def _notify(session, result: new_checks.SweepResult) -> int:
    """One message per project that follows new checks."""
    sent = 0
    for project_id in sorted(result.projects(), key=str):
        payload = new_checks_started(
            NewChecksSweep(
                templates=result.templates,
                targets=result.started.get(project_id, 0),
                busy=result.busy.get(project_id, 0),
                waiting=result.waiting.get(project_id, 0),
                skipped=result.skipped.get(project_id, 0),
            )
        )
        if payload is None:
            continue
        try:
            SyncNotificationPublisher(settings.redis_url).publish(
                session=session,
                type=payload["type"],
                severity=payload["severity"],
                title=payload["title"],
                message=payload["message"],
                metadata=payload.get("metadata"),
                project_id=project_id,
            )
        except Exception:
            logger.warning("new checks notification failed", exc_info=True)
            continue
        sent += 1
    return sent


@shared_task(name="app.tasks.new_checks.sweep")
def sweep() -> dict:
    with get_sync_session() as session:
        result = new_checks.sweep(session)
        notified = _notify(session, result) if result.templates else 0
    return {
        "templates": result.templates,
        "targets": result.targets,
        "busy": sum(result.busy.values()),
        "waiting": sum(result.waiting.values()),
        "skipped": sum(result.skipped.values()),
        "failed": result.failed,
        "notified": notified,
    }
