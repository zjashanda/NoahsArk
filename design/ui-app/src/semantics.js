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
  COMPLETED: "neutral",
  EXPECTED: "neutral",
  RELEASED: "neutral",
  PENDING: "neutral",
  NONE: "neutral",
  UNKNOWN: "neutral",
  OFFLINE: "neutral",
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
  BLOCKED: "danger",
  INVALID: "danger",
  FAIL: "danger",
  FAILED: "danger",
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
