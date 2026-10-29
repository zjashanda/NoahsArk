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

const Q09 = "Q-09 未裁决：只读候选 TASK_AUTHORIZED、写入候选 ADMIN_ONLY；裁决前不得实现治理写入。";

export function render({ route, params, view }) {
  const generic = genericState(view, "Agent");

  if (route.id === "AG-03") {
    const head = pageHeader({
      eyebrow: `Agents & Reviews · AG-03 · ${view.scenario.id}`,
      title: "评审会话",
      description: "呈现评审共识与未决风险；评审结果不替代 Linux 判定或人工审批。",
      actions: button("查看 Agent 注册表", { href: "/console/agents", kind: "quiet", icon: "arrow" })
    });
    if (generic) return head + generic;
    return `
      ${head}
      ${stateBanners(view)}
      ${panel({
        title: "评审记录",
        note: "consensus 不是 business PASS",
        body: table({
          head: ["评审", "任务", "修订", "阶段", "共识", "未决风险", "更新时间"],
          rows: view.world.reviews.map((review) => [
            `<span class="cell-primary mono">${review.id}</span>`,
            `<a href="#/console/tasks/${review.task_id}/revisions">${review.task_id}</a>`,
            `<span class="mono">${review.revision_id}</span>`,
            statusBadge(review.stage),
            review.consensus,
            review.open_risks ? badge(String(review.open_risks), "attention") : badge("0", "neutral"),
            review.updated_at
          ])
        }),
        flush: true
      })}
      ${panel({
        title: "评审边界",
        body: `
          <ul class="list-plain">
            <li>评审会话只提供建议与共识，不写入五轴或门禁。</li>
            <li>审批必须由具备 APPROVE_TASK 的真人执行；生成者不得是唯一批准者。</li>
            <li>共识 3 / 3 也不等于正式 PASS；证据与复核仍须完整。</li>
          </ul>
        `
      })}
      ${inlineNote(Q09)}
    `;
  }

  if (route.id === "AG-02") {
    const agent = view.world.agents.find((item) => item.id === params.agentId) || view.world.agents[0];
    const head = pageHeader({
      eyebrow: `Agents & Reviews · AG-02 · ${view.scenario.id}`,
      title: agent.name,
      description: `<span class="mono">${agent.id}</span> · ${agent.role} · binding <span class="mono">${agent.model_binding}</span>`,
      actions: button("返回注册表", { href: "/console/agents", kind: "quiet", icon: "arrow" })
    });
    if (generic) return head + generic;
    return `
      ${head}
      ${stateBanners(view)}
      <div class="layout-2">
        ${panel({
          title: "职责与绑定",
          body: kv([
            ["agent_id", `<span class="mono">${agent.id}</span>`],
            ["role", agent.role],
            ["status", statusBadge(agent.status)],
            ["model_binding", `<span class="mono">${agent.model_binding}</span>`],
            ["last_review", `<span class="mono">${agent.last_review}</span>`],
            ["写权限", badge("PENDING Q-09", "attention")]
          ])
        })}
        ${panel({
          title: "策略与插件",
          note: "fictional prototype values",
          body: kv([
            ["policy", badge("READ_ONLY", "plain")],
            ["plugin · planner", badge("REGISTERED", "neutral")],
            ["plugin · verifier", badge("REGISTERED", "neutral")],
            ["governance write", badge("DISABLED", "attention", "lock")]
          ])
        })}
      </div>
      <div class="row" style="margin-top:16px">
        ${button("暂停 Agent", { disabledReason: Q09 })}
        ${button("修改绑定", { disabledReason: Q09 })}
      </div>
      ${inlineNote(Q09)}
    `;
  }

  const head = pageHeader({
    eyebrow: `Agents & Reviews · AG-01 · ${view.scenario.id}`,
    title: "Agent 注册表",
    description: "回答谁负责什么、绑定是否锁定；治理写入等待 Q-09。",
    actions: button("评审会话", { href: "/console/reviews", kind: "primary", icon: "shield" })
  });
  if (generic) return head + generic;
  return `
    ${head}
    ${stateBanners(view)}
    ${panel({
      title: "Registry",
      note: "只读投影",
      body: table({
        head: ["Agent", "职责", "model binding", "状态", "最后评审", "写入"],
        rows: view.world.agents.map((agent) => [
          `<a href="#/console/agents/${agent.id}"><span class="cell-primary">${agent.name}</span></a><div class="caption mono">${agent.id}</div>`,
          agent.role,
          `<span class="mono">${agent.model_binding}</span>`,
          statusBadge(agent.status),
          agent.last_review,
          button("治理动作", { small: true, disabledReason: Q09 })
        ])
      }),
      flush: true
    })}
    ${inlineNote(Q09)}
  `;
}
