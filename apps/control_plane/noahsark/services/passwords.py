"""Password hashing and bootstrap secret policy.

Passwords are stored only as Argon2id digests produced by ``pwdlib`` (the
standard FastAPI/OWASP recommendation).  Plain SHA-256 is intentionally not
used: it is fast, unsalted by default and unsuitable for credential storage.

The bootstrap policy refuses empty or well-known default values so an operator
cannot accidentally create an account with a placeholder credential.  Error
messages never echo the supplied value.
"""

from __future__ import annotations

import secrets

from pwdlib import PasswordHash

# pwdlib's recommended configuration is Argon2id with current OWASP-aligned
# parameters (m=64 MiB, t=3, p=4 at the time of writing).
_hasher = PasswordHash.recommended()

MIN_SECRET_LENGTH = 8
MAX_SECRET_LENGTH = 256

# Rejected case-insensitively.  These are common placeholders, not accounts.
DEFAULT_SECRETS: frozenset[str] = frozenset(
    {
        "password",
        "password1",
        "password123",
        "passw0rd",
        "changeme",
        "change_me",
        "change-me",
        "admin",
        "administrator",
        "root",
        "test",
        "test001",
        "guest",
        "default",
        "secret",
        "qwerty",
        "letmein",
        "12345678",
        "123456789",
        "noahsark",
    }
)

_dummy_digest: str | None = None


class WeakSecretError(ValueError):
    """Raised when a bootstrap secret violates the local policy."""


def hash_password(secret_value: str) -> str:
    """Return an Argon2id digest; the plaintext is not retained."""

    return _hasher.hash(secret_value)


def verify_password(secret_value: str, digest: str | None) -> bool:
    """Verify a candidate against a stored digest.  Any failure is a denial."""

    if not digest:
        return False
    try:
        return bool(_hasher.verify(secret_value, digest))
    except Exception:  # noqa: BLE001 - malformed/unsupported hashes fail closed
        return False


def _dummy() -> str:
    """A real Argon2 digest used to equalize unknown-user timing."""

    global _dummy_digest
    digest = _dummy_digest
    if digest is None:
        digest = _hasher.hash(secrets.token_urlsafe(32))
        _dummy_digest = digest
    return digest


def verify_dummy(secret_value: str) -> None:
    """Burn comparable time when the account does not exist."""

    verify_password(secret_value, _dummy())


def is_argon2_hash(value: str | None) -> bool:
    return value is not None and value.startswith("$argon2")


def validate_bootstrap_secret(secret_value: str | None, *, username: str) -> str:
    """Return the accepted secret or raise ``WeakSecretError``.

    The value itself is never included in the exception text.
    """

    if secret_value is None or not secret_value:
        raise WeakSecretError("bootstrap secret is missing or empty")
    if secret_value != secret_value.strip():
        raise WeakSecretError("bootstrap secret must not start or end with whitespace")
    if len(secret_value) < MIN_SECRET_LENGTH:
        raise WeakSecretError(
            f"bootstrap secret must be at least {MIN_SECRET_LENGTH} characters"
        )
    if len(secret_value) > MAX_SECRET_LENGTH:
        raise WeakSecretError(
            f"bootstrap secret must be at most {MAX_SECRET_LENGTH} characters"
        )
    lowered = secret_value.casefold()
    if lowered in DEFAULT_SECRETS:
        raise WeakSecretError("bootstrap secret is a known default value")
    if lowered == username.casefold():
        raise WeakSecretError("bootstrap secret must differ from the username")
    return secret_value
