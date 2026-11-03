"""Exclusive resource leases for hardware-bound work.

A campaign that drives a node (serial ports and the ListenAI sound card) must
hold one ``ACTIVE`` lease per resource key for its whole lifetime.  The partial
unique index on ``resource_key`` is the authority: PostgreSQL itself refuses a
second active holder even if two transactions race past the application check.

Leases are soft state: ``expires_at`` makes a crashed owner reclaimable once
the TTL passes.  A released/expired row stays in the table so the history of who
held a resource is auditable; only ``ACTIVE`` rows take part in the unique index.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, enum_check

LEASE_STATUSES = ("ACTIVE", "RELEASED", "EXPIRED")


class ResourceLease(Base):
    __tablename__ = "resource_leases"

    lease_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    resource_key: Mapped[str] = mapped_column(String(300), nullable=False)
    owner_type: Mapped[str] = mapped_column(String(32), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="ACTIVE", server_default=text("'ACTIVE'")
    )
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    release_reason: Mapped[str | None] = mapped_column(String(80))

    __table_args__ = (
        CheckConstraint(
            enum_check("status", LEASE_STATUSES, "status"),
            name="status_closed",
        ),
        # The one invariant that matters: at most one ACTIVE owner per resource.
        Index(
            "uq_resource_leases_active_key",
            "resource_key",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index("ix_resource_leases_owner", "owner_type", "owner_id"),
        Index("ix_resource_leases_status_expires", "status", "expires_at"),
    )
