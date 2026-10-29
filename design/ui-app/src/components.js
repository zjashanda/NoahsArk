// Shared HTML component primitives. All output is static markup.

import { icon } from "./icons.js";
import { can, inferCapability, roleReason } from "./roles.js";
import {
  AXIS_LABELS,
  AXIS_ORDER,
  axisTone,
  isFormalPass,
  progressModel,
  releaseModel,
  verdictLabel
} from "./semantics.js";

export function esc(value) {
  return String(value == null ? "" : value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function link(path, label, className = "") {
  const cls = className ? ` class="${className}"` : "";
  return `<a href="#${esc(path)}"${cls}>${label}</a>`;
}

export function badge(text, tone = "neutral", glyph = null) {
  const glyphHtml = glyph ? icon(glyph, "badge-glyph") : "";
  return `<span class="badge tone-${esc(tone)}">${glyphHtml}${esc(text)}</span>`;
}

export function statusBadge(value) {
  return badge(value, axisTone(value));
}

export function button(label, options = {}) {
  const classes = ["btn"];
  if (options.kind) classes.push(`btn-${options.kind}`);
  if (options.small) classes.push("btn-sm");
  const cls = classes.join(" ");
  const glyph = options.icon ? icon(options.icon) : "";
  if (options.href) {
    return `<a class="${cls}" href="#${esc(options.href)}">${glyph}${label}</a>`;
  }
  const capability = options.cap || inferCapability(label);
  const disabledReason = options.disabledReason
    || (capability && !can(capability) ? roleReason(capability) : "");
  if (disabledReason) {
    return `<button type="button" class="${cls}" aria-disabled="true" disabled title="${esc(disabledReason)}">${glyph}${label}</button><span class="btn-reason">${esc(disabledReason)}</span>`;
  }
  const attrs = [
    `data-action="${esc(options.action || "mock")}"`,
    `data-label="${esc(options.label || label)}"`,
    options.title ? `data-title="${esc(options.title)}"` : "",
    options.message ? `data-message="${esc(options.message)}"` : "",
    options.confirmLabel ? `data-confirm-label="${esc(options.confirmLabel)}"` : "",
    options.result ? `data-result="${esc(options.result)}"` : ""
  ].filter(Boolean).join(" ");
  return `<button type="button" class="${cls}" ${attrs}>${glyph}${label}</button>`;
}

export function pageHeader({ eyebrow, title, description, actions = "" }) {
  return `
    <header class="page-head">
      <div class="page-head-main">
        <div class="eyebrow">${eyebrow}</div>
        <h1 class="page-title">${title}</h1>
        ${description ? `<p class="page-desc">${description}</p>` : ""}
      </div>
      ${actions ? `<div class="page-actions">${actions}</div>` : ""}
    </header>
  `;
}

export function panel({ title, note = "", actions = "", body, flush = false, footer = "" }) {
  return `
    <section class="panel">
      <header class="panel-head">
        <div>
          <h2 class="panel-title">${title}</h2>
          ${note ? `<p class="panel-note">${note}</p>` : ""}
        </div>
        ${actions ? `<div class="panel-actions">${actions}</div>` : ""}
      </header>
      <div class="panel-body${flush ? " flush" : ""}">${body}</div>
      ${footer ? `<footer class="panel-foot">${footer}</footer>` : ""}
    </section>
  `;
}

export function section(title, body, note = "") {
  return `
    <section class="section">
      <div class="section-head">
        <h2 class="section-title">${title}</h2>
        ${note ? `<span class="section-note">${note}</span>` : ""}
      </div>
      ${body}
    </section>
  `;
}

export function stats(items) {
  return `<div class="stats">${items.map((item) => `
    <div class="stat">
      <div class="stat-label">${item.label}</div>
      <div class="stat-value">${item.value}</div>
      ${item.note ? `<div class="stat-note">${item.note}</div>` : ""}
    </div>`).join("")}</div>`;
}

export function kv(rows) {
  return `<dl class="kv">${rows.map(([label, value]) => `
    <div class="kv-row"><dt>${label}</dt><dd>${value}</dd></div>`).join("")}</dl>`;
}

export function table({ head, rows, caption = "" }) {
  const headHtml = head.map((cell) => `<th scope="col">${cell}</th>`).join("");
  const bodyHtml = rows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`).join("");
  return `
    <div class="table-wrap">
      <table class="table">
        ${caption ? `<caption>${caption}</caption>` : ""}
        <thead><tr>${headHtml}</tr></thead>
        <tbody>${bodyHtml}</tbody>
      </table>
    </div>
  `;
}

export function axisMatrix(axes, options = {}) {
  const cells = AXIS_ORDER.map((key) => `
    <div class="axis">
      <span class="axis-label">${AXIS_LABELS[key]} · ${key}</span>
      <span class="axis-value">${statusBadge(axes[key] || "UNKNOWN")}</span>
    </div>`).join("");
  const note = options.note ? `<p class="axes-note">${options.note}</p>` : "";
  return `<div class="axes" role="group" aria-label="五轴状态">${cells}</div>${note}`;
}

export function verdictBanner(axes) {
  if (isFormalPass(axes)) {
    return `<div class="formal-pass">${icon("check")}<span>正式 PASS · 五轴精确满足 <span class="mono">COMPLETED / VALID / PASS / COMPLETE / PASS</span></span></div>`;
  }
  const reason = axes.business_verdict === "PASS" && axes.evidence_status !== "COMPLETE"
    ? "业务判定为 PASS，但证据未 COMPLETE，因此不可显示正式 PASS。"
    : `当前五轴不满足正式 PASS 的唯一精确组合；判定为「${verdictLabel(axes)}」。`;
  return `<div class="fail-closed">${icon("alert")}<div><strong>不可正式 PASS</strong> · ${reason} ` +
    `正式 PASS 仅允许 <span class="mono">COMPLETED / VALID / PASS / COMPLETE / PASS</span>。</div></div>`;
}

export function stateBanners(view) {
  const { flags, link } = view;
  const blocks = [];
  if (flags.blocked) {
    blocks.push(banner("blocked", "BLOCKED", "任务在 G3 资源资格被阻塞，责任方为资源调度 · Session Manager。解除前禁止派发或标记通过。"));
  }
  if (flags.offline) {
    blocks.push(banner("offline", "OFFLINE", "通信离线，但执行仍在 RUNNING、设备仍 OCCUPIED、执行许可 GRANTED。离线不等于停止、空闲或可重派。"));
  }
  if (flags.stale) {
    blocks.push(banner("stale", "STALE", `投影已陈旧：最后权威更新 ${esc(link.freshness.last_authoritative_update)}；最后已知活动 ${esc(link.freshness.last_known_at)}。陈旧徽章只追加，不改写执行或占用。`));
  }
  if (flags.reconciling) {
    blocks.push(banner("reconciling", "RECONCILING", "存在待送达 STOP。固定顺序：处理待 STOP → 停止后续动作 → 补传 → 去重 → 对账 → 恢复领取。对账完成前保持占用。"));
  }
  if (flags.quarantined) {
    blocks.push(banner("quarantined", "QUARANTINED", "设备已隔离且仍被占用；释放前置未满足，必须人工恢复并完成清理回执。"));
  }
  if (flags.draining) {
    blocks.push(banner("draining", "DRAINING", "设备进入排空：不再接受新任务，已有运行继续，直到停止与对账完成。"));
  }
  if (flags.unknownProgress) {
    blocks.push(banner("unknown", "UNKNOWN", "进度模式为 INDETERMINATE；总量未知，不显示 0%、99% 或阶段序号百分比。"));
  }
  if (flags.partialEvidence) {
    blocks.push(banner("partial", "PARTIAL EVIDENCE", "证据已接收但未全部核验；received 不等于 verified，业务 PASS 也不能形成正式 PASS。"));
  }
  if (flags.noPermission) {
    blocks.push(banner("blocked", "NO PERMISSION", "当前角色只能查看只读摘要；受限动作保留可见但禁用，并显示原因。客户端隐藏不构成访问控制。"));
  }
  return blocks.join("");
}

function banner(kind, title, text) {
  const glyph = kind === "offline" ? "offline" : kind === "quarantined" || kind === "blocked" ? "shield" : kind === "reconciling" ? "refresh" : kind === "partial" ? "alert" : "alert";
  return `<div class="banner banner-${kind}" role="status">${icon(glyph, "banner-icon")}<div class="banner-body"><strong>${title}</strong> · ${text}</div></div>`;
}

export function stateBlock(kind, options = {}) {
  const map = {
    empty: { title: "暂无记录", note: "当前筛选范围没有可显示的投影。空态不代表平台无数据。", glyph: "file" },
    loading: { title: "正在加载投影", note: "等待 Linux 控制面返回只读快照；不推断成功。", glyph: "refresh" },
    error: { title: "投影加载失败", note: "保留错误状态和重试入口，不把失败写成空数据。", glyph: "alert" },
    "no-permission": { title: "仅可查看摘要", note: "原始证据需要 EVIDENCE_AUTHORIZED；拒绝访问也会写入审计。", glyph: "lock" }
  };
  const item = map[kind] || map.empty;
  const title = options.title || item.title;
  const note = options.note || item.note;
  const body = kind === "loading"
    ? `<div style="width:min(360px,80%)"><div class="skeleton" style="width:92%"></div><div class="skeleton" style="width:74%"></div><div class="skeleton" style="width:58%"></div></div>`
    : "";
  return `<div class="state-block">${icon(item.glyph, "state-icon")}<div class="state-title">${esc(title)}</div><div class="state-note">${esc(note)}</div>${body}</div>`;
}

export function genericState(view, label = "投影") {
  if (view.flags.loading) return stateBlock("loading", { title: `正在加载${label}`, note: "等待只读投影；不推断成功或完成。" });
  if (view.flags.error) return stateBlock("error", { title: `${label}加载失败`, note: "错误状态保留，重试入口可见；不把失败写成空数据。" });
  if (view.flags.empty) return stateBlock("empty", { title: `暂无${label}`, note: "当前筛选范围为空；空态不代表平台无数据。" });
  return "";
}

export function progressBar(progress) {
  const model = progressModel(progress);
  if (!model.known) {
    return `<div class="progress-unknown" role="img" aria-label="进度未知"></div>
      <div class="progress-label"><span>${esc(model.label)}</span><span>${esc(model.caption)}</span></div>`;
  }
  return `<div class="progress" role="progressbar" aria-valuenow="${model.percent}" aria-valuemin="0" aria-valuemax="100"><span style="--progress-value:${model.percent}%"></span></div>
    <div class="progress-label"><span>${esc(model.label)} · ${model.percent}%</span><span>${esc(model.caption)}</span></div>`;
}

export function leasePanel(view) {
  const { link } = view;
  return kv([
    ["通信状态 communication", statusBadge(link.communication_state)],
    ["占用状态 occupancy", statusBadge(link.occupancy_state)],
    ["执行许可 permit", statusBadge(link.execution_permit)],
    ["执行状态 execution", statusBadge(link.execution_status)],
    ["租约 lease", `${statusBadge(link.lease_state)} <span class="mono">${esc(link.lease_id || "—")}</span>`],
    ["租约 epoch", `<span class="mono">${esc(link.epoch)}</span>`],
    ["新鲜度 freshness", link.freshness.is_stale ? badge("STALE", "attention", "clock") : badge("FRESH", "neutral", "clock")],
    ["最后权威更新", esc(link.freshness.last_authoritative_update || "UNKNOWN")],
    ["最后已知活动", esc(link.freshness.last_known_at || "UNKNOWN")]
  ]);
}

export function releaseChecklist(view) {
  const model = releaseModel(view.release);
  const items = model.items.map((item) => `
    <div class="check-item ${item.value ? "is-done" : "is-missing"}">
      ${icon(item.value ? "check" : "x", "check-icon")}
      <div><strong>${esc(item.label)}</strong><span class="check-note">${esc(item.note)}</span></div>
    </div>`).join("");
  const receipt = view.release.cleanup_receipt_id
    ? `<p class="caption">cleanup_receipt: <span class="mono">${esc(view.release.cleanup_receipt_id)}</span></p>`
    : `<p class="caption">cleanup_receipt: 缺失 → 保持 OCCUPIED，不得确认释放。</p>`;
  return `
    <div class="spread" style="margin-bottom:10px">
      <span class="secondary small">release_state</span>
      ${model.done ? badge("RELEASED", "neutral", "check") : badge("HELD", "neutral", "lock")}
    </div>
    <div class="checks">${items}</div>
    ${receipt}
    <p class="caption" style="margin-top:8px">释放仅取决于三项前置与 R-05；释放不等于 PASS，也不等待最终判定。</p>
  `;
}

export function gateList(gates) {
  const rows = gates.map((gate) => {
    const tone = gate.status === "BLOCKED" || gate.status === "FAILED" ? "danger"
      : gate.status === "IN_PROGRESS" ? "action"
      : gate.status === "PENDING" || gate.status === "UNKNOWN" ? "neutral" : "success";
    const current = gate.status === "IN_PROGRESS" ? " is-current" : gate.status === "BLOCKED" ? " is-blocked" : "";
    return `<div class="gate${current}">
      <span class="gate-code">${esc(gate.code)}</span>
      <span class="gate-name">${esc(gate.name)}</span>
      <span class="gate-owner">${esc(gate.owner)} · ${esc(gate.note)}</span>
      ${badge(gate.status, tone)}
    </div>`;
  }).join("");
  return `<div class="gates" role="list">${rows}</div>
    <p class="caption" style="margin-top:8px">门禁 PASSED 不等于业务 PASS；G4 烟测永不进入正式分母。</p>`;
}

export function evidenceLedger(view, options = {}) {
  const { counts, evidence, flags } = view;
  const rows = evidence.map((item) => {
    const expected = item.expected ? `<span class="mark mark-yes">${icon("check")}期望</span>` : `<span class="mark mark-unknown">${icon("x")}无要求</span>`;
    const received = item.received ? `<span class="mark mark-partial">${icon("check")}已接收</span>` : `<span class="mark mark-no">${icon("x")}未接收</span>`;
    let verified;
    if (item.verified) verified = `<span class="mark mark-yes">${icon("check")}已核验</span>`;
    else if (item.state === "QUARANTINED") verified = `<span class="mark mark-no">${icon("shield")}隔离</span>`;
    else verified = `<span class="mark mark-unknown">${icon("clock")}未核验</span>`;
    const access = item.access_level === "NO_ACCESS" ? badge("NO ACCESS", "neutral", "lock") : badge(item.access_level, "plain");
    return [
      `<a href="#/console/evidence/${esc(item.id)}"><span class="cell-primary">${esc(item.label)}</span></a><div class="caption mono">${esc(item.id)} · ${esc(item.kind)}</div>`,
      `<span class="mono">${esc(item.size)}</span><div class="digest">${esc(item.digest)}</div>`,
      esc(item.collected_at),
      expected,
      received,
      verified,
      access
    ];
  });
  const head = ["证据项", "大小 / digest", "采集时间", "expected", "received", "verified", "访问级别"];
  const note = flags.partialEvidence
    ? "received 与 verified 分离：已接收不等于已核验；缺失项 fail-closed。"
    : "三列独立：expected 是要求，received 是到达，verified 是复核结果。";
  return `
    <div class="evidence-counts">
      <div class="evidence-count expected"><div class="label">expected</div><div class="value">${counts.expected}</div><div class="hint">声明的证据要求</div></div>
      <div class="evidence-count received"><div class="label">received</div><div class="value">${counts.received}</div><div class="hint">已到达，不代表已核验</div></div>
      <div class="evidence-count verified"><div class="label">verified</div><div class="value">${counts.verified}</div><div class="hint">通过复核的数量</div></div>
    </div>
    ${table({ head, rows })}
    <p class="evidence-note">${note}</p>
    ${options.footer || ""}
  `;
}

export function timeline(items) {
  return `<div class="timeline">${items.map((item) => `
    <div class="tl-item ${item.state ? `is-${item.state}` : ""}">
      <div class="tl-rail"><span class="tl-dot">${icon(item.state === "done" ? "check" : item.state === "blocked" ? "x" : item.state === "current" ? "dot" : "clock")}</span></div>
      <div>
        <div class="tl-head"><span class="tl-title">${esc(item.title)}</span>${item.time ? `<span class="tl-time">${esc(item.time)}</span>` : ""}</div>
        ${item.body ? `<div class="tl-body">${esc(item.body)}</div>` : ""}
      </div>
    </div>`).join("")}</div>`;
}

export function tabs(items) {
  return `<nav class="tabs" aria-label="任务子视图">${items.map((item) => `
    <a class="tab" href="#${esc(item.path)}" ${item.current ? 'aria-current="page"' : ""}>${esc(item.label)}</a>`).join("")}</nav>`;
}

export function inlineNote(text) {
  return `<div class="note">${text}</div>`;
}

export function feedbackSlot() {
  return `<div id="page-feedback" role="status" aria-live="polite"></div>`;
}

export function scenarioChip(scenario) {
  return `<span class="scenario-chip">${esc(scenario.id)}</span>`;
}

export function permissionReason(view) {
  return view.flags.noPermission ? "当前角色无写入权限；服务端求值顺序为显式 DENY → 显式 ALLOW → 默认 DENY。" : "";
}

export function splitFacts(nodeObserved, linuxView) {
  return `
    <div class="split-facts">
      <section>
        <h3>节点观察事实 · node_observed_*</h3>
        ${kv(Object.entries(nodeObserved).map(([key, value]) => [esc(key), `<span class="mono">${esc(value)}</span>`]))}
        <p class="caption" style="margin-top:8px">used_for_decision=false · 仅回传事实，不写平台判定。</p>
      </section>
      <section>
        <h3>Linux 平台判定</h3>
        ${kv(Object.entries(linuxView).map(([key, value]) => [esc(key), typeof value === "string" && /^[A-Z_]+$/.test(value) ? statusBadge(value) : esc(value)]))}
        <p class="caption" style="margin-top:8px">唯一权威写入方；节点回执不得渲染为 business_verdict 或 verification_status。</p>
      </section>
    </div>
  `;
}

export function mockStamp() {
  return `<span class="scenario-chip">MOCK · server_authoritative=false</span>`;
}
