// Pure semantic helpers. No DOM access, no inferred success.

export const AXIS_ORDER = [
  "execution_status",
  "validity_status",
  "business_verdict",
  "evidence_status",
  "verification_status"
];

export const AXIS_LABELS = {
  execution_status: "执行",
  validity_status: "有效性",
  business_verdict: "业务判定",
  evidence_status: "证据",
  verification_status: "复核"
};

export const FORMAL_PASS = Object.freeze({
  execution_status: "COMPLETED",
  validity_status: "VALID",
  business_verdict: "PASS",
  evidence_status: "COMPLETE",
  verification_status: "PASS"
});

export function isFormalPass(axes) {
  if (!axes) return false;
  return AXIS_ORDER.every((key) => axes[key] === FORMAL_PASS[key]);
}

const TONE_BY_VALUE = {
  COMPLETED: "success",
  SUCCEEDED: "success",
  PASSED: "success",
  SUCCESS: "success",
  OK: "success",
  RECOGNIZED: "success",
  EXPECTED: "neutral",
  RELEASED: "neutral",
  PENDING: "neutral",
  QUEUED: "neutral",
  WAITING: "neutral",
  PAUSED: "neutral",
  STOPPED: "neutral",
  NONE: "neutral",
  UNKNOWN: "neutral",
  OFFLINE: "neutral",
  BLOCKED: "neutral",
  DRAINING: "attention",
  DEGRADED: "attention",
  STALE: "attention",
  NEEDS_REVIEW: "attention",
  INCOMPLETE: "attention",
  UNVERIFIED: "attention",
  RUNNING: "action",
  VERIFYING: "action",
  RECONCILING: "action",
  GRANTED: "action",
  ONLINE: "success",
  VALID: "success",
  PASS: "success",
  COMPLETE: "success",
  VERIFIED: "success",
  INVALID: "danger",
  FAIL: "danger",
  FAILED: "danger",
  TIMEOUT: "danger",
  CONFLICTED: "danger",
  QUARANTINED: "danger",
  DENIED: "danger"
};

export function axisTone(value) {
  return TONE_BY_VALUE[value] || "neutral";
}

export function progressModel(progress) {
  const mode = progress && progress.mode ? progress.mode : "INDETERMINATE";
  if (mode === "COUNTS" && Number.isFinite(progress.completed) && Number.isFinite(progress.total) && progress.total > 0) {
    const percent = Math.max(0, Math.min(100, Math.round((progress.completed / progress.total) * 100)));
    return {
      mode,
      percent,
      known: true,
      label: `${progress.completed} / ${progress.total}`,
      caption: "仅计数模式显示百分比，不作为完成度承诺"
    };
  }
  if (mode === "QUALITATIVE") {
    return { mode, percent: null, known: false, label: "定性阶段", caption: "服务端未提供已批准分母" };
  }
  return { mode: "INDETERMINATE", percent: null, known: false, label: "未知", caption: "未知总量，禁止显示百分比" };
}

export function releaseModel(preconditions) {
  const pre = preconditions || {};
  const done = Boolean(pre.local_stop_confirmed && pre.safe_cleanup_done && pre.occupancy_reconciled);
  return {
    state: done ? "RELEASED" : "HELD",
    done,
    items: [
      {
        key: "local_stop_confirmed",
        label: "本地停止已确认",
        value: Boolean(pre.local_stop_confirmed),
        note: pre.local_stop_confirmed ? "节点已确认停止后续动作" : "等待节点停止回执"
      },
      {
        key: "safe_cleanup_done",
        label: "安全清理完成",
        value: Boolean(pre.safe_cleanup_done),
        note: pre.safe_cleanup_done ? "清理回执已记录" : "缺少 cleanup_receipt，保持占用"
      },
      {
        key: "occupancy_reconciled",
        label: "占用已对账",
        value: Boolean(pre.occupancy_reconciled),
        note: pre.occupancy_reconciled ? "lease / epoch / occupancy 已对账" : "对账完成前不得释放或重派"
      }
    ]
  };
}

export function verdictLabel(axes) {
  if (isFormalPass(axes)) return "正式 PASS";
  if (axes && axes.business_verdict === "PASS" && axes.evidence_status !== "COMPLETE") {
    return "不可正式 PASS";
  }
  if (axes && axes.business_verdict === "BLOCKED") return "BLOCKED";
  if (axes && ["RUNNING", "PENDING", "UNKNOWN"].includes(axes.execution_status)) return "未形成正式判定";
  return "非正式判定";
}

export function denominatorEligible(run) {
  return Boolean(run && run.mode === "formal" && run.denominator_eligible);
}

export function freshnessLabel(freshness) {
  if (!freshness) return "UNKNOWN";
  return freshness.is_stale ? "STALE" : "FRESH";
}

export function offlineCombination(entity) {
  const communication = entity && entity.communication_state;
  const execution = entity && entity.execution_status;
  const occupancy = entity && entity.occupancy_state;
  const permit = entity && entity.execution_permit;
  return communication === "OFFLINE" && execution === "RUNNING" && occupancy === "OCCUPIED" && permit === "GRANTED";
}

export function disabledReasonForOperation(area) {
  if (area === "RT" || area === "AG") {
    return "访问级别待 Q-09 裁决；裁决前不实现写入。";
  }
  return "原型只读：未连接服务端，写操作不生效。";
}

// ---------------------------------------------------------------------------
// Test campaign outcome
// ---------------------------------------------------------------------------
//
// A campaign is not a Task and is not one of the five formal axes.  Its
// outcome is a display projection over the deterministic test result:
//
// * FAILED / TIMEOUT / STOPPED never become PASS, even if a stale summary
//   happens to contain pass tokens.
// * RUNNING never becomes PASS while the node is still executing.
// * PASS is derived only from an explicit verdict, or from SUCCEEDED plus a
//   complete summary whose status_counts account for every requested round and
//   contain only pass tokens (for wake-recognition the pass token is
//   RECOGNIZED).
// * A missing/oversized summary stays "verdict not provided" instead of being
//   inferred into a success.

const CAMPAIGN_PASS_TOKENS = new Set([
  "PASS", "PASSED", "SUCCESS", "SUCCEEDED", "OK", "RECOGNIZED"
]);
const CAMPAIGN_FAIL_TOKENS = new Set([
  "FAIL", "FAILED", "ERROR", "ERRORED", "TIMEOUT", "REJECTED",
  "UNRECOGNIZED", "NO_RECOGNITION", "MISS"
]);
const CAMPAIGN_ACTIVE_STATUSES = new Set(["QUEUED", "SENT", "RUNNING"]);
const CAMPAIGN_FAILURE_STATUSES = new Set(["FAILED", "TIMEOUT", "STOPPED"]);

function count(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? Math.trunc(parsed) : fallback;
}

function campaignCounts(campaign) {
  const summary = campaign && typeof campaign.summary === "object" && campaign.summary
    ? campaign.summary
    : {};
  const raw = campaign && typeof campaign.status_counts === "object" && campaign.status_counts
    ? campaign.status_counts
    : summary.status_counts;
  return raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
}

export function campaignOutcome(campaign) {
  const source = campaign && typeof campaign === "object" ? campaign : {};
  const status = String(source.status || "").toUpperCase();
  const explicit = String(source.verdict || "").toUpperCase();
  // Lifecycle wins over a stale/incorrect verdict: a FAILED or RUNNING campaign
  // is never promoted to PASS by an explicit summary field.
  if (CAMPAIGN_ACTIVE_STATUSES.has(status)) {
    return {
      verdict: null,
      label: "进行中",
      tone: "action",
      derived: false,
      basis: `命令 ${source.command_status || status}`
    };
  }
  if (CAMPAIGN_FAILURE_STATUSES.has(status)) {
    return {
      verdict: "FAIL",
      label: "FAIL",
      tone: "danger",
      derived: false,
      basis: source.error_code || source.command_status || status
    };
  }
  if (explicit === "PASS" || explicit === "FAIL") {
    return {
      verdict: explicit,
      label: explicit,
      tone: explicit === "PASS" ? "success" : "danger",
      derived: false,
      basis: source.verdict_basis || "服务端 verdict"
    };
  }
  if (status === "SUCCEEDED") {
    const counts = campaignCounts(source);
    const total = count(
      source.total_rounds,
      count(source.expected_rounds, count(source.rounds, 0))
    );
    const completed = count(
      source.completed_rounds,
      count(source.rounds_count, 0)
    );
    let passCount = 0;
    let failCount = 0;
    for (const [key, value] of Object.entries(counts)) {
      const token = String(key || "").toUpperCase();
      const amount = count(value, 0);
      if (CAMPAIGN_PASS_TOKENS.has(token)) passCount += amount;
      if (CAMPAIGN_FAIL_TOKENS.has(token)) failCount += amount;
    }
    if (total > 0 && completed === total && failCount === 0 && passCount === total) {
      return {
        verdict: "PASS",
        label: "PASS",
        tone: "success",
        derived: true,
        basis: `summary.status_counts ${passCount}/${total}`
      };
    }
    if (total > 0 && failCount > 0) {
      return {
        verdict: "FAIL",
        label: "FAIL",
        tone: "danger",
        derived: true,
        basis: `summary.status_counts FAIL ${failCount}/${total}`
      };
    }
    return {
      verdict: null,
      label: "判定未提供",
      tone: "neutral",
      derived: false,
      basis: "命令 SUCCEEDED；summary 未给出完整逐轮计数"
    };
  }
  return {
    verdict: null,
    label: status || "UNKNOWN",
    tone: axisTone(status),
    derived: false,
    basis: source.error_code || "状态未知"
  };
}
