import {
  badge,
  button,
  genericState,
  kv,
  pageHeader,
  panel,
  stateBanners,
  statusBadge,
  table,
  inlineNote
} from "../components.js";

const Q09 = "Q-09 未裁决：只读候选 TASK_AUTHORIZED、写入候选 ADMIN_ONLY；裁决前不得实现写入。";

export function render({ route, view }) {
  const generic = genericState(view, "运行时");

  if (route.id === "RT-02") {
    const head = pageHeader({
      eyebrow: `Runtime & Toolchain · RT-02 · ${view.scenario.id}`,
      title: "工具链锁定",
      description: "展示 lock 与 drift；任何写入动作等待 Q-09 访问级别裁决。",
      actions: button("查看模型绑定", { href: "/console/runtime/models", kind: "quiet", icon: "arrow" })
    });
    if (generic) return head + generic;
    return `
      ${head}
      ${stateBanners(view)}
      <div class="banner banner-stale">
        ${badge("DRIFT", "attention", "alert")}
        <div class="banner-body"><strong>检测到工具链漂移</strong> · audio-harness 0.9.4 与锁定版本不一致；漂移只报告事实，不自动修复。</div>
      </div>
      ${panel({
        title: "Toolchain locks",
        note: "静态检查 G2 的输入之一",
        body: table({
          head: ["工具", "版本", "lock", "checked_at", "写入"],
          rows: view.world.runtime.locks.map((lock) => [
            `<span class="cell-primary mono">${lock.name}</span>`,
            `<span class="mono">${lock.version}</span>`,
            statusBadge(lock.lock),
            lock.checked_at,
            button("重新锁定", { small: true, disabledReason: Q09 })
          ])
        }),
        flush: true
      })}
      ${panel({
        title: "与 G2 的关系",
        body: `<p class="small secondary">G2 静态检查使用冻结工具链执行；用 static run 声称真机可用是禁止的。漂移需要显式处置并写入审计。</p>
        <p style="margin-top:8px"><a href="#/console/tasks/tsk-voice-001/runs">查看 static run-036</a></p>`
      })}
      ${inlineNote(Q09)}
    `;
  }

  const head = pageHeader({
    eyebrow: `Runtime & Toolchain · RT-01 · ${view.scenario.id}`,
    title: "模型绑定",
    description: "回答谁在执行、绑定是否锁定、哪里发生漂移。写入能力等待 Q-09。",
    actions: button("查看工具链", { href: "/console/runtime/toolchain", kind: "quiet", icon: "arrow" })
  });
  if (generic) return head + generic;
  return `
    ${head}
    ${stateBanners(view)}
    ${panel({
      title: "ModelBinding",
      note: "绑定链只读；不显示密钥",
      body: table({
        head: ["binding", "用途", "model", "状态", "drift", "写入"],
        rows: view.world.runtime.models.map((model) => [
          `<span class="cell-primary mono">${model.binding}</span>`,
          model.purpose,
          `<span class="mono">${model.model}</span>`,
          statusBadge(model.status),
          model.drift === "NONE" ? badge("NONE", "neutral") : badge(model.drift, "attention"),
          button("修改绑定", { small: true, disabledReason: Q09 })
        ])
      }),
      flush: true
    })}
    ${panel({
      title: "运行影响",
      body: `
        <p class="small secondary">模型绑定影响候选计划、节点执行与证据复核；绑定漂移不会被 UI 自动改写为通过或失败。</p>
        <p style="margin-top:8px"><a href="#/console/agents">查看 Agents & Reviews</a></p>
      `
    })}
    ${inlineNote(Q09)}
  `;
}
