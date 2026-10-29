"""w3 write requests

Revision ID: 7f3d2b91c4a5
Revises: c240583c8a27
Create Date: 2026-10-29 19:20:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7f3d2b91c4a5"
down_revision: Union[str, None] = "c240583c8a27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "write_requests",
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("display_id", sa.String(length=80), nullable=False),
        sa.Column("request_type", sa.String(length=16), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.String(length=120), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'REQUESTED'"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("requested_by", sa.UUID(), nullable=True),
        sa.Column("requested_role", sa.String(length=32), nullable=False),
        sa.Column("correlation_id", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.CheckConstraint(
            "request_type IN ('STOP', 'RELEASE')",
            name="ck_write_requests_request_type_closed",
        ),
        sa.CheckConstraint(
            "status IN ('REQUESTED', 'ACCEPTED', 'REJECTED')",
            name="ck_write_requests_status_closed",
        ),
        sa.PrimaryKeyConstraint("request_id", name="pk_write_requests"),
        sa.UniqueConstraint("display_id", name="uq_write_requests_display_id"),
    )


def downgrade() -> None:
    op.drop_table("write_requests")
