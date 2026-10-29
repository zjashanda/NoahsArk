"""Run and Attempt models.  The five axes are always independent columns."""

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

EXECUTION_STATUS = ("NOT_STARTED", "RUNNING", "COMPLETED", "ABORTED", "SKIPPED")
VALIDITY_STATUS = ("VALID", "INVALID", "BLOCKED", "UNKNOWN")
BUSINESS_VERDICT = ("PASS", "FAIL", "EXPECTED", "WARN", "NEEDS_REVIEW", "NOT_EVALUATED")
EVIDENCE_STATUS = ("COMPLETE", "INCOMPLETE", "CONFLICTED", "UNVERIFIED")
VERIFICATION_STATUS = ("PASS", "FAIL", "NOT_RUN")
FAILURE_CLASSIFICATION = (
    "INVALID_INPUT",
    "INVALID_ENVIRONMENT",
    "INVALID_EVIDENCE",
    "VALID_FAILURE",
    "BLOCKED",
    "STOPPED",
    "UNSUPPORTED",
    "INFRA_ERROR",
)


def five_axis_columns() -> tuple:
    return (
        CheckConstraint(enum_check("execution_status", EXECUTION_STATUS, "execution_status"), name="execution_status_closed"),
        CheckConstraint(enum_check("validity_status", VALIDITY_STATUS, "validity_status"), name="validity_status_closed"),
        CheckConstraint(enum_check("business_verdict", BUSINESS_VERDICT, "business_verdict"), name="business_verdict_closed"),
        CheckConstraint(enum_check("evidence_status", EVIDENCE_STATUS, "evidence_status"), name="evidence_status_closed"),
        CheckConstraint(enum_check("verification_status", VERIFICATION_STATUS, "verification_status"), name="verification_status_closed"),
    )


class Run(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    __tablename__ = "runs"

    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.task_id"), nullable=False, index=True
    )
    revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_revisions.revision_id"), nullable=False, index=True
    )
    bundle_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(32), nullable=False)

    execution_status: Mapped[str] = mapped_column(String(32), nullable=False)
    validity_status: Mapped[str] = mapped_column(String(32), nullable=False)
    business_verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(32), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False)

    node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("nodes.node_id"))
    device_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.device_id"))
    # Lease owns the authoritative run reference.  Keeping this column without a
    # FK avoids a runs <-> leases cycle at table-create time.
    lease_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    lease_epoch: Mapped[int | None] = mapped_column(Integer)
    communication_state: Mapped[str] = mapped_column(String(16), nullable=False)
    occupancy_state: Mapped[str] = mapped_column(String(16), nullable=False)
    execution_permit: Mapped[str] = mapped_column(String(16), nullable=False)
    formal_denominator_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attempt_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    cleanup_receipt_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    evidence_manifest_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    stop_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stop_reason: Mapped[str | None] = mapped_column(Text)
    failure_classification: Mapped[str | None] = mapped_column(String(32))
    error_code: Mapped[str | None] = mapped_column(String(80))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        *five_axis_columns(),
        CheckConstraint(enum_check("mode", ("static", "smoke", "formal"), "mode"), name="mode_closed"),
        CheckConstraint(
            enum_check(
                "lifecycle_status",
                ("CREATED", "DISPATCHED", "RUNNING", "FINISHING", "COMPLETED", "STOPPED", "ABORTED", "BLOCKED"),
                "lifecycle_status",
            ),
            name="lifecycle_status_closed",
        ),
        CheckConstraint(enum_check("communication_state", ("ONLINE", "STALE", "OFFLINE"), "communication_state"), name="communication_state_closed"),
        CheckConstraint(enum_check("occupancy_state", ("IDLE", "OCCUPIED", "RELEASING"), "occupancy_state"), name="occupancy_state_closed"),
        CheckConstraint(enum_check("execution_permit", ("GRANTED", "NOT_GRANTED", "SUSPENDED"), "execution_permit"), name="execution_permit_closed"),
        CheckConstraint(
            "failure_classification IS NULL OR " + enum_check("failure_classification", FAILURE_CLASSIFICATION, "failure_classification"),
            name="failure_classification_closed",
        ),
    )


class Attempt(Base, SchemaVersionMixin, ProvenanceMixin, CreatedAtMixin):
    __tablename__ = "attempts"

    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.run_id"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.case_id"), nullable=False, index=True
    )
    case_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    run_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    attempt_ordinal: Mapped[int] = mapped_column(Integer, nullable=False)

    execution_status: Mapped[str] = mapped_column(String(32), nullable=False)
    validity_status: Mapped[str] = mapped_column(String(32), nullable=False)
    business_verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(32), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False)

    evidence_origin: Mapped[str] = mapped_column(String(16), nullable=False)
    denominator_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retry_of_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attempts.attempt_id")
    )
    flaky_suspect: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("nodes.node_id"))
    device_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.device_id"))
    receipt_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    evidence_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    anomaly_event_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    facts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    failure_classification: Mapped[str | None] = mapped_column(String(32))
    failure_detail: Mapped[str | None] = mapped_column(String(120))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        *five_axis_columns(),
        UniqueConstraint("run_id", "case_id", "attempt_ordinal", name="uq_attempts_run_case_ordinal"),
        CheckConstraint(enum_check("run_mode", ("static", "smoke", "formal"), "run_mode"), name="run_mode_closed"),
        CheckConstraint(enum_check("evidence_origin", ("real_device", "simulated", "replay", "imported"), "evidence_origin"), name="evidence_origin_closed"),
        CheckConstraint(
            "failure_classification IS NULL OR " + enum_check("failure_classification", FAILURE_CLASSIFICATION, "failure_classification"),
            name="failure_classification_closed",
        ),
        CheckConstraint("case_version >= 1", name="case_version_positive"),
        CheckConstraint("attempt_ordinal >= 1", name="attempt_ordinal_positive"),
    )
