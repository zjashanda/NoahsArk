"""Deterministic test campaign records.

A campaign is the platform-side record of one long-running node test (for
example the TCL003 five-round wake-recognition run).  It is deliberately *not*
a Task: the run is deterministic, needs no agent prompt and must never start a
supervisor session.  The campaign owns the intent (node, scenario, rounds,
bench) while ``command_id`` points at the ``node_commands`` row that carries the
single ``test.run`` invocation to the node.

``task_id`` is an optional owning-Task link so campaigns can be listed inside a
task detail page.  It is nullable and ``ON DELETE SET NULL``: campaigns created
before the link existed stay unassociated (``NULL``), and a campaign remains
runnable without a Task.  The FK does not by itself remove campaigns; their rows
survive only until the application-level task deletion runs.  That deletion
refuses to proceed while a linked campaign is ``QUEUED``/``RUNNING`` (it must be
stopped first), and otherwise hard-deletes the terminal campaign rows after
releasing their resource leases and recording audit events.

``summary`` and ``rounds_data`` store the node-reported payload.  Both are
untrusted input: the service validates their shape and caps their size before
they are persisted.  A missing summary stays NULL so an artifact path can never
be mistaken for a PASS verdict.
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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAtMixin, enum_check

CAMPAIGN_STATUSES = ("QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "TIMEOUT", "STOPPED")
FINAL_CAMPAIGN_STATUSES = frozenset({"SUCCEEDED", "FAILED", "TIMEOUT", "STOPPED"})


class TestCampaign(Base, CreatedAtMixin):
    __tablename__ = "test_campaigns"

    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.task_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scenario: Mapped[str] = mapped_column(String(80), nullable=False)
    rounds: Mapped[int] = mapped_column(Integer, nullable=False)
    bench: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="QUEUED", server_default=text("'QUEUED'")
    )
    command_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("node_commands.command_id", ondelete="SET NULL"),
        nullable=True,
    )
    summary: Mapped[dict | None] = mapped_column(JSONB)
    rounds_data: Mapped[list | None] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(String(80))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            enum_check("status", CAMPAIGN_STATUSES, "status"),
            name="status_closed",
        ),
        Index("uq_test_campaigns_command_id", "command_id", unique=True),
    )
