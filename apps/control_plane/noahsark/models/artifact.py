"""Downloadable evidence artifacts attached to a test campaign.

The node bundles a finished run's evidence (serial logs, tool.log, results.csv,
summary_final.json, rounds.csv) into a zip and uploads it after the runner
exits.  The blob is stored by the control plane; this row is the immutable
metadata that makes it discoverable and downloadable.

``storage_key`` is a *relative* key below the configured artifact root.  It is
generated from the campaign UUID and the SHA-256 digest, never from the
client-supplied name, so a hostile name can never become a filesystem path.
The display ``name`` is sanitized to a single path segment before it is stored.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAtMixin


class TestCampaignArtifact(Base, CreatedAtMixin):
    __tablename__ = "test_campaign_artifacts"

    artifact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_campaigns.campaign_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    command_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("node_commands.command_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    digest: Mapped[str] = mapped_column(String(71), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    # Retained for provenance; the storage layer never trusts it.
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="node")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "campaign_id", "name", name="uq_test_campaign_artifacts_campaign_name"
        ),
        CheckConstraint("size_bytes >= 0", name="size_non_negative"),
        Index("ix_test_campaign_artifacts_campaign_uploaded", "campaign_id", "uploaded_at"),
    )
