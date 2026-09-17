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
from shared.models.bounty_program import BountyEventRow, BountyProgram
from shared.models.watch import ProgramWatch, WatchHost

pytestmark = pytest.mark.api


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

    web = [i for i in out.items if i.kind == ChangeKind.WEB_ASSET.value]
    assert [i.value for i in web] == ["b.example.com"]
    assert web[0].source == "subfinder"
    assert web[0].scan_id == estate.scans["fresh"]
    assert out.counts[ChangeKind.WEB_ASSET.value] == 1
    assert out.basis == ChangeBasis.MARK.value


async def test_a_first_run_reports_the_target_not_its_hosts(estate, now):
    await estate.scan("example.com", "first", at=now)
    await estate.hosts("first", ["a.example.com", "b.example.com"], at=now)

    out = await ChangeFeedService(estate.session).feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1)
    )

    assert out.counts[ChangeKind.WEB_ASSET.value] == 0
    targets = [i for i in out.items if i.kind == ChangeKind.TARGET.value]
    assert [i.value for i in targets] == ["example.com"]


async def test_a_certificate_host_is_reported_once(estate, now):
    await estate.scan("example.com", "older", at=now - timedelta(days=2))
    await estate.hosts("older", ["a.example.com"], at=now - timedelta(days=2))
    await estate.scan("example.com", "fresh", at=now)
    await estate.hosts("fresh", ["ct.example.com"], at=now, sources=[CT_SOURCE])

    out = await ChangeFeedService(estate.session).feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1)
    )

    assert out.counts[ChangeKind.WEB_ASSET.value] == 0


async def test_the_window_stands_in_until_a_mark_exists(estate, now):
    service = ChangeFeedService(estate.session)

    first = await service.feed(estate.project_id, estate.user_id)
    assert first.basis == ChangeBasis.WINDOW.value
    assert first.window == "7d"
    assert first.marked_at is None

    marked = await service.mark_seen(estate.user_id, estate.project_id)
    second = await service.feed(estate.project_id, estate.user_id)
    assert second.basis == ChangeBasis.MARK.value
    assert second.since == marked
    assert second.marked_at == marked


async def test_a_watch_host_and_its_program_events_join_the_feed(estate, now):
    tid = await estate.target("recurly.com")
    program = BountyProgram(
        platform="hackerone",
        handle="recurly",
        name="Recurly",
        program_state="public",
        submission_state="open",
    )
    estate.session.add(program)
    await estate.session.flush()
    watch = ProgramWatch(
        project_id=estate.project_id,
        program_id=program.id,
        created_by=estate.user_id,
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
    estate.session.add(
        BountyEventRow(
            platform="hackerone",
            program_id=program.id,
            handle="recurly",
            program_name="Recurly",
            kind=BountyEvent.SCOPE_ADDED.value,
            asset_type="wildcard",
            asset_identifier="*.recurly.com",
            created_at=now,
        )
    )
    other = BountyProgram(
        platform="hackerone",
        handle="other",
        name="Other",
        program_state="public",
        submission_state="open",
    )
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

    hosts = [i for i in out.items if i.kind == ChangeKind.HOST.value]
    assert [i.value for i in hosts] == ["app.recurly.com"]
    assert hosts[0].detail == "200 · Log In"
    assert hosts[0].handle == "recurly"
    scope = [i for i in out.items if i.kind == ChangeKind.SCOPE_ADDED.value]
    assert [i.value for i in scope] == ["*.recurly.com"]
    assert out.counts[ChangeKind.SCOPE_ADDED.value] == 1

    by_program = await ChangeFeedService(estate.session).feed(
        estate.project_id,
        estate.user_id,
        since=now - timedelta(hours=1),
        platform="hackerone",
        handle="other",
    )
    assert [
        i.value for i in by_program.items if i.kind == ChangeKind.SCOPE_ADDED.value
    ] == ["*.other.com"]
    assert by_program.counts[ChangeKind.HOST.value] == 0


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

    assert [i.value for i in out.items if i.kind == ChangeKind.WEB_ASSET.value] == [
        "new.a.com"
    ]
    assert [i.value for i in out.items if i.kind == ChangeKind.TARGET.value] == [
        "a.com"
    ]


async def test_unknown_kinds_are_rejected_by_the_route():
    with pytest.raises(HTTPException):
        await change_feed(
            current_user=None,  # type: ignore[arg-type]
            service=None,  # type: ignore[arg-type]
            session=None,  # type: ignore[arg-type]
            project_id=uuid.uuid4(),
            kinds="nope",
        )
