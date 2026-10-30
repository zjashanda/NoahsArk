"""Task, revision, approval, gate and case models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAtMixin, ProvenanceMixin, SchemaVersionMixin, enum_check


class Task(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    __tablename__ = "tasks"

    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    task_category: Mapped[str] = mapped_column(String(48), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    entry_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    origin: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    lead_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.agent_id"), nullable=False
    )
    lead_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    current_revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    revision_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(enum_check("task_category", ("voice_interaction",), "category"), name="category_closed"),
        CheckConstraint(
            enum_check("entry_mode", ("conversation", "file", "spreadsheet", "form", "template"), "entry_mode"),
            name="entry_mode_closed",
        ),
        CheckConstraint(
            enum_check(
                "status",
                ("DRAFT", "REVIEW", "APPROVED", "EXECUTING", "VERIFYING", "REPORTED", "CLOSED", "BLOCKED", "STOPPED", "ARCHIVED"),
                "status",
            ),
            name="status_closed",
        ),
    )


class TaskRevision(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    __tablename__ = "task_revisions"

    revision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.task_id"), nullable=False, index=True
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_revisions.revision_id")
    )
    change_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    change_reason: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    content: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    immutable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    content_digest: Mapped[str] = mapped_column(String(80), nullable=False)
    frozen_scope: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approval_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    bundle_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    superseded_by_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_revisions.revision_id")
    )

    __table_args__ = (
        UniqueConstraint("task_id", "revision_number", name="uq_task_revisions_task_number"),
        CheckConstraint(
            enum_check(
                "change_kind",
                ("initial", "clarification", "scope_change", "repair", "regeneration", "knowledge_update"),
                "change_kind",
            ),
            name="change_kind_closed",
        ),
        CheckConstraint(
            enum_check("status", ("DRAFT", "FROZEN", "APPROVED", "SUPERSEDED", "REJECTED"), "status"),
            name="status_closed",
        ),
    )


class Approval(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    __tablename__ = "approvals"

    approval_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.task_id"), nullable=False, index=True
    )
    revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_revisions.revision_id"), nullable=False, index=True
    )
    submitter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    approver_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    revision_content_digest: Mapped[str] = mapped_column(String(80), nullable=False)
    scope_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    self_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prevent_self_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    wait_timer_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawn_reason: Mapped[str | None] = mapped_column(Text)
    superseded_by_approval_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("approvals.approval_id")
    )
    idempotency_key: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)

    __table_args__ = (
        Index(
            "uq_approvals_one_approved_per_revision",
            "revision_id",
            unique=True,
            postgresql_where=text("decision = 'APPROVED'"),
        ),
        CheckConstraint(
            enum_check("decision", ("PENDING", "APPROVED", "REJECTED", "WITHDRAWN", "SUPERSEDED"), "decision"),
            name="decision_closed",
        ),
    )


class Gate(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    __tablename__ = "gates"

    gate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.task_id"), nullable=False, index=True
    )
    revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_revisions.revision_id"), nullable=False, index=True
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    gate_code: Mapped[str] = mapped_column(String(8), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    entered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evaluated_by: Mapped[str | None] = mapped_column(String(120))
    blocker_owner: Mapped[str | None] = mapped_column(String(200))
    blockers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evidence_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("task_id", "revision_id", "gate_code", name="uq_gates_task_revision_code"),
        CheckConstraint(
            enum_check("gate_code", ("G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7"), "gate_code"),
            name="gate_code_closed",
        ),
        CheckConstraint(
            enum_check("status", ("PENDING", "IN_PROGRESS", "PASSED", "FAILED", "BLOCKED", "SKIPPED"), "status"),
            name="status_closed",
        ),
    )


class Case(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    __tablename__ = "cases"

    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.task_id"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    case_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content_digest: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    steps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    required_inputs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    validity_conditions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    required_evidence: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    assertion_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    frozen_by_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_revisions.revision_id")
    )
    supersedes_case_version: Mapped[int | None] = mapped_column(Integer)
    superseded_by_case_version: Mapped[int | None] = mapped_column(Integer)
    run_mode: Mapped[str | None] = mapped_column(String(16))
    reference_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("task_id", "name", "case_version", name="uq_cases_task_name_version"),
        CheckConstraint(
            enum_check("status", ("ACTIVE", "SUPERSEDED", "RETIRED"), "status"),
            name="status_closed",
        ),
        CheckConstraint(
            "run_mode IS NULL OR run_mode IN ('static','smoke','formal')",
            name="run_mode_closed",
        ),
    )
