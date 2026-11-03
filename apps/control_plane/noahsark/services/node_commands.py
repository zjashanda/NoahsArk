"""Node command queue rules: tool allow-list, output sanitization, lifecycle.

The platform never forwards a free-form command line.  A tool id must appear in
``TOOL_ARGUMENTS`` and every argument name must be declared for that tool.  The
node receives the allow-listed id plus the validated argument values only.

Output is hostile input: it may contain terminal escapes, NUL bytes or unbounded
text.  ``sanitize_output`` strips non-printing controls and caps the payload in
UTF-8 bytes before it is stored or returned.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import ApiError
from ..models.command import NodeCommand

MAX_OUTPUT_BYTES = 1_000_000
DEFAULT_TIMEOUT_SECONDS = 30

# tool_id -> declared argument names.  ``usb.scan`` is deliberately argument-free:
# the node fixes the executable AND its arguments, so there is nothing to inject.
# ``test.run`` names a scenario file plus a round count; the node still decides
# the executable and rejects anything outside this declared set.
TEST_RUN_TIMEOUT_SECONDS = 28800
TEST_RUN_COMMAND_SETS = frozenset({"single", "full"})
TEST_RUN_DEFAULT_COMMAND_SET = "single"
TOOL_ARGUMENTS: dict[str, frozenset[str]] = {
    "usb.scan": frozenset(),
    "test.run": frozenset(
        {"scenario", "rounds", "bench", "result_root", "command_set"}
    ),
}
TOOL_TIMEOUTS: dict[str, int] = {
    "usb.scan": DEFAULT_TIMEOUT_SECONDS,
    "test.run": TEST_RUN_TIMEOUT_SECONDS,
}

RESULT_STATUSES = frozenset({"RUNNING", "SUCCEEDED", "FAILED", "TIMEOUT"})
TERMINAL_STATUSES = frozenset({"SUCCEEDED", "FAILED", "TIMEOUT"})

_ANSI_ESCAPE = re.compile(
    r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]"
)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass(frozen=True, slots=True)
class CommandResultInput:
    status: str
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    truncated: bool = False
    error_code: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    # Structured ``test.run`` payload.  The node agent flattens its ToolResult
    # details into the command-result body; these fields stay optional so
    # ``usb.scan`` results are unchanged.
    summary: dict[str, object] | str | None = None
    rounds: list[object] | None = None
    result_dir: str | None = None
    summary_path: str | None = None
    rounds_path: str | None = None


def _unknown_tool(tool_id: str) -> ApiError:
    return ApiError(
        422,
        "UNKNOWN_TOOL",
        f"tool {tool_id!r} is not in the platform allow-list",
        details={"tool_id": tool_id, "allowed_tools": sorted(TOOL_ARGUMENTS)},
    )


def validate_tool_request(
    tool_id: str, args: dict[str, object] | None
) -> dict[str, object]:
    """Return the normalized args or raise a typed 422."""

    declared = TOOL_ARGUMENTS.get(tool_id)
    if declared is None:
        raise _unknown_tool(tool_id)
    normalized = dict(args or {})
    unknown = sorted(set(normalized) - declared)
    if unknown:
        raise ApiError(
            422,
            "INVALID_TOOL_ARGS",
            f"tool {tool_id!r} does not accept these arguments",
            details={
                "tool_id": tool_id,
                "unknown_arguments": unknown,
                "allowed_arguments": sorted(declared),
            },
        )
    return normalized


def sanitize_output(value: str | None) -> tuple[str | None, bool]:
    """Strip terminal controls and cap at ``MAX_OUTPUT_BYTES`` UTF-8 bytes."""

    if value is None:
        return None, False
    clean = _CONTROL_CHARS.sub("", _ANSI_ESCAPE.sub("", value))
    encoded = clean.encode("utf-8")
    if len(encoded) <= MAX_OUTPUT_BYTES:
        return clean, False
    return encoded[:MAX_OUTPUT_BYTES].decode("utf-8", errors="ignore"), True


def command_message(command: NodeCommand) -> dict[str, object]:
    return {
        "kind": "command",
        "command_id": str(command.command_id),
        "tool_id": command.tool_id,
        "args": dict(command.args_json or {}),
        "timeout_seconds": TOOL_TIMEOUTS.get(command.tool_id, DEFAULT_TIMEOUT_SECONDS),
        # Platform half of a user STOP for an already-claimed runner.  Older node
        # agents ignore the extra key; a current agent can use it to kill the
        # local process.  The authoritative campaign status is already STOPPED.
        "cancel_requested": command.cancel_requested_at is not None,
    }


async def claim_next_command(
    session: AsyncSession,
    *,
    node_id: uuid.UUID,
    now: datetime | None = None,
) -> NodeCommand | None:
    """Atomically claim the oldest QUEUED command for one node.

    ``FOR UPDATE SKIP LOCKED`` makes two concurrent polls mutually exclusive:
    the loser skips the locked row and returns no message instead of handing the
    same command to two executions.
    """

    query = (
        select(NodeCommand)
        .where(
            NodeCommand.node_id == node_id,
            NodeCommand.status == "QUEUED",
        )
        .order_by(NodeCommand.created_at.asc(), NodeCommand.command_id.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    command = (await session.execute(query)).scalar_one_or_none()
    if command is None:
        return None
    command.status = "SENT"
    command.started_at = now or datetime.now(UTC)
    await session.commit()
    return command


async def pending_command_cancellations(
    session: AsyncSession, *, node_id: uuid.UUID
) -> list[NodeCommand]:
    """Commands the platform already handed to the node but the user stopped.

    The node is outbound-only, so a STOP cannot open a connection to it.  Poll
    returns one ``command_cancel`` message per still-claimed command; a node agent
    that understands the kind can kill the local runner, while an older agent
    ignores the unknown message without breaking its command flow.
    """

    rows = await session.execute(
        select(NodeCommand)
        .where(
            NodeCommand.node_id == node_id,
            NodeCommand.status.in_(("SENT", "RUNNING")),
            NodeCommand.cancel_requested_at.is_not(None),
        )
        .order_by(NodeCommand.created_at.asc(), NodeCommand.command_id.asc())
    )
    return list(rows.scalars())


async def record_command_result(
    session: AsyncSession,
    *,
    node_id: uuid.UUID,
    command_id: str,
    result: CommandResultInput,
) -> NodeCommand:
    """Store a node result for a command owned by ``node_id``.

    Terminal rows are immutable: a replayed result returns the stored row
    unchanged instead of regressing it.  A command addressed to another node is
    reported as not found, never as forbidden, so ids cannot be probed.
    """

    if result.status not in RESULT_STATUSES:
        raise ApiError(
            422,
            "INVALID_COMMAND_STATUS",
            f"status {result.status!r} is not a valid command result",
            details={"allowed_statuses": sorted(RESULT_STATUSES)},
        )
    try:
        parsed_id = uuid.UUID(command_id)
    except ValueError as exc:
        raise command_not_found(command_id) from exc
    command = await session.get(NodeCommand, parsed_id)
    if command is None or command.node_id != node_id:
        raise command_not_found(command_id)
    # Imported lazily: the campaign service reuses this module's allow-list and
    # sanitizer, so a module-level import would be circular.
    from .test_campaign_results import apply_command_result

    if command.status in TERMINAL_STATUSES:
        # A replayed result must still reconcile a campaign that was not folded
        # in the first attempt; the campaign service is idempotent for final rows.
        if command.campaign_id is not None:
            await apply_command_result(
                session, command=command, result=result, now=command.finished_at
            )
            await session.commit()
        return command

    stdout, stdout_truncated = sanitize_output(result.stdout)
    stderr, stderr_truncated = sanitize_output(result.stderr)
    command.status = result.status
    command.exit_code = result.exit_code
    command.stdout = stdout
    command.stderr = stderr
    command.truncated = bool(
        result.truncated or stdout_truncated or stderr_truncated
    )
    command.error_code = result.error_code
    if result.started_at is not None:
        command.started_at = result.started_at
    if result.status in TERMINAL_STATUSES:
        command.finished_at = result.finished_at or datetime.now(UTC)
    if command.campaign_id is not None:
        await apply_command_result(
            session,
            command=command,
            result=result,
            now=result.finished_at,
        )
    await session.commit()
    return command


def command_not_found(command_id: str) -> ApiError:
    return ApiError(
        404,
        "COMMAND_NOT_FOUND",
        f"command {command_id!r} was not found for this node",
        details={"object_type": "node_command", "identifier": command_id},
    )
