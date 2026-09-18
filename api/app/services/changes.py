"""What is new to hunt in a project since a point in time."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID

from sqlalchemy import cast, exists, func, not_, or_, select
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
    EVENT_TONES,
    KIND_LABELS,
    KIND_ORDER,
    NEW_EVENTS,
    SOURCE_LABELS,
    ChangeBasis,
    ChangeKind,
    ChangeTone,
    change_kind_of_event,
    event_kinds_for,
    mark_key,
)
from shared.definitions.watch import ARRIVED_STATES, CT_SOURCE
from shared.models.bounty_program import BountyEventRow, BountyProgram, BountyScope
from shared.models.changes import ChangeDay, ChangeFeed, ChangeItem
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.models.target import Target, TargetOrganization
from shared.models.watch import ProgramWatch, UserMark, WatchHost
from shared.services.scan_scope import census_only
from shared.utils.datetime import utc_now

WATCH_SOURCE = "watch"
SCOPE_SOURCE = "scope"


def _source_label(source: str | None) -> str | None:
    if not source:
        return None
    return SOURCE_LABELS.get(source, source)


class _Tally:
    """Counts, per-day buckets and the rows a feed answers with."""

    def __init__(self, limit: int):
        self.limit = limit
        self.counts: dict[str, int] = dict.fromkeys(KIND_ORDER, 0)
        self.daily: dict[str, dict[str, int]] = {}
        self.items: list[ChangeItem] = []
        self.truncated = False

    def count(self, kind: str, total: int, by_day) -> None:
        self.counts[kind] = total
        for day, n in by_day:
            self.daily.setdefault(str(day), {})[kind] = n

    def bump(self, kind: str, day, n: int) -> None:
        self.counts[kind] += n
        bucket = self.daily.setdefault(str(day), {})
        bucket[kind] = bucket.get(kind, 0) + n

    def add(self, rows: list[ChangeItem], cut: bool) -> None:
        self.items.extend(rows)
        self.truncated |= cut

    def rows(self) -> list[ChangeItem]:
        self.items.sort(key=lambda i: i.at, reverse=True)
        if len(self.items) > self.limit:
            self.truncated = True
            self.items = self.items[: self.limit]
        return self.items


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
        tally = _Tally(limit)

        scanned = self._scanned_conds(project_id, cutoff, target_ids)
        tally.count(
            ChangeKind.SCANNED_ASSET.value,
            await self._count(
                select(func.count()).select_from(Subdomain).where(*scanned)
            ),
            await self._by_day(Subdomain.discovered_at, Subdomain, scanned),
        )
        if ChangeKind.SCANNED_ASSET.value in wanted:
            tally.add(*await self._scanned(scanned, limit))

        if programs:
            await self._bounty(
                tally, wanted, project_id, cutoff, target_ids, target_value, program
            )

        return ChangeFeed(
            since=cutoff,
            basis=basis,
            marked_at=marked_at,
            window=window if basis == ChangeBasis.WINDOW.value else None,
            counts=tally.counts,
            daily=self._days(cutoff, tally.daily),
            items=tally.rows(),
            truncated=tally.truncated,
        )

    async def _bounty(
        self, tally, wanted, project_id, cutoff, target_ids, target_value, program
    ) -> None:
        limit = tally.limit
        hosts = self._host_conds(project_id, cutoff, target_ids, program)
        host_join = (ProgramWatch, ProgramWatch.id == WatchHost.watch_id)
        tally.count(
            ChangeKind.WATCH_HOST.value,
            await self._count(
                select(func.count())
                .select_from(WatchHost)
                .join(*host_join)
                .where(*hosts)
            ),
            await self._by_day(
                WatchHost.first_seen_at, WatchHost, hosts, join=host_join
            ),
        )
        if ChangeKind.WATCH_HOST.value in wanted:
            tally.add(*await self._hosts(hosts, limit))

        targets = self._target_conds(project_id, cutoff, target_ids)
        tally.count(
            ChangeKind.TARGET.value,
            await self._count(select(func.count()).select_from(Target).where(*targets)),
            await self._by_day(Target.created_at, Target, targets),
        )
        if ChangeKind.TARGET.value in wanted:
            tally.add(*await self._targets(project_id, targets, limit))

        events = self._event_conds(project_id, cutoff, program, target_value)
        by_kind = (
            await self.session.execute(
                select(
                    BountyEventRow.kind,
                    func.date(BountyEventRow.created_at),
                    func.count(),
                )
                .where(*events)
                .group_by(BountyEventRow.kind, func.date(BountyEventRow.created_at))
            )
        ).all()
        for kind, day, n in by_kind:
            change_kind = change_kind_of_event(kind)
            if change_kind is not None:
                tally.bump(change_kind, day, int(n))
        event_kinds = event_kinds_for(wanted)
        if event_kinds:
            tally.add(*await self._events(events, event_kinds, limit))

    @staticmethod
    def _days(cutoff: datetime, daily: dict[str, dict[str, int]]) -> list[ChangeDay]:
        day = cutoff.date()
        end = utc_now().date()
        out: list[ChangeDay] = []
        while day <= end:
            key = day.isoformat()
            out.append(ChangeDay(date=key, counts=daily.get(key, {})))
            day += timedelta(days=1)
        return out

    async def _by_day(self, column, model, conds, join=None) -> list[tuple[date, int]]:
        stmt = select(func.date(column), func.count()).select_from(model)
        if join is not None:
            stmt = stmt.join(*join)
        rows = await self.session.execute(
            stmt.where(*conds).group_by(func.date(column))
        )
        return [(d, int(n)) for d, n in rows.all()]

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

    @staticmethod
    def _watched_programs(project_id: UUID):
        return select(ProgramWatch.program_id).where(
            ProgramWatch.project_id == project_id
        )

    @staticmethod
    def _covering_programs(project_id: UUID):
        return (
            select(BountyScope.program_id)
            .join(Target, Target.target_value == BountyScope.target_value)
            .where(Target.project_id == project_id)
        )

    def _engaged_programs(self, project_id: UUID):
        return self._watched_programs(project_id).union(
            self._covering_programs(project_id)
        )

    @staticmethod
    def _watch_targets(project_id: UUID):
        return (
            select(TargetOrganization.target_id)
            .join(Target, Target.id == TargetOrganization.target_id)
            .where(
                Target.project_id == project_id,
                TargetOrganization.organization_id.in_(
                    select(ProgramWatch.organization_id).where(
                        ProgramWatch.project_id == project_id,
                        ProgramWatch.organization_id.is_not(None),
                    )
                ),
            )
        )

    @staticmethod
    def _scope_targets(project_id: UUID, program_id: UUID | None = None):
        scopes = select(BountyScope.target_value).where(
            BountyScope.target_value.is_not(None)
        )
        if program_id is not None:
            scopes = scopes.where(BountyScope.program_id == program_id)
        return select(Target.id).where(
            Target.project_id == project_id, Target.target_value.in_(scopes)
        )

    async def _target_ids(
        self, project_id: UUID, target_id: UUID | None, program
    ) -> list[UUID] | None:
        if target_id is not None:
            return [target_id]
        if program is None:
            return None
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
        rows = await self.session.execute(
            self._scope_targets(project_id, program.id).union(by_org)
        )
        return [r[0] for r in rows.all()]

    # ---------- scanned assets ----------

    @staticmethod
    def _scanned_conds(project_id: UUID, since: datetime, target_ids):
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

    async def _scanned(self, conds, limit: int):
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
                    id=f"{ChangeKind.SCANNED_ASSET.value}:{s.id}",
                    at=s.discovered_at,
                    kind=ChangeKind.SCANNED_ASSET.value,
                    label=KIND_LABELS[ChangeKind.SCANNED_ASSET.value],
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

    # ---------- targets from bounty hub ----------

    def _target_conds(self, project_id: UUID, since: datetime, target_ids):
        conds = [
            Target.project_id == project_id,
            Target.created_at >= since,
            or_(
                Target.id.in_(self._watch_targets(project_id)),
                Target.id.in_(self._scope_targets(project_id)),
            ),
        ]
        if target_ids is not None:
            conds.append(Target.id.in_(target_ids))
        return conds

    async def _targets(self, project_id: UUID, conds, limit: int):
        rows = (
            await self.session.execute(
                select(Target)
                .where(*conds)
                .order_by(Target.created_at.desc(), Target.target_value)
                .limit(limit + 1)
            )
        ).all()
        targets = [r[0] for r in rows[:limit]]
        if not targets:
            return [], False
        watched = {
            r[0]
            for r in (
                await self.session.execute(
                    self._watch_targets(project_id).where(
                        TargetOrganization.target_id.in_([t.id for t in targets])
                    )
                )
            ).all()
        }
        names = dict(
            (
                await self.session.execute(
                    select(BountyScope.target_value, BountyProgram.name)
                    .join(BountyProgram, BountyProgram.id == BountyScope.program_id)
                    .where(
                        BountyScope.target_value.in_([t.target_value for t in targets])
                    )
                )
            ).all()
        )
        items = []
        for t in targets:
            source = WATCH_SOURCE if t.id in watched else SCOPE_SOURCE
            items.append(
                ChangeItem(
                    id=f"{ChangeKind.TARGET.value}:{t.id}",
                    at=t.created_at,
                    kind=ChangeKind.TARGET.value,
                    label=KIND_LABELS[ChangeKind.TARGET.value],
                    value=t.target_value,
                    detail=names.get(t.target_value),
                    source=source,
                    source_label=_source_label(source),
                    tone=ChangeTone.NEW.value,
                    target_id=t.id,
                    target_value=t.target_value,
                    program_name=names.get(t.target_value),
                )
            )
        return items, len(rows) > limit

    # ---------- watched hosts ----------

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
                    id=f"{ChangeKind.WATCH_HOST.value}:{h.id}",
                    at=h.first_seen_at,
                    kind=ChangeKind.WATCH_HOST.value,
                    label=KIND_LABELS[ChangeKind.WATCH_HOST.value],
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

    def _event_conds(self, project_id: UUID, since: datetime, program, target_value):
        conds = [
            BountyEventRow.created_at >= since,
            BountyEventRow.kind.in_(list(NEW_EVENTS)),
        ]
        if program is not None:
            conds.append(BountyEventRow.program_id == program.id)
        else:
            conds.append(
                BountyEventRow.program_id.in_(self._engaged_programs(project_id))
            )
        if target_value:
            conds.append(
                BountyEventRow.asset_identifier.in_([target_value, f"*.{target_value}"])
            )
        return conds

    async def _events(self, conds, kinds: set[str], limit: int):
        rows = (
            await self.session.execute(
                select(BountyEventRow, BountyProgram.source)
                .join(BountyProgram, BountyProgram.id == BountyEventRow.program_id)
                .where(*conds, BountyEventRow.kind.in_(list(kinds)))
                .order_by(BountyEventRow.created_at.desc())
                .limit(limit + 1)
            )
        ).all()
        items = []
        for e, source in rows[:limit]:
            kind = change_kind_of_event(e.kind)
            if kind is None:
                continue
            spec = event_spec(e.kind)
            scoped = kind == ChangeKind.SCOPE_ASSET.value
            items.append(
                ChangeItem(
                    id=f"{kind}:{e.id}",
                    at=e.created_at,
                    kind=kind,
                    label=KIND_LABELS[kind] if scoped else spec.label,
                    value=(e.asset_identifier or e.program_name)
                    if scoped
                    else e.program_name,
                    detail=(e.asset_type if scoped else e.detail) or None,
                    source=source,
                    source_label=_source_label(source),
                    tone=EVENT_TONES.get(spec.tone, ChangeTone.NEUTRAL.value),
                    platform=e.platform,
                    handle=e.handle,
                    program_name=e.program_name,
                )
            )
        return items, len(rows) > limit

    # ---------- helpers ----------

    async def _count(self, stmt) -> int:
        return int(await self.session.scalar(stmt) or 0)
