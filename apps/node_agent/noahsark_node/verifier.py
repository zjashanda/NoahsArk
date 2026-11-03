"""Artifact digest and signature verification.

Only verified artifacts may be executed. The signature verifier is a hook:
production must supply a real Ed25519 verifier (PENDING under G-NODE); tests use
an HMAC verifier so the refusal path is executable without external keys.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass
from typing import Protocol

from .protocol import ArtifactRef


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_prefixed(content: bytes) -> str:
    return f"sha256:{sha256_hex(content)}"


@dataclass(frozen=True, slots=True)
class ArtifactVerification:
    ok: bool
    digest: str
    reason: str


class SignatureVerifier(Protocol):
    def verify(self, key_id: str, payload: bytes, signature: str) -> bool: ...


class ArtifactRejected(RuntimeError):
    """Raised when an unverified artifact must not be executed."""


class RejectingSignatureVerifier:
    """Default hook: no key material configured, therefore every signature fails."""

    def verify(self, key_id: str, payload: bytes, signature: str) -> bool:
        return False


class HmacSignatureVerifier:
    """Development-only HMAC hook; not the production Ed25519 contract."""

    def __init__(self, secret: bytes) -> None:
        if not secret:
            raise ValueError("HMAC secret must not be empty")
        self._secret = secret

    def sign(self, key_id: str, payload: bytes) -> str:
        message = key_id.encode("utf-8") + b"\x00" + payload
        digest = hmac.new(self._secret, message, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    def verify(self, key_id: str, payload: bytes, signature: str) -> bool:
        expected = self.sign(key_id, payload)
        return hmac.compare_digest(expected, signature)


class ArtifactVerifier:
    def __init__(self, signature_verifier: SignatureVerifier | None = None) -> None:
        self._signature_verifier = signature_verifier

    def verify(self, artifact: ArtifactRef, content: bytes) -> ArtifactVerification:
        digest = sha256_hex(content)
        if artifact.size_bytes > 0 and len(content) != artifact.size_bytes:
            return ArtifactVerification(False, digest, "size_mismatch")
        if not hmac.compare_digest(digest, artifact.sha256.lower()):
            return ArtifactVerification(False, digest, "digest_mismatch")
        if artifact.signature is None or artifact.key_id is None:
            return ArtifactVerification(False, digest, "signature_missing")
        if self._signature_verifier is None:
            return ArtifactVerification(False, digest, "signature_verifier_missing")
        if not self._signature_verifier.verify(
            artifact.key_id, content, artifact.signature
        ):
            return ArtifactVerification(False, digest, "signature_invalid")
        return ArtifactVerification(True, digest, "verified")

    def require(self, artifact: ArtifactRef, content: bytes) -> str:
        result = self.verify(artifact, content)
        if not result.ok:
            raise ArtifactRejected(f"{artifact.artifact_id}: {result.reason}")
        return result.digest
