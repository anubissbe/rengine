from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.changes import ChangeFeedService
from app.services.instance_settings import InstanceSettingsService
from shared.definitions.changes import CHANGE_FEED_LIMIT, CHANGE_WINDOWS, KIND_ORDER
from shared.definitions.mode_features import CAP_BOUNTY_PROGRAMS, has_capability
from shared.models.changes import ChangeFeed, ChangeMark

router = APIRouter(prefix="/changes", tags=["changes"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChangeFeedService:
    return ChangeFeedService(session)


ServiceDep = Annotated[ChangeFeedService, Depends(get_service)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=ChangeFeed)
async def change_feed(
    current_user: CurrentUser,
    service: ServiceDep,
    session: SessionDep,
    project_id: Annotated[UUID, Query(description="Project ID")],
    since: datetime | None = None,
    window: Annotated[str | None, Query(max_length=8)] = None,
    target_id: UUID | None = None,
    platform: Annotated[str | None, Query(max_length=32)] = None,
    handle: Annotated[str | None, Query(max_length=200)] = None,
    kinds: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=CHANGE_FEED_LIMIT)] = CHANGE_FEED_LIMIT,
) -> ChangeFeed:
    if window is not None and window not in CHANGE_WINDOWS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Window must be one of {', '.join(CHANGE_WINDOWS)}.",
        )
    wanted = {k.strip() for k in kinds.split(",") if k.strip()} if kinds else None
    if wanted and not wanted <= set(KIND_ORDER):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Kinds must be among {', '.join(KIND_ORDER)}.",
        )
    settings = await InstanceSettingsService(session).get_or_create()
    return await service.feed(
        project_id,
        current_user.id,
        since=since,
        window=window,
        target_id=target_id,
        platform=platform,
        handle=handle,
        kinds=wanted,
        programs=has_capability(settings.mode, CAP_BOUNTY_PROGRAMS),
        limit=limit,
    )


@router.post("/seen", response_model=ChangeMark)
async def mark_changes_seen(
    current_user: CurrentUser,
    service: ServiceDep,
    project_id: Annotated[UUID, Query(description="Project ID")],
) -> ChangeMark:
    return ChangeMark(marked_at=await service.mark_seen(current_user.id, project_id))
