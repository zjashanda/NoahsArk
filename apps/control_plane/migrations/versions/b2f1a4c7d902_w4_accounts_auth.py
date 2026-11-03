"""w4 local accounts and password hashes

Revision ID: b2f1a4c7d902
Revises: 8a4e6c21d9f0
Create Date: 2026-10-30 09:40:00.000000

Adds the Argon2id password digest to ``users`` and allows the application
``ADMIN`` role code alongside the legacy ``SUPER_ADMIN`` seed row.  The column
is nullable: service identities and pre-existing prototype rows keep no local
password and therefore cannot use the development login endpoint.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2f1a4c7d902"
down_revision: str | None = "8a4e6c21d9f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE_CODES = ("SUPER_ADMIN", "ADMIN", "SESSION_MANAGER", "APPROVER", "OBSERVER")
LEGACY_ROLE_CODES = ("SUPER_ADMIN", "SESSION_MANAGER", "APPROVER", "OBSERVER")


def _role_check(values: Sequence[str]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"role_code IN ({quoted})"


def upgrade() -> None:
    op.drop_constraint(op.f("ck_roles_role_code_closed"), "roles", type_="check")
    op.create_check_constraint(
        "role_code_closed", "roles", _role_check(ROLE_CODES)
    )
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    # Destructive by design: local password digests cannot be recovered once
    # dropped, and ADMIN rows must be removed before the narrow role check can
    # be restored.
    op.drop_column("users", "password_hash")
    op.drop_constraint(op.f("ck_roles_role_code_closed"), "roles", type_="check")
    op.create_check_constraint(
        "role_code_closed", "roles", _role_check(LEGACY_ROLE_CODES)
    )
