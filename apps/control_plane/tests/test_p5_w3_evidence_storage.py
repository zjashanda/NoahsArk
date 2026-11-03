"""P5-W3 evidence storage and integrity rules (unit level).

These tests exercise the content-addressed store directly with temporary
directories.  They need no database and lock down the properties the wave
depends on:

- bytes are addressed by their recomputed SHA-256 digest;
- a declared digest mismatch never writes and never trusts the caller;
- an existing blob is never overwritten, including when it is corrupt;
- missing/corrupt bytes fail closed instead of returning partial content;
- only a relative ``sha256/..`` storage key is ever exposed to callers;
- ``received`` and ``verified`` remain independent;
- retention dry-runs classify eligibility, holds and blob state without
  deleting anything.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from noahsark.errors import ApiError
from noahsark.services.evidence_storage import (
    ContentAddressedStorage,
    IntegrityResult,
    RetentionPolicy,
    StoredBlob,
    apply_upload,
    apply_verification,
    attach_evidence_blob,
    begin_upload,
    digest_bytes,
    dry_run_cleanup,
    manifest_counts,
    normalize_digest,
    record_partial,
    role_may_read_raw_evidence,
)

DIGEST_HEX = hashlib.sha256(b"abc").hexdigest()


def _item(**overrides: Any) -> SimpleNamespace:
    values: dict[str, Any] = {
        "evidence_id": uuid.uuid4(),
        "display_id": "ev-unit-001",
        "state": "declared",
        "content_digest": None,
        "size_bytes": None,
        "media_type": None,
        "digest_scope": None,
        "upload": None,
        "locator": None,
        "integrity": None,
        "retention": {},
        "expected": True,
        "received": False,
        "verified": False,
        "created_at": datetime.now(UTC),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _assert_api_error(exc_info: pytest.ExceptionInfo[ApiError], status: int, code: str) -> None:
    assert exc_info.value.status_code == status
    assert exc_info.value.code == code


def _stored(data: bytes) -> StoredBlob:
    return StoredBlob(
        digest=digest_bytes(data),
        size_bytes=len(data),
        storage_key=ContentAddressedStorage.storage_key_for(digest_bytes(data)),
    )


# ---------------------------------------------------------------------------
# Digest canonicalization
# ---------------------------------------------------------------------------
def test_digest_helpers_are_canonical_and_reject_non_sha256() -> None:
    assert digest_bytes(b"abc") == f"sha256:{DIGEST_HEX}"
    assert normalize_digest(f"  SHA256:{DIGEST_HEX.upper()}  ") == f"sha256:{DIGEST_HEX}"

    for bad in (None, "", "sha256:abc", f"md5:{DIGEST_HEX}", f"sha256:{DIGEST_HEX[:-1]}g"):
        with pytest.raises(ApiError) as exc_info:
            normalize_digest(bad)
        _assert_api_error(exc_info, 400, "VALIDATION_ERROR")


# ---------------------------------------------------------------------------
# Content-addressed storage
# ---------------------------------------------------------------------------
def test_put_read_and_verify_roundtrip_exposes_only_relative_key(tmp_path) -> None:
    store = ContentAddressedStorage(tmp_path / "private-root")
    data = b"raw evidence bytes"

    blob = store.put_blob(data)

    assert blob.digest == digest_bytes(data)
    assert blob.size_bytes == len(data)
    assert blob.storage_key.startswith("sha256/")
    assert blob.storage_key.endswith(".blob")
    assert "private-root" not in json.dumps(blob.as_dict())
    assert blob.as_dict()["absolute_path_exposed"] is False
    assert store.path_for(blob.digest).read_bytes() == data
    assert store.read_blob(blob.digest) == data

    integrity = store.verify_digest(blob.digest)
    assert integrity.ok is True
    assert integrity.digest == blob.digest
    assert integrity.size_bytes == len(data)
    assert integrity.reason is None


def test_put_blob_rejects_declared_digest_mismatch_without_writing(tmp_path) -> None:
    store = ContentAddressedStorage(tmp_path / "store")
    data = b"declared bytes"
    declared = digest_bytes(b"different bytes")

    with pytest.raises(ApiError) as exc_info:
        store.put_blob(data, expected_digest=declared)

    _assert_api_error(exc_info, 400, "EVIDENCE_DIGEST_MISMATCH")
    assert exc_info.value.details["expected_digest"] == declared
    assert exc_info.value.details["actual_digest"] == digest_bytes(data)
    assert store.has_blob(digest_bytes(data)) is False


def test_put_blob_is_idempotent_and_does_not_replace_same_digest(tmp_path) -> None:
    store = ContentAddressedStorage(tmp_path / "store")
    data = b"same bytes"

    first = store.put_blob(data)
    path = store.path_for(first.digest)
    before = (path.stat().st_ino, path.stat().st_mtime_ns, path.read_bytes())

    second = store.put_blob(data)
    after = (path.stat().st_ino, path.stat().st_mtime_ns, path.read_bytes())

    assert second == first
    assert after == before


def test_corrupt_existing_blob_is_never_overwritten(tmp_path) -> None:
    store = ContentAddressedStorage(tmp_path / "store")
    data = b"original evidence"
    blob = store.put_blob(data)
    path = store.path_for(blob.digest)
    path.write_bytes(b"tampered evidence")

    with pytest.raises(ApiError) as exc_info:
        store.put_blob(data)

    _assert_api_error(exc_info, 409, "EVIDENCE_INTEGRITY_FAILURE")
    assert path.read_bytes() == b"tampered evidence"
    integrity = store.verify_digest(blob.digest)
    assert integrity.ok is False
    assert integrity.reason == "digest_mismatch"


def test_missing_and_corrupt_blobs_fail_closed(tmp_path) -> None:
    store = ContentAddressedStorage(tmp_path / "store")
    missing_digest = digest_bytes(b"never stored")

    integrity = store.verify_digest(missing_digest)
    assert integrity.ok is False
    assert integrity.reason == "missing"
    assert integrity.size_bytes is None
    with pytest.raises(ApiError) as exc_info:
        store.read_blob(missing_digest)
    _assert_api_error(exc_info, 404, "NOT_FOUND")

    data = b"later corrupted"
    blob = store.put_blob(data)
    store.path_for(blob.digest).write_bytes(b"corrupted")
    with pytest.raises(ApiError) as exc_info:
        store.read_blob(blob.digest)
    _assert_api_error(exc_info, 409, "EVIDENCE_INTEGRITY_FAILURE")


def test_size_limit_and_path_traversal_are_rejected(tmp_path) -> None:
    store = ContentAddressedStorage(tmp_path / "store", max_bytes=4)

    with pytest.raises(ApiError) as exc_info:
        store.put_blob(b"12345")
    _assert_api_error(exc_info, 413, "EVIDENCE_TOO_LARGE")
    assert exc_info.value.details == {"size_bytes": 5, "max_bytes": 4}

    for traversal in ("../../etc/passwd", "sha256:../../etc/passwd", "sha256:" + "a" * 63 + "/"):
        with pytest.raises(ApiError) as exc_info:
            store.read_blob(traversal)
        _assert_api_error(exc_info, 400, "VALIDATION_ERROR")

    safe_digest = digest_bytes(b"safe")
    safe_hex = safe_digest.removeprefix("sha256:")
    key = ContentAddressedStorage.storage_key_for(safe_digest)
    assert ".." not in key
    assert key == f"sha256/{safe_hex[:2]}/{safe_hex[2:4]}/{safe_hex}.blob"


# ---------------------------------------------------------------------------
# Received versus verified state machine
# ---------------------------------------------------------------------------
def test_apply_upload_marks_received_but_not_verified() -> None:
    item = _item()
    blob = _stored(b"incoming")

    result = apply_upload(item, blob, media_type="text/plain")

    assert item.state == "complete"
    assert item.received is True
    assert item.verified is False
    assert item.content_digest == blob.digest
    assert item.integrity["digest_verified"] is False
    assert item.integrity["integrity_status"] == "UNVERIFIED"
    assert item.locator["uri"] == blob.storage_key
    assert result["received"] is True
    assert result["verified"] is False
    assert result["received_is_not_verified"] is True


def test_apply_upload_rejects_different_digest_and_size_mismatch() -> None:
    existing_digest = digest_bytes(b"existing")
    item = _item(content_digest=existing_digest, received=True, state="complete")
    different = _stored(b"different")

    with pytest.raises(ApiError) as exc_info:
        apply_upload(item, different)
    _assert_api_error(exc_info, 409, "EVIDENCE_IMMUTABLE")
    assert item.content_digest == existing_digest

    fresh = _item()
    blob = _stored(b"size")
    with pytest.raises(ApiError) as exc_info:
        apply_upload(fresh, blob, expected_size=blob.size_bytes + 1)
    _assert_api_error(exc_info, 400, "EVIDENCE_SIZE_MISMATCH")
    assert fresh.received is False


def test_reuploading_identical_verified_bytes_does_not_downgrade() -> None:
    digest = digest_bytes(b"verified")
    item = _item(
        state="verified",
        content_digest=digest,
        received=True,
        verified=True,
        integrity={"digest_verified": True},
    )
    blob = _stored(b"verified")

    result = apply_upload(item, blob)

    assert item.state == "verified"
    assert item.received is True
    assert item.verified is True
    assert result["verified"] is True
    assert result["received_is_not_verified"] is False


class _EmptyAuditSession:
    """Narrow session seam for orchestration tests that need no database."""

    def __init__(self) -> None:
        self.events: list[Any] = []

    def get_bind(self) -> Any:
        raise RuntimeError("unit test session has no bind")

    async def execute(self, *_args: Any, **_kwargs: Any) -> Any:
        return SimpleNamespace(scalar_one_or_none=lambda: None)

    def add(self, event: Any) -> None:
        self.events.append(event)


@pytest.mark.asyncio
async def test_receiving_identical_bytes_for_verified_item_reports_verified(tmp_path) -> None:
    store = ContentAddressedStorage(tmp_path / "store")
    data = b"already verified"
    item = _item(
        state="verified",
        content_digest=digest_bytes(data),
        received=True,
        verified=True,
    )
    session = _EmptyAuditSession()

    payload = await attach_evidence_blob(
        session,  # type: ignore[arg-type]
        item,  # type: ignore[arg-type]
        data,
        storage=store,
        actor_role="ADMIN",
        actor_id=None,
        correlation_id="w3-unit-receive",
        path="/api/v1/evidence/w3/content",
    )

    assert payload["received"] is True
    assert payload["verified"] is True
    assert payload["received_is_not_verified"] is False
    assert item.state == "verified"
    assert session.events[0].action == "EVIDENCE_RECEIVED"
    assert session.events[0].after["verified"] is True


def test_apply_verification_requires_received_and_recomputes() -> None:
    not_received = _item()
    with pytest.raises(ApiError) as exc_info:
        apply_verification(
            not_received,
            IntegrityResult(ok=True, digest=digest_bytes(b"x"), size_bytes=1, storage_key="k"),
        )
    _assert_api_error(exc_info, 409, "EVIDENCE_NOT_RECEIVED")

    digest = digest_bytes(b"verified bytes")
    item = _item(
        state="complete",
        content_digest=digest,
        received=True,
        verified=False,
    )
    payload = apply_verification(
        item,
        IntegrityResult(ok=True, digest=digest, size_bytes=14, storage_key="k"),
        verified_at=datetime(2026, 10, 30, tzinfo=UTC),
    )
    assert item.state == "verified"
    assert item.verified is True
    assert item.integrity["integrity_status"] == "OK"
    assert item.integrity["verified_at"] == "2026-10-30T00:00:00Z"
    assert payload["received_is_not_verified"] is False

    conflicted = _item(state="complete", content_digest=digest, received=True)
    payload = apply_verification(
        conflicted,
        IntegrityResult(
            ok=False,
            digest=digest,
            size_bytes=14,
            storage_key="k",
            reason="digest_mismatch",
        ),
    )
    assert conflicted.state == "conflicted"
    assert conflicted.verified is False
    assert conflicted.integrity["integrity_status"] == "DIGEST_MISMATCH"
    assert payload["received_is_not_verified"] is True

    forged = _item(state="complete", content_digest=digest, received=True)
    apply_verification(
        forged,
        IntegrityResult(ok=True, digest=digest_bytes(b"other"), size_bytes=1, storage_key="k"),
    )
    assert forged.state == "conflicted"
    assert forged.verified is False


def test_upload_chunk_state_machine() -> None:
    item = _item()

    started = begin_upload(item, chunks_total=3)
    assert started["state"] == "uploading"
    assert item.state == "uploading"
    assert item.upload == {"chunks_total": 3, "chunks_received": 0, "complete": False}

    partial = record_partial(item, chunks_received=2, chunks_total=3)
    assert partial["state"] == "partial"
    assert item.state == "partial"
    assert item.upload["complete"] is False

    item.content_digest = digest_bytes(b"chunks")
    done = record_partial(item, chunks_received=3, chunks_total=3)
    assert done["state"] == "complete"
    assert item.state == "complete"


def test_raw_evidence_capability_is_explicit() -> None:
    assert role_may_read_raw_evidence("ADMIN") is True
    assert role_may_read_raw_evidence("OBSERVER") is False
    assert role_may_read_raw_evidence("APPROVER") is False
    assert role_may_read_raw_evidence("SESSION_MANAGER") is False


# ---------------------------------------------------------------------------
# Manifest counts
# ---------------------------------------------------------------------------
def test_manifest_counts_keep_expected_received_verified_separate() -> None:
    missing = _item(expected=True, received=False, verified=False, state="declared")
    received_only = _item(expected=True, received=True, verified=False, state="complete")
    verified = _item(expected=True, received=True, verified=True, state="verified")

    counts = manifest_counts([missing, received_only, verified])

    assert counts["total"] == 3
    assert counts["expected"] == 3
    assert counts["received"] == 2
    assert counts["verified"] == 1
    assert counts["missing"] == 1
    assert counts["pending_verification"] == 1
    assert counts["received_equals_verified"] is False
    assert counts["complete"] is False
    assert counts["evidence_status"] == "INCOMPLETE"


def test_received_but_unverified_is_unverified_not_complete() -> None:
    counts = manifest_counts(
        [_item(expected=True, received=True, verified=False, state="complete")]
    )

    assert counts["received"] == 1
    assert counts["verified"] == 0
    assert counts["complete"] is False
    assert counts["evidence_status"] == "UNVERIFIED"
    assert counts["received_not_verified"] == 1


def test_all_expected_verified_is_complete_and_conflict_dominates() -> None:
    complete = manifest_counts(
        [_item(expected=True, received=True, verified=True, state="verified")]
    )
    assert complete["complete"] is True
    assert complete["evidence_status"] == "COMPLETE"

    conflicted = manifest_counts(
        [
            _item(expected=True, received=True, verified=True, state="verified"),
            _item(expected=True, received=True, verified=False, state="conflicted"),
        ]
    )
    assert conflicted["conflicted"] == 1
    assert conflicted["complete"] is False
    assert conflicted["evidence_status"] == "CONFLICTED"


def test_extra_received_item_cannot_mask_a_missing_expected_item() -> None:
    missing_expected = _item(expected=True, received=False, verified=False, state="declared")
    extra_verified = _item(expected=False, received=True, verified=True, state="verified")

    counts = manifest_counts([missing_expected, extra_verified])

    assert counts["expected"] == 1
    assert counts["received"] == 1
    assert counts["verified"] == 1
    assert counts["missing"] == 1
    assert counts["complete"] is False
    assert counts["evidence_status"] == "INCOMPLETE"


def test_empty_manifest_is_not_reported_complete() -> None:
    counts = manifest_counts([])
    assert counts["total"] == 0
    assert counts["expected"] == 0
    assert counts["complete"] is False
    assert counts["evidence_status"] == "UNVERIFIED"


# ---------------------------------------------------------------------------
# Retention dry-run
# ---------------------------------------------------------------------------
def _retention_item(
    store: ContentAddressedStorage,
    *,
    display_id: str,
    created_at: datetime,
    data: bytes | None = b"old evidence",
    **overrides: Any,
) -> SimpleNamespace:
    digest = None
    if data is not None:
        digest = store.put_blob(data).digest
    values: dict[str, Any] = {
        "display_id": display_id,
        "evidence_id": uuid.uuid4(),
        "state": "verified",
        "content_digest": digest,
        "received": True,
        "verified": True,
        "retention": {"class": "task_scoped", "archive_state": "pending"},
        "created_at": created_at,
    }
    values.update(overrides)
    if values["content_digest"] is not None and not store.has_blob(values["content_digest"]):
        store.put_blob(data or b"old evidence")
    return SimpleNamespace(**values)


def test_retention_dry_run_classifies_holds_and_blob_states_without_deleting(tmp_path) -> None:
    store = ContentAddressedStorage(tmp_path / "store")
    now = datetime(2026, 10, 30, tzinfo=UTC)
    old = now - timedelta(days=60)
    recent = now - timedelta(days=1)
    present = _retention_item(store, display_id="ev-present", created_at=old)
    held = _retention_item(
        store,
        display_id="ev-hold",
        created_at=old,
        data=b"held evidence",
        retention={"class": "legal_hold", "archive_state": "hold"},
    )
    recent_item = _retention_item(store, display_id="ev-recent", created_at=recent, data=b"recent")
    not_received = _retention_item(
        store,
        display_id="ev-not-received",
        created_at=old,
        data=b"not received",
        received=False,
        verified=False,
        state="declared",
    )
    partial = _retention_item(
        store,
        display_id="ev-partial",
        created_at=old,
        data=b"partial",
        state="partial",
        verified=False,
    )
    missing = _retention_item(
        store, display_id="ev-missing", created_at=old, data=b"missing evidence"
    )
    store.delete_blob(missing.content_digest)
    corrupt = _retention_item(store, display_id="ev-corrupt", created_at=old, data=b"corrupt")
    store.path_for(corrupt.content_digest).write_bytes(b"tampered")

    plan = dry_run_cleanup(
        [present, held, recent_item, not_received, partial, missing, corrupt],
        policy=RetentionPolicy(retention_days=30),
        now=now,
        storage=store,
    )

    assert plan["dry_run"] is True
    assert plan["destructive"] is False
    assert plan["deleted_count"] == 0
    assert plan["requires_confirm_phrase"] == "PURGE_EVIDENCE"
    assert plan["absolute_path_exposed"] is False
    assert str(tmp_path) not in json.dumps(plan)
    assert plan["present_blob_count"] == 1
    assert plan["missing_blob_count"] == 1
    assert plan["corrupt_blob_count"] == 1
    candidates = {row["display_id"]: row for row in plan["candidates"]}
    assert set(candidates) == {"ev-present", "ev-missing", "ev-corrupt"}
    assert candidates["ev-present"]["blob_state"] == "present"
    assert candidates["ev-present"]["storage_key"].startswith("sha256/")
    assert candidates["ev-missing"]["blob_state"] == "missing"
    assert candidates["ev-corrupt"]["blob_state"] == "corrupt"
    assert candidates["ev-present"]["disposition"] == "purge_blob_keep_metadata"
    skipped = {row["display_id"]: row["reason"] for row in plan["skipped"]}
    assert skipped["ev-hold"] == "retention_hold"
    assert skipped["ev-recent"] == "within_retention_window"
    assert skipped["ev-not-received"] == "not_received"
    assert skipped["ev-partial"] == "state_partial"

    assert store.has_blob(present.content_digest) is True
    assert store.has_blob(held.content_digest) is True
    assert store.has_blob(missing.content_digest) is False


def test_retention_dry_run_limit_is_bounded_and_policy_is_recorded() -> None:
    now = datetime(2026, 10, 30, tzinfo=UTC)
    old = now - timedelta(days=60)
    policy = RetentionPolicy(retention_days=30, version="ret-test")
    items = [
        _item(
            display_id=f"ev-limit-{index}",
            state="verified",
            received=True,
            verified=True,
            content_digest=digest_bytes(f"limit-{index}".encode()),
            created_at=old,
        )
        for index in range(3)
    ]

    dry = dry_run_cleanup(items, policy=policy, now=now, limit=2)

    assert dry["analyzed"] == 2
    assert dry["candidate_count"] == 2
    assert dry["policy"]["policy_id"] == "ret-pol-raw-evidence"
    assert dry["policy"]["version"] == "ret-test"
    assert dry["policy"]["metadata_retained"] is True
    assert dry["policy"]["audit_retained"] is True
    assert dry["cutoff"] == "2026-09-30T00:00:00Z"
