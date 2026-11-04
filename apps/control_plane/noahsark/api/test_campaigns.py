"""Admin surface for deterministic test campaigns.

``POST /api/v1/test-campaigns`` validates the target node, enqueues exactly one
``test.run`` ``NodeCommand`` and records the campaign.  No Task or OpenCode
session is created: a campaign is a deterministic, platform-owned run.

``GET /api/v1/test-campaigns?task_id=<uuid>`` filters the list to campaigns
owned by one Task so the task detail page can render them inline; omitting the
filter keeps the historical all-campaigns behaviour.  Campaigns created before
the link existed have ``task_id = NULL`` and are unassociated legacy campaigns.

``GET /api/v1/test-campaigns/{campaign_id}`` exposes campaign status, the
underlying command status and the parsed ``summary`` / ``rounds`` once the node
reports back through the existing ``/node/v1/command-results`` handler.

``DELETE /api/v1/test-campaigns/{campaign_id}`` removes a terminal campaign
after releasing its resource leases.  Active campaigns are refused with
``409 CAMPAIGN_ACTIVE`` and must be stopped first.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from ..db import get_session
from ..errors import ApiError
from ..models.command import NodeCommand
from ..models.device import Device, Node
from ..models.task import Task
from ..models.test_campaign import CAMPAIGN_STATUSES, TestCampaign
from ..services import artifact_storage, campaign_artifacts, test_campaigns
from ..services.auth import Principal
from .deps import get_principal, require_admin
from .envelope import correlation_id, success, utc_iso

router = APIRouter(tags=["test-campaigns"], dependencies=[Depends(get_principal)])

Session = Annotated[AsyncSession, Depends(get_session)]
Admin = Annotated[Principal, Depends(require_admin)]


class CampaignCreate(BaseModel):
    node_id: str = Field(min_length=1, max_length=64)
    scenario: str = Field(min_length=1, max_length=80)
    rounds: int = Field(
        strict=True,
        ge=test_campaigns.MIN_ROUNDS,
        le=test_campaigns.MAX_ROUNDS,
    )
    bench: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=200)
    # Optional owning Task.  Only the UUID is accepted here; the service
    # validates that the Task exists and returns 404 NOT_FOUND otherwise.
    task_id: str | None = Field(default=None, max_length=64)
    command_set: str | None = Field(default=None, max_length=16)
    # Default behaviour is fail-fast 409 DEVICE_BUSY.  ``preempt`` explicitly
    # stops the active owner campaign before taking its resources.
    preempt: bool = False


def _iso(value: datetime | None) -> str | None:
    return utc_iso(value) if value is not None else None


def _campaign_projection(
    campaign: TestCampaign,
    command: NodeCommand | None,
    artifacts: dict[str, object] | None = None,
    node: Node | None = None,
    task_context: dict[str, object] | None = None,
    node_devices: list[Device] | None = None,
) -> dict[str, object]:
    view = test_campaigns.campaign_view(
        campaign,
        command,
        artifacts,
        node=node,
        task_context=task_context,
    )
    view["node_devices"] = [
        {
            "device_id": str(device.device_id),
            "display_id": device.display_id,
            "communication_state": device.communication_state,
            "capabilities": list(device.capabilities or []),
        }
        for device in (node_devices or [])
    ]
    for key in ("created_at", "started_at", "finished_at"):
        view[key] = _iso(view[key])  # type: ignore[arg-type]
    return view


async def _nodes_for(
    session: AsyncSession, campaigns: list[TestCampaign]
) -> dict[object, Node]:
    node_ids = {campaign.node_id for campaign in campaigns if campaign.node_id}
    if not node_ids:
        return {}
    result = await session.execute(select(Node).where(Node.node_id.in_(node_ids)))
    return {node.node_id: node for node in result.scalars()}


async def _task_contexts_for(
    session: AsyncSession, campaigns: list[TestCampaign]
) -> dict[object, dict[str, object]]:
    task_ids = {campaign.task_id for campaign in campaigns if campaign.task_id}
    if not task_ids:
        return {}
    result = await session.execute(
        select(Task.task_id, Task.execution_context).where(Task.task_id.in_(task_ids))
    )
    return {
        task_id: dict(execution_context or {})
        for task_id, execution_context in result.all()
    }


async def _node_devices_for(
    session: AsyncSession, campaigns: list[TestCampaign]
) -> dict[object, list[Device]]:
    node_ids = {campaign.node_id for campaign in campaigns if campaign.node_id}
    if not node_ids:
        return {}
    result = await session.execute(
        select(Device)
        .where(Device.node_id.in_(node_ids))
        .order_by(Device.display_id)
    )
    grouped: dict[object, list[Device]] = {}
    for device in result.scalars():
        grouped.setdefault(device.node_id, []).append(device)
    return grouped


async def _artifact_collection(
    session: AsyncSession, campaign_id: uuid.UUID
) -> dict[str, object]:
    grouped = await campaign_artifacts.list_artifacts(session, [campaign_id])
    return campaign_artifacts.artifact_collection(
        grouped.get(campaign_id, []), campaign_id
    )


def _upload_chunks(upload: UploadFile) -> Iterator[bytes]:
    """Read the multipart body without buffering it in memory.

    ``UploadFile.file`` is a spooled temp file; the generator is consumed inside
    the worker thread that runs the blocking storage write.
    """

    while True:
        chunk = upload.file.read(artifact_storage.READ_CHUNK)
        if not chunk:
            break
        yield chunk


@router.post("/test-campaigns", status_code=201)
async def create_campaign(
    request: Request,
    body: CampaignCreate,
    session: Session,
    principal: Admin,
) -> dict:
    campaign, command = await test_campaigns.create_campaign(
        session,
        node_id=body.node_id,
        scenario=body.scenario,
        rounds=body.rounds,
        bench=body.bench,
        title=body.title,
        actor_role=principal.role,
        actor_id=principal.actor_id,
        correlation_id=correlation_id(request),
        path=request.url.path,
        command_set=body.command_set,
        preempt=body.preempt,
        task_id=body.task_id,
    )
    # ``status`` is the command lifecycle the caller just enqueued; the campaign
    # itself is already in flight and is exposed as ``campaign_status``.
    return success(
        request,
        {
            "campaign_id": str(campaign.campaign_id),
            "task_id": (
                str(campaign.task_id) if campaign.task_id is not None else None
            ),
            "command_id": str(command.command_id),
            "status": "QUEUED",
            "campaign_status": campaign.status,
            "node_id": str(campaign.node_id),
            "scenario": campaign.scenario,
            "rounds": campaign.rounds,
            "bench": campaign.bench,
            "command_set": (command.args_json or {}).get("command_set"),
            "title": campaign.title,
            "created_at": _iso(campaign.created_at),
            "started_at": _iso(campaign.started_at),
        },
    )


async def _commands_for(
    session: AsyncSession, campaigns: list[TestCampaign]
) -> dict[object, NodeCommand]:
    command_ids = [campaign.command_id for campaign in campaigns if campaign.command_id]
    if not command_ids:
        return {}
    result = await session.execute(
        select(NodeCommand).where(NodeCommand.command_id.in_(command_ids))
    )
    return {command.command_id: command for command in result.scalars()}


@router.get("/test-campaigns")
async def list_campaigns(
    request: Request,
    session: Session,
    principal: Admin,
    status: str | None = Query(default=None),
    node_id: str | None = Query(default=None),
    task_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """Paginated campaign list, newest first, with optional status/node/task filters.

    ``task_id`` narrows the list to the owning Task's campaigns.  Omitting it
    returns every campaign, including unassociated legacy rows with
    ``task_id = NULL``.
    """

    if status is not None and status not in CAMPAIGN_STATUSES:
        raise ApiError(
            422,
            "INVALID_CAMPAIGN_STATUS",
            f"status {status!r} is not a campaign status",
            details={"allowed_statuses": list(CAMPAIGN_STATUSES)},
        )
    filters = []
    if status is not None:
        filters.append(TestCampaign.status == status)
    if node_id is not None:
        try:
            filters.append(TestCampaign.node_id == uuid.UUID(node_id))
        except ValueError as exc:
            raise ApiError(
                422,
                "INVALID_NODE_ID",
                f"node_id {node_id!r} is not a UUID",
            ) from exc
    if task_id is not None:
        try:
            filters.append(TestCampaign.task_id == uuid.UUID(task_id))
        except ValueError as exc:
            raise ApiError(
                422,
                "INVALID_TASK_ID",
                f"task_id {task_id!r} is not a UUID",
            ) from exc

    total = (
        await session.execute(
            select(func.count()).select_from(TestCampaign).where(*filters)
        )
    ).scalar_one()
    campaigns = list(
        (
            await session.execute(
                select(TestCampaign)
                .where(*filters)
                .order_by(TestCampaign.created_at.desc(), TestCampaign.campaign_id.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    commands = await _commands_for(session, campaigns)
    nodes = await _nodes_for(session, campaigns)
    task_contexts = await _task_contexts_for(session, campaigns)
    node_devices = await _node_devices_for(session, campaigns)
    artifacts = await campaign_artifacts.list_artifacts(
        session, [campaign.campaign_id for campaign in campaigns]
    )
    return success(
        request,
        {
            "items": [
                _campaign_projection(
                    campaign,
                    commands.get(campaign.command_id),
                    campaign_artifacts.artifact_collection(
                        artifacts.get(campaign.campaign_id, []),
                        campaign.campaign_id,
                    ),
                    nodes.get(campaign.node_id),
                    task_contexts.get(campaign.task_id),
                    node_devices.get(campaign.node_id),
                )
                for campaign in campaigns
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    )


@router.get("/test-campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    request: Request,
    session: Session,
    principal: Admin,
) -> dict:
    campaign, command = await test_campaigns.get_campaign(session, campaign_id)
    artifacts = await _artifact_collection(session, campaign.campaign_id)
    nodes = await _nodes_for(session, [campaign])
    task_contexts = await _task_contexts_for(session, [campaign])
    node_devices = await _node_devices_for(session, [campaign])
    return success(
        request,
        _campaign_projection(
            campaign,
            command,
            artifacts,
            nodes.get(campaign.node_id),
            task_contexts.get(campaign.task_id),
            node_devices.get(campaign.node_id),
        ),
    )


@router.post("/test-campaigns/{campaign_id}/artifacts", status_code=201)
async def upload_campaign_artifact(
    campaign_id: str,
    request: Request,
    session: Session,
    principal: Admin,
    file: Annotated[UploadFile, File()],
    name: Annotated[str | None, Form()] = None,
) -> dict:
    """Store one evidence file and record its immutable metadata.

    ``name`` is a display label, not a path: the storage service sanitizes it to
    a single segment and derives the on-disk key from the campaign id plus the
    SHA-256 it recomputes from the received bytes.  Re-uploading the same bytes
    under the same name is idempotent; different bytes are rejected as
    ``409 ARTIFACT_IMMUTABLE``.
    """

    campaign, _ = await test_campaigns.get_campaign(session, campaign_id)
    storage = artifact_storage.default_storage()
    display_name = (name or "").strip() or (file.filename or artifact_storage.DEFAULT_NAME)
    stored = await run_in_threadpool(
        storage.write,
        _upload_chunks(file),
        campaign_id=campaign.campaign_id,
        name=display_name,
    )
    row, duplicate = await campaign_artifacts.record_artifact(
        session,
        campaign_id=campaign.campaign_id,
        command_id=campaign.command_id,
        stored=stored,
    )
    await session.commit()
    view = campaign_artifacts.artifact_view(row, campaign.campaign_id)
    view["duplicate"] = duplicate
    view["max_bytes"] = storage.max_bytes
    return success(request, view)


@router.get("/test-campaigns/{campaign_id}/artifacts/{artifact_name}")
async def download_campaign_artifact(
    campaign_id: str,
    artifact_name: str,
    session: Session,
    principal: Admin,
) -> StreamingResponse:
    """Stream one stored artifact after re-verifying size and SHA-256.

    The URL segment is resolved through the artifact row, never used as a
    filesystem path.  ``campaign_artifacts.get_artifact`` rejects any name that
    is not already a sanitized single segment, so ``../`` traversal cannot reach
    the storage root.
    """

    campaign, _ = await test_campaigns.get_campaign(session, campaign_id)
    row = await campaign_artifacts.get_artifact(
        session, campaign.campaign_id, artifact_name
    )
    storage = artifact_storage.default_storage()
    path = await run_in_threadpool(
        storage.verify,
        row.storage_key,
        digest=row.digest,
        size_bytes=row.size_bytes,
    )
    filename = row.name.replace('"', "_")
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Length": str(row.size_bytes),
        "ETag": f'"{row.digest}"',
        "X-Artifact-Digest": row.digest,
    }
    return StreamingResponse(
        artifact_storage.iter_file(path),
        media_type=row.media_type,
        headers=headers,
    )


@router.post("/test-campaigns/{campaign_id}/stop")
async def stop_campaign(
    campaign_id: str,
    request: Request,
    session: Session,
    principal: Admin,
) -> dict:
    """Stop a campaign and release its hardware leases.

    A ``QUEUED`` command is cancelled before the node sees it.  A command the
    node already claimed gets ``cancel_requested_at``; the node agent stops the
    local runner on its next poll (the outbound-only protocol has no inbound
    kill channel).  The response reports ``runner_active`` so the caller knows
    whether it must wait for the node-side stop to take effect.
    """

    campaign, command, runner_active = await test_campaigns.stop_campaign(
        session,
        campaign_id=campaign_id,
        actor_role=principal.role,
        actor_id=principal.actor_id,
        correlation_id=correlation_id(request),
        path=request.url.path,
    )
    artifacts = await _artifact_collection(session, campaign.campaign_id)
    nodes = await _nodes_for(session, [campaign])
    task_contexts = await _task_contexts_for(session, [campaign])
    node_devices = await _node_devices_for(session, [campaign])
    projection = _campaign_projection(
        campaign,
        command,
        artifacts,
        nodes.get(campaign.node_id),
        task_contexts.get(campaign.task_id),
        node_devices.get(campaign.node_id),
    )
    projection["runner_active"] = runner_active
    return success(request, projection)


@router.delete("/test-campaigns/{campaign_id}", status_code=204)
async def delete_campaign(
    campaign_id: str,
    request: Request,
    session: Session,
    principal: Admin,
) -> Response:
    """Hard-delete a terminal campaign and release its resource leases.

    ``QUEUED``/``RUNNING`` campaigns return ``409 CAMPAIGN_ACTIVE`` with the
    current ``status`` and the stop endpoint to call first; the running node is
    never killed implicitly.  The linked command row is retained for audit.
    """

    await test_campaigns.delete_campaign(
        session,
        campaign_id=campaign_id,
        actor_role=principal.role,
        actor_id=principal.actor_id,
        correlation_id=correlation_id(request),
        path=request.url.path,
    )
    return Response(status_code=204)
