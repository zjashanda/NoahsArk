"""add test campaign artifacts

Revision ID: d9c3e5a71b04
Revises: b7e1c4d92f60
Create Date: 2026-11-02 17:00:00.000000

Downloadable evidence artifacts for deterministic test campaigns.  The node
uploads one zip per campaign/command after the runner finishes; the row stores
only metadata plus a relative ``storage_key``.  Bytes live below
``NOAHSARK_ARTIFACT_STORAGE_ROOT`` (``artifact_storage_root``) addressed by the
SHA-256 digest, so a client-supplied filename never becomes a path.

``uq_test_campaign_artifacts_campaign_name`` makes one artifact name per
campaign a database invariant: a retried upload with the same digest is
idempotent, a different digest is rejected by the service as immutable.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9c3e5a71b04"
down_revision: str | None = "b7e1c4d92f60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "test_campaign_artifacts",
        sa.Column("artifact_id", sa.UUID(), nullable=False),
        sa.Column("campaign_id", sa.UUID(), nullable=False),
        sa.Column("command_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("digest", sa.String(length=71), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("media_type", sa.String(length=128), nullable=False),
        sa.Column(
            "source",
            sa.String(length=32),
            server_default=sa.text("'node'"),
            nullable=False,
        ),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "size_bytes >= 0",
            name=op.f("ck_test_campaign_artifacts_size_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["test_campaigns.campaign_id"],
            name=op.f("fk_test_campaign_artifacts_campaign_id_test_campaigns"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["command_id"],
            ["node_commands.command_id"],
            name=op.f("fk_test_campaign_artifacts_command_id_node_commands"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("artifact_id", name=op.f("pk_test_campaign_artifacts")),
        sa.UniqueConstraint(
            "campaign_id",
            "name",
            name="uq_test_campaign_artifacts_campaign_name",
        ),
    )
    op.create_index(
        op.f("ix_test_campaign_artifacts_campaign_id"),
        "test_campaign_artifacts",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_test_campaign_artifacts_command_id"),
        "test_campaign_artifacts",
        ["command_id"],
        unique=False,
    )
    op.create_index(
        "ix_test_campaign_artifacts_campaign_uploaded",
        "test_campaign_artifacts",
        ["campaign_id", "uploaded_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_test_campaign_artifacts_campaign_uploaded",
        table_name="test_campaign_artifacts",
    )
    op.drop_index(
        op.f("ix_test_campaign_artifacts_command_id"),
        table_name="test_campaign_artifacts",
    )
    op.drop_index(
        op.f("ix_test_campaign_artifacts_campaign_id"),
        table_name="test_campaign_artifacts",
    )
    op.drop_table("test_campaign_artifacts")
