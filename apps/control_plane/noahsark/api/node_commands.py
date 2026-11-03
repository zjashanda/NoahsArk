"""Admin command surface for the node tool channel.

Only ADMIN can enqueue a tool invocation or read its output.  The node-facing
half of the channel lives in ``node_gateway`` (poll claim + result delivery).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..errors import not_found
from ..models.command import NodeCommand
from ..models.device import Node
from ..services import audit, node_commands
from ..services.auth import Principal
from .deps import get_principal, require_admin
from .envelope import correlation_id, success, utc_iso

router = APIRouter(tags=["node-commands"], dependencies=[Depends(get_principal)])

Session = Annotated[AsyncSession, Depends(get_session)]
Admin = Annotated[Principal, Depends(require_admin)]


class CommandEnqueue(BaseModel):
    tool_id: str = Field(min_length=1, max_length=80)
    args: dict[str, object] = Field(default_factory=dict)


class CommandResultSubmit(BaseModel):
    """Admin-side mirror of the node result body.

    Used by ``POST /nodes/{node_id}/commands/{command_id}/result`` for manual
    verification and backfill; the node itself posts the same shape to
    ``/node/v1/command-results`` with its bearer token.
    """

    status: Literal["RUNNING", "SUCCEEDED", "FAILED", "TIMEOUT"]
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    truncated: bool = False
    error_code: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    summary: dict[str, object] | str | None = None
    rounds: list[object] | None = None
    rounds_rows: list[object] | None = None
    result_dir: str | None = None
    summary_path: str | None = None
    rounds_path: str | None = None


def _resolve_node_id(node_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(node_id)
    except ValueError as exc:
        raise not_found("node", node_id) from exc


def command_projection(command: NodeCommand) -> dict[str, object]:
    stdout, stdout_truncated = node_commands.sanitize_output(command.stdout)
    stderr, stderr_truncated = node_commands.sanitize_output(command.stderr)
    return {
        "command_id": str(command.command_id),
        "node_id": str(command.node_id),
        "campaign_id": str(command.campaign_id) if command.campaign_id else None,
        "tool_id": command.tool_id,
        "args": dict(command.args_json or {}),
        "status": command.status,
        "exit_code": command.exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "truncated": bool(
            command.truncated or stdout_truncated or stderr_truncated
        ),
        "error_code": command.error_code,
        "cancel_requested_at": (
            utc_iso(command.cancel_requested_at)
            if command.cancel_requested_at
            else None
        ),
        "created_by": command.created_by,
        "created_at": utc_iso(command.created_at),
        "started_at": utc_iso(command.started_at) if command.started_at else None,
        "finished_at": utc_iso(command.finished_at) if command.finished_at else None,
    }


@router.post("/nodes/{node_id}/commands")
async def enqueue_command(
    node_id: str,
    request: Request,
    body: CommandEnqueue,
    session: Session,
    principal: Admin,
) -> dict:
    parsed_node_id = _resolve_node_id(node_id)
    node = await session.get(Node, parsed_node_id)
    if node is None:
        raise not_found("node", node_id)
    args = node_commands.validate_tool_request(body.tool_id, body.args)

    command = NodeCommand(
        command_id=uuid.uuid4(),
        node_id=node.node_id,
        tool_id=body.tool_id,
        args_json=args,
        status="QUEUED",
        truncated=False,
        created_by=principal.actor or principal.role,
    )
    session.add(command)
    await session.flush()
    await audit.append_event(
        session,
        actor_role=principal.role,
        actor_id=principal.actor_id,
        action="NODE_COMMAND_ENQUEUED",
        object_type="node_command",
        object_id=str(command.command_id),
        before=None,
        after={
            "command_id": str(command.command_id),
            "node_id": str(node.node_id),
            "tool_id": command.tool_id,
            "args": args,
            "status": command.status,
        },
        reason=None,
        correlation_id=correlation_id(request),
        path=request.url.path,
    )
    await session.commit()
    return success(
        request,
        {"command_id": str(command.command_id), "status": "QUEUED"},
    )


@router.get("/nodes/{node_id}/commands/{command_id}")
async def get_command(
    node_id: str,
    command_id: str,
    request: Request,
    session: Session,
    principal: Admin,
) -> dict:
    parsed_node_id = _resolve_node_id(node_id)
    try:
        parsed_command_id = uuid.UUID(command_id)
    except ValueError as exc:
        raise node_commands.command_not_found(command_id) from exc
    command = await session.get(NodeCommand, parsed_command_id)
    if command is None or command.node_id != parsed_node_id:
        raise node_commands.command_not_found(command_id)
    return success(request, command_projection(command))


@router.post("/nodes/{node_id}/commands/{command_id}/result")
async def submit_command_result(
    node_id: str,
    command_id: str,
    request: Request,
    body: CommandResultSubmit,
    session: Session,
    principal: Admin,
) -> dict:
    """Record a result through the same path the node gateway uses.

    The command must belong to ``node_id`` and be non-terminal; a campaign linked
    through ``NodeCommand.campaign_id`` is reconciled in the same transaction.
    """

    parsed_node_id = _resolve_node_id(node_id)
    command = await node_commands.record_command_result(
        session,
        node_id=parsed_node_id,
        command_id=command_id,
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
            rounds=body.rounds if body.rounds is not None else body.rounds_rows,
            result_dir=body.result_dir,
            summary_path=body.summary_path,
            rounds_path=body.rounds_path,
        ),
    )
    return success(
        request,
        {
            "command_id": str(command.command_id),
            "status": command.status,
            "campaign_id": str(command.campaign_id) if command.campaign_id else None,
        },
    )
