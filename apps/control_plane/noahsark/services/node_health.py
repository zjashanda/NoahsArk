"""Node communication-state expiry.

Registration and heartbeats set a node ``ONLINE``; nothing else ever moved it
back.  This service owns the *downward* transitions only:

- ``ONLINE`` -> ``STALE`` once the last heartbeat is older than
  ``3 x heartbeat_interval_seconds`` (never less than 90 seconds);
- ``ONLINE``/``STALE`` -> ``OFFLINE`` once it is older than
  ``10 x heartbeat_interval_seconds`` (never less than 300 seconds);
- a node with no ``last_heartbeat_at`` is ``OFFLINE``.

A sweep never promotes a node.  ``ONLINE`` is only set by the node gateway when
the agent actually registers or heartbeats.  Nodes that are already ``OFFLINE``
are out of scope, so a stale sweep cannot revive them.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.device import Node

STALE_INTERVAL_MULTIPLIER = 3
OFFLINE_INTERVAL_MULTIPLIER = 10
MIN_STALE_SECONDS = 90
MIN_OFFLINE_SECONDS = 300
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 30

# Only these states can transition down. OFFLINE is terminal for this sweep.
_EXPIRABLE_STATES = ("ONLINE", "STALE")


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _interval(heartbeat_interval_seconds: int | None) -> int:
    if isinstance(heartbeat_interval_seconds, int) and heartbeat_interval_seconds > 0:
        return heartbeat_interval_seconds
    return DEFAULT_HEARTBEAT_INTERVAL_SECONDS


def staleness_thresholds(heartbeat_interval_seconds: int | None) -> tuple[int, int]:
    """Return ``(stale_after_seconds, offline_after_seconds)``.

    The floor values keep a fast-heartbeat node from flapping and keep a
    misconfigured interval (for example one second) from expiring healthy nodes.
    """

    interval = _interval(heartbeat_interval_seconds)
    stale_after = max(interval * STALE_INTERVAL_MULTIPLIER, MIN_STALE_SECONDS)
    offline_after = max(interval * OFFLINE_INTERVAL_MULTIPLIER, MIN_OFFLINE_SECONDS)
    return stale_after, offline_after


def next_communication_state(
    *,
    state: str,
    last_heartbeat_at: datetime | None,
    heartbeat_interval_seconds: int | None,
    now: datetime,
) -> str | None:
    """Return the next state for a node, or ``None`` when it stays as-is."""

    if state not in _EXPIRABLE_STATES:
        return None
    if last_heartbeat_at is None:
        return "OFFLINE"

    moment = _as_utc(now)
    heartbeat = _as_utc(last_heartbeat_at)
    stale_after, offline_after = staleness_thresholds(heartbeat_interval_seconds)
    age = (moment - heartbeat).total_seconds()

    if age >= offline_after:
        return "OFFLINE"
    if age >= stale_after and state == "ONLINE":
        return "STALE"
    return None


async def sweep_node_staleness(
    session: AsyncSession, *, now: datetime | None = None
) -> dict[str, int]:
    """Expire nodes whose heartbeat stopped and return transition counts.

    ``now`` is injectable so callers and tests can pin the clock.  Rows are
    committed only when at least one state changed.
    """

    moment = now if now is not None else datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)

    result = await session.execute(
        select(Node).where(Node.communication_state.in_(_EXPIRABLE_STATES))
    )
    counts = {"stale": 0, "offline": 0}
    for node in result.scalars():
        target = next_communication_state(
            state=node.communication_state,
            last_heartbeat_at=node.last_heartbeat_at,
            heartbeat_interval_seconds=node.heartbeat_interval_seconds,
            now=moment,
        )
        if target is None:
            continue
        if target == "STALE":
            counts["stale"] += 1
        else:
            counts["offline"] += 1
        node.communication_state = target
        node.updated_at = moment

    if counts["stale"] or counts["offline"]:
        await session.commit()
    return counts


__all__ = [
    "DEFAULT_HEARTBEAT_INTERVAL_SECONDS",
    "MIN_OFFLINE_SECONDS",
    "MIN_STALE_SECONDS",
    "OFFLINE_INTERVAL_MULTIPLIER",
    "STALE_INTERVAL_MULTIPLIER",
    "next_communication_state",
    "staleness_thresholds",
    "sweep_node_staleness",
]
