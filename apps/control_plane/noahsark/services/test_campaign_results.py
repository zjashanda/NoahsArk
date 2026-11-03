"""Parse untrusted ``test.run`` results and fold them into a campaign.

The node payload is hostile input: ``summary`` may be a dict or a JSON string,
``rounds`` may be missing, oversized or malformed, and artifact paths may be the
only thing the node returned.  This module validates and caps everything before
persistence.

The campaign status always follows the command lifecycle.  A verdict is recorded
only when the summary states one explicitly; a missing summary or a paths-only
result keeps ``verdict`` null so the platform never claims a PASS it did not see.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.command import NodeCommand
from ..models.test_campaign import FINAL_CAMPAIGN_STATUSES, TestCampaign
from . import audit, node_commands, resource_leases

MAX_ROUNDS_ENTRIES = 1000
# ``summary`` and ``rounds`` are independent evidence: a 489-round campaign
# sends ~0.5 MiB of rows plus a small summary, so one oversized part must not
# discard the other.  Each part has its own budget comfortably above the
# largest campaign the API accepts (1000 rounds).
MAX_SUMMARY_BYTES = 4 * 1024 * 1024
MAX_ROUNDS_BYTES = 4 * 1024 * 1024
MAX_PATH_CHARS = 1024
MAX_TEXT_CHARS = 8192
PASS, FAIL = "PASS", "FAIL"
PASS_TOKENS = frozenset({"PASS", "PASSED", "SUCCESS", "SUCCEEDED", "OK"})
FAIL_TOKENS = frozenset({"FAIL", "FAILED", "ERROR", "ERRORED"})
# ``STOPPED`` stays reserved for an explicit platform stop and is never inferred
# from a node result.
COMMAND_STATUS_TO_CAMPAIGN = {
    "QUEUED": "RUNNING",
    "SENT": "RUNNING",
    "RUNNING": "RUNNING",
    "SUCCEEDED": "SUCCEEDED",
    "FAILED": "FAILED",
    "TIMEOUT": "TIMEOUT",
}
TERMINAL_COMMAND_STATUSES = frozenset({"SUCCEEDED", "FAILED", "TIMEOUT"})


def _clean_text(value: Any, limit: int = MAX_TEXT_CHARS) -> str | None:
    if not isinstance(value, str):
        return None
    clean, _ = node_commands.sanitize_output(value)
    if not clean:
        return None
    return clean[:limit]


def _json_size(value: Any) -> int:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return len(encoded.encode("utf-8"))


def _coerce_summary(value: Any) -> tuple[dict[str, Any] | None, str | None]:
    if value is None:
        return None, None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            return None, "SUMMARY_INVALID"
    if not isinstance(value, dict):
        return None, "SUMMARY_INVALID"
    return dict(value), None


def _coerce_rounds(value: Any) -> tuple[list[dict[str, Any]] | None, str | None]:
    if value is None:
        return None, None
    if not isinstance(value, list) or len(value) > MAX_ROUNDS_ENTRIES:
        return None, "ROUNDS_INVALID"
    rows: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            return None, "ROUNDS_INVALID"
        rows.append(dict(item))
    return rows, None


def _token(value: Any) -> str | None:
    return value.strip().upper() if isinstance(value, str) and value.strip() else None


def _derive_rounds_from_summary(
    summary: dict[str, Any] | None,
) -> list[dict[str, Any]] | None:
    """Expand a single-status summary into per-round rows.

    ``results.csv`` can be empty for the formal ``wake-recognition`` path.  When
    the summary reports one unambiguous status for every completed round (the
    TCL003 5/5 ``RECOGNIZED`` case) the rows are derived from that aggregate and
    tagged ``derived``/``source`` so the platform never presents them as raw
    per-case evidence.  Mixed-status summaries stay aggregate-only: their round
    ordering is unknown and guessing it would fabricate evidence.
    """

    if not summary:
        return None
    nested = summary.get("rounds")
    if isinstance(nested, list) and nested:
        rows, error = _coerce_rounds(nested)
        if rows and error is None:
            return rows
    counts = summary.get("status_counts")
    if not isinstance(counts, dict) or len(counts) != 1:
        return None
    status, count = next(iter(counts.items()))
    if not isinstance(status, str) or not status.strip():
        return None
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        return None
    completed = summary.get("completed_rounds")
    if isinstance(completed, bool) or not isinstance(completed, int):
        return None
    if completed != count or count > MAX_ROUNDS_ENTRIES:
        return None
    return [
        {
            "round": index + 1,
            "status": status,
            "source": "summary_final.json",
            "derived": True,
        }
        for index in range(count)
    ]


def _verdict_from_summary(summary: dict[str, Any] | None) -> str | None:
    """Return an explicit PASS/FAIL verdict, never a guess."""

    if not summary:
        return None
    for key in ("outcome", "verdict", "result", "overall_status", "status"):
        token = _token(summary.get(key))
        if token in PASS_TOKENS:
            return PASS
        if token in FAIL_TOKENS:
            return FAIL
    counts = summary.get("status_counts")
    if isinstance(counts, dict) and counts:
        try:
            total = sum(int(value) for value in counts.values())
        except (TypeError, ValueError):
            return None
        target = summary.get("target_rounds")
        expected = int(target) if isinstance(target, int) else None
        if expected is not None and total == expected:
            if int(counts.get(PASS, 0)) == expected:
                return PASS
            if int(counts.get(FAIL, 0)) > 0:
                return FAIL
    return None


def _payload(
    *,
    campaign: TestCampaign,
    command: NodeCommand,
    result: Any,
    notes: list[str],
) -> tuple[dict[str, Any], str | None]:
    summary, summary_error = _coerce_summary(getattr(result, "summary", None))
    raw_rounds = getattr(result, "rounds", None)
    if raw_rounds is None:
        raw_rounds = getattr(result, "rounds_rows", None)
    rounds, rounds_error = _coerce_rounds(raw_rounds)
    if not rounds and summary is not None:
        derived = _derive_rounds_from_summary(summary)
        if derived:
            rounds = derived
            rounds_error = None
            notes.append("ROUNDS_DERIVED_FROM_SUMMARY")
        elif isinstance(summary.get("status_counts"), dict) and summary.get("status_counts"):
            notes.append("ROUNDS_AGGREGATE_ONLY")
    parse_error = summary_error or rounds_error
    if summary_error:
        notes.append(summary_error)
    if rounds_error:
        notes.append(rounds_error)
    if summary is None:
        notes.append("SUMMARY_MISSING")
    if rounds is not None and len(rounds) != campaign.rounds:
        notes.append("ROUNDS_COUNT_MISMATCH")
    if summary is not None and _json_size(summary) > MAX_SUMMARY_BYTES:
        notes.append("SUMMARY_TOO_LARGE")
        parse_error = parse_error or "SUMMARY_TOO_LARGE"
        summary = None
    if rounds is not None and _json_size(rounds) > MAX_ROUNDS_BYTES:
        notes.append("ROUNDS_TOO_LARGE")
        parse_error = parse_error or "ROUNDS_TOO_LARGE"
        rounds = None
    if summary is None and (
        getattr(result, "result_dir", None)
        or getattr(result, "summary_path", None)
        or getattr(result, "rounds_path", None)
    ):
        notes.append("ARTIFACT_PATHS_ONLY")

    payload = {
        "verdict": _verdict_from_summary(summary),
        "summary": summary,
        "rounds": rounds,
        "rounds_count": len(rounds) if rounds is not None else 0,
        "expected_rounds": campaign.rounds,
        "artifacts": {
            "result_dir": _clean_text(getattr(result, "result_dir", None), MAX_PATH_CHARS),
            "summary_path": _clean_text(getattr(result, "summary_path", None), MAX_PATH_CHARS),
            "rounds_path": _clean_text(getattr(result, "rounds_path", None), MAX_PATH_CHARS),
        },
        "command": {
            "command_id": str(command.command_id),
            "status": command.status,
            "exit_code": command.exit_code,
            "error_code": command.error_code,
            "truncated": bool(command.truncated),
        },
        "notes": notes,
    }
    return payload, parse_error


async def apply_command_result(
    session: AsyncSession,
    *,
    command: NodeCommand,
    result: Any,
    now: datetime | None = None,
) -> TestCampaign | None:
    """Fold a ``test.run`` result into its campaign.

    Returns ``None`` when the command is not a campaign command (for example the
    unchanged ``usb.scan`` path).  The caller owns the commit.  Replayed results
    and terminal campaigns are idempotent: the campaign is never regressed.
    """

    if command.campaign_id is None:
        return None
    campaign = await session.get(TestCampaign, command.campaign_id)
    if campaign is None:
        return campaign

    notes: list[str] = []
    payload, parse_error = _payload(
        campaign=campaign, command=command, result=result, notes=notes
    )
    final_campaign = campaign.status in FINAL_CAMPAIGN_STATUSES
    if final_campaign:
        # A terminal campaign is never regressed, but a replayed result may
        # still carry evidence the first fold missed (empty results.csv, a
        # summary that arrived out of band).  Fill only the missing parts.
        stored = dict(campaign.summary or {})
        new_rounds = payload["rounds"] or []
        if payload["summary"] is None and not new_rounds:
            return campaign
        if stored:
            merged = stored
            if payload["summary"] is not None and merged.get("summary") is None:
                merged["summary"] = payload["summary"]
            if new_rounds and not campaign.rounds_data:
                merged["rounds"] = new_rounds
                merged["rounds_count"] = len(new_rounds)
                campaign.rounds_data = new_rounds
            if merged.get("verdict") is None and payload.get("verdict") is not None:
                merged["verdict"] = payload["verdict"]
            if not merged.get("artifacts"):
                merged["artifacts"] = payload["artifacts"]
            if not merged.get("notes"):
                merged["notes"] = payload["notes"]
            campaign.summary = merged
        else:
            campaign.summary = payload
            campaign.rounds_data = payload["rounds"]
        recorded_status = campaign.status
    else:
        campaign.summary = payload
        campaign.rounds_data = payload["rounds"]
        campaign.status = COMMAND_STATUS_TO_CAMPAIGN.get(command.status, "RUNNING")
        campaign.error_code = parse_error or command.error_code
        if command.started_at is not None and campaign.started_at is None:
            campaign.started_at = command.started_at
        if command.status in TERMINAL_COMMAND_STATUSES:
            campaign.finished_at = now or command.finished_at or datetime.now(UTC)
        recorded_status = campaign.status

    # Hardware exclusivity follows the campaign lifecycle: a terminal result
    # releases the node's resources; an in-flight result renews the lease so a
    # long 8-hour run cannot be reclaimed by TTL while it is still alive.
    if campaign.status in FINAL_CAMPAIGN_STATUSES:
        await resource_leases.release_owner(
            session,
            owner_type=resource_leases.OWNER_TEST_CAMPAIGN,
            owner_id=campaign.campaign_id,
            reason=resource_leases.RELEASE_TERMINAL,
            now=now or command.finished_at,
        )
    else:
        await resource_leases.renew_owner(
            session,
            owner_type=resource_leases.OWNER_TEST_CAMPAIGN,
            owner_id=campaign.campaign_id,
            now=now,
        )

    await audit.append_event(
        session,
        actor_role="SYSTEM",
        actor_id=None,
        action="TEST_CAMPAIGN_RESULT_RECORDED",
        object_type="test_campaign",
        object_id=str(campaign.campaign_id),
        before=None,
        after={
            "campaign_id": str(campaign.campaign_id),
            "command_id": str(command.command_id),
            "command_status": command.status,
            "status": recorded_status,
            "verdict": payload["verdict"],
            "rounds_count": payload["rounds_count"],
            "notes": notes,
            "backfill": final_campaign,
        },
        reason=None,
        correlation_id=None,
        path="/node/v1/command-results",
    )
    return campaign
