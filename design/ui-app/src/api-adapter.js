// Adapter: control-plane read models -> the existing fixture-shaped page view.
//
// The fixture projection stays the base so every page keeps its full shape even
// when an endpoint returns only one collection.  API keys are overlaid with
// explicit, per-entity mappers; nothing is inferred into a PASS and
// NOT_EVALUATED / NOT_RUN always survive as written by the server.

import { AXIS_ORDER, isFormalPass } from "./semantics.js";
import { can } from "./roles.js";

const AXIS_KEYS = AXIS_ORDER;
const GATE_NAMES = {
  G0: "受理审阅",
  G1: "冻结批准",
  G2: "静态检查",
  G3: "资源资格与租约",
  G4: "真机烟测",
  G5: "正式采样",
  G6: "证据复核与判定",
  G7: "报告与知识"
};
function firstDefined(...values) {
  for (const value of values) {
    if (value !== undefined && value !== null) return value;
  }
  return undefined;
}

function text(value, fallback = "—") {
  if (value === undefined || value === null || value === "") return fallback;
  return String(value);
}

function list(value) {
  return Array.isArray(value) ? value : null;
}

function looksLikeEvidence(items) {
  if (!Array.isArray(items) || !items.length) return false;
  return items.every((item) => item && (item.evidence_id || item.evidence_class || typeof item.expected === "boolean"));
}

function byId(items, id) {
  if (!Array.isArray(items) || !id) return null;
  return items.find((item) => item && (item.id === id || item.display_id === id)) || null;
}

function humanBytes(size) {
  if (!Number.isFinite(size)) return "—";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function maskSerial(id) {
  const raw = text(id, "");
  if (!raw) return "—";
  return raw.length <= 6 ? raw : `${raw.slice(0, 3)}…${raw.slice(-3)}`;
}

function axisSource(data) {
  if (data.axes && typeof data.axes === "object") return data.axes;
  if (AXIS_KEYS.every((key) => typeof data[key] === "string")) return data;
  for (const nested of [data.task, data.run, data.verdict, data.item, data.attempt]) {
    if (nested && nested.axes && typeof nested.axes === "object") return nested.axes;
    if (nested && AXIS_KEYS.every((key) => typeof nested[key] === "string")) return nested;
  }
  return null;
}

function normalizeAxes(data, base) {
  const source = axisSource(data);
  if (!source) return base.axes;
  const axes = { ...base.axes };
  for (const key of AXIS_KEYS) {
    const value = source[key];
    // Copy the server value verbatim.  NOT_EVALUATED / NOT_RUN are never
    // rewritten, and a lone PASS axis can never become a formal PASS because
    // isFormalPass requires the exact five-axis tuple.
    if (typeof value === "string" && value) axes[key] = value;
  }
  return axes;
}

function normalizeLink(data, base) {
  const signal = data.link || data.signals || data.run || data.attempt || {};
  const link = { ...base.link };
  const pairs = [
    ["communication_state", firstDefined(signal.communication_state, data.communication_state)],
    ["occupancy_state", firstDefined(signal.occupancy_state, data.occupancy_state)],
    ["execution_permit", firstDefined(signal.execution_permit, data.execution_permit)],
    ["execution_status", firstDefined(signal.execution_status, data.execution_status, signal.axes?.execution_status)],
    ["lease_state", firstDefined(data.lease?.state, signal.lease_state)],
    ["lease_id", firstDefined(data.lease?.display_id, data.lease?.lease_id, signal.lease_id)],
    ["epoch", firstDefined(data.lease?.epoch, signal.lease_epoch, signal.epoch)],
    ["pool_state", firstDefined(data.device?.pool_state, signal.pool_state)],
    ["health_state", firstDefined(data.device?.health_state, signal.health_state)]
  ];
  for (const [key, value] of pairs) {
    if (value !== undefined && value !== null) link[key] = value;
  }
  const freshness = data.freshness || signal.freshness;
  if (freshness && typeof freshness === "object") {
    link.freshness = {
      ...base.link.freshness,
      is_stale: Boolean(freshness.is_stale),
      last_authoritative_update: firstDefined(
        freshness.last_authoritative_update,
        freshness.last_known_at,
        base.link.freshness.last_authoritative_update
      ),
      last_known_at: firstDefined(freshness.last_known_at, base.link.freshness.last_known_at)
    };
  }
  return link;
}

function normalizeRelease(data, base) {
  if (!data.release || typeof data.release !== "object") return base.release;
  const release = { ...base.release };
  const preconditions = data.release.preconditions || {};
  for (const key of ["local_stop_confirmed", "safe_cleanup_done", "occupancy_reconciled"]) {
    if (typeof preconditions[key] === "boolean") release[key] = preconditions[key];
  }
  if (data.release.release_state) release.release_state = data.release.release_state;
  // The read model does not project a cleanup receipt.  Never inherit the
  // fixture receipt when authoritative release facts are present.
  release.cleanup_receipt_id = firstDefined(
    data.release.cleanup_receipt_id,
    data.lease && data.lease.cleanup_receipt_id,
    null
  );
  release.r05 = firstDefined(data.release.r05, data.lease && data.lease.r05, null);
  return release;
}

function normalizeProgress(data, base) {
  const progress = data.progress;
  if (!progress || typeof progress !== "object") return base.progress;
  if (progress.mode === "COUNTS" && Number.isFinite(progress.total) && progress.total > 0) {
    return {
      mode: "COUNTS",
      completed: Number.isFinite(progress.completed) ? progress.completed : 0,
      total: progress.total
    };
  }
  return { mode: "INDETERMINATE", completed: null, total: null };
}

function normalizeCounts(data, evidence, base) {
  const source = data.counts || data.evidence_counts;
  if (source && typeof source === "object") {
    return {
      expected: Number(source.expected) || 0,
      received: Number(source.received) || 0,
      verified: Number(source.verified) || 0
    };
  }
  if (evidence) {
    return {
      expected: evidence.filter((item) => item.expected).length,
      received: evidence.filter((item) => item.received).length,
      verified: evidence.filter((item) => item.verified).length
    };
  }
  return base.counts;
}

function evidenceStatusFor(item) {
  if (item.evidence_status) return item.evidence_status;
  if (item.state === "conflicted") return "CONFLICTED";
  if (item.state === "quarantined" || item.state === "unavailable") return "INCOMPLETE";
  if (item.verified && item.state === "verified") return "COMPLETE";
  if (item.received) return "UNVERIFIED";
  return "INCOMPLETE";
}

function mapAccessLevel(value) {
  const raw = String(value || "").toLowerCase();
  if (!raw || raw === "none" || raw === "no_access") return "NO_ACCESS";
  if (raw.includes("summary")) return "SUMMARY_INDEX";
  if (raw.includes("evidence") || raw.includes("raw")) return "EVIDENCE_AUTHORIZED";
  return text(value);
}

function mapEvidenceItem(item, baseEvidence) {
  const base = byId(baseEvidence, item.display_id || item.evidence_id) || {};
  const status = evidenceStatusFor(item);
  let state = base.state || "DECLARED";
  if (item.state === "quarantined" || status === "CONFLICTED") state = item.state === "quarantined" ? "QUARANTINED" : "CONFLICTED";
  else if (status === "COMPLETE") state = "VERIFIED";
  else if (status === "UNVERIFIED") state = "PARTIAL";
  else if (!item.received) state = "DECLARED";
  return {
    ...base,
    id: text(firstDefined(item.display_id, item.evidence_id), base.id),
    label: text(firstDefined(item.label, item.role, item.evidence_class), base.label || "证据项"),
    kind: text(firstDefined(item.evidence_class, item.kind), base.kind || "EVIDENCE").toUpperCase(),
    size: firstDefined(item.size, base.size, humanBytes(item.size_bytes)),
    digest: text(firstDefined(item.content_digest, item.digest), "—"),
    collected_at: text(firstDefined(item.collected_at, item.created_at), "—"),
    access_level: firstDefined(item.access_level ? mapAccessLevel(item.access_level) : undefined, base.access_level, "SUMMARY_INDEX"),
    expected: item.expected === undefined ? Boolean(base.expected) : Boolean(item.expected),
    received: item.received === undefined ? Boolean(base.received) : Boolean(item.received),
    verified: item.verified === undefined ? Boolean(base.verified) : Boolean(item.verified),
    state,
    evidence_status: status
  };
}

function mapGate(gate, baseGates) {
  const code = text(firstDefined(gate.gate_code, gate.code), "G?");
  const base = (baseGates || []).find((item) => item.code === code) || {};
  const blockers = Array.isArray(gate.blockers) ? gate.blockers : [];
  return {
    ...base,
    code,
    name: firstDefined(gate.name, base.name, GATE_NAMES[code], code),
    status: text(firstDefined(gate.status, base.status), "UNKNOWN"),
    owner: text(firstDefined(gate.blocker_owner, base.owner), "—"),
    note: text(firstDefined(gate.notes, blockers[0], base.note), "—")
  };
}

function mapTask(source, baseTask, baseRevisions) {
  const summary = source && source.task ? source.task : source;
  if (!summary) return baseTask;
  const revisionNumber = firstDefined(summary.revision_number, baseTask.revision_number);
  const baseRevision = (baseRevisions || []).find((item) => item.number === `R-${revisionNumber}`);
  return {
    ...baseTask,
    id: text(firstDefined(summary.display_id, summary.task_id), baseTask.id),
    display_id: text(firstDefined(summary.display_id, summary.task_id), baseTask.display_id),
    title: text(firstDefined(summary.title, baseTask.title), baseTask.title),
    stage: text(firstDefined(summary.status, summary.latest_run_lifecycle, baseTask.stage), baseTask.stage),
    current_revision_id: text(
      firstDefined(summary.current_revision_display_id, baseRevision && baseRevision.id, summary.current_revision_id, baseTask.current_revision_id),
      baseTask.current_revision_id
    ),
    revision_number: revisionNumber,
    change_kind: firstDefined(summary.change_kind, baseTask.change_kind),
    content_digest: firstDefined(summary.content_digest, summary.current_revision?.content_digest, baseTask.content_digest),
    frozen_scope: firstDefined(summary.frozen_scope, summary.current_revision?.frozen_scope, baseTask.frozen_scope),
    updated_at: text(firstDefined(summary.updated_at, baseTask.updated_at), baseTask.updated_at)
  };
}

function mapRevision(revision, baseRevisions) {
  const id = text(firstDefined(revision.display_id, revision.revision_id));
  const base = byId(baseRevisions, id) || {};
  const number = firstDefined(revision.revision_number, base.revision_number, 0);
  return {
    ...base,
    id,
    number: `R-${number}`,
    title: text(firstDefined(revision.change_reason, revision.title, base.title), `修订 ${number}`),
    parent: firstDefined(revision.parent_display_id, base.parent, revision.parent_revision_id, null),
    change_kind: text(firstDefined(revision.change_kind, base.change_kind), "—"),
    status: text(firstDefined(revision.status, base.status), "UNKNOWN"),
    frozen_at: firstDefined(revision.frozen_at, base.frozen_at, null),
    digest: firstDefined(revision.content_digest, base.digest, null)
  };
}

function mapApproval(approval, baseApproval) {
  if (!approval) return baseApproval;
  return {
    ...baseApproval,
    approver_role: firstDefined(approval.role, baseApproval.approver_role, "APPROVER"),
    approver_id: text(firstDefined(approval.approver_display_id, approval.approver_id), baseApproval.approver_id),
    decision: text(firstDefined(approval.decision, baseApproval.decision), "—"),
    comment: text(firstDefined(approval.comment, baseApproval.comment), "—"),
    revision_content_digest: text(firstDefined(approval.revision_content_digest, baseApproval.revision_content_digest), "—"),
    scope_snapshot: text(firstDefined(approval.scope_snapshot, baseApproval.scope_snapshot), "—"),
    effective_at: text(firstDefined(approval.effective_at, approval.decided_at, baseApproval.effective_at), "—"),
    wait_timer: Number.isFinite(approval.wait_timer_seconds)
      ? `${approval.wait_timer_seconds} 秒`
      : baseApproval.wait_timer,
    self_approval: firstDefined(approval.self_approval, baseApproval.self_approval),
    prevent_self_review: firstDefined(approval.prevent_self_review, baseApproval.prevent_self_review)
  };
}

function mapCase(testCase, baseCases) {
  const id = text(firstDefined(testCase.display_id, testCase.case_id));
  const base = byId(baseCases, id) || {};
  const evidence = Array.isArray(testCase.required_evidence) ? testCase.required_evidence : [];
  const oracles = Array.isArray(testCase.assertion_refs) ? testCase.assertion_refs : [];
  return {
    ...base,
    case_id: id,
    version: text(firstDefined(testCase.case_version, base.version), "—"),
    title: text(firstDefined(testCase.name, testCase.title, base.title), id),
    oracle: text(firstDefined(testCase.oracle, oracles[0], base.oracle), "由冻结用例定义"),
    required_evidence: evidence.length ? evidence : base.required_evidence || [],
    mode: text(firstDefined(testCase.run_mode, testCase.mode, base.mode), "—"),
    status: text(firstDefined(testCase.status, base.status), "UNKNOWN")
  };
}

function mapRun(run, baseRuns) {
  const id = text(firstDefined(run.display_id, run.run_id));
  const base = byId(baseRuns, id) || {};
  return {
    ...base,
    id,
    task_id: firstDefined(base.task_id, run.task_display_id, run.task_id, "—"),
    revision_id: firstDefined(base.revision_id, run.revision_display_id, run.revision_id, "—"),
    mode: text(firstDefined(run.mode, base.mode), "—"),
    lifecycle_status: text(firstDefined(run.lifecycle_status, base.lifecycle_status), "UNKNOWN"),
    denominator_eligible: Boolean(
      firstDefined(run.formal_denominator_eligible, run.denominator_eligible, base.denominator_eligible)
    ),
    attempts: Array.isArray(run.attempts)
      ? run.attempts.length
      : Number(firstDefined(run.attempt_count, base.attempts, 0)),
    started_at: text(firstDefined(run.started_at, base.started_at), "—"),
    last_heartbeat_at: text(firstDefined(run.last_heartbeat_at, base.last_heartbeat_at), "—"),
    stop_requested_at: firstDefined(run.stop_requested_at, base.stop_requested_at, null),
    flaky_suspect: Boolean(firstDefined(run.flaky_suspect, base.flaky_suspect))
  };
}

function mapAttempt(attempt, baseAttempts, runId) {
  const id = text(firstDefined(attempt.display_id, attempt.attempt_id));
  const base = byId(baseAttempts, id) || {};
  const facts = Array.isArray(attempt.facts) ? attempt.facts : [];
  const lastFact = facts.length ? facts[facts.length - 1] : null;
  const lastStep = typeof lastFact === "string"
    ? lastFact
    : firstDefined(lastFact && lastFact.step, lastFact && lastFact.name, lastFact && lastFact.event);
  return {
    ...base,
    id,
    run_id: firstDefined(runId, base.run_id, attempt.run_display_id, attempt.run_id, "—"),
    ordinal: Number(firstDefined(attempt.attempt_ordinal, base.ordinal, 0)),
    retry_of: firstDefined(base.retry_of, attempt.retry_of_display_id, attempt.retry_of_attempt_id, null),
    status: text(firstDefined(attempt.execution_status, attempt.status, base.status), "UNKNOWN"),
    started_at: text(firstDefined(attempt.started_at, base.started_at), "—"),
    flaky_suspect: Boolean(firstDefined(attempt.flaky_suspect, base.flaky_suspect)),
    failure_class: firstDefined(attempt.failure_classification, attempt.failure_class, base.failure_class, null),
    node_observed: base.node_observed || {
      heartbeat: text(firstDefined(attempt.finished_at, attempt.started_at), "—"),
      last_step: text(lastStep, "—"),
      local_state: text(firstDefined(attempt.execution_status, base.status), "UNKNOWN"),
      used_for_decision: false
    }
  };
}

function mapDevice(device, baseDevices) {
  const id = text(firstDefined(device.display_id, device.device_id));
  const base = byId(baseDevices, id) || {};
  return {
    ...base,
    id,
    label: text(firstDefined(base.label, device.identity, device.display_id), id),
    identity: text(firstDefined(device.identity, base.identity, device.display_id), id),
    pool_state: text(firstDefined(device.pool_state, base.pool_state), "UNKNOWN"),
    health_state: text(firstDefined(device.health_state, base.health_state), "UNKNOWN"),
    serial_masked: text(firstDefined(base.serial_masked, maskSerial(id)), "—"),
    firmware: text(firstDefined(device.firmware_version, device.firmware, base.firmware), "—"),
    current_lease_id: firstDefined(
      device.current_lease?.display_id,
      device.current_lease_id && base.current_lease_id,
      device.current_lease_id,
      base.current_lease_id,
      null
    ),
    epoch: Number(firstDefined(device.current_lease?.epoch, device.epoch, base.epoch, 0)),
    communication_state: firstDefined(device.communication_state, base.communication_state),
    occupancy_state: firstDefined(device.occupancy_state, base.occupancy_state)
  };
}

function mapNode(node, baseNodes) {
  const id = text(firstDefined(node.display_id, node.node_id));
  const base = byId(baseNodes, id) || {};
  const spool = node.spool && typeof node.spool === "object" ? node.spool : {};
  return {
    ...base,
    id,
    label: text(firstDefined(base.label, node.hostname, node.display_id), id),
    communication_state: text(firstDefined(node.communication_state, base.communication_state), "UNKNOWN"),
    interactive_session: text(firstDefined(node.interactive_session, base.interactive_session), "UNKNOWN"),
    spool_state: text(firstDefined(spool.state, node.spool_state, node.status, base.spool_state), "UNKNOWN"),
    spool_pending: Number(firstDefined(spool.pending, node.spool_pending, base.spool_pending, 0)),
    last_heartbeat_at: text(firstDefined(node.last_heartbeat_at, base.last_heartbeat_at), "—"),
    endpoints: list(node.capabilities) || node.endpoints || base.endpoints || []
  };
}

function mapDraft(draft, baseDrafts) {
  const id = text(firstDefined(draft.display_id, draft.draft_id));
  const base = byId(baseDrafts, id) || {};
  return {
    ...base,
    id,
    title: text(firstDefined(draft.title, base.title), id),
    entry_mode: text(firstDefined(draft.entry_mode, base.entry_mode), "—").toUpperCase(),
    stage: text(firstDefined(draft.stage, base.stage), "UNKNOWN"),
    sources: Number(firstDefined(draft.source_count, base.sources, 0)),
    conflicts: Number(firstDefined(draft.conflict_count, base.conflicts, 0)),
    gaps: Number(firstDefined(draft.gap_count, base.gaps, 0)),
    updated_at: text(firstDefined(draft.updated_at, base.updated_at), "—"),
    owner_role: text(firstDefined(draft.owner_role, base.owner_role), "—")
  };
}

function mapReport(report, baseReports) {
  const id = text(firstDefined(report.display_id, report.report_id));
  const base = byId(baseReports, id) || {};
  return {
    ...base,
    id,
    version: Number(firstDefined(report.version, base.version, 0)),
    title: text(firstDefined(report.title, base.title), id),
    task_id: firstDefined(base.task_id, report.task_display_id, report.task_id, "—"),
    lifecycle: text(firstDefined(report.lifecycle, base.lifecycle), "UNKNOWN"),
    denominator: firstDefined(report.denominator, base.denominator, null),
    created_at: text(firstDefined(report.created_at, report.frozen_at, base.created_at), "—"),
    disclosure: text(firstDefined(report.disclosure, base.disclosure), "—"),
    sections: Number(firstDefined(report.sections, base.sections, 0)),
    evidence_index: Number(firstDefined(report.evidence_index_count, report.evidence_index, base.evidence_index, 0))
  };
}

function mapKnowledge(item, baseItems) {
  const id = text(firstDefined(item.display_id, item.knowledge_id));
  const base = byId(baseItems, id) || {};
  return {
    ...base,
    id,
    status: text(firstDefined(item.status, base.status), "UNKNOWN"),
    title: text(firstDefined(item.title, base.title), id),
    applicability: text(firstDefined(item.applicability, base.applicability), "—"),
    summary: text(firstDefined(item.summary, base.summary), "—"),
    source_chain: list(item.source_chain) || base.source_chain || [],
    updated_at: text(firstDefined(item.updated_at, base.updated_at), "—")
  };
}

function mapCandidate(candidate, baseCandidates) {
  const id = text(firstDefined(candidate.display_id, candidate.candidate_id));
  const base = byId(baseCandidates, id) || {};
  return {
    ...base,
    id,
    status: text(firstDefined(candidate.status, base.status), "UNKNOWN"),
    title: text(firstDefined(candidate.title, base.title), id),
    source_chain: list(candidate.source_chain) || base.source_chain || [],
    applicability: text(firstDefined(candidate.applicability, base.applicability), "—"),
    proposed_by: text(firstDefined(candidate.proposed_by, base.proposed_by), "—"),
    automatic_promotion_allowed: Boolean(
      firstDefined(candidate.automatic_promotion_allowed, base.automatic_promotion_allowed)
    ),
    requires_human_review: Boolean(firstDefined(candidate.requires_human_review, base.requires_human_review)),
    updated_at: text(firstDefined(candidate.updated_at, base.updated_at), "—")
  };
}

function mapAgent(agent, baseAgents) {
  const id = text(firstDefined(agent.display_id, agent.agent_id));
  const base = byId(baseAgents, id) || {};
  return {
    ...base,
    id,
    name: text(firstDefined(agent.name, base.name), id),
    role: text(firstDefined(agent.role, base.role), "—"),
    model_binding: text(firstDefined(agent.model_binding, base.model_binding), "—"),
    status: text(firstDefined(agent.status, base.status), "UNKNOWN"),
    last_review: text(firstDefined(agent.last_review, base.last_review), "—")
  };
}

function mapReview(review, baseReviews) {
  const id = text(firstDefined(review.display_id, review.review_id));
  const base = byId(baseReviews, id) || {};
  return {
    ...base,
    id,
    task_id: firstDefined(review.task_display_id, base.task_id, review.task_id, "—"),
    revision_id: firstDefined(review.revision_display_id, base.revision_id, review.revision_id, "—"),
    stage: text(firstDefined(review.stage, base.stage), "UNKNOWN"),
    consensus: text(firstDefined(review.consensus, base.consensus), "—"),
    open_risks: Number(firstDefined(review.open_risks, base.open_risks, 0)),
    updated_at: text(firstDefined(review.updated_at, base.updated_at), "—")
  };
}

function mapAudit(event, baseAudit) {
  const id = text(firstDefined(event.event_id, event.id));
  const base = byId(baseAudit, id) || {};
  return {
    ...base,
    id,
    occurred_at: text(firstDefined(event.occurred_at, base.occurred_at), "—"),
    actor_role: text(firstDefined(event.actor_role, base.actor_role), "—"),
    action: text(firstDefined(event.action, base.action), "—"),
    object: text(firstDefined(event.object_id, event.object, base.object), "—"),
    access_decision: text(firstDefined(event.access_decision, base.access_decision), "UNKNOWN"),
    integrity: text(firstDefined(event.integrity, base.integrity), "NOT_VERIFIED")
  };
}

function mapVerdict(verdict) {
  return {
    id: text(firstDefined(verdict.display_id, verdict.verdict_id)),
    subject: text(firstDefined(verdict.subject, verdict.task_display_id, verdict.task_id), "—"),
    execution: text(firstDefined(verdict.execution_status, verdict.axes?.execution_status), "UNKNOWN"),
    validity: text(firstDefined(verdict.validity_status, verdict.axes?.validity_status), "UNKNOWN"),
    business: text(firstDefined(verdict.business_verdict, verdict.axes?.business_verdict), "UNKNOWN"),
    evidence: text(firstDefined(verdict.evidence_status, verdict.axes?.evidence_status), "UNKNOWN"),
    verification: text(firstDefined(verdict.verification_status, verdict.axes?.verification_status), "UNKNOWN"),
    scope: text(firstDefined(verdict.denominator, verdict.scope), "—"),
    updated: text(firstDefined(verdict.decided_at, verdict.updated_at), "—")
  };
}

function replaceArray(baseItems, mapped, idKey = "id") {
  if (!mapped || !mapped.length) return baseItems || [];
  const copy = (baseItems || []).slice();
  for (const item of mapped) {
    const index = copy.findIndex((entry) => entry[idKey] === item[idKey]);
    if (index >= 0) copy[index] = item;
    else copy.push(item);
  }
  return copy;
}

function applyCollections(routeId, data, world, baseEvidence) {
  const next = { ...world };
  const evidenceBase = Array.isArray(world.evidence) ? world.evidence : (baseEvidence || []);
  const runs = list(data.runs);
  const runItems = list(data.items);
  const attempts = list(data.attempts);

  switch (routeId) {
    case "MC-01": {
      if (runs) next.runs = runs.map((run) => mapRun(run, world.runs));
      if (list(data.nodes)) next.nodes = data.nodes.map((node) => mapNode(node, world.nodes));
      if (list(data.devices)) next.devices = data.devices.map((device) => mapDevice(device, world.devices));
      if (list(data.tasks) && data.tasks[0]) next.task = mapTask(data.tasks[0], world.task, world.revisions);
      break;
    }
    case "IN-01":
    case "IN-02": {
      if (runItems) next.intake = { ...world.intake, drafts: runItems.map((draft) => mapDraft(draft, world.intake.drafts)) };
      break;
    }
    case "IN-03": {
      const draft = data.draft || data;
      if (draft && (draft.display_id || draft.draft_id)) {
        next.intake = { ...world.intake, drafts: replaceArray(world.intake.drafts, [mapDraft(draft, world.intake.drafts)]) };
      }
      break;
    }
    case "TK-01": {
      if (runItems && runItems[0]) next.task = mapTask(runItems[0], world.task, world.revisions);
      break;
    }
    case "TK-02":
    case "TK-03":
    case "TK-04":
    case "TK-05":
    case "TK-06":
    case "TK-07":
    case "TK-08":
    case "TK-09": {
      if (data.task || data.display_id || data.task_id) {
        next.task = mapTask(data.task || data, world.task, world.revisions);
      }
      if (list(data.revisions)) {
        next.revisions = data.revisions.map((revision) => mapRevision(revision, world.revisions));
      }
      if (data.approval) next.approval = mapApproval(data.approval, world.approval);
      if (list(data.cases)) next.cases = data.cases.map((testCase) => mapCase(testCase, world.cases));
      if (list(data.gates)) next.gates = data.gates.map((gate) => mapGate(gate, world.gates));
      if (runs) next.runs = replaceArray(world.runs, runs.map((run) => mapRun(run, world.runs)));
      if (list(data.knowledge)) next.knowledge = data.knowledge.map((item) => mapKnowledge(item, world.knowledge));
      if (list(data.candidates)) next.candidates = data.candidates.map((candidate) => mapCandidate(candidate, world.candidates));
      if (attempts) {
        const runId = next.task && next.task.id;
        next.attempts = replaceArray(world.attempts, attempts.map((attempt) => mapAttempt(attempt, world.attempts, runId)));
      }
      if (data.run) next.runs = replaceArray(next.runs || world.runs, [mapRun(data.run, world.runs)]);
      if (data.attempt) {
        const runId = data.run ? text(firstDefined(data.run.display_id, data.run.run_id)) : undefined;
        next.attempts = replaceArray(world.attempts, [mapAttempt(data.attempt, world.attempts, runId)]);
      }
      if (data.node) next.nodes = replaceArray(world.nodes, [mapNode(data.node, world.nodes)]);
      if (data.device) next.devices = replaceArray(world.devices, [mapDevice(data.device, world.devices)]);
      break;
    }
    case "RN-01": {
      if (runItems) next.runs = runItems.map((run) => mapRun(run, world.runs));
      break;
    }
    case "RN-02": {
      if (data.display_id || data.run_id) next.runs = replaceArray(world.runs, [mapRun(data, world.runs)]);
      if (attempts) {
        const runId = text(firstDefined(data.display_id, data.run_id));
        next.attempts = replaceArray(world.attempts, attempts.map((attempt) => mapAttempt(attempt, world.attempts, runId)));
      }
      if (data.node) next.nodes = replaceArray(world.nodes, [mapNode(data.node, world.nodes)]);
      if (data.device) next.devices = replaceArray(world.devices, [mapDevice(data.device, world.devices)]);
      break;
    }
    case "RN-03": {
      if (data.display_id || data.attempt_id) {
        const runId = data.run ? text(firstDefined(data.run.display_id, data.run.run_id)) : undefined;
        next.attempts = replaceArray(world.attempts, [mapAttempt(data, world.attempts, runId)]);
      }
      if (data.run) next.runs = replaceArray(world.runs, [mapRun(data.run, world.runs)]);
      break;
    }
    case "EV-01": {
      if (runItems) next.evidence = runItems.map((item) => mapEvidenceItem(item, evidenceBase));
      break;
    }
    case "EV-02": {
      if (data.item || data.display_id || data.evidence_id) {
        next.evidence = replaceArray(evidenceBase, [mapEvidenceItem(data.item || data, evidenceBase)]);
      }
      if (data.run) next.runs = replaceArray(world.runs, [mapRun(data.run, world.runs)]);
      if (data.attempt) next.attempts = replaceArray(world.attempts, [mapAttempt(data.attempt, world.attempts)]);
      break;
    }
    case "EV-03": {
      if (runItems) next.verdicts = runItems.map(mapVerdict);
      break;
    }
    case "DV-01": {
      if (runItems) next.devices = runItems.map((device) => mapDevice(device, world.devices));
      if (list(data.nodes)) next.nodes = data.nodes.map((node) => mapNode(node, world.nodes));
      break;
    }
    case "DV-02": {
      if (data.display_id || data.device_id) next.devices = replaceArray(world.devices, [mapDevice(data, world.devices)]);
      if (data.node) next.nodes = replaceArray(world.nodes, [mapNode(data.node, world.nodes)]);
      if (data.run) next.runs = replaceArray(world.runs, [mapRun(data.run, world.runs)]);
      break;
    }
    case "DV-03": {
      if (data.display_id || data.node_id) next.nodes = replaceArray(world.nodes, [mapNode(data, world.nodes)]);
      if (list(data.devices)) next.devices = data.devices.map((device) => mapDevice(device, world.devices));
      break;
    }
    case "RP-01": {
      if (runItems) next.reports = runItems.map((report) => mapReport(report, world.reports));
      break;
    }
    case "RP-02": {
      if (data.display_id || data.report_id) next.reports = replaceArray(world.reports, [mapReport(data, world.reports)]);
      break;
    }
    case "KN-01": {
      if (runItems) next.knowledge = runItems.map((item) => mapKnowledge(item, world.knowledge));
      break;
    }
    case "KN-02": {
      if (data.item || data.display_id || data.knowledge_id) {
        next.knowledge = replaceArray(world.knowledge, [mapKnowledge(data.item || data, world.knowledge)]);
      }
      break;
    }
    case "KN-03": {
      if (runItems) next.candidates = runItems.map((candidate) => mapCandidate(candidate, world.candidates));
      break;
    }
    case "RT-01": {
      if (runItems) next.runtime = { ...world.runtime, models: runItems };
      break;
    }
    case "RT-02": {
      if (runItems) next.runtime = { ...world.runtime, locks: runItems };
      break;
    }
    case "AG-01": {
      if (runItems) next.agents = runItems.map((agent) => mapAgent(agent, world.agents));
      break;
    }
    case "AG-02": {
      if (data.agent || data.display_id || data.agent_id) {
        next.agents = replaceArray(world.agents, [mapAgent(data.agent || data, world.agents)]);
      }
      break;
    }
    case "AG-03": {
      if (runItems) next.reviews = runItems.map((review) => mapReview(review, world.reviews));
      break;
    }
    case "AU-01": {
      if (runItems) next.audit = runItems.map((event) => mapAudit(event, world.audit));
      break;
    }
    case "AU-02": {
      if (data.event || data.event_id) next.audit = replaceArray(world.audit, [mapAudit(data.event || data, world.audit)]);
      break;
    }
    case "AU-03": {
      if (list(data.events)) next.audit = data.events.map((event) => mapAudit(event, world.audit));
      break;
    }
    case "ST-01": {
      const categories = data.categories || {};
      const settings = { ...world.settings };
      if (Array.isArray(categories.notification)) settings.notifications = mapNotifications(categories.notification);
      if (Array.isArray(categories.retention)) settings.retention = mapRetention(categories.retention);
      next.settings = settings;
      break;
    }
    case "ST-02": {
      const settings = { ...world.settings };
      if (list(data.roles)) settings.roles = data.roles.map(mapRole);
      next.settings = settings;
      break;
    }
    case "ST-03": {
      const settings = { ...world.settings };
      if (runItems) settings.notifications = mapNotifications(runItems);
      next.settings = settings;
      break;
    }
    case "ST-04": {
      const settings = { ...world.settings };
      if (runItems) settings.retention = mapRetention(runItems);
      next.settings = settings;
      break;
    }
    default:
      break;
  }
  return next;
}

function mapRole(role) {
  return {
    role: text(firstDefined(role.role_code, role.role), "—"),
    scope: text(role.scope, "—"),
    access: text(firstDefined(role.access_level, role.access), "—"),
    capability: (list(role.capabilities) || []).join(" · ") || text(role.capability, "—")
  };
}

function mapNotifications(items) {
  return items.map((item) => {
    const value = item.value && typeof item.value === "object" ? item.value : item;
    return {
      channel: text(firstDefined(item.channel, value.channel), "—"),
      target: text(firstDefined(item.target, value.target), "—"),
      delivery: text(firstDefined(item.delivery, value.delivery), "UNKNOWN"),
      dead_letter: Number(firstDefined(item.dead_letter, value.dead_letter, 0))
    };
  });
}

function mapRetention(items) {
  return items.map((item) => {
    const value = item.value && typeof item.value === "object" ? item.value : item;
    return {
      object: text(firstDefined(item.object, value.object), "—"),
      policy: text(firstDefined(item.policy, value.policy), "—"),
      version: text(firstDefined(item.version, value.version), "—"),
      effective_at: text(firstDefined(item.effective_at, value.effective_at), "—")
    };
  });
}

function deriveFlags(baseFlags, axes, link, progress, data) {
  const runs = [data.run, ...(list(data.runs) || []), ...(list(data.items) || [])]
    .filter((item) => item && typeof item === "object" && "lifecycle_status" in item);
  const devices = [data.device, ...(list(data.devices) || []), ...(list(data.items) || [])]
    .filter((item) => item && typeof item === "object" && item.pool_state);
  const run = runs.find((item) => item.stop_requested_at) || runs[0] || {};
  const reconciliation = data.reconciliation && typeof data.reconciliation === "object"
    ? data.reconciliation
    : {};
  return {
    ...baseFlags,
    empty: false,
    loading: false,
    error: false,
    blocked: axes.execution_status === "BLOCKED",
    offline: link.communication_state === "OFFLINE",
    stale: Boolean(link.freshness && link.freshness.is_stale),
    reconciling: link.communication_state === "DEGRADED"
      || Number(reconciliation.reconciling_run_count || 0) > 0,
    pendingStop: Boolean(run.stop_requested_at)
      || Number(reconciliation.pending_stop_count || 0) > 0,
    quarantined: devices.some((device) => device.pool_state === "QUARANTINED"),
    draining: devices.some((device) => device.pool_state === "DRAINING"),
    unknownProgress: progress.mode === "INDETERMINATE",
    partialEvidence: axes.evidence_status === "UNVERIFIED",
    noPermission: !can("CREATE_TASK"),
    formalPass: isFormalPass(axes)
  };
}

export function adaptRouteView(route, params, payload, base) {
  const envelope = payload && typeof payload === "object" ? payload : {};
  const data = envelope.data && typeof envelope.data === "object" ? envelope.data : {};
  const axes = normalizeAxes(data, base);
  const link = normalizeLink(data, base);
  const release = normalizeRelease(data, base);
  const progress = normalizeProgress(data, base);

  let evidence = base.evidence;
  const evidencePayload = list(data.evidence) || (looksLikeEvidence(data.items) ? data.items : null);
  if (evidencePayload) evidence = evidencePayload.map((item) => mapEvidenceItem(item, base.evidence));

  const gates = list(data.gates) && data.gates.length
    ? data.gates.map((gate) => mapGate(gate, base.gates))
    : base.gates;

  const world = applyCollections(route.id, data, base.world, base.evidence);
  const counts = normalizeCounts(data, evidence === base.evidence ? null : evidence, base);
  const flags = deriveFlags(base.flags, axes, link, progress, data);

  return {
    ...base,
    meta: {
      ...base.meta,
      ...(envelope.meta && typeof envelope.meta === "object" ? envelope.meta : {}),
      server_authoritative: true
    },
    flags,
    axes,
    link,
    release,
    progress,
    gates,
    evidence,
    counts,
    world
  };
}
