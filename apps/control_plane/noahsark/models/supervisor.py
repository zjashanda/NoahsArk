"""OpenCode supervisor session binding for a task.

The row is a durable *binding*, not an execution record.  It stores which task
and immutable revision the supervisor is attached to, the lifecycle state, an
optional remote OpenCode session id (distinct from NoahsArk auth session
tokens), and only a digest/byte-count of the dispatch prompt.  Raw prompts,
transcripts and credentials are never persisted here.

Exactly one row may be active per task.  Terminal rows stay for history, while
the partial unique index allows a later revision to open a new active binding.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ProvenanceMixin, SchemaVersionMixin, TimestampMixin, enum_check

SUPERVISOR_STATES = (
    "PENDING",
    "BINDING",
    "READY",
    "DISPATCHED",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "STOP_REQUESTED",
    "STOPPED",
)
ACTIVE_SUPERVISOR_STATES = (
    "PENDING",
    "BINDING",
    "READY",
    "DISPATCHED",
    "RUNNING",
    "STOP_REQUESTED",
)
TERMINAL_SUPERVISOR_STATES = ("COMPLETED", "FAILED", "STOPPED")
_ACTIVE_STATE_SQL = "state IN (" + ", ".join(
    f"'{state}'" for state in ACTIVE_SUPERVISOR_STATES
) + ")"


class SupervisorSession(Base, SchemaVersionMixin, ProvenanceMixin, TimestampMixin):
    __tablename__ = "supervisor_sessions"

    supervisor_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    display_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.task_id"), nullable=False, index=True
    )
    revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("task_revisions.revision_id"),
        nullable=False,
        index=True,
    )
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING", server_default=text("'PENDING'")
    )
    # Remote OpenCode session identifier.  This is not a bearer credential and
    # is never confused with ``sessions.token_hash`` for NoahsArk auth.
    remote_session_id: Mapped[str | None] = mapped_column(String(200))
    # Dispatch prompt is represented only by its digest and UTF-8 byte count.
    prompt_digest: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    # Worker-reported result summary must already be sanitized by the caller.
    result_summary: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(120))
    result_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            enum_check("state", SUPERVISOR_STATES, "state"),
            name="state_closed",
        ),
        CheckConstraint("prompt_bytes >= 0", name="prompt_bytes_non_negative"),
        UniqueConstraint(
            "remote_session_id", name="uq_supervisor_sessions_remote_session_id"
        ),
        Index(
            "uq_supervisor_sessions_active_task",
            "task_id",
            unique=True,
            postgresql_where=text(_ACTIVE_STATE_SQL),
        ),
    )
