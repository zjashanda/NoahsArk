import {
  axisMatrix,
  badge,
  button,
  genericState,
  kv,
  leasePanel,
  pageHeader,
  panel,
  progressBar,
  splitFacts,
  stateBanners,
  stats,
  statusBadge,
  table,
  timeline,
  inlineNote
} from "../components.js";

function runHeader(view, route, run) {
  return pageHeader({
    eyebrow: `Runs & Attempts · ${route.id} · ${view.scenario.id}`,
    title: run ? `Run ${run.id}` : "运行",
    description: run
      ? `${run.mode.toUpperCase()} · ${run.lifecycle_status} · task <span class="mono">${run.task_id}</span> · revision <span class="mono">${run.revision_id}</span>`
      : "运行、Attempt、STOP 与对账事实。",
    actions: button("返回运行列表", { href: "/console/runs", kind: "quiet", icon: "arrow" })
  });
}

export function render({ route, params, view }) {
  const world = view.world;
  const generic = genericState(view, "运行");

  if (route.id === "RN-01") {
    const head = pageHeader({
      eyebrow: `Runs & Attempts · RN-01 · ${view.scenario.id}`,
      title: "运行与 Attempt",
      description: "显示在跑、停止、断线、待对账的运行；mode 与正式分母严格分离。",
      actions: button("打开任务运行", { href: "/console/tasks/tsk-voice-001/runs", icon: "tasks" })
    });
    if (generic) return head + generic;
    return `
      ${head}
      ${stateBanners(view)}
      ${stats([
        { label: "运行中", value: "1", note: "run-042 · formal" },
        { label: "待 STOP", value: String(view.flags.pendingStop || view.flags.reconciling ? 1 : 0), note: "未送达不算已停止" },
        { label: "对账中", value: String(view.flags.reconciling ? 1 : 0), note: "保持占用" },
        { label: "离线运行", value: String(view.flags.offline ? 1 : 0), note: "OFFLINE ≠ IDLE" }
      ])}
      ${panel({
        title: "运行列表",
        note: "formal / smoke / static 分母分离",
        body: table({
          head: ["run", "mode", "lifecycle", "分母资格", "attempts", "开始", "最后心跳", "STOP"],
          rows: world.runs.map((run) => [
            `<a href="#/console/runs/${run.id}"><span class="cell-primary mono">${run.id}</span></a><div class="caption">${run.task_id}</div>`,
            badge(run.mode, run.mode === "formal" ? "action" : "neutral"),
            statusBadge(run.lifecycle_status),
            run.denominator_eligible ? badge("ELIGIBLE", "success") : badge("NOT ELIGIBLE", "neutral"),
            `<a href="#/console/runs/${run.id}">${run.attempts}</a>`,
            run.started_at,
            run.last_heartbeat_at,
            run.stop_requested_at ? badge("REQUESTED", "attention") : badge("NONE", "neutral")
          ])
        }),
        flush: true
      })}
      ${inlineNote("OFFLINE + RUNNING + OCCUPIED + permit GRANTED 允许同时存在；不得把离线渲染为已停止或可重派。")}
    `;
  }

  if (route.id === "RN-03") {
    const attempt = world.attempts.find((item) => item.id === params.attemptId) || world.attempts[0];
    const run = world.runs.find((item) => item.id === attempt.run_id) || world.runs[0];
    const head = pageHeader({
      eyebrow: `Runs & Attempts · RN-03 · ${view.scenario.id}`,
      title: `Attempt ${attempt.id}`,
      description: `run <a class="mono" href="#/console/runs/${run.id}">${run.id}</a> · ordinal ${attempt.ordinal} · retry_of ${attempt.retry_of || "—"} · ${attempt.status}`,
      actions: button("返回 Run", { href: `/console/runs/${run.id}`, kind: "quiet", icon: "arrow" })
    });
    if (generic) return head + generic;
    const linuxView = {
      execution_status: attempt.status,
      business_verdict: view.axes.business_verdict,
      evidence_status: view.axes.evidence_status,
      verification_status: view.axes.verification_status
    };
    return `
      ${head}
      ${stateBanners(view)}
      ${splitFacts(attempt.node_observed, linuxView)}
      <div class="layout-2" style="margin-top:16px">
        ${panel({
          title: "重试链",
          note: "retry_of 与 flaky_suspect 分开记录",
          body: table({
            head: ["attempt", "ordinal", "retry_of", "状态", "flaky_suspect", "开始"],
            rows: world.attempts.filter((item) => item.run_id === run.id).map((item) => [
              `<a class="mono" href="#/console/runs/${run.id}/attempts/${item.id}">${item.id}</a>`,
              String(item.ordinal),
              item.retry_of || "—",
              statusBadge(item.status),
              item.flaky_suspect ? badge("SUSPECT", "attention") : badge("NO", "neutral"),
              item.started_at
            ])
          }),
          flush: true
        })}
        ${panel({
          title: "失败分类与证据引用",
          note: "分类由 Linux 写入，节点只回传事实",
          body: `
            ${kv([
              ["failure_class", `<span class="mono">${attempt.failure_class || "—"}</span>`],
              ["node local_state", badge(attempt.node_observed.local_state, "plain")],
              ["used_for_decision", badge("false", "neutral")],
              ["证据引用", `<a href="#/console/evidence/ev-serial-log-04">ev-serial-log-04</a>`]
            ])}
            <p class="caption" style="margin-top:8px">不得把节点回执渲染为 business_verdict 或 verification_status。</p>
          `
        })}
      </div>
    `;
  }

  const run = world.runs.find((item) => item.id === params.runId) || world.runs[0];
  const head = runHeader(view, route, run);
  if (generic) return head + generic;
  const attempts = world.attempts.filter((item) => item.run_id === run.id);
  const stopTimeline = view.flags.pendingStop
    ? timeline([
      { title: "待 STOP", time: run.stop_requested_at || "—", body: "已登记，未送达；不得显示为已停止。", state: "current" },
      { title: "停止后续动作", body: "等待节点回执。", state: "blocked" },
      { title: "补传", body: "补传离线期间的事实。", state: "blocked" },
      { title: "去重", body: "按 attempt / evidence digest 去重。", state: "blocked" },
      { title: "对账", body: "占用、lease、epoch 对账完成前保持占用。", state: "blocked" },
      { title: "恢复领取", body: "仅六步完成后恢复。", state: "blocked" }
    ])
    : `<p class="muted small">当前没有待 STOP 或对账范围。</p>`;

  return `
    ${head}
    ${stateBanners(view)}
    ${stats([
      { label: "mode", value: run.mode.toUpperCase(), note: run.denominator_eligible ? "正式分母" : "非正式分母" },
      { label: "lifecycle", value: run.lifecycle_status, note: "Linux 权威" },
      { label: "attempts", value: String(run.attempts), note: "含重试" },
      { label: "STOP", value: run.stop_requested_at ? "REQUESTED" : "NONE", note: "请求 ≠ 已停止" }
    ])}
    <div class="layout-2" style="margin-top:16px">
      <div>
        ${panel({
          title: "五轴与分母",
          note: "五轴不折叠；烟测不进入正式分母",
          body: `${axisMatrix(view.axes)}<div style="margin-top:12px">${progressBar(view.progress)}</div>`
        })}
        ${panel({
          title: "Attempt 矩阵",
          note: "run × attempt；重试不隐藏",
          body: table({
            head: ["attempt", "ordinal", "retry_of", "状态", "flaky_suspect", "节点最后步骤"],
            rows: attempts.map((attempt) => [
              `<a class="mono" href="#/console/runs/${run.id}/attempts/${attempt.id}"><span class="cell-primary">${attempt.id}</span></a>`,
              String(attempt.ordinal),
              attempt.retry_of || "—",
              statusBadge(attempt.status),
              attempt.flaky_suspect ? badge("SUSPECT", "attention") : badge("NO", "neutral"),
              `<span class="mono">${attempt.node_observed.last_step}</span>`
            ])
          }),
          flush: true
        })}
        ${panel({
          title: "STOP-first 重连顺序",
          note: "对账完成前保持占用，禁止新派发",
          body: stopTimeline
        })}
      </div>
      <div>
        ${panel({
          title: "四信号 + 新鲜度",
          note: "分别显示，互不替代",
          body: leasePanel(view)
        })}
        ${panel({
          title: "危险动作",
          body: `
            ${button("请求 STOP", {
              kind: "danger",
              icon: "stop",
              disabledReason: view.flags.noPermission
                ? "当前角色无执行许可；动作保留可见但禁用。"
                : view.flags.pendingStop
                  ? "已有待送达 STOP；不得重复登记为已停止。"
                  : ""
            })}
            <p class="caption" style="margin-top:8px">危险动作需要二次确认，并写明结果动词与前置条件。</p>
          `
        })}
        ${panel({
          title: "任务与修订",
          body: kv([
            ["task", `<a href="#/console/tasks/${run.task_id}/overview"><span class="mono">${run.task_id}</span></a>`],
            ["revision", `<span class="mono">${run.revision_id}</span>`],
            ["denominator", run.denominator_eligible ? badge("ELIGIBLE", "success") : badge("NOT ELIGIBLE", "neutral")],
            ["last heartbeat", `<span class="mono">${run.last_heartbeat_at}</span>`]
          ])
        })}
      </div>
    </div>
  `;
}
