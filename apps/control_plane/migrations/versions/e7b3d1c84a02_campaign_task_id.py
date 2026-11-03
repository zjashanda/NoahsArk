"""link test campaigns to tasks

Revision ID: e7b3d1c84a02
Revises: d9c3e5a71b04
Create Date: 2026-11-02 18:30:00.000000

Optional owning-Task link for deterministic test campaigns.  ``task_id`` is
nullable and ``ON DELETE SET NULL``:

* Existing campaigns are intentionally **not** backfilled.  Rows created before
  this revision keep ``task_id = NULL`` and are documented as unassociated
  legacy campaigns.
* Deleting a Task nulls the link and leaves the campaign untouched, so Task
  deletion semantics do not change.

The index supports ``GET /api/v1/test-campaigns?task_id=<uuid>`` without a
sequential scan as campaigns accumulate per Task.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7b3d1c84a02"
down_revision: str | None = "d9c3e5a71b04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "test_campaigns",
        sa.Column("task_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_test_campaigns_task_id_tasks"),
        "test_campaigns",
        "tasks",
        ["task_id"],
        ["task_id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_test_campaigns_task_id"),
        "test_campaigns",
        ["task_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_test_campaigns_task_id"), table_name="test_campaigns")
    op.drop_constraint(
        op.f("fk_test_campaigns_task_id_tasks"),
        "test_campaigns",
        type_="foreignkey",
    )
    op.drop_column("test_campaigns", "task_id")
