"""Node staleness sweep tests.

The sweep is exercised through an in-memory session double, so no database is
required: the decision table and the returned counts are the contract under
test.  A live smoke check against PostgreSQL is done separately.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from noahsark.services.node_health import (
    MIN_OFFLINE_SECONDS,
    MIN_STALE_SECONDS,
    next_communication_state,
    staleness_thresholds,
    sweep_node_staleness,
)

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
STALE_UPDATED_AT = NOW - timedelta(days=1)


class _FakeScalars:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)


class _FakeResult:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._rows)


class _FakeSession:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self.rows = rows
        self.commits = 0

    async def execute(self, _statement: object) -> _FakeResult:
        return _FakeResult(self.rows)

    async def commit(self) -> None:
        self.commits += 1


def _node(
    state: str,
    *,
    seconds_ago: int | None,
    interval: int = 30,
    updated_at: datetime = STALE_UPDATED_AT,
) -> SimpleNamespace:
    return SimpleNamespace(
        communication_state=state,
        last_heartbeat_at=(
            None if seconds_ago is None else NOW - timedelta(seconds=seconds_ago)
        ),
        heartbeat_interval_seconds=interval,
        updated_at=updated_at,
    )


def _sweep(rows: list[SimpleNamespace]) -> tuple[dict[str, int], _FakeSession]:
    session = _FakeSession(rows)
    counts = asyncio.run(sweep_node_staleness(session, now=NOW))
    return counts, session


def test_thresholds_apply_multipliers_and_minimum_floors() -> None:
    assert staleness_thresholds(30) == (90, 300)
    assert staleness_thresholds(10) == (MIN_STALE_SECONDS, MIN_OFFLINE_SECONDS)
    assert staleness_thresholds(120) == (360, 1200)
    assert staleness_thresholds(None) == (90, 300)


def test_old_heartbeat_moves_online_node_to_stale() -> None:
    node = _node("ONLINE", seconds_ago=100)

    counts, session = _sweep([node])

    assert counts == {"stale": 1, "offline": 0}
    assert node.communication_state == "STALE"
    assert node.updated_at == NOW
    assert session.commits == 1


def test_much_older_heartbeat_moves_online_node_straight_to_offline() -> None:
    node = _node("ONLINE", seconds_ago=400)

    counts, _ = _sweep([node])

    assert counts == {"stale": 0, "offline": 1}
    assert node.communication_state == "OFFLINE"


def test_recent_heartbeat_leaves_online_node_untouched() -> None:
    node = _node("ONLINE", seconds_ago=10)

    counts, session = _sweep([node])

    assert counts == {"stale": 0, "offline": 0}
    assert node.communication_state == "ONLINE"
    assert node.updated_at == STALE_UPDATED_AT
    assert session.commits == 0


def test_stale_node_becomes_offline_past_offline_threshold() -> None:
    node = _node("STALE", seconds_ago=300)

    counts, _ = _sweep([node])

    assert counts == {"stale": 0, "offline": 1}
    assert node.communication_state == "OFFLINE"


def test_stale_node_inside_offline_threshold_stays_stale() -> None:
    node = _node("STALE", seconds_ago=100)

    counts, session = _sweep([node])

    assert counts == {"stale": 0, "offline": 0}
    assert node.communication_state == "STALE"
    assert session.commits == 0


def test_offline_node_is_never_revived_by_a_fresh_heartbeat() -> None:
    recent = _node("OFFLINE", seconds_ago=1)
    silent = _node("OFFLINE", seconds_ago=None)

    counts, session = _sweep([recent, silent])

    assert counts == {"stale": 0, "offline": 0}
    assert recent.communication_state == "OFFLINE"
    assert silent.communication_state == "OFFLINE"
    assert session.commits == 0


def test_missing_heartbeat_is_offline() -> None:
    online = _node("ONLINE", seconds_ago=None)
    stale = _node("STALE", seconds_ago=None)

    counts, _ = _sweep([online, stale])

    assert counts == {"stale": 0, "offline": 2}
    assert online.communication_state == "OFFLINE"
    assert stale.communication_state == "OFFLINE"


def test_fast_heartbeat_interval_cannot_expire_below_floor() -> None:
    # 3 x 10 = 30s, but the 90s floor keeps a 40s-old heartbeat healthy.
    young = _node("ONLINE", seconds_ago=40, interval=10)
    old = _node("ONLINE", seconds_ago=100, interval=10)
    stale_under_offline_floor = _node("STALE", seconds_ago=299, interval=10)

    counts, _ = _sweep([young, old, stale_under_offline_floor])

    assert counts == {"stale": 1, "offline": 0}
    assert young.communication_state == "ONLINE"
    assert old.communication_state == "STALE"
    assert stale_under_offline_floor.communication_state == "STALE"


def test_counts_and_updates_only_touched_rows() -> None:
    to_stale = _node("ONLINE", seconds_ago=100)
    to_offline = _node("ONLINE", seconds_ago=400)
    stale_to_offline = _node("STALE", seconds_ago=400)
    healthy = _node("ONLINE", seconds_ago=5)
    offline = _node("OFFLINE", seconds_ago=5)

    counts, session = _sweep(
        [to_stale, to_offline, stale_to_offline, healthy, offline]
    )

    assert counts == {"stale": 1, "offline": 2}
    assert to_stale.communication_state == "STALE"
    assert to_offline.communication_state == "OFFLINE"
    assert stale_to_offline.communication_state == "OFFLINE"
    assert healthy.communication_state == "ONLINE"
    assert offline.communication_state == "OFFLINE"
    assert to_stale.updated_at == NOW
    assert to_offline.updated_at == NOW
    assert stale_to_offline.updated_at == NOW
    assert healthy.updated_at == STALE_UPDATED_AT
    assert offline.updated_at == STALE_UPDATED_AT
    assert session.commits == 1


def test_next_state_accepts_naive_heartbeat_as_utc() -> None:
    naive = NOW.replace(tzinfo=None) - timedelta(seconds=400)

    target = next_communication_state(
        state="ONLINE",
        last_heartbeat_at=naive,
        heartbeat_interval_seconds=30,
        now=NOW,
    )

    assert target == "OFFLINE"


def test_lifespan_starts_the_sweeper_and_cancels_it_on_shutdown(monkeypatch) -> None:
    import noahsark.main as main_module

    async def scenario() -> None:
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def fake_loop() -> None:
            started.set()
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                cancelled.set()
                raise

        monkeypatch.setattr(main_module, "_node_health_loop", fake_loop)

        async with main_module.lifespan(main_module.app):
            await asyncio.wait_for(started.wait(), timeout=1)

        assert cancelled.is_set()
        assert all(
            task.get_name() != "node-health-sweep"
            for task in asyncio.all_tasks()
            if task is not asyncio.current_task()
        )

    asyncio.run(scenario())
