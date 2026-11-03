"""W3 local content-addressed evidence storage, manifest and retention rules.

Evidence bytes are addressed by ``sha256:<hex>``.  The store never trusts a
declared digest: every write, read and verification recomputes the digest from
the bytes on disk.  Missing or corrupt blobs fail closed instead of returning
partial content.

Two invariants are deliberately kept separate:

* ``received`` means bytes were accepted at some point;
* ``verified`` means the stored bytes were re-hashed and matched the declared
  digest.

A received-but-unverified item is ``UNVERIFIED``, never ``COMPLETE``.  Raw
bytes are only readable by a role holding ``EVIDENCE_RAW``; metadata stays on
the existing ``SUMMARY_INDEX`` read routes.

The public JSON shapes in this module only ever expose a *relative* storage
key (``sha256/ab/cd/....blob``).  Absolute paths and storage credentials are
never returned to API callers.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..domain.permissions import Capability, ensure_capability, has_capability
from ..errors import ApiError, forbidden, not_found
from ..models import EvidenceItem, EvidenceManifest, Run
from . import audit

DIGEST_ALGORITHM = "sha256"
DIGEST_PREFIX = f"{DIGEST_ALGORITHM}:"
HEX_LENGTH = 64
STORAGE_LAYOUT = "sha256"
BLOB_SUFFIX = ".blob"
READ_CHUNK = 1024 * 1024

EVIDENCE_STATES: tuple[str, ...] = (
    "declared",
    "uploading",
    "partial",
    "complete",
    "verified",
    "conflicted",
    "unavailable",
    "quarantined",
)
RECEIVED_STATES = frozenset({"complete", "verified"})
RETENTION_CONFIRM_PHRASE = "PURGE_EVIDENCE"
RETENTION_ELIGIBLE_STATES = frozenset({"complete", "verified"})
RETENTION_HOLD_CLASSES = frozenset({"hold", "legal_hold", "permanent"})


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
def digest_mismatch(expected: str, actual: str) -> ApiError:
    return ApiError(
        400,
        "EVIDENCE_DIGEST_MISMATCH",
        "Declared evidence digest does not match the uploaded bytes",
        retryable=False,
        details={"expected_digest": expected, "actual_digest": actual},
    )


def integrity_failure(digest: str, reason: str) -> ApiError:
    return ApiError(
        409,
        "EVIDENCE_INTEGRITY_FAILURE",
        "Stored evidence bytes failed digest verification",
        retryable=False,
        details={"digest": digest, "integrity_reason": reason},
    )


def evidence_immutable(digest: str, existing: str) -> ApiError:
    return ApiError(
        409,
        "EVIDENCE_IMMUTABLE",
        "Evidence already has different bytes; evidence is never overwritten",
        retryable=False,
        details={"digest": digest, "existing_digest": existing},
    )


def evidence_not_received(identifier: str) -> ApiError:
    return ApiError(
        409,
        "EVIDENCE_NOT_RECEIVED",
        "Evidence has no received blob to verify or read",
        retryable=False,
        details={"evidence_id": identifier},
    )


def evidence_too_large(size: int, limit: int) -> ApiError:
    return ApiError(
        413,
        "EVIDENCE_TOO_LARGE",
        "Uploaded evidence exceeds the configured size limit",
        retryable=False,
        details={"size_bytes": size, "max_bytes": limit},
    )


def storage_unavailable(reason: str) -> ApiError:
    return ApiError(
        503,
        "EVIDENCE_STORAGE_UNAVAILABLE",
        "Evidence storage is not available",
        retryable=True,
        details={"reason": reason},
    )


# ---------------------------------------------------------------------------
# Digest helpers
# ---------------------------------------------------------------------------
def digest_bytes(data: bytes) -> str:
    return DIGEST_PREFIX + hashlib.sha256(data).hexdigest()


def normalize_digest(value: str | None) -> str:
    """Return a canonical ``sha256:<hex>`` digest or raise a 400 error."""

    raw = (value or "").strip().lower()
    raw = raw.removeprefix(DIGEST_PREFIX)
    if len(raw) != HEX_LENGTH or any(char not in "0123456789abcdef" for char in raw):
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            "Evidence digest must be sha256:<64 hex characters>",
            retryable=False,
            details={"digest": value},
        )
    return DIGEST_PREFIX + raw


def digest_hex(digest: str) -> str:
    return normalize_digest(digest)[len(DIGEST_PREFIX) :]


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class StoredBlob:
    """Public, path-free description of a stored blob."""

    digest: str
    size_bytes: int
    storage_key: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "digest": self.digest,
            "size_bytes": self.size_bytes,
            "storage_key": self.storage_key,
            "locator": {"kind": "content_addressed", "uri": self.storage_key},
            "address_kind": "content_addressed",
            "absolute_path_exposed": False,
        }


@dataclass(frozen=True)
class IntegrityResult:
    ok: bool
    digest: str
    size_bytes: int | None
    storage_key: str
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "digest": self.digest,
            "size_bytes": self.size_bytes,
            "storage_key": self.storage_key,
            "integrity_status": "OK" if self.ok else "DIGEST_MISMATCH",
            "reason": self.reason,
        }


class ContentAddressedStorage:
    """Local SHA-256 addressed blob store.

    Layout: ``<root>/sha256/<ab>/<cd>/<sha256hex>.blob``.  Writes are atomic
    (temp file in the destination directory + ``os.replace``) and never
    overwrite a blob that already exists under the same digest.
    """

    def __init__(self, root: str | Path | None = None, *, max_bytes: int | None = None) -> None:
        configured = root if root is not None else settings.evidence_storage_root
        self._root = Path(configured).expanduser()
        self._max_bytes = (
            max_bytes if max_bytes is not None else settings.evidence_max_blob_bytes
        )

    # -- paths ---------------------------------------------------------
    @property
    def root(self) -> Path:
        """Internal root path.  Never serialize this value into an API body."""

        return self._root

    @staticmethod
    def storage_key_for(digest: str) -> str:
        hex_digest = digest_hex(digest)
        return f"{STORAGE_LAYOUT}/{hex_digest[:2]}/{hex_digest[2:4]}/{hex_digest}{BLOB_SUFFIX}"

    def path_for(self, digest: str) -> Path:
        return self._root / self.storage_key_for(digest)

    def has_blob(self, digest: str) -> bool:
        return self.path_for(digest).is_file()

    # -- write ---------------------------------------------------------
    def put_blob(
        self, data: bytes, *, expected_digest: str | None = None
    ) -> StoredBlob:
        if not isinstance(data, (bytes, bytearray)):
            raise ApiError(
                400,
                "VALIDATION_ERROR",
                "Evidence payload must be raw bytes",
                retryable=False,
            )
        payload = bytes(data)
        if self._max_bytes and len(payload) > self._max_bytes:
            raise evidence_too_large(len(payload), self._max_bytes)
        computed = digest_bytes(payload)
        if expected_digest is not None:
            declared = normalize_digest(expected_digest)
            if declared != computed:
                raise digest_mismatch(declared, computed)

        target = self.path_for(computed)
        if target.exists():
            existing = self.verify_digest(computed)
            if not existing.ok:
                # Never overwrite a corrupt immutable blob; quarantine is a
                # separate, explicit operation.
                raise integrity_failure(computed, existing.reason or "corrupt")
            return StoredBlob(
                digest=computed,
                size_bytes=target.stat().st_size,
                storage_key=self.storage_key_for(computed),
            )

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temp_name = tempfile.mkstemp(
                prefix=".upload-", dir=str(target.parent)
            )
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, target)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
        except OSError as exc:  # pragma: no cover - environment dependent
            raise storage_unavailable(exc.__class__.__name__) from exc

        return StoredBlob(
            digest=computed,
            size_bytes=len(payload),
            storage_key=self.storage_key_for(computed),
        )

    # -- read / verify -------------------------------------------------
    def verify_digest(self, digest: str) -> IntegrityResult:
        normalized = normalize_digest(digest)
        path = self.path_for(normalized)
        key = self.storage_key_for(normalized)
        if not path.is_file():
            return IntegrityResult(
                ok=False,
                digest=normalized,
                size_bytes=None,
                storage_key=key,
                reason="missing",
            )
        hasher = hashlib.sha256()
        size = 0
        try:
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(READ_CHUNK), b""):
                    hasher.update(chunk)
                    size += len(chunk)
        except OSError as exc:  # pragma: no cover - environment dependent
            raise storage_unavailable(exc.__class__.__name__) from exc
        actual = DIGEST_PREFIX + hasher.hexdigest()
        if actual != normalized:
            return IntegrityResult(
                ok=False,
                digest=normalized,
                size_bytes=size,
                storage_key=key,
                reason="digest_mismatch",
            )
        return IntegrityResult(
            ok=True, digest=normalized, size_bytes=size, storage_key=key
        )

    def read_blob(self, digest: str) -> bytes:
        normalized = normalize_digest(digest)
        path = self.path_for(normalized)
        if not path.is_file():
            raise not_found("evidence_blob", normalized)
        try:
            data = path.read_bytes()
        except OSError as exc:  # pragma: no cover - environment dependent
            raise storage_unavailable(exc.__class__.__name__) from exc
        actual = digest_bytes(data)
        if actual != normalized:
            raise integrity_failure(normalized, "digest_mismatch")
        return data

    # -- destructive primitive ----------------------------------------
    def delete_blob(self, digest: str) -> bool:
        """Remove one blob.  Only the audited admin retention flow calls this."""

        path = self.path_for(normalize_digest(digest))
        try:
            path.unlink()
        except FileNotFoundError:
            return False
        except OSError as exc:  # pragma: no cover - environment dependent
            raise storage_unavailable(exc.__class__.__name__) from exc
        return True


def default_storage() -> ContentAddressedStorage:
    return ContentAddressedStorage()


# ---------------------------------------------------------------------------
# Manifest counting / item state machine
# ---------------------------------------------------------------------------
def _as_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return None


def _state_of(item: Any) -> str:
    state = str(getattr(item, "state", "") or "declared")
    return state if state in EVIDENCE_STATES else "unavailable"


def manifest_counts(items: Iterable[Any]) -> dict[str, Any]:
    """Count expected/received/verified independently and describe states."""

    rows = list(items)
    total = len(rows)
    expected_rows = [
        item for item in rows if bool(getattr(item, "expected", True))
    ]
    expected = len(expected_rows)
    received = sum(1 for item in rows if bool(getattr(item, "received", False)))
    verified = sum(1 for item in rows if bool(getattr(item, "verified", False)))
    expected_received = sum(
        1 for item in expected_rows if bool(getattr(item, "received", False))
    )
    expected_verified = sum(
        1 for item in expected_rows if bool(getattr(item, "verified", False))
    )
    states = {state: 0 for state in EVIDENCE_STATES}
    for item in rows:
        states[_state_of(item)] += 1
    conflicted = states["conflicted"]
    missing = max(expected - expected_received, 0)
    pending_verification = max(received - verified, 0)
    complete = (
        expected > 0
        and expected_received >= expected
        and expected_verified >= expected
        and conflicted == 0
    )

    if conflicted:
        status = "CONFLICTED"
    elif expected > expected_received:
        status = "INCOMPLETE"
    elif expected_received > expected_verified:
        status = "UNVERIFIED"
    elif expected > 0:
        status = "COMPLETE"
    else:
        status = "UNVERIFIED"

    return {
        "total": total,
        "expected": expected,
        "received": received,
        "verified": verified,
        "conflicted": conflicted,
        "missing": missing,
        "pending_verification": pending_verification,
        "received_not_verified": pending_verification,
        "complete": complete,
        "evidence_status": status,
        "status": status,
        "states": states,
        "counts_are_independent": True,
        "received_equals_verified": received == verified,
    }


def apply_upload(
    item: Any,
    blob: StoredBlob,
    *,
    media_type: str | None = None,
    expected_size: int | None = None,
    chunks_total: int = 1,
    chunks_received: int | None = None,
) -> dict[str, Any]:
    """Attach stored bytes to an item without claiming verification."""

    existing = getattr(item, "content_digest", None)
    if existing:
        normalized_existing = normalize_digest(existing)
        if normalized_existing != blob.digest:
            raise evidence_immutable(blob.digest, normalized_existing)
    if expected_size is not None and expected_size != blob.size_bytes:
        raise ApiError(
            400,
            "EVIDENCE_SIZE_MISMATCH",
            "Declared evidence size does not match the uploaded bytes",
            retryable=False,
            details={
                "expected_size_bytes": expected_size,
                "actual_size_bytes": blob.size_bytes,
            },
        )

    total_chunks = max(int(chunks_total or 1), 1)
    received_chunks = (
        total_chunks
        if chunks_received is None
        else min(max(int(chunks_received), 0), total_chunks)
    )

    already_verified = bool(getattr(item, "verified", False)) and _state_of(item) == "verified"
    if already_verified:
        # Re-receiving identical bytes is idempotent and must not downgrade a
        # previously verified item back to ``UNVERIFIED``.
        item.received = True
        return {
            **blob.as_dict(),
            "received": True,
            "verified": True,
            "state": _state_of(item),
            "received_is_not_verified": False,
            "media_type": getattr(item, "media_type", None),
        }

    item.state = "complete"
    item.received = True
    item.verified = False

    item.content_digest = blob.digest
    item.size_bytes = blob.size_bytes
    if media_type:
        item.media_type = media_type
    item.digest_scope = "raw_bytes"
    item.upload = {
        "chunks_total": total_chunks,
        "chunks_received": received_chunks,
        "complete": received_chunks == total_chunks,
    }
    item.locator = {
        "kind": "content_addressed",
        "uri": blob.storage_key,
        "storage_key": blob.storage_key,
    }
    item.integrity = {
        "algorithm": DIGEST_ALGORITHM,
        "digest_verified": False,
        "integrity_status": "UNVERIFIED",
        "size_bytes": blob.size_bytes,
        "storage_key": blob.storage_key,
    }
    return {
        **blob.as_dict(),
        "received": True,
        "verified": False,
        "state": _state_of(item),
        "received_is_not_verified": True,
        "media_type": getattr(item, "media_type", None),
    }


def apply_verification(
    item: Any,
    result: IntegrityResult,
    *,
    verified_at: datetime | None = None,
) -> dict[str, Any]:
    """Recompute-based verification result; a mismatch never marks verified."""

    digest = getattr(item, "content_digest", None)
    if not digest or not bool(getattr(item, "received", False)):
        raise evidence_not_received(str(getattr(item, "display_id", "")))
    expected = normalize_digest(digest)
    ok = result.ok and result.digest == expected
    when = verified_at or datetime.now(UTC)
    if ok:
        item.verified = True
        item.state = "verified"
        integrity_status = "OK"
    else:
        item.verified = False
        item.state = "conflicted"
        integrity_status = "DIGEST_MISMATCH"
    item.integrity = {
        "algorithm": DIGEST_ALGORITHM,
        "digest_verified": ok,
        "integrity_status": integrity_status,
        "size_bytes": result.size_bytes,
        "storage_key": result.storage_key,
        "reason": result.reason if not ok else None,
        "verified_at": when.isoformat().replace("+00:00", "Z"),
    }
    return {
        **result.as_dict(),
        "ok": ok,
        "verified": ok,
        "received": True,
        "state": _state_of(item),
        "received_is_not_verified": not ok,
    }


def begin_upload(item: Any, *, chunks_total: int = 1) -> dict[str, Any]:
    """Move a declared item into the uploading state before bytes arrive."""

    if bool(getattr(item, "verified", False)):
        raise evidence_immutable(str(getattr(item, "content_digest", "")), str(getattr(item, "content_digest", "")))
    total = max(int(chunks_total or 1), 1)
    item.state = "uploading"
    item.upload = {
        "chunks_total": total,
        "chunks_received": 0,
        "complete": False,
    }
    return {"state": "uploading", "chunks_total": total, "received": bool(getattr(item, "received", False))}


def record_partial(item: Any, *, chunks_received: int, chunks_total: int) -> dict[str, Any]:
    total = max(int(chunks_total or 1), 1)
    received = min(max(int(chunks_received), 0), total)
    has_digest = bool(getattr(item, "content_digest", None))
    item.state = "complete" if received == total and has_digest else "partial"
    item.upload = {
        "chunks_total": total,
        "chunks_received": received,
        "complete": received == total,
    }
    return {**item.upload, "state": _state_of(item)}


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------
def role_may_read_raw_evidence(role: str | None) -> bool:
    return has_capability(role, Capability.EVIDENCE_RAW)


def ensure_raw_evidence_access(role: str | None) -> None:
    ensure_capability(role, Capability.EVIDENCE_RAW)


async def audit_raw_evidence_access(
    session: AsyncSession,
    *,
    actor_role: str,
    actor_id: uuid.UUID | None,
    evidence_id: str,
    allowed: bool,
    reason: str,
    correlation_id: str | None,
    path: str,
) -> None:
    """Append an ALLOW or DENY event for raw evidence access.

    Callers must commit before returning content or raising the 403 so a denied
    attempt remains auditable.
    """

    event = await audit.append_event(
        session,
        actor_role=actor_role,
        actor_id=actor_id,
        action="EVIDENCE_RAW_ACCESS",
        object_type="evidence",
        object_id=evidence_id,
        before=None,
        after={
            "access_decision": "ALLOW" if allowed else "DENY",
            "required_capability": Capability.EVIDENCE_RAW.value,
            "raw_content_read": allowed,
        },
        reason=reason,
        correlation_id=correlation_id,
        path=path,
    )
    # Access decision is outside the audit hash-chain fields but is part of the
    # persisted chain payload (``after``), so a DENY remains provable.
    event.access_decision = "ALLOW" if allowed else "DENY"
    event.result = "SUCCESS" if allowed else "DENIED"


# ---------------------------------------------------------------------------
# DB orchestration
# ---------------------------------------------------------------------------
async def resolve_evidence_item(session: AsyncSession, identifier: str) -> EvidenceItem:
    """Resolve an evidence item by display id or canonical UUID."""

    raw = (identifier or "").strip()
    if not raw:
        raise not_found("evidence", identifier)
    conditions = [EvidenceItem.display_id == raw]
    try:
        conditions.append(EvidenceItem.evidence_id == uuid.UUID(raw))
    except ValueError:
        pass
    item = (
        await session.execute(
            select(EvidenceItem).where(or_(*conditions)).limit(1)
        )
    ).scalar_one_or_none()
    if item is None:
        raise not_found("evidence", identifier)
    return item


async def read_raw_evidence(
    session: AsyncSession,
    item: EvidenceItem,
    *,
    storage: ContentAddressedStorage | None = None,
    actor_role: str,
    actor_id: uuid.UUID | None,
    correlation_id: str | None,
    path: str,
) -> tuple[bytes, IntegrityResult]:
    """Fail-closed raw read with an ALLOW/DENY audit event.

    Authorization is checked before bytes are touched.  A denied attempt still
    appends its audit event (the caller must commit before raising/returning).
    """

    store = storage or default_storage()
    try:
        ensure_raw_evidence_access(actor_role)
    except ApiError:
        await audit_raw_evidence_access(
            session,
            actor_role=actor_role,
            actor_id=actor_id,
            evidence_id=item.display_id,
            allowed=False,
            reason="Role lacks EVIDENCE_RAW capability",
            correlation_id=correlation_id,
            path=path,
        )
        raise

    digest = getattr(item, "content_digest", None)
    if not digest or not bool(getattr(item, "received", False)):
        raise evidence_not_received(item.display_id)
    data = store.read_blob(digest)
    result = IntegrityResult(
        ok=True,
        digest=normalize_digest(digest),
        size_bytes=len(data),
        storage_key=store.storage_key_for(digest),
    )
    await audit_raw_evidence_access(
        session,
        actor_role=actor_role,
        actor_id=actor_id,
        evidence_id=item.display_id,
        allowed=True,
        reason="Authorized raw evidence read",
        correlation_id=correlation_id,
        path=path,
    )
    return data, result


async def collect_manifest_items(
    session: AsyncSession, item: Any
) -> tuple[EvidenceManifest | None, list[EvidenceItem]]:
    run: Run | None = None
    if getattr(item, "run_id", None) is not None:
        run = await session.get(Run, item.run_id)
    manifest: EvidenceManifest | None = None
    if run is not None and run.evidence_manifest_id is not None:
        manifest = await session.get(EvidenceManifest, run.evidence_manifest_id)
    if manifest is None and getattr(item, "run_id", None) is not None:
        manifest = (
            await session.execute(
                select(EvidenceManifest)
                .where(EvidenceManifest.run_id == item.run_id)
                .order_by(EvidenceManifest.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    query = select(EvidenceItem)
    if manifest is not None:
        query = query.where(EvidenceItem.task_id == manifest.task_id)
    elif getattr(item, "task_id", None) is not None:
        query = query.where(EvidenceItem.task_id == item.task_id)
    else:
        query = query.where(EvidenceItem.evidence_id == item.evidence_id)
    rows = list(
        (
            await session.execute(
                query.order_by(EvidenceItem.display_id)
            )
        ).scalars().all()
    )
    return manifest, rows


def manifest_public_dict(manifest: EvidenceManifest | None) -> dict[str, Any] | None:
    if manifest is None:
        return None
    return {
        "manifest_id": str(manifest.manifest_id),
        "display_id": manifest.display_id,
        "task_id": str(manifest.task_id),
        "revision_id": str(manifest.revision_id),
        "run_id": str(manifest.run_id),
        "mode": manifest.mode,
        "acceptance_level": manifest.acceptance_level,
        "test_level": manifest.test_level,
        "required_evidence": dict(manifest.required_evidence or {}),
        "completeness": dict(manifest.completeness or {}),
        "denominators": dict(manifest.denominators or {}),
        "manifest_digest": manifest.manifest_digest,
        "created_by": manifest.created_by,
        "absolute_path_exposed": False,
    }


async def manifest_summary(
    session: AsyncSession, item: Any, *, storage: ContentAddressedStorage | None = None
) -> dict[str, Any]:
    manifest, rows = await collect_manifest_items(session, item)
    counts = manifest_counts(rows)
    blob_status: dict[str, str] = {}
    if storage is not None:
        for row in rows:
            if not row.content_digest:
                blob_status[row.display_id] = "missing"
                continue
            try:
                integrity = storage.verify_digest(row.content_digest)
                if integrity.ok:
                    blob_status[row.display_id] = "present"
                elif integrity.reason == "missing":
                    blob_status[row.display_id] = "missing"
                else:
                    blob_status[row.display_id] = "corrupt"
            except ApiError:
                blob_status[row.display_id] = "corrupt"
    item_states = [
        {
            "evidence_id": str(row.evidence_id),
            "display_id": row.display_id,
            "state": row.state,
            "expected": row.expected,
            "received": row.received,
            "verified": row.verified,
            "content_digest": row.content_digest,
            "storage_key": (
                storage.storage_key_for(row.content_digest)
                if storage is not None and row.content_digest
                else None
            ),
            "blob_state": blob_status.get(row.display_id),
        }
        for row in rows
    ]
    return {
        "manifest": manifest_public_dict(manifest),
        "counts": counts,
        "manifest_counts": counts,
        "items": item_states,
        "received_not_verified": counts["pending_verification"],
        "verified_requires_recompute": True,
        "immutable_evidence": True,
        "absolute_path_exposed": False,
    }


async def attach_evidence_blob(
    session: AsyncSession,
    item: EvidenceItem,
    data: bytes,
    *,
    storage: ContentAddressedStorage | None = None,
    expected_digest: str | None = None,
    expected_size: int | None = None,
    media_type: str | None = None,
    chunks_total: int = 1,
    chunks_received: int | None = None,
    actor_role: str,
    actor_id: uuid.UUID | None,
    correlation_id: str | None,
    path: str,
) -> dict[str, Any]:
    store = storage or default_storage()
    blob = store.put_blob(data, expected_digest=expected_digest)
    result = apply_upload(
        item,
        blob,
        media_type=media_type or getattr(item, "media_type", None),
        expected_size=expected_size,
        chunks_total=chunks_total,
        chunks_received=chunks_received,
    )
    await audit.append_event(
        session,
        actor_role=actor_role,
        actor_id=actor_id,
        action="EVIDENCE_RECEIVED",
        object_type="evidence",
        object_id=item.display_id,
        before=None,
        after={
            "digest": blob.digest,
            "size_bytes": blob.size_bytes,
            "storage_key": blob.storage_key,
            "state": item.state,
            "received": True,
            "verified": bool(result["verified"]),
        },
        reason="Content-addressed evidence blob received",
        correlation_id=correlation_id,
        path=path,
    )
    return {
        "evidence_id": str(item.evidence_id),
        "display_id": item.display_id,
        **result,
    }


async def verify_evidence_blob(
    session: AsyncSession,
    item: EvidenceItem,
    *,
    storage: ContentAddressedStorage | None = None,
    actor_role: str,
    actor_id: uuid.UUID | None,
    correlation_id: str | None,
    path: str,
) -> tuple[dict[str, Any], IntegrityResult]:
    store = storage or default_storage()
    digest = getattr(item, "content_digest", None)
    if not digest or not bool(getattr(item, "received", False)):
        raise evidence_not_received(item.display_id)
    result = store.verify_digest(digest)
    payload = apply_verification(item, result)
    await audit.append_event(
        session,
        actor_role=actor_role,
        actor_id=actor_id,
        action=(
            "EVIDENCE_VERIFIED"
            if result.ok
            else "EVIDENCE_INTEGRITY_FAILED"
        ),
        object_type="evidence",
        object_id=item.display_id,
        before=None,
        after={
            "digest": result.digest,
            "verified": result.ok,
            "integrity_status": payload["integrity_status"],
            "reason": result.reason,
            "state": item.state,
            "storage_key": result.storage_key,
        },
        reason=(
            "Digest recomputed and matched"
            if result.ok
            else "Digest recomputation failed; evidence marked conflicted"
        ),
        correlation_id=correlation_id,
        path=path,
    )
    return payload, result


# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RetentionPolicy:
    policy_id: str = "ret-pol-raw-evidence"
    object_class: str = "raw_evidence"
    retention_days: int = 30
    disposition: str = "purge_blob_keep_metadata"
    version: str = "ret-raw-01"
    hot_store: str = "local_content_addressed"
    audit_retained: bool = True
    metadata_retained: bool = True

    def as_record(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "object_class": self.object_class,
            "retention_days": self.retention_days,
            "disposition": self.disposition,
            "version": self.version,
            "hot_store": self.hot_store,
            "audit_retained": self.audit_retained,
            "metadata_retained": self.metadata_retained,
            "record_kind": "retention_policy",
        }


def default_retention_policy() -> RetentionPolicy:
    return RetentionPolicy(retention_days=int(settings.evidence_retention_days))


async def load_retention_policy(session: AsyncSession) -> RetentionPolicy:
    """Load the persisted raw-evidence policy when present, else the default.

    The seeded retention records cover audit/report/evidence metadata.  A
    dedicated raw-evidence row is optional; the default is a typed record that
    is always returned to callers so dry-runs are reproducible.
    """

    from ..models import Setting

    row = (
        await session.execute(
            select(Setting).where(
                Setting.category == "retention", Setting.key == "raw_evidence"
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return default_retention_policy()
    value = dict(row.value or {})
    try:
        days = int(value.get("retention_days", settings.evidence_retention_days))
    except (TypeError, ValueError):
        days = int(settings.evidence_retention_days)
    return RetentionPolicy(
        policy_id=str(value.get("policy_id") or "ret-pol-raw-evidence"),
        object_class=str(value.get("object_class") or "raw_evidence"),
        retention_days=max(days, 0),
        disposition=str(value.get("disposition") or "purge_blob_keep_metadata"),
        version=str(value.get("version") or "ret-raw-01"),
        hot_store=str(value.get("hot_store") or "local_content_addressed"),
        audit_retained=bool(value.get("audit_retained", True)),
        metadata_retained=bool(value.get("metadata_retained", True)),
    )


def _retention_hold(item: Any) -> bool:
    retention = getattr(item, "retention", None) or {}
    if not isinstance(retention, dict):
        return False
    if retention.get("archive_state") in ("legal_hold", "hold", "purged", "archived"):
        return True
    policy_class = str(retention.get("class") or "").lower()
    return policy_class in RETENTION_HOLD_CLASSES


def dry_run_cleanup(
    items: Iterable[Any],
    *,
    policy: RetentionPolicy | None = None,
    now: datetime | None = None,
    storage: ContentAddressedStorage | None = None,
    limit: int = 500,
) -> dict[str, Any]:
    """Return eligible items and blob states without deleting anything.

    This function is intentionally read-only: it never unlinks a file and never
    mutates the item.  ``analyzed`` is capped by ``limit`` so a dry-run stays
    bounded.
    """

    active_policy = policy or default_retention_policy()
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    cutoff = moment - timedelta(days=active_policy.retention_days)
    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    analyzed = 0
    present = 0
    missing = 0
    corrupt = 0

    for item in items:
        if analyzed >= limit:
            break
        analyzed += 1
        display_id = str(getattr(item, "display_id", getattr(item, "evidence_id", "")))
        digest = getattr(item, "content_digest", None)
        state = _state_of(item)
        created = _as_datetime(getattr(item, "created_at", None))
        reason: str | None = None
        if not bool(getattr(item, "received", False)):
            reason = "not_received"
        elif not digest:
            reason = "no_digest"
        elif state not in RETENTION_ELIGIBLE_STATES:
            reason = f"state_{state}"
        elif created is None:
            reason = "unknown_created_at"
        elif created > cutoff:
            reason = "within_retention_window"
        elif _retention_hold(item):
            reason = "retention_hold"
        if reason is not None:
            skipped.append({"display_id": display_id, "reason": reason})
            continue

        blob_state = "unchecked"
        digest_text = str(digest)
        if storage is not None:
            integrity = storage.verify_digest(digest_text)
            if integrity.ok:
                blob_state = "present"
                present += 1
            elif integrity.reason == "missing":
                blob_state = "missing"
                missing += 1
            else:
                blob_state = "corrupt"
                corrupt += 1
        age_days = max((moment - created).days, 0) if created is not None else None
        candidates.append(
            {
                "evidence_id": str(
                    getattr(item, "evidence_id", display_id)
                ),
                "display_id": display_id,
                "content_digest": digest,
                "storage_key": (
                    storage.storage_key_for(digest_text)
                    if storage is not None and digest
                    else None
                ),
                "state": state,
                "age_days": age_days,
                "blob_state": blob_state,
                "disposition": active_policy.disposition,
                "metadata_retained": active_policy.metadata_retained,
                "audit_retained": active_policy.audit_retained,
            }
        )

    return {
        "dry_run": True,
        "destructive": False,
        "deleted_count": 0,
        "policy": active_policy.as_record(),
        "cutoff": cutoff.isoformat().replace("+00:00", "Z"),
        "analyzed": analyzed,
        "candidate_count": len(candidates),
        "present_blob_count": present,
        "missing_blob_count": missing,
        "corrupt_blob_count": corrupt,
        "candidates": candidates,
        "skipped": skipped,
        "requires_explicit_admin_call": True,
        "requires_confirm_phrase": RETENTION_CONFIRM_PHRASE,
        "absolute_path_exposed": False,
    }


async def retention_dry_run(
    session: AsyncSession,
    *,
    storage: ContentAddressedStorage | None = None,
    now: datetime | None = None,
    limit: int = 500,
) -> dict[str, Any]:
    policy = await load_retention_policy(session)
    rows = list(
        (
            await session.execute(
                select(EvidenceItem).order_by(EvidenceItem.created_at)
            )
        ).scalars().all()
    )
    return dry_run_cleanup(
        rows, policy=policy, now=now, storage=storage or default_storage(), limit=limit
    )


async def execute_retention_cleanup(
    session: AsyncSession,
    *,
    dry_run: bool,
    confirm: str | None,
    principal_role: str,
    actor_id: uuid.UUID | None,
    correlation_id: str | None,
    path: str,
    storage: ContentAddressedStorage | None = None,
    now: datetime | None = None,
    limit: int = 500,
) -> dict[str, Any]:
    """Dry-run by default; a destructive purge needs ADMIN + explicit phrase."""

    if principal_role != "ADMIN":
        raise forbidden(
            "Retention cleanup is ADMIN only",
            details={"required_role": "ADMIN", "actual_role": principal_role},
        )
    store = storage or default_storage()
    plan = await retention_dry_run(session, storage=store, now=now, limit=limit)
    if dry_run:
        return plan

    if confirm != RETENTION_CONFIRM_PHRASE:
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            "Destructive retention requires the explicit confirm phrase",
            retryable=False,
            details={"field": "confirm", "expected": RETENTION_CONFIRM_PHRASE},
        )

    purged: list[dict[str, Any]] = []
    moment = now or datetime.now(UTC)
    for candidate in plan["candidates"]:
        digest = candidate.get("content_digest")
        if not digest or candidate.get("blob_state") != "present":
            continue
        removed = store.delete_blob(digest)
        if not removed:
            continue
        row = (
            await session.execute(
                select(EvidenceItem).where(
                    EvidenceItem.display_id == candidate["display_id"]
                )
            )
        ).scalar_one_or_none()
        if row is not None:
            retention = dict(row.retention or {})
            retention.update(
                {
                    "archive_state": "purged",
                    "purged_at": moment.isoformat().replace("+00:00", "Z"),
                    "disposition": plan["policy"]["disposition"],
                }
            )
            row.retention = retention
        purged.append(
            {
                "display_id": candidate["display_id"],
                "content_digest": digest,
                "storage_key": candidate.get("storage_key"),
            }
        )
        await audit.append_event(
            session,
            actor_role=principal_role,
            actor_id=actor_id,
            action="EVIDENCE_RETENTION_PURGED",
            object_type="evidence",
            object_id=candidate["display_id"],
            before={"archive_state": "pending"},
            after={
                "archive_state": "purged",
                "content_digest": digest,
                "storage_key": candidate.get("storage_key"),
                "metadata_retained": True,
                "audit_retained": True,
            },
            reason="Explicit ADMIN retention cleanup",
            correlation_id=correlation_id,
            path=path,
        )

    return {
        **plan,
        "dry_run": False,
        "destructive": True,
        "deleted_count": len(purged),
        "purged": purged,
        "policy": plan["policy"],
        "metadata_retained": True,
        "audit_retained": True,
    }


# ---------------------------------------------------------------------------
# Convenience export used by tests and the API
# ---------------------------------------------------------------------------
def public_blob_summary(blob: StoredBlob) -> dict[str, Any]:
    return blob.as_dict()


def retention_policy_record(policy: RetentionPolicy | None = None) -> dict[str, Any]:
    return (policy or default_retention_policy()).as_record()


FIELD_NAMES = ("digest", "size_bytes", "storage_key")
__all__ = [
    "ContentAddressedStorage",
    "IntegrityResult",
    "RetentionPolicy",
    "StoredBlob",
    "apply_upload",
    "apply_verification",
    "attach_evidence_blob",
    "audit_raw_evidence_access",
    "begin_upload",
    "default_retention_policy",
    "default_storage",
    "digest_bytes",
    "dry_run_cleanup",
    "ensure_raw_evidence_access",
    "execute_retention_cleanup",
    "load_retention_policy",
    "manifest_counts",
    "manifest_summary",
    "normalize_digest",
    "public_blob_summary",
    "record_partial",
    "retention_dry_run",
    "retention_policy_record",
    "role_may_read_raw_evidence",
    "verify_evidence_blob",
]
