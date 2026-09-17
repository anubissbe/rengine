"""What arrived in a project since a point in time."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, cast, exists, func, not_, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.services.scan import _host_seen_before
from shared.definitions.bounty_programs import event_spec
from shared.definitions.changes import (
    CHANGE_FEED_LIMIT,
    CHANGE_WINDOWS,
    DEFAULT_CHANGE_WINDOW,
    KIND_LABELS,
    KIND_ORDER,
    SOURCE_LABELS,
    ChangeBasis,
    ChangeKind,
    ChangeTone,
    change_kind_of_event,
    mark_key,
)
from shared.definitions.watch import ARRIVED_STATES, CT_SOURCE
from shared.enums.activity import ActivityEvent
from shared.models.activity_log import ActivityLog
from shared.models.bounty_program import BountyEventRow, BountyProgram, BountyScope
from shared.models.changes import ChangeFeed, ChangeItem
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.models.target import Target, TargetOrganization
from shared.models.user import User
from shared.models.watch import ProgramWatch, UserMark, WatchHost
from shared.services.scan_scope import census_only
from shared.utils.datetime import utc_now

WATCH_ADDED = "watch"
USER_ADDED = "user"


def _source_label(source: str | None) -> str | None:
    if not source:
        return None
    return SOURCE_LABELS.get(source, source)


class ChangeFeedService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------- marks ----------

    async def mark(self, user_id: UUID, project_id: UUID) -> datetime | None:
        return await self.session.scalar(
            select(UserMark.marked_at).where(
                UserMark.user_id == user_id, UserMark.key == mark_key(project_id)
            )
        )

    async def mark_seen(self, user_id: UUID, project_id: UUID) -> datetime:
        now = utc_now()
        stmt = pg_insert(UserMark).values(
            user_id=user_id, key=mark_key(project_id), marked_at=now
        )
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=["user_id", "key"], set_={"marked_at": now}
            )
        )
        await self.session.commit()
        return now

    # ---------- feed ----------

    async def feed(
        self,
        project_id: UUID,
        user_id: UUID,
        *,
        since: datetime | None = None,
        window: str | None = None,
        target_id: UUID | None = None,
        platform: str | None = None,
        handle: str | None = None,
        kinds: set[str] | None = None,
        programs: bool = True,
        limit: int = CHANGE_FEED_LIMIT,
    ) -> ChangeFeed:
        marked_at = await self.mark(user_id, project_id)
        if since is not None:
            basis, cutoff = ChangeBasis.MARK.value, since
        elif window:
            basis, cutoff = ChangeBasis.WINDOW.value, utc_now() - CHANGE_WINDOWS[window]
        elif marked_at is not None:
            basis, cutoff = ChangeBasis.MARK.value, marked_at
        else:
            window = DEFAULT_CHANGE_WINDOW
            basis, cutoff = ChangeBasis.WINDOW.value, utc_now() - CHANGE_WINDOWS[window]

        program = await self._program(platform, handle) if programs else None
        target_ids = await self._target_ids(project_id, target_id, program)
        target_value = await self._target_value(project_id, target_id)
        wanted = set(kinds) if kinds else set(KIND_ORDER)

        counts: dict[str, int] = dict.fromkeys(KIND_ORDER, 0)
        items: list[ChangeItem] = []
        truncated = False

        web_conds = self._web_asset_conds(project_id, cutoff, target_ids)
        counts[ChangeKind.WEB_ASSET.value] = await self._count(
            select(func.count()).select_from(Subdomain).where(*web_conds)
        )
        if ChangeKind.WEB_ASSET.value in wanted:
            rows, cut = await self._web_assets(web_conds, limit)
            items.extend(rows)
            truncated |= cut

        target_conds = self._target_conds(project_id, cutoff, target_ids)
        counts[ChangeKind.TARGET.value] = await self._count(
            select(func.count()).select_from(Target).where(*target_conds)
        )
        if ChangeKind.TARGET.value in wanted:
            rows, cut = await self._targets(target_conds, limit)
            items.extend(rows)
            truncated |= cut

        if programs:
            host_conds = self._host_conds(project_id, cutoff, target_ids, program)
            counts[ChangeKind.HOST.value] = await self._count(
                select(func.count())
                .select_from(WatchHost)
                .join(ProgramWatch, ProgramWatch.id == WatchHost.watch_id)
                .where(*host_conds)
            )
            if ChangeKind.HOST.value in wanted:
                rows, cut = await self._hosts(host_conds, limit)
                items.extend(rows)
                truncated |= cut

            event_conds = self._event_conds(project_id, cutoff, program, target_value)
            for kind, n in (await self._event_counts(event_conds)).items():
                counts[kind] = n
            event_kinds = wanted & {
                ChangeKind.SCOPE_ADDED.value,
                ChangeKind.SCOPE_REMOVED.value,
                ChangeKind.PROGRAM.value,
            }
            if event_kinds:
                rows, cut = await self._events(event_conds, event_kinds, limit)
                items.extend(rows)
                truncated |= cut

        items.sort(key=lambda i: i.at, reverse=True)
        if len(items) > limit:
            truncated = True
            items = items[:limit]
        return ChangeFeed(
            since=cutoff,
            basis=basis,
            marked_at=marked_at,
            window=window if basis == ChangeBasis.WINDOW.value else None,
            counts=counts,
            items=items,
            truncated=truncated,
        )

    # ---------- scope ----------

    async def _program(self, platform: str | None, handle: str | None):
        if not platform or not handle:
            return None
        return await self.session.scalar(
            select(BountyProgram).where(
                BountyProgram.platform == platform, BountyProgram.handle == handle
            )
        )

    async def _target_value(self, project_id: UUID, target_id: UUID | None):
        if target_id is None:
            return None
        return await self.session.scalar(
            select(Target.target_value).where(
                Target.id == target_id, Target.project_id == project_id
            )
        )

    async def _target_ids(
        self, project_id: UUID, target_id: UUID | None, program
    ) -> list[UUID] | None:
        if target_id is not None:
            return [target_id]
        if program is None:
            return None
        by_scope = select(Target.id).where(
            Target.project_id == project_id,
            Target.target_value.in_(
                select(BountyScope.target_value).where(
                    BountyScope.program_id == program.id,
                    BountyScope.target_value.is_not(None),
                )
            ),
        )
        by_org = (
            select(TargetOrganization.target_id)
            .join(Target, Target.id == TargetOrganization.target_id)
            .where(
                Target.project_id == project_id,
                TargetOrganization.organization_id.in_(
                    select(ProgramWatch.organization_id).where(
                        ProgramWatch.project_id == project_id,
                        ProgramWatch.program_id == program.id,
                        ProgramWatch.organization_id.is_not(None),
                    )
                ),
            )
        )
        rows = await self.session.execute(by_scope.union(by_org))
        return [r[0] for r in rows.all()]

    # ---------- web assets ----------

    @staticmethod
    def _web_asset_conds(project_id: UUID, since: datetime, target_ids):
        earlier = aliased(Scan)
        scans = select(Scan.id).where(
            Scan.project_id == project_id,
            census_only(),
            or_(Scan.completed_at.is_(None), Scan.completed_at >= since),
            exists(
                select(1).where(
                    earlier.target_id == Scan.target_id,
                    earlier.id != Scan.id,
                    census_only(earlier),
                    earlier.started_at < Scan.started_at,
                )
            ),
        )
        if target_ids is not None:
            scans = scans.where(Scan.target_id.in_(target_ids))
        return [
            Subdomain.scan_id.in_(scans),
            Subdomain.discovered_at >= since,
            not_(_host_seen_before()),
            not_(cast(Subdomain.sources, JSONB).contains([CT_SOURCE])),
        ]

    async def _web_assets(self, conds, limit: int):
        rows = (
            await self.session.execute(
                select(Subdomain, Target.target_value)
                .join(Target, Target.id == Subdomain.target_id)
                .where(*conds)
                .order_by(Subdomain.discovered_at.desc(), Subdomain.name)
                .limit(limit + 1)
            )
        ).all()
        items = []
        for s, target_value in rows[:limit]:
            source = (s.sources or [None])[0]
            detail = None
            if s.http_status is not None:
                detail = f"{s.http_status}" + (
                    f" · {s.page_title}" if s.page_title else ""
                )
            items.append(
                ChangeItem(
                    id=f"{ChangeKind.WEB_ASSET.value}:{s.id}",
                    at=s.discovered_at,
                    kind=ChangeKind.WEB_ASSET.value,
                    label=KIND_LABELS[ChangeKind.WEB_ASSET.value],
                    value=s.name,
                    detail=detail,
                    source=source,
                    source_label=_source_label(source),
                    tone=ChangeTone.NEW.value,
                    target_id=s.target_id,
                    target_value=target_value,
                    scan_id=s.scan_id,
                )
            )
        return items, len(rows) > limit

    # ---------- targets ----------

    @staticmethod
    def _target_conds(project_id: UUID, since: datetime, target_ids):
        conds = [Target.project_id == project_id, Target.created_at >= since]
        if target_ids is not None:
            conds.append(Target.id.in_(target_ids))
        return conds

    async def _targets(self, conds, limit: int):
        created = ActivityLog.event_type == ActivityEvent.TARGET_CREATED
        rows = (
            await self.session.execute(
                select(Target, ActivityLog.user_id, User.username)
                .outerjoin(
                    ActivityLog, and_(ActivityLog.target_id == Target.id, created)
                )
                .outerjoin(User, User.id == ActivityLog.user_id)
                .where(*conds)
                .order_by(Target.created_at.desc(), Target.target_value)
                .limit(limit + 1)
            )
        ).all()
        items = []
        seen: set[UUID] = set()
        for t, logged_by, username in rows:
            if t.id in seen:
                continue
            seen.add(t.id)
            source = USER_ADDED if logged_by is not None else WATCH_ADDED
            items.append(
                ChangeItem(
                    id=f"{ChangeKind.TARGET.value}:{t.id}",
                    at=t.created_at,
                    kind=ChangeKind.TARGET.value,
                    label=KIND_LABELS[ChangeKind.TARGET.value],
                    value=t.target_value,
                    detail=f"Added by {username}" if username else None,
                    source=source,
                    source_label=_source_label(source),
                    tone=ChangeTone.NEW.value,
                    target_id=t.id,
                    target_value=t.target_value,
                )
            )
        return items[:limit], len(rows) > limit

    # ---------- watch hosts ----------

    @staticmethod
    def _host_conds(project_id: UUID, since: datetime, target_ids, program):
        conds = [
            WatchHost.project_id == project_id,
            WatchHost.first_seen_at >= since,
            WatchHost.state.in_(list(ARRIVED_STATES)),
        ]
        if target_ids is not None:
            conds.append(WatchHost.target_id.in_(target_ids))
        if program is not None:
            conds.append(ProgramWatch.program_id == program.id)
        return conds

    async def _hosts(self, conds, limit: int):
        rows = (
            await self.session.execute(
                select(
                    WatchHost,
                    BountyProgram.platform,
                    BountyProgram.handle,
                    BountyProgram.name,
                    Target.target_value,
                )
                .join(ProgramWatch, ProgramWatch.id == WatchHost.watch_id)
                .join(BountyProgram, BountyProgram.id == ProgramWatch.program_id)
                .join(Target, Target.id == WatchHost.target_id)
                .where(*conds)
                .order_by(WatchHost.first_seen_at.desc(), WatchHost.name)
                .limit(limit + 1)
            )
        ).all()
        items = []
        for h, platform, handle, program_name, target_value in rows[:limit]:
            detail = None
            if h.status_code is not None:
                detail = f"{h.status_code}" + (f" · {h.title}" if h.title else "")
            elif h.resolved_ips:
                detail = ", ".join(h.resolved_ips[:3])
            items.append(
                ChangeItem(
                    id=f"{ChangeKind.HOST.value}:{h.id}",
                    at=h.first_seen_at,
                    kind=ChangeKind.HOST.value,
                    label=KIND_LABELS[ChangeKind.HOST.value],
                    value=h.name,
                    detail=detail,
                    source=CT_SOURCE,
                    source_label=_source_label(CT_SOURCE),
                    tone=ChangeTone.NEW.value,
                    target_id=h.target_id,
                    target_value=target_value,
                    scan_id=h.scan_id,
                    watch_id=h.watch_id,
                    platform=platform,
                    handle=handle,
                    program_name=program_name,
                )
            )
        return items, len(rows) > limit

    # ---------- program events ----------

    @staticmethod
    def _event_conds(project_id: UUID, since: datetime, program, target_value):
        conds = [BountyEventRow.created_at >= since]
        if program is not None:
            conds.append(BountyEventRow.program_id == program.id)
        else:
            conds.append(
                BountyEventRow.program_id.in_(
                    select(ProgramWatch.program_id).where(
                        ProgramWatch.project_id == project_id
                    )
                )
            )
        if target_value:
            conds.append(
                BountyEventRow.asset_identifier.in_([target_value, f"*.{target_value}"])
            )
        return conds

    async def _event_counts(self, conds) -> dict[str, int]:
        rows = (
            await self.session.execute(
                select(BountyEventRow.kind, func.count())
                .where(*conds)
                .group_by(BountyEventRow.kind)
            )
        ).all()
        out = {
            ChangeKind.SCOPE_ADDED.value: 0,
            ChangeKind.SCOPE_REMOVED.value: 0,
            ChangeKind.PROGRAM.value: 0,
        }
        for kind, n in rows:
            out[change_kind_of_event(kind)] += int(n)
        return out

    async def _events(self, conds, kinds: set[str], limit: int):
        rows = (
            await self.session.execute(
                select(BountyEventRow, BountyProgram.source)
                .join(BountyProgram, BountyProgram.id == BountyEventRow.program_id)
                .where(*conds)
                .order_by(BountyEventRow.created_at.desc())
                .limit(limit + 1)
            )
        ).all()
        items = []
        for e, source in rows:
            kind = change_kind_of_event(e.kind)
            if kind not in kinds:
                continue
            spec = event_spec(e.kind)
            scoped = kind != ChangeKind.PROGRAM.value
            items.append(
                ChangeItem(
                    id=f"{kind}:{e.id}",
                    at=e.created_at,
                    kind=kind,
                    label=spec.label if not scoped else KIND_LABELS[kind],
                    value=(e.asset_identifier or e.program_name)
                    if scoped
                    else e.program_name,
                    detail=(e.asset_type if scoped else e.detail) or None,
                    source=source,
                    source_label=_source_label(source),
                    tone=spec.tone,
                    platform=e.platform,
                    handle=e.handle,
                    program_name=e.program_name,
                )
            )
        return items[:limit], len(rows) > limit

    # ---------- helpers ----------

    async def _count(self, stmt) -> int:
        return int(await self.session.scalar(stmt) or 0)
