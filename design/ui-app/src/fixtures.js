// Prototype fixtures. No real hosts, credentials, logs, or personal data.
// Every projection is non-authoritative: server_authoritative=false.

import { AXIS_ORDER } from "./semantics.js";

export const FIXTURE_META = Object.freeze({
  source: "prototype-fixture",
  schema_version: "0.1",
  server_authoritative: false
});

export const SCENARIOS = [
  { id: "FX-01", label: "FX-01 · 正常候选流程", flags: {} },
  { id: "FX-02", label: "FX-02 · blocked", flags: { blocked: true } },
  { id: "FX-03", label: "FX-03 · stale + running", flags: { stale: true } },
  { id: "FX-04", label: "FX-04 · offline + running + occupied + granted", flags: { offline: true } },
  { id: "FX-05", label: "FX-05 · reconciling + pending STOP", flags: { reconciling: true, pendingStop: true } },
  { id: "FX-06", label: "FX-06 · unknown-progress", flags: { unknownProgress: true } },
  { id: "FX-07", label: "FX-07 · partial evidence + business PASS", flags: { partialEvidence: true } },
  { id: "FX-08", label: "FX-08 · quarantined + occupied", flags: { quarantined: true } },
  { id: "FX-09", label: "FX-09 · draining + running", flags: { draining: true } },
  { id: "FX-10", label: "FX-10 · no-permission", flags: { noPermission: true } },
  { id: "FX-11E", label: "FX-11E · empty", flags: { empty: true } },
  { id: "FX-11L", label: "FX-11L · loading", flags: { loading: true } },
  { id: "FX-11X", label: "FX-11X · error", flags: { error: true } },
  { id: "FX-12", label: "FX-12 · complete formal PASS", flags: { formalPass: true } }
];

const STORAGE_KEY = "naa-scenario";

export function scenarioById(id) {
  return SCENARIOS.find((item) => item.id === id) || SCENARIOS[0];
}

export function getScenarioId() {
  if (typeof window === "undefined" || !window.localStorage) return "FX-01";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return SCENARIOS.some((item) => item.id === stored) ? stored : "FX-01";
}

export function setScenarioId(id) {
  if (typeof window !== "undefined" && window.localStorage) {
    window.localStorage.setItem(STORAGE_KEY, scenarioById(id).id);
  }
}

export function currentScenario() {
  return scenarioById(getScenarioId());
}

const BASE_AXES = {
  execution_status: "RUNNING",
  validity_status: "VALID",
  business_verdict: "PENDING",
  evidence_status: "INCOMPLETE",
  verification_status: "PENDING"
};

const AXES_BY_SCENARIO = {
  "FX-01": BASE_AXES,
  "FX-02": { execution_status: "BLOCKED", validity_status: "UNKNOWN", business_verdict: "BLOCKED", evidence_status: "INCOMPLETE", verification_status: "BLOCKED" },
  "FX-03": BASE_AXES,
  "FX-04": { execution_status: "RUNNING", validity_status: "VALID", business_verdict: "PENDING", evidence_status: "INCOMPLETE", verification_status: "PENDING" },
  "FX-05": { execution_status: "RUNNING", validity_status: "VALID", business_verdict: "PENDING", evidence_status: "UNVERIFIED", verification_status: "PENDING" },
  "FX-06": BASE_AXES,
  "FX-07": { execution_status: "COMPLETED", validity_status: "VALID", business_verdict: "PASS", evidence_status: "INCOMPLETE", verification_status: "NEEDS_REVIEW" },
  "FX-08": { execution_status: "BLOCKED", validity_status: "INVALID", business_verdict: "BLOCKED", evidence_status: "CONFLICTED", verification_status: "BLOCKED" },
  "FX-09": { execution_status: "RUNNING", validity_status: "VALID", business_verdict: "PENDING", evidence_status: "INCOMPLETE", verification_status: "PENDING" },
  "FX-10": { execution_status: "UNKNOWN", validity_status: "UNKNOWN", business_verdict: "UNKNOWN", evidence_status: "UNKNOWN", verification_status: "UNKNOWN" },
  "FX-11E": BASE_AXES,
  "FX-11L": BASE_AXES,
  "FX-11X": BASE_AXES,
  "FX-12": { execution_status: "COMPLETED", validity_status: "VALID", business_verdict: "PASS", evidence_status: "COMPLETE", verification_status: "PASS" }
};

export function axesFor(id) {
  const axes = AXES_BY_SCENARIO[id] || BASE_AXES;
  return Object.fromEntries(AXIS_ORDER.map((key) => [key, axes[key]]));
}

export const WORLD = {
  task: {
    id: "tsk-voice-001",
    display_id: "TSK-VOICE-001",
    title: "TCL001 唤醒词回归",
    subtitle: "小T小T · 噪声场景与串口恢复",
    stage: "FORMAL_RUNNING",
    current_revision_id: "rev-003",
    revision_number: 3,
    parent_revision_id: "rev-002",
    change_kind: "SCOPE_EXPANSION",
    content_digest: "sha256:5ac1d0f2…8b41",
    frozen_scope: "40 次正式采样 · 2 类噪声 · 串口恢复 3 次",
    blocker_owner: "资源调度 · Session Manager",
    updated_at: "2026-10-29 14:06:22 +08:00"
  },
  revisions: [
    { id: "rev-001", number: "R-1", title: "初始用例集", parent: null, change_kind: "INITIAL", status: "FROZEN", frozen_at: "2026-10-27 16:10 +08:00", digest: "sha256:1d70bc…22f0" },
    { id: "rev-002", number: "R-2", title: "增加串口恢复场景", parent: "rev-001", change_kind: "SCOPE_EXPANSION", status: "SUPERSEDED", frozen_at: "2026-10-28 10:02 +08:00", digest: "sha256:74e902…a13c" },
    { id: "rev-003", number: "R-3", title: "增加两类噪声场景", parent: "rev-002", change_kind: "SCOPE_EXPANSION", status: "APPROVED", frozen_at: "2026-10-29 11:18 +08:00", digest: "sha256:5ac1d0f2…8b41" },
    { id: "rev-004", number: "R-4", title: "候选：低温启动扩展", parent: "rev-003", change_kind: "DRAFT", status: "DRAFT", frozen_at: null, digest: null }
  ],
  approval: {
    approver_role: "APPROVER",
    approver_id: "approver-02",
    decision: "APPROVED",
    comment: "范围、证据要求与冻结摘要一致；允许进入 G3。",
    revision_content_digest: "sha256:5ac1d0f2…8b41",
    scope_snapshot: "40 次正式采样 · 2 类噪声 · 串口恢复 3 次",
    effective_at: "2026-10-29 11:20 +08:00",
    wait_timer: "已生效 2 小时 46 分",
    self_approval: false,
    prevent_self_review: true
  },
  cases: [
    { case_id: "case-voice-001", version: "v3", title: "唤醒词命中", oracle: "转写包含“小T小T”", required_evidence: ["audio_trace", "run_record"], mode: "formal", status: "ACTIVE" },
    { case_id: "case-voice-002", version: "v2", title: "误唤醒控制", oracle: "40 次采样中 false_trigger ≤ 1", required_evidence: ["audio_trace", "run_record"], mode: "formal", status: "ACTIVE" },
    { case_id: "case-voice-003", version: "v1", title: "串口恢复", oracle: "断开后 30 秒内恢复会话", required_evidence: ["serial_log", "manifest"], mode: "formal", status: "ACTIVE" },
    { case_id: "case-voice-004", version: "v1", title: "噪声鲁棒性", oracle: "两类噪声下命中率不低于基线", required_evidence: ["audio_trace", "run_record"], mode: "formal", status: "ACTIVE" },
    { case_id: "case-voice-005", version: "v1", title: "烟测预检", oracle: "端点可达且一次命中", required_evidence: ["manifest"], mode: "smoke", status: "REFERENCE_ONLY" }
  ],
  runs: [
    { id: "run-042", task_id: "tsk-voice-001", revision_id: "rev-003", mode: "formal", lifecycle_status: "RUNNING", denominator_eligible: true, attempts: 2, started_at: "2026-10-29 13:38:04 +08:00", last_heartbeat_at: "2026-10-29 14:06:19 +08:00", stop_requested_at: null, flaky_suspect: false },
    { id: "run-039", task_id: "tsk-voice-001", revision_id: "rev-003", mode: "smoke", lifecycle_status: "COMPLETED", denominator_eligible: false, attempts: 1, started_at: "2026-10-29 12:52:11 +08:00", last_heartbeat_at: "2026-10-29 13:04:47 +08:00", stop_requested_at: null, flaky_suspect: false },
    { id: "run-036", task_id: "tsk-voice-001", revision_id: "rev-003", mode: "static", lifecycle_status: "COMPLETED", denominator_eligible: false, attempts: 1, started_at: "2026-10-29 11:41:02 +08:00", last_heartbeat_at: "2026-10-29 11:43:19 +08:00", stop_requested_at: null, flaky_suspect: false },
    { id: "run-031", task_id: "tsk-voice-000", revision_id: "rev-006", mode: "formal", lifecycle_status: "COMPLETED", denominator_eligible: true, attempts: 1, started_at: "2026-10-28 15:10:00 +08:00", last_heartbeat_at: "2026-10-28 15:44:30 +08:00", stop_requested_at: null, flaky_suspect: false }
  ],
  attempts: [
    { id: "att-112", run_id: "run-042", ordinal: 2, retry_of: "att-111", status: "RUNNING", started_at: "2026-10-29 13:58:12 +08:00", flaky_suspect: false, node_observed: { heartbeat: "2026-10-29 14:06:19 +08:00", last_step: "playback_noise_burst", local_state: "RUNNING", used_for_decision: false } },
    { id: "att-111", run_id: "run-042", ordinal: 1, retry_of: null, status: "FAILED", failure_class: "transport_reset", started_at: "2026-10-29 13:38:04 +08:00", ended_at: "2026-10-29 13:55:40 +08:00", flaky_suspect: true, node_observed: { heartbeat: "2026-10-29 13:55:38 +08:00", last_step: "serial_reset", local_state: "FAILED", used_for_decision: false } },
    { id: "att-105", run_id: "run-039", ordinal: 1, retry_of: null, status: "COMPLETED", started_at: "2026-10-29 12:52:11 +08:00", ended_at: "2026-10-29 13:04:47 +08:00", flaky_suspect: false, node_observed: { heartbeat: "2026-10-29 13:04:46 +08:00", last_step: "smoke_complete", local_state: "COMPLETED", used_for_decision: false } }
  ],
  devices: [
    { id: "dev-tcl-001", label: "TCL001", identity: "ListenAIVCOM", pool_state: "ASSIGNED", health_state: "HEALTHY", serial_masked: "TCL…001", firmware: "V038", current_lease_id: "lease-7781", epoch: 7 },
    { id: "dev-tcl-002", label: "TCL002", identity: "ListenAIVCOM", pool_state: "AVAILABLE", health_state: "HEALTHY", serial_masked: "TCL…002", firmware: "V038", current_lease_id: null, epoch: 0 },
    { id: "dev-tcl-003", label: "TCL003", identity: "ListenAIVCOM", pool_state: "QUARANTINED", health_state: "QUARANTINED", serial_masked: "TCL…003", firmware: "V037", current_lease_id: "lease-7790", epoch: 4 },
    { id: "dev-tcl-004", label: "TCL004", identity: "ListenAIVCOM", pool_state: "DRAINING", health_state: "HEALTHY", serial_masked: "TCL…004", firmware: "V038", current_lease_id: "lease-7792", epoch: 2 }
  ],
  nodes: [
    { id: "node-lab-win-01", label: "实验室 Windows 节点 A", communication_state: "ONLINE", interactive_session: "ACTIVE", spool_state: "DRAINING", spool_pending: 2, last_heartbeat_at: "2026-10-29 14:06:19 +08:00", endpoints: ["Endpoint A · 串口", "Endpoint B · 音频采集"] },
    { id: "node-lab-win-02", label: "实验室 Windows 节点 B", communication_state: "OFFLINE", interactive_session: "UNKNOWN", spool_state: "STOPPED", spool_pending: 0, last_heartbeat_at: "2026-10-28 22:11:04 +08:00", endpoints: ["Endpoint C · 串口"] }
  ],
  reports: [
    { id: "rpt-voice-001", version: 3, title: "TCL001 唤醒词回归报告", task_id: "tsk-voice-001", lifecycle: "FROZEN", denominator: 40, created_at: "2026-10-29 15:20:00 +08:00", disclosure: "INTERNAL", sections: 14, evidence_index: 5 },
    { id: "rpt-static-004", version: 1, title: "静态检查汇总", task_id: "tsk-voice-001", lifecycle: "DRAFT", denominator: null, created_at: "2026-10-29 11:44:00 +08:00", disclosure: "INTERNAL", sections: 6, evidence_index: 2 }
  ],
  knowledge: [
    { id: "kn-wake-false-trigger", status: "APPROVED", title: "噪声段误唤醒阈值", applicability: "TCL001 · V038 · 两类噪声", summary: "在两类噪声下将误唤醒上限设为 1/40，需人工复核后用于新修订。", source_chain: ["run-031", "ev-noise-run-07", "review-006"], updated_at: "2026-10-28 17:02 +08:00" },
    { id: "kn-noise-profile", status: "CORROBORATED", title: "串口恢复时间基线", applicability: "TCL 系列 · V038", summary: "串口恢复中位数 12.4 秒，仍需更多样本佐证。", source_chain: ["run-036", "ev-serial-log-04"], updated_at: "2026-10-29 09:31 +08:00" },
    { id: "kn-legacy-flaky", status: "STALE", title: "旧版重试策略", applicability: "V036 及以前", summary: "基于旧固件的重试策略，已被当前基线取代，不得直接推广。", source_chain: ["run-018"], updated_at: "2026-09-12 10:15 +08:00" }
  ],
  candidates: [
    { id: "knc-014", status: "PROPOSED", title: "低温启动补偿", source_chain: ["run-031", "ev-noise-run-07"], applicability: "TCL001 · 环境温度 0–5°C", proposed_by: "AGENT_PLANNER", automatic_promotion_allowed: false, requires_human_review: true, updated_at: "2026-10-29 13:10 +08:00" },
    { id: "knc-012", status: "UNDER_REVIEW", title: "噪声突发前的静音窗口", source_chain: ["run-039", "ev-voice-trace-01"], applicability: "TCL001 · V038", proposed_by: "AGENT_PLANNER", automatic_promotion_allowed: false, requires_human_review: true, updated_at: "2026-10-29 12:02 +08:00" },
    { id: "knc-009", status: "NEEDS_INFO", title: "串口重连抖动分类", source_chain: ["run-042", "att-111"], applicability: "待补充样本", proposed_by: "AGENT_VERIFIER", automatic_promotion_allowed: false, requires_human_review: true, updated_at: "2026-10-29 10:44 +08:00" },
    { id: "knc-006", status: "APPROVED", title: "唤醒词基线阈值", source_chain: ["run-031"], applicability: "TCL001 · V038", proposed_by: "AGENT_PLANNER", automatic_promotion_allowed: false, requires_human_review: true, updated_at: "2026-10-28 17:00 +08:00" }
  ],
  agents: [
    { id: "agt-planner", name: "规划 Agent", role: "候选计划与用例生成", model_binding: "mb-plan-03", status: "ACTIVE", last_review: "2026-10-29 09:00 +08:00" },
    { id: "agt-runner-win", name: "Windows 执行 Agent", role: "只执行冻结工件并回传事实", model_binding: "mb-run-01", status: "ACTIVE", last_review: "2026-10-29 08:45 +08:00" },
    { id: "agt-verifier", name: "复核 Agent", role: "证据校验与 fail-closed 建议", model_binding: "mb-verify-02", status: "PAUSED", last_review: "2026-10-28 18:30 +08:00" }
  ],
  reviews: [
    { id: "revw-007", task_id: "tsk-voice-001", revision_id: "rev-003", stage: "PENDING", consensus: "2 / 3", open_risks: 1, updated_at: "2026-10-29 11:06 +08:00" },
    { id: "revw-006", task_id: "tsk-voice-000", revision_id: "rev-006", stage: "COMPLETED", consensus: "3 / 3", open_risks: 0, updated_at: "2026-10-28 16:58 +08:00" }
  ],
  audit: [
    { id: "aud-20261029-041", occurred_at: "2026-10-29 11:20:03 +08:00", actor_role: "APPROVER", action: "APPROVAL_GRANTED", object: "rev-003", access_decision: "ALLOW", integrity: "HASH_CHAIN_OK" },
    { id: "aud-20261029-040", occurred_at: "2026-10-29 11:18:44 +08:00", actor_role: "SESSION_MANAGER", action: "LEASE_GRANTED", object: "lease-7781", access_decision: "ALLOW", integrity: "HASH_CHAIN_OK" },
    { id: "aud-20261029-039", occurred_at: "2026-10-29 10:59:12 +08:00", actor_role: "OBSERVER", action: "EVIDENCE_ACCESS_DENIED", object: "ev-voice-trace-01", access_decision: "DENY", integrity: "HASH_CHAIN_OK" },
    { id: "aud-20261029-038", occurred_at: "2026-10-29 10:41:30 +08:00", actor_role: "ADMIN", action: "TOOLCHAIN_LOCK_CHANGED", object: "toolchain-lock-12", access_decision: "ALLOW", integrity: "HASH_CHAIN_OK" },
    { id: "aud-20261029-037", occurred_at: "2026-10-29 10:12:08 +08:00", actor_role: "SESSION_MANAGER", action: "RECONCILE_STARTED", object: "run-042", access_decision: "ALLOW", integrity: "HASH_CHAIN_OK" }
  ],
  runtime: {
    models: [
      { binding: "mb-plan-03", purpose: "候选计划", model: "planner-binding-v3", status: "LOCKED", drift: "NONE" },
      { binding: "mb-run-01", purpose: "节点执行", model: "runner-binding-v1", status: "LOCKED", drift: "NONE" },
      { binding: "mb-verify-02", purpose: "证据复核", model: "verifier-binding-v2", status: "LOCKED", drift: "NONE" },
      { binding: "mb-summary-01", purpose: "报告摘要", model: "summary-binding-v1", status: "DRIFT", drift: "VERSION_MISMATCH" }
    ],
    locks: [
      { name: "lstest", version: "1.8.2", lock: "LOCKED", checked_at: "2026-10-29 11:41 +08:00" },
      { name: "audio-harness", version: "0.9.4", lock: "DRIFT", checked_at: "2026-10-29 11:41 +08:00" },
      { name: "serial-adapter", version: "2.2.0", lock: "LOCKED", checked_at: "2026-10-29 11:41 +08:00" }
    ]
  },
  settings: {
    roles: [
      { role: "SUPER_ADMIN", scope: "全局", access: "ADMIN_ONLY", capability: "MANAGE_SETTINGS · MANAGE_ROLES" },
      { role: "SESSION_MANAGER", scope: "任务与设备", access: "TASK_AUTHORIZED", capability: "NODE_CONTROL · LEASE" },
      { role: "APPROVER", scope: "任务", access: "TASK_AUTHORIZED", capability: "APPROVE_TASK" },
      { role: "OBSERVER", scope: "任务", access: "SUMMARY_INDEX", capability: "READ_ONLY" }
    ],
    notifications: [
      { channel: "站内", target: "审批队列", delivery: "HEALTHY", dead_letter: 0 },
      { channel: "邮件", target: "已脱敏通讯组", delivery: "DEGRADED", dead_letter: 2 }
    ],
    retention: [
      { object: "审计事件", policy: "730 天 · 不可原地修改", version: "ret-04", effective_at: "2026-10-01" },
      { object: "证据元数据", policy: "365 天 · 删除走补偿事件", version: "ret-03", effective_at: "2026-09-15" },
      { object: "报告", policy: "冻结后长期保留", version: "ret-02", effective_at: "2026-08-20" }
    ]
  },
  intake: {
    drafts: [
      { id: "drf-009", title: "低温启动回归", entry_mode: "FORM", stage: "DRAFT", sources: 3, conflicts: 1, gaps: 2, updated_at: "2026-10-29 14:02 +08:00", owner_role: "Submitter" },
      { id: "drf-008", title: "噪声场景补充", entry_mode: "CONVERSATION", stage: "REVIEW", sources: 2, conflicts: 0, gaps: 1, updated_at: "2026-10-29 10:18 +08:00", owner_role: "Submitter" },
      { id: "drf-007", title: "串口恢复脚本", entry_mode: "FILE", stage: "DRAFT", sources: 4, conflicts: 2, gaps: 3, updated_at: "2026-10-28 17:44 +08:00", owner_role: "Submitter" }
    ]
  }
};

function linkState(flags) {
  const base = {
    communication_state: "ONLINE",
    occupancy_state: "OCCUPIED",
    execution_permit: "GRANTED",
    execution_status: "RUNNING",
    lease_state: "HELD",
    lease_id: "lease-7781",
    epoch: 7,
    pool_state: "ASSIGNED",
    health_state: "HEALTHY",
    freshness: {
      is_stale: false,
      last_authoritative_update: "2026-10-29 14:05:40 +08:00",
      last_known_at: "2026-10-29 14:06:19 +08:00"
    }
  };
  if (flags.blocked) {
    return { ...base, execution_status: "BLOCKED", execution_permit: "REVOKED", lease_state: "HELD" };
  }
  if (flags.stale) {
    return {
      ...base,
      freshness: {
        is_stale: true,
        last_authoritative_update: "2026-10-29 13:12:05 +08:00",
        last_known_at: "2026-10-29 14:06:19 +08:00"
      }
    };
  }
  if (flags.offline) {
    return { ...base, communication_state: "OFFLINE", execution_status: "RUNNING", occupancy_state: "OCCUPIED", execution_permit: "GRANTED" };
  }
  if (flags.reconciling) {
    return { ...base, communication_state: "DEGRADED", execution_status: "RUNNING", occupancy_state: "OCCUPIED", execution_permit: "GRANTED", stop_requested_at: "2026-10-29 14:02:44 +08:00" };
  }
  if (flags.quarantined) {
    return { ...base, pool_state: "QUARANTINED", health_state: "QUARANTINED", execution_status: "BLOCKED", execution_permit: "REVOKED" };
  }
  if (flags.draining) {
    return { ...base, pool_state: "DRAINING", execution_status: "RUNNING", occupancy_state: "OCCUPIED", execution_permit: "GRANTED" };
  }
  if (flags.noPermission) {
    return {
      ...base,
      communication_state: "UNKNOWN",
      occupancy_state: "UNKNOWN",
      execution_permit: "UNKNOWN",
      execution_status: "UNKNOWN",
      lease_state: "UNKNOWN",
      freshness: { is_stale: false, last_authoritative_update: null, last_known_at: null }
    };
  }
  if (flags.formalPass) {
    return { ...base, execution_status: "COMPLETED", occupancy_state: "RELEASED", execution_permit: "NONE", lease_state: "RELEASED" };
  }
  return base;
}

function releasePreconditions(flags) {
  if (flags.formalPass) {
    return { local_stop_confirmed: true, safe_cleanup_done: true, occupancy_reconciled: true, cleanup_receipt_id: "cln-2026-041", r05: "NODE_REACHABLE" };
  }
  if (flags.quarantined) {
    return { local_stop_confirmed: false, safe_cleanup_done: false, occupancy_reconciled: false, cleanup_receipt_id: null, r05: "NODE_REACHABLE" };
  }
  return { local_stop_confirmed: true, safe_cleanup_done: false, occupancy_reconciled: false, cleanup_receipt_id: null, r05: "NODE_REACHABLE" };
}

function progressFor(flags) {
  if (flags.unknownProgress) {
    return { mode: "INDETERMINATE", completed: null, total: null };
  }
  if (flags.formalPass) {
    return { mode: "COUNTS", completed: 40, total: 40 };
  }
  if (flags.draining) {
    return { mode: "COUNTS", completed: 12, total: 40 };
  }
  return { mode: "COUNTS", completed: 18, total: 40 };
}

function gatesFor(flags) {
  const base = [
    { code: "G0", name: "受理审阅", status: "PASSED", owner: "Submitter", note: "三入口来源已归一。" },
    { code: "G1", name: "冻结批准", status: "PASSED", owner: "Approver", note: "审批绑定内容摘要。" },
    { code: "G2", name: "静态检查", status: "PASSED", owner: "Platform", note: "static run 已完成。" },
    { code: "G3", name: "资源资格与租约", status: "PASSED", owner: "Session Manager", note: "lease-7781 / epoch 7。" },
    { code: "G4", name: "真机烟测", status: "PASSED", owner: "Operator", note: "独立 smoke run，不进入正式分母。" },
    { code: "G5", name: "正式采样", status: "IN_PROGRESS", owner: "Operator", note: "40 次正式采样进行中。" },
    { code: "G6", name: "证据复核与判定", status: "PENDING", owner: "Verifier", note: "等待证据完整。" },
    { code: "G7", name: "报告与知识", status: "PENDING", owner: "Approver", note: "判定后生成报告。" }
  ];
  if (flags.blocked) {
    return base.map((gate) => gate.code === "G3" ? { ...gate, status: "BLOCKED", note: "端点资格未满足，责任方为资源调度。" } : gate);
  }
  if (flags.quarantined) {
    return base.map((gate) => {
      if (gate.code === "G3") return { ...gate, status: "BLOCKED", note: "设备隔离，保持占用。" };
      if (gate.code === "G6") return { ...gate, status: "BLOCKED", note: "证据冲突，fail-closed。" };
      return gate;
    });
  }
  if (flags.reconciling) {
    return base.map((gate) => gate.code === "G5" ? { ...gate, status: "IN_PROGRESS", note: "待 STOP 处理完成后对账。" } : gate);
  }
  if (flags.noPermission) {
    return base.map((gate) => ({ ...gate, status: "UNKNOWN", note: "投影不可见。" }));
  }
  if (flags.formalPass) {
    return base.map((gate) => ({ ...gate, status: "PASSED", note: gate.note }));
  }
  return base;
}

function evidenceItems(flags) {
  const access = flags.noPermission ? "NO_ACCESS" : "EVIDENCE_AUTHORIZED";
  const items = [
    { id: "ev-voice-trace-01", label: "唤醒词音频轨迹", kind: "AUDIO_TRACE", size: "18.4 MB", digest: "sha256:9f2c41…a7d0", collected_at: "2026-10-29 13:42:08 +08:00", access_level: access, expected: true, received: true, verified: true, state: "VERIFIED" },
    { id: "ev-serial-log-04", label: "串口恢复日志", kind: "SERIAL_LOG", size: "2.1 MB", digest: "sha256:41bb0e…c918", collected_at: "2026-10-29 13:44:51 +08:00", access_level: access, expected: true, received: true, verified: false, state: "PARTIAL" },
    { id: "ev-manifest-02", label: "运行 manifest", kind: "MANIFEST", size: "12 KB", digest: "sha256:7d90af…23e1", collected_at: "2026-10-29 13:40:02 +08:00", access_level: "SUMMARY_INDEX", expected: true, received: true, verified: true, state: "VERIFIED" },
    { id: "ev-audio-ref-02", label: "参考音频基线", kind: "AUDIO_REFERENCE", size: "—", digest: "—", collected_at: "—", access_level: access, expected: true, received: false, verified: false, state: "DECLARED" },
    { id: "ev-noise-run-07", label: "噪声场景运行记录", kind: "RUN_RECORD", size: "4.8 MB", digest: "sha256:ce11b4…90fa", collected_at: "2026-10-29 14:02:19 +08:00", access_level: "SUMMARY_INDEX", expected: true, received: true, verified: flags.partialEvidence ? false : true, state: flags.partialEvidence ? "RECEIVED" : "VERIFIED" }
  ];
  if (flags.quarantined) {
    return items.map((item) => item.id === "ev-serial-log-04" ? { ...item, state: "QUARANTINED", verified: false } : item);
  }
  if (flags.formalPass) {
    return items.map((item) => ({ ...item, access_level: item.access_level === "NO_ACCESS" ? "SUMMARY_INDEX" : item.access_level, received: true, verified: true, state: "VERIFIED" }));
  }
  return items;
}

export function view(id = getScenarioId()) {
  const scenario = scenarioById(id);
  const flags = scenario.flags;
  const evidence = evidenceItems(flags);
  return {
    meta: FIXTURE_META,
    scenario,
    flags,
    axes: axesFor(scenario.id),
    link: linkState(flags),
    release: releasePreconditions(flags),
    progress: progressFor(flags),
    gates: gatesFor(flags),
    evidence,
    counts: {
      expected: evidence.filter((item) => item.expected).length,
      received: evidence.filter((item) => item.received).length,
      verified: evidence.filter((item) => item.verified).length
    },
    world: WORLD
  };
}
