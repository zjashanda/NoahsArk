from datetime import UTC, datetime, timedelta

import pytest

from noahsark.errors import ApiError
from noahsark.services import sessions
from noahsark.services.auth import Credentials, DevHeaderProvider


@pytest.mark.asyncio
async def test_unknown_role_header_fails_closed():
    provider = DevHeaderProvider()
    with pytest.raises(ApiError) as exc:
        await provider.authenticate(Credentials(role_header="SUPERUSER"))
    assert exc.value.status_code == 403
    assert exc.value.code == "FORBIDDEN"


@pytest.mark.asyncio
async def test_missing_role_defaults_to_observer_without_authentication():
    principal = await DevHeaderProvider().authenticate(Credentials())
    assert principal.role == "OBSERVER"
    assert principal.authenticated is False


def test_session_token_is_hashed_not_stored_plaintext():
    issued = sessions.create_session_record(role="APPROVER", actor="approver-02")
    assert issued.token.startswith("nsk_")
    assert issued.token not in issued.record.token_hash
    assert issued.record.token_hash == sessions.hash_token(issued.token)
    assert issued.record.role_code == "APPROVER"


def test_expired_and_revoked_sessions_are_inactive():
    issued = sessions.create_session_record(role="APPROVER")
    record = issued.record

    record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    active, code = sessions.session_is_active(record)
    assert active is False
    assert code == "SESSION_EXPIRED"

    record.expires_at = datetime.now(UTC) + timedelta(hours=1)
    record.revoked_at = datetime.now(UTC)
    active, code = sessions.session_is_active(record)
    assert active is False
    assert code == "SESSION_REVOKED"
