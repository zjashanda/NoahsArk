"""add test campaigns

Revision ID: 8d41c6a9e2b7
Revises: 4d9b6e2f8a10
Create Date: 2026-10-31 21:00:00.000000

Deterministic test campaign records.  A campaign owns the intent (node,
scenario, rounds, bench) and exactly one ``test.run`` command; it intentionally
has no ``task_id`` and never starts an OpenCode supervisor session.

``summary`` holds the node-reported ``summary_final.json`` payload and
``rounds_data`` holds the per-round rows when the node reports them.  A missing
summary leaves both NULL so the platform can never mistake an artifact path for
a PASS verdict.

The reverse pointer ``node_commands.campaign_id`` lets the existing node result
handler find the campaign from the command that delivered the result.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8d41c6a9e2b7"
down_revision: str | None = "4d9b6e2f8a10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUSES = ("QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "TIMEOUT", "STOPPED")


def upgrade() -> None:
    op.create_table(
        "test_campaigns",
        sa.Column("campaign_id", sa.UUID(), nullable=False),
        sa.Column("node_id", sa.UUID(), nullable=False),
        sa.Column("scenario", sa.String(length=80), nullable=False),
        sa.Column("rounds", sa.Integer(), nullable=False),
        sa.Column("bench", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'QUEUED'"),
            nullable=False,
        ),
        sa.Column("command_id", sa.UUID(), nullable=True),
        sa.Column(
            "summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "rounds_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN (" + ", ".join(f"'{state}'" for state in STATUSES) + ")",
            name=op.f("ck_test_campaigns_status_closed"),
        ),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["nodes.node_id"],
            name=op.f("fk_test_campaigns_node_id_nodes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["command_id"],
            ["node_commands.command_id"],
            name=op.f("fk_test_campaigns_command_id_node_commands"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("campaign_id", name=op.f("pk_test_campaigns")),
    )
    op.create_index(
        op.f("ix_test_campaigns_node_id"),
        "test_campaigns",
        ["node_id"],
        unique=False,
    )
    op.create_index(
        "uq_test_campaigns_command_id",
        "test_campaigns",
        ["command_id"],
        unique=True,
    )

    # Reverse pointer from the command row: the node result handler resolves the
    # campaign from the command that delivered the result.
    op.add_column(
        "node_commands",
        sa.Column("campaign_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_node_commands_campaign_id_test_campaigns"),
        "node_commands",
        "test_campaigns",
        ["campaign_id"],
        ["campaign_id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_node_commands_campaign_id"),
        "node_commands",
        ["campaign_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_node_commands_campaign_id"), table_name="node_commands")
    op.drop_constraint(
        op.f("fk_node_commands_campaign_id_test_campaigns"),
        "node_commands",
        type_="foreignkey",
    )
    op.drop_column("node_commands", "campaign_id")
    op.drop_index("uq_test_campaigns_command_id", table_name="test_campaigns")
    op.drop_index(op.f("ix_test_campaigns_node_id"), table_name="test_campaigns")
    op.drop_table("test_campaigns")
