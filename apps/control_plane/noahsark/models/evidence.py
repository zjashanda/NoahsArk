"""Evidence, manifest, verdict, report and knowledge models."""

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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAtMixin, ProvenanceMixin, SchemaVersionMixin, enum_check
from .run import (
    five_axis_columns,
)


class EvidenceItem(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    __tablename__ = "evidence_items"

    evidence_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.task_id"), index=True
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.run_id"), index=True
    )
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attempts.attempt_id")
    )
    evidence_class: Mapped[str] = mapped_column(String(48), nullable=False)
    role: Mapped[str] = mapped_column(String(48), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    content_digest: Mapped[str | None] = mapped_column(String(80), unique=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    media_type: Mapped[str | None] = mapped_column(String(120))
    digest_scope: Mapped[str | None] = mapped_column(String(32))
    provenance: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    upload: Mapped[dict | None] = mapped_column(JSONB)
    locator: Mapped[dict | None] = mapped_column(JSONB)
    retention: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    access_level: Mapped[str] = mapped_column(String(48), nullable=False)
    classification: Mapped[dict | None] = mapped_column(JSONB)
    integrity: Mapped[dict | None] = mapped_column(JSONB)
    log_read: Mapped[dict | None] = mapped_column(JSONB)
    related_event_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    supersedes: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence_items.evidence_id")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    expected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    received: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        CheckConstraint(
            enum_check(
                "evidence_class",
                (
                    "raw_audio",
                    "device_log",
                    "serial_log",
                    "screenshot",
                    "execution_log",
                    "manifest",
                    "receipt",
                    "anomaly_event",
                    "linux_log_read",
                    "human_note",
                ),
                "evidence_class",
            ),
            name="evidence_class_closed",
        ),
        CheckConstraint(
            enum_check(
                "state",
                ("declared", "uploading", "partial", "complete", "verified", "conflicted", "unavailable", "quarantined"),
                "state",
            ),
            name="state_closed",
        ),
        CheckConstraint(
            enum_check("access_level", ("summary", "task_member", "evidence_reader", "system_internal"), "access_level"),
            name="access_level_closed",
        ),
        CheckConstraint(
            "digest_scope IS NULL OR digest_scope IN ('raw_bytes','canonical_json')",
            name="digest_scope_closed",
        ),
    )


class EvidenceManifest(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    __tablename__ = "evidence_manifests"

    manifest_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    predicate_type: Mapped[str] = mapped_column(String(80), nullable=False, default="noahsark.test-evidence/v1")
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.task_id"), nullable=False, index=True)
    revision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("task_revisions.revision_id"), nullable=False)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.run_id"), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    acceptance_level: Mapped[str] = mapped_column(String(8), nullable=False)
    test_level: Mapped[str] = mapped_column(String(8), nullable=False)
    node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("nodes.node_id"))
    device_identity: Mapped[dict | None] = mapped_column(JSONB)
    lease_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("leases.lease_id"))
    lease_epoch: Mapped[int | None] = mapped_column(Integer)
    endpoints: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    bundle: Mapped[dict | None] = mapped_column(JSONB)
    approval: Mapped[dict | None] = mapped_column(JSONB)
    timebase: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    cases: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evidence_items: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    required_evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    completeness: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    denominators: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    invalid_classification: Mapped[dict | None] = mapped_column(JSONB)
    anomalies: Mapped[dict | None] = mapped_column(JSONB)
    cleanup_receipt: Mapped[dict | None] = mapped_column(JSONB)
    node_receipt: Mapped[dict | None] = mapped_column(JSONB)
    linux_verification: Mapped[dict | None] = mapped_column(JSONB)
    archive: Mapped[dict | None] = mapped_column(JSONB)
    redaction: Mapped[dict | None] = mapped_column(JSONB)
    manifest_digest: Mapped[str | None] = mapped_column(String(80), unique=True)
    supersedes_manifest_digest: Mapped[str | None] = mapped_column(String(80))
    signatures: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)

    __table_args__ = (
        CheckConstraint(enum_check("mode", ("static", "smoke", "formal"), "mode"), name="mode_closed"),
        CheckConstraint(
            enum_check("acceptance_level", ("L0", "L1", "L2", "L3", "L4", "L5"), "acceptance_level"),
            name="acceptance_level_closed",
        ),
        CheckConstraint(
            enum_check("test_level", ("T1", "T2", "T3", "T4", "T5", "T6"), "test_level"),
            name="test_level_closed",
        ),
    )


class Verdict(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    __tablename__ = "verdicts"

    verdict_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.task_id"), nullable=False, index=True)
    revision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("task_revisions.revision_id"), nullable=False)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.run_id"), nullable=False, unique=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    acceptance_level: Mapped[str] = mapped_column(String(8), nullable=False)
    test_level: Mapped[str] = mapped_column(String(8), nullable=False)

    execution_status: Mapped[str] = mapped_column(String(32), nullable=False)
    validity_status: Mapped[str] = mapped_column(String(32), nullable=False)
    business_verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(32), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False)

    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    mode_outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    failure_class: Mapped[str] = mapped_column(String(32), nullable=False)
    formal_pass: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    case_results: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    denominator: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    pass_preconditions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    reasons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    anomalies: Mapped[dict | None] = mapped_column(JSONB)
    evidence_manifest: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    verification: Mapped[dict | None] = mapped_column(JSONB)
    cleanup_receipt: Mapped[dict | None] = mapped_column(JSONB)
    node_reported_status: Mapped[dict | None] = mapped_column(JSONB)
    decided_by: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verdict_digest: Mapped[str | None] = mapped_column(String(80), unique=True)
    supersedes_verdict_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("verdicts.verdict_id"))

    __table_args__ = (
        *five_axis_columns(),
        CheckConstraint(enum_check("mode", ("static", "smoke", "formal"), "mode"), name="mode_closed"),
        CheckConstraint(
            enum_check("decision", ("PASS", "FAIL", "INVALID", "BLOCKED", "STOPPED", "NEEDS_REVIEW", "NOT_EVALUATED", "NOT_APPLICABLE"), "decision"),
            name="decision_closed",
        ),
        CheckConstraint(
            enum_check("mode_outcome", ("PASS", "FAIL", "BLOCKED", "STOPPED", "NOT_EVALUATED", "NOT_APPLICABLE"), "mode_outcome"),
            name="mode_outcome_closed",
        ),
        CheckConstraint(
            enum_check(
                "failure_class",
                ("none", "invalid-input", "invalid-environment", "invalid-evidence", "blocked", "stopped", "infra-error", "valid-failure", "unsupported", "needs-review"),
                "failure_class",
            ),
            name="failure_class_closed",
        ),
        CheckConstraint(
            "NOT formal_pass OR (decision = 'PASS' AND mode = 'formal' AND failure_class = 'none' "
            "AND execution_status = 'COMPLETED' AND validity_status = 'VALID' AND business_verdict = 'PASS' "
            "AND evidence_status = 'COMPLETE' AND verification_status = 'PASS')",
            name="formal_pass_fail_closed",
        ),
    )


class Report(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    __tablename__ = "reports"

    report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.task_id"), nullable=False, index=True)
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("task_revisions.revision_id"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    lifecycle: Mapped[str] = mapped_column(String(32), nullable=False)
    denominator: Mapped[int | None] = mapped_column(Integer)
    disclosure: Mapped[str] = mapped_column(String(32), nullable=False)
    sections: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evidence_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    denominator_statement: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    runs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evidence_index_data: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    release_index: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    access: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    unresolved: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    redaction: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    report_digest: Mapped[str | None] = mapped_column(String(80), unique=True)
    notes: Mapped[str | None] = mapped_column(Text)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("task_id", "version", name="uq_reports_task_version"),
        CheckConstraint("lifecycle IN ('DRAFT','FROZEN','SUPERSEDED')", name="lifecycle_closed"),
    )


class KnowledgeItem(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    __tablename__ = "knowledge_items"

    knowledge_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    applicability: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_chain: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class KnowledgeCandidate(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    __tablename__ = "knowledge_candidates"

    candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    source_chain: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    applicability: Mapped[str] = mapped_column(String(300), nullable=False)
    proposed_by: Mapped[str] = mapped_column(String(120), nullable=False)
    automatic_promotion_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("automatic_promotion_allowed = false", name="no_automatic_promotion"),
        CheckConstraint("requires_human_review = true", name="human_review_required"),
    )
