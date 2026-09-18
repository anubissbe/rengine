from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.api.v1.changes import change_feed
from app.services.changes import ChangeFeedService
from shared.definitions.bounty_programs import BountyEvent
from shared.definitions.changes import ChangeBasis, ChangeKind
from shared.definitions.watch import CT_SOURCE, WatchHostState
from shared.models.bounty_program import BountyEventRow, BountyProgram, BountyScope
from shared.models.watch import ProgramWatch, WatchHost

pytestmark = pytest.mark.api


def _program(handle: str, name: str) -> BountyProgram:
    return BountyProgram(
        platform="hackerone",
        handle=handle,
        name=name,
        program_state="public",
        submission_state="open",
    )


async def test_a_host_the_previous_run_lacked_is_new(estate, now):
    await estate.scan("example.com", "older", at=now - timedelta(days=2))
    await estate.hosts("older", ["a.example.com"], at=now - timedelta(days=2))
    await estate.scan("example.com", "fresh", at=now)
    await estate.hosts(
        "fresh", ["a.example.com", "b.example.com"], at=now, sources=["subfinder"]
    )

    out = await ChangeFeedService(estate.session).feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1)
    )

    rows = [i for i in out.items if i.kind == ChangeKind.SCANNED_ASSET.value]
    assert [i.value for i in rows] == ["b.example.com"]
    assert rows[0].source == "subfinder"
    assert rows[0].scan_id == estate.scans["fresh"]
    assert out.counts[ChangeKind.SCANNED_ASSET.value] == 1
    assert out.basis == ChangeBasis.MARK.value
    today = now.date().isoformat()
    assert [d.counts for d in out.daily if d.date == today] == [
        {ChangeKind.SCANNED_ASSET.value: 1}
    ]


async def test_a_first_run_reports_nothing(estate, now):
    await estate.scan("example.com", "first", at=now)
    await estate.hosts("first", ["a.example.com", "b.example.com"], at=now)

    out = await ChangeFeedService(estate.session).feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1)
    )

    assert out.items == []
    assert sum(out.counts.values()) == 0


async def test_a_hand_added_target_is_not_a_change(estate, now):
    await estate.target("example.com")

    out = await ChangeFeedService(estate.session).feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1)
    )

    assert out.counts[ChangeKind.TARGET.value] == 0


async def test_a_certificate_host_is_reported_once(estate, now):
    await estate.scan("example.com", "older", at=now - timedelta(days=2))
    await estate.hosts("older", ["a.example.com"], at=now - timedelta(days=2))
    await estate.scan("example.com", "fresh", at=now)
    await estate.hosts("fresh", ["ct.example.com"], at=now, sources=[CT_SOURCE])

    out = await ChangeFeedService(estate.session).feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1)
    )

    assert out.counts[ChangeKind.SCANNED_ASSET.value] == 0


async def test_the_window_stands_in_until_a_mark_exists(estate, now):
    service = ChangeFeedService(estate.session)

    first = await service.feed(estate.project_id, estate.user_id)
    assert first.basis == ChangeBasis.WINDOW.value
    assert first.window == "30d"
    assert first.marked_at is None
    assert len(first.daily) == 31

    marked = await service.mark_seen(estate.user_id, estate.project_id)
    second = await service.feed(estate.project_id, estate.user_id)
    assert second.basis == ChangeBasis.MARK.value
    assert second.since == marked
    assert second.marked_at == marked


async def test_bounty_hub_rows_join_the_feed(estate, now):
    tid = await estate.target("recurly.com")
    program = _program("recurly", "Recurly")
    estate.session.add(program)
    await estate.session.flush()
    estate.session.add(
        BountyScope(
            program_id=program.id,
            asset_type="wildcard",
            asset_identifier="*.recurly.com",
            scope_state="in",
            target_value="recurly.com",
        )
    )
    watch = ProgramWatch(
        project_id=estate.project_id, program_id=program.id, created_by=estate.user_id
    )
    estate.session.add(watch)
    await estate.session.flush()
    estate.session.add(
        WatchHost(
            watch_id=watch.id,
            project_id=estate.project_id,
            target_id=tid,
            name="app.recurly.com",
            state=WatchHostState.ALERTED.value,
            first_seen_at=now,
            status_code=200,
            title="Log In",
        )
    )
    for kind in (
        BountyEvent.SCOPE_ADDED,
        BountyEvent.SCOPE_REMOVED,
        BountyEvent.PROGRAM_WENT_PUBLIC,
    ):
        estate.session.add(
            BountyEventRow(
                platform="hackerone",
                program_id=program.id,
                handle="recurly",
                program_name="Recurly",
                kind=kind.value,
                asset_type="wildcard",
                asset_identifier="*.recurly.com",
                created_at=now,
            )
        )
    other = _program("other", "Other")
    estate.session.add(other)
    await estate.session.flush()
    estate.session.add(
        BountyEventRow(
            platform="hackerone",
            program_id=other.id,
            handle="other",
            program_name="Other",
            kind=BountyEvent.SCOPE_ADDED.value,
            asset_identifier="*.other.com",
            created_at=now,
        )
    )
    await estate.session.flush()

    out = await ChangeFeedService(estate.session).feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1)
    )

    by_kind = {k: [i.value for i in out.items if i.kind == k] for k in out.counts}
    assert by_kind[ChangeKind.WATCH_HOST.value] == ["app.recurly.com"]
    assert by_kind[ChangeKind.SCOPE_ASSET.value] == ["*.recurly.com"]
    assert by_kind[ChangeKind.PROGRAM.value] == ["Recurly"]
    assert by_kind[ChangeKind.TARGET.value] == ["recurly.com"]
    target = next(i for i in out.items if i.kind == ChangeKind.TARGET.value)
    assert target.source == "scope"
    assert target.program_name == "Recurly"
    assert out.counts[ChangeKind.SCOPE_ASSET.value] == 1
    assert "scope_removed" not in {i.kind for i in out.items}

    by_program = await ChangeFeedService(estate.session).feed(
        estate.project_id,
        estate.user_id,
        since=now - timedelta(hours=1),
        platform="hackerone",
        handle="other",
    )
    assert [
        i.value for i in by_program.items if i.kind == ChangeKind.SCOPE_ASSET.value
    ] == ["*.other.com"]
    assert by_program.counts[ChangeKind.WATCH_HOST.value] == 0


async def test_a_program_covering_a_target_counts_without_a_watch(estate, now):
    await estate.target("acme.com")
    program = _program("acme", "Acme")
    estate.session.add(program)
    await estate.session.flush()
    estate.session.add(
        BountyScope(
            program_id=program.id,
            asset_type="url",
            asset_identifier="acme.com",
            scope_state="in",
            target_value="acme.com",
        )
    )
    estate.session.add(
        BountyEventRow(
            platform="hackerone",
            program_id=program.id,
            handle="acme",
            program_name="Acme",
            kind=BountyEvent.SCOPE_ADDED.value,
            asset_identifier="api.acme.com",
            created_at=now,
        )
    )
    await estate.session.flush()

    out = await ChangeFeedService(estate.session).feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1)
    )

    assert out.counts[ChangeKind.SCOPE_ASSET.value] == 1


async def test_a_target_filter_narrows_every_source(estate, now):
    for name in ("a.com", "b.com"):
        await estate.scan(name, f"{name}-older", at=now - timedelta(days=2))
        await estate.scan(name, f"{name}-fresh", at=now)
        await estate.hosts(f"{name}-fresh", [f"new.{name}"], at=now)

    out = await ChangeFeedService(estate.session).feed(
        estate.project_id,
        estate.user_id,
        since=now - timedelta(hours=1),
        target_id=estate.targets["a.com"],
    )

    assert [i.value for i in out.items] == ["new.a.com"]


async def test_unknown_kinds_are_rejected_by_the_route():
    with pytest.raises(HTTPException):
        await change_feed(
            current_user=None,  # type: ignore[arg-type]
            service=None,  # type: ignore[arg-type]
            session=None,  # type: ignore[arg-type]
            project_id=uuid.uuid4(),
            kinds="nope",
        )
