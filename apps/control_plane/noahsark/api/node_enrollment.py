"""Platform enrollment for fresh nodes.

A machine with no pre-created node calls ``POST /node/v1/enroll`` once with the
platform enrollment token.  The control plane derives a unique ``display_id``
from the hostname, stores only the SHA-256 digest of a freshly generated
per-node bearer token, and returns that plaintext exactly once.  Neither token
is ever logged or written to the audit payload.
"""

from __future__ import annotations

import hmac
import re
import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_session
from ..errors import ApiError
from ..models.device import Node
from ..services import audit
from .envelope import correlation_id
from .node_gateway import TOKEN_HASH_KEY, token_digest

router = APIRouter(prefix="/node/v1", tags=["node-gateway"])

Session = Annotated[AsyncSession, Depends(get_session)]

MAX_DISPLAY_ID_LENGTH = 80
_SLUG_MAX_LENGTH = 64


class EnrollRequest(BaseModel):
    enrollment_token: str = ""
    hostname: str = Field(min_length=1, max_length=200)
    agent_version: str = Field(default="unknown", max_length=80)


def _enrollment_display_slug(hostname: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", hostname.strip().lower()).strip("-")
    return slug[:_SLUG_MAX_LENGTH] or "node"


async def _display_id_taken(session: AsyncSession, display_id: str) -> bool:
    row = await session.execute(
        select(Node.node_id).where(Node.display_id == display_id)
    )
    return row.scalar_one_or_none() is not None


async def _unique_display_id(session: AsyncSession, hostname: str) -> str:
    """Derive a display_id from the hostname, suffixing on a collision."""

    slug = _enrollment_display_slug(hostname)
    if not await _display_id_taken(session, slug):
        return slug
    base = slug[: MAX_DISPLAY_ID_LENGTH - 5]
    for _ in range(20):
        candidate = f"{base}-{secrets.token_hex(2)}"
        if not await _display_id_taken(session, candidate):
            return candidate
    raise ApiError(
        503,
        "NODE_ENROLLMENT_BUSY",
        "Could not allocate a unique node display_id",
        retryable=True,
    )


@router.post("/enroll")
async def enroll(
    body: EnrollRequest,
    request: Request,
    session: Session,
) -> dict:
    provided = body.enrollment_token or ""
    configured = settings.node_enrollment_token
    if not provided.strip() or not hmac.compare_digest(
        configured.encode("utf-8"), provided.encode("utf-8")
    ):
        raise ApiError(
            401,
            "ENROLLMENT_UNAUTHORIZED",
            "The enrollment token is not valid",
        )

    now = datetime.now(UTC)
    agent_token = secrets.token_urlsafe(32)
    display_id = await _unique_display_id(session, body.hostname)
    node = Node(
        node_id=uuid.uuid4(),
        display_id=display_id,
        hostname=body.hostname,
        identity={TOKEN_HASH_KEY: token_digest(agent_token)},
        agent_version=body.agent_version or "unknown",
        os={},
        runtime={},
        communication_state="OFFLINE",
        heartbeat_interval_seconds=30,
        status="ACTIVE",
        interactive_session={},
        work_dir={},
        spool={},
        capabilities=[],
        endpoint_ids=[],
        updated_at=now,
    )
    session.add(node)
    await session.flush()
    await audit.append_event(
        session,
        actor_role="SYSTEM",
        actor_id=None,
        action="NODE_ENROLLED",
        object_type="node",
        object_id=node.display_id,
        before=None,
        after={
            "node_id": str(node.node_id),
            "display_id": node.display_id,
            "hostname": node.hostname,
            "agent_version": node.agent_version,
            "status": node.status,
            "communication_state": node.communication_state,
        },
        reason=None,
        correlation_id=correlation_id(request),
        path=request.url.path,
    )
    await session.commit()
    return {
        "node_id": str(node.node_id),
        "display_id": node.display_id,
        "agent_token": agent_token,
    }
