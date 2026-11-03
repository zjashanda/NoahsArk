"""Node Agent gateway.

The Windows/Linux node agent is outbound-only: it calls these routes and never
accepts inbound connections.  Each request carries a per-node bearer token; the
plaintext is never stored, only its SHA-256 digest under
``Node.identity["agent_token_hash"]``.

The gateway also carries the controlled tool channel: poll atomically claims one
QUEUED row from ``node_commands`` and the node posts its result back to
``/command-results``.  Jobs/STOP/lease message handling is unchanged.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header
from pydantic import AliasChoices, BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..errors import ApiError
from ..models.device import Node
from ..services import node_commands

router = APIRouter(prefix="/node/v1", tags=["node-gateway"])

TOKEN_HASH_KEY = "agent_token_hash"

Session = Annotated[AsyncSession, Depends(get_session)]
AuthorizationHeader = Annotated[str | None, Header(alias="Authorization")]


class RegisterRequest(BaseModel):
    node_id: str
    agent_version: str = "unknown"
    protocol_version: str | int | None = None


class HeartbeatRequest(RegisterRequest):
    status: dict = Field(default_factory=dict)


class PollRequest(BaseModel):
    node_id: str
    lease_id: str | None = None
    epoch: int | None = None
    timeout_seconds: int | None = None


class ReceiptRequest(BaseModel):
    node_id: str


class CommandResultRequest(BaseModel):
    node_id: str
    command_id: str
    status: Literal["RUNNING", "SUCCEEDED", "FAILED", "TIMEOUT"]
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    truncated: bool = False
    error_code: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    # ``test.run`` structured detail.  The node agent flattens its ToolResult
    # details into this body; ``usb.scan`` simply omits them.  ``rounds_rows``
    # is accepted as an alias because that is the node-side key name.
    summary: dict[str, object] | str | None = None
    rounds: list[object] | None = Field(
        default=None, validation_alias=AliasChoices("rounds", "rounds_rows")
    )
    result_dir: str | None = Field(default=None, max_length=4096)
    summary_path: str | None = Field(default=None, max_length=4096)
    rounds_path: str | None = Field(default=None, max_length=4096)

    @field_validator("rounds", mode="before")
    @classmethod
    def _legacy_round_count_is_not_a_row(cls, value: object) -> object:
        # Older node agents sent ``rounds_rows`` as an integer count.  A count is
        # not per-round evidence, so drop it instead of rejecting the whole
        # result body (the summary in the same body is still authoritative).
        if value is None or isinstance(value, list):
            return value
        return None


class ReconcileRequest(BaseModel):
    node_id: str
    lease_id: str | None = None
    epoch: int | None = None
    executed_job_ids: list[str] = Field(default_factory=list)


def _now() -> datetime:
    return datetime.now(UTC)


def token_digest(token: str) -> str:
    """Return the stored fingerprint for a node bearer token."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _bearer_token(authorization: str | None) -> str:
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token.strip():
            return token.strip()
    raise ApiError(
        401,
        "NODE_UNAUTHORIZED",
        "A node bearer token is required",
    )


def _node_not_found(node_id: str) -> ApiError:
    return ApiError(
        404,
        "NODE_NOT_FOUND",
        f"node {node_id!r} was not found",
        details={"object_type": "node", "identifier": node_id},
    )


async def _authorize_node(
    session: AsyncSession,
    node_id: str,
    authorization: str | None,
) -> Node:
    """Resolve the node from the body id and verify its bearer token.

    A missing token fails before any lookup so callers cannot probe which
    node ids exist without a credential.
    """

    token = _bearer_token(authorization)
    try:
        node_uuid = uuid.UUID(node_id)
    except ValueError as exc:
        raise _node_not_found(node_id) from exc
    node = await session.get(Node, node_uuid)
    if node is None:
        raise _node_not_found(node_id)
    expected = (node.identity or {}).get(TOKEN_HASH_KEY)
    if not isinstance(expected, str) or not hmac.compare_digest(
        expected, token_digest(token)
    ):
        raise ApiError(
            401,
            "NODE_UNAUTHORIZED",
            "The node bearer token is not valid",
        )
    return node


def _mark_online(node: Node, *, now: datetime, agent_version: str) -> None:
    node.agent_version = agent_version
    node.communication_state = "ONLINE"
    node.last_heartbeat_at = now
    node.status = "ACTIVE"
    node.updated_at = now


@router.post("/register")
async def register(
    body: RegisterRequest,
    session: Session,
    authorization: AuthorizationHeader = None,
) -> dict:
    node = await _authorize_node(session, body.node_id, authorization)
    _mark_online(node, now=_now(), agent_version=body.agent_version)
    await session.commit()
    return {"node_id": str(node.node_id), "registered": True}


@router.post("/heartbeat")
async def heartbeat(
    body: HeartbeatRequest,
    session: Session,
    authorization: AuthorizationHeader = None,
) -> dict:
    node = await _authorize_node(session, body.node_id, authorization)
    now = _now()
    node.agent_version = body.agent_version
    node.communication_state = "ONLINE"
    node.last_heartbeat_at = now
    node.updated_at = now
    await session.commit()
    return {"ok": True}


@router.post("/poll")
async def poll(
    body: PollRequest,
    session: Session,
    authorization: AuthorizationHeader = None,
) -> dict:
    node = await _authorize_node(session, body.node_id, authorization)
    command = await node_commands.claim_next_command(
        session, node_id=node.node_id, now=_now()
    )
    messages: list[dict] = []
    if command is not None:
        messages.append(node_commands.command_message(command))
    # Platform half of a user STOP for a runner the node already claimed.  The
    # older agent ignores ``command_cancel``; the current agent can use it to
    # stop the local subprocess.  Sending it is idempotent.
    for cancelled in await node_commands.pending_command_cancellations(
        session, node_id=node.node_id
    ):
        messages.append(
            {
                "kind": "command_cancel",
                "message_id": f"cancel-{cancelled.command_id}",
                "command_id": str(cancelled.command_id),
                "reason": cancelled.error_code or "STOPPED_BY_USER",
            }
        )
    if not messages:
        return {"messages": []}
    return {"messages": messages}


@router.post("/command-results")
async def command_results(
    body: CommandResultRequest,
    session: Session,
    authorization: AuthorizationHeader = None,
) -> dict:
    node = await _authorize_node(session, body.node_id, authorization)
    await node_commands.record_command_result(
        session,
        node_id=node.node_id,
        command_id=body.command_id,
        result=node_commands.CommandResultInput(
            status=body.status,
            exit_code=body.exit_code,
            stdout=body.stdout,
            stderr=body.stderr,
            truncated=body.truncated,
            error_code=body.error_code,
            started_at=body.started_at,
            finished_at=body.finished_at,
            summary=body.summary,
            rounds=body.rounds,
            result_dir=body.result_dir,
            summary_path=body.summary_path,
            rounds_path=body.rounds_path,
        ),
    )
    return {"ok": True}


@router.post("/receipts")
async def receipts(
    body: ReceiptRequest,
    session: Session,
    authorization: AuthorizationHeader = None,
) -> dict:
    await _authorize_node(session, body.node_id, authorization)
    return {"accepted": True, "duplicate": False}


@router.post("/reconcile")
async def reconcile(
    body: ReconcileRequest,
    session: Session,
    authorization: AuthorizationHeader = None,
) -> dict:
    await _authorize_node(session, body.node_id, authorization)
    return {"ok": True, "messages": []}
