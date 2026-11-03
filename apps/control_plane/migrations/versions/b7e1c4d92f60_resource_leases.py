"""add resource leases and command cancel flag

Revision ID: b7e1c4d92f60
Revises: 8d41c6a9e2b7
Create Date: 2026-11-02 09:00:00.000000

One row per resource a campaign holds: the node itself (``node:win009``) plus
the serial/audio endpoints the platform knows about.  A *partial* unique index
on ``resource_key`` where ``status = 'ACTIVE'`` is the concurrency authority: it
makes a second active holder impossible even if two API transactions race.

``node_commands.cancel_requested_at`` is the platform half of a user STOP for a
runner the node has already claimed.  The node agent polls it and stops the
local process; no inbound channel to the node is introduced.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e1c4d92f60"
down_revision: str | None = "8d41c6a9e2b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEASE_STATUSES = ("ACTIVE", "RELEASED", "EXPIRED")


def upgrade() -> None:
    op.create_table(
        "resource_leases",
        sa.Column("lease_id", sa.UUID(), nullable=False),
        sa.Column("resource_key", sa.String(length=300), nullable=False),
        sa.Column("owner_type", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'ACTIVE'"),
            nullable=False,
        ),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_reason", sa.String(length=80), nullable=True),
        sa.CheckConstraint(
            "status IN (" + ", ".join(f"'{state}'" for state in LEASE_STATUSES) + ")",
            name=op.f("ck_resource_leases_status_closed"),
        ),
        sa.PrimaryKeyConstraint("lease_id", name=op.f("pk_resource_leases")),
    )
    op.create_index(
        "uq_resource_leases_active_key",
        "resource_leases",
        ["resource_key"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(
        "ix_resource_leases_owner",
        "resource_leases",
        ["owner_type", "owner_id"],
        unique=False,
    )
    op.create_index(
        "ix_resource_leases_status_expires",
        "resource_leases",
        ["status", "expires_at"],
        unique=False,
    )

    op.add_column(
        "node_commands",
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("node_commands", "cancel_requested_at")
    op.drop_index(
        "ix_resource_leases_status_expires", table_name="resource_leases"
    )
    op.drop_index("ix_resource_leases_owner", table_name="resource_leases")
    op.drop_index(
        "uq_resource_leases_active_key",
        table_name="resource_leases",
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.drop_table("resource_leases")
