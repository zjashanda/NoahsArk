"""Freeze a DRAFT report; frozen versions are never mutated in place."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import ApiError, not_found
from ..models import Report
from . import audit
from .report_model import iso
from .writes import resolve_actor_id


async def _resolve_report(session: AsyncSession, identifier: str) -> Report:
    raw = (identifier or "").strip()
    if not raw:
        raise not_found("report", identifier)
    conditions = [Report.display_id == raw]
    try:
        conditions.append(Report.report_id == uuid.UUID(raw))
    except ValueError:
        pass
    report = (
        await session.execute(select(Report).where(or_(*conditions)).limit(1))
    ).scalar_one_or_none()
    if report is None:
        raise not_found("report", identifier)
    return report


async def freeze_report(
    session: AsyncSession,
    identifier: str,
    *,
    principal_role: str,
    actor: str | None,
    correlation_id: str | None,
    path: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = await _resolve_report(session, identifier)
    if report.lifecycle != "DRAFT":
        raise ApiError(
            409,
            "REPORT_NOT_DRAFT",
            "Only a DRAFT report can be frozen",
            retryable=False,
            details={"report_id": report.display_id, "lifecycle": report.lifecycle},
        )
    frozen_at = now or datetime.now(UTC)
    report.lifecycle = "FROZEN"
    report.frozen_at = frozen_at
    await audit.append_event(
        session,
        actor_role=principal_role,
        actor_id=await resolve_actor_id(session, actor),
        action="REPORT_FROZEN",
        object_type="report",
        object_id=report.display_id,
        before={"lifecycle": "DRAFT", "frozen_at": None},
        after={
            "lifecycle": "FROZEN",
            "frozen_at": frozen_at.isoformat().replace("+00:00", "Z"),
            "report_digest": report.report_digest,
        },
        reason="Froze report version; later corrections require a new version",
        correlation_id=correlation_id,
        path=path,
    )
    return {
        "report_id": str(report.report_id),
        "display_id": report.display_id,
        "version": report.version,
        "lifecycle": report.lifecycle,
        "frozen": True,
        "frozen_at": iso(report.frozen_at),
        "report_digest": report.report_digest,
    }


__all__ = ["freeze_report"]
