import {
  axisMatrix,
  badge,
  button,
  evidenceLedger,
  gateList,
  genericState,
  kv,
  pageHeader,
  panel,
  progressBar,
  releaseChecklist,
  stateBanners,
  stats,
  statusBadge,
  table,
  tabs,
  timeline,
  verdictBanner,
  splitFacts,
  inlineNote
} from "../components.js";

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
  return pageHeader({
    eyebrow: `Tasks · ${route.id} · ${view.scenario.id}`,
    title: task.title,
    description: `<span class="mono">${task.display_id}</span> · 稳定 task_id <span class="mono">${task.id}</span> · 当前 <span class="mono">${task.current_revision_id}</span> (R-${task.revision_number}) · ${task.subtitle}`,
    actions: button("请求审批", { icon: "shield" }) +
      button("派生新修订", { icon: "plus" }) +
      button("返回列表", { href: "/console/tasks", kind: "quiet", icon: "arrow" })
  });
}

function taskTabs(route, task) {
  return tabs(SUBVIEWS.map((item) => ({
    path: `/console/tasks/${task.id}/${item.seg}`,
    label: item.label,
    current: item.id === route.id
  })));
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
          title: "事件流（只读回放）",
          note: "mock 事件，不声称真实执行",
          body: timeline([
            { title: "attempt att-112 运行中", time: "14:06:19", body: "最后步骤 playback_noise_burst；节点回执 used_for_decision=false。", state: "current" },
            { title: "heartbeat", time: "14:06:19", body: "仅节点事实。", state: "done" },
            { title: "重试启动", time: "13:58:12", body: "retry_of=att-111。", state: "done" },
            { title: "att-111 transport_reset", time: "13:55:40", body: "失败分类由 Linux 写入。", state: "blocked" }
          ])
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

export function render({ route, params, view }) {
  const task = view.world.task;
  const generic = genericState(view, "任务");
  if (route.id === "TK-01") {
    const head = pageHeader({
      eyebrow: `Tasks · TK-01 · ${view.scenario.id}`,
      title: "任务",
      description: "以持续运营对象组织任务；详情包含 8 个固定子视图、修订谱系与门禁。",
      actions: button("新建任务", { href: "/console/intake/new", kind: "primary", icon: "plus" })
    });
    if (generic) return head + generic;
    return `
      ${head}
      ${stateBanners(view)}
      ${stats([
        { label: "活跃任务", value: "1", note: "另有 1 个历史任务" },
        { label: "阻塞", value: String(view.flags.blocked ? 1 : 0), note: "G3 资源资格" },
        { label: "运行中", value: "1", note: "formal run-042" },
        { label: "陈旧投影", value: String(view.flags.stale ? 1 : 0), note: "只追加徽章" }
      ])}
      ${panel({
        title: "任务列表",
        note: "点击进入 Overview；列表不折叠五轴与阻塞",
        body: table({
          head: ["任务", "阶段", "当前修订", "门禁", "阻塞方", "进度", "更新时间"],
          rows: [[
            `<a href="#/console/tasks/${task.id}/overview"><span class="cell-primary">${task.title}</span></a><div class="caption mono">${task.display_id}</div>`,
            statusBadge(task.stage),
            `<span class="mono">${task.current_revision_id}</span> · R-${task.revision_number}`,
            view.flags.blocked ? badge("G3 BLOCKED", "danger") : badge("G5 RUNNING", "action"),
            task.blocker_owner,
            view.progress.mode === "COUNTS" ? `${view.progress.completed} / ${view.progress.total}` : "未知",
            task.updated_at
          ]]
        }),
        flush: true
      })}
      ${inlineNote("旧修订强制只读；范围变化派生同任务新修订，并重新走冻结批准。")}
    `;
  }

  if (generic) return taskHeader(view, route, task) + generic;

  const run = view.world.runs[0];
  const attempt = view.world.attempts[0];
  switch (route.id) {
    case "TK-02": return overviewBody(view, route, task);
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
