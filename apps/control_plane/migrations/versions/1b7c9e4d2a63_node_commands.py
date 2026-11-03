"""add node command queue

Revision ID: 1b7c9e4d2a63
Revises: f6a2c8d41e07
Create Date: 2026-10-31 10:00:00.000000

Platform-to-node tool invocations.  The platform owns the row lifecycle and the
node may only update the result columns of a command addressed to itself.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "1b7c9e4d2a63"
down_revision: str | None = "f6a2c8d41e07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUSES = ("QUEUED", "SENT", "RUNNING", "SUCCEEDED", "FAILED", "TIMEOUT")


def upgrade() -> None:
    op.create_table(
        "node_commands",
        sa.Column("command_id", sa.UUID(), nullable=False),
        sa.Column("node_id", sa.UUID(), nullable=False),
        sa.Column("tool_id", sa.String(length=80), nullable=False),
        sa.Column(
            "args_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'QUEUED'"),
            nullable=False,
        ),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("stdout", sa.Text(), nullable=True),
        sa.Column("stderr", sa.Text(), nullable=True),
        sa.Column(
            "truncated", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("created_by", sa.String(length=200), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN (" + ", ".join(f"'{state}'" for state in STATUSES) + ")",
            name=op.f("ck_node_commands_status_closed"),
        ),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["nodes.node_id"],
            name=op.f("fk_node_commands_node_id_nodes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("command_id", name=op.f("pk_node_commands")),
    )
    op.create_index(
        op.f("ix_node_commands_node_id"),
        "node_commands",
        ["node_id"],
        unique=False,
    )
    op.create_index(
        "ix_node_commands_node_status_created",
        "node_commands",
        ["node_id", "status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_node_commands_node_status_created", table_name="node_commands")
    op.drop_index(op.f("ix_node_commands_node_id"), table_name="node_commands")
    op.drop_table("node_commands")
