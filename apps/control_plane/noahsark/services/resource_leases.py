"""Exclusive leases for node hardware resources.

The platform-side lock is a row in ``resource_leases``.  Acquisition happens in
the same transaction as campaign/command creation:

1. take a PostgreSQL advisory *transaction* lock per resource key (sorted, so two
   concurrent creators cannot deadlock);
2. reclaim rows whose TTL already passed;
3. look for ``ACTIVE`` holders and either fail with ``DEVICE_BUSY`` or stop the
   current owner when the caller asked to preempt;
4. insert one ``ACTIVE`` row per key.  The partial unique index is the final
   backstop if a caller ever forgets the advisory lock.

Release is an ``UPDATE ... WHERE status = 'ACTIVE'``: a released row keeps its
history but no longer participates in the unique index.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import ApiError
from ..models.device import Device, Node
from ..models.resource_lease import ResourceLease
from ..models.test_campaign import TestCampaign
from . import node_commands

OWNER_TEST_CAMPAIGN = "TEST_CAMPAIGN"

LEASE_STATUS_ACTIVE = "ACTIVE"
LEASE_STATUS_RELEASED = "RELEASED"
LEASE_STATUS_EXPIRED = "EXPIRED"

RELEASE_TERMINAL = "CAMPAIGN_TERMINAL"
RELEASE_STOPPED = "STOPPED_BY_USER"
RELEASE_PREEMPTED = "PREEMPTED"
RELEASE_DELETED = "CAMPAIGN_DELETED"
RELEASE_TTL = "TTL_EXPIRED"

# A campaign may legitimately run for the full ``test.run`` timeout.  The lease
# outlives it by an hour so a slow result upload cannot let a second campaign in
# while the node is still finishing.
DEFAULT_LEASE_TTL_SECONDS = node_commands.TEST_RUN_TIMEOUT_SECONDS + 3600


def _now(value: datetime | None) -> datetime:
    return value or datetime.now(UTC)


async def resource_keys_for_node(
    session: AsyncSession, node: Node
) -> list[str]:
    """Return the sorted resource set a campaign on ``node`` must hold.

    The node key is always present: it covers ports the platform does not know
    about (the control plane only registers COM6, while the TCL runner also uses
    COM3/COM4).  Endpoint keys add finer-grained exclusion for future shared
    devices without weakening the node-level guarantee.
    """

    keys = {f"node:{node.display_id}"}
    devices = (
        await session.execute(select(Device).where(Device.node_id == node.node_id))
    ).scalars()
    for device in devices:
        endpoints = device.endpoints or []
        if not isinstance(endpoints, list):
            continue
        for endpoint in endpoints:
            if not isinstance(endpoint, dict):
                continue
            kind = endpoint.get("kind")
            if kind == "audio":
                device_key = endpoint.get("device_key")
                if isinstance(device_key, str) and device_key:
                    keys.add(f"audio:{node.display_id}:{device_key}")
            elif kind == "serial":
                port = endpoint.get("port") or endpoint.get("binding")
                if isinstance(port, str) and port:
                    keys.add(f"serial:{node.display_id}:{port}")
    return sorted(keys)


async def lock_resource_keys(
    session: AsyncSession, resource_keys: list[str]
) -> None:
    """Take transaction-scoped advisory locks in deterministic order."""

    for key in sorted(set(resource_keys)):
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key)::bigint)"),
            {"key": f"resource_lease:{key}"},
        )


async def reclaim_expired(
    session: AsyncSession, *, now: datetime | None = None
) -> int:
    """Mark stale ``ACTIVE`` rows ``EXPIRED``; the caller owns the transaction."""

    moment = _now(now)
    result = await session.execute(
        update(ResourceLease)
        .where(
            ResourceLease.status == LEASE_STATUS_ACTIVE,
            ResourceLease.expires_at < moment,
        )
        .values(
            status=LEASE_STATUS_EXPIRED,
            released_at=moment,
            release_reason=RELEASE_TTL,
        )
    )
    return int(getattr(result, "rowcount", 0) or 0)


async def active_leases(
    session: AsyncSession, resource_keys: list[str]
) -> list[ResourceLease]:
    if not resource_keys:
        return []
    rows = await session.execute(
        select(ResourceLease)
        .where(
            ResourceLease.status == LEASE_STATUS_ACTIVE,
            ResourceLease.resource_key.in_(sorted(set(resource_keys))),
        )
        .order_by(ResourceLease.resource_key.asc())
    )
    return list(rows.scalars())


async def insert_leases(
    session: AsyncSession,
    *,
    resource_keys: list[str],
    owner_type: str,
    owner_id: uuid.UUID,
    now: datetime | None = None,
    ttl_seconds: int = DEFAULT_LEASE_TTL_SECONDS,
) -> list[ResourceLease]:
    moment = _now(now)
    leases = [
        ResourceLease(
            lease_id=uuid.uuid4(),
            resource_key=key,
            owner_type=owner_type,
            owner_id=owner_id,
            status=LEASE_STATUS_ACTIVE,
            acquired_at=moment,
            heartbeat_at=moment,
            expires_at=moment + timedelta(seconds=ttl_seconds),
        )
        for key in sorted(set(resource_keys))
    ]
    session.add_all(leases)
    await session.flush()
    return leases


async def release_owner(
    session: AsyncSession,
    *,
    owner_type: str,
    owner_id: uuid.UUID,
    reason: str,
    now: datetime | None = None,
    status: str = LEASE_STATUS_RELEASED,
) -> int:
    """Release every active lease owned by one campaign/command."""

    moment = _now(now)
    result = await session.execute(
        update(ResourceLease)
        .where(
            ResourceLease.status == LEASE_STATUS_ACTIVE,
            ResourceLease.owner_type == owner_type,
            ResourceLease.owner_id == owner_id,
        )
        .values(
            status=status,
            released_at=moment,
            release_reason=reason,
            heartbeat_at=moment,
        )
    )
    return int(getattr(result, "rowcount", 0) or 0)


async def renew_owner(
    session: AsyncSession,
    *,
    owner_type: str,
    owner_id: uuid.UUID,
    now: datetime | None = None,
    ttl_seconds: int = DEFAULT_LEASE_TTL_SECONDS,
) -> int:
    """Refresh ``heartbeat_at``/``expires_at`` for a still-running campaign."""

    moment = _now(now)
    result = await session.execute(
        update(ResourceLease)
        .where(
            ResourceLease.status == LEASE_STATUS_ACTIVE,
            ResourceLease.owner_type == owner_type,
            ResourceLease.owner_id == owner_id,
        )
        .values(
            heartbeat_at=moment,
            expires_at=moment + timedelta(seconds=ttl_seconds),
        )
    )
    return int(getattr(result, "rowcount", 0) or 0)


async def busy_payload(
    session: AsyncSession, leases: list[ResourceLease]
) -> dict[str, Any]:
    """Describe the active holders for a ``DEVICE_BUSY`` error body."""

    campaign_ids = [
        lease.owner_id
        for lease in leases
        if lease.owner_type == OWNER_TEST_CAMPAIGN
    ]
    campaigns: dict[uuid.UUID, TestCampaign] = {}
    if campaign_ids:
        rows = await session.execute(
            select(TestCampaign).where(TestCampaign.campaign_id.in_(campaign_ids))
        )
        campaigns = {campaign.campaign_id: campaign for campaign in rows.scalars()}

    owners: list[dict[str, Any]] = []
    seen: set[tuple[str, uuid.UUID]] = set()
    for lease in leases:
        identity = (lease.owner_type, lease.owner_id)
        if identity in seen:
            continue
        seen.add(identity)
        campaign = campaigns.get(lease.owner_id)
        owners.append(
            {
                "owner_type": lease.owner_type,
                "owner_id": str(lease.owner_id),
                "campaign_id": (
                    str(campaign.campaign_id)
                    if campaign is not None
                    else (
                        str(lease.owner_id)
                        if lease.owner_type == OWNER_TEST_CAMPAIGN
                        else None
                    )
                ),
                "campaign_status": campaign.status if campaign is not None else None,
                "campaign_title": campaign.title if campaign is not None else None,
                "node_id": (
                    str(campaign.node_id)
                    if campaign is not None
                    else None
                ),
                "resource_key": lease.resource_key,
                "expires_at": lease.expires_at.isoformat().replace("+00:00", "Z"),
            }
        )
    expires_at = min(
        (lease.expires_at for lease in leases),
        default=None,
    )
    return {
        "busy_resources": sorted({lease.resource_key for lease in leases}),
        "owners": owners,
        "expires_at": (
            expires_at.isoformat().replace("+00:00", "Z")
            if expires_at is not None
            else None
        ),
    }


def device_busy_error(details: dict[str, Any]) -> ApiError:
    resources = ", ".join(details.get("busy_resources", []))
    return ApiError(
        409,
        "DEVICE_BUSY",
        f"device resources are busy: {resources}",
        retryable=True,
        details=details,
    )
