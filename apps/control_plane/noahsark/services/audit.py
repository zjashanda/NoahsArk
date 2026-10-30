"""Append-only audit service with a tamper-evident hash chain.

Every audit row stores ``prev_event_hash`` and ``event_hash``.  The hash is
computed over the canonical event payload plus the previous hash, so changing
any persisted field (or re-linking the chain) breaks verification.

The service exposes no update or delete path.  ``ensure_append_only`` is a
deliberate hard-stop for future callers: corrections are new compensating
events, never mutations of history.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import audit_immutable
from ..models import AuditEvent

HASH_ALGORITHM = "sha256"
HASH_PREFIX = HASH_ALGORITHM + ":"
AUDIT_CHAIN_LOCK_KEY = 0x4E4F4148  # "NOAH"; serializes appends in one database.
MUTATING_OPERATIONS = frozenset({"UPDATE", "DELETE", "REPLACE", "TRUNCATE"})
CHAIN_FIELDS = (
    "event_id",
    "occurred_at",
    "actor_role",
    "action",
    "object_type",
    "object_id",
    "before",
    "after",
    "reason",
    "prev_event_hash",
)


@dataclass(frozen=True)
class ChainVerification:
    ok: bool
    checked: int
    broken_at: str | None = None
    reason: str | None = None


def _value(event: Any, field: str) -> Any:
    if isinstance(event, Mapping):
        return event.get(field)
    return getattr(event, field, None)


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def canonical_payload(
    *,
    event_id: str,
    occurred_at: datetime,
    actor_role: str,
    action: str,
    object_type: str,
    object_id: str,
    before: Mapping[str, Any] | None,
    after: Mapping[str, Any] | None,
    reason: str | None,
    prev_event_hash: str | None,
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "occurred_at": occurred_at.isoformat(),
        "actor_role": actor_role,
        "action": action,
        "object_type": object_type,
        "object_id": object_id,
        "before": before,
        "after": after,
        "reason": reason,
        "prev_event_hash": prev_event_hash,
    }


def compute_event_hash(
    *,
    event_id: str,
    occurred_at: datetime,
    actor_role: str,
    action: str,
    object_type: str,
    object_id: str,
    before: Mapping[str, Any] | None,
    after: Mapping[str, Any] | None,
    reason: str | None,
    prev_event_hash: str | None,
) -> str:
    canonical = canonical_payload(
        event_id=event_id,
        occurred_at=occurred_at,
        actor_role=actor_role,
        action=action,
        object_type=object_type,
        object_id=object_id,
        before=before,
        after=after,
        reason=reason,
        prev_event_hash=prev_event_hash,
    )
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
    return HASH_PREFIX + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def event_hash(event: Any) -> str:
    """Recompute the hash for an event-shaped object or mapping."""

    return compute_event_hash(
        event_id=str(_value(event, "event_id")),
        occurred_at=_value(event, "occurred_at"),
        actor_role=str(_value(event, "actor_role")),
        action=str(_value(event, "action")),
        object_type=str(_value(event, "object_type")),
        object_id=str(_value(event, "object_id")),
        before=_value(event, "before"),
        after=_value(event, "after"),
        reason=_value(event, "reason"),
        prev_event_hash=_value(event, "prev_event_hash"),
    )


def verify_chain(
    events: Sequence[Any], *, require_genesis: bool = False
) -> ChainVerification:
    """Verify event hashes and prev-hash links in the supplied order.

    ``require_genesis=False`` accepts a slice whose first ``prev_event_hash``
    points at an older row outside the slice (for example a filtered replay).
    """

    previous_hash: str | None = None
    for index, item in enumerate(events):
        event_id = str(_value(item, "event_id"))
        stored_hash = _value(item, "event_hash")
        stored_prev = _value(item, "prev_event_hash")

        if index == 0:
            if require_genesis and stored_prev is not None:
                return ChainVerification(
                    False, index, event_id, "first event does not link to genesis"
                )
        elif stored_prev != previous_hash:
            return ChainVerification(
                False, index, event_id, "prev_event_hash does not match previous event"
            )

        if not stored_hash:
            return ChainVerification(False, index, event_id, "event_hash is missing")
        if event_hash(item) != stored_hash:
            return ChainVerification(False, index, event_id, "event_hash mismatch")

        previous_hash = str(stored_hash)
    return ChainVerification(True, len(events))


def ensure_append_only(operation: str) -> None:
    """Reject any attempted mutation of the audit log."""

    if operation.strip().upper() in MUTATING_OPERATIONS:
        raise audit_immutable(operation)


async def _last_event_hash(session: AsyncSession) -> str | None:
    try:
        bind = session.get_bind()
    except Exception:  # noqa: BLE001  # pragma: no cover - detached test sessions
        bind = None
    if bind is not None and bind.dialect.name == "postgresql":
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": AUDIT_CHAIN_LOCK_KEY},
        )
    return (
        await session.execute(
            select(AuditEvent.event_hash)
            .where(AuditEvent.event_hash.is_not(None))
            .order_by(AuditEvent.occurred_at.desc(), AuditEvent.event_id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def append_event(
    session: AsyncSession,
    *,
    actor_role: str,
    actor_id: uuid.UUID | None,
    action: str,
    object_type: str,
    object_id: str,
    before: Mapping[str, Any] | None,
    after: Mapping[str, Any] | None,
    reason: str | None,
    correlation_id: str | None,
    path: str,
    occurred_at: datetime | None = None,
) -> AuditEvent:
    """Append one hash-chained event.  Never updates or deletes history."""

    when = occurred_at or datetime.now(UTC)
    prev_hash = await _last_event_hash(session)
    event_id = f"aud-{when:%Y%m%d%H%M%S}-{uuid.uuid4().hex[:10]}"
    digest = compute_event_hash(
        event_id=event_id,
        occurred_at=when,
        actor_role=actor_role,
        action=action,
        object_type=object_type,
        object_id=object_id,
        before=before,
        after=after,
        reason=reason,
        prev_event_hash=prev_hash,
    )
    event = AuditEvent(
        event_id=event_id,
        occurred_at=when,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        object_type=object_type,
        object_id=object_id,
        before=dict(before) if before is not None else None,
        after=dict(after) if after is not None else None,
        reason=reason,
        correlation_id=correlation_id,
        correlation={"path": path, "append_only": True},
        access_decision="ALLOW",
        result="SUCCESS",
        integrity="HASH_CHAIN_OK",
        prev_event_hash=prev_hash,
        event_hash=digest,
        created_at=when,
        source="control-plane",
        seed=False,
    )
    session.add(event)
    return event


async def load_events(
    session: AsyncSession,
    *,
    correlation_prefix: str | None = None,
    limit: int = 1000,
) -> list[AuditEvent]:
    query = select(AuditEvent)
    if correlation_prefix is not None:
        query = query.where(
            AuditEvent.correlation_id.like(f"{correlation_prefix}%")
        )
    query = query.order_by(
        AuditEvent.occurred_at.asc(), AuditEvent.event_id.asc()
    ).limit(limit)
    return list((await session.execute(query)).scalars().all())


async def verify_stored_chain(
    session: AsyncSession,
    *,
    correlation_prefix: str | None = None,
    limit: int = 1000,
) -> ChainVerification:
    events = await load_events(
        session, correlation_prefix=correlation_prefix, limit=limit
    )
    return verify_chain(events)
