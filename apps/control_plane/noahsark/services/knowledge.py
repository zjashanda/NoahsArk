"""Human-reviewed promotion of knowledge candidates.

Candidates are proposals: they are never auto-promoted.  Promotion requires an
explicit human reviewer holding the target-library capability, a candidate that
has already passed review (``APPROVED``), a complete source chain and an audit
event.  The resulting knowledge item is a new version; existing history is not
rewritten.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.permissions import Capability, ensure_capability
from ..errors import ApiError, not_found
from ..models import KnowledgeCandidate, KnowledgeItem
from . import audit
from .writes import resolve_actor_id

TARGET_CAPABILITIES: dict[str, Capability] = {
    "COMMON": Capability.KNOWLEDGE_MERGE_COMMON,
    "TOOL": Capability.KNOWLEDGE_MERGE_TOOL,
    "ANOMALY": Capability.KNOWLEDGE_PROMOTE_ANOMALY,
}
PROMOTION_READY_STATUS = "APPROVED"
PROMOTED_STATUS = "PROMOTED"
HUMAN_REVIEW_ROLES = frozenset({"ADMIN"})


def promotion_forbidden(reason: str, **details: Any) -> ApiError:
    return ApiError(
        409,
        "KNOWLEDGE_PROMOTION_FORBIDDEN",
        "Knowledge candidate cannot be promoted",
        retryable=False,
        details={"reason": reason, **details},
    )


async def _resolve_candidate(
    session: AsyncSession, identifier: str
) -> KnowledgeCandidate:
    raw = (identifier or "").strip()
    if not raw:
        raise not_found("knowledge_candidate", identifier)
    conditions = [KnowledgeCandidate.display_id == raw]
    try:
        conditions.append(KnowledgeCandidate.candidate_id == uuid.UUID(raw))
    except ValueError:
        pass
    candidate = (
        await session.execute(
            select(KnowledgeCandidate).where(or_(*conditions)).limit(1)
        )
    ).scalar_one_or_none()
    if candidate is None:
        raise not_found("knowledge_candidate", identifier)
    return candidate


def _ensure_human_reviewer(principal_role: str, actor: str | None) -> None:
    if principal_role not in HUMAN_REVIEW_ROLES:
        raise promotion_forbidden(
            "HUMAN_REVIEW_REQUIRED",
            principal_role=principal_role,
        )
    if actor is None or not actor.strip():
        raise promotion_forbidden("HUMAN_IDENTITY_REQUIRED")
    lowered = actor.strip().lower()
    if lowered.startswith(("agent", "system")):
        raise promotion_forbidden("AGENT_CANNOT_PROMOTE", actor=actor)


async def promote_candidate(
    session: AsyncSession,
    identifier: str,
    *,
    target_library: str,
    reason: str,
    similarity_check: dict[str, Any],
    principal_role: str,
    actor: str | None,
    correlation_id: str | None,
    path: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    capability = TARGET_CAPABILITIES.get(target_library)
    if capability is None:
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            "target_library must be COMMON, TOOL or ANOMALY",
            details={"allowed": sorted(TARGET_CAPABILITIES)},
        )
    ensure_capability(principal_role, capability)
    _ensure_human_reviewer(principal_role, actor)

    candidate = await _resolve_candidate(session, identifier)
    if candidate.automatic_promotion_allowed:
        raise promotion_forbidden(
            "AUTO_PROMOTION_NEVER_ALLOWED",
            candidate_id=candidate.display_id,
        )
    if not candidate.requires_human_review:
        raise promotion_forbidden(
            "HUMAN_REVIEW_FLAG_MISSING",
            candidate_id=candidate.display_id,
        )
    if candidate.status != PROMOTION_READY_STATUS:
        raise promotion_forbidden(
            "REVIEW_NOT_COMPLETE",
            candidate_id=candidate.display_id,
            status=candidate.status,
            required_status=PROMOTION_READY_STATUS,
        )
    if not candidate.source_chain:
        raise promotion_forbidden(
            "SOURCE_CHAIN_INCOMPLETE", candidate_id=candidate.display_id
        )
    if not candidate.applicability.strip():
        raise promotion_forbidden(
            "APPLICABILITY_REQUIRED", candidate_id=candidate.display_id
        )

    promoted_at = now or datetime.now(UTC)
    knowledge_id = uuid.uuid4()
    display_id = f"kn-{knowledge_id.hex[:8]}"
    content = dict(candidate.content or {})
    summary = str(
        content.get("summary")
        or candidate.title
    )
    item = KnowledgeItem(
        knowledge_id=knowledge_id,
        display_id=display_id,
        status="APPROVED",
        title=candidate.title,
        applicability=candidate.applicability,
        summary=summary,
        source_chain=list(candidate.source_chain),
        content={
            "source_candidate_ids": [candidate.display_id],
            "promotion": {
                "decision": "APPROVED",
                "target_library": target_library,
                "reviewed_by": actor,
                "similarity_check": similarity_check,
            },
            "source_content": content,
        },
        version=1,
        approved_by=await resolve_actor_id(session, actor),
        updated_at=promoted_at,
        source="control-plane",
        seed=False,
    )
    session.add(item)
    event = await audit.append_event(
        session,
        actor_role=principal_role,
        actor_id=await resolve_actor_id(session, actor),
        action="KNOWLEDGE_PROMOTED",
        object_type="knowledge_candidate",
        object_id=candidate.display_id,
        before={
            "status": candidate.status,
            "automatic_promotion_allowed": candidate.automatic_promotion_allowed,
        },
        after={
            "status": PROMOTED_STATUS,
            "knowledge_id": display_id,
            "target_library": target_library,
            "decision": "APPROVED",
            "similarity_check": similarity_check,
        },
        reason=reason,
        correlation_id=correlation_id,
        path=path,
    )
    candidate.status = PROMOTED_STATUS
    candidate.updated_at = promoted_at
    candidate.content = {
        **content,
        "promotion": {
            "decision": "APPROVED",
            "target_library": target_library,
            "knowledge_id": display_id,
            "promotion_event_id": event.event_id,
            "reviewed_by": actor,
            "similarity_check": similarity_check,
        },
    }
    item.content = {
        **item.content,
        "promotion_event_id": event.event_id,
    }
    return {
        "candidate_id": str(candidate.candidate_id),
        "candidate_display_id": candidate.display_id,
        "knowledge_id": str(knowledge_id),
        "knowledge_display_id": display_id,
        "status": candidate.status,
        "decision": "APPROVED",
        "target_library": target_library,
        "promotion_event_id": event.event_id,
        "automatic_promotion_allowed": False,
        "requires_human_review": True,
        "created": True,
    }


__all__ = ["TARGET_CAPABILITIES", "promote_candidate", "promotion_forbidden"]
