"""Append-only audit events and persisted idempotency keys."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAtMixin, ProvenanceMixin


class AuditEvent(Base, ProvenanceMixin):
    """Audit rows are append-only; corrections are new compensating events."""

    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    object_id: Mapped[str] = mapped_column(String(120), nullable=False)
    before: Mapped[dict | None] = mapped_column(JSONB)
    after: Mapped[dict | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str | None] = mapped_column(String(120))
    correlation: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    access_decision: Mapped[str | None] = mapped_column(String(16))
    result: Mapped[str | None] = mapped_column(String(32))
    integrity: Mapped[str | None] = mapped_column(String(32))
    prev_event_hash: Mapped[str | None] = mapped_column(String(80))
    event_hash: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IdempotencyKey(Base, CreatedAtMixin):
    """Persisted request/response for safe write replays."""

    __tablename__ = "idempotency_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    scope: Mapped[str] = mapped_column(String(120), nullable=False)
    key: Mapped[str] = mapped_column(String(300), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(80), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    response: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("scope", "key", name="uq_idempotency_keys_scope_key"),
    )
