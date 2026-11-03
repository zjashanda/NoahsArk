"""add task execution context

Revision ID: 4d9b6e2f8a10
Revises: 1b7c9e4d2a63
Create Date: 2026-10-31 11:00:00.000000

Stores the immutable-at-creation snapshot of the nodes and devices a task was
scheduled against.  The snapshot is the task's execution context: it exists so
the prompt and later read models can name the selected resources without
depending on live topology that may change afterwards.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4d9b6e2f8a10"
down_revision: str | None = "1b7c9e4d2a63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column(
            "execution_context",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("tasks", "execution_context")
