import {
  badge,
  genericState,
  kv,
  link,
  pageHeader,
  panel,
  progressBar,
  stateBanners,
  stats,
  statusBadge,
  table,
  timeline,
  button
} from "../components.js";

export function render({ view }) {
  const { flags, world, axes, progress, link: linkState } = view;
  const head = pageHeader({
    eyebrow: `Mission Control · MC-01 · ${view.scenario.id}`,
    title: "平台健康与需要我处理",
    description: "只呈现异常、待决断、离线、对账中与隔离设备，不做全量监控墙。完整清单下钻到任务、运行与设备。",
    actions: button("新建任务", { href: "/console/intake/new", kind: "primary", icon: "plus" }) +
      button("查看运行", { href: "/console/runs", icon: "runs" })
  });
  const generic = genericState(view, "Mission Control");
  if (generic) return head + generic;

  const actionCount = 1 +
    (flags.blocked ? 1 : 0) +
    (flags.pendingStop || flags.reconciling ? 1 : 0) +
    (flags.quarantined ? 1 : 0) +
    (flags.stale ? 1 : 0);

  const actionItems = [];
  if (flags.blocked) {
    actionItems.push({ title: "G3 资源资格阻塞", note: "端点资格未满足；解除前禁止派发。责任方：资源调度 · Session Manager。", href: "/console/tasks/tsk-voice-001/verdict", tone: "danger", label: "BLOCKED" });
  }
  if (flags.reconciling) {
    actionItems.push({ title: "待 STOP 与占用对账", note: "先处理待 STOP，再停止后续动作、补传、去重、对账、恢复领取。", href: "/console/runs/run-042", tone: "attention", label: "RECONCILING" });
  }
  if (flags.quarantined) {
    actionItems.push({ title: "隔离设备仍被占用", note: "缺少清理回执，保持 OCCUPIED；释放前置未满足。", href: "/console/devices/dev-tcl-003", tone: "danger", label: "QUARANTINED" });
  }
  if (flags.stale) {
    actionItems.push({ title: "投影陈旧", note: "最后权威更新落后；陈旧只追加徽章，不改写执行或占用。", href: "/console/tasks/tsk-voice-001/overview", tone: "attention", label: "STALE" });
  }
  actionItems.push({ title: "证据复核待处理", note: "serial_log 已接收但未核验；G6 尚未完成。", href: "/console/tasks/tsk-voice-001/evidence", tone: "attention", label: "NEEDS REVIEW" });

  const actionBody = `<div class="checks">${actionItems.map((item) => `
    <div class="check-item is-${item.tone === "danger" ? "missing" : "unknown"}">
      <div style="min-width:0">
        <div class="spread"><a href="#${item.href}"><strong>${item.title}</strong></a>${badge(item.label, item.tone)}</div>
        <span class="check-note">${item.note}</span>
      </div>
    </div>`).join("")}</div>`;

  const run = world.runs[0];
  const runBody = `
    <div class="spread" style="margin-bottom:10px">
      <div><a class="mono" href="#/console/runs/${run.id}">${run.id}</a><div class="caption">${world.task.title} · ${world.task.current_revision_id}</div></div>
      <div class="row">${badge(run.mode.toUpperCase(), run.mode === "formal" ? "action" : "plain")}${statusBadge(run.lifecycle_status)}</div>
    </div>
    ${kv([
      ["执行 execution", statusBadge(axes.execution_status)],
      ["通信 communication", statusBadge(linkState.communication_state)],
      ["占用 occupancy", statusBadge(linkState.occupancy_state)],
      ["许可 permit", statusBadge(linkState.execution_permit)]
    ])}
    <div style="margin-top:12px">${progressBar(progress)}</div>
    <p class="caption" style="margin-top:8px">正式分母资格：${run.denominator_eligible ? "eligible" : "not eligible"} · 烟测与模拟永不进入正式分母。</p>
  `;

  const node = world.nodes[0];
  const healthBody = kv([
    ["节点通信", statusBadge(flags.offline ? "OFFLINE" : node.communication_state)],
    ["设备池", `${badge("1 ASSIGNED", "neutral")} ${badge(flags.quarantined ? "1 QUARANTINED" : "1 AVAILABLE", flags.quarantined ? "danger" : "neutral")}`],
    ["spool", `${statusBadge(node.spool_state)} · pending ${node.spool_pending}`],
    ["陈旧投影", flags.stale ? badge("STALE", "attention", "clock") : badge("FRESH", "neutral", "clock")],
    ["最后权威更新", `<span class="mono">${linkState.freshness.last_authoritative_update || "UNKNOWN"}</span>`]
  ]) + `<p style="margin-top:10px"><a href="#/console/devices">打开设备与节点</a></p>`;

  const taskBody = table({
    head: ["任务", "阶段", "当前修订", "阻塞方", "进度"],
    rows: [[
      `<a href="#/console/tasks/${world.task.id}/overview"><span class="cell-primary">${world.task.title}</span></a><div class="caption mono">${world.task.display_id}</div>`,
      statusBadge(world.task.stage),
      `<span class="mono">${world.task.current_revision_id}</span> · R-${world.task.revision_number}`,
      world.task.blocker_owner,
      `${progress.mode === "COUNTS" ? `${progress.completed} / ${progress.total}` : "未知"}`
    ]]
  });

  const stopTimeline = flags.pendingStop
    ? timeline([
      { title: "待 STOP 已登记，尚未送达节点", time: "14:02:44", body: "不得显示为已停止；等待节点回执。", state: "current" },
      { title: "停止后续动作", body: "节点确认后停止新动作。", state: "blocked" },
      { title: "补传与去重", body: "补传离线期间事实，去重后再对账。", state: "blocked" },
      { title: "占用对账", body: "对账完成前保持 OCCUPIED，禁止新派发。", state: "blocked" },
      { title: "恢复领取", body: "仅在四项完成后恢复。", state: "blocked" }
    ])
    : `<p class="muted small">当前没有待 STOP 或对账范围。此处为空不代表节点无风险。</p>`;

  return `
    ${head}
    ${stateBanners(view)}
    ${stats([
      { label: "需要我处理", value: String(actionCount), note: "含证据复核待办" },
      { label: "运行中", value: "1", note: "formal · run-042" },
      { label: "待 STOP", value: String(flags.pendingStop || flags.reconciling ? 1 : 0), note: "未送达不算已停止" },
      { label: "隔离设备", value: String(flags.quarantined ? 1 : 0), note: "保持占用" }
    ])}
    <div class="layout-3" style="margin-top:16px">
      ${panel({ title: "需要我处理", note: "按风险排序，不做监控墙", body: actionBody })}
      ${panel({ title: "运行中", note: "五轴与四信号分离", body: runBody })}
      ${panel({ title: "平台健康", note: "异常优先，正常项折叠", body: healthBody })}
    </div>
    ${panel({ title: "任务快照", note: "仅显示与异常相关的任务", body: taskBody, flush: true })}
    ${panel({ title: "待 STOP 与对账", note: "固定顺序；对账完成前保持占用", body: stopTimeline })}
    <p class="caption" style="margin-top:16px">${view.meta && view.meta.server_authoritative ? "control-plane API" : `fixture ${view.scenario.id}`} · source=${view.meta && view.meta.source ? view.meta.source : "prototype-fixture"} · server_authoritative=${view.meta && view.meta.server_authoritative ? "true" : "false"} · 非冻结</p>
  `;
}
