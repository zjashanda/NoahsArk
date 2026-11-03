"""Bootstrap the two local development accounts from environment secrets.

Usage (secrets are read only from the environment; never from argv or files)::

    export NOAHSARK_ADMIN_PASSWORD=...
    export NOAHSARK_OBSERVER_PASSWORD=...
    python -m noahsark.bootstrap_accounts

The command upserts ``bszheng`` (ADMIN, all capabilities) and ``test001``
(OBSERVER, READ only).  Only Argon2id digests are written.  Nothing prints the
plaintext, the digest, or the database URL; the output is limited to account,
role and action metadata.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from .config import settings
from .domain.permissions import ROLE_CAPABILITIES
from .models import Role, User
from .services.passwords import (
    WeakSecretError,
    hash_password,
    is_argon2_hash,
    validate_bootstrap_secret,
    verify_password,
)

ADMIN_ENV_VAR = "NOAHSARK_ADMIN_PASSWORD"
OBSERVER_ENV_VAR = "NOAHSARK_OBSERVER_PASSWORD"
ADMIN_USERNAME = "bszheng"
TEST_USERNAME = "test001"

_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")

ROLE_ROWS: dict[str, dict[str, Any]] = {
    "ADMIN": {
        "name": "平台管理员（本地账号）",
        "scope": "全局",
        "access_level": "ADMIN_ONLY",
        "sort_order": 0,
    },
    "OBSERVER": {
        "name": "观察者",
        "scope": "任务",
        "access_level": "SUMMARY_INDEX",
        "sort_order": 4,
    },
}


@dataclass(frozen=True)
class AccountSpec:
    username: str
    role_code: str
    display_name: str
    env_var: str


ACCOUNTS: tuple[AccountSpec, ...] = (
    AccountSpec(ADMIN_USERNAME, "ADMIN", "bszheng（超级管理员）", ADMIN_ENV_VAR),
    AccountSpec(TEST_USERNAME, "OBSERVER", "test001（只读测试账号）", OBSERVER_ENV_VAR),
)


def _read_secret(env_var: str, username: str) -> str:
    raw = os.environ.get(env_var)
    try:
        return validate_bootstrap_secret(raw, username=username)
    except WeakSecretError as exc:
        raise WeakSecretError(f"{env_var}: {exc}") from exc


async def _ensure_role(session: AsyncSession, role_code: str) -> None:
    capabilities = ROLE_CAPABILITIES.get(role_code)
    if capabilities is None:  # fail closed; never invent a role capability set
        raise RuntimeError(f"no capability definition for role {role_code!r}")
    meta = ROLE_ROWS[role_code]
    statement = (
        pg_insert(Role)
        .values(
            role_code=role_code,
            name=meta["name"],
            scope=meta["scope"],
            access_level=meta["access_level"],
            capabilities=sorted(capability.value for capability in capabilities),
            sort_order=meta["sort_order"],
            created_at=datetime.now(UTC),
            source="bootstrap",
            seed=False,
        )
        .on_conflict_do_nothing(index_elements=["role_code"])
    )
    await session.execute(statement)


async def _upsert_account(
    session: AsyncSession, spec: AccountSpec, secret_value: str
) -> dict[str, Any]:
    digest = hash_password(secret_value)
    if not is_argon2_hash(digest) or not verify_password(secret_value, digest):
        raise RuntimeError("Argon2 hashing self-check failed")
    now = datetime.now(UTC)

    existing = (
        await session.execute(select(User).where(User.display_id == spec.username))
    ).scalar_one_or_none()
    if existing is None:
        session.add(
            User(
                user_id=uuid.uuid5(_NAMESPACE, f"user:{spec.username}"),
                display_id=spec.username,
                name=spec.display_name,
                actor_kind="human",
                role_code=spec.role_code,
                status="ACTIVE",
                password_hash=digest,
                created_at=now,
                updated_at=now,
                schema_version="1.0",
                source="bootstrap",
                seed=False,
            )
        )
        action = "created"
    else:
        existing.name = spec.display_name
        existing.actor_kind = "human"
        existing.role_code = spec.role_code
        existing.status = "ACTIVE"
        existing.password_hash = digest
        existing.updated_at = now
        existing.source = "bootstrap"
        existing.seed = False
        action = "updated"

    return {
        "display_id": spec.username,
        "role_code": spec.role_code,
        "status": "ACTIVE",
        "action": action,
    }


async def bootstrap_accounts(
    *,
    database_url: str | None = None,
    admin_secret: str | None = None,
    test_secret: str | None = None,
) -> dict[str, Any]:
    """Create or update the two development accounts.

    Secrets default to the environment variables.  Callers may pass values
    directly (tests do); neither path logs or returns them.
    """

    admin_value = (
        _read_secret(ADMIN_ENV_VAR, ADMIN_USERNAME)
        if admin_secret is None
        else validate_bootstrap_secret(admin_secret, username=ADMIN_USERNAME)
    )
    test_value = (
        _read_secret(OBSERVER_ENV_VAR, TEST_USERNAME)
        if test_secret is None
        else validate_bootstrap_secret(test_secret, username=TEST_USERNAME)
    )

    url = database_url or settings.database_url
    if not url or url.startswith("sqlite"):
        raise RuntimeError(
            "DATABASE_URL must point at PostgreSQL; refusing to bootstrap without an authority"
        )

    engine = create_async_engine(url)
    try:
        async with (
            engine.begin() as connection,
            AsyncSession(connection, expire_on_commit=False) as session,
        ):
            for spec in ACCOUNTS:
                await _ensure_role(session, spec.role_code)
            # Flush roles before user inserts so the FK is always satisfied,
            # independent of SQLAlchemy's unit-of-work ordering.
            await session.flush()
            secrets_by_username = {
                ADMIN_USERNAME: admin_value,
                TEST_USERNAME: test_value,
            }
            accounts = [
                await _upsert_account(
                    session, spec, secrets_by_username[spec.username]
                )
                for spec in ACCOUNTS
            ]
            # The engine-level transaction commits on exit, but the session
            # must flush pending inserts first; otherwise the last account is
            # silently dropped when no later query triggers autoflush.
            await session.flush()
        return {
            "accounts": accounts,
            "roles": [spec.role_code for spec in ACCOUNTS],
            "secrets_printed": False,
        }
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create/update bszheng (ADMIN) and test001 (OBSERVER) using secrets "
            "from NOAHSARK_ADMIN_PASSWORD / "
            "NOAHSARK_OBSERVER_PASSWORD."
        )
    )
    parser.parse_args(argv)
    try:
        result = asyncio.run(bootstrap_accounts())
    except WeakSecretError as exc:
        print(f"bootstrap refused: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"bootstrap failed: {exc}", file=sys.stderr)
        return 1
    print("bootstrap ok; Argon2id digests stored; secrets not printed")
    for account in result["accounts"]:
        print(
            f"  {account['display_id']}: role={account['role_code']} "
            f"status={account['status']} action={account['action']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
