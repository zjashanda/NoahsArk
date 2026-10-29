"""Persisted stop/release request records.

A request records intent.  It never mutates run/lease lifecycle: STOP becomes
an execution fact only when a node confirms it, and release is confirmed only
after the three preconditions plus R-05 hold.  Keeping requests as their own
rows lets the audit trail point at a stable object id.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAtMixin, ProvenanceMixin, SchemaVersionMixin, enum_check


class WriteRequest(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    __tablename__ = "write_requests"

    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    request_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="REQUESTED", server_default=text("'REQUESTED'")
    )
    reason: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    requested_role: Mapped[str] = mapped_column(String(32), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            enum_check("request_type", ("STOP", "RELEASE"), "request_type"),
            name="request_type_closed",
        ),
        CheckConstraint(
            enum_check("status", ("REQUESTED", "ACCEPTED", "REJECTED"), "status"),
            name="status_closed",
        ),
    )
