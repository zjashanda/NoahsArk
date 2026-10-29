"""Intake draft model backing the read-only intake projections.

The W1 schema did not include intake drafts.  W2 needs a first-class read model
for ``/api/v1/intake/drafts``; this table is added by a forward-only migration.
"""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ProvenanceMixin, SchemaVersionMixin, TimestampMixin, enum_check


class IntakeDraft(Base, SchemaVersionMixin, ProvenanceMixin, TimestampMixin):
    __tablename__ = "intake_drafts"

    draft_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    entry_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conflict_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gap_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    owner_role: Mapped[str] = mapped_column(String(80), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    facts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    conflicts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    gaps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    freshness: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        CheckConstraint(
            enum_check("entry_mode", ("conversation", "file", "spreadsheet", "form", "template"), "entry_mode"),
            name="entry_mode_closed",
        ),
        CheckConstraint(
            enum_check("stage", ("DRAFT", "REVIEW", "FROZEN", "CONVERTED", "ABANDONED"), "stage"),
            name="stage_closed",
        ),
    )
