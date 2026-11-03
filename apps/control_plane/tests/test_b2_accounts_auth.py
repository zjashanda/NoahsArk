"""B2 local accounts and development session authentication.

Unit-level checks always run.  Database-backed checks require the seeded
PostgreSQL authority and skip cleanly otherwise.  Test credentials are
generated at runtime and are never written to the repository or printed.
"""

from __future__ import annotations

import asyncio
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import asyncpg
import pytest
from fastapi.testclient import TestClient

from noahsark.bootstrap_accounts import (
    ADMIN_ENV_VAR,
    ADMIN_USERNAME,
    OBSERVER_ENV_VAR,
    TEST_USERNAME,
    bootstrap_accounts,
)
from noahsark.config import settings
from noahsark.domain.permissions import (
    ALL_CAPABILITIES,
    Capability,
    capabilities_for,
    ensure_capability,
)
from noahsark.errors import ApiError
from noahsark.main import app
from noahsark.seed import seed_database
from noahsark.services import passwords, sessions

DATABASE_URL = os.environ.get("DATABASE_URL") or settings.database_url
requires_db = pytest.mark.skipif(
    not DATABASE_URL or DATABASE_URL.startswith("sqlite"),
    reason="DATABASE_URL is not configured for PostgreSQL; skipping B2 DB tests",
)

ADMIN_SECRET = secrets.token_urlsafe(24)
TEST_SECRET = secrets.token_urlsafe(24)
client = TestClient(app)


def _dsn() -> str:
    assert DATABASE_URL
    return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


def _run(coro):
    return asyncio.run(coro)


async def _fetch(query: str, *args):
    connection = await asyncpg.connect(_dsn())
    try:
        return await connection.fetch(query, *args)
    finally:
        await connection.close()


async def _execute(query: str, *args) -> None:
    connection = await asyncpg.connect(_dsn())
    try:
        await connection.execute(query, *args)
    finally:
        await connection.close()


@pytest.fixture(scope="module")
def accounts_database():
    try:
        _run(_fetch("SELECT 1"))
    except (OSError, asyncpg.PostgresError) as exc:  # pragma: no cover
        pytest.skip(f"PostgreSQL not reachable: {exc.__class__.__name__}")
    _run(seed_database(reset=True))
    _run(bootstrap_accounts(admin_secret=ADMIN_SECRET, test_secret=TEST_SECRET))
    return True


def _login(username: str, secret_value: str) -> dict:
    response = client.post(
        "/api/v1/auth/dev-login",
        json={"username": username, "password": secret_value},
    )
    return response


# ---------------------------------------------------------------------------
# Argon2 and capability invariants (no database)
# ---------------------------------------------------------------------------


def test_argon2_hash_differs_from_plaintext_and_verifies():
    digest = passwords.hash_password(ADMIN_SECRET)
    assert digest != ADMIN_SECRET
    assert ADMIN_SECRET not in digest
    assert digest.startswith("$argon2id$")
    assert passwords.verify_password(ADMIN_SECRET, digest) is True
    assert passwords.verify_password(TEST_SECRET, digest) is False


def test_argon2_salts_are_unique_per_hash():
    first = passwords.hash_password(ADMIN_SECRET)
    second = passwords.hash_password(ADMIN_SECRET)
    assert first != second
    assert passwords.verify_password(ADMIN_SECRET, first)
    assert passwords.verify_password(ADMIN_SECRET, second)


def test_bootstrap_policy_refuses_empty_and_default_values():
    for bad in (None, "", "   ", "password", "changeme", "test001"):
        with pytest.raises(passwords.WeakSecretError):
            passwords.validate_bootstrap_secret(bad, username=ADMIN_USERNAME)
    with pytest.raises(passwords.WeakSecretError):
        passwords.validate_bootstrap_secret(ADMIN_SECRET, username=ADMIN_SECRET)
    with pytest.raises(passwords.WeakSecretError):
        passwords.validate_bootstrap_secret(f" {ADMIN_SECRET}", username=ADMIN_USERNAME)


def test_bootstrap_reads_the_required_environment_names(monkeypatch):
    admin_value = secrets.token_urlsafe(24)
    observer_value = secrets.token_urlsafe(24)
    monkeypatch.setenv(ADMIN_ENV_VAR, admin_value)
    monkeypatch.setenv(OBSERVER_ENV_VAR, observer_value)

    # Validation happens before the database check; a SQLite authority is
    # therefore rejected only after both environment secrets were accepted.
    with pytest.raises(RuntimeError) as exc:
        _run(bootstrap_accounts(database_url="sqlite+aiosqlite:///:memory:"))

    message = str(exc.value)
    assert "PostgreSQL" in message
    assert admin_value not in message
    assert observer_value not in message
    assert ADMIN_ENV_VAR == "NOAHSARK_ADMIN_PASSWORD"
    assert OBSERVER_ENV_VAR == "NOAHSARK_OBSERVER_PASSWORD"


def test_bootstrap_refuses_a_missing_environment_secret(monkeypatch):
    monkeypatch.setenv(ADMIN_ENV_VAR, secrets.token_urlsafe(24))
    monkeypatch.delenv(OBSERVER_ENV_VAR, raising=False)

    with pytest.raises(passwords.WeakSecretError) as exc:
        _run(bootstrap_accounts(database_url="sqlite+aiosqlite:///:memory:"))

    message = str(exc.value)
    assert OBSERVER_ENV_VAR in message
    assert "missing or empty" in message


def test_admin_holds_every_capability():
    granted = capabilities_for("ADMIN")
    assert granted == ALL_CAPABILITIES
    for capability in Capability:
        ensure_capability("ADMIN", capability)


def test_observer_holds_only_read():
    granted = capabilities_for("OBSERVER")
    assert granted == frozenset({Capability.READ})
    for capability in Capability:
        if capability is Capability.READ:
            ensure_capability("OBSERVER", capability)
        else:
            with pytest.raises(ApiError) as exc:
                ensure_capability("OBSERVER", capability)
            assert exc.value.status_code == 403


def test_unknown_role_still_fails_closed():
    with pytest.raises(ApiError) as exc:
        capabilities_for("SUPERUSER")
    assert exc.value.status_code == 403
    assert "ADMIN" in exc.value.details["valid_roles"]
    assert "SUPER_ADMIN" not in exc.value.details["valid_roles"]


# ---------------------------------------------------------------------------
# Bootstrap and login against PostgreSQL
# ---------------------------------------------------------------------------


@requires_db
def test_bootstrap_stores_only_argon2_digests(accounts_database):
    rows = _run(
        _fetch(
            "SELECT display_id, role_code, status, password_hash, source, seed "
            "FROM users WHERE display_id = ANY($1::text[]) ORDER BY display_id",
            [ADMIN_USERNAME, TEST_USERNAME],
        )
    )
    assert [row["display_id"] for row in rows] == [ADMIN_USERNAME, TEST_USERNAME]
    assert rows[0]["role_code"] == "ADMIN"
    assert rows[1]["role_code"] == "OBSERVER"
    for row, expected_secret in ((rows[0], ADMIN_SECRET), (rows[1], TEST_SECRET)):
        digest = row["password_hash"]
        assert row["status"] == "ACTIVE"
        assert digest and digest.startswith("$argon2id$")
        assert digest != expected_secret
        assert expected_secret not in digest
        assert passwords.verify_password(expected_secret, digest)
        assert row["source"] == "bootstrap"
        assert row["seed"] is False


@requires_db
def test_bootstrap_is_idempotent_and_updates_hashes(accounts_database):
    before = _run(
        _fetch(
            "SELECT user_id, password_hash FROM users WHERE display_id = $1",
            ADMIN_USERNAME,
        )
    )
    _run(bootstrap_accounts(admin_secret=ADMIN_SECRET, test_secret=TEST_SECRET))
    after = _run(
        _fetch(
            "SELECT user_id, password_hash FROM users WHERE display_id = $1",
            ADMIN_USERNAME,
        )
    )
    assert len(after) == 1
    assert before[0]["user_id"] == after[0]["user_id"]
    assert before[0]["password_hash"] != after[0]["password_hash"]
    assert passwords.verify_password(ADMIN_SECRET, after[0]["password_hash"])
    count = _run(
        _fetch(
            "SELECT count(*) AS n FROM users WHERE display_id = ANY($1::text[])",
            [ADMIN_USERNAME, TEST_USERNAME],
        )
    )[0]["n"]
    assert count == 2


@requires_db
def test_admin_session_has_every_capability(accounts_database):
    response = _login(ADMIN_USERNAME, ADMIN_SECRET)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["role"] == "ADMIN"
    assert data["actor"] == ADMIN_USERNAME
    assert data["token"].startswith("nsk_")
    assert data["token_type"] == "Bearer"
    assert set(data["capabilities"]) == {item.value for item in ALL_CAPABILITIES}

    session_response = client.get(
        "/api/v1/auth/session",
        headers={"X-NoahsArk-Session": data["token"]},
    )
    assert session_response.status_code == 200
    body = session_response.json()["data"]
    assert body["role"] == "ADMIN"
    assert body["authenticated"] is True
    assert body["auth_method"] == "session"
    assert body["session_id"] == data["session_id"]


@requires_db
def test_test001_is_read_only(accounts_database):
    response = _login(TEST_USERNAME, TEST_SECRET)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["role"] == "OBSERVER"
    assert data["capabilities"] == ["READ"]
    token = data["token"]

    read = client.get(
        "/api/v1/tasks", headers={"X-NoahsArk-Session": token}
    )
    assert read.status_code == 200

    denied = client.post(
        "/api/v1/intake/drafts",
        headers={
            "X-NoahsArk-Session": token,
            "Idempotency-Key": f"b2-observer-{uuid.uuid4()}",
        },
        json={
            "title": "observer must not create",
            "entry_mode": "form",
            "scope_snapshot": {},
        },
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "FORBIDDEN"


@requires_db
def test_wrong_password_and_unknown_user_fail_closed(accounts_database):
    wrong = _login(ADMIN_USERNAME, secrets.token_urlsafe(24))
    unknown = _login("no-such-account", secrets.token_urlsafe(24))
    assert wrong.status_code == 401
    assert unknown.status_code == 401
    assert wrong.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert unknown.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"]
    assert "token" not in wrong.json()


@requires_db
def test_login_success_and_denial_are_audited(accounts_database):
    _login(ADMIN_USERNAME, ADMIN_SECRET)
    _login(ADMIN_USERNAME, secrets.token_urlsafe(24))
    rows = _run(
        _fetch(
            "SELECT access_decision, result, reason, object_id "
            "FROM audit_events WHERE action = 'AUTH_LOGIN' "
            "ORDER BY occurred_at DESC LIMIT 20"
        )
    )
    decisions = {(row["access_decision"], row["result"]) for row in rows}
    assert ("ALLOW", "SUCCESS") in decisions
    assert ("DENY", "DENIED") in decisions
    reasons = {row["reason"] for row in rows}
    assert "password_verified" in reasons
    assert "bad_credential" in reasons


@requires_db
def test_expired_session_is_rejected(accounts_database):
    issued = sessions.create_session_record(
        role="OBSERVER",
        actor=TEST_USERNAME,
        ttl_seconds=60,
        now=datetime.now(UTC) - timedelta(hours=2),
    )
    _run(
        _execute(
            "INSERT INTO sessions (session_id, token_hash, actor, role_code, "
            "issued_at, expires_at, created_at, source, seed) "
            "VALUES ($1, $2, $3, $4, $5, $6, $5, 'test', false)",
            issued.record.session_id,
            issued.record.token_hash,
            TEST_USERNAME,
            "OBSERVER",
            issued.record.issued_at,
            issued.record.expires_at,
        )
    )
    response = client.get(
        "/api/v1/auth/session",
        headers={"X-NoahsArk-Session": issued.token},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "SESSION_EXPIRED"


@requires_db
def test_logout_revokes_the_session(accounts_database):
    token = _login(TEST_USERNAME, TEST_SECRET).json()["data"]["token"]
    logout = client.post(
        "/api/v1/auth/logout", headers={"X-NoahsArk-Session": token}
    )
    assert logout.status_code == 200
    assert logout.json()["data"]["revoked"] is True

    reused = client.get(
        "/api/v1/auth/session", headers={"X-NoahsArk-Session": token}
    )
    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "SESSION_REVOKED"


@requires_db
def test_password_hash_never_appears_in_api_responses(accounts_database):
    token = _login(ADMIN_USERNAME, ADMIN_SECRET).json()["data"]["token"]
    headers = {"X-NoahsArk-Session": token}
    responses = [
        _login(ADMIN_USERNAME, ADMIN_SECRET),
        client.get("/api/v1/auth/session", headers=headers),
        client.get("/api/v1/settings/access", headers=headers),
        client.get("/api/v1/tasks", headers=headers),
        client.get("/openapi.json"),
    ]
    forbidden_markers = ("password_hash", "$argon2", ADMIN_SECRET, TEST_SECRET)
    for response in responses:
        assert response.status_code in {200, 201}, response.text
        for marker in forbidden_markers:
            assert marker not in response.text
