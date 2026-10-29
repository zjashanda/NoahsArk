"""Lease, Device and Node models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAtMixin, ProvenanceMixin, SchemaVersionMixin, enum_check


class Node(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    __tablename__ = "nodes"

    node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    hostname: Mapped[str] = mapped_column(String(200), nullable=False)
    identity: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    agent_version: Mapped[str] = mapped_column(String(80), nullable=False)
    os: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    runtime: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    communication_state: Mapped[str] = mapped_column(String(16), nullable=False)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    interactive_session: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    work_dir: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    spool: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    capabilities: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    endpoint_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    quarantine_reason: Mapped[str | None] = mapped_column(Text)
    draining_reason: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(80))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(enum_check("communication_state", ("ONLINE", "STALE", "OFFLINE"), "communication_state"), name="communication_state_closed"),
        CheckConstraint(enum_check("status", ("ACTIVE", "DRAINING", "QUARANTINED", "RETIRED"), "status"), name="status_closed"),
    )


class Device(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    __tablename__ = "devices"

    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("nodes.node_id"), nullable=False, index=True
    )
    identity: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    capabilities: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    endpoints: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    firmware_version: Mapped[str] = mapped_column(String(80), nullable=False)
    config_digest: Mapped[str] = mapped_column(String(80), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(80), nullable=False)
    project_scope: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    pool_state: Mapped[str] = mapped_column(String(32), nullable=False)
    health_state: Mapped[str] = mapped_column(String(32), nullable=False)
    communication_state: Mapped[str] = mapped_column(String(16), nullable=False)
    occupancy_state: Mapped[str] = mapped_column(String(16), nullable=False)
    current_lease_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    equivalence: Mapped[dict | None] = mapped_column(JSONB)
    provenance: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quarantine_reason: Mapped[str | None] = mapped_column(Text)
    draining_reason: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(80))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            enum_check(
                "pool_state",
                ("DISCOVERED", "READY", "RESERVED", "ATTACHED", "DRAINING", "QUARANTINED", "OFFLINE", "RETIRED"),
                "pool_state",
            ),
            name="pool_state_closed",
        ),
        CheckConstraint(enum_check("health_state", ("HEALTHY", "DEGRADED", "UNHEALTHY", "UNKNOWN"), "health_state"), name="health_state_closed"),
        CheckConstraint(enum_check("communication_state", ("ONLINE", "STALE", "OFFLINE"), "communication_state"), name="communication_state_closed"),
        CheckConstraint(enum_check("occupancy_state", ("IDLE", "OCCUPIED", "RELEASING"), "occupancy_state"), name="occupancy_state_closed"),
    )


class Lease(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    __tablename__ = "leases"

    lease_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("nodes.node_id"), nullable=False, index=True
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.device_id"), nullable=False, index=True
    )
    endpoint_set: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.task_id"), nullable=False, index=True
    )
    revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_revisions.revision_id"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.run_id"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    epoch: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    occupancy_state: Mapped[str] = mapped_column(String(16), nullable=False)
    communication_state: Mapped[str] = mapped_column(String(16), nullable=False)
    execution_permit: Mapped[str] = mapped_column(String(16), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    renewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    release_preconditions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    release_reason: Mapped[str | None] = mapped_column(Text)
    reclaim_reason: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(80))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    idempotency_key: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)

    __table_args__ = (
        CheckConstraint(
            enum_check("state", ("GRANTED", "HELD", "RELEASING", "RECLAIM_PENDING", "RELEASED", "QUARANTINED"), "state"),
            name="state_closed",
        ),
        CheckConstraint(enum_check("occupancy_state", ("OCCUPIED", "RELEASING", "IDLE"), "occupancy_state"), name="occupancy_state_closed"),
        CheckConstraint(enum_check("communication_state", ("ONLINE", "STALE", "OFFLINE"), "communication_state"), name="communication_state_closed"),
        CheckConstraint(enum_check("execution_permit", ("GRANTED", "NOT_GRANTED", "SUSPENDED"), "execution_permit"), name="execution_permit_closed"),
        CheckConstraint(
            "state <> 'QUARANTINED' OR occupancy_state = 'OCCUPIED'",
            name="quarantined_stays_occupied",
        ),
        CheckConstraint("epoch >= 1", name="epoch_positive"),
    )
