"""Server-side sessions.

A session token is shown to the caller exactly once.  Only its SHA-256 hash is
persisted, so a database read can never reconstruct a usable bearer token.
Expired or revoked sessions fail closed with ``401``.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.permissions import capabilities_for, normalize_role
from ..errors import unauthorized
from ..models import SessionToken

TOKEN_PREFIX = "nsk_"
TOKEN_BYTES = 32
MIN_TTL_SECONDS = 60
MAX_TTL_SECONDS = 86400


@dataclass(frozen=True)
class IssuedSession:
    token: str
    record: SessionToken


def hash_token(token: str) -> str:
    """Hash a bearer token for storage.  The plaintext is never persisted."""

    return "sha256:" + hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(TOKEN_BYTES)


def create_session_record(
    *,
    role: str,
    actor: str | None = None,
    actor_id: uuid.UUID | None = None,
    ttl_seconds: int | None = None,
    now: datetime | None = None,
) -> IssuedSession:
    """Build an unsaved session with a fresh token and hashed storage value.

    The role is validated through the capability map, so an unknown role can
    never obtain a session.
    """

    normalized = normalize_role(role)
    capabilities_for(normalized)  # fail closed for unknown roles
    issued_at = now or datetime.now(UTC)
    ttl = _clamp_ttl(ttl_seconds)
    token = new_token()
    record = SessionToken(
        session_id=uuid.uuid4(),
        token_hash=hash_token(token),
        actor=actor,
        actor_id=actor_id,
        role_code=normalized,
        issued_at=issued_at,
        expires_at=issued_at + timedelta(seconds=ttl),
        revoked_at=None,
        revoked_reason=None,
        created_at=issued_at,
        source="control-plane",
        seed=False,
    )
    return IssuedSession(token=token, record=record)


def _clamp_ttl(ttl_seconds: int | None) -> int:
    if ttl_seconds is None:
        return 3600
    return max(MIN_TTL_SECONDS, min(MAX_TTL_SECONDS, int(ttl_seconds)))


def session_is_active(
    record: SessionToken, *, now: datetime | None = None
) -> tuple[bool, str | None]:
    """Return ``(active, rejection_code)``; rejection codes are fail-closed."""

    moment = now or datetime.now(UTC)
    if record.revoked_at is not None:
        return False, "SESSION_REVOKED"
    if record.expires_at <= moment:
        return False, "SESSION_EXPIRED"
    return True, None


def ensure_session_active(
    record: SessionToken, *, now: datetime | None = None
) -> SessionToken:
    active, code = session_is_active(record, now=now)
    if not active:
        raise unauthorized(
            f"Session is not active ({code})",
            code=code or "INVALID_SESSION",
            details={"session_id": str(record.session_id)},
        )
    return record


async def issue_session(
    session: AsyncSession,
    *,
    role: str,
    actor: str | None = None,
    actor_id: uuid.UUID | None = None,
    ttl_seconds: int | None = None,
) -> IssuedSession:
    issued = create_session_record(
        role=role,
        actor=actor,
        actor_id=actor_id,
        ttl_seconds=ttl_seconds,
    )
    session.add(issued.record)
    await session.flush()
    return issued


async def resolve_session(
    session: AsyncSession,
    token: str,
    *,
    now: datetime | None = None,
) -> SessionToken:
    """Look up a token by hash; missing/expired/revoked sessions fail closed."""

    if not token or not token.strip():
        raise unauthorized(
            "A session token is required",
            code="SESSION_REQUIRED",
        )
    record = (
        await session.execute(
            select(SessionToken).where(
                SessionToken.token_hash == hash_token(token.strip())
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise unauthorized(
            "Session token is not recognized",
            code="INVALID_SESSION",
        )
    return ensure_session_active(record, now=now)


async def revoke_session(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    reason: str | None = None,
    now: datetime | None = None,
) -> SessionToken:
    record = await session.get(SessionToken, session_id)
    if record is None:
        raise unauthorized(
            "Session is not recognized",
            code="INVALID_SESSION",
            details={"session_id": str(session_id)},
        )
    if record.revoked_at is None:
        record.revoked_at = now or datetime.now(UTC)
        record.revoked_reason = reason or "revoked"
    await session.flush()
    return record
