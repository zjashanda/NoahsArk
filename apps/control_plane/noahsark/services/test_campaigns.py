"""Deterministic test campaigns: create, enqueue ``test.run``, read projection.

A campaign is *not* a Task.  It never creates a supervisor session; it only
enqueues one allow-listed ``NodeCommand`` and later exposes the campaign row.
A campaign may optionally reference an owning ``Task`` (``task_id``) so the
task detail page can list it; the link is validated when supplied and never
required.  Result parsing lives in
:mod:`noahsark.services.test_campaign_results`.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import ApiError, not_found
from ..models.command import NodeCommand
from ..models.device import Node
from ..models.task import Task
from ..models.test_campaign import (
    FINAL_CAMPAIGN_STATUSES,
    TestCampaign,
)
from . import audit, node_commands, resource_leases

CAMPAIGN_TOOL_ID = "test.run"
TEST_SCENARIOS = frozenset({"wake-recognition"})
MIN_ROUNDS = 1
MAX_ROUNDS = 1000
BENCH_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.json")

# A campaign in one of these states may still hold the node.  DELETE must refuse
# instead of silently canceling it: the caller has to STOP first so the node-side
# runner and the platform lease are torn down through the audited stop path.
ACTIVE_CAMPAIGN_STATUSES = frozenset({"QUEUED", "RUNNING"})


def _invalid(field: str, message: str, **details: object) -> ApiError:
    return ApiError(
        422,
        "INVALID_CAMPAIGN_REQUEST",
        message,
        details={"field": field, **details},
    )


def _normalize_scenario(scenario: str) -> str:
    normalized = scenario.strip()
    if normalized not in TEST_SCENARIOS:
        raise _invalid(
            "scenario",
            f"scenario {scenario!r} is not supported",
            allowed=sorted(TEST_SCENARIOS),
        )
    return normalized


def _normalize_rounds(rounds: int) -> int:
    if isinstance(rounds, bool) or not isinstance(rounds, int):
        raise _invalid("rounds", "rounds must be an integer")
    if rounds < MIN_ROUNDS or rounds > MAX_ROUNDS:
        raise _invalid(
            "rounds",
            f"rounds must be between {MIN_ROUNDS} and {MAX_ROUNDS}",
            min=MIN_ROUNDS,
            max=MAX_ROUNDS,
        )
    return rounds


def _normalize_bench(bench: str) -> str:
    normalized = bench.strip()
    if not BENCH_PATTERN.fullmatch(normalized):
        raise _invalid("bench", "bench must be a bare JSON file name such as tcl003.json")
    return normalized


def _normalize_command_set(command_set: str | None) -> str:
    if command_set is None:
        return node_commands.TEST_RUN_DEFAULT_COMMAND_SET
    normalized = command_set.strip()
    if normalized not in node_commands.TEST_RUN_COMMAND_SETS:
        raise _invalid(
            "command_set",
            f"command_set {command_set!r} is not supported",
            allowed=sorted(node_commands.TEST_RUN_COMMAND_SETS),
        )
    return normalized


def _resolve_node_id(raw_node_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw_node_id)
    except ValueError as exc:
        raise not_found("node", raw_node_id) from exc


def _resolve_task_id(raw_task_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw_task_id)
    except ValueError as exc:
        raise not_found("task", raw_task_id) from exc


async def _validate_task_exists(
    session: AsyncSession, raw_task_id: str | None
) -> uuid.UUID | None:
    """Parse an optional ``task_id`` and fail 404 when the Task is missing.

    The campaign link is optional, so ``None`` stays ``None``.  A malformed or
    unknown id is a client error, not a silently dropped association.
    """

    if raw_task_id is None:
        return None
    task_uuid = _resolve_task_id(raw_task_id)
    if await session.get(Task, task_uuid) is None:
        raise not_found("task", raw_task_id)
    return task_uuid


async def create_campaign(
    session: AsyncSession,
    *,
    node_id: str,
    scenario: str,
    rounds: int,
    bench: str,
    title: str | None,
    actor_role: str,
    actor_id: uuid.UUID | None,
    correlation_id: str | None,
    path: str,
    command_set: str | None = None,
    preempt: bool = False,
    task_id: str | None = None,
) -> tuple[TestCampaign, NodeCommand]:
    """Validate the node (and optional Task), acquire resources, enqueue ``test.run``.

    The lease and the campaign/command rows commit together.  A busy node fails
    with 409 ``DEVICE_BUSY`` *before* anything is written, unless ``preempt`` is
    set: then the active owner campaign is stopped, its lease released, and the
    new campaign takes the resources.

    ``task_id`` is an optional owning Task.  It is validated before any lease is
    taken so a bad link never leaves a half-created campaign behind.
    """

    node_uuid = _resolve_node_id(node_id)
    node = await session.get(Node, node_uuid)
    if node is None:
        raise not_found("node", node_id)
    if node.communication_state != "ONLINE":
        raise ApiError(
            409,
            "NODE_NOT_ONLINE",
            f"node {node.display_id!r} is not online; a campaign cannot be queued",
            details={
                "node_id": str(node.node_id),
                "communication_state": node.communication_state,
            },
        )

    task_uuid = await _validate_task_exists(session, task_id)

    scenario = _normalize_scenario(scenario)
    rounds = _normalize_rounds(rounds)
    bench = _normalize_bench(bench)
    command_set = _normalize_command_set(command_set)
    request_args: dict[str, object] = {
        "scenario": scenario,
        "rounds": rounds,
        "bench": bench,
    }
    if command_set != node_commands.TEST_RUN_DEFAULT_COMMAND_SET:
        # Omit the default so an older node agent that predates ``command_set``
        # sees exactly the historical three-key request.
        request_args["command_set"] = command_set
    # Single source of truth for "which arguments may reach test.run".
    args = node_commands.validate_tool_request(CAMPAIGN_TOOL_ID, request_args)

    now = datetime.now(UTC)
    resource_keys = await resource_leases.resource_keys_for_node(session, node)
    # Serialize creators per resource key, then reclaim any TTL-expired holder.
    await resource_leases.lock_resource_keys(session, resource_keys)
    await resource_leases.reclaim_expired(session, now=now)
    conflicts = await resource_leases.active_leases(session, resource_keys)
    if conflicts:
        if not preempt:
            raise resource_leases.device_busy_error(
                await resource_leases.busy_payload(session, conflicts)
            )
        await _stop_conflicting_owners(
            session,
            conflicts,
            now=now,
            actor_role=actor_role,
            actor_id=actor_id,
            correlation_id=correlation_id,
            path=path,
        )
        conflicts = await resource_leases.active_leases(session, resource_keys)
        if conflicts:
            raise resource_leases.device_busy_error(
                await resource_leases.busy_payload(session, conflicts)
            )

    campaign = TestCampaign(
        campaign_id=uuid.uuid4(),
        node_id=node.node_id,
        task_id=task_uuid,
        scenario=scenario,
        rounds=rounds,
        bench=bench,
        title=(title.strip()[:200] or None) if title else None,
        status="RUNNING",
        command_id=None,
        summary=None,
        rounds_data=None,
        error_code=None,
        created_at=now,
        started_at=now,
        finished_at=None,
    )
    session.add(campaign)
    await session.flush()

    try:
        leases = await resource_leases.insert_leases(
            session,
            resource_keys=resource_keys,
            owner_type=resource_leases.OWNER_TEST_CAMPAIGN,
            owner_id=campaign.campaign_id,
            now=now,
        )
    except IntegrityError as exc:
        # The advisory lock should make this unreachable, but the partial unique
        # index is the authority.  Roll back so the caller can retry cleanly.
        await session.rollback()
        raise resource_leases.device_busy_error(
            {
                "busy_resources": resource_keys,
                "owners": [],
                "expires_at": None,
            }
        ) from exc

    command = NodeCommand(
        command_id=uuid.uuid4(),
        node_id=node.node_id,
        tool_id=CAMPAIGN_TOOL_ID,
        args_json=args,
        campaign_id=campaign.campaign_id,
        status="QUEUED",
        truncated=False,
        created_by=actor_role,
        created_at=now,
    )
    session.add(command)
    await session.flush()
    campaign.command_id = command.command_id
    await session.flush()

    await audit.append_event(
        session,
        actor_role=actor_role,
        actor_id=actor_id,
        action="TEST_CAMPAIGN_CREATED",
        object_type="test_campaign",
        object_id=str(campaign.campaign_id),
        before=None,
        after={
            "campaign_id": str(campaign.campaign_id),
            "command_id": str(command.command_id),
            "node_id": str(node.node_id),
            "task_id": str(task_uuid) if task_uuid is not None else None,
            "scenario": scenario,
            "rounds": rounds,
            "bench": bench,
            "command_set": command_set,
            "title": campaign.title,
            "status": campaign.status,
            "resource_keys": resource_keys,
            "lease_ids": [str(lease.lease_id) for lease in leases],
        },
        reason=None,
        correlation_id=correlation_id,
        path=path,
    )
    await session.commit()
    return campaign, command


async def _stop_campaign_row(
    session: AsyncSession,
    campaign: TestCampaign,
    *,
    now: datetime,
    reason: str,
    audit_action: str,
    actor_role: str,
    actor_id: uuid.UUID | None,
    correlation_id: str | None,
    path: str,
) -> tuple[NodeCommand | None, bool]:
    """Stop one campaign, release its leases and record the audit event.

    ``QUEUED`` commands are cancelled before the node can claim them.  A command
    the node already claimed (``SENT``/``RUNNING``) gets ``cancel_requested_at``;
    the node agent stops the local runner on its next poll.  This function does
    not commit: callers own the surrounding transaction.
    """

    previous_status = campaign.status
    command = (
        await session.get(NodeCommand, campaign.command_id)
        if campaign.command_id is not None
        else None
    )
    runner_active = False
    campaign.status = "STOPPED"
    campaign.error_code = "STOPPED_BY_USER"
    campaign.finished_at = now
    if command is not None:
        if command.status == "QUEUED":
            command.status = "FAILED"
            command.error_code = "STOPPED_BY_USER"
            command.finished_at = now
        elif command.status in {"SENT", "RUNNING"}:
            command.cancel_requested_at = now
            runner_active = True
    await resource_leases.release_owner(
        session,
        owner_type=resource_leases.OWNER_TEST_CAMPAIGN,
        owner_id=campaign.campaign_id,
        reason=reason,
        now=now,
    )
    await audit.append_event(
        session,
        actor_role=actor_role,
        actor_id=actor_id,
        action=audit_action,
        object_type="test_campaign",
        object_id=str(campaign.campaign_id),
        before={"status": previous_status},
        after={
            "campaign_id": str(campaign.campaign_id),
            "command_id": str(command.command_id) if command is not None else None,
            "status": campaign.status,
            "error_code": campaign.error_code,
            "runner_active": runner_active,
            "cancel_requested_at": (
                now.isoformat() if runner_active else None
            ),
            "release_reason": reason,
        },
        reason=reason,
        correlation_id=correlation_id,
        path=path,
    )
    return command, runner_active


async def _stop_conflicting_owners(
    session: AsyncSession,
    leases: list[resource_leases.ResourceLease],
    *,
    now: datetime,
    actor_role: str,
    actor_id: uuid.UUID | None,
    correlation_id: str | None,
    path: str,
) -> None:
    """Preempt path: stop every distinct active campaign owner before re-locking."""

    stopped: set[uuid.UUID] = set()
    for lease in leases:
        if lease.owner_type != resource_leases.OWNER_TEST_CAMPAIGN:
            await resource_leases.release_owner(
                session,
                owner_type=lease.owner_type,
                owner_id=lease.owner_id,
                reason=resource_leases.RELEASE_PREEMPTED,
                now=now,
            )
            continue
        if lease.owner_id in stopped:
            continue
        stopped.add(lease.owner_id)
        campaign = await session.get(TestCampaign, lease.owner_id)
        if campaign is None or campaign.status in FINAL_CAMPAIGN_STATUSES:
            await resource_leases.release_owner(
                session,
                owner_type=lease.owner_type,
                owner_id=lease.owner_id,
                reason=resource_leases.RELEASE_PREEMPTED,
                now=now,
            )
            continue
        await _stop_campaign_row(
            session,
            campaign,
            now=now,
            reason=resource_leases.RELEASE_PREEMPTED,
            audit_action="TEST_CAMPAIGN_PREEMPTED",
            actor_role=actor_role,
            actor_id=actor_id,
            correlation_id=correlation_id,
            path=path,
        )


async def stop_campaign(
    session: AsyncSession,
    *,
    campaign_id: str,
    actor_role: str,
    actor_id: uuid.UUID | None,
    correlation_id: str | None,
    path: str,
) -> tuple[TestCampaign, NodeCommand | None, bool]:
    """User STOP: mark ``STOPPED``, release leases, request a runner stop.

    Idempotent for an already stopped campaign.  A campaign that already reached
    a different terminal status cannot be rewritten into ``STOPPED``.
    """

    campaign, command = await get_campaign(session, campaign_id)
    if campaign.status == "STOPPED":
        return campaign, command, False
    if campaign.status in FINAL_CAMPAIGN_STATUSES:
        raise ApiError(
            409,
            "INVALID_STATE_TRANSITION",
            f"campaign {campaign.campaign_id} is already {campaign.status}",
            details={"status": campaign.status},
        )
    now = datetime.now(UTC)
    command, runner_active = await _stop_campaign_row(
        session,
        campaign,
        now=now,
        reason=resource_leases.RELEASE_STOPPED,
        audit_action="TEST_CAMPAIGN_STOPPED",
        actor_role=actor_role,
        actor_id=actor_id,
        correlation_id=correlation_id,
        path=path,
    )
    await session.commit()
    return campaign, command, runner_active


async def delete_campaign(
    session: AsyncSession,
    *,
    campaign_id: str,
    actor_role: str,
    actor_id: uuid.UUID | None,
    correlation_id: str | None,
    path: str,
) -> tuple[uuid.UUID, int]:
    """Hard-delete one terminal campaign after releasing its leases.

    ``QUEUED``/``RUNNING`` campaigns are refused with ``409 CAMPAIGN_ACTIVE``:
    deleting them would orphan a live runner, so the caller must use the audited
    STOP endpoint first.  Terminal campaigns release every owned resource lease,
    append ``TEST_CAMPAIGN_DELETED`` and then drop the campaign row.

    The linked ``node_commands`` row is deliberately retained: the FK is
    ``ON DELETE SET NULL``, so the command history survives the campaign with a
    null ``campaign_id``.  This function commits the surrounding transaction.
    """

    campaign, command = await get_campaign(session, campaign_id)
    if campaign.status in ACTIVE_CAMPAIGN_STATUSES:
        raise ApiError(
            409,
            "CAMPAIGN_ACTIVE",
            (
                f"campaign {campaign.campaign_id} is {campaign.status}; "
                "stop it before deleting"
            ),
            details={
                "status": campaign.status,
                "campaign_id": str(campaign.campaign_id),
                "hint": (
                    "Call POST /api/v1/test-campaigns/"
                    f"{campaign.campaign_id}/stop first, then delete."
                ),
                "stop_endpoint": (
                    f"/api/v1/test-campaigns/{campaign.campaign_id}/stop"
                ),
            },
        )

    now = datetime.now(UTC)
    released = await resource_leases.release_owner(
        session,
        owner_type=resource_leases.OWNER_TEST_CAMPAIGN,
        owner_id=campaign.campaign_id,
        reason=resource_leases.RELEASE_DELETED,
        now=now,
    )
    deleted_campaign_id = campaign.campaign_id
    command_id = campaign.command_id
    await audit.append_event(
        session,
        actor_role=actor_role,
        actor_id=actor_id,
        action="TEST_CAMPAIGN_DELETED",
        object_type="test_campaign",
        object_id=str(campaign.campaign_id),
        before={
            "campaign_id": str(campaign.campaign_id),
            "node_id": str(campaign.node_id),
            "status": campaign.status,
            "command_id": str(command_id) if command_id is not None else None,
            "error_code": campaign.error_code,
            "finished_at": (
                campaign.finished_at.isoformat()
                if campaign.finished_at is not None
                else None
            ),
        },
        after={
            "campaign_id": str(campaign.campaign_id),
            "deleted": True,
            "released_lease_count": released,
            "command_retained": command is not None,
        },
        reason="USER_REQUESTED",
        correlation_id=correlation_id,
        path=path,
    )
    await session.delete(campaign)
    await session.commit()
    return deleted_campaign_id, released


async def load_task_campaigns(
    session: AsyncSession, task_id: uuid.UUID
) -> list[TestCampaign]:
    """Load every campaign linked to ``task_id`` without mutating anything.

    The caller uses this before provider work so an active campaign can abort
    task deletion with zero external side effects.
    """

    rows = await session.execute(
        select(TestCampaign).where(TestCampaign.task_id == task_id)
    )
    return list(rows.scalars().all())


async def validate_task_campaigns_deletable(
    task_id: uuid.UUID, campaigns: list[TestCampaign]
) -> None:
    """Refuse task deletion while any linked campaign is ``QUEUED``/``RUNNING``.

    A live campaign still owns the node and may hold a runner; the caller must
    STOP it through the audited endpoint first.  Nothing is mutated here, so the
    check is safe before the provider session is touched.
    """

    active = [row for row in campaigns if row.status in ACTIVE_CAMPAIGN_STATUSES]
    if not active:
        return
    details = [
        {
            "campaign_id": str(row.campaign_id),
            "status": row.status,
            "stop_endpoint": f"/api/v1/test-campaigns/{row.campaign_id}/stop",
        }
        for row in active
    ]
    raise ApiError(
        409,
        "CAMPAIGN_ACTIVE",
        (
            f"task {task_id} has {len(active)} active test campaign(s); "
            "stop them before deleting the task"
        ),
        details={
            "task_id": str(task_id),
            "campaigns": details,
            "hint": "Stop every active test campaign before deleting the task.",
        },
    )


async def delete_task_campaigns(
    session: AsyncSession,
    campaigns: list[TestCampaign],
    *,
    actor_role: str,
    actor_id: uuid.UUID | None,
    correlation_id: str | None,
    path: str,
) -> tuple[list[str], int]:
    """Hard-delete terminal campaigns that belong to a task; never commits.

    Runs inside the caller's task-deletion transaction.  Every campaign releases
    its resource leases and appends ``TEST_CAMPAIGN_DELETED`` (reason
    ``TASK_DELETED``) before the rows are removed.  ``node_commands`` rows are
    intentionally retained: their FK is ``ON DELETE SET NULL``.
    """

    if not campaigns:
        return [], 0

    now = datetime.now(UTC)
    campaign_ids: list[str] = []
    released_total = 0
    for campaign in campaigns:
        released = await resource_leases.release_owner(
            session,
            owner_type=resource_leases.OWNER_TEST_CAMPAIGN,
            owner_id=campaign.campaign_id,
            reason=resource_leases.RELEASE_DELETED,
            now=now,
        )
        released_total += released
        await audit.append_event(
            session,
            actor_role=actor_role,
            actor_id=actor_id,
            action="TEST_CAMPAIGN_DELETED",
            object_type="test_campaign",
            object_id=str(campaign.campaign_id),
            before={
                "campaign_id": str(campaign.campaign_id),
                "node_id": str(campaign.node_id),
                "task_id": str(campaign.task_id) if campaign.task_id is not None else None,
                "status": campaign.status,
                "command_id": (
                    str(campaign.command_id)
                    if campaign.command_id is not None
                    else None
                ),
                "error_code": campaign.error_code,
                "finished_at": (
                    campaign.finished_at.isoformat()
                    if campaign.finished_at is not None
                    else None
                ),
            },
            after={
                "campaign_id": str(campaign.campaign_id),
                "deleted": True,
                "released_lease_count": released,
                "command_retained": campaign.command_id is not None,
            },
            reason="TASK_DELETED",
            correlation_id=correlation_id,
            path=path,
        )
        campaign_ids.append(str(campaign.campaign_id))

    await session.execute(
        delete(TestCampaign).where(
            TestCampaign.campaign_id.in_(
                [campaign.campaign_id for campaign in campaigns]
            )
        )
    )
    return campaign_ids, released_total


async def get_campaign(
    session: AsyncSession, campaign_id: str
) -> tuple[TestCampaign, NodeCommand | None]:
    try:
        parsed_id = uuid.UUID(campaign_id)
    except ValueError as exc:
        raise not_found("test_campaign", campaign_id) from exc
    campaign = await session.get(TestCampaign, parsed_id)
    if campaign is None:
        raise not_found("test_campaign", campaign_id)
    command = (
        await session.get(NodeCommand, campaign.command_id)
        if campaign.command_id is not None
        else None
    )
    return campaign, command


def _facts(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("facts_json")
    if value is None:
        value = row.get("facts")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return {}
    return dict(value) if isinstance(value, dict) else {}


def _first(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _round_rows(
    raw_rows: list[Any] | None, artifacts: dict[str, Any]
) -> list[dict[str, Any]]:
    """Project stored node rows into the display contract.

    ``results.csv`` rows carry ``facts_json``; summary-derived rows carry only a
    status.  The projection keeps the five fields the platform needs (round,
    status, wake/keyword, command/intent, evidence) and tags derived rows so a
    consumer never mistakes an aggregate for per-case evidence.
    """

    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_rows or []):
        if not isinstance(raw, dict):
            continue
        facts = _facts(raw)
        derived = bool(raw.get("derived"))
        source = raw.get("source") or ("summary_final.json" if derived else "results.csv")
        evidence = _first(
            raw.get("evidence"),
            raw.get("evidence_refs"),
            facts.get("evidence"),
            facts.get("evidence_refs"),
        )
        if evidence is None and derived and artifacts.get("summary_path"):
            evidence = [artifacts["summary_path"]]
        rows.append(
            {
                "round": _first(raw.get("round"), raw.get("round_number"), index + 1),
                "status": _first(
                    raw.get("status"),
                    raw.get("final_status"),
                    raw.get("business_verdict"),
                    raw.get("result"),
                ),
                "wake": _first(
                    raw.get("wake"),
                    raw.get("keyword"),
                    facts.get("keyword"),
                    facts.get("wake"),
                ),
                "command": _first(
                    raw.get("command"),
                    raw.get("intent"),
                    facts.get("intent"),
                    facts.get("command"),
                ),
                "intent": _first(raw.get("intent"), facts.get("intent")),
                "evidence": evidence,
                "case_id": raw.get("case_id"),
                "source": source,
                "derived": derived,
            }
        )
    return rows


def empty_artifact_collection() -> dict[str, Any]:
    """Projection shape when no platform-stored artifact exists.

    ``artifacts`` is a downloadable collection, never the node-reported
    ``result_dir``/``summary_path``/``rounds_path`` strings: a raw node path must
    not reach an API consumer.
    """

    return {"files": [], "count": 0, "total_bytes": 0, "all_downloadable": True}


def campaign_view(
    campaign: TestCampaign,
    command: NodeCommand | None,
    artifacts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read projection shared with the API layer (summary/rounds already parsed).

    ``artifacts`` is the platform artifact collection resolved from
    ``test_campaign_artifacts``.  The node payload's path dictionary is kept
    private for round evidence derivation and is never serialized.
    """

    payload = campaign.summary or {}
    summary_json = payload.get("summary")
    node_artifacts = payload.get("artifacts")
    if not isinstance(node_artifacts, dict):
        node_artifacts = {}
    stored_rows = campaign.rounds_data or payload.get("rounds") or []
    round_rows = _round_rows(stored_rows, node_artifacts)
    command_args = dict(command.args_json or {}) if command is not None else {}
    return {
        "campaign_id": str(campaign.campaign_id),
        "node_id": str(campaign.node_id),
        "task_id": str(campaign.task_id) if campaign.task_id is not None else None,
        "scenario": campaign.scenario,
        "rounds": campaign.rounds,
        "bench": campaign.bench,
        "command_set": command_args.get("command_set"),
        "title": campaign.title,
        "status": campaign.status,
        "command_id": str(campaign.command_id) if campaign.command_id else None,
        "command_status": command.status if command is not None else None,
        "command": {
            "command_id": str(command.command_id),
            "tool_id": command.tool_id,
            "status": command.status,
            "exit_code": command.exit_code,
            "error_code": command.error_code,
            "truncated": bool(command.truncated),
        }
        if command is not None
        else None,
        "summary": summary_json,
        "summary_json": summary_json,
        # ``rounds`` is the requested round count; ``rounds_data``/``round_rows``
        # carry the parsed per-round rows so the two are never confused.
        "rounds_data": round_rows,
        "round_rows": round_rows,
        "rounds_count": len(round_rows),
        "expected_rounds": campaign.rounds,
        "verdict": payload.get("verdict"),
        "artifacts": (
            artifacts if artifacts is not None else empty_artifact_collection()
        ),
        "notes": payload.get("notes", []),
        "error_code": campaign.error_code,
        "created_at": campaign.created_at,
        "started_at": campaign.started_at,
        "finished_at": campaign.finished_at,
    }
