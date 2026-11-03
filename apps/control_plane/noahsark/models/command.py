"""Durable platform-to-node command queue.

A command is a single allow-listed tool invocation.  The row is the platform's
authority over the request lifecycle: it is created ``QUEUED``, claimed by the
node on poll (``SENT``), optionally reported ``RUNNING``, and finally terminal
(``SUCCEEDED`` / ``FAILED`` / ``TIMEOUT``).  Arguments are JSON so a future tool
can add typed parameters without a schema migration; the allow-list of tools and
their argument names lives in ``services.node_commands``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAtMixin, enum_check

COMMAND_STATUSES = ("QUEUED", "SENT", "RUNNING", "SUCCEEDED", "FAILED", "TIMEOUT")


class NodeCommand(Base, CreatedAtMixin):
    __tablename__ = "node_commands"

    command_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_id: Mapped[str] = mapped_column(String(80), nullable=False)
    args_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Set only for commands that belong to a deterministic test campaign.  The
    # node result handler follows this pointer to fold the result back in.
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_campaigns.campaign_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="QUEUED")
    exit_code: Mapped[int | None] = mapped_column(Integer)
    stdout: Mapped[str | None] = mapped_column(Text)
    stderr: Mapped[str | None] = mapped_column(Text)
    truncated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    error_code: Mapped[str | None] = mapped_column(String(80))
    created_by: Mapped[str | None] = mapped_column(String(200))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Platform half of a user STOP for an already-running command.  The node
    # agent reads this on its next poll and kills the local runner; the platform
    # cannot reach into the node directly (outbound-only protocol).
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    __table_args__ = (
        CheckConstraint(
            enum_check("status", COMMAND_STATUSES, "status"),
            name="status_closed",
        ),
    )
