"""Database metadata and public projection for campaign evidence artifacts.

Blob bytes live in :mod:`noahsark.services.artifact_storage`; this module only
owns the immutable row and the API view.  A download always resolves the row
first and then a generated relative storage key, so the URL segment is never
used as a filesystem path.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import not_found
from ..models.artifact import TestCampaignArtifact
from .artifact_storage import (
    ArtifactStorage,
    StoredArtifact,
    artifact_immutable,
    safe_artifact_name,
)


def artifact_view(row: TestCampaignArtifact, campaign_id: uuid.UUID) -> dict[str, object]:
    uploaded = row.uploaded_at
    if uploaded.tzinfo is None:
        uploaded = uploaded.replace(tzinfo=UTC)
    return {
        "artifact_id": str(row.artifact_id),
        "name": row.name,
        "size_bytes": row.size_bytes,
        "digest": row.digest,
        "media_type": row.media_type,
        "uploaded_at": uploaded.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "download_url": (
            f"/api/v1/test-campaigns/{campaign_id}/artifacts/"
            f"{quote(row.name, safe='')}"
        ),
        "downloadable": True,
    }


def artifact_collection(
    rows: Iterable[TestCampaignArtifact], campaign_id: uuid.UUID
) -> dict[str, object]:
    stored_rows = list(rows)
    files = [artifact_view(row, campaign_id) for row in stored_rows]
    return {
        "files": files,
        "count": len(files),
        "total_bytes": sum(row.size_bytes for row in stored_rows),
        "all_downloadable": True,
    }


async def list_artifacts(
    session: AsyncSession, campaign_ids: Iterable[uuid.UUID]
) -> dict[uuid.UUID, list[TestCampaignArtifact]]:
    ids = list(campaign_ids)
    if not ids:
        return {}
    rows = (
        await session.execute(
            select(TestCampaignArtifact)
            .where(TestCampaignArtifact.campaign_id.in_(ids))
            .order_by(TestCampaignArtifact.uploaded_at, TestCampaignArtifact.name)
        )
    ).scalars()
    grouped: dict[uuid.UUID, list[TestCampaignArtifact]] = {
        campaign_id: [] for campaign_id in ids
    }
    for row in rows:
        grouped.setdefault(row.campaign_id, []).append(row)
    return grouped


async def record_artifact(
    session: AsyncSession,
    *,
    campaign_id: uuid.UUID,
    command_id: uuid.UUID | None,
    stored: StoredArtifact,
    now: datetime | None = None,
) -> tuple[TestCampaignArtifact, bool]:
    """Insert immutable metadata; same name + same digest is idempotent."""

    existing = await _find(session, campaign_id, stored.name)
    if existing is not None:
        return _reconcile_existing(existing, stored)

    row = TestCampaignArtifact(
        artifact_id=uuid.uuid4(),
        campaign_id=campaign_id,
        command_id=command_id,
        name=stored.name,
        storage_key=stored.storage_key,
        digest=stored.digest,
        size_bytes=stored.size_bytes,
        media_type=stored.media_type,
        source="node",
        uploaded_at=now or datetime.now(UTC),
    )
    try:
        async with session.begin_nested():
            session.add(row)
            await session.flush()
    except IntegrityError:
        # A concurrent upload won the (campaign, name) race; reconcile instead
        # of surfacing a raw constraint error.  Same digest stays idempotent.
        existing = await _find(session, campaign_id, stored.name)
        if existing is None:
            raise
        return _reconcile_existing(existing, stored)
    return row, False


async def _find(
    session: AsyncSession, campaign_id: uuid.UUID, name: str
) -> TestCampaignArtifact | None:
    return (
        await session.execute(
            select(TestCampaignArtifact).where(
                TestCampaignArtifact.campaign_id == campaign_id,
                TestCampaignArtifact.name == name,
            )
        )
    ).scalar_one_or_none()


def _reconcile_existing(
    existing: TestCampaignArtifact, stored: StoredArtifact
) -> tuple[TestCampaignArtifact, bool]:
    if existing.digest == stored.digest and existing.size_bytes == stored.size_bytes:
        return existing, True
    raise artifact_immutable(existing.name, existing.digest, stored.digest)


async def get_artifact(
    session: AsyncSession, campaign_id: uuid.UUID, name: str
) -> TestCampaignArtifact:
    if safe_artifact_name(name) != name:
        raise not_found("test_campaign_artifact", name)
    row = await _find(session, campaign_id, name)
    if row is None:
        raise not_found("test_campaign_artifact", name)
    return row


def descriptor_dict(storage: ArtifactStorage, stored: StoredArtifact) -> dict[str, object]:
    return {
        **stored.as_dict(),
        "downloadable": True,
        "max_bytes": storage.max_bytes,
    }
