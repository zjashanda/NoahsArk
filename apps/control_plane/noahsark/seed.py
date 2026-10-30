"""Deterministic, idempotent prototype seed for the W1 control plane.

Every row is marked ``source='prototype-fixture'`` and ``seed=true``.  IDs are
UUIDv5 derived from stable display keys and timestamps are fixed, so repeated
runs produce byte-identical rows instead of duplicates.

Usage (from apps/control_plane):
    python -m noahsark.seed
    python -m noahsark.seed --reset
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from .config import settings
from .models import Base

SOURCE = "prototype-fixture"
SEED_NAMESPACE = uuid.UUID("6f0d2f5e-7f4a-5c1e-9b8d-3a2f1e0d9c8b")
CST = timezone(timedelta(hours=8))


def stable_uuid(key: str) -> uuid.UUID:
    """Stable UUID for a seed key; exported for tests."""
    return uuid.uuid5(SEED_NAMESPACE, f"noahsark-seed:{key}")


def digest(key: str) -> str:
    return "sha256:" + hashlib.sha256(f"noahsark-seed:{key}".encode()).hexdigest()


def dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=CST)
    return parsed.astimezone(UTC)


def _id(key: str) -> uuid.UUID:
    return stable_uuid(key)


# ---------------------------------------------------------------------------
# Fixed identities used by both seed rows and tests.
# ---------------------------------------------------------------------------
TASK = _id("task:tsk-voice-001")
TASK_OLD = _id("task:tsk-voice-000")
TASK_DISPLAY = "tsk-voice-001"

REVISIONS = {n: _id(f"revision:rev-{n:03d}") for n in range(1, 5)}
REVISION_OLD = _id("revision:rev-006")
APPROVAL = _id("approval:apr-voice-003")
APPROVER = _id("user:approver-02")
SUBMITTER = _id("user:submitter-01")
PLANNER_AGENT = _id("agent:agt-planner")

RUNS = {name: _id(f"run:{name}") for name in ("run-042", "run-039", "run-036", "run-031")}
ATTEMPTS = {name: _id(f"attempt:{name}") for name in ("att-112", "att-111", "att-105")}
CASES = {name: _id(f"case:{name}") for name in (
    "case-voice-001",
    "case-voice-002",
    "case-voice-003",
    "case-voice-004",
    "case-voice-005",
)}
NODES = {name: _id(f"node:{name}") for name in ("node-lab-win-01", "node-lab-win-02")}
DEVICES = {name: _id(f"device:{name}") for name in (
    "dev-tcl-001",
    "dev-tcl-002",
    "dev-tcl-003",
    "dev-tcl-004",
)}
LEASES = {name: _id(f"lease:{name}") for name in ("lease-7781", "lease-7790", "lease-7792")}
EVIDENCE = {name: _id(f"evidence:{name}") for name in (
    "ev-voice-trace-01",
    "ev-serial-log-04",
    "ev-manifest-02",
    "ev-audio-ref-02",
    "ev-noise-run-07",
)}
REPORT = _id("report:rpt-voice-001")
REPORT_STATIC = _id("report:rpt-static-004")


def _common() -> dict[str, Any]:
    return {"schema_version": "1.0", "source": SOURCE, "seed": True}


# ---------------------------------------------------------------------------
# Rows
# ---------------------------------------------------------------------------
def rows_roles() -> list[dict[str, Any]]:
    roles = [
        ("SUPER_ADMIN", "超级管理员", "全局", "ADMIN_ONLY", ["MANAGE_SETTINGS", "MANAGE_ROLES"], 1),
        ("SESSION_MANAGER", "会话管理员", "任务与设备", "TASK_AUTHORIZED", ["NODE_CONTROL", "LEASE"], 2),
        ("APPROVER", "审批者", "任务", "TASK_AUTHORIZED", ["APPROVE_TASK"], 3),
        ("OBSERVER", "观察者", "任务", "SUMMARY_INDEX", ["READ_ONLY"], 4),
    ]
    return [
        {
            "role_code": code,
            "name": name,
            "scope": scope,
            "access_level": access,
            "capabilities": caps,
            "sort_order": order,
            "created_at": dt("2026-10-01 09:00:00"),
            "source": SOURCE,
            "seed": True,
        }
        for code, name, scope, access, caps, order in roles
    ]


def rows_users() -> list[dict[str, Any]]:
    users = [
        ("submitter-01", "任务提交者", "human", "SESSION_MANAGER"),
        ("approver-02", "审批者 02", "human", "APPROVER"),
        ("session-manager-01", "会话管理员 01", "human", "SESSION_MANAGER"),
        ("observer-01", "观察者 01", "human", "OBSERVER"),
        ("admin-01", "平台管理员", "human", "SUPER_ADMIN"),
    ]
    return [
        {
            **_common(),
            "user_id": _id(f"user:{display}"),
            "display_id": display,
            "name": name,
            "actor_kind": kind,
            "role_code": role,
            "status": "ACTIVE",
            "created_at": dt("2026-10-01 09:00:00"),
            "updated_at": dt("2026-10-29 11:20:00"),
        }
        for display, name, kind, role in users
    ]


def rows_agents() -> list[dict[str, Any]]:
    agents = [
        ("agt-planner", "规划 Agent", "候选计划与用例生成", "mb-plan-03", "ACTIVE", "2026-10-29 09:00:00"),
        ("agt-runner-win", "Windows 执行 Agent", "只执行冻结工件并回传事实", "mb-run-01", "ACTIVE", "2026-10-29 08:45:00"),
        ("agt-verifier", "复核 Agent", "证据校验与 fail-closed 建议", "mb-verify-02", "PAUSED", "2026-10-28 18:30:00"),
    ]
    return [
        {
            **_common(),
            "agent_id": _id(f"agent:{display}"),
            "display_id": display,
            "name": name,
            "role": role,
            "model_binding": binding,
            "status": status,
            "last_review": dt(reviewed),
            "created_at": dt("2026-10-01 09:00:00"),
        }
        for display, name, role, binding, status, reviewed in agents
    ]


def rows_nodes() -> list[dict[str, Any]]:
    return [
        {
            **_common(),
            "node_id": NODES["node-lab-win-01"],
            "display_id": "node-lab-win-01",
            "hostname": "LAB-WIN-01",
            "identity": {
                "certificate_subject": "CN=node-lab-win-01",
                "key_id": "key-lab-win-01-3",
                "chain_id": "naa-lab-chain",
                "key_generation": 3,
                "issued_at": dt("2026-10-01 08:00:00").isoformat(),
                "expires_at": dt("2027-10-01 08:00:00").isoformat(),
            },
            "agent_version": "0.1.0-prototype",
            "os": {"name": "Windows", "version": "11", "build": "22631"},
            "runtime": {"python_version": "3.12.3", "lstest_version": "1.8.2", "adapter_version": "2.2.0"},
            "communication_state": "ONLINE",
            "last_heartbeat_at": dt("2026-10-29 14:06:19"),
            "heartbeat_interval_seconds": 30,
            "status": "ACTIVE",
            "interactive_session": {"state": "AVAILABLE", "session_id": "sess-lab-01", "checked_at": dt("2026-10-29 14:06:19").isoformat()},
            "work_dir": {"drive": "D:", "root": "D:\\naa", "capacity_bytes": 512_000_000_000, "free_bytes": 180_000_000_000, "warn_threshold_bytes": 50_000_000_000, "protect_threshold_bytes": 10_000_000_000},
            "spool": {"state": "WARN", "used_bytes": 2_400_000_000, "pending_messages": 2, "oldest_message_at": dt("2026-10-29 13:55:40").isoformat()},
            "capabilities": ["audio_capture", "audio_playback", "serial", "log_read"],
            "endpoint_ids": ["ep-lab-01-serial", "ep-lab-01-audio-in", "ep-lab-01-audio-out"],
            "quarantine_reason": None,
            "draining_reason": None,
            "error_code": None,
            "created_at": dt("2026-10-01 08:30:00"),
            "updated_at": dt("2026-10-29 14:06:19"),
        },
        {
            **_common(),
            "node_id": NODES["node-lab-win-02"],
            "display_id": "node-lab-win-02",
            "hostname": "LAB-WIN-02",
            "identity": {
                "certificate_subject": "CN=node-lab-win-02",
                "key_id": "key-lab-win-02-1",
                "chain_id": "naa-lab-chain",
                "key_generation": 1,
                "issued_at": dt("2026-10-02 08:00:00").isoformat(),
                "expires_at": dt("2027-10-02 08:00:00").isoformat(),
            },
            "agent_version": "0.1.0-prototype",
            "os": {"name": "Windows", "version": "11", "build": "22631"},
            "runtime": {"python_version": "3.12.3", "lstest_version": "1.8.2", "adapter_version": "2.2.0"},
            "communication_state": "OFFLINE",
            "last_heartbeat_at": dt("2026-10-28 22:11:04"),
            "heartbeat_interval_seconds": 30,
            "status": "ACTIVE",
            "interactive_session": {"state": "UNAVAILABLE", "session_id": None, "checked_at": dt("2026-10-28 22:11:04").isoformat()},
            "work_dir": {"drive": "D:", "root": "D:\\naa", "capacity_bytes": 512_000_000_000, "free_bytes": 240_000_000_000, "warn_threshold_bytes": 50_000_000_000, "protect_threshold_bytes": 10_000_000_000},
            "spool": {"state": "BLOCKED", "used_bytes": 0, "pending_messages": 0, "oldest_message_at": None},
            "capabilities": ["audio_capture", "audio_playback", "serial"],
            "endpoint_ids": ["ep-lab-02-serial"],
            "quarantine_reason": None,
            "draining_reason": None,
            "error_code": "communication_offline",
            "created_at": dt("2026-10-02 08:30:00"),
            "updated_at": dt("2026-10-28 22:11:04"),
        },
    ]


def rows_tasks() -> list[dict[str, Any]]:
    return [
        {
            **_common(),
            "task_id": TASK,
            "display_id": TASK_DISPLAY,
            "task_category": "voice_interaction",
            "title": "TCL001 唤醒词回归",
            "objective": "验证 TCL001 在两类噪声与串口恢复场景下的唤醒词命中率与误唤醒上限。",
            "entry_mode": "conversation",
            "origin": {
                "raw_input_refs": [
                    {"ref_id": str(_id("origin:voice-001")), "kind": "conversation", "digest": digest("origin:voice-001"), "captured_at": dt("2026-10-27 15:50:00").isoformat()}
                ],
                "submitted_by": str(SUBMITTER),
                "submitted_at": dt("2026-10-27 15:50:00").isoformat(),
                "normalization_digest": digest("origin-normalized:voice-001"),
            },
            "status": "EXECUTING",
            "lead_agent_id": PLANNER_AGENT,
            "lead_session_id": _id("session:tsk-voice-001"),
            "project_id": _id("project:voice-interaction"),
            "current_revision_id": REVISIONS[3],
            "revision_ids": [str(REVISIONS[n]) for n in range(1, 5)],
            "created_at": dt("2026-10-27 15:50:00"),
            "updated_at": dt("2026-10-29 14:06:22"),
        },
        {
            **_common(),
            "task_id": TASK_OLD,
            "display_id": "tsk-voice-000",
            "task_category": "voice_interaction",
            "title": "TCL001 唤醒词基线",
            "objective": "建立 TCL001 唤醒词基线样本，供后续修订与知识条目引用。",
            "entry_mode": "form",
            "origin": {
                "raw_input_refs": [
                    {"ref_id": str(_id("origin:voice-000")), "kind": "form", "digest": digest("origin:voice-000"), "captured_at": dt("2026-10-26 10:00:00").isoformat()}
                ],
                "submitted_by": str(SUBMITTER),
                "submitted_at": dt("2026-10-26 10:00:00").isoformat(),
                "normalization_digest": digest("origin-normalized:voice-000"),
            },
            "status": "REPORTED",
            "lead_agent_id": PLANNER_AGENT,
            "lead_session_id": _id("session:tsk-voice-000"),
            "project_id": _id("project:voice-interaction"),
            "current_revision_id": REVISION_OLD,
            "revision_ids": [str(REVISION_OLD)],
            "created_at": dt("2026-10-26 10:00:00"),
            "updated_at": dt("2026-10-28 16:58:00"),
        },
    ]


def rows_revisions() -> list[dict[str, Any]]:
    scope_v1 = {"statement": "初始用例集 · 20 次采样", "sample_count": 20}
    scope_v2 = {"statement": "增加串口恢复场景 · 30 次采样", "sample_count": 30, "serial_recovery": 3}
    scope_v3 = {"statement": "40 次正式采样 · 2 类噪声 · 串口恢复 3 次", "sample_count": 40, "noise_types": 2, "serial_recovery": 3}
    scope_v4 = {"statement": "候选：低温启动扩展 0–5°C", "sample_count": 10, "temperature_range_c": [0, 5]}
    return [
        {
            **_common(), "revision_id": REVISIONS[1], "display_id": "rev-001", "task_id": TASK, "revision_number": 1,
            "parent_revision_id": None, "change_kind": "initial", "change_reason": "初始用例集", "origin": {"kind": "initial"},
            "status": "FROZEN", "immutable": True, "content_digest": digest("revision:rev-001"), "frozen_scope": scope_v1,
            "frozen_at": dt("2026-10-27 16:10:00"), "approved_at": dt("2026-10-27 16:30:00"), "approval_id": None,
            "bundle_id": _id("bundle:rev-001"), "superseded_by_revision_id": REVISIONS[2], "created_at": dt("2026-10-27 15:55:00"),
        },
        {
            **_common(), "revision_id": REVISIONS[2], "display_id": "rev-002", "task_id": TASK, "revision_number": 2,
            "parent_revision_id": REVISIONS[1], "change_kind": "scope_change", "change_reason": "增加串口恢复场景", "origin": {"kind": "scope_change", "parent": "rev-001"},
            "status": "SUPERSEDED", "immutable": True, "content_digest": digest("revision:rev-002"), "frozen_scope": scope_v2,
            "frozen_at": dt("2026-10-28 10:02:00"), "approved_at": dt("2026-10-28 10:20:00"), "approval_id": None,
            "bundle_id": _id("bundle:rev-002"), "superseded_by_revision_id": REVISIONS[3], "created_at": dt("2026-10-28 09:40:00"),
        },
        {
            **_common(), "revision_id": REVISIONS[3], "display_id": "rev-003", "task_id": TASK, "revision_number": 3,
            "parent_revision_id": REVISIONS[2], "change_kind": "scope_change", "change_reason": "增加两类噪声场景", "origin": {"kind": "scope_change", "parent": "rev-002"},
            "status": "APPROVED", "immutable": True, "content_digest": digest("revision:rev-003"), "frozen_scope": scope_v3,
            "frozen_at": dt("2026-10-29 11:18:00"), "approved_at": dt("2026-10-29 11:20:00"), "approval_id": APPROVAL,
            "bundle_id": _id("bundle:rev-003"), "superseded_by_revision_id": None, "created_at": dt("2026-10-29 10:40:00"),
        },
        {
            **_common(), "revision_id": REVISIONS[4], "display_id": "rev-004", "task_id": TASK, "revision_number": 4,
            "parent_revision_id": REVISIONS[3], "change_kind": "scope_change", "change_reason": "候选：低温启动扩展", "origin": {"kind": "draft", "parent": "rev-003"},
            "status": "DRAFT", "immutable": False, "content_digest": digest("revision:rev-004"), "frozen_scope": scope_v4,
            "frozen_at": None, "approved_at": None, "approval_id": None, "bundle_id": None, "superseded_by_revision_id": None,
            "created_at": dt("2026-10-29 13:10:00"),
        },
        {
            **_common(), "revision_id": REVISION_OLD, "display_id": "rev-006", "task_id": TASK_OLD, "revision_number": 6,
            "parent_revision_id": None, "change_kind": "regeneration", "change_reason": "基线重生成", "origin": {"kind": "regeneration"},
            "status": "APPROVED", "immutable": True, "content_digest": digest("revision:rev-006"),
            "frozen_scope": {"statement": "基线 1 次正式采样", "sample_count": 1},
            "frozen_at": dt("2026-10-28 14:20:00"), "approved_at": dt("2026-10-28 14:30:00"), "approval_id": None,
            "bundle_id": _id("bundle:rev-006"), "superseded_by_revision_id": None, "created_at": dt("2026-10-28 14:00:00"),
        },
    ]


def rows_approvals() -> list[dict[str, Any]]:
    return [
        {
            **_common(),
            "approval_id": APPROVAL,
            "display_id": "apr-voice-003",
            "task_id": TASK,
            "revision_id": REVISIONS[3],
            "submitter_id": SUBMITTER,
            "approver_id": APPROVER,
            "decision": "APPROVED",
            "comment": "范围、证据要求与冻结摘要一致；允许进入 G3。",
            "revision_content_digest": digest("revision:rev-003"),
            "scope_snapshot": {
                "scope_digest": digest("scope:rev-003"),
                "case_ids": [str(CASES[n]) for n in ("case-voice-001", "case-voice-002", "case-voice-003", "case-voice-004")],
                "oracle_set_digest": digest("oracle:rev-003"),
                "device_action_set_digest": digest("device-actions:rev-003"),
                "budget_digest": digest("budget:rev-003"),
                "evidence_requirement_digest": digest("evidence-requirements:rev-003"),
            },
            "self_approval": False,
            "prevent_self_review": True,
            "wait_timer_seconds": 0,
            "effective_at": dt("2026-10-29 11:20:00"),
            "decided_at": dt("2026-10-29 11:20:00"),
            "withdrawn_reason": None,
            "superseded_by_approval_id": None,
            "idempotency_key": "approval:rev-003:approver-02:scope-v1",
            "created_at": dt("2026-10-29 11:20:00"),
        }
    ]


def rows_gates() -> list[dict[str, Any]]:
    base = [
        ("G0", "受理审阅", "PASSED", "Submitter", "三入口来源已归一。", None),
        ("G1", "冻结批准", "PASSED", "Approver", "审批绑定内容摘要。", None),
        ("G2", "静态检查", "PASSED", "Platform", "static run 已完成。", RUNS["run-036"]),
        ("G3", "资源资格与租约", "PASSED", "Session Manager", "lease-7781 / epoch 7。", RUNS["run-042"]),
        ("G4", "真机烟测", "PASSED", "Operator", "独立 smoke run，不进入正式分母。", RUNS["run-039"]),
        ("G5", "正式采样", "IN_PROGRESS", "Operator", "40 次正式采样进行中。", RUNS["run-042"]),
        ("G6", "证据复核与判定", "PENDING", "Verifier", "等待证据完整。", None),
        ("G7", "报告与知识", "PENDING", "Approver", "判定后生成报告。", None),
    ]
    return [
        {
            **_common(),
            "gate_id": _id(f"gate:{TASK_DISPLAY}:{code}"),
            "display_id": f"gate-{TASK_DISPLAY}-{code}",
            "task_id": TASK,
            "revision_id": REVISIONS[3],
            "run_id": run_id,
            "gate_code": code,
            "order_index": index,
            "status": status,
            "entered_at": dt("2026-10-29 11:20:00") if status != "PENDING" else None,
            "exited_at": dt("2026-10-29 11:30:00") if status == "PASSED" else None,
            "evaluated_by": owner,
            "blocker_owner": None,
            "blockers": [],
            "evidence_refs": [],
            "version": 1,
            "notes": note,
            "created_at": dt("2026-10-29 11:20:00"),
        }
        for index, (code, _name, status, owner, note, run_id) in enumerate(base)
    ]


def rows_cases() -> list[dict[str, Any]]:
    cases = [
        ("case-voice-001", 3, "唤醒词命中", "转写包含“小T小T”", ["raw_audio", "execution_log"], "formal", False),
        ("case-voice-002", 2, "误唤醒控制", "40 次采样中 false_trigger ≤ 1", ["raw_audio", "execution_log"], "formal", False),
        ("case-voice-003", 1, "串口恢复", "断开后 30 秒内恢复会话", ["serial_log", "manifest"], "formal", False),
        ("case-voice-004", 1, "噪声鲁棒性", "两类噪声下命中率不低于基线", ["raw_audio", "execution_log"], "formal", False),
        ("case-voice-005", 1, "烟测预检", "端点可达且一次命中", ["manifest"], "smoke", True),
    ]
    return [
        {
            **_common(),
            "case_id": CASES[name],
            "display_id": name,
            "task_id": TASK,
            "project_id": _id("project:voice-interaction"),
            "name": title,
            "case_version": version,
            "content_digest": digest(f"case:{name}:v{version}"),
            "status": "ACTIVE",
            "steps": [{"step": 1, "action": "prepare"}, {"step": 2, "action": "execute"}, {"step": 3, "action": "collect_evidence"}],
            "required_inputs": ["approved_bundle", "device_lease"],
            "validity_conditions": ["interactive_session_available", "firmware_matches"],
            "required_evidence": required,
            "assertion_refs": [{"oracle": oracle}],
            "frozen_by_revision_id": REVISIONS[3],
            "supersedes_case_version": version - 1 if version > 1 else None,
            "superseded_by_case_version": None,
            "run_mode": mode,
            "reference_only": reference_only,
            "created_at": dt("2026-10-27 16:00:00"),
        }
        for name, version, title, oracle, required, mode, reference_only in cases
    ]


def rows_runs() -> list[dict[str, Any]]:
    return [
        {
            **_common(),
            "run_id": RUNS["run-042"], "display_id": "run-042", "task_id": TASK, "revision_id": REVISIONS[3],
            "bundle_id": _id("bundle:rev-003"), "mode": "formal", "lifecycle_status": "RUNNING",
            "execution_status": "RUNNING", "validity_status": "VALID", "business_verdict": "NOT_EVALUATED",
            "evidence_status": "INCOMPLETE", "verification_status": "NOT_RUN",
            "node_id": NODES["node-lab-win-01"], "device_id": DEVICES["dev-tcl-001"], "lease_id": LEASES["lease-7781"], "lease_epoch": 7,
            "communication_state": "ONLINE", "occupancy_state": "OCCUPIED", "execution_permit": "GRANTED",
            "formal_denominator_eligible": True,
            "attempt_ids": [str(ATTEMPTS["att-112"]), str(ATTEMPTS["att-111"])],
            "cleanup_receipt_id": None, "evidence_manifest_id": _id("manifest:man-run-042"),
            "stop_requested_at": None, "stop_reason": None, "failure_classification": None, "error_code": None,
            "started_at": dt("2026-10-29 13:38:04"), "finished_at": None, "last_heartbeat_at": dt("2026-10-29 14:06:19"),
            "created_at": dt("2026-10-29 13:38:04"), "updated_at": dt("2026-10-29 14:06:19"),
        },
        {
            **_common(),
            "run_id": RUNS["run-039"], "display_id": "run-039", "task_id": TASK, "revision_id": REVISIONS[3],
            "bundle_id": _id("bundle:rev-003"), "mode": "smoke", "lifecycle_status": "COMPLETED",
            "execution_status": "COMPLETED", "validity_status": "VALID", "business_verdict": "PASS",
            "evidence_status": "COMPLETE", "verification_status": "NOT_RUN",
            "node_id": NODES["node-lab-win-01"], "device_id": DEVICES["dev-tcl-001"], "lease_id": LEASES["lease-7781"], "lease_epoch": 7,
            "communication_state": "ONLINE", "occupancy_state": "OCCUPIED", "execution_permit": "NOT_GRANTED",
            "formal_denominator_eligible": False,
            "attempt_ids": [str(ATTEMPTS["att-105"])],
            "cleanup_receipt_id": _id("receipt:cleanup-run-039"), "evidence_manifest_id": None,
            "stop_requested_at": None, "stop_reason": None, "failure_classification": None, "error_code": None,
            "started_at": dt("2026-10-29 12:52:11"), "finished_at": dt("2026-10-29 13:04:47"), "last_heartbeat_at": dt("2026-10-29 13:04:47"),
            "created_at": dt("2026-10-29 12:52:11"), "updated_at": dt("2026-10-29 13:04:47"),
        },
        {
            **_common(),
            "run_id": RUNS["run-036"], "display_id": "run-036", "task_id": TASK, "revision_id": REVISIONS[3],
            "bundle_id": _id("bundle:rev-003"), "mode": "static", "lifecycle_status": "COMPLETED",
            "execution_status": "COMPLETED", "validity_status": "VALID", "business_verdict": "PASS",
            "evidence_status": "COMPLETE", "verification_status": "NOT_RUN",
            "node_id": None, "device_id": None, "lease_id": None, "lease_epoch": None,
            "communication_state": "ONLINE", "occupancy_state": "IDLE", "execution_permit": "NOT_GRANTED",
            "formal_denominator_eligible": False, "attempt_ids": [],
            "cleanup_receipt_id": None, "evidence_manifest_id": None,
            "stop_requested_at": None, "stop_reason": None, "failure_classification": None, "error_code": None,
            "started_at": dt("2026-10-29 11:41:02"), "finished_at": dt("2026-10-29 11:43:19"), "last_heartbeat_at": dt("2026-10-29 11:43:19"),
            "created_at": dt("2026-10-29 11:41:02"), "updated_at": dt("2026-10-29 11:43:19"),
        },
        {
            **_common(),
            "run_id": RUNS["run-031"], "display_id": "run-031", "task_id": TASK_OLD, "revision_id": REVISION_OLD,
            "bundle_id": _id("bundle:rev-006"), "mode": "formal", "lifecycle_status": "COMPLETED",
            "execution_status": "COMPLETED", "validity_status": "VALID", "business_verdict": "PASS",
            "evidence_status": "COMPLETE", "verification_status": "PASS",
            "node_id": NODES["node-lab-win-01"], "device_id": DEVICES["dev-tcl-002"], "lease_id": None, "lease_epoch": None,
            "communication_state": "ONLINE", "occupancy_state": "IDLE", "execution_permit": "NOT_GRANTED",
            "formal_denominator_eligible": True, "attempt_ids": [],
            "cleanup_receipt_id": _id("receipt:cleanup-run-031"), "evidence_manifest_id": None,
            "stop_requested_at": None, "stop_reason": None, "failure_classification": None, "error_code": None,
            "started_at": dt("2026-10-28 15:10:00"), "finished_at": dt("2026-10-28 15:44:30"), "last_heartbeat_at": dt("2026-10-28 15:44:30"),
            "created_at": dt("2026-10-28 15:10:00"), "updated_at": dt("2026-10-28 15:44:30"),
        },
    ]


def rows_attempts() -> list[dict[str, Any]]:
    return [
        {
            **_common(),
            "attempt_id": ATTEMPTS["att-112"], "display_id": "att-112", "run_id": RUNS["run-042"],
            "case_id": CASES["case-voice-001"], "case_version": 3, "run_mode": "formal", "attempt_ordinal": 2,
            "execution_status": "RUNNING", "validity_status": "VALID", "business_verdict": "NOT_EVALUATED",
            "evidence_status": "INCOMPLETE", "verification_status": "NOT_RUN",
            "evidence_origin": "real_device", "denominator_eligible": False,
            "retry_of_attempt_id": ATTEMPTS["att-111"], "flaky_suspect": False,
            "node_id": NODES["node-lab-win-01"], "device_id": DEVICES["dev-tcl-001"], "receipt_id": None,
            "evidence_ids": [str(EVIDENCE["ev-voice-trace-01"]), str(EVIDENCE["ev-serial-log-04"]), str(EVIDENCE["ev-manifest-02"])],
            "anomaly_event_ids": [],
            "facts": [
                {"fact_id": str(_id("fact:att-112:heartbeat")), "name": "node_observed_heartbeat", "value_type": "string", "value": dt("2026-10-29 14:06:19").isoformat(), "observed_at": dt("2026-10-29 14:06:19").isoformat(), "source": "node_agent"},
                {"fact_id": str(_id("fact:att-112:step")), "name": "last_step", "value_type": "string", "value": "playback_noise_burst", "observed_at": dt("2026-10-29 14:06:19").isoformat(), "source": "node_agent"},
                {"fact_id": str(_id("fact:att-112:used")), "name": "node_observed_used_for_decision", "value_type": "boolean", "value": False, "observed_at": dt("2026-10-29 14:06:19").isoformat(), "source": "node_agent"},
            ],
            "failure_classification": None, "failure_detail": None,
            "started_at": dt("2026-10-29 13:58:12"), "finished_at": None,
            "created_at": dt("2026-10-29 13:58:12"),
        },
        {
            **_common(),
            "attempt_id": ATTEMPTS["att-111"], "display_id": "att-111", "run_id": RUNS["run-042"],
            "case_id": CASES["case-voice-001"], "case_version": 3, "run_mode": "formal", "attempt_ordinal": 1,
            "execution_status": "ABORTED", "validity_status": "VALID", "business_verdict": "NOT_EVALUATED",
            "evidence_status": "INCOMPLETE", "verification_status": "NOT_RUN",
            "evidence_origin": "real_device", "denominator_eligible": False,
            "retry_of_attempt_id": None, "flaky_suspect": True,
            "node_id": NODES["node-lab-win-01"], "device_id": DEVICES["dev-tcl-001"], "receipt_id": None,
            "evidence_ids": [str(EVIDENCE["ev-serial-log-04"])],
            "anomaly_event_ids": [],
            "facts": [
                {"fact_id": str(_id("fact:att-111:step")), "name": "last_step", "value_type": "string", "value": "serial_reset", "observed_at": dt("2026-10-29 13:55:38").isoformat(), "source": "node_agent"},
                {"fact_id": str(_id("fact:att-111:state")), "name": "node_observed_local_state", "value_type": "string", "value": "FAILED", "observed_at": dt("2026-10-29 13:55:38").isoformat(), "source": "node_agent"},
                {"fact_id": str(_id("fact:att-111:used")), "name": "node_observed_used_for_decision", "value_type": "boolean", "value": False, "observed_at": dt("2026-10-29 13:55:38").isoformat(), "source": "node_agent"},
            ],
            # Prototype fixture says transport_reset; the authoritative contract has
            # no such failure-classification value, so it stays in failure_detail.
            "failure_classification": None, "failure_detail": "transport_reset",
            "started_at": dt("2026-10-29 13:38:04"), "finished_at": dt("2026-10-29 13:55:40"),
            "created_at": dt("2026-10-29 13:38:04"),
        },
        {
            **_common(),
            "attempt_id": ATTEMPTS["att-105"], "display_id": "att-105", "run_id": RUNS["run-039"],
            "case_id": CASES["case-voice-005"], "case_version": 1, "run_mode": "smoke", "attempt_ordinal": 1,
            "execution_status": "COMPLETED", "validity_status": "VALID", "business_verdict": "PASS",
            "evidence_status": "COMPLETE", "verification_status": "NOT_RUN",
            "evidence_origin": "real_device", "denominator_eligible": False,
            "retry_of_attempt_id": None, "flaky_suspect": False,
            "node_id": NODES["node-lab-win-01"], "device_id": DEVICES["dev-tcl-001"], "receipt_id": None,
            "evidence_ids": [str(EVIDENCE["ev-manifest-02"]), str(EVIDENCE["ev-audio-ref-02"])],
            "anomaly_event_ids": [],
            "facts": [
                {"fact_id": str(_id("fact:att-105:step")), "name": "last_step", "value_type": "string", "value": "smoke_complete", "observed_at": dt("2026-10-29 13:04:46").isoformat(), "source": "node_agent"},
                {"fact_id": str(_id("fact:att-105:used")), "name": "node_observed_used_for_decision", "value_type": "boolean", "value": False, "observed_at": dt("2026-10-29 13:04:46").isoformat(), "source": "node_agent"},
            ],
            "failure_classification": None, "failure_detail": None,
            "started_at": dt("2026-10-29 12:52:11"), "finished_at": dt("2026-10-29 13:04:47"),
            "created_at": dt("2026-10-29 12:52:11"),
        },
    ]


def rows_devices() -> list[dict[str, Any]]:
    def identity(n: str) -> dict[str, Any]:
        return {
            "manufacturer": "ListenAI",
            "model": "ListenAIVCOM",
            "hardware_revision": "R2",
            "serial_number_masked": f"TCL…{n}",
            "identity_digest": digest(f"device-identity:{n}"),
        }

    def endpoints(idx: str) -> list[dict[str, Any]]:
        return [
            {"endpoint_id": f"ep-tcl-{idx}-serial", "kind": "serial", "binding": "COM3", "available": True},
            {"endpoint_id": f"ep-tcl-{idx}-audio-in", "kind": "audio_capture", "binding": "default", "available": True},
            {"endpoint_id": f"ep-tcl-{idx}-audio-out", "kind": "audio_playback", "binding": "default", "available": True},
        ]

    devices = [
        ("dev-tcl-001", "001", "HEALTHY", "ONLINE", "ATTACHED", "OCCUPIED", LEASES["lease-7781"], "TCL001 在役"),
        ("dev-tcl-002", "002", "HEALTHY", "ONLINE", "READY", "IDLE", None, None),
        ("dev-tcl-003", "003", "UNHEALTHY", "OFFLINE", "QUARANTINED", "OCCUPIED", LEASES["lease-7790"], "隔离：串口连续失败"),
        ("dev-tcl-004", "004", "HEALTHY", "ONLINE", "DRAINING", "OCCUPIED", LEASES["lease-7792"], "排空中"),
    ]
    rows = []
    for display, idx, health, comm, pool, occupancy, lease, reason in devices:
        rows.append(
            {
                **_common(),
                "device_id": DEVICES[display],
                "display_id": display,
                "node_id": NODES["node-lab-win-02"] if display == "dev-tcl-003" else NODES["node-lab-win-01"],
                "identity": identity(idx),
                "capabilities": ["audio_capture", "audio_playback", "serial"],
                "endpoints": endpoints(idx),
                "firmware_version": "V037" if display == "dev-tcl-003" else "V038",
                "config_digest": digest(f"device-config:{display}"),
                "adapter_version": "2.2.0",
                "project_scope": [str(_id("project:voice-interaction"))],
                "pool_state": pool,
                "health_state": health,
                "communication_state": comm,
                "occupancy_state": occupancy,
                "current_lease_id": lease,
                "equivalence": None,
                "provenance": {"source": "prototype-fixture", "verified_at": dt("2026-10-01 09:00:00").isoformat(), "verified_by": "seed"},
                "last_seen_at": dt("2026-10-29 14:06:19") if comm == "ONLINE" else dt("2026-10-28 22:11:04"),
                "quarantine_reason": reason if pool == "QUARANTINED" else None,
                "draining_reason": reason if pool == "DRAINING" else None,
                "error_code": None,
                "created_at": dt("2026-10-01 09:00:00"),
                "updated_at": dt("2026-10-29 14:06:19"),
            }
        )
    return rows


def rows_leases() -> list[dict[str, Any]]:
    def preconditions(local: bool, cleanup: bool, reconciled: bool) -> dict[str, bool]:
        return {"local_stop_confirmed": local, "safe_cleanup_done": cleanup, "occupancy_reconciled": reconciled}

    return [
        {
            **_common(), "lease_id": LEASES["lease-7781"], "display_id": "lease-7781",
            "node_id": NODES["node-lab-win-01"], "device_id": DEVICES["dev-tcl-001"],
            "endpoint_set": ["ep-tcl-001-serial", "ep-tcl-001-audio-in", "ep-tcl-001-audio-out"],
            "task_id": TASK, "revision_id": REVISIONS[3], "run_id": RUNS["run-042"], "job_id": _id("job:run-042:att-112"),
            "epoch": 7, "state": "HELD", "occupancy_state": "OCCUPIED", "communication_state": "ONLINE",
            "execution_permit": "GRANTED", "acquired_at": dt("2026-10-29 11:18:44"), "renewed_at": dt("2026-10-29 14:06:19"),
            "expires_at": dt("2026-10-29 14:10:19"), "last_heartbeat_at": dt("2026-10-29 14:06:19"),
            "release_preconditions": preconditions(True, False, False), "released_at": None,
            "release_reason": None, "reclaim_reason": None, "error_code": None, "version": 3,
            "idempotency_key": "lease:node-lab-win-01:dev-tcl-001:epset:run-042",
            "created_at": dt("2026-10-29 11:18:44"),
        },
        {
            **_common(), "lease_id": LEASES["lease-7790"], "display_id": "lease-7790",
            "node_id": NODES["node-lab-win-02"], "device_id": DEVICES["dev-tcl-003"],
            "endpoint_set": ["ep-tcl-003-serial"],
            "task_id": TASK, "revision_id": REVISIONS[3], "run_id": RUNS["run-042"], "job_id": None,
            "epoch": 4, "state": "QUARANTINED", "occupancy_state": "OCCUPIED", "communication_state": "OFFLINE",
            "execution_permit": "SUSPENDED", "acquired_at": dt("2026-10-28 20:00:00"), "renewed_at": None,
            "expires_at": dt("2026-10-28 20:30:00"), "last_heartbeat_at": dt("2026-10-28 22:11:04"),
            "release_preconditions": preconditions(False, False, False), "released_at": None,
            "release_reason": None, "reclaim_reason": "serial_failure_quarantine", "error_code": "DEVICE_QUARANTINED", "version": 2,
            "idempotency_key": "lease:node-lab-win-02:dev-tcl-003:epset:run-042",
            "created_at": dt("2026-10-28 20:00:00"),
        },
        {
            **_common(), "lease_id": LEASES["lease-7792"], "display_id": "lease-7792",
            "node_id": NODES["node-lab-win-01"], "device_id": DEVICES["dev-tcl-004"],
            "endpoint_set": ["ep-tcl-004-serial"],
            "task_id": TASK, "revision_id": REVISIONS[3], "run_id": RUNS["run-039"], "job_id": None,
            "epoch": 2, "state": "HELD", "occupancy_state": "OCCUPIED", "communication_state": "ONLINE",
            "execution_permit": "GRANTED", "acquired_at": dt("2026-10-29 12:00:00"), "renewed_at": dt("2026-10-29 13:04:47"),
            "expires_at": dt("2026-10-29 13:10:00"), "last_heartbeat_at": dt("2026-10-29 13:04:47"),
            "release_preconditions": preconditions(True, False, False), "released_at": None,
            "release_reason": None, "reclaim_reason": None, "error_code": None, "version": 1,
            "idempotency_key": "lease:node-lab-win-01:dev-tcl-004:epset:run-039",
            "created_at": dt("2026-10-29 12:00:00"),
        },
    ]


def rows_evidence() -> list[dict[str, Any]]:
    def item(
        key: str,
        evidence_class: str,
        role: str,
        state: str,
        access: str,
        size: int | None,
        media: str | None,
        received: bool,
        verified: bool,
        created: str,
        digest_value: str | None = None,
    ) -> dict[str, Any]:
        return {
            **_common(),
            "evidence_id": EVIDENCE[key],
            "display_id": key,
            "task_id": TASK,
            "run_id": RUNS["run-042"],
            "attempt_id": ATTEMPTS["att-112"],
            "evidence_class": evidence_class,
            "role": role,
            "state": state,
            "content_digest": digest(f"evidence:{key}") if digest_value is None else digest_value,
            "size_bytes": size,
            "media_type": media,
            "digest_scope": "raw_bytes",
            "provenance": {
                "producer": "node_agent",
                "producer_version": "0.1.0-prototype",
                "captured_at": dt(created).isoformat(),
                "received_at": dt(created).isoformat(),
                "task_id": str(TASK),
                "revision_id": str(REVISIONS[3]),
                "run_id": str(RUNS["run-042"]),
                "case_id": str(CASES["case-voice-001"]),
                "attempt": 2,
                "node_id": str(NODES["node-lab-win-01"]),
                "lease_id": str(LEASES["lease-7781"]),
                "lease_epoch": 7,
                "trust_level": "node_reported",
            },
            "upload": {"chunks_total": 1, "chunks_received": 1 if received else 0},
            "locator": {"kind": "content_addressed", "uri": f"dev-evidence/{key}"},
            "retention": {"class": "task_scoped", "archive_state": "pending"},
            "access_level": access,
            "classification": {"contains_personal_data": False},
            "integrity": {"digest_verified": verified},
            "log_read": None,
            "related_event_ids": [],
            "supersedes": None,
            "notes": None,
            "expected": True,
            "received": received,
            "verified": verified,
            "created_at": dt(created),
        }

    return [
        item("ev-voice-trace-01", "raw_audio", "required", "verified", "evidence_reader", 19_293_798, "audio/wav", True, True, "2026-10-29 13:42:08"),
        item("ev-serial-log-04", "serial_log", "required", "partial", "evidence_reader", 2_201_600, "text/plain", True, False, "2026-10-29 13:44:51"),
        item("ev-manifest-02", "manifest", "required", "verified", "summary", 12_288, "application/json", True, True, "2026-10-29 13:40:02"),
        {**item("ev-audio-ref-02", "raw_audio", "required", "declared", "evidence_reader", None, None, False, False, "2026-10-29 13:35:00", None), "content_digest": None},
        item("ev-noise-run-07", "execution_log", "required", "verified", "summary", 5_033_165, "application/json", True, True, "2026-10-29 14:02:19"),
    ]


def rows_manifests() -> list[dict[str, Any]]:
    return [
        {
            **_common(),
            "manifest_id": _id("manifest:man-run-042"), "display_id": "man-run-042",
            "predicate_type": "noahsark.test-evidence/v1",
            "task_id": TASK, "revision_id": REVISIONS[3], "run_id": RUNS["run-042"],
            "mode": "formal", "acceptance_level": "L4", "test_level": "T6",
            "node_id": NODES["node-lab-win-01"],
            "device_identity": {"device_id": str(DEVICES["dev-tcl-001"]), "model": "ListenAIVCOM", "serial": "TCL…001", "firmware": "V038", "endpoints": ["ep-tcl-001-serial", "ep-tcl-001-audio-in", "ep-tcl-001-audio-out"]},
            "lease_id": LEASES["lease-7781"], "lease_epoch": 7,
            "endpoints": ["ep-tcl-001-serial", "ep-tcl-001-audio-in", "ep-tcl-001-audio-out"],
            "bundle": {"bundle_id": str(_id("bundle:rev-003")), "bundle_digest": digest("bundle:rev-003")},
            "approval": {"approval_id": str(APPROVAL), "revision_content_digest": digest("revision:rev-003")},
            "timebase": {"timebase_id": "tb-lab-01", "clock_source": "linux_ntp", "max_clock_drift_ms": 12},
            "cases": [{"case_id": str(CASES[f"case-voice-00{i}"]), "case_version": v} for i, v in ((1, 3), (2, 2), (3, 1), (4, 1))],
            "evidence_items": [str(EVIDENCE[k]) for k in ("ev-voice-trace-01", "ev-serial-log-04", "ev-manifest-02", "ev-audio-ref-02", "ev-noise-run-07")],
            "required_evidence": {"required_total": 5, "required_verified": 3},
            "completeness": {"complete": False, "missing": ["ev-audio-ref-02"], "unverified": ["ev-serial-log-04"], "conflicted": []},
            "denominators": {"formal_denominator": 40, "excluded_invalid": 0, "excluded_blocked": 0, "excluded_stopped": 0, "excluded_infra": 0, "smoke_excluded": True},
            "invalid_classification": {"counts": {}, "details": []},
            "anomalies": {"blocking_ids": [], "non_blocking_ids": [], "events": []},
            "cleanup_receipt": None,
            "node_receipt": {"receipt_id": str(_id("receipt:node-run-042-att-112")), "receipt_digest": digest("receipt:node-run-042-att-112"), "status": "started"},
            "linux_verification": None,
            "archive": {"state": "hot_only"},
            "redaction": {"policy_id": "redact-default", "applied": False, "redacted_paths": []},
            "manifest_digest": digest("manifest:man-run-042"),
            "supersedes_manifest_digest": None,
            "signatures": [],
            "created_at": dt("2026-10-29 14:06:19"),
            "created_by": "seed",
        }
    ]


def rows_reports() -> list[dict[str, Any]]:
    return [
        {
            **_common(),
            "report_id": REPORT, "display_id": "rpt-voice-001", "task_id": TASK, "revision_id": REVISIONS[3],
            "version": 3, "title": "TCL001 唤醒词回归报告", "lifecycle": "FROZEN", "denominator": 40,
            "disclosure": "INTERNAL", "sections": 14, "evidence_index": 5,
            "denominator_statement": {"formal_denominator": 40, "excluded_invalid": 0, "excluded_blocked": 0, "excluded_stopped": 0, "excluded_infra": 0, "smoke_excluded": True, "statement": "formal_denominator = 有效正式样本；smoke/invalid/blocked/stopped/infra 不计入。"},
            "runs": [{"run_id": str(RUNS["run-042"]), "mode": "formal", "decision": "NOT_EVALUATED", "release_state": "held"}],
            "evidence_index_data": [{"evidence_id": str(EVIDENCE[k]), "state": "verified" if k != "ev-serial-log-04" else "partial"} for k in ("ev-voice-trace-01", "ev-serial-log-04", "ev-manifest-02", "ev-audio-ref-02", "ev-noise-run-07")],
            "release_index": [{"run_id": str(RUNS["run-042"]), "release_confirmed": False, "held_reason": "safe_cleanup_done=false"}],
            "access": {"default_visibility": "summary_and_index", "raw_material_requires": "evidence_reader"},
            "unresolved": [{"code": "cleanup_receipt_missing", "description": "设备释放未确认", "owner": "Session Manager", "blocking": False}],
            "redaction": {"policy_id": "redact-default", "applied": False, "redacted_paths": []},
            "report_digest": digest("report:rpt-voice-001"),
            "notes": None,
            "content": {"summary": "正式采样进行中；释放保持 held。"},
            "frozen_at": dt("2026-10-29 15:20:00"),
            "created_at": dt("2026-10-29 15:20:00"),
        },
        {
            **_common(),
            "report_id": REPORT_STATIC, "display_id": "rpt-static-004", "task_id": TASK, "revision_id": REVISIONS[3],
            "version": 1, "title": "静态检查汇总", "lifecycle": "DRAFT", "denominator": None,
            "disclosure": "INTERNAL", "sections": 6, "evidence_index": 2,
            "denominator_statement": {"formal_denominator": 0, "excluded_invalid": 0, "excluded_blocked": 0, "excluded_stopped": 0, "excluded_infra": 0, "smoke_excluded": True, "statement": "静态检查不进入正式分母。"},
            "runs": [{"run_id": str(RUNS["run-036"]), "mode": "static", "decision": "NOT_APPLICABLE", "release_state": "not_applicable"}],
            "evidence_index_data": [],
            "release_index": [],
            "access": {"default_visibility": "summary_and_index", "raw_material_requires": "evidence_reader"},
            "unresolved": [],
            "redaction": {"policy_id": "redact-default", "applied": False, "redacted_paths": []},
            "report_digest": digest("report:rpt-static-004"),
            "notes": None,
            "content": {"summary": "静态检查通过，仅供预检。"},
            "frozen_at": None,
            "created_at": dt("2026-10-29 11:44:00"),
        },
    ]


def rows_knowledge() -> list[dict[str, Any]]:
    return [
        {
            **_common(), "knowledge_id": _id("knowledge:kn-wake-false-trigger"), "display_id": "kn-wake-false-trigger",
            "status": "APPROVED", "title": "噪声段误唤醒阈值", "applicability": "TCL001 · V038 · 两类噪声",
            "summary": "在两类噪声下将误唤醒上限设为 1/40，需人工复核后用于新修订。",
            "source_chain": ["run-031", "ev-noise-run-07", "review-006"], "content": {}, "version": 2,
            "approved_by": APPROVER, "updated_at": dt("2026-10-28 17:02:00"), "created_at": dt("2026-10-28 16:00:00"),
        },
        {
            **_common(), "knowledge_id": _id("knowledge:kn-noise-profile"), "display_id": "kn-noise-profile",
            "status": "CORROBORATED", "title": "串口恢复时间基线", "applicability": "TCL 系列 · V038",
            "summary": "串口恢复中位数 12.4 秒，仍需更多样本佐证。",
            "source_chain": ["run-036", "ev-serial-log-04"], "content": {}, "version": 1,
            "approved_by": None, "updated_at": dt("2026-10-29 09:31:00"), "created_at": dt("2026-10-29 09:31:00"),
        },
        {
            **_common(), "knowledge_id": _id("knowledge:kn-legacy-flaky"), "display_id": "kn-legacy-flaky",
            "status": "STALE", "title": "旧版重试策略", "applicability": "V036 及以前",
            "summary": "基于旧固件的重试策略，已被当前基线取代，不得直接推广。",
            "source_chain": ["run-018"], "content": {}, "version": 1,
            "approved_by": None, "updated_at": dt("2026-09-12 10:15:00"), "created_at": dt("2026-09-12 10:15:00"),
        },
    ]


def rows_candidates() -> list[dict[str, Any]]:
    candidates = [
        ("knc-014", "PROPOSED", "低温启动补偿", ["run-031", "ev-noise-run-07"], "TCL001 · 环境温度 0–5°C", "AGENT_PLANNER", "2026-10-29 13:10:00"),
        ("knc-012", "UNDER_REVIEW", "噪声突发前的静音窗口", ["run-039", "ev-voice-trace-01"], "TCL001 · V038", "AGENT_PLANNER", "2026-10-29 12:02:00"),
        ("knc-009", "NEEDS_INFO", "串口重连抖动分类", ["run-042", "att-111"], "待补充样本", "AGENT_VERIFIER", "2026-10-29 10:44:00"),
        ("knc-006", "APPROVED", "唤醒词基线阈值", ["run-031"], "TCL001 · V038", "AGENT_PLANNER", "2026-10-28 17:00:00"),
    ]
    return [
        {
            **_common(), "candidate_id": _id(f"candidate:{cid}"), "display_id": cid, "status": status,
            "title": title, "source_chain": chain, "applicability": applicability, "proposed_by": proposed_by,
            "automatic_promotion_allowed": False, "requires_human_review": True, "content": {},
            "updated_at": dt(updated), "created_at": dt(updated),
        }
        for cid, status, title, chain, applicability, proposed_by, updated in candidates
    ]


def rows_reviews() -> list[dict[str, Any]]:
    return [
        {
            **_common(), "review_id": _id("review:revw-007"), "display_id": "revw-007", "task_id": TASK,
            "revision_id": REVISIONS[3], "stage": "PENDING", "consensus": "2 / 3", "open_risks": 1,
            "updated_at": dt("2026-10-29 11:06:00"), "created_at": dt("2026-10-29 10:30:00"),
        },
        {
            **_common(), "review_id": _id("review:revw-006"), "display_id": "revw-006", "task_id": TASK_OLD,
            "revision_id": REVISION_OLD, "stage": "COMPLETED", "consensus": "3 / 3", "open_risks": 0,
            "updated_at": dt("2026-10-28 16:58:00"), "created_at": dt("2026-10-28 16:00:00"),
        },
    ]


def rows_audit() -> list[dict[str, Any]]:
    events = [
        ("aud-20261029-041", "2026-10-29 11:20:03", "APPROVER", "APPROVAL_GRANTED", "task_revision", "rev-003", "ALLOW"),
        ("aud-20261029-040", "2026-10-29 11:18:44", "SESSION_MANAGER", "LEASE_GRANTED", "lease", "lease-7781", "ALLOW"),
        ("aud-20261029-039", "2026-10-29 10:59:12", "OBSERVER", "EVIDENCE_ACCESS_DENIED", "evidence_item", "ev-voice-trace-01", "DENY"),
        ("aud-20261029-038", "2026-10-29 10:41:30", "ADMIN", "TOOLCHAIN_LOCK_CHANGED", "toolchain", "toolchain-lock-12", "ALLOW"),
        ("aud-20261029-037", "2026-10-29 10:12:08", "SESSION_MANAGER", "RECONCILE_STARTED", "run", "run-042", "ALLOW"),
    ]
    rows = []
    for event_id, occurred, role, action, object_type, object_id, decision in events:
        rows.append(
            {
                "source": SOURCE,
                "seed": True,
                "event_id": event_id,
                "occurred_at": dt(occurred),
                "actor_id": APPROVER if role == "APPROVER" else None,
                "actor_role": role,
                "action": action,
                "object_type": object_type,
                "object_id": object_id,
                "before": None,
                "after": {"object_id": object_id},
                "reason": None,
                "correlation_id": f"seed:{event_id}",
                "correlation": {"task_id": str(TASK)},
                "access_decision": decision,
                "result": "SUCCESS",
                "integrity": "HASH_CHAIN_OK",
                "prev_event_hash": None,
                "event_hash": digest(f"audit:{event_id}"),
                "created_at": dt(occurred),
            }
        )
    return rows


def rows_settings() -> list[dict[str, Any]]:
    settings_rows = [
        ("notification", "inbox", {"channel": "站内", "target": "审批队列", "delivery": "HEALTHY", "dead_letter": 0}),
        ("notification", "email", {"channel": "邮件", "target": "已脱敏通讯组", "delivery": "DEGRADED", "dead_letter": 2}),
        ("retention", "audit_events", {"object": "审计事件", "policy": "730 天 · 不可原地修改", "version": "ret-04", "effective_at": "2026-10-01"}),
        ("retention", "evidence_metadata", {"object": "证据元数据", "policy": "365 天 · 删除走补偿事件", "version": "ret-03", "effective_at": "2026-09-15"}),
        ("retention", "reports", {"object": "报告", "policy": "冻结后长期保留", "version": "ret-02", "effective_at": "2026-08-20"}),
        ("runtime_model", "mb-plan-03", {"binding": "mb-plan-03", "purpose": "候选计划", "model": "planner-binding-v3", "status": "LOCKED", "drift": "NONE"}),
        ("runtime_model", "mb-run-01", {"binding": "mb-run-01", "purpose": "节点执行", "model": "runner-binding-v1", "status": "LOCKED", "drift": "NONE"}),
        ("runtime_model", "mb-verify-02", {"binding": "mb-verify-02", "purpose": "证据复核", "model": "verifier-binding-v2", "status": "LOCKED", "drift": "NONE"}),
        ("runtime_model", "mb-summary-01", {"binding": "mb-summary-01", "purpose": "报告摘要", "model": "summary-binding-v1", "status": "DRIFT", "drift": "VERSION_MISMATCH"}),
        ("runtime_lock", "lstest", {"name": "lstest", "version": "1.8.2", "lock": "LOCKED", "checked_at": "2026-10-29 11:41 +08:00"}),
        ("runtime_lock", "audio-harness", {"name": "audio-harness", "version": "0.9.4", "lock": "DRIFT", "checked_at": "2026-10-29 11:41 +08:00"}),
        ("runtime_lock", "serial-adapter", {"name": "serial-adapter", "version": "2.2.0", "lock": "LOCKED", "checked_at": "2026-10-29 11:41 +08:00"}),
    ]
    return [
        {
            **_common(), "setting_id": _id(f"setting:{category}:{key}"), "category": category, "key": key,
            "value": value, "version": 1, "updated_at": dt("2026-10-29 11:41:00"),
            "created_at": dt("2026-10-01 09:00:00"),
        }
        for category, key, value in settings_rows
    ]


def rows_intake_drafts() -> list[dict[str, Any]]:
    drafts = [
        ("drf-009", "低温启动回归", "form", "DRAFT", 3, 1, 2, "Submitter", "2026-10-29 14:02:00",
         "低温启动扩展的入口草稿，等待补齐环境温度边界。"),
        ("drf-008", "噪声场景补充", "conversation", "REVIEW", 2, 0, 1, "Submitter", "2026-10-29 10:18:00",
         "会话入口抽取的噪声场景补充，已进入审阅。"),
        ("drf-007", "串口恢复脚本", "file", "DRAFT", 4, 2, 3, "Submitter", "2026-10-28 17:44:00",
         "文件入口导入的串口恢复脚本，存在两个来源冲突。"),
    ]
    rows: list[dict[str, Any]] = []
    for display, title, mode, stage, sources, conflicts, gaps, owner, updated, summary in drafts:
        rows.append(
            {
                **_common(),
                "draft_id": _id(f"intake-draft:{display}"),
                "display_id": display,
                "title": title,
                "entry_mode": mode,
                "stage": stage,
                "source_count": sources,
                "conflict_count": conflicts,
                "gap_count": gaps,
                "owner_role": owner,
                "summary": summary,
                "sources": [
                    {"ref_id": str(_id(f"intake-source:{display}:{index}")), "kind": mode, "label": f"来源 {index + 1}"}
                    for index in range(sources)
                ],
                "facts": [
                    {"fact_id": str(_id(f"intake-fact:{display}:{index}")), "name": name, "origin": "extracted"}
                    for index, name in enumerate(("device", "firmware", "sample_count")[:max(1, min(3, sources))])
                ],
                "conflicts": [
                    {"conflict_id": str(_id(f"intake-conflict:{display}:{index}")), "summary": f"来源冲突 {index + 1}", "status": "OPEN"}
                    for index in range(conflicts)
                ],
                "gaps": [
                    {"gap_id": str(_id(f"intake-gap:{display}:{index}")), "summary": f"待补充信息 {index + 1}", "status": "OPEN"}
                    for index in range(gaps)
                ],
                "freshness": {
                    "is_stale": False,
                    "last_authoritative_update": dt(updated).isoformat(),
                    "last_known_at": dt(updated).isoformat(),
                },
                "created_at": dt(updated),
                "updated_at": dt(updated),
            }
        )
    return rows


def rows_idempotency() -> list[dict[str, Any]]:
    return [
        {
            "id": _id("idempotency:approval:rev-003"),
            "scope": "approval",
            "key": "approval:rev-003:approver-02:scope-v1",
            "request_hash": digest("idempotency-request:approval:rev-003"),
            "status_code": 201,
            "response": {"approval_id": str(APPROVAL), "decision": "APPROVED"},
            "expires_at": None,
            "created_at": dt("2026-10-29 11:20:00"),
        }
    ]


# Insert order respects foreign keys.  A run's lease_id has no FK (cycle breaker).
SEED_TABLES: list[tuple[str, Iterable[dict[str, Any]]]] = [
    ("intake_drafts", rows_intake_drafts()),
    ("roles", rows_roles()),
    ("users", rows_users()),
    ("agents", rows_agents()),
    ("nodes", rows_nodes()),
    ("devices", rows_devices()),
    ("tasks", rows_tasks()),
    ("task_revisions", rows_revisions()),
    ("approvals", rows_approvals()),
    ("gates", rows_gates()),
    ("cases", rows_cases()),
    ("runs", rows_runs()),
    ("attempts", rows_attempts()),
    ("leases", rows_leases()),
    ("evidence_items", rows_evidence()),
    ("evidence_manifests", rows_manifests()),
    ("reports", rows_reports()),
    ("knowledge_items", rows_knowledge()),
    ("knowledge_candidates", rows_candidates()),
    ("reviews", rows_reviews()),
    ("audit_events", rows_audit()),
    ("settings", rows_settings()),
    ("idempotency_keys", rows_idempotency()),
    # Empty on purpose: W3 write requests must never be seeded, but ``--reset``
    # must truncate them so write tests start from a clean slate.
    ("write_requests", []),
    # Sessions are runtime-only; ``--reset`` clears them.
    ("sessions", []),
]

RESET_ORDER = [name for name, _ in reversed(SEED_TABLES)]


async def upsert_table(session: AsyncSession, name: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    table = Base.metadata.tables[name]
    stmt = pg_insert(table).values(rows)
    pk_columns = [column.name for column in table.primary_key.columns]
    update_columns = {
        column.name: getattr(stmt.excluded, column.name)
        for column in table.columns
        if column.name not in pk_columns
    }
    stmt = stmt.on_conflict_do_update(index_elements=pk_columns, set_=update_columns)
    await session.execute(stmt)


async def reset_seed_tables(session: AsyncSession) -> None:
    names = ", ".join(RESET_ORDER)
    await session.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))


async def seed_database(reset: bool = False) -> dict[str, int]:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured; refusing to seed without PostgreSQL")
    if settings.database_url.startswith("sqlite"):
        raise RuntimeError("SQLite is not an authority; refusing to seed")

    engine = create_async_engine(settings.database_url)
    try:
        async with (
            engine.begin() as connection,
            AsyncSession(connection, expire_on_commit=False) as session,
        ):
            if reset:
                await reset_seed_tables(session)
            for name, rows in SEED_TABLES:
                await upsert_table(session, name, list(rows))
        async with engine.connect() as connection:
            counts = {}
            for name, _ in SEED_TABLES:
                result = await connection.execute(text(f"SELECT count(*) FROM {name}"))
                counts[name] = int(result.scalar_one())
        return counts
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed deterministic prototype data into PostgreSQL.")
    parser.add_argument("--reset", action="store_true", help="truncate seeded tables before inserting")
    args = parser.parse_args()
    counts = asyncio.run(seed_database(reset=args.reset))
    print("seed ok" + (" (reset)" if args.reset else ""))
    for name in ("intake_drafts", "tasks", "task_revisions", "approvals", "gates", "cases", "runs", "attempts",
                 "leases", "devices", "nodes", "evidence_items", "evidence_manifests", "reports",
                 "knowledge_items", "knowledge_candidates", "agents", "reviews", "audit_events",
                 "roles", "users", "settings"):
        print(f"  {name}: {counts[name]}")


if __name__ == "__main__":
    main()
