import {
  axisMatrix,
  badge,
  button,
  esc,
  evidenceLedger,
  gateList,
  genericState,
  kv,
  pageHeader,
  panel,
  progressBar,
  releaseChecklist,
  stateBanners,
  stateBlock,
  stats,
  statusBadge,
  table,
  tabs,
  timeline,
  verdictBanner,
  splitFacts,
  inlineNote
} from "../components.js";
import { can } from "../roles.js";
import { icon } from "../icons.js";
import {
  createTestCampaign,
  deleteTask,
  deleteTestCampaign,
  demoSessionMessages,
  demoSupervisor,
  loadTaskResources,
  loadTaskSessionMessages,
  loadTaskSupervisor,
  loadTestCampaign,
  loadTestCampaignArtifact,
  loadTestCampaigns,
  MAX_TASK_RESOURCES,
  normalizeCampaign,
  sendTaskSessionMessage,
  stopTestCampaign
} from "../data-source.js";
import { applyLanguage } from "../i18n.js";
import { navigate } from "../router.js";

const TERMINAL_STATES = new Set(["COMPLETED", "FAILED", "STOPPED"]);
const TERMINAL_CAMPAIGN_STATES = new Set(["SUCCEEDED", "FAILED", "TIMEOUT", "STOPPED"]);
const CAMPAIGN_ACTIVE_STATES = new Set(["QUEUED", "RUNNING"]);
const REFRESH_ACTIVE_MS = 2000;
const REFRESH_TERMINAL_MS = 10000;

const SUBVIEWS = [
  { id: "TK-02", seg: "overview", label: "Overview" },
  { id: "TK-03", seg: "revisions", label: "Revisions & Approval" },
  { id: "TK-04", seg: "plan", label: "Plan & Cases" },
  { id: "TK-05", seg: "runs", label: "Runs & Attempts" },
  { id: "TK-06", seg: "evidence", label: "Evidence" },
  { id: "TK-07", seg: "verdict", label: "Verdict & Gates" },
  { id: "TK-08", seg: "live", label: "Live" },
  { id: "TK-09", seg: "knowledge", label: "Knowledge & Similar" }
];

function taskHeader(view, route, task) {
  const apiMode = Boolean(view.meta && view.meta.server_authoritative);
  return pageHeader({
    eyebrow: `Tasks · ${route.id} · ${view.scenario.id}`,
    title: task.title,
    description: `<span class="mono">${task.display_id}</span> · 稳定 task_id <span class="mono">${task.id}</span> · 当前 <span class="mono">${task.current_revision_id}</span> (R-${task.revision_number}) · ${task.subtitle}`,
    actions: button("请求审批", { icon: "shield" }) +
      button("派生新修订", { icon: "plus" }) +
      deleteTaskButton(task, { disabled: !apiMode }) +
      button("返回列表", { href: "/console/tasks", kind: "quiet", icon: "arrow" })
  }) + deleteDialog();
}

function taskTabs(route, task) {
  return tabs(SUBVIEWS.map((item) => ({
    path: `/console/tasks/${task.id}/${item.seg}`,
    label: item.label,
    current: item.id === route.id
  })));
}

// Supervisor lifecycle is display-only. The success tone here describes the
// supervisor session reaching COMPLETED, not the task's five-axis formal PASS.
const SUPERVISOR_TONES = {
  COMPLETED: "success",
  FAILED: "danger",
  RUNNING: "action",
  BINDING: "action",
  DISPATCHED: "action",
  READY: "action",
  STOP_REQUESTED: "attention",
  STOPPED: "neutral",
  PENDING: "neutral"
};

function supervisorTone(state) {
  return SUPERVISOR_TONES[state] || "neutral";
}

function localTimestamp(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "medium",
      timeZoneName: "short"
    }).format(date);
  } catch {
    return date.toLocaleString();
  }
}

function deleteTaskButton(task, options = {}) {
  const disabled = options.disabled === true;
  const attrs = [
    "data-delete-task",
    `data-task-id="${esc(task.id)}"`,
    `data-task-title="${esc(task.title || task.display_id || task.id)}"`,
    disabled ? 'disabled aria-disabled="true" title="fixture 演示不会删除真实任务"' : ""
  ].filter(Boolean).join(" ");
  return `<button class="btn btn-danger btn-sm" type="button" ${attrs}>${icon("x")}删除</button>`;
}

function campaignActionButton(campaign, options = {}) {
  const disabled = options.disabled === true;
  const active = CAMPAIGN_ACTIVE_STATES.has(campaign.status);
  const attrs = [
    active ? "data-stop-campaign" : "data-delete-campaign",
    `data-campaign-id="${esc(campaign.id)}"`,
    `data-campaign-title="${esc(campaign.title || campaign.scenario || campaign.id)}"`,
    disabled ? 'disabled aria-disabled="true" title="fixture 演示不会停止或删除真实测试活动"' : ""
  ].filter(Boolean).join(" ");
  const label = active ? "停止" : "删除";
  const cls = active ? "btn btn-sm" : "btn btn-danger btn-sm";
  const glyph = active ? icon("stop") : icon("x");
  return `<button class="${cls}" type="button" ${attrs}>${glyph}${label}</button>`;
}

function newTaskButton(apiMode) {
  const disabled = apiMode && !can("CREATE_TASK");
  const attrs = disabled
    ? 'disabled aria-disabled="true" title="当前角色无 CREATE_TASK"'
    : "";
  return `<button class="btn btn-primary" type="button" data-task-modal-open data-label="新建任务" ${attrs}>${icon("plus")}新建任务</button>`;
}

function taskCreateDialog(view, apiMode) {
  const needsPermission = apiMode && !can("CREATE_TASK");
  return `
    <dialog class="task-create-dialog" id="task-create-dialog" role="dialog" aria-modal="true" aria-labelledby="task-create-title">
      <div class="task-dialog-card">
        <div class="task-dialog-head">
          <h2 class="task-dialog-title" id="task-create-title">新建任务</h2>
          <button class="icon-button" type="button" data-task-modal-close aria-label="关闭">${icon("close")}</button>
        </div>
        <form id="task-create-form" data-api-mode="${apiMode ? "true" : "false"}" aria-describedby="task-create-note" novalidate>
          <div class="field">
            <label for="task-description">任务描述</label>
            <textarea class="textarea task-description" id="task-description" name="description" required
              maxlength="20000" placeholder="例如：Reply with the single word PONG and nothing else."></textarea>
            <span class="hint">标题取描述前 60 个字符；描述同时作为任务目标与 Supervisor 提示词。入口为 conversation，类别为 voice_interaction。</span>
          </div>
          <fieldset class="task-resource-group" aria-describedby="task-node-hint">
            <legend>节点</legend>
            <p class="hint" id="task-node-hint">可选，最多 ${MAX_TASK_RESOURCES} 个；选择设备时会自动加入其所属节点。</p>
            <div class="task-resource-list" data-task-node-list role="group" aria-label="节点选择" aria-busy="true">
              <p class="task-resource-status" data-task-node-status role="status" aria-live="polite">正在读取节点…</p>
            </div>
            <p class="task-resource-count" data-task-node-count aria-live="polite"></p>
          </fieldset>
          <fieldset class="task-resource-group" aria-describedby="task-device-hint">
            <legend>设备</legend>
            <p class="hint" id="task-device-hint">可选，最多 ${MAX_TASK_RESOURCES} 个；设备按所属节点分组。</p>
            <div class="task-resource-list" data-task-device-list role="group" aria-label="设备选择" aria-busy="true">
              <p class="task-resource-status" data-task-device-status role="status" aria-live="polite">正在读取设备…</p>
            </div>
            <p class="task-resource-count" data-task-device-count aria-live="polite"></p>
            <p class="task-resource-warning" data-task-resource-warning role="status" aria-live="polite"></p>
          </fieldset>
          <p class="caption" id="task-create-note">${apiMode ? "提交后创建任务并绑定 Supervisor 会话，随后进入任务会话页；创建期间按钮禁用。" : "FIXTURE 演示：不会创建真实任务，也不会发送真实会话。"}</p>
          <div class="row task-dialog-actions">
            <button class="btn btn-primary" type="submit" data-label="开始任务"${needsPermission ? ' disabled aria-disabled="true" title="当前角色无 CREATE_TASK"' : ""}>开始任务</button>
            <button class="btn" type="button" data-task-modal-close>取消</button>
          </div>
          <div class="form-feedback" id="task-create-feedback" role="alert" aria-live="assertive" hidden></div>
        </form>
      </div>
    </dialog>
  `;
}

function deleteDialog() {
  return `
    <dialog class="task-delete-dialog" id="task-delete-dialog" role="dialog" aria-modal="true" aria-labelledby="task-delete-title">
      <div class="task-dialog-card">
        <div class="task-dialog-head">
          <h2 class="task-dialog-title" id="task-delete-title">删除任务</h2>
          <button class="icon-button" type="button" data-delete-cancel aria-label="关闭">${icon("close")}</button>
        </div>
        <p class="task-dialog-note">将删除任务、Supervisor 绑定、依赖行、已绑定的 OpenCode 会话及关联的测试活动，且无法恢复；存在进行中的测试活动（QUEUED/RUNNING）时必须先停止该活动。</p>
        <p class="task-dialog-target mono" data-delete-target>—</p>
        <p class="form-error" data-delete-error role="alert" hidden></p>
        <div class="row task-dialog-actions">
          <button class="btn" type="button" data-delete-cancel>取消</button>
          <button class="btn btn-danger" type="button" data-delete-confirm>确认删除</button>
          <span class="caption" data-delete-status role="status" aria-live="polite"></span>
        </div>
      </div>
    </dialog>
  `;
}

function campaignActionDialog() {
  return `
    <dialog class="task-delete-dialog campaign-action-dialog" id="campaign-action-dialog" role="dialog" aria-modal="true" aria-labelledby="campaign-action-title">
      <div class="task-dialog-card">
        <div class="task-dialog-head">
          <h2 class="task-dialog-title" id="campaign-action-title" data-campaign-dialog-title>测试活动操作</h2>
          <button class="icon-button" type="button" data-campaign-cancel aria-label="关闭">${icon("close")}</button>
        </div>
        <p class="task-dialog-note" data-campaign-dialog-note>—</p>
        <p class="task-dialog-target mono" data-campaign-target>—</p>
        <p class="form-error" data-campaign-error role="alert" hidden></p>
        <div class="row task-dialog-actions">
          <button class="btn" type="button" data-campaign-cancel>取消</button>
          <button class="btn btn-danger" type="button" data-campaign-stop-delete hidden>停止后删除</button>
          <button class="btn btn-primary" type="button" data-campaign-confirm>停止</button>
          <span class="caption" data-campaign-status role="status" aria-live="polite"></span>
        </div>
      </div>
    </dialog>
  `;
}

function inspectorValue(supervisor, session) {
  const state = String((supervisor && supervisor.state) || "UNKNOWN");
  const result = state === "COMPLETED"
    ? (supervisor.result_available ? "已完成 · 查看下方结果" : "任务已完成，结果尚不可用")
    : "—";
  const error = supervisor && supervisor.result_error_code
    ? supervisor.result_error_code
    : state === "FAILED" || state === "STOPPED" ? state : "—";
  return {
    result,
    error,
    count: String((session && session.messages && session.messages.length) || 0)
  };
}

function inspectorRow(label, value) {
  return `<div class="inspector-row"><dt>${label}</dt><dd>${value}</dd></div>`;
}

function inspectorMarkup(task, supervisor, session) {
  const state = String((supervisor && supervisor.state) || "UNKNOWN");
  const values = inspectorValue(supervisor, session);
  const refreshed = localTimestamp(new Date().toISOString());
  return `
    <aside class="task-inspector" id="task-inspector" data-inspector aria-label="Inspector">
      <div class="inspector-head">
        <h2 class="inspector-title">Inspector</h2>
        <button class="icon-button" type="button" data-inspector-close aria-label="收起 Inspector">${icon("close")}</button>
      </div>
      <dl class="inspector-list">
        ${inspectorRow("任务 ID", `<span class="mono">${esc(task.id)}</span>`)}
        ${inspectorRow("Supervisor ID", `<span class="mono">${esc(supervisor.supervisor_display_id || "—")}</span>`)}
        ${inspectorRow("会话（掩码）", `<span class="mono" data-inspector-field="session">${esc(supervisor.remote_session_id || "—")}</span>`)}
        ${inspectorRow("模型", `<span class="mono" data-inspector-field="model">${esc(supervisor.model || "服务端未投影")}</span>`)}
        ${inspectorRow("状态", `<span data-inspector-field="state">${stateMarkup(state)}</span>`)}
        ${inspectorRow("最后刷新", `<span data-inspector-field="refreshed">${esc(refreshed)}</span>`)}
        ${inspectorRow("消息数", `<span data-inspector-field="message_count">${esc(values.count)}</span>`)}
        ${inspectorRow("结果", `<a href="#task-result" data-inspector-field="result">${esc(values.result)}</a>`)}
        ${inspectorRow("错误", `<span data-inspector-field="error">${esc(values.error)}</span>`)}
      </dl>
      <p class="caption">只读投影；remote session 已由服务端掩码。</p>
    </aside>
  `;
}

export function supervisorPanelBody(supervisor) {
  const sup = supervisor && typeof supervisor === "object" ? supervisor : { status: "missing" };

  if (sup.status === "loading") {
    return stateBlock("loading", {
      title: "正在读取 Supervisor 状态",
      note: "等待只读投影；不推断执行成功或结果。"
    });
  }

  if (sup.status === "error") {
    const error = sup.error || {};
    return `
      ${stateBlock("error", {
        title: `Supervisor 读取失败 · ${error.code || "ERROR"}`,
        note: error.message || "控制面请求未成功。"
      })}
      ${kv([
        ["endpoint", `<span class="mono">${esc(sup.endpoint || "—")}</span>`],
        ["HTTP status", `<span class="mono">${esc(String(error.status ?? "—"))}</span>`],
        ["retryable", `<span class="mono">${error.retryable === false ? "false" : "true"}</span>`]
      ])}
      <p class="caption" style="margin-top:8px">请求失败保持可见，不回落 fixture；使用“刷新”重试。</p>
    `;
  }

  if (sup.status === "missing") {
    return stateBlock("empty", {
      title: "缺少 task_id",
      note: "当前路由没有可查询的任务标识，未发起 Supervisor 请求。"
    });
  }

  if (sup.status === "absent") {
    return stateBlock("empty", {
      title: "该任务没有 Supervisor 绑定",
      note: "按传统任务投影显示；没有可读取或继续的任务会话。"
    });
  }

  const state = String(sup.state || "UNKNOWN");
  const rows = [
    ["supervisor_state", `${badge(state, supervisorTone(state))}${sup.state_is_terminal ? ` ${badge("TERMINAL", "plain")}` : ""}`],
    ["supervisor_id", `<span class="mono">${esc(sup.supervisor_display_id || "—")}</span>`],
    ["remote_session_id", `<span class="mono">${esc(sup.remote_session_id || "—")}</span>`],
    ["result", sup.result_available
      ? `<span class="cell-primary">${esc(sup.result_summary || "—")}</span>`
      : `<span class="caption">结果尚不可用</span>`]
  ];
  if (sup.result_error_code) rows.push(["result.error_code", badge(sup.result_error_code, "danger")]);
  if (sup.prompt_digest) {
    const bytes = Number.isFinite(sup.prompt_bytes) ? ` · ${esc(String(sup.prompt_bytes))} B` : "";
    rows.push(["prompt", `<span class="digest">${esc(sup.prompt_digest)}</span>${bytes}`]);
  }
  rows.push(["updated_at", sup.updated_at
    ? `<time class="mono" datetime="${esc(sup.updated_at)}">${esc(localTimestamp(sup.updated_at))}</time>`
    : "—"]);

  const demoNote = sup.status === "demo" ? " DEMO 为 fixture 演示值，非实时。" : "";
  return `
    ${kv(rows)}
    <p class="caption" style="margin-top:8px">只读投影；remote_session_id 由服务端掩码返回，界面不还原完整会话 ID。仅表示 Supervisor 生命周期，不构成任务判定。${demoNote}</p>
  `;
}

export function supervisorPanel(supervisor, options = {}) {
  const sup = supervisor && typeof supervisor === "object" ? supervisor : { status: "missing" };
  const live = Boolean(options.live);
  const loading = sup.status === "loading";
  const showRefresh = live && (sup.status === "ready" || sup.status === "error");
  const action = showRefresh
    ? button("刷新", { action: "refresh-supervisor", small: true, icon: "refresh" })
    : live ? "" : badge("DEMO", "plain");
  return panel({
    title: "Supervisor",
    note: live ? "只读；单次读取，可手动刷新" : "fixture 演示值；非实时，不代表真实任务",
    actions: action,
    body: `<div data-supervisor-slot aria-busy="${loading ? "true" : "false"}">${supervisorPanelBody(sup)}</div>`
  });
}

function metaPanel(task, view) {
  return panel({
    title: "任务身份",
    note: "稳定 task_id；修订谱系独立",
    body: kv([
      ["display_id", `<span class="mono">${task.display_id}</span>`],
      ["task_id", `<span class="mono">${task.id}</span>`],
      ["stage", statusBadge(task.stage)],
      ["current_revision", `<span class="mono">${task.current_revision_id}</span> · R-${task.revision_number}`],
      ["parent_revision", `<span class="mono">${task.parent_revision_id}</span>`],
      ["change_kind", `<span class="mono">${task.change_kind}</span>`],
      ["content_digest", `<span class="digest">${task.content_digest}</span>`],
      ["blocker.owner", task.blocker_owner],
      ["updated_at", `<span class="mono">${task.updated_at}</span>`]
    ])
  });
}

function axesPanel(view) {
  return panel({
    title: "五轴状态",
    note: "永不折叠；任一项不满足即无正式 PASS",
    body: `${axisMatrix(view.axes)}<div style="margin-top:12px">${verdictBanner(view.axes)}</div>`
  });
}

function overviewBody(view, route, task) {
  return `
    ${taskHeader(view, route, task)}
    ${stateBanners(view)}
    ${taskTabs(route, task)}
    ${stats([
      { label: "当前修订", value: `R-${task.revision_number}`, note: task.change_kind },
      { label: "正式分母", value: view.progress.mode === "COUNTS" ? String(view.progress.total) : "未知", note: "仅 formal 且 approved" },
      { label: "expected / received / verified", value: `${view.counts.expected} / ${view.counts.received} / ${view.counts.verified}`, note: "三列分离" },
      { label: "证据复核", value: view.axes.evidence_status === "COMPLETE" ? "COMPLETE" : "INCOMPLETE", note: `verification ${view.axes.verification_status}` }
    ])}
    <div class="layout-2" style="margin-top:16px">
      <div>
        ${axesPanel(view)}
        ${panel({ title: "G0–G7 门禁", note: "门禁 PASSED 不等于业务 PASS", body: gateList(view.gates) })}
        ${panel({
          title: "最近活动",
          note: "只读时间线；不替代审计",
          body: timeline([
            { title: "节点心跳与事实回传", time: "14:06:19", body: "att-112 继续运行；used_for_decision=false。", state: "done" },
            { title: "重试 attempt att-112 启动", time: "13:58:12", body: "retry_of=att-111；flaky_suspect 仍在观察。", state: "done" },
            { title: "att-111 transport_reset", time: "13:55:40", body: "失败分类由 Linux 写入；节点回执未参与判定。", state: "blocked" },
            { title: "G1 冻结批准生效", time: "11:20:03", body: "审批绑定 content_digest 与范围快照。", state: "done" }
          ])
        })}
      </div>
      <div>
        ${supervisorPanel(view.supervisor, { live: Boolean(view.meta && view.meta.server_authoritative) })}
        ${metaPanel(task, view)}
        ${panel({
          title: "当前阻塞与下一步",
          note: "责任方明确",
          body: `
            ${kv([
              ["主阻塞", view.flags.blocked ? badge("G3 资源资格", "danger") : badge("无硬阻塞", "neutral")],
              ["证据缺口", badge("serial_log 未核验", "attention")],
              ["下一步", "等待 G6 证据复核；禁止提前标记 PASS"],
              ["release_state", badge("HELD", "neutral", "lock")]
            ])}
            <div class="row" style="margin-top:12px">${button("打开证据", { href: `/console/tasks/${task.id}/evidence`, small: true })}${button("查看判定", { href: `/console/tasks/${task.id}/verdict`, small: true })}</div>
          `
        })}
        ${panel({
          title: "进度口径",
          note: "仅 COUNTS + 已批准分母显示百分比",
          body: progressBar(view.progress)
        })}
      </div>
    </div>
    ${taskCampaignSection(view, task, Boolean(view.meta && view.meta.server_authoritative))}
    ${campaignActionDialog()}
    ${campaignTriggerDialog(view, task, Boolean(view.meta && view.meta.server_authoritative))}
  `;
}

function revisionsBody(view, route, task) {
  const rows = view.world.revisions.map((rev) => [
    `<span class="cell-primary mono">${rev.id}</span><div class="caption">${rev.number}</div>`,
    rev.title,
    rev.parent ? `<span class="mono">${rev.parent}</span>` : "—",
    badge(rev.change_kind, "plain"),
    statusBadge(rev.status),
    rev.frozen_at || "—",
    `<span class="digest">${rev.digest || "—"}</span>`,
    rev.id === task.current_revision_id
      ? badge("当前修订", "action")
      : rev.status === "DRAFT"
        ? badge("可编辑草稿", "neutral")
        : badge("只读", "plain", "lock")
  ]);
  const approval = view.world.approval;
  return `
    ${taskHeader(view, route, task)}
    ${stateBanners(view)}
    ${taskTabs(route, task)}
    ${panel({
      title: "修订谱系",
      note: "冻结后禁止原地编辑；范围变化派生同任务新修订",
      body: table({
        head: ["修订", "标题", "父修订", "变更类型", "状态", "冻结时间", "content_digest", "访问"],
        rows
      }),
      flush: true
    })}
    <div class="layout-2" style="margin-top:16px">
      ${panel({
        title: "唯一有效审批",
        note: "绑定冻结内容摘要与范围快照",
        body: `
          ${kv([
            ["审批人", `${approval.approver_role} · <span class="mono">${approval.approver_id}</span>`],
            ["decision", badge(approval.decision, "success")],
            ["comment", approval.comment],
            ["revision_content_digest", `<span class="digest">${approval.revision_content_digest}</span>`],
            ["scope_snapshot", approval.scope_snapshot],
            ["effective_at", `<span class="mono">${approval.effective_at}</span>`],
            ["wait_timer", approval.wait_timer],
            ["self_approval", approval.self_approval ? badge("YES", "danger") : badge("NO", "neutral")],
            ["prevent_self_review", approval.prevent_self_review ? badge("ENABLED", "neutral") : badge("DISABLED", "danger")]
          ])}
          <div class="form-grid" style="margin-top:14px">
            <div class="field field-full"><label for="approval-comment">审批意见（批准/拒绝均必填）</label><textarea class="textarea" id="approval-comment" placeholder="说明依据、范围与风险；超时不自动拒绝。"></textarea></div>
          </div>
          <div class="row" style="margin-top:10px">
            ${button("批准", { kind: "primary", icon: "check" })}
            ${button("拒绝", { kind: "danger", icon: "x" })}
          </div>
          <p class="caption" style="margin-top:8px">按钮为 prototype mock；审批只由具备 APPROVE_TASK 的角色执行，客户端隐藏不构成访问控制。</p>
        `
      })}
      ${panel({
        title: "冻结范围与只读规则",
        note: "旧修订永不改写",
        body: `
          ${kv([
            ["R-3 范围", task.frozen_scope],
            ["R-3 状态", statusBadge("APPROVED")],
            ["R-4 草稿", "低温启动扩展；未冻结，不得进入执行"],
            ["R-2 及更早", `${badge("READ ONLY", "plain", "lock")} 历史事实`]
          ])}
          <p class="caption" style="margin-top:8px">比较修订只读；范围变化必须派生同任务新修订，并重新走 G0/G1。</p>
        `
      })}
    </div>
  `;
}

function planBody(view, route, task) {
  return `
    ${taskHeader(view, route, task)}
    ${stateBanners(view)}
    ${taskTabs(route, task)}
    ${panel({
      title: "用例与 oracle",
      note: "Case 随修订冻结，先于 Run",
      body: table({
        head: ["case", "版本", "标题", "oracle", "required_evidence", "mode", "状态"],
        rows: view.world.cases.map((testCase) => [
          `<span class="cell-primary mono">${testCase.case_id}</span>`,
          testCase.version,
          testCase.title,
          testCase.oracle,
          testCase.required_evidence.map((item) => badge(item, "plain")).join(" "),
          badge(testCase.mode, testCase.mode === "formal" ? "action" : "neutral"),
          statusBadge(testCase.status)
        ])
      }),
      flush: true
    })}
    ${inlineNote("烟测 case 只用于 G4 预检，reference-only，永不进入正式分母。冻结后新增或修改 case 必须派生新修订。")}
  `;
}

function runsBody(view, route, task) {
  const rows = view.world.runs.map((run) => [
    `<a class="mono" href="#/console/runs/${run.id}"><span class="cell-primary">${run.id}</span></a>`,
    badge(run.mode, run.mode === "formal" ? "action" : "neutral"),
    statusBadge(run.lifecycle_status),
    run.denominator_eligible ? badge("ELIGIBLE", "success") : badge("NOT ELIGIBLE", "neutral"),
    String(run.attempts),
    run.started_at,
    run.last_heartbeat_at
  ]);
  return `
    ${taskHeader(view, route, task)}
    ${stateBanners(view)}
    ${taskTabs(route, task)}
    ${panel({
      title: "运行与 Attempt 矩阵",
      note: "static / smoke / formal 分母严格分离",
      body: table({
        head: ["run", "mode", "lifecycle", "正式分母", "attempts", "开始", "最后心跳"],
        rows
      }),
      flush: true
    })}
    <div class="layout-2" style="margin-top:16px">
      ${panel({ title: "正式采样进度", note: "仅计数模式", body: progressBar(view.progress) })}
      ${panel({
        title: "分母资格",
        note: "由 Linux 判定",
        body: `
          ${kv([
            ["formal run", `<a class="mono" href="#/console/runs/run-042">run-042</a>`],
            ["denominator_eligible", badge("TRUE", "success")],
            ["smoke run", `<span class="mono">run-039</span> · ${badge("NOT ELIGIBLE", "neutral")}`],
            ["static run", `<span class="mono">run-036</span> · ${badge("NOT ELIGIBLE", "neutral")}`]
          ])}
          <p class="caption" style="margin-top:8px">模拟、回放、烟测拼入正式样本即视为无效分母。</p>
        `
      })}
    </div>
  `;
}

function evidenceBody(view, route, task) {
  return `
    ${taskHeader(view, route, task)}
    ${stateBanners(view)}
    ${taskTabs(route, task)}
    ${panel({
      title: "证据台账",
      note: "metadata only；原始访问跳 EV 并二次鉴权",
      body: evidenceLedger(view, {
        footer: `<p class="caption" style="margin-top:8px">大日志未归档不阻断证据上传；缺 cleanup_receipt 也不等于 evidence INCOMPLETE，二者独立。</p>`
      })
    })}
    ${panel({
      title: "manifest 摘要",
      note: "仅显示引用与大小，不展示绝对路径",
      body: table({
        head: ["manifest", "case", "大小", "collected_at", "状态"],
        rows: [
          ["<span class='mono'>man-042-a</span>", "case-voice-001 · v3", "18.4 MB", "2026-10-29 13:42:08", badge("VERIFIED", "success")],
          ["<span class='mono'>man-042-b</span>", "case-voice-003 · v1", "2.1 MB", "2026-10-29 13:44:51", badge("PARTIAL", "attention")],
          ["<span class='mono'>man-039-s</span>", "smoke", "4.8 MB", "2026-10-29 13:04:47", badge("REFERENCE ONLY", "neutral")]
        ]
      }),
      flush: true
    })}
  `;
}

function verdictBody(view, route, task) {
  const rows = [
    ["case-voice-001 · v3", "10 / 10", "10", "10", badge("VERIFIED", "success")],
    ["case-voice-002 · v2", "10 / 10", "10", "9", badge("PARTIAL", "attention")],
    ["case-voice-003 · v1", "10 / 10", "10", "10", badge("VERIFIED", "success")],
    ["case-voice-004 · v1", "10 / 10", "10", "9", badge("PARTIAL", "attention")]
  ];
  return `
    ${taskHeader(view, route, task)}
    ${stateBanners(view)}
    ${taskTabs(route, task)}
    ${axesPanel(view)}
    <div class="layout-2" style="margin-top:16px">
      ${panel({
        title: "fail-closed 原因",
        note: "逐项列出，不合并为模糊结论",
        body: `
          <ul class="list-plain">
            <li>evidence_status = <span class="mono">${view.axes.evidence_status}</span>：serial_log 未核验，reference audio 缺失。</li>
            <li>verification_status = <span class="mono">${view.axes.verification_status}</span>：G6 证据复核尚未完成。</li>
            <li>G5 正式采样仍在进行；不得提前给出正式 PASS。</li>
            <li>release_state 与 PASS 独立：缺 cleanup_receipt 时保持 HELD，但可同时为业务 PASS。</li>
          </ul>
        `
      })}
      ${panel({
        title: "分母与记录分离",
        note: "总量 + per_device / per_case",
        body: `
          ${stats([
            { label: "正式总量", value: "40", note: "approved denominator" },
            { label: "per_device", value: "1", note: "dev-tcl-001" },
            { label: "per_case", value: "4", note: "formal cases" },
            { label: "smoke", value: "0", note: "never counted" }
          ])}
          <p class="caption" style="margin-top:8px">四类记录分离：formal / smoke / simulation / replay 不得拼入同一分母。</p>
        `
      })}
    </div>
    ${panel({
      title: "按用例的结果",
      body: table({ head: ["case", "采样", "received", "verified", "状态"], rows })
    })}
    <div class="layout-2" style="margin-top:16px">
      ${panel({ title: "释放前置（与判定独立）", body: releaseChecklist(view) })}
      ${panel({
        title: "报告",
        note: "冻结后不可原地改",
        body: `
          ${kv([
            ["report", `<a href="#/console/reports/rpt-voice-001"><span class="mono">rpt-voice-001</span></a>`],
            ["版本", "v3"],
            ["lifecycle", statusBadge("FROZEN")],
            ["披露", badge("INTERNAL", "plain")]
          ])}
          <p style="margin-top:10px"><a class="btn" href="#/console/reports/rpt-voice-001">打开报告</a></p>
        `
      })}
    </div>
  `;
}

function liveBody(view, route, task, run, attempt) {
  const nodeObserved = attempt.node_observed;
  const linuxView = {
    execution_status: view.axes.execution_status,
    communication_state: view.link.communication_state,
    occupancy_state: view.link.occupancy_state,
    execution_permit: view.link.execution_permit,
    business_verdict: view.axes.business_verdict
  };
  const liveEvents = view.meta.server_authoritative
    ? view.liveEvents
    : [
      { title: "attempt att-112 运行中", time: "14:06:19", body: "最后步骤 playback_noise_burst；节点回执 used_for_decision=false。", state: "current" },
      { title: "heartbeat", time: "14:06:19", body: "仅节点事实。", state: "done" },
      { title: "重试启动", time: "13:58:12", body: "retry_of=att-111。", state: "done" },
      { title: "att-111 transport_reset", time: "13:55:40", body: "失败分类由 Linux 写入。", state: "blocked" }
    ];
  const eventBody = liveEvents.length
    ? timeline(liveEvents)
    : `<p class="caption" role="status">控制面尚未返回可显示事件；空态不推断运行成功、停止或 PASS。</p>`;
  return `
    ${taskHeader(view, route, task)}
    ${stateBanners(view)}
    ${taskTabs(route, task)}
    <div class="layout-2">
      <div>
        ${panel({
          title: "运行现场",
          note: "节点事实与 Linux 判定分栏，异形异色",
          body: splitFacts(nodeObserved, linuxView)
        })}
        ${panel({
          title: "事件流（只读投影）",
          note: "API 模式每 10 秒刷新；仅显示控制面返回的只读事实",
          body: eventBody
        })}
      </div>
      <div>
        ${panel({
          title: "当前信号",
          body: kv([
            ["通信", statusBadge(view.link.communication_state)],
            ["执行", statusBadge(view.link.execution_status)],
            ["占用", statusBadge(view.link.occupancy_state)],
            ["许可", statusBadge(view.link.execution_permit)],
            ["STOP", view.flags.pendingStop ? badge("PENDING", "attention", "stop") : badge("NONE", "neutral")],
            ["freshness", view.link.freshness.is_stale ? badge("STALE", "attention") : badge("FRESH", "neutral")]
          ])
        })}
        ${panel({
          title: "危险动作",
          note: "二次确认 + 前置条件",
          body: `
            ${button("请求 STOP", {
              kind: "danger",
              icon: "stop",
              disabledReason: view.flags.noPermission ? "当前角色无执行许可；动作保留可见但禁用。" : ""
            })}
            <p class="caption" style="margin-top:8px">STOP 请求不显示为已执行；只有节点回执后才进入停止后续动作。</p>
          `
        })}
        ${panel({ title: "进度", body: progressBar(view.progress) })}
      </div>
    </div>
  `;
}

function knowledgeBody(view, route, task) {
  return `
    ${taskHeader(view, route, task)}
    ${stateBanners(view)}
    ${taskTabs(route, task)}
    ${panel({
      title: "相关已批准知识",
      note: "候选与条目视觉权重分开",
      body: table({
        head: ["条目", "状态", "适用性", "更新时间"],
        rows: view.world.knowledge.map((item) => [
          `<a href="#/console/knowledge/${item.id}"><span class="cell-primary">${item.title}</span></a><div class="caption mono">${item.id}</div>`,
          statusBadge(item.status),
          item.applicability,
          item.updated_at
        ])
      }),
      flush: true
    })}
    <div class="layout-2" style="margin-top:16px">
      ${panel({
        title: "候选知识",
        note: "无 PROPOSED → PROMOTED 捷径",
        body: `
          <ul class="list-plain">
            ${view.world.candidates.slice(0, 3).map((candidate) => `<li>${candidate.title} · ${badge(candidate.status, candidate.status === "NEEDS_INFO" ? "attention" : "neutral")}</li>`).join("")}
          </ul>
          <p style="margin-top:10px"><a href="#/console/knowledge/candidates">打开候选治理队列</a></p>
        `
      })}
      ${panel({
        title: "应用到计划",
        note: "只生成草案修订，需再次审批",
        body: `
          ${button("生成草案修订", { icon: "plus" })}
          <p class="caption" style="margin-top:8px">生成者不得是唯一批准者；自动推广始终禁止（automatic_allowed=false）。</p>
        `
      })}
    </div>
  `;
}

function isTerminalState(state) {
  return TERMINAL_STATES.has(String(state || ""));
}

function stateMarkup(state) {
  const value = String(state || "UNKNOWN");
  return badge(value, supervisorTone(value));
}

function messageHtml(message) {
  const role = String(message.role || "unknown");
  const rowClass = role === "user" ? "user" : role === "assistant" ? "assistant" : "unknown";
  const roleLabel = role === "user" ? "用户" : role === "assistant" ? "助手" : role === "system" ? "系统" : role;
  const time = message.created_at
    ? `<time class="chat-time mono" datetime="${esc(message.created_at)}">${esc(localTimestamp(message.created_at))}</time>`
    : "";
  const error = message.error_code
    ? `<div class="chat-message-error">错误：${esc(message.error_code)}</div>`
    : "";
  return `
    <div class="chat-row ${rowClass}" data-message-id="${esc(message.message_id || "")}" data-no-i18n>
      <div class="chat-bubble">
        <div class="chat-meta"><span class="chat-role">${esc(roleLabel)}</span>${time}</div>
        <div class="chat-text">${renderMarkdown(message.text || "")}</div>
        ${error}
      </div>
    </div>
  `;
}

function isToolOnlyMessage(message) {
  return String((message && message.text) || "").trim().startsWith("(模型未返回文本");
}

function messagesHtml(messages, emptyNote) {
  const visible = (messages || []).filter(
    (message) => !isToolOnlyMessage(message) && (String(message.text || "").trim() || message.role === "user")
  );
  if (!visible.length) {
    return `<p class="chat-empty">${esc(emptyNote)}</p>`;
  }
  return visible.map(messageHtml).join("");
}

function emptyNoteFor(session) {
  if (session && session.status === "unbound") return "会话尚未绑定，等待 Supervisor 启动…";
  if (session && session.status === "error") return "会话不可用 · 任务结果仍可查看";
  return "尚无会话内容。发送一条消息开始对话。";
}

function resultMarkup(supervisor) {
  const state = String((supervisor && supervisor.state) || "UNKNOWN");
  if (state === "COMPLETED") {
    return supervisor.result_available
      ? `<div class="chat-result" data-chat-result><span class="chat-result-label">结果</span><div class="chat-result-body chat-text">${renderMarkdown(supervisor.result_summary || "—")}</div></div>`
      : `<div class="chat-result" data-chat-result><span class="chat-result-label">结果</span><div class="chat-result-body chat-text">任务已完成，结果尚不可用</div></div>`;
  }
  return `<div class="chat-result" data-chat-result hidden></div>`;
}

function errorMarkup(supervisor) {
  const state = String((supervisor && supervisor.state) || "UNKNOWN");
  if (state === "FAILED" || state === "STOPPED") {
    const code = (supervisor && supervisor.result_error_code) || state;
    const suffix = supervisor.result_available ? "" : " · 结果尚不可用";
    return `<p class="chat-error" data-chat-error role="alert"><span class="chat-result-label">${esc(state)}</span>${esc(code)}${esc(suffix)}</p>`;
  }
  return `<p class="chat-error" data-chat-error role="alert" hidden></p>`;
}

function composerMarkup(supervisor, session, demo) {
  const bound = Boolean(supervisor && supervisor.remote_session_id && supervisor.remote_session_id !== "—");
  const unavailable = Boolean(session && session.status === "error");
  const disabled = demo || !bound || unavailable;
  const note = demo
    ? "DEMO · fixture 演示不会发送真实消息。"
    : unavailable
      ? "会话内容不可用；任务结果和测试活动仍可查看。"
      : !bound
        ? "会话尚未绑定，等待 Supervisor 启动…"
        : "Enter 发送，Shift+Enter 换行。";
  return `
    <form class="chat-composer" data-chat-form>
      <label class="sr-only" for="task-chat-input">继续会话</label>
      <div class="chat-composer-main">
        <textarea class="textarea chat-input" id="task-chat-input" data-chat-input rows="2" maxlength="20000"
          placeholder="继续对这个会话说点什么…"${disabled ? " disabled" : ""}></textarea>
        <button class="btn btn-primary chat-send" type="submit" data-chat-send data-label="发送"${disabled ? " disabled" : ""}>发送</button>
      </div>
      <div class="chat-composer-row">
        <span class="hint" data-chat-status role="status" aria-live="polite">${esc(note)}</span>
      </div>
    </form>
  `;
}

function runStatusVisual(supervisor) {
  if (supervisor && supervisor.status === "error") return { level: "danger", label: "状态异常" };
  if (supervisor && supervisor.status === "absent") return { level: "neutral", label: "未启动" };
  const value = String((supervisor && supervisor.state) || "UNKNOWN").toUpperCase();
  if (["RUNNING", "ACTIVE", "IN_PROGRESS", "BINDING", "DISPATCHED", "READY"].includes(value)) {
    return { level: "running", label: "执行中" };
  }
  if (["COMPLETED", "SUCCEEDED", "PASSED"].includes(value)) {
    return { level: "success", label: "已完成" };
  }
  if (["FAILED", "ERROR"].includes(value)) {
    return { level: "danger", label: "异常" };
  }
  if (["STOPPED", "CANCELLED"].includes(value)) {
    return { level: "neutral", label: "已停止" };
  }
  if (["QUEUED", "PENDING", "WAITING", "BLOCKED", "PAUSED", "STOP_REQUESTED"].includes(value)) {
    return { level: "attention", label: "等待/阻塞" };
  }
  return { level: "neutral", label: "空闲" };
}

function runDurationLabel(milliseconds) {
  const total = Math.max(0, Math.floor(Number(milliseconds) / 1000));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  const pad = (value) => String(value).padStart(2, "0");
  return hours ? `${hours}:${pad(minutes)}:${pad(seconds)}` : `${pad(minutes)}:${pad(seconds)}`;
}

function runClock(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  try {
    return new Intl.DateTimeFormat(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false
    }).format(date);
  } catch {
    return String(value);
  }
}

function lastAgentActivity(session) {
  return ((session && session.messages) || [])
    .filter((message) => String(message && message.text ? message.text : "").trim() && !isToolOnlyMessage(message))
    .slice(-1)[0] || null;
}

function agentActivity(supervisor, session) {
  const visual = runStatusVisual(supervisor);
  if (visual.level === "running") {
    const last = lastAgentActivity(session);
    if (!last || !last.created_at) return "等待首条输出…";
    const age = Date.now() - Date.parse(last.created_at);
    if (Number.isFinite(age) && age > 120000) {
      return `疑似停滞 · ${runDurationLabel(age)} 无新输出`;
    }
    return `最后活动 ${runClock(last.created_at)}`;
  }
  if (visual.level === "success") return "结果已写入";
  if (visual.level === "danger") return "执行异常，请查看错误";
  if (visual.level === "attention") return "等待输入或依赖";
  if (visual.label === "已停止") return "执行已停止";
  return "尚未开始";
}

function agentStatusMarkup(task, supervisor, session) {
  const source = task || {};
  const visual = runStatusVisual(supervisor);
  const start = (supervisor && supervisor.created_at) || source.created_at || "";
  const end = isTerminalState(supervisor && supervisor.state) ? ((supervisor && supervisor.updated_at) || "") : "";
  const elapsed = start ? Date.parse(end || new Date().toISOString()) - Date.parse(start) : null;
  const lead = source.lead_agent_display_id || source.lead_agent_name || source.lead_agent_id || "未投影";
  const leadTitle = source.lead_agent_name && source.lead_agent_display_id
    ? `${source.lead_agent_name} · ${source.lead_agent_display_id}`
    : "服务端未投影主 Agent 信息";
  const subagents = Array.isArray(source.subagent_display_ids) ? source.subagent_display_ids.filter(Boolean) : [];
  return `<div class="agent-status" data-agent-status data-level="${visual.level}" aria-label="Agent 运行状态">
    <span class="agent-status-dot" aria-hidden="true"></span>
    <span class="agent-status-label" data-agent-status-label role="status" aria-live="polite">${esc(visual.label)}</span>
    <span class="agent-status-elapsed-wrap" title="执行耗时"><span class="sr-only">耗时</span><strong class="agent-status-elapsed mono" data-agent-elapsed aria-hidden="true" data-start="${esc(start)}" data-end="${esc(end)}">${Number.isFinite(elapsed) ? runDurationLabel(elapsed) : "—"}</strong></span>
    <span class="agent-status-sep" aria-hidden="true"></span>
    <span class="agent-status-item" title="主 Agent"><span class="agent-status-key">主</span><strong title="${esc(leadTitle)}">${esc(lead)}</strong></span>
    <span class="agent-status-item" title="子 Agent"><span class="agent-status-key">子</span><strong title="当前会话未返回子 Agent 投影">${esc(subagents.length ? subagents.join("、") : "未上报")}</strong></span>
    <span class="agent-status-activity" data-agent-activity aria-live="off">${esc(agentActivity(supervisor, session))}</span>
  </div>`;
}

function chatPanel(view, task, supervisor, session, demo) {
  const messages = (session && session.messages) || [];
  const refreshed = localTimestamp(new Date().toISOString());
  return `
    <section class="panel chat-panel" data-chat-root data-task-id="${esc(task.id)}"${demo ? ' data-demo="true"' : ""}>
      <div class="chat-head">
        <h2 class="panel-title">任务会话</h2>
        <div class="chat-head-meta">
          <span class="caption chat-head-note" title="只读 Supervisor 状态仅表示会话生命周期，不构成任务判定。">Supervisor 只读</span>
          <span class="sr-only" data-chat-state>${stateMarkup(supervisor && supervisor.state)}</span>
          <time class="sr-only" data-chat-refreshed datetime="${esc(new Date().toISOString())}">${esc(refreshed)}</time>
          <button class="btn btn-sm" type="button" data-inspector-toggle aria-expanded="true" aria-controls="task-inspector">Inspector</button>
          ${demo ? badge("DEMO", "plain") : button("刷新", { action: "refresh-chat", small: true, icon: "refresh" })}
        </div>
      </div>
      ${agentStatusMarkup(task, supervisor, session)}
      ${errorMarkup(supervisor)}
      <div class="chat-history" data-chat-history role="log" aria-live="polite" aria-relevant="additions" aria-label="任务会话内容">
        ${messagesHtml(messages, emptyNoteFor(session))}
      </div>
      ${composerMarkup(supervisor, session, demo)}
    </section>
  `;
}

// ---------------------------------------------------------------------------
// Read-only conversation trace.  Every row is derived from an existing view
// projection (task, supervisor, session, campaign/round rows).  No synthetic
// events are invented; when a field is missing the row says so and keeps a "—"
// timestamp.  Rows without their own timestamp are anchored to their parent
// projection only for ordering, never to imply a time they do not have.
// ---------------------------------------------------------------------------

const TRACE_KIND_LABELS = {
  task: "任务",
  supervisor: "SUP",
  session: "会话",
  campaign: "活动",
  artifact: "产物",
  result: "结果",
  error: "降级"
};

function traceMs(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.getTime();
}

function traceDuration(startValue, endValue) {
  const start = traceMs(startValue);
  const end = traceMs(endValue);
  if (start == null || end == null || end < start) return null;
  return runDurationLabel(end - start);
}

function traceExcerpt(value, max = 320) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (!text) return "（服务端未返回文本）";
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function traceEvents(view, task) {
  const supervisor = view.supervisor || { status: "absent" };
  const session = view.session || null;
  const campaigns = (Array.isArray(view.taskCampaigns) ? view.taskCampaigns : [])
    .map(normalizeCampaign)
    .filter((campaign) => campaign.id && task && campaign.task_id === task.id);

  const knownTimes = [];
  const remember = (value) => {
    const ms = traceMs(value);
    if (ms != null) knownTimes.push(ms);
  };
  remember(task && task.created_at);
  remember(task && task.updated_at);
  if (supervisor.status === "ready" || supervisor.status === "demo") {
    remember(supervisor.created_at);
    remember(supervisor.updated_at);
    remember(supervisor.result_updated_at);
  }
  campaigns.forEach((campaign) => {
    remember(campaign.created_at);
    remember(campaign.started_at);
    remember(campaign.finished_at);
  });
  const earliest = knownTimes.length ? Math.min(...knownTimes) : null;

  const events = [];
  let order = 0;
  function addEvent({ kind, time = null, anchor = null, title, detail = "", refs = [], extraSearch = "" }) {
    const label = TRACE_KIND_LABELS[kind] || kind;
    const cleanRefs = refs.filter((ref) => ref !== undefined && ref !== null && String(ref).trim() !== "").map(String);
    const search = [label, title, detail, ...cleanRefs, extraSearch, task.id, task.display_id]
      .filter(Boolean)
      .join(" ")
      .replace(/\s+/g, " ")
      .toLowerCase();
    events.push({
      kind,
      time,
      anchor: anchor == null ? earliest : anchor,
      title,
      detail,
      refs: cleanRefs,
      search,
      order: order++
    });
  }

  // Task created.  The current stage is just a projection, so it is not a
  // separate timeline event; it remains visible in the task header.
  addEvent({
    kind: "task",
    time: task.created_at || null,
    anchor: traceMs(task.created_at) ?? earliest,
    title: `创建 · ${task.display_id || task.id}`,
    detail: `${task.title || "未命名任务"}${task.current_revision_id ? ` · ${task.current_revision_id}` : ""}`,
    refs: [`task ${task.id}`],
    extraSearch: task.subtitle || ""
  });

  // Supervisor binding milestone.  This replaces the old "current state" row:
  // a timeline should show when the binding started, not repeat the header badge.
  if (supervisor.status === "ready" || supervisor.status === "demo") {
    addEvent({
      kind: "supervisor",
      time: supervisor.created_at || null,
      anchor: traceMs(supervisor.created_at) ?? earliest,
      title: `绑定 · ${supervisor.state || "UNKNOWN"}`,
      detail: `${supervisor.state_is_terminal ? "终态" : "非终态"} · ${supervisor.supervisor_display_id || "—"} · model ${supervisor.model || "服务端未投影"}`,
      refs: [
        supervisor.remote_session_id ? `session ${supervisor.remote_session_id}` : "session —",
        supervisor.prompt_digest
          ? `prompt ${supervisor.prompt_digest}${supervisor.prompt_bytes != null ? ` · ${supervisor.prompt_bytes}B` : ""}`
          : null
      ]
    });
  } else if (supervisor.status === "absent") {
    addEvent({
      kind: "supervisor",
      time: null,
      title: "无 Supervisor 绑定",
      detail: "该任务没有 Supervisor 会话；仅展示任务与测试活动投影。",
      refs: [`task ${task.id}`]
    });
  } else if (supervisor.status === "error") {
    const error = supervisor.error || {};
    addEvent({
      kind: "error",
      time: null,
      title: "Supervisor 读取失败",
      detail: `${error.code || "ERROR"}${error.status ? ` · HTTP ${error.status}` : ""} · ${error.message || "控制面请求未成功。"}`,
      refs: [supervisor.endpoint ? `endpoint ${supervisor.endpoint}` : null]
    });
  }

  // A degraded session stays visible as an error; healthy session messages are
  // intentionally not duplicated here because the conversation panel owns them.
  const sessionDegraded = Boolean(session && session.status === "error");
  if (session && session.status !== "ready") {
    if (session.status === "unbound") {
      addEvent({
        kind: "session",
        time: null,
        anchor: traceMs(supervisor.updated_at) ?? earliest,
        title: "会话未绑定",
        detail: "Supervisor 尚未绑定远端会话；会话内容不可用。",
        refs: [session.endpoint ? `endpoint ${session.endpoint}` : null]
      });
    } else if (session.status === "error") {
      const error = session.error || {};
      addEvent({
        kind: "error",
        time: null,
        anchor: traceMs(supervisor.updated_at) ?? earliest,
        title: "会话读取失败",
        detail: `${error.code || "ERROR"}${error.status ? ` · HTTP ${error.status}` : ""} · ${error.message || "控制面请求未成功。"}`,
        refs: [session.endpoint ? `endpoint ${session.endpoint}` : null]
      });
    } else if (session.status === "absent" || session.status === "missing") {
      addEvent({
        kind: "session",
        time: null,
        title: "会话不存在",
        detail: "该任务没有可读取的会话投影。",
        refs: [session.endpoint ? `endpoint ${session.endpoint}` : null]
      });
    }
  }

  // Campaign created/status, round rows, artifacts and outcome.
  if (view.taskCampaignError) {
    const error = view.taskCampaignError;
    addEvent({
      kind: "error",
      time: null,
      title: "测试活动读取失败",
      detail: `${error.code || "ERROR"}${error.status != null ? ` · HTTP ${error.status}` : ""} · ${error.message || "控制面请求未成功。"}`,
      refs: [error.endpoint ? `endpoint ${error.endpoint}` : null]
    });
  }
  campaigns.forEach((campaign) => {
    const createdMs = traceMs(campaign.created_at);
    const startedMs = traceMs(campaign.started_at);
    const finishedMs = traceMs(campaign.finished_at);
    const baseAnchor = createdMs ?? startedMs ?? earliest;
    const statusAnchor = finishedMs ?? startedMs ?? createdMs ?? earliest;
    addEvent({
      kind: "campaign",
      time: campaign.created_at || null,
      anchor: createdMs ?? baseAnchor,
      title: `创建 · ${campaign.id}`,
      detail: `${campaign.title || campaign.scenario} · ${campaign.rounds} 轮 · bench ${campaign.bench} · node ${campaign.node_id || "—"}`,
      refs: [`task ${campaign.task_id || "—"}`, campaign.command_id ? `command ${campaign.command_id}` : null],
      extraSearch: `${campaign.scenario} ${campaign.bench}`
    });
    if (campaign.started_at) {
      addEvent({
        kind: "campaign",
        time: campaign.started_at,
        anchor: startedMs ?? baseAnchor,
        title: "开始执行",
        detail: `${campaign.scenario} · ${campaign.rounds} 轮 · bench ${campaign.bench}`,
        refs: [campaign.command_id ? `command ${campaign.command_id}` : null],
        extraSearch: `${campaign.scenario} start`
      });
    }
    if (campaign.finished_at) {
      const duration = traceDuration(campaign.started_at || campaign.created_at, campaign.finished_at);
      addEvent({
        kind: "campaign",
        time: campaign.finished_at,
        anchor: finishedMs ?? statusAnchor,
        title: `执行结束 · ${campaign.status}`,
        detail: `已回传 ${campaign.rounds_count} / ${campaign.rounds} · 完成 ${campaign.completed_rounds} · 结果 ${campaign.outcome.label}${campaign.outcome.derived ? "（derived）" : ""}${duration ? ` · 耗时 ${duration}` : ""} · 命令 ${campaign.command_status || "—"}`,
        refs: [
          `basis ${campaign.outcome.basis}`,
          campaign.error_code ? `error ${campaign.error_code}` : null,
          ...campaign.notes.map((note) => `note ${note}`)
        ],
        extraSearch: `${campaign.outcome.verdict || ""} ${campaign.scenario} ${campaign.rounds_count}/${campaign.rounds} finish`
      });
    } else {
      addEvent({
        kind: "campaign",
        time: campaign.started_at || campaign.created_at || null,
        anchor: statusAnchor,
        title: `当前状态 · ${campaign.status}`,
        detail: `已回传 ${campaign.rounds_count} / ${campaign.rounds} · 活动尚未结束 · 命令 ${campaign.command_status || "—"}`,
        refs: [campaign.error_code ? `error ${campaign.error_code}` : null],
        extraSearch: `${campaign.scenario} ${campaign.status} active`
      });
    }
    const artifactFiles = campaign.artifact_files || [];
    if (artifactFiles.length || campaign.artifact_entries.length) {
      const preview = artifactFiles.length
        ? artifactFiles.map((file) => `${file.name} (${formatBytes(file.size_bytes)})`).join(" · ")
        : campaign.artifact_entries.map(([key, value]) => `${key}: ${value}`).join(" · ");
      addEvent({
        kind: "artifact",
        time: null,
        anchor: finishedMs ?? startedMs ?? createdMs ?? earliest,
        title: `产物 · ${artifactFiles.length || campaign.artifact_entries.length} 项`,
        detail: traceExcerpt(preview, 240),
        refs: [`campaign ${campaign.id}`]
      });
    }
  });

  // Task-level result projection last (it is the outcome of the supervisor turn).
  if (supervisor.status === "ready" || supervisor.status === "demo") {
    const resultAnchor = traceMs(supervisor.result_updated_at) ?? traceMs(supervisor.updated_at) ?? earliest;
    if (supervisor.result_available) {
      const duration = traceDuration(supervisor.created_at, supervisor.result_updated_at || supervisor.updated_at);
      addEvent({
        kind: "result",
        time: supervisor.result_updated_at || supervisor.updated_at || null,
        anchor: resultAnchor,
        title: `任务 · ${supervisor.state}`,
        detail: `${traceExcerpt(supervisor.result_summary)}${duration ? ` · Supervisor 耗时 ${duration}` : ""}`,
        refs: [
          `state ${supervisor.state}`,
          supervisor.result_updated_at ? `updated ${supervisor.result_updated_at}` : null
        ]
      });
    } else if (supervisor.result_error_code) {
      addEvent({
        kind: "error",
        time: supervisor.result_updated_at || supervisor.updated_at || null,
        anchor: resultAnchor,
        title: `任务结果不可用 · ${supervisor.result_error_code}`,
        detail: "Supervisor 已结束但服务端未投影 result.summary。",
        refs: [`state ${supervisor.state}`]
      });
    } else if (String(supervisor.state) === "COMPLETED") {
      addEvent({
        kind: "result",
        time: supervisor.result_updated_at || supervisor.updated_at || null,
        anchor: resultAnchor,
        title: "任务 · 结果尚不可用",
        detail: "Supervisor 已到 COMPLETED，但服务端未投影 result.summary。",
        refs: [`state ${supervisor.state}`]
      });
    }
  }

  const seen = new Set();
  const unique = events.filter((event) => {
    const key = `${event.kind}|${event.title}|${event.detail}|${(event.refs || []).join(",")}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  events.splice(0, events.length, ...unique);

  events.sort((a, b) => {
    if (a.anchor == null && b.anchor == null) return a.order - b.order;
    if (a.anchor == null) return 1;
    if (b.anchor == null) return -1;
    return a.anchor - b.anchor || a.order - b.order;
  });
  return { events, sessionDegraded, degradedError: sessionDegraded ? (session.error || {}) : null };
}

function tracePanelMarkup(view, task) {
  const { events, sessionDegraded, degradedError } = traceEvents(view, task);
  const total = events.length;
  const rows = events.map((event) => {
    const time = event.time
      ? `<time datetime="${esc(event.time)}">${esc(localTimestamp(event.time))}</time>`
      : "—";
    return `
      <li class="trace-event" data-trace-event data-trace-kind="${esc(event.kind)}" data-trace-search="${esc(event.search)}">
        <span class="trace-event-time mono">${time}</span>
        <span class="trace-event-main">
          <span class="trace-event-title"><span class="trace-kind" data-kind="${esc(event.kind)}">${esc(TRACE_KIND_LABELS[event.kind] || event.kind)}</span>${esc(event.title)}</span>
          ${event.detail ? `<span class="trace-event-detail">${esc(event.detail)}</span>` : ""}
          ${event.refs.length ? `<span class="trace-event-refs">${event.refs.map((ref) => `<span class="trace-ref mono">${esc(ref)}</span>`).join("")}</span>` : ""}
        </span>
      </li>
    `;
  }).join("");
  const degraded = sessionDegraded
    ? `<p class="trace-degraded" data-trace-degraded role="status"><strong>会话内容不可用</strong> · ${esc(degradedError.code || "ERROR")}${degradedError.status ? ` · HTTP ${esc(String(degradedError.status))}` : ""}；以下仍显示任务、测试活动与逐轮事件，不伪造会话消息。</p>`
    : "";
  return `
    <details class="trace-panel" data-trace-panel>
      <summary class="trace-panel-summary">
        <span class="trace-panel-heading">
          <span class="trace-panel-title">执行时间线</span>
          <span class="trace-panel-note">只读 · 任务、Supervisor 与测试活动里程碑；消息请在会话中查看</span>
        </span>
        <span class="trace-panel-count"><span data-trace-total>${total}</span> 条事件</span>
      </summary>
      <div class="trace-panel-body">
        ${degraded}
        <div class="trace-toolbar">
          <label class="sr-only" for="task-trace-filter">过滤执行事件</label>
          <input class="input trace-filter" id="task-trace-filter" data-trace-filter type="search"
            placeholder="过滤事件（如 RECOGNIZED、campaign id、第 3 轮）" autocomplete="off" spellcheck="false">
          <span class="caption trace-filter-status" data-trace-filter-status role="status" aria-live="polite">显示 ${total} / ${total}</span>
        </div>
        <ol class="trace-list" data-trace-list>${rows}</ol>
        <p class="trace-empty" data-trace-empty hidden>没有匹配的事件。</p>
      </div>
    </details>
  `;
}

function chatDetailBody(view, route, task) {
  const supervisor = view.supervisor || { status: "absent" };
  const demo = supervisor.status === "demo";
  const apiMode = Boolean(view.meta && view.meta.server_authoritative);
  const session = view.session || (demo ? demoSessionMessages() : null);
  const subtitle = `<span class="mono">${esc(task.display_id)}</span> · task_id <span class="mono">${esc(task.id)}</span>`;
  return `
    <div class="task-detail-page">
    ${pageHeader({
      eyebrow: `Tasks · ${route.id} · ${view.scenario.id}`,
      title: esc(task.title),
      description: `${subtitle} · 任务详情即会话：查看历史并继续对话。`,
      actions: `${stateMarkup(supervisor.state)} ${deleteTaskButton(task, { disabled: demo })} ${button("返回任务列表", { href: "/console/tasks", kind: "quiet", icon: "arrow" })}`
    })}
    <div class="chat-layout" data-inspector-layout data-inspector-open="true">
      ${chatPanel(view, task, supervisor, session, demo)}
      ${inspectorMarkup(task, supervisor, session)}
    </div>
    <section class="panel task-result-panel" id="task-result">${resultMarkup(supervisor)}</section>
    ${tracePanelMarkup(view, task)}
    ${taskArtifactSection(view, task, apiMode)}
    ${taskCampaignSection(view, task, apiMode)}
    ${campaignActionDialog()}
    ${campaignTriggerDialog(view, task, apiMode)}
    ${deleteDialog()}
    ${artifactPreviewDialog()}
    </div>
  `;
}

function activeTaskRows(view, apiMode) {
  if (!apiMode) {
    const sup = demoSupervisor();
    return [{
      id: view.world.task.id,
      display_id: view.world.task.display_id,
      title: view.world.task.title,
      status: view.world.task.stage,
      updated_at: view.world.task.updated_at,
      node: "",
      progress: null,
      demo: true,
      supervisor_state: sup.state
    }];
  }
  const rows = Array.isArray(view.world.taskRows) ? view.world.taskRows : [];
  return rows.slice(0, 20);
}

// Cards stay legible at a glance: long ids/nodes are shortened, and the
// progress line is derived only from the server projection.
function markdownInline(value) {
  return esc(value)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

function renderMarkdown(value) {
  const lines = String(value || "").replace(/\r\n/g, "\n").split("\n");
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (/^```/.test(line)) {
      const code = [];
      i += 1;
      while (i < lines.length && !/^```/.test(lines[i])) {
        code.push(esc(lines[i]));
        i += 1;
      }
      if (i < lines.length) i += 1;
      out.push(`<pre><code>${code.join("\n")}</code></pre>`);
      continue;
    }
    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      const level = heading[1].length;
      out.push(`<h${level}>${markdownInline(heading[2])}</h${level}>`);
      i += 1;
      continue;
    }
    if (/^\s*\|/.test(line) && i + 1 < lines.length && /^\s*\|?[\s:|-]+\|/.test(lines[i + 1])) {
      const header = line;
      i += 2;
      const rows = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) {
        rows.push(lines[i]);
        i += 1;
      }
      const cells = (row) =>
        row
          .trim()
          .replace(/^\|/, "")
          .replace(/\|$/, "")
          .split("|")
          .map((cell) => markdownInline(cell.trim()));
      out.push(
        `<div class="chat-table"><table><thead><tr>${cells(header)
          .map((cell) => `<th>${cell}</th>`)
          .join("")}</tr></thead><tbody>${rows
          .map((row) => `<tr>${cells(row).map((cell) => `<td>${cell}</td>`).join("")}</tr>`)
          .join("")}</tbody></table></div>`
      );
      continue;
    }
    if (/^\s*[-*]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(`<li>${markdownInline(lines[i].replace(/^\s*[-*]\s+/, ""))}</li>`);
        i += 1;
      }
      out.push(`<ul>${items.join("")}</ul>`);
      continue;
    }
    if (!line.trim()) {
      i += 1;
      continue;
    }
    out.push(`<p>${markdownInline(line)}</p>`);
    i += 1;
  }
  return out.join("");
}

function compactRef(value, max = 18) {
  const raw = String(value == null ? "" : value).trim();
  if (!raw) return "—";
  return raw.length > max ? `${raw.slice(0, max - 1)}…` : raw;
}

function cardTypeBadge(kind) {
  const label = kind === "campaign" ? "测试活动" : "任务";
  return `<span class="task-card-type" data-card-type="${kind}">${label}</span>`;
}

function taskProgressLabel(progress) {
  const source = progress && typeof progress === "object" ? progress : {};
  if (source.percent_label) return String(source.percent_label);
  const total = Number(source.total);
  if (Number.isFinite(total) && total > 0) {
    const completed = Number(source.completed);
    return `${Number.isFinite(completed) ? completed : 0} / ${total}`;
  }
  return "—";
}

function conversationRow(row) {
  const demo = Boolean(row.demo);
  const updated = row.updated_at ? localTimestamp(row.updated_at) : "—";
  const status = row.status ? statusBadge(row.status) : badge("读取中", "plain");
  const node = compactRef(row.node);
  const progress = taskProgressLabel(row.progress);
  return `
    <article class="task-card task-card-task" data-task-row data-task-id="${esc(row.id)}">
      <a class="task-card-link" href="#/console/tasks/${encodeURIComponent(row.id)}/overview"
        aria-label="查看任务 ${esc(row.title || row.display_id || row.id)}">
        <div class="task-card-head">
          <span class="task-card-title">${esc(row.title || row.display_id || row.id)}</span>
          <span class="task-card-status" data-row-supervisor>${demo ? badge("DEMO", "plain") : status}</span>
        </div>
        <div class="task-card-idline">${cardTypeBadge("task")}<span class="task-card-id mono">${esc(row.display_id || row.id)}</span></div>
        <div class="task-card-meta">
          <span class="task-card-meta-item" title="执行节点"><span class="task-card-meta-label">节点</span><span class="mono">${esc(node)}</span></span>
          <span class="task-card-meta-item" title="轮次 / 进度"><span class="task-card-meta-label">轮次</span><span class="mono">${esc(progress)}</span></span>
        </div>
        <p class="task-card-result" data-row-result hidden></p>
        <div class="task-card-foot">
          <span class="caption">最后活动 <time class="mono" datetime="${esc(row.updated_at || "")}">${esc(updated)}</time></span>
        </div>
      </a>
      <div class="task-card-actions">${deleteTaskButton(row, { disabled: demo })}</div>
    </article>
  `;
}

function listLayer(view, apiMode) {
  const rows = activeTaskRows(view, apiMode);
  const body = rows.length
    ? `<div class="task-card-grid">${rows.map(conversationRow).join("")}</div>`
    : `<p class="muted small" role="status">暂无任务。点击“新建任务”创建第一个任务。</p>`;
  return panel({
    title: "任务卡片",
    note: apiMode
      ? `GET /api/v1/tasks · ${rows.length} 个任务`
      : `fixture 演示卡片 · ${rows.length} 个任务 · 非实时`,
    actions: apiMode ? button("刷新列表", { action: "refresh-tasks", small: true, icon: "refresh" }) : badge("DEMO", "plain"),
    body
  });
}

function supervisorErrorBody(view, route, task, supervisor) {
  const error = supervisor.error || {};
  return `
    ${pageHeader({
      eyebrow: `Tasks · ${route.id} · ${view.scenario.id}`,
      title: esc(task.title),
      description: `<span class="mono">${esc(task.display_id)}</span> · task_id <span class="mono">${esc(task.id)}</span>`,
      actions: `${deleteTaskButton(task, { disabled: !(view.meta && view.meta.server_authoritative) })} ${button("返回任务列表", { href: "/console/tasks", kind: "quiet", icon: "arrow" })}`
    })}
    ${deleteDialog()}
    ${stateBlock("error", {
      title: `Supervisor 读取失败 · ${error.code || "ERROR"}`,
      note: error.message || "控制面请求未成功。API 模式不回落 fixture。"
    })}
    <div class="row" style="margin-top:16px">
      <button class="btn" type="button" data-action="retry-task">${icon("refresh")}重试</button>
    </div>
    <p class="caption" style="margin-top:8px">API 模式不回落 fixture；失败事实与重试入口保持可见。</p>
  `;
}

const TASK_AREA_TABS = [
  { id: "tasks", path: "/console/tasks", label: "任务" },
  { id: "campaigns", path: "/console/tasks?panel=campaigns", label: "测试活动" }
];

function taskAreaTabs(current) {
  return tabs(TASK_AREA_TABS.map((item) => ({
    path: item.path,
    label: item.label,
    current: item.id === current
  })), "任务与测试活动");
}

function campaignRowsFor(view) {
  const raw = Array.isArray(view.campaigns)
    ? view.campaigns
    : Array.isArray(view.world && view.world.campaigns)
      ? view.world.campaigns
      : [];
  return raw.map(normalizeCampaign).filter((campaign) => campaign.id);
}

function campaignFor(view, campaignId) {
  if (view.campaign) return normalizeCampaign(view.campaign);
  if (!campaignId) return null;
  return campaignRowsFor(view).find((campaign) => campaign.id === campaignId) || null;
}

function campaignCounts(campaign) {
  return Object.entries(campaign.status_counts || {})
    .filter(([key]) => key);
}

function campaignStatusCountsMarkup(campaign) {
  const entries = campaignCounts(campaign);
  if (!entries.length) {
    return `<p class="muted small" role="status">服务端尚未返回 summary.status_counts；不推断成功或失败。</p>`;
  }
  return `<div class="row">${entries.map(([key, value]) => `
    <span class="badge tone-neutral">${esc(key)} <span class="mono">${esc(value)}</span></span>
  `).join("")}</div>`;
}

function campaignRoundTable(campaign) {
  const rows = campaign.round_rows || [];
  if (!rows.length) {
    return stateBlock("empty", {
      title: "暂无逐轮行",
      note: campaign.status === "RUNNING"
        ? "命令仍在执行，节点尚未回传逐轮结果；已回传计数仅来自当前投影。"
        : "节点结果未包含逐轮行（可能只有 summary 或产物路径）；不伪造逐轮证据。"
    });
  }
  return table({
    head: ["轮次", "状态", "关键词 / 命令", "证据", "来源"],
    rows: rows.map((row) => [
      `<span class="mono">${esc(row.round)}</span>`,
      statusBadge(row.status),
      esc(row.wake || row.command || row.intent || "—"),
      row.evidence && row.evidence.length
        ? row.evidence.map((item) => `<span class="mono cell-path">${esc(item)}</span>`).join("<br>")
        : "—",
      `${esc(row.source || "—")}${row.derived ? ` ${badge("derived", "neutral")}` : ""}`
    ]),
    caption: "derived 行来自 summary 聚合计数，不是逐案原始证据。"
  });
}

function formatBytes(value) {
  const bytes = Number(value);
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
}

function artifactViewable(file) {
  const name = String(file.name || "").toLowerCase();
  const media = String(file.media_type || "").toLowerCase();
  return media.startsWith("text/")
    || media.includes("json")
    || /\.(log|txt|csv|json|md|ya?ml|xml|html?)$/.test(name);
}

function artifactActions(campaign, file) {
  const attrs = `data-campaign-id="${esc(campaign.id)}" data-artifact-name="${esc(file.name)}"`;
  return `<span class="row">
    ${artifactViewable(file) ? `<button class="btn btn-sm" type="button" data-artifact-action="view" ${attrs}>查看</button>` : ""}
    ${file.downloadable === false ? "" : `<button class="btn btn-sm" type="button" data-artifact-action="download" ${attrs}>下载</button>`}
  </span>`;
}

function artifactFileTable(campaign, options = {}) {
  const files = campaign.artifact_files || [];
  if (!files.length) {
    const entries = campaign.artifact_entries || [];
    if (!entries.length) {
      return `<p class="muted small" role="status">平台尚未收到可下载的日志或产物文件。</p>`;
    }
    return table({
      head: ["节点产物", "路径"],
      rows: entries.map(([key, value]) => [
        `<span class="mono">${esc(key)}</span>`,
        `<span class="mono cell-path">${esc(value)}</span>`
      ])
    });
  }
  return table({
    head: options.showCampaign
      ? ["文件", "来源活动", "大小", "上传时间", "操作"]
      : ["文件", "大小", "上传时间", "操作"],
    rows: files.map((file) => {
      const base = [
        `<span class="mono">${esc(file.name)}</span>`,
        formatBytes(file.size_bytes),
        esc(file.uploaded_at ? localTimestamp(file.uploaded_at) : "—")
      ];
      if (options.showCampaign) {
        base.splice(1, 0, `<span class="mono cell-path">${esc(campaign.title || campaign.id)}</span>`);
      }
      base.push(artifactActions(campaign, file));
      return base;
    }),
    caption: "文件由节点上传并由控制面保存；下载会重新校验大小和 digest。"
  });
}

function campaignArtifactTable(campaign) {
  return artifactFileTable(campaign);
}

function taskArtifactFiles(view, task) {
  return (Array.isArray(view.taskCampaigns) ? view.taskCampaigns : [])
    .map(normalizeCampaign)
    .filter((campaign) => campaign.id && task && campaign.task_id === task.id)
    .flatMap((campaign) => campaign.artifact_files.map((file) => ({ campaign, file })));
}

function taskArtifactSection(view, task, apiMode) {
  if (!apiMode) return "";
  const entries = taskArtifactFiles(view, task);
  if (!entries.length) {
    return panel({
      title: "结果与日志",
      note: "平台上传的测试产物、串口日志与汇总文件。",
      body: `<p class="muted small" role="status">该任务还没有已上传的日志或产物。节点可能只回传了会话摘要，原始日志尚未上传。</p>`
    });
  }
  const campaigns = [];
  const seen = new Set();
  entries.forEach(({ campaign }) => {
    if (seen.has(campaign.id)) return;
    seen.add(campaign.id);
    campaigns.push(campaign);
  });
  return panel({
    title: "结果与日志",
    note: "查看文本日志，或下载原始文件；内容来自平台产物库，不是模型摘要。",
    body: `${campaigns.map((campaign) => artifactFileTable(campaign, { showCampaign: campaigns.length > 1 })).join("")}
      <p class="caption" data-artifact-status role="status" aria-live="polite"></p>`
  });
}

function artifactPreviewDialog() {
  return `
    <dialog class="task-delete-dialog artifact-preview-dialog" id="artifact-preview-dialog" role="dialog" aria-modal="true" aria-labelledby="artifact-preview-title">
      <div class="task-dialog-card artifact-preview-card">
        <div class="task-dialog-head">
          <h2 class="task-dialog-title mono" id="artifact-preview-title" data-artifact-preview-title>日志预览</h2>
          <button class="icon-button" type="button" data-artifact-preview-close aria-label="关闭">${icon("close")}</button>
        </div>
        <p class="caption" data-artifact-preview-status role="status" aria-live="polite"></p>
        <pre class="artifact-preview-body mono" data-artifact-preview-body></pre>
        <div class="row task-dialog-actions">
          <button class="btn" type="button" data-artifact-preview-close>关闭</button>
        </div>
      </div>
    </dialog>
  `;
}

function campaignCard(campaign, options = {}) {
  const href = `/console/tasks?panel=campaigns&campaignId=${encodeURIComponent(campaign.id)}`;
  const title = campaign.title || campaign.scenario || campaign.id;
  const rounds = `${campaign.rounds_count} / ${campaign.rounds}`;
  const node = compactRef(campaign.node_id);
  const created = campaign.created_at ? localTimestamp(campaign.created_at) : "—";
  return `
    <article class="task-card campaign-card" data-campaign-row data-campaign-id="${esc(campaign.id)}">
      <a class="task-card-link" href="#${esc(href)}" aria-label="查看测试活动 ${esc(campaign.id)}">
        <div class="task-card-head">
          <span class="task-card-title">${esc(title)}</span>
          <span class="task-card-status">${badge(campaign.outcome.label, campaign.outcome.tone)}</span>
        </div>
        <div class="task-card-idline">${cardTypeBadge("campaign")}<span class="task-card-id mono">${esc(campaign.id)}</span></div>
        <div class="task-card-meta">
          <span class="task-card-meta-item" title="节点"><span class="task-card-meta-label">节点</span><span class="mono">${esc(node)}</span></span>
          <span class="task-card-meta-item" title="已回传 / 目标轮次"><span class="task-card-meta-label">轮次</span><span class="mono">${esc(rounds)}</span></span>
        </div>
        <div class="task-card-foot">
          <span class="task-card-statusline" title="命令状态 ${esc(campaign.command_status || "—")}">${statusBadge(campaign.status)}</span>
          <span class="caption">创建 <time class="mono" datetime="${esc(campaign.created_at || "")}">${esc(created)}</time></span>
        </div>
      </a>
      <div class="task-card-actions">${campaignActionButton(campaign, { disabled: options.disabled === true || campaign.demo })}</div>
    </article>
  `;
}

function campaignCardGrid(campaigns, options = {}) {
  return `<div class="task-card-grid task-card-grid-campaigns">${campaigns
    .map((campaign) => campaignCard(campaign, options))
    .join("")}</div>`;
}

function taskCampaignErrorMarkup(error, taskId, endpoint) {
  return `
    <div class="task-campaign-error" data-task-campaign-error role="status">
      <p class="small"><span class="mono">${esc(error.code || "ERROR")}</span>：${esc(error.message || "控制面请求未成功。")}</p>
      <p class="caption">task_id <span class="mono">${esc(taskId || "—")}</span> · endpoint <span class="mono">${esc(endpoint || error.endpoint || "—")}</span></p>
      <button class="btn btn-sm" type="button" data-campaign-refresh>${icon("refresh")}重试测试活动</button>
    </div>
  `;
}

function taskCampaignListMarkup(campaigns, options = {}, taskId = "", endpoint = "") {
  if (!campaigns.length) {
    return `
      <p class="muted small task-campaign-empty" data-task-campaign-empty role="status">
        该任务暂无测试活动。测试活动只会显示 <span class="mono">task_id = ${esc(taskId || "—")}</span> 的记录；
        历史未关联的活动仍保留在“测试活动”标签。
      </p>
    `;
  }
  return `${campaignCardGrid(campaigns, options)}<p class="caption task-campaign-endpoint">来源 <span class="mono">${esc(endpoint || `GET /api/v1/test-campaigns?task_id=${taskId}`)}</span> · ${campaigns.length} 条</p>`;
}

function campaignTriggerDialog(view, task, apiMode) {
  const defaultNode = view.taskNode && typeof view.taskNode === "object" ? view.taskNode : {};
  const disabled = !apiMode || !task || !task.id;
  const reason = !apiMode ? "fixture 演示模式不会触发真实测试活动" : !task || !task.id ? "缺少 task_id" : "";
  return `
    <dialog class="task-create-dialog campaign-trigger-dialog" id="campaign-trigger-dialog" role="dialog" aria-modal="true" aria-labelledby="campaign-trigger-title">
      <div class="task-dialog-card">
        <div class="task-dialog-head">
          <h2 class="task-dialog-title" id="campaign-trigger-title">触发测试活动</h2>
          <button class="icon-button" type="button" data-campaign-trigger-cancel aria-label="关闭">${icon("close")}</button>
        </div>
        <p class="task-dialog-note">触发后控制面会入队一条 <span class="mono">test.run</span> 节点命令；不会创建 Task 或 Supervisor 会话。活动状态只以服务端返回为准。</p>
        <p class="task-dialog-target mono">task_id ${esc(task && task.id ? task.id : "—")}</p>
        <form id="campaign-trigger-form" data-default-node-id="${esc(defaultNode.id || "")}" data-default-node-display="${esc(defaultNode.display_id || "WIN009")}" data-api-mode="${apiMode ? "true" : "false"}" aria-describedby="campaign-trigger-note" novalidate>
          <div class="field">
            <label for="campaign-trigger-scenario">场景 scenario</label>
            <select class="select" id="campaign-trigger-scenario" name="scenario">
              <option value="wake-recognition">wake-recognition</option>
            </select>
          </div>
          <div class="field">
            <label for="campaign-trigger-rounds">轮次 rounds</label>
            <select class="select" id="campaign-trigger-rounds" name="rounds">
              <option value="5">5</option>
              <option value="489">489</option>
            </select>
          </div>
          <div class="field">
            <label for="campaign-trigger-bench">基准 bench</label>
            <input class="input" id="campaign-trigger-bench" name="bench" value="tcl003.json" maxlength="200" required>
            <span class="hint">必须是 JSON 文件名，例如 tcl003.json。</span>
          </div>
          <div class="field">
            <label for="campaign-trigger-node">执行节点 node</label>
            <select class="select" id="campaign-trigger-node" name="node_id" data-campaign-node required aria-busy="true">
              <option value="">正在读取节点…</option>
            </select>
            <p class="hint" data-campaign-node-status role="status" aria-live="polite">默认使用任务节点；读取失败时不提交。</p>
          </div>
          <p class="caption" id="campaign-trigger-note">${apiMode ? "提交后刷新该任务的测试活动列表；节点状态与轮次结果不会在本地推断。" : esc(reason)}</p>
          <div class="row task-dialog-actions">
            <button class="btn btn-primary" type="submit" data-campaign-trigger-submit${disabled ? ' disabled aria-disabled="true"' : ""}>触发测试活动</button>
            <button class="btn" type="button" data-campaign-trigger-cancel>取消</button>
            <span class="caption" data-campaign-trigger-status role="status" aria-live="polite"></span>
          </div>
          <div class="form-feedback" data-campaign-trigger-feedback role="alert" aria-live="assertive" hidden></div>
        </form>
      </div>
    </dialog>
  `;
}

function taskCampaignSection(view, task, apiMode) {
  const campaigns = (Array.isArray(view.taskCampaigns) ? view.taskCampaigns : [])
    .map(normalizeCampaign)
    .filter((campaign) => campaign.id && task && campaign.task_id === task.id);
  const error = view.taskCampaignError;
  const endpoint = view.taskCampaignEndpoint || `GET /api/v1/test-campaigns?task_id=${task.id}`;
  const triggerDisabled = !apiMode;
  const actions = `
    <button class="btn btn-sm btn-primary" type="button" data-campaign-trigger-open${triggerDisabled ? ' disabled aria-disabled="true" title="fixture 演示模式不会触发真实测试活动"' : ""}>${icon("play")}触发测试活动</button>
    <button class="btn btn-sm" type="button" data-campaign-refresh>${icon("refresh")}刷新测试活动</button>
  `;
  const content = error
    ? taskCampaignErrorMarkup(error, task.id, endpoint)
    : `<div data-task-campaign-list>${taskCampaignListMarkup(campaigns, { disabled: !apiMode }, task.id, endpoint)}</div>`;
  const body = `
    <div data-task-campaign-section data-task-id="${esc(task.id)}" data-endpoint="${esc(endpoint)}">
      ${content}
      <p class="caption task-campaign-status" data-task-campaign-status role="status" aria-live="polite"></p>
    </div>
  `;
  return panel({
    title: "测试活动",
    note: apiMode
      ? `该任务拥有的确定性节点测试 · ${esc(endpoint)}`
      : "FIXTURE · 演示活动；不会触发真实执行",
    actions,
    body
  });
}

function campaignListBody(view, apiMode) {
  const campaigns = campaignRowsFor(view);
  const error = view.campaignError;
  const head = pageHeader({
    eyebrow: `Tasks · 测试活动 · ${view.scenario.id}`,
    title: "测试活动",
    description: "确定性的节点测试（test.run）记录；按服务端 campaign 状态、轮次计数与 summary 展示。API 模式读取 <span class=\"mono\">GET /api/v1/test-campaigns</span>，失败不回退 fixture。",
    actions: `${apiMode ? badge("API · server_authoritative", "action") : badge("FIXTURE · DEMO", "plain")}
      ${apiMode ? button("刷新测试活动", { action: "refresh-campaigns", small: true, icon: "refresh" }) : ""}`
  });
  const tabsHtml = taskAreaTabs("campaigns");
  if (error) {
    return `
      ${head}
      ${tabsHtml}
      ${stateBlock("error", {
        title: `测试活动读取失败 · ${error.code || "ERROR"}`,
        note: error.message || "控制面请求未成功。API 模式不回退 fixture。"
      })}
      <div class="row" style="margin-top:16px">
        <button class="btn btn-primary" type="button" data-action="refresh-campaigns">${icon("refresh")}重试</button>
        <a class="btn" href="#/console/tasks">${icon("arrow")}返回任务</a>
      </div>
      <p class="caption" style="margin-top:8px">HTTP <span class="mono">${esc(String(error.status ?? "—"))}</span> · endpoint <span class="mono">${esc(error.endpoint || "—")}</span></p>
    `;
  }
  if (!campaigns.length) {
    return `
      ${head}
      ${tabsHtml}
      ${stateBlock("empty", {
        title: "暂无测试活动",
        note: apiMode
          ? "GET /api/v1/test-campaigns 返回 0 条；空态不代表节点没有执行历史。"
          : "fixture 演示数据为空；fixture 不是服务端事实。"
      })}
    `;
  }
  return `
    ${head}
    ${tabsHtml}
    ${panel({
      title: "测试活动列表",
      note: apiMode
        ? `GET /api/v1/test-campaigns · ${campaigns.length} 条 · 结果列中的 PASS 仅在服务端 SUCCEEDED 且 summary 覆盖全部轮次时显示`
        : "FIXTURE 演示活动 · 非服务端事实；不会伪装 API 成功",
      body: `<div class="task-card-grid task-card-grid-campaigns">${campaigns.map((campaign) => campaignCard(campaign, { disabled: !apiMode })).join("")}</div>`
    })}
    ${campaignActionDialog()}
    ${inlineNote("列表直接读取控制面投影；“已完成”是已回传行数，不是推测的执行进度。FAILED / RUNNING 永不显示为 PASS。")}
  `;
}

function campaignDetailBody(view, params, apiMode) {
  const campaign = campaignFor(view, params.campaignId);
  if (!campaign) {
    return `
      ${pageHeader({
        eyebrow: `Tasks · 测试活动 · ${view.scenario.id}`,
        title: "测试活动详情",
        description: `未找到 campaign <span class="mono">${esc(params.campaignId || "—")}</span>。`,
        actions: button("返回测试活动", { href: "/console/tasks?panel=campaigns", kind: "quiet", icon: "arrow" })
      })}
      ${taskAreaTabs("campaigns")}
      ${stateBlock("empty", {
        title: "活动不存在或不可见",
        note: "API 模式只会展示服务端返回的活动；不会用 fixture 冒充成功。"
      })}
    `;
  }
  const outcome = campaign.outcome;
  const counts = campaignCounts(campaign);
  const command = campaign.command || {};
  const commandRows = [
    ["命令状态", campaign.command_status ? statusBadge(campaign.command_status) : "—"],
    ["command_id", `<span class="mono cell-path">${esc(campaign.command_id || "—")}</span>`],
    ["tool_id", `<span class="mono">${esc(command.tool_id || "—")}</span>`],
    ["exit_code", `<span class="mono">${esc(command.exit_code ?? "—")}</span>`],
    ["error_code", `<span class="mono">${esc(campaign.error_code || command.error_code || "—")}</span>`],
    ["truncated", `<span class="mono">${esc(String(Boolean(command.truncated)))}</span>`],
    ["command_set", `<span class="mono">${esc(campaign.command_set || "—")}</span>`],
    ["notes", esc((campaign.notes || []).join(" · ") || "—")]
  ];
  return `
    ${pageHeader({
      eyebrow: `Tasks · 测试活动 · ${view.scenario.id}`,
      title: esc(campaign.title || campaign.scenario),
      description: `<span class="mono">${esc(campaign.id)}</span> · node <span class="mono">${esc(campaign.node_id || "—")}</span> · ${esc(campaign.scenario)} · bench <span class="mono">${esc(campaign.bench)}</span> · 创建 ${esc(localTimestamp(campaign.created_at))}`,
      actions: `${apiMode ? badge("API · server_authoritative", "action") : badge("FIXTURE · DEMO", "plain")}
        ${campaign.demo ? badge("DEMO", "plain") : ""}
        ${button("返回测试活动", { href: "/console/tasks?panel=campaigns", kind: "quiet", icon: "arrow" })}`
    })}
    ${taskAreaTabs("campaigns")}
    ${stats([
      { label: "目标轮次", value: esc(campaign.rounds), note: "campaign.rounds" },
      { label: "已回传", value: `${esc(campaign.rounds_count)} / ${esc(campaign.rounds)}`, note: "round_rows 计数" },
      { label: "完成轮次", value: esc(campaign.completed_rounds), note: "summary.completed_rounds" },
      { label: "结果", value: badge(outcome.label, outcome.tone), note: outcome.basis },
      { label: "状态", value: statusBadge(campaign.status), note: campaign.command_status || "—" }
    ])}
    ${panel({
      title: "进度",
      note: campaign.status === "RUNNING" ? "RUNNING：0% 只表示当前已回传计数，不代表失败、完成或最终判定。" : "计数来自服务端投影，不作为完成度承诺。",
      body: progressBar({ mode: "COUNTS", completed: campaign.rounds_count, total: campaign.rounds })
    })}
    ${panel({
      title: "汇总计数",
      note: "summary.status_counts 原样展示；未知状态不映射为成功。",
      body: campaignStatusCountsMarkup(campaign)
    })}
    ${panel({
      title: "逐轮结果",
      note: "round / status / keyword-or-command / evidence；derived 标记表示来自 summary 聚合。",
      body: campaignRoundTable(campaign)
    })}
    ${panel({
      title: "命令与产物",
      note: "命令生命周期与产物路径；失败保持失败，不因产物存在而变为 PASS。",
      body: `${kv(commandRows)}<div style="margin-top:16px">${campaignArtifactTable(campaign)}</div>`
    })}
    ${inlineNote("PASS 只在服务端 SUCCEEDED、summary 覆盖全部轮次且无失败计数时显示；FAILED / RUNNING / TIMEOUT 永不显示为 PASS。")}
    ${artifactPreviewDialog()}
  `;
}

export function render({ route, params, view }) {
  const task = view.world.task;
  const generic = genericState(view, "任务");
  if (route.id === "TK-01") {
    const apiMode = Boolean(view.meta && view.meta.server_authoritative);
    if (params.panel === "campaigns") {
      return params.campaignId ? campaignDetailBody(view, params, apiMode) : campaignListBody(view, apiMode);
    }
    const head = pageHeader({
      eyebrow: `Tasks · TK-01 · ${view.scenario.id}`,
      title: "任务",
      description: "任务以卡片展示；点击卡片进入任务会话详情。“新建任务”仍在原位置：描述任务后创建任务与会话，并进入任务详情。",
      actions: `${apiMode ? badge("API · server_authoritative", "action") : badge("FIXTURE · DEMO", "plain")} ${newTaskButton(apiMode)}`
    });
    if (generic) return head + generic;
    return `
      ${head}
      ${taskAreaTabs("tasks")}
      ${stateBanners(view)}
      ${listLayer(view, apiMode)}
      ${taskCreateDialog(view, apiMode)}
      ${deleteDialog()}
      ${campaignActionDialog()}
      ${inlineNote("任务创建后自动绑定一个 Supervisor 会话；后续消息进入同一任务会话，不另开独立 Session 页。“测试活动”标签展示确定性节点测试记录。")}
    `;
  }

  if (generic) return taskHeader(view, route, task) + generic;

  const run = view.world.runs[0];
  const attempt = view.world.attempts[0];
  switch (route.id) {
    case "TK-02": {
      const supervisor = view.supervisor || {};
      if (supervisor.status === "error") return supervisorErrorBody(view, route, task, supervisor);
      if (supervisor.status === "ready" || supervisor.status === "demo") {
        return chatDetailBody(view, route, task);
      }
      // No supervisor binding: keep the traditional task detail projection.
      return overviewBody(view, route, task);
    }
    case "TK-03": return revisionsBody(view, route, task);
    case "TK-04": return planBody(view, route, task);
    case "TK-05": return runsBody(view, route, task);
    case "TK-06": return evidenceBody(view, route, task);
    case "TK-07": return verdictBody(view, route, task);
    case "TK-08": return liveBody(view, route, task, run, attempt);
    case "TK-09": return knowledgeBody(view, route, task);
    default: return overviewBody(view, route, task);
  }
}

// ---------------------------------------------------------------------------
// Page hydration: conversation polling/composer and list supervisor projection.
// These bind to the rendered markup and never construct control-plane URLs.
// ---------------------------------------------------------------------------

function messageSignature(messages) {
  return (messages || [])
    .map((message) => `${message.message_id || ""}|${message.role || ""}|${message.created_at || ""}|${String(message.text || "").length}`)
    .join("\n");
}

function hydrateTaskList({ host, mode }) {
  if (mode !== "api") return null;
  const rows = Array.from(host.querySelectorAll("[data-task-row][data-task-id]"));
  if (!rows.length) return null;

  let disposed = false;
  const queue = rows.slice();
  const worker = async () => {
    while (queue.length && !disposed) {
      const row = queue.shift();
      const taskId = row.dataset.taskId;
      const slot = row.querySelector("[data-row-supervisor]");
      const resultSlot = row.querySelector("[data-row-result]");
      if (!slot) continue;
      const supervisor = await loadTaskSupervisor(taskId);
      if (disposed || !slot.isConnected) return;
      if (supervisor.status === "ready") {
        slot.innerHTML = stateMarkup(supervisor.state);
        if (resultSlot) {
          if (supervisor.result_available && supervisor.result_summary) {
            resultSlot.hidden = false;
            row.classList.add("has-result");
            resultSlot.innerHTML = `<span class="task-card-result-label">结果</span>${esc(supervisor.result_summary)}`;
          } else if (String(supervisor.state) === "COMPLETED") {
            resultSlot.hidden = false;
            row.classList.add("has-result");
            resultSlot.innerHTML = `<span class="task-card-result-label">结果</span>任务已完成，结果尚不可用`;
          } else {
            resultSlot.hidden = true;
            row.classList.remove("has-result");
            resultSlot.textContent = "";
          }
        }
      } else if (supervisor.status === "demo") {
        slot.innerHTML = badge("DEMO", "plain");
      } else if (supervisor.status === "absent") {
        slot.innerHTML = badge("NO SUPERVISOR", "neutral");
      } else {
        slot.innerHTML = badge("ERROR", "attention");
        const error = supervisor.error || {};
        slot.setAttribute("title", `${error.code || "ERROR"}${error.message ? ` · ${error.message}` : ""}`);
      }
    }
  };
  void Promise.all([worker(), worker(), worker(), worker()]);
  return () => {
    disposed = true;
  };
}

function hydrateChat({ root, taskId, mode, initialSupervisor, initialSession, refresh }) {
  const history = root.querySelector("[data-chat-history]");
  const form = root.querySelector("[data-chat-form]");
  const input = root.querySelector("[data-chat-input]");
  const send = root.querySelector("[data-chat-send]");
  const statusEl = root.querySelector("[data-chat-status]");
  const stateEl = root.querySelector("[data-chat-state]");
  const refreshedEl = root.querySelector("[data-chat-refreshed]");
  const resultEl = document.querySelector("[data-chat-result]");
  const errorEl = root.querySelector("[data-chat-error]");
  const runStatusEl = root.querySelector("[data-agent-status]");
  const runLabelEl = root.querySelector("[data-agent-status-label]");
  const runElapsedEl = root.querySelector("[data-agent-elapsed]");
  const runActivityEl = root.querySelector("[data-agent-activity]");
  const refreshButton = root.querySelector('[data-action="refresh-chat"]');
  const inspectorLayout = root.closest("[data-inspector-layout]");
  const inspectorToggle = root.querySelector("[data-inspector-toggle]");
  const inspectorClose = root.querySelector("[data-inspector-close]");
  const demo = root.dataset.demo === "true";

  let supervisor = initialSupervisor || {};
  let session = initialSession || null;
  let disposed = false;
  let timer = null;
  let statusTimer = null;
  let polling = false;
  let busy = false;
  let followupWatching = false;
  let followupStartedAt = 0;
  let followupBaseline = 0;
  let followupNote = "";
  let watchTimer = null;
  let signature = messageSignature((session && session.messages) || []);
  let firstRender = true;

  const unboundNote = "会话尚未绑定，等待 Supervisor 启动…";
  const readyNote = "Enter 发送，Shift+Enter 换行。";

  function inspectorField(name) {
    return inspectorLayout ? inspectorLayout.querySelector(`[data-inspector-field="${name}"]`) : null;
  }

  function renderInspector() {
    if (!inspectorLayout) return;
    const sessionField = inspectorField("session");
    const modelField = inspectorField("model");
    const stateField = inspectorField("state");
    const refreshedField = inspectorField("refreshed");
    const countField = inspectorField("message_count");
    const resultField = inspectorField("result");
    const errorField = inspectorField("error");
    const values = inspectorValue(supervisor, session);
    if (sessionField) sessionField.textContent = supervisor.remote_session_id || "—";
    if (modelField) modelField.textContent = supervisor.model || "服务端未投影";
    if (stateField) stateField.innerHTML = stateMarkup(supervisor.state);
    if (refreshedField) refreshedField.textContent = refreshedEl ? refreshedEl.textContent : "—";
    if (countField) countField.textContent = values.count;
    if (resultField) resultField.textContent = values.result;
    if (errorField) errorField.textContent = values.error;
  }

  function setInspectorOpen(open) {
    if (!inspectorLayout || !inspectorToggle) return;
    inspectorLayout.dataset.inspectorOpen = open ? "true" : "false";
    inspectorToggle.setAttribute("aria-expanded", String(open));
  }

  function touchRefreshed() {
    if (!refreshedEl) return;
    const now = new Date();
    refreshedEl.textContent = localTimestamp(now.toISOString());
    refreshedEl.setAttribute("datetime", now.toISOString());
    renderInspector();
  }

  function activeFollowup() {
    return busy || followupWatching;
  }

  function followupReplySeen() {
    return ((session && session.messages) || [])
      .slice(followupBaseline)
      .some((message) => message && message.role === "assistant" && String(message.text || "").trim());
  }

  function finishFollowup(note) {
    if (watchTimer) window.clearTimeout(watchTimer);
    watchTimer = null;
    followupWatching = false;
    busy = false;
    const elapsed = followupStartedAt ? Date.now() - followupStartedAt : 0;
    followupStartedAt = 0;
    followupNote = note ? `${note} · ${runDurationLabel(elapsed)}` : "";
    updateAgentStatus();
  }

  function watchForFollowupReply() {
    followupWatching = true;
    updateAgentStatus();
    if (watchTimer) window.clearTimeout(watchTimer);
    watchTimer = window.setTimeout(() => {
      if (!followupWatching) return;
      const pending = history ? history.querySelector(".chat-row.is-pending") : null;
      if (pending) pending.remove();
      finishFollowup("本轮回复超时");
      setStatus("模型响应超时，请稍后刷新查看。", true);
      schedule();
    }, 120000);
  }

  function updateAgentStatus() {
    if (!runStatusEl) return;
    const following = activeFollowup();
    const visual = following ? { level: "running", label: "执行中" } : runStatusVisual(supervisor);
    runStatusEl.dataset.level = visual.level;
    if (runLabelEl) runLabelEl.textContent = visual.label;
    if (following) {
      const elapsed = Date.now() - (followupStartedAt || Date.now());
      const messages = (session && session.messages) || [];
      const last = lastAgentActivity(session);
      const tail = last && last.created_at ? ` · 最后活动 ${runClock(last.created_at)}` : "";
      if (runElapsedEl) runElapsedEl.textContent = runDurationLabel(elapsed);
      if (runActivityEl) {
        const activity = `模型回复中 · 已等待 ${runDurationLabel(elapsed)} · 会话 ${messages.length} 条${tail}`;
        if (runActivityEl.textContent !== activity) runActivityEl.textContent = activity;
      }
      return;
    }
    if (runActivityEl) {
      const activity = followupNote || agentActivity(supervisor, session);
      if (runActivityEl.textContent !== activity) runActivityEl.textContent = activity;
    }
    if (!runElapsedEl) return;
    if (supervisor.status === "error" || supervisor.status === "absent" || !supervisor.state) {
      runElapsedEl.textContent = "—";
      return;
    }
    const start = Date.parse(supervisor.created_at || runElapsedEl.dataset.start || "");
    const end = isTerminalState(supervisor.state)
      ? Date.parse(supervisor.updated_at || runElapsedEl.dataset.end || "")
      : Date.now();
    runElapsedEl.textContent = Number.isFinite(start) && Number.isFinite(end)
      ? runDurationLabel(end - start)
      : "—";
  }

  function setStatus(text, isError) {
    if (!statusEl) return;
    statusEl.textContent = text || "";
    statusEl.classList.toggle("is-error", Boolean(isError));
    applyLanguage(statusEl);
  }

  function setState(next) {
    supervisor = next || {};
    updateAgentStatus();
    if (stateEl) {
      if (supervisor.status === "ready" || supervisor.status === "demo") {
        stateEl.innerHTML = stateMarkup(supervisor.state);
      } else if (supervisor.status === "absent") {
        stateEl.innerHTML = badge("NO SUPERVISOR", "neutral");
      } else {
        stateEl.innerHTML = badge("ERROR", "attention");
      }
    }
    if (supervisor.status === "error") {
      const error = supervisor.error || {};
      if (errorEl) {
        errorEl.hidden = false;
        errorEl.innerHTML = `<span class="chat-result-label">${esc(error.code || "ERROR")}</span>${esc(error.message || "控制面请求未成功。")}`;
      }
      if (resultEl) {
        resultEl.hidden = true;
        resultEl.textContent = "";
      }
      renderInspector();
      return;
    }
    const state = String(supervisor.state || "UNKNOWN");
    if (resultEl) {
      if (state === "COMPLETED") {
        resultEl.hidden = false;
        resultEl.innerHTML = `<span class="chat-result-label">结果</span><div class="chat-result-body chat-text">${renderMarkdown(supervisor.result_available ? (supervisor.result_summary || "—") : "任务已完成，结果尚不可用")}</div>`;
      } else {
        resultEl.hidden = true;
        resultEl.textContent = "";
      }
    }
    if (errorEl) {
      if (state === "FAILED" || state === "STOPPED") {
        errorEl.hidden = false;
        errorEl.innerHTML = `<span class="chat-result-label">${esc(state)}</span>${esc(supervisor.result_error_code || state)}`;
      } else {
        errorEl.hidden = true;
        errorEl.textContent = "";
      }
    }
    renderInspector();
  }

  function bound() {
    return Boolean(supervisor && supervisor.remote_session_id && supervisor.remote_session_id !== "—");
  }

  function syncComposer() {
    const unavailable = Boolean(session && session.status === "error");
    const locked = activeFollowup();
    const disabled = demo || !bound() || locked || unavailable;
    if (input) input.disabled = disabled;
    if (send) send.disabled = disabled;
    if (demo || locked) return;
    if (unavailable) {
      setStatus("会话内容不可用；任务结果和测试活动仍可查看。", true);
      return;
    }
    if (!bound()) {
      setStatus(unboundNote, false);
    } else if (statusEl && statusEl.textContent === unboundNote) {
      setStatus(readyNote, false);
    }
  }

  function scrollToBottom() {
    if (!history) return;
    history.scrollTop = history.scrollHeight;
    window.requestAnimationFrame(() => {
      if (history) history.scrollTop = history.scrollHeight;
    });
  }

  function nearBottom() {
    if (!history) return true;
    return history.scrollHeight - history.scrollTop - history.clientHeight < 80;
  }

  function setMessages(next) {
    session = next || null;
    updateAgentStatus();
    if (!history) return;
    if (session && session.status === "unbound") {
      history.innerHTML = messagesHtml([], emptyNoteFor(session));
      applyLanguage(history);
      signature = "";
      firstRender = false;
      setStatus(unboundNote, false);
      syncComposer();
      renderInspector();
      return;
    }
    if (session && session.status === "error") {
      if (!signature) history.innerHTML = messagesHtml([], emptyNoteFor(session));
      setStatus("会话不可用 · 任务结果仍可查看", true);
      syncComposer();
      renderInspector();
      return;
    }
    const messages = (session && session.messages) || [];
    const nextSignature = messageSignature(messages);
    if (nextSignature !== signature) {
      const stick = firstRender || nearBottom();
      history.innerHTML = messagesHtml(messages, emptyNoteFor(session));
      applyLanguage(history);
      signature = nextSignature;
      firstRender = false;
      if (stick) scrollToBottom();
    }
    if (!activeFollowup() && statusEl && statusEl.textContent === unboundNote) setStatus(readyNote, false);
    syncComposer();
    renderInspector();
  }

  function schedule() {
    if (timer) window.clearTimeout(timer);
    const delay = activeFollowup() ? 1500 : isTerminalState(supervisor.state) ? REFRESH_TERMINAL_MS : REFRESH_ACTIVE_MS;
    timer = window.setTimeout(() => {
      void tick();
    }, delay);
  }

  async function tick() {
    if (disposed || polling) return;
    polling = true;
    const [nextSupervisor, nextSession] = await Promise.all([
      loadTaskSupervisor(taskId),
      loadTaskSessionMessages(taskId)
    ]);
    polling = false;
    // Ignore a response from a previous mount or a different task.
    if (disposed || !root.isConnected || root.dataset.taskId !== String(taskId)) return;
    touchRefreshed();
    setState(nextSupervisor);
    setMessages(nextSession);
    if (followupWatching && followupReplySeen()) {
      finishFollowup("本轮回复完成");
      setStatus("已收到回复", false);
    }
    schedule();
  }

  async function submit() {
    if (busy || followupWatching || demo) return;
    const text = input ? input.value.trim() : "";
    if (!text) {
      setStatus("请输入内容后再发送。", true);
      if (input) input.focus();
      return;
    }
    busy = true;
    followupStartedAt = Date.now();
    followupBaseline = ((session && session.messages) || []).length;
    followupNote = "";
    // The request can block for minutes while the model answers.  Clear the
    // composer now so the sent text does not stay in the input box; the
    // optimistic row below keeps it visible in the conversation.  On a real
    // failure the draft is restored for retry.
    if (input) input.value = "";
    syncComposer();
    updateAgentStatus();
    setStatus("发送中…", false);
    if (history) {
      const empty = history.querySelector(".chat-empty");
      if (empty) empty.remove();
      const now = new Date().toISOString();
      history.insertAdjacentHTML("beforeend", messageHtml({
        message_id: "pending-local",
        role: "user",
        created_at: now,
        text,
        error_code: null
      }).replace('class="chat-row user"', 'class="chat-row user is-pending"'));
      scrollToBottom();
    }
    // The control-plane POST is blocking. Poll independently so the user sees
    // the accepted turn and session activity while the model is still working.
    schedule();

    const result = await sendTaskSessionMessage(taskId, text);
    if (disposed) return;

    const pending = history ? history.querySelector(".chat-row.is-pending") : null;
    if (!result.ok) {
      busy = false;
      const code = result.error && result.error.code;
      const message = result.error && result.error.message;
      await tick();
      if (followupReplySeen()) {
        if (pending) pending.remove();
        followupStartedAt = 0;
        followupNote = "本轮请求返回错误，但会话已同步到回复";
        setStatus("请求返回错误；会话回复已同步。", true);
        updateAgentStatus();
        syncComposer();
        return;
      }
      const hasNewActivity = ((session && session.messages) || []).length > followupBaseline;
      if (hasNewActivity) {
        // The server now owns the accepted user turn; drop the optimistic row
        // before the next poll renders the authoritative conversation.
        if (pending) pending.remove();
        watchForFollowupReply();
        setStatus("请求返回错误，但会话仍在执行；正在同步…", true);
        syncComposer();
        schedule();
        return;
      }
      if (pending) pending.remove();
      followupStartedAt = 0;
      followupNote = "发送失败，请重试";
      // Restoration is safe here: this branch has no accepted turn and no new
      // server activity, so the draft was not consumed by the backend.
      if (input && !input.value) {
        input.value = text;
        input.focus();
      }
      if (code === "SESSION_BUSY") {
        setStatus("会话仍在执行，请稍后重试。", true);
      } else if (code === "SESSION_NOT_BOUND") {
        setStatus("会话尚未绑定，无法发送。", true);
      } else {
        setStatus(`${code || "ERROR"}${message ? `：${message}` : ""}`, true);
      }
      updateAgentStatus();
      syncComposer();
      return;
    }

    if (pending) pending.classList.remove("is-pending");
    if (input) {
      input.value = "";
      input.focus();
    }
    signature = "";
    await tick();
    const messageId = result.message && result.message.message_id;
    if (history && messageId && result.message && String(result.message.text || "").trim()) {
      const exists = Array.from(history.querySelectorAll("[data-message-id]"))
        .some((row) => row.dataset.messageId === messageId);
      if (!exists) {
        history.insertAdjacentHTML("beforeend", messageHtml(result.message));
        scrollToBottom();
      }
    }
    followupNote = `本轮回复完成 · ${runDurationLabel(Date.now() - followupStartedAt)}`;
    followupStartedAt = 0;
    busy = false;
    setStatus("已发送", false);
    updateAgentStatus();
    syncComposer();
    schedule();
  }

  if (form && !demo) {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      void submit();
    });
  }
  if (input && !demo) {
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing && event.keyCode !== 229) {
        event.preventDefault();
        void submit();
      }
    });
  }
  if (refreshButton && !demo) {
    refreshButton.addEventListener("click", () => {
      void tick();
    });
  }
  if (inspectorToggle) {
    inspectorToggle.addEventListener("click", () => {
      setInspectorOpen(inspectorLayout.dataset.inspectorOpen === "false");
    });
  }
  if (inspectorClose) {
    inspectorClose.addEventListener("click", () => setInspectorOpen(false));
  }

  touchRefreshed();
  setState(supervisor);
  setMessages(session);
  scrollToBottom();
  firstRender = false;
  statusTimer = window.setInterval(updateAgentStatus, 1000);
  if (mode === "api" && !demo) schedule();

  return () => {
    disposed = true;
    if (timer) window.clearTimeout(timer);
    timer = null;
    if (watchTimer) window.clearTimeout(watchTimer);
    watchTimer = null;
    if (statusTimer) window.clearInterval(statusTimer);
    statusTimer = null;
  };
}

function hydrateTrace({ host }) {
  const panel = host.querySelector("[data-trace-panel]");
  if (!panel) return null;
  const filter = panel.querySelector("[data-trace-filter]");
  const status = panel.querySelector("[data-trace-filter-status]");
  const empty = panel.querySelector("[data-trace-empty]");
  const events = Array.from(panel.querySelectorAll("[data-trace-event]"));
  const total = events.length;

  function apply() {
    const query = filter ? filter.value.trim().toLowerCase() : "";
    let shown = 0;
    events.forEach((event) => {
      const match = !query || String(event.dataset.traceSearch || "").includes(query);
      event.hidden = !match;
      if (match) shown += 1;
    });
    if (status) status.textContent = `显示 ${shown} / ${total}`;
    if (empty) empty.hidden = shown !== 0;
  }

  if (filter) filter.addEventListener("input", apply);
  apply();
  return () => {
    if (filter) filter.removeEventListener("input", apply);
  };
}

function hydrateArtifacts({ host }) {
  const dialog = host.querySelector("#artifact-preview-dialog");
  const previewTitle = dialog ? dialog.querySelector("[data-artifact-preview-title]") : null;
  const previewStatus = dialog ? dialog.querySelector("[data-artifact-preview-status]") : null;
  const previewBody = dialog ? dialog.querySelector("[data-artifact-preview-body]") : null;
  const closeButtons = dialog ? Array.from(dialog.querySelectorAll("[data-artifact-preview-close]")) : [];
  const controller = new AbortController();
  let busy = false;

  function openPreview(name) {
    if (!dialog) return;
    if (previewTitle) previewTitle.textContent = name || "日志预览";
    if (previewStatus) previewStatus.textContent = "正在读取…";
    if (previewBody) previewBody.textContent = "";
    if (typeof dialog.showModal === "function") {
      if (!dialog.open) dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
  }

  function closePreview() {
    if (!dialog) return;
    if (typeof dialog.close === "function" && dialog.open) dialog.close();
    else dialog.removeAttribute("open");
  }

  async function handle(button) {
    if (busy) return;
    const action = button.dataset.artifactAction;
    const campaignId = button.dataset.campaignId;
    const name = button.dataset.artifactName;
    if (!campaignId || !name) return;
    busy = true;
    const sectionStatus = host.querySelector("[data-artifact-status]");
    if (sectionStatus) sectionStatus.textContent = `正在读取 ${name}…`;
    if (action === "view") openPreview(name);

    const result = await loadTestCampaignArtifact(campaignId, name);
    busy = false;
    if (!result.ok) {
      const error = result.error || {};
      const message = `${error.code || "ERROR"}${error.message ? `：${error.message}` : ""}`;
      if (sectionStatus) sectionStatus.textContent = `读取失败：${message}`;
      if (previewStatus) previewStatus.textContent = `读取失败：${message}`;
      return;
    }

    if (action === "view") {
      const text = await result.blob.text();
      const limit = 200000;
      const truncated = text.length > limit;
      if (previewBody) {
        previewBody.textContent = truncated
          ? `${text.slice(0, limit)}\n\n… 已截断，仅显示前 ${limit} 个字符；请下载完整文件。`
          : text;
      }
      if (previewStatus) {
        previewStatus.textContent = `${formatBytes(result.blob.size)}${truncated ? " · 预览已截断" : ""}`;
      }
      if (sectionStatus) sectionStatus.textContent = `已打开 ${name}`;
      return;
    }

    const url = URL.createObjectURL(result.blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    if (sectionStatus) sectionStatus.textContent = `已开始下载 ${name}`;
  }

  function onClick(event) {
    const button = event.target && event.target.closest
      ? event.target.closest("[data-artifact-action]")
      : null;
    if (!button) return;
    event.preventDefault();
    void handle(button);
  }

  host.addEventListener("click", onClick, { signal: controller.signal });
  closeButtons.forEach((button) => button.addEventListener("click", closePreview, { signal: controller.signal }));
  return () => controller.abort();
}

function resourceStateText(state) {
  if (state === "ONLINE") return "在线";
  if (state === "OFFLINE") return "离线";
  return state || "UNKNOWN";
}

function resourceStateClass(state) {
  if (state === "ONLINE") return "is-online";
  if (state === "OFFLINE") return "is-offline";
  return "is-unknown";
}

function resourceInput(item) {
  return `
    <label class="task-resource-item">
      <input type="checkbox" data-task-resource="${item.type}" value="${esc(item.id)}"${item.nodeId ? ` data-node-id="${esc(item.nodeId)}"` : ""}>
      <span class="task-resource-body">
        <span class="task-resource-name" data-no-i18n>${esc(item.name)}</span>
        <span class="task-resource-meta">${esc(item.meta)}</span>
      </span>
      <span class="task-resource-state ${resourceStateClass(item.state)}">${esc(resourceStateText(item.state))}</span>
    </label>
  `;
}

function hydrateTaskModal({ host }) {
  const dialog = host.querySelector("#task-create-dialog");
  if (!dialog) return null;
  const openButton = host.querySelector("[data-task-modal-open]");
  const textarea = dialog.querySelector("#task-description");
  const feedback = dialog.querySelector("#task-create-feedback");
  const nodeList = dialog.querySelector("[data-task-node-list]");
  const deviceList = dialog.querySelector("[data-task-device-list]");
  const nodeCount = dialog.querySelector("[data-task-node-count]");
  const deviceCount = dialog.querySelector("[data-task-device-count]");
  const warning = dialog.querySelector("[data-task-resource-warning]");
  const controls = [nodeList, deviceList, nodeCount, deviceCount, warning];
  if (controls.some((node) => !node)) return null;

  let resourcesLoaded = false;
  let resourcesLoading = false;
  let requestToken = 0;
  let resources = { nodes: [], devices: [] };

  function resourceInputs(type) {
    return Array.from(dialog.querySelectorAll(`input[data-task-resource="${type}"]`));
  }

  function selectedInputs(type) {
    return resourceInputs(type).filter((input) => input.checked);
  }

  function announce(text) {
    warning.textContent = text || "";
  }

  function setBusy(busy) {
    nodeList.setAttribute("aria-busy", busy ? "true" : "false");
    deviceList.setAttribute("aria-busy", busy ? "true" : "false");
  }

  function renderError(error) {
    const code = (error && error.code) || "ERROR";
    const message = (error && error.message) || "控制面请求未成功。";
    const markup = `
      <div class="task-resource-error" role="alert">
        <p class="task-resource-error-title">执行资源读取失败</p>
        <p class="task-resource-meta"><span class="mono">${esc(code)}</span> · ${esc(message)}</p>
        <button class="btn btn-sm" type="button" data-task-resource-retry>重试</button>
      </div>
    `;
    nodeList.innerHTML = markup;
    deviceList.innerHTML = markup;
    setBusy(false);
    applyLanguage(dialog);
  }

  function renderNodes() {
    if (!resources.nodes.length) {
      nodeList.innerHTML = `<p class="task-resource-status" role="status">暂无可用节点；本次任务将不绑定节点。</p>`;
    } else {
      nodeList.innerHTML = resources.nodes.map((node) => resourceInput({
        type: "node",
        id: node.id,
        name: node.display_id,
        meta: node.hostname,
        state: node.state
      })).join("");
    }
    nodeList.setAttribute("aria-busy", "false");
  }

  function renderDevices() {
    if (!resources.devices.length) {
      deviceList.innerHTML = `<p class="task-resource-status" role="status">暂无可用设备；本次任务将不绑定设备。</p>`;
    } else {
      const nodesById = new Map(resources.nodes.map((node) => [node.id, node]));
      const groups = new Map();
      for (const device of resources.devices) {
        const key = device.node_id || "__unowned__";
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(device);
      }
      const ordered = Array.from(groups.entries()).sort(([a], [b]) => {
        if (a === "__unowned__") return 1;
        if (b === "__unowned__") return -1;
        return a.localeCompare(b);
      });
      deviceList.innerHTML = ordered.map(([nodeId, devices]) => {
        const node = nodesById.get(nodeId);
        const heading = node ? node.display_id : (devices[0].node_label || "未归属节点");
        return `
          <section class="task-resource-node-group">
            <p class="task-resource-node-heading" data-no-i18n>${esc(heading)}</p>
            ${devices.map((device) => resourceInput({
              type: "device",
              id: device.id,
              nodeId: device.node_id || "",
              name: device.display_id,
              meta: `${device.kind} · ${device.node_label}`,
              state: device.state
            })).join("")}
          </section>
        `;
      }).join("");
    }
    deviceList.setAttribute("aria-busy", "false");
  }

  function updateLimits() {
    const nodeInputs = resourceInputs("node");
    const deviceInputs = resourceInputs("device");
    const nodeTotal = selectedInputs("node").length;
    const deviceTotal = selectedInputs("device").length;
    const selectedNodeIds = new Set(selectedInputs("node").map((input) => input.value));

    for (const input of nodeInputs) {
      const blocked = nodeTotal >= MAX_TASK_RESOURCES && !input.checked;
      input.disabled = blocked;
      input.setAttribute("aria-disabled", blocked ? "true" : "false");
    }
    for (const input of deviceInputs) {
      const nodeBlocked = input.dataset.nodeId
        && !selectedNodeIds.has(input.dataset.nodeId)
        && nodeTotal >= MAX_TASK_RESOURCES;
      const limitBlocked = deviceTotal >= MAX_TASK_RESOURCES && !input.checked;
      const blocked = nodeBlocked || limitBlocked;
      input.disabled = blocked;
      input.setAttribute("aria-disabled", blocked ? "true" : "false");
    }

    nodeCount.textContent = `已选 ${nodeTotal} / ${MAX_TASK_RESOURCES}`;
    deviceCount.textContent = `已选 ${deviceTotal} / ${MAX_TASK_RESOURCES}`;
    applyLanguage(dialog);
  }

  function renderResources() {
    renderNodes();
    renderDevices();
    updateLimits();
  }

  async function loadResources(force = false) {
    if (resourcesLoading || (resourcesLoaded && !force)) return;
    resourcesLoading = true;
    const token = ++requestToken;
    setBusy(true);
    nodeList.innerHTML = `<p class="task-resource-status" role="status">正在读取节点…</p>`;
    deviceList.innerHTML = `<p class="task-resource-status" role="status">正在读取设备…</p>`;
    applyLanguage(dialog);
    const result = await loadTaskResources();
    resourcesLoading = false;
    if (token !== requestToken) return;
    if (!result.ok) {
      resourcesLoaded = false;
      renderError(result.error);
      return;
    }
    resourcesLoaded = true;
    resources = { nodes: result.nodes, devices: result.devices };
    renderResources();
  }

  function onChange(event) {
    const input = event.target.closest("input[data-task-resource]");
    if (!input) return;
    announce("");
    if (input.dataset.taskResource === "device" && input.checked) {
      const nodeId = input.dataset.nodeId;
      const nodeInput = nodeId
        ? resourceInputs("node").find((item) => item.value === nodeId)
        : null;
      if (nodeInput && !nodeInput.checked) {
        if (selectedInputs("node").length >= MAX_TASK_RESOURCES) {
          input.checked = false;
          announce("节点数量已达上限，无法加入该设备所属节点。");
        } else {
          nodeInput.checked = true;
        }
      }
    }
    if (input.dataset.taskResource === "node" && !input.checked) {
      for (const device of resourceInputs("device")) {
        if (device.dataset.nodeId === input.value) device.checked = false;
      }
    }
    updateLimits();
  }

  function onClick(event) {
    const retry = event.target.closest("[data-task-resource-retry]");
    if (retry) {
      event.preventDefault();
      void loadResources(true);
    }
  }

  function open() {
    if (feedback) {
      feedback.hidden = true;
      feedback.innerHTML = "";
    }
    if (typeof dialog.showModal === "function") {
      if (!dialog.open) dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
    void loadResources();
    window.setTimeout(() => {
      if (textarea) textarea.focus();
    }, 0);
  }

  function close() {
    if (typeof dialog.close === "function" && dialog.open) dialog.close();
    else dialog.removeAttribute("open");
  }

  function onOpen(event) {
    event.preventDefault();
    open();
  }

  function onCancel() {
    close();
  }

  function onBackdrop(event) {
    if (event.target === dialog) close();
  }

  if (openButton && !openButton.disabled) openButton.addEventListener("click", onOpen);
  dialog.querySelectorAll("[data-task-modal-close]").forEach((node) => {
    node.addEventListener("click", onCancel);
  });
  dialog.addEventListener("click", onBackdrop);
  dialog.addEventListener("change", onChange);
  dialog.addEventListener("click", onClick);

  return () => {
    if (openButton) openButton.removeEventListener("click", onOpen);
    dialog.querySelectorAll("[data-task-modal-close]").forEach((node) => {
      node.removeEventListener("click", onCancel);
    });
    dialog.removeEventListener("click", onBackdrop);
    dialog.removeEventListener("change", onChange);
    dialog.removeEventListener("click", onClick);
    if (dialog.open && typeof dialog.close === "function") dialog.close();
  };
}

function hydrateDelete({ host, route, refresh }) {
  const dialog = host.querySelector("#task-delete-dialog");
  if (!dialog) return null;
  const target = dialog.querySelector("[data-delete-target]");
  const errorEl = dialog.querySelector("[data-delete-error]");
  const statusEl = dialog.querySelector("[data-delete-status]");
  const confirmButton = dialog.querySelector("[data-delete-confirm]");
  const cancelButtons = Array.from(dialog.querySelectorAll("[data-delete-cancel]"));
  const controller = new AbortController();
  let pendingId = null;
  let pendingTitle = "";
  let busy = false;
  let disposed = false;

  function open(taskId, title) {
    pendingId = taskId;
    pendingTitle = title || taskId;
    if (target) target.textContent = title ? `${title} · ${taskId}` : taskId;
    if (errorEl) {
      errorEl.hidden = true;
      errorEl.textContent = "";
    }
    if (statusEl) statusEl.textContent = "";
    if (confirmButton) confirmButton.disabled = false;
    cancelButtons.forEach((node) => {
      node.disabled = false;
    });
    if (typeof dialog.showModal === "function") {
      if (!dialog.open) dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
    window.setTimeout(() => {
      if (cancelButtons[0]) cancelButtons[0].focus();
    }, 0);
  }

  function close() {
    if (typeof dialog.close === "function" && dialog.open) dialog.close();
    else dialog.removeAttribute("open");
  }

  function showError(message) {
    if (!errorEl) return;
    errorEl.textContent = message;
    errorEl.hidden = false;
  }

  async function remove() {
    if (busy || !pendingId) return;
    busy = true;
    if (confirmButton) confirmButton.disabled = true;
    cancelButtons.forEach((node) => {
      node.disabled = true;
    });
    if (statusEl) statusEl.textContent = "正在删除…";
    if (errorEl) {
      errorEl.hidden = true;
      errorEl.textContent = "";
    }

    const removedId = pendingId;
    const result = await deleteTask(removedId);
    busy = false;
    if (disposed) return;

    if (!result.ok) {
      if (confirmButton) confirmButton.disabled = false;
      cancelButtons.forEach((node) => {
        node.disabled = false;
      });
      if (statusEl) statusEl.textContent = "";
      const code = result.error && result.error.code;
      const message = result.error && result.error.message;
      showError(code === "TASK_ACTIVE"
        ? "任务仍在执行，暂不能删除"
        : `${code || "ERROR"}${message ? `：${message}` : ""}`);
      return;
    }

    close();
    if (route.id === "TK-01") {
      const row = Array.from(host.querySelectorAll("[data-task-row]"))
        .find((item) => item.dataset.taskId === removedId);
      if (row) row.remove();
      const grid = host.querySelector(".task-card-grid");
      if (grid && !grid.querySelector("[data-task-row]")) {
        grid.outerHTML = `<p class="muted small" role="status">暂无任务。点击“新建任务”创建第一个任务。</p>`;
      }
    } else {
      navigate("/console/tasks");
    }
  }

  function onClick(event) {
    const deleteButton = event.target.closest("[data-delete-task]");
    if (deleteButton) {
      event.preventDefault();
      if (deleteButton.disabled) return;
      open(deleteButton.dataset.taskId, deleteButton.dataset.taskTitle);
      return;
    }
    if (event.target.closest("[data-delete-cancel]")) {
      event.preventDefault();
      close();
      return;
    }
    if (event.target.closest("[data-delete-confirm]")) {
      event.preventDefault();
      void remove();
    }
  }

  function onBackdrop(event) {
    if (event.target === dialog) close();
  }

  host.addEventListener("click", onClick, { signal: controller.signal });
  dialog.addEventListener("click", onBackdrop, { signal: controller.signal });

  return () => {
    disposed = true;
    controller.abort();
    if (dialog.open && typeof dialog.close === "function") dialog.close();
  };
}

function hydrateCampaignActions({ host, refresh }) {
  const dialog = host.querySelector("#campaign-action-dialog");
  if (!dialog) return null;
  const titleEl = dialog.querySelector("[data-campaign-dialog-title]");
  const noteEl = dialog.querySelector("[data-campaign-dialog-note]");
  const target = dialog.querySelector("[data-campaign-target]");
  const errorEl = dialog.querySelector("[data-campaign-error]");
  const statusEl = dialog.querySelector("[data-campaign-status]");
  const confirmButton = dialog.querySelector("[data-campaign-confirm]");
  const stopDeleteButton = dialog.querySelector("[data-campaign-stop-delete]");
  const cancelButtons = Array.from(dialog.querySelectorAll("[data-campaign-cancel]"));
  const controller = new AbortController();
  let pendingId = null;
  let pendingMode = "delete";
  let busy = false;
  let disposed = false;

  const COPY = {
    delete: {
      title: "删除测试活动",
      note: "仅删除终态活动记录；QUEUED / RUNNING 活动必须先停止。删除后无法恢复。",
      confirm: "确认删除",
      confirmClass: "btn btn-danger",
      showStopDelete: false
    },
    stop: {
      title: "停止测试活动",
      note: "停止会请求节点取消执行并释放设备租约；也可选择停止后删除活动记录。",
      confirm: "停止",
      confirmClass: "btn btn-primary",
      showStopDelete: true
    },
    "stop-delete": {
      title: "停止后删除测试活动",
      note: "先停止活动并等待其到达终态，然后删除活动记录；无法恢复。",
      confirm: "停止后删除",
      confirmClass: "btn btn-danger",
      showStopDelete: false
    }
  };

  function setBusy(state) {
    busy = state;
    if (confirmButton) confirmButton.disabled = state;
    if (stopDeleteButton) stopDeleteButton.disabled = state;
    cancelButtons.forEach((node) => {
      node.disabled = state;
    });
  }

  function open(campaignId, title, mode) {
    const copy = COPY[mode] || COPY.delete;
    pendingId = campaignId;
    pendingMode = mode;
    if (titleEl) titleEl.textContent = copy.title;
    if (noteEl) noteEl.textContent = copy.note;
    if (target) target.textContent = title ? `${title} · ${campaignId}` : campaignId;
    if (confirmButton) {
      confirmButton.textContent = copy.confirm;
      confirmButton.className = copy.confirmClass;
    }
    if (stopDeleteButton) stopDeleteButton.hidden = !copy.showStopDelete;
    if (errorEl) {
      errorEl.hidden = true;
      errorEl.textContent = "";
    }
    if (statusEl) statusEl.textContent = "";
    setBusy(false);
    if (typeof dialog.showModal === "function") {
      if (!dialog.open) dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
    window.setTimeout(() => {
      if (cancelButtons[0]) cancelButtons[0].focus();
    }, 0);
  }

  function close() {
    if (typeof dialog.close === "function" && dialog.open) dialog.close();
    else dialog.removeAttribute("open");
  }

  function showError(result) {
    if (!errorEl) return;
    const code = result && result.error && result.error.code;
    const message = result && result.error && result.error.message;
    let text;
    if (code === "CAMPAIGN_ACTIVE") {
      text = "活动仍在执行，暂不能删除；请先停止活动。";
    } else if (code === "INVALID_STATE_TRANSITION") {
      text = `活动状态不允许该操作${message ? `：${message}` : ""}`;
    } else if (result && result.status === 0) {
      text = "控制面不可达，操作未提交。";
    } else {
      text = `${code || "ERROR"}${message ? `：${message}` : ""}`;
    }
    errorEl.textContent = text;
    errorEl.hidden = false;
  }

  async function waitForTerminal(campaignId) {
    let last = null;
    for (let attempt = 0; attempt < 6; attempt += 1) {
      if (disposed) {
        return { ok: false, status: 0, error: { code: "DISPOSED", message: "页面已关闭" } };
      }
      last = await loadTestCampaign(campaignId);
      if (!last.ok) {
        if (last.status === 404) return { ok: true, gone: true };
        return last;
      }
      const status = last.campaign && last.campaign.status;
      if (TERMINAL_CAMPAIGN_STATES.has(status)) return { ok: true, campaign: last.campaign };
      if (attempt < 5) {
        await new Promise((resolve) => window.setTimeout(resolve, 500));
      }
    }
    return {
      ok: false,
      status: last ? last.status : 0,
      error: {
        code: "CAMPAIGN_STILL_ACTIVE",
        message: "停止请求已提交，但活动尚未到达终态；请稍后重试删除"
      }
    };
  }

  function finish() {
    close();
    if (typeof refresh === "function") refresh();
  }

  async function run(mode) {
    if (busy || !pendingId) return;
    setBusy(true);
    if (errorEl) {
      errorEl.hidden = true;
      errorEl.textContent = "";
    }
    if (statusEl) statusEl.textContent = mode === "delete" ? "正在删除…" : "正在停止…";

    const campaignId = pendingId;
    try {
      if (mode === "delete") {
        const deleted = await deleteTestCampaign(campaignId);
        if (disposed) return;
        if (!deleted.ok) {
          if (statusEl) statusEl.textContent = "";
          showError(deleted);
          return;
        }
        finish();
        return;
      }

      const stopped = await stopTestCampaign(campaignId);
      if (disposed) return;
      if (!stopped.ok) {
        const code = stopped.error && stopped.error.code;
        if (!(mode === "stop-delete" && (code === "INVALID_STATE_TRANSITION" || stopped.status === 404))) {
          if (statusEl) statusEl.textContent = "";
          showError(stopped);
          return;
        }
      }

      if (mode === "stop") {
        finish();
        return;
      }

      if (statusEl) {
        statusEl.textContent = stopped.runner_active
          ? "已请求节点停止；等待活动到达终态…"
          : "等待活动到达终态…";
      }
      const terminal = await waitForTerminal(campaignId);
      if (disposed) return;
      if (!terminal.ok) {
        if (statusEl) statusEl.textContent = "";
        showError(terminal);
        return;
      }
      if (terminal.gone) {
        finish();
        return;
      }

      const deleted = await deleteTestCampaign(campaignId);
      if (disposed) return;
      if (!deleted.ok) {
        if (statusEl) statusEl.textContent = "";
        showError(deleted);
        return;
      }
      finish();
    } finally {
      busy = false;
      if (dialog.open) setBusy(false);
    }
  }

  function onClick(event) {
    const deleteButton = event.target.closest("[data-delete-campaign]");
    if (deleteButton) {
      event.preventDefault();
      event.stopPropagation();
      if (deleteButton.disabled) return;
      open(deleteButton.dataset.campaignId, deleteButton.dataset.campaignTitle, "delete");
      return;
    }
    const stopButton = event.target.closest("[data-stop-campaign]");
    if (stopButton) {
      event.preventDefault();
      event.stopPropagation();
      if (stopButton.disabled) return;
      open(stopButton.dataset.campaignId, stopButton.dataset.campaignTitle, "stop");
      return;
    }
    if (event.target.closest("[data-campaign-cancel]")) {
      event.preventDefault();
      close();
      return;
    }
    if (event.target.closest("[data-campaign-stop-delete]")) {
      event.preventDefault();
      void run("stop-delete");
      return;
    }
    if (event.target.closest("[data-campaign-confirm]")) {
      event.preventDefault();
      void run(pendingMode);
    }
  }

  function onBackdrop(event) {
    if (event.target === dialog) close();
  }

  host.addEventListener("click", onClick, { signal: controller.signal });
  dialog.addEventListener("click", onBackdrop, { signal: controller.signal });

  return () => {
    disposed = true;
    controller.abort();
    if (dialog.open && typeof dialog.close === "function") dialog.close();
  };
}

function hydrateTaskCampaigns({ host, taskId, mode }) {
  const section = host.querySelector("[data-task-campaign-section]");
  if (!section) return null;
  const dialog = host.querySelector("#campaign-trigger-dialog");
  const openButton = host.querySelector("[data-campaign-trigger-open]");
  const form = dialog ? dialog.querySelector("#campaign-trigger-form") : null;
  const nodeSelect = dialog ? dialog.querySelector("[data-campaign-node]") : null;
  const nodeStatus = dialog ? dialog.querySelector("[data-campaign-node-status]") : null;
  const feedback = dialog ? dialog.querySelector("[data-campaign-trigger-feedback]") : null;
  const triggerStatus = dialog ? dialog.querySelector("[data-campaign-trigger-status]") : null;
  const submitButton = dialog ? dialog.querySelector("[data-campaign-trigger-submit]") : null;
  const cancelButtons = dialog ? Array.from(dialog.querySelectorAll("[data-campaign-trigger-cancel]")) : [];
  const controller = new AbortController();
  const apiMode = mode === "api";
  const sectionTaskId = section.dataset.taskId || taskId || "";
  const endpoint = section.dataset.endpoint || "";
  let disposed = false;
  let busy = false;
  let nodesLoaded = false;

  function setTriggerStatus(text, isError) {
    if (!triggerStatus) return;
    triggerStatus.textContent = text || "";
    triggerStatus.classList.toggle("is-error", Boolean(isError));
  }

  function setSectionStatus(text, isError) {
    const node = section.querySelector("[data-task-campaign-status]");
    if (!node) return;
    node.textContent = text || "";
    node.classList.toggle("is-error", Boolean(isError));
  }

  function showTriggerError(result) {
    if (!feedback) return;
    const error = (result && result.error) || {};
    const status = result && result.status ? `HTTP ${result.status} · ` : "";
    feedback.innerHTML = `
      <div class="form-error">
        <p class="form-error-title">触发测试活动失败</p>
        <p class="caption"><span class="mono">${esc(status)}${esc(error.code || "ERROR")}</span></p>
        <p class="form-error-message">${esc(error.message || "控制面请求未成功。")}</p>
      </div>
    `;
    feedback.hidden = false;
  }

  function renderSection(campaigns, error) {
    const previous = section.querySelector("[data-task-campaign-list]");
    if (error) {
      if (previous) previous.remove();
      const existing = section.querySelector("[data-task-campaign-error]");
      const markup = taskCampaignErrorMarkup(error, sectionTaskId, endpoint);
      if (existing) existing.outerHTML = markup;
      else section.insertAdjacentHTML("afterbegin", markup);
      return;
    }
    const markup = `<div data-task-campaign-list>${taskCampaignListMarkup(campaigns, { disabled: !apiMode }, sectionTaskId, endpoint)}</div>`;
    const existingError = section.querySelector("[data-task-campaign-error]");
    if (existingError) existingError.remove();
    if (previous) previous.outerHTML = markup;
    else section.insertAdjacentHTML("afterbegin", markup);
  }

  async function reload() {
    if (!sectionTaskId) return;
    const buttons = Array.from(host.querySelectorAll("[data-campaign-refresh]"));
    buttons.forEach((node) => { node.disabled = true; });
    setSectionStatus("正在刷新测试活动…", false);
    const result = await loadTestCampaigns({ taskId: sectionTaskId });
    if (disposed || !section.isConnected) return;
    buttons.forEach((node) => { node.disabled = false; });
    if (result.ok) {
      renderSection(result.campaigns || [], null);
      setSectionStatus("已刷新；仅显示服务端返回的该任务活动。", false);
    } else {
      renderSection([], { ...(result.error || {}), status: result.status, endpoint: result.endpoint });
      setSectionStatus("测试活动刷新失败；失败事实已保留。", true);
    }
  }

  function close() {
    if (typeof dialog.close === "function" && dialog.open) dialog.close();
    else dialog.removeAttribute("open");
  }

  function setBusy(state) {
    busy = state;
    if (submitButton) submitButton.disabled = state;
    cancelButtons.forEach((node) => { node.disabled = state; });
  }

  async function loadNodes(force = false) {
    if (!nodeSelect || !form) return;
    if (nodesLoaded && !force) return;
    nodesLoaded = false;
    nodeSelect.setAttribute("aria-busy", "true");
    nodeSelect.innerHTML = `<option value="">正在读取节点…</option>`;
    if (nodeStatus) nodeStatus.textContent = "正在读取节点…";
    if (submitButton) submitButton.disabled = true;
    const result = await loadTaskResources();
    if (disposed || !nodeSelect.isConnected) return;
    if (!result.ok) {
      nodeSelect.innerHTML = `<option value="">节点读取失败</option>`;
      nodeSelect.setAttribute("aria-busy", "false");
      const error = result.error || {};
      if (nodeStatus) nodeStatus.textContent = `${error.code || "ERROR"}：${error.message || "节点读取失败；请重试。"}`;
      return;
    }
    const nodes = Array.isArray(result.nodes) ? result.nodes : [];
    if (!nodes.length) {
      nodeSelect.innerHTML = `<option value="">暂无节点</option>`;
      nodeSelect.setAttribute("aria-busy", "false");
      if (nodeStatus) nodeStatus.textContent = "控制面未返回节点；无法提交测试活动。";
      return;
    }
    nodeSelect.innerHTML = nodes.map((node) => `
      <option value="${esc(node.id)}">${esc(node.display_id)} · ${esc(node.hostname)} · ${esc(node.state || "UNKNOWN")}</option>
    `).join("");
    const defaultId = form.dataset.defaultNodeId || "";
    const defaultDisplay = String(form.dataset.defaultNodeDisplay || "WIN009").toLowerCase();
    const selected = (defaultId && nodes.find((node) => node.id === defaultId))
      || nodes.find((node) => String(node.display_id || "").toLowerCase() === defaultDisplay)
      || null;
    if (selected) {
      nodeSelect.value = selected.id;
      if (nodeStatus) nodeStatus.textContent = `默认节点 ${selected.display_id}（任务节点优先；未知时回退 WIN009）。`;
    } else {
      nodeSelect.value = "";
      if (nodeStatus) nodeStatus.textContent = `未找到默认节点 ${defaultDisplay.toUpperCase()}；请手动选择节点。`;
    }
    nodeSelect.setAttribute("aria-busy", "false");
    nodesLoaded = true;
    if (submitButton && apiMode) submitButton.disabled = false;
  }

  function open() {
    if (!dialog || !apiMode) return;
    if (feedback) {
      feedback.hidden = true;
      feedback.innerHTML = "";
    }
    setTriggerStatus("", false);
    setBusy(false);
    if (typeof dialog.showModal === "function") {
      if (!dialog.open) dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
    void loadNodes();
  }

  async function submit(event) {
    event.preventDefault();
    if (busy || !form || !apiMode) return;
    const values = new FormData(form);
    const nodeId = String(values.get("node_id") || "").trim();
    if (!nodeId) {
      showTriggerError({ status: 0, error: { code: "NODE_REQUIRED", message: "请选择执行节点。" } });
      return;
    }
    setBusy(true);
    if (feedback) {
      feedback.hidden = true;
      feedback.innerHTML = "";
    }
    setTriggerStatus("正在提交…", false);
    const result = await createTestCampaign({
      node_id: nodeId,
      task_id: sectionTaskId,
      scenario: values.get("scenario") || "wake-recognition",
      rounds: Number(values.get("rounds") || 0),
      bench: values.get("bench") || ""
    });
    if (disposed) return;
    setBusy(false);
    if (!result.ok) {
      setTriggerStatus("", true);
      showTriggerError(result);
      return;
    }
    setTriggerStatus("已提交；正在刷新该任务的活动列表…", false);
    close();
    setSectionStatus(`测试活动已提交${result.campaign && result.campaign.id ? ` · ${result.campaign.id}` : ""}；等待服务端返回。`, false);
    await reload();
  }

  function onClick(event) {
    if (event.target.closest("[data-campaign-trigger-open]")) {
      event.preventDefault();
      open();
      return;
    }
    if (event.target.closest("[data-campaign-refresh]")) {
      event.preventDefault();
      void reload();
      return;
    }
    if (event.target.closest("[data-campaign-trigger-cancel]")) {
      event.preventDefault();
      close();
    }
  }

  function onBackdrop(event) {
    if (event.target === dialog) close();
  }

  host.addEventListener("click", onClick, { signal: controller.signal });
  if (openButton && !apiMode) openButton.disabled = true;
  if (dialog) dialog.addEventListener("click", onBackdrop, { signal: controller.signal });
  const onSubmit = (event) => { void submit(event); };
  if (form) form.addEventListener("submit", onSubmit);

  return () => {
    disposed = true;
    controller.abort();
    if (form) form.removeEventListener("submit", onSubmit);
    if (dialog && dialog.open && typeof dialog.close === "function") dialog.close();
  };
}

export function hydrate({ route, params, view, mode, host, refresh } = {}) {
  if (!host) return null;
  const cleanups = [];
  if (route.id === "TK-01") {
    cleanups.push(hydrateTaskList({ host, mode }));
    cleanups.push(hydrateTaskModal({ host }));
    cleanups.push(hydrateCampaignActions({ host, refresh }));
  }
  if (route.id === "TK-02") {
    const root = host.querySelector("[data-chat-root]");
    if (root) {
      cleanups.push(hydrateChat({
        root,
        taskId: params.taskId,
        mode,
        initialSupervisor: view.supervisor,
        initialSession: view.session,
        refresh
      }));
    }
    cleanups.push(hydrateTaskCampaigns({ host, taskId: params.taskId, mode }));
    cleanups.push(hydrateCampaignActions({ host, refresh }));
    cleanups.push(hydrateTrace({ host }));
  }
  cleanups.push(hydrateArtifacts({ host }));
  cleanups.push(hydrateDelete({ host, route, refresh }));
  const active = cleanups.filter(Boolean);
  if (!active.length) return null;
  return () => {
    active.forEach((cleanup) => cleanup());
  };
}
