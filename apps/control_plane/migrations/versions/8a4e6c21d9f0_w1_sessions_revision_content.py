"""w1 sessions and revision content

Revision ID: 8a4e6c21d9f0
Revises: 7f3d2b91c4a5
Create Date: 2026-10-29 23:10:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8a4e6c21d9f0"
down_revision: str | None = "7f3d2b91c4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "task_revisions",
        sa.Column(
            "content",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_table(
        "sessions",
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=80), nullable=False),
        sa.Column("actor", sa.String(length=200), nullable=True),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("role_code", sa.String(length=32), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "source",
            sa.String(length=64),
            server_default=sa.text("'control-plane'"),
            nullable=False,
        ),
        sa.Column(
            "seed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "expires_at > issued_at", name=op.f("ck_sessions_expiry_after_issue")
        ),
        sa.PrimaryKeyConstraint("session_id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_sessions_token_hash")),
    )


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_column("task_revisions", "content")
