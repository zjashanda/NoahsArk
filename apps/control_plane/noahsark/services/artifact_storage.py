"""Content-addressed storage for downloadable test-campaign evidence.

The node uploads one zip per campaign/command.  Bytes are addressed by SHA-256
under ``<artifact_root>/<campaign_id>/<sha256><suffix>``; the client-supplied
name is only a display label and is sanitized to a single path segment.  A
download resolves the database row first, then a generated relative storage key,
so ``../`` in a URL or an upload name can never escape the root.

The digest is always recomputed from the bytes that arrived; the declared
digest (when supplied) is only compared against that recomputation.  Downloads
re-verify size and digest before any byte is streamed.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import tempfile
import uuid
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from ..config import settings
from ..errors import ApiError, not_found

DIGEST_PREFIX = "sha256:"
HEX_LENGTH = 64
NAME_MAX = 200
READ_CHUNK = 1024 * 1024
DEFAULT_NAME = "evidence.zip"
DEFAULT_MEDIA_TYPE = "application/zip"
_NAME_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+", re.ASCII)
_SAFE_SUFFIX = re.compile(r"^\.[A-Za-z0-9]{1,8}$", re.ASCII)


def artifact_too_large(size: int, limit: int) -> ApiError:
    return ApiError(
        413,
        "ARTIFACT_TOO_LARGE",
        "Uploaded campaign artifact exceeds the configured size limit",
        retryable=False,
        details={"size_bytes": size, "max_bytes": limit},
    )


def artifact_empty() -> ApiError:
    return ApiError(
        400,
        "ARTIFACT_EMPTY",
        "Campaign artifact upload contained no bytes",
        retryable=False,
    )


def artifact_immutable(name: str, existing: str, received: str) -> ApiError:
    return ApiError(
        409,
        "ARTIFACT_IMMUTABLE",
        "An artifact with this name already exists with different bytes",
        retryable=False,
        details={"name": name, "existing_digest": existing, "received_digest": received},
    )


def artifact_integrity_failure(name: str, reason: str) -> ApiError:
    return ApiError(
        409,
        "ARTIFACT_INTEGRITY_FAILURE",
        "Stored artifact bytes failed integrity verification",
        retryable=False,
        details={"name": name, "integrity_reason": reason},
    )


def safe_artifact_name(raw: str | None, *, fallback: str = DEFAULT_NAME) -> str:
    """Return a single-segment display name, never a path.

    Both POSIX and Windows separators are treated as path separators because the
    uploader is a Windows node that may send ``D:\\...\\evidence.zip``.
    """

    candidate = (raw or "").strip().replace("\x00", "")
    candidate = re.split(r"[\\/]", candidate)[-1]
    candidate = _NAME_UNSAFE.sub("_", candidate).strip(" .")
    if not candidate or candidate in {".", ".."}:
        candidate = fallback
    if len(candidate) > NAME_MAX:
        suffix = Path(candidate).suffix
        keep = NAME_MAX - len(suffix) if _SAFE_SUFFIX.fullmatch(suffix) else NAME_MAX
        candidate = candidate[:keep].rstrip(" .") or fallback
        if _SAFE_SUFFIX.fullmatch(suffix):
            candidate += suffix
    return candidate


def normalize_digest(value: str | None) -> str | None:
    """Return canonical ``sha256:<hex>`` or ``None`` when not supplied."""

    if value is None or not value.strip():
        return None
    raw = value.strip().lower().removeprefix(DIGEST_PREFIX)
    if len(raw) != HEX_LENGTH or any(c not in "0123456789abcdef" for c in raw):
        raise ApiError(
            400,
            "ARTIFACT_DIGEST_INVALID",
            "Artifact digest must be sha256:<64 hex characters>",
            retryable=False,
            details={"digest": value},
        )
    return DIGEST_PREFIX + raw


def digest_bytes(data: bytes) -> str:
    return DIGEST_PREFIX + hashlib.sha256(data).hexdigest()


def _suffix_for(name: str) -> str:
    suffix = Path(name).suffix
    return suffix if _SAFE_SUFFIX.fullmatch(suffix) else ".bin"


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    name: str
    digest: str
    size_bytes: int
    storage_key: str
    media_type: str
    created: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "digest": self.digest,
            "size_bytes": self.size_bytes,
            "media_type": self.media_type,
            "duplicate": not self.created,
        }


class ArtifactStorage:
    """Local artifact root; all public keys are relative and generated."""

    def __init__(self, root: str | Path | None = None, *, max_bytes: int | None = None) -> None:
        self._root = Path(root if root is not None else settings.artifact_storage_root).expanduser()
        self._max_bytes = (
            max_bytes if max_bytes is not None else settings.artifact_max_bytes
        )

    @property
    def root(self) -> Path:
        return self._root

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    def storage_key_for(self, campaign_id: uuid.UUID, digest: str, name: str) -> str:
        hex_digest = digest.removeprefix(DIGEST_PREFIX)
        return f"{campaign_id}/{hex_digest}{_suffix_for(name)}"

    def path_for_key(self, storage_key: str) -> Path:
        root = self._root.resolve()
        candidate = (root / storage_key).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ApiError(
                400,
                "ARTIFACT_PATH_INVALID",
                "Artifact storage key escapes the configured root",
                retryable=False,
            ) from exc
        return candidate

    def write(
        self,
        chunks: Iterable[bytes],
        *,
        campaign_id: uuid.UUID,
        name: str,
        expected_digest: str | None = None,
    ) -> StoredArtifact:
        """Stream bytes to a temp file, verify the digest, then publish atomically."""

        safe_name = safe_artifact_name(name)
        media_type = (
            DEFAULT_MEDIA_TYPE
            if _suffix_for(safe_name) == ".zip"
            else "application/octet-stream"
        )
        hex_digest, size, temp_path = self._write_temp(chunks)
        published = False
        try:
            digest = DIGEST_PREFIX + hex_digest
            declared = normalize_digest(expected_digest)
            if declared is not None and not hmac.compare_digest(declared, digest):
                raise ApiError(
                    400,
                    "ARTIFACT_DIGEST_MISMATCH",
                    "Declared artifact digest does not match the uploaded bytes",
                    retryable=False,
                    details={"expected_digest": declared, "actual_digest": digest},
                )
            if size == 0:
                raise artifact_empty()
            key = self.storage_key_for(campaign_id, digest, safe_name)
            target = self.path_for_key(key)
            target.parent.mkdir(parents=True, exist_ok=True)
            created = not target.exists()
            if created:
                os.replace(temp_path, target)
                published = True
            return StoredArtifact(
                name=safe_name,
                digest=digest,
                size_bytes=size,
                storage_key=key,
                media_type=media_type,
                created=created,
            )
        finally:
            if not published and os.path.exists(temp_path):
                os.unlink(temp_path)

    def _write_temp(self, chunks: Iterable[bytes]) -> tuple[str, int, str]:
        self._root.mkdir(parents=True, exist_ok=True)
        hasher = hashlib.sha256()
        size = 0
        descriptor, temp_path = tempfile.mkstemp(prefix=".upload-", dir=str(self._root))
        try:
            with os.fdopen(descriptor, "wb") as handle:
                for chunk in chunks:
                    if not chunk:
                        continue
                    size += len(chunk)
                    if self._max_bytes and size > self._max_bytes:
                        raise artifact_too_large(size, self._max_bytes)
                    hasher.update(chunk)
                    handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
        return hasher.hexdigest(), size, temp_path

    def verify(self, storage_key: str, *, digest: str, size_bytes: int) -> Path:
        path = self.path_for_key(storage_key)
        if not path.is_file():
            raise not_found("test_campaign_artifact_blob", storage_key)
        hasher = hashlib.sha256()
        actual_size = 0
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(READ_CHUNK), b""):
                hasher.update(chunk)
                actual_size += len(chunk)
        actual = DIGEST_PREFIX + hasher.hexdigest()
        if actual_size != size_bytes:
            raise artifact_integrity_failure(storage_key, "size_mismatch")
        if not hmac.compare_digest(actual, digest):
            raise artifact_integrity_failure(storage_key, "digest_mismatch")
        return path

    def delete(self, storage_key: str) -> bool:
        path = self.path_for_key(storage_key)
        try:
            path.unlink()
        except FileNotFoundError:
            return False
        return True



def default_storage() -> ArtifactStorage:
    return ArtifactStorage()


def iter_file(path: Path) -> Iterator[bytes]:
    with path.open("rb") as handle:
        yield from iter(lambda: handle.read(READ_CHUNK), b"")
