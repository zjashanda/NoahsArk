"""add supervisor session binding

Revision ID: f6a2c8d41e07
Revises: b2f1a4c7d902
Create Date: 2026-10-30 15:10:00.000000

Adds the durable OpenCode supervisor binding for a task.  The row stores only a
prompt digest/byte count, an optional remote OpenCode session id and sanitized
result metadata.  A partial unique index enforces one active binding per task
while keeping terminal rows for history.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a2c8d41e07"
down_revision: str | None = "b2f1a4c7d902"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTIVE_STATES = (
    "PENDING",
    "BINDING",
    "READY",
    "DISPATCHED",
    "RUNNING",
    "STOP_REQUESTED",
)


def upgrade() -> None:
    op.create_table(
        "supervisor_sessions",
        sa.Column("supervisor_session_id", sa.UUID(), nullable=False),
        sa.Column("display_id", sa.String(length=80), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("revision_id", sa.UUID(), nullable=False),
        sa.Column(
            "state",
            sa.String(length=32),
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column("remote_session_id", sa.String(length=200), nullable=True),
        sa.Column("prompt_digest", sa.String(length=80), nullable=False),
        sa.Column("prompt_bytes", sa.Integer(), nullable=False),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("result_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "schema_version",
            sa.String(length=16),
            server_default=sa.text("'1.0'"),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(length=64),
            server_default=sa.text("'control-plane'"),
            nullable=False,
        ),
        sa.Column(
            "seed", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('PENDING', 'BINDING', 'READY', 'DISPATCHED', 'RUNNING', "
            "'COMPLETED', 'FAILED', 'STOP_REQUESTED', 'STOPPED')",
            name=op.f("ck_supervisor_sessions_state_closed"),
        ),
        sa.CheckConstraint(
            "prompt_bytes >= 0",
            name=op.f("ck_supervisor_sessions_prompt_bytes_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["task_revisions.revision_id"],
            name=op.f("fk_supervisor_sessions_revision_id_task_revisions"),
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.task_id"],
            name=op.f("fk_supervisor_sessions_task_id_tasks"),
        ),
        sa.PrimaryKeyConstraint(
            "supervisor_session_id", name=op.f("pk_supervisor_sessions")
        ),
        sa.UniqueConstraint(
            "display_id", name=op.f("uq_supervisor_sessions_display_id")
        ),
        sa.UniqueConstraint(
            "remote_session_id",
            name=op.f("uq_supervisor_sessions_remote_session_id"),
        ),
    )
    op.create_index(
        op.f("ix_supervisor_sessions_revision_id"),
        "supervisor_sessions",
        ["revision_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supervisor_sessions_task_id"),
        "supervisor_sessions",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        "uq_supervisor_sessions_active_task",
        "supervisor_sessions",
        ["task_id"],
        unique=True,
        postgresql_where=sa.text(
            "state IN (" + ", ".join(f"'{state}'" for state in ACTIVE_STATES) + ")"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_supervisor_sessions_active_task", table_name="supervisor_sessions"
    )
    op.drop_index(
        op.f("ix_supervisor_sessions_task_id"), table_name="supervisor_sessions"
    )
    op.drop_index(
        op.f("ix_supervisor_sessions_revision_id"), table_name="supervisor_sessions"
    )
    op.drop_table("supervisor_sessions")
