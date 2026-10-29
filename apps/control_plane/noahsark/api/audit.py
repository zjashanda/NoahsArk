"""Read-only audit, hash-chain and recovery projections.

Audit rows are append-only.  This module never mutates an event, never deletes
one, and sanitizes before/after payloads so credentials, keys, certificates and
tokens can never be exposed through a read.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services import read_models
from .deps import get_principal
from .envelope import success

router = APIRouter(tags=["audit"], dependencies=[Depends(get_principal)])

Session = Annotated[AsyncSession, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=200)]


@router.get("/audit")
async def list_audit(
    request: Request,
    session: Session,
    limit: Limit = 50,
    cursor: str | None = None,
) -> dict:
    data = await read_models.list_audit(session, limit=limit, cursor=cursor)
    return success(request, data)


@router.get("/audit/{event_id}")
async def get_audit_event(
    event_id: str,
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.get_audit_event(session, event_id))


@router.get("/recovery")
async def get_recovery(
    request: Request,
    session: Session,
) -> dict:
    return success(request, await read_models.recovery(session))
