import {
  badge,
  button,
  genericState,
  kv,
  pageHeader,
  panel,
  stateBanners,
  stats,
  statusBadge,
  table,
  timeline,
  inlineNote
} from "../components.js";

export function render({ route, params, view }) {
  const generic = genericState(view, "知识");

  if (route.id === "KN-03") {
    const head = pageHeader({
      eyebrow: `Knowledge · KN-03 · ${view.scenario.id}`,
      title: "候选知识治理",
      description: "候选必须人工审阅并具备目标库权限；不存在 PROPOSED → PROMOTED 捷径。",
      actions: button("返回知识库", { href: "/console/knowledge", kind: "quiet", icon: "arrow" })
    });
    if (generic) return head + generic;
    return `
      ${head}
      ${stateBanners(view)}
      ${stats([
        { label: "PROPOSED", value: "1", note: "待分配审阅" },
        { label: "UNDER_REVIEW", value: "1", note: "人工审阅中" },
        { label: "NEEDS_INFO", value: "1", note: "来源不足" },
        { label: "APPROVED", value: "1", note: "未自动推广" }
      ])}
      ${panel({
        title: "候选队列",
        note: "生成者不得是唯一批准者",
        body: table({
          head: ["候选", "状态", "来源链", "拟适用性", "提出者", "自动推广", "人工审阅", "更新时间"],
          rows: view.world.candidates.map((candidate) => [
            `<span class="cell-primary">${candidate.title}</span><div class="caption mono">${candidate.id}</div>`,
            statusBadge(candidate.status),
            candidate.source_chain.map((source) => `<span class="mono">${source}</span>`).join(" · "),
            candidate.applicability,
            `<span class="mono">${candidate.proposed_by}</span>`,
            badge(candidate.automatic_promotion_allowed ? "ALLOWED" : "FORBIDDEN", candidate.automatic_promotion_allowed ? "danger" : "neutral"),
            badge(candidate.requires_human_review ? "REQUIRED" : "MISSING", candidate.requires_human_review ? "neutral" : "danger"),
            candidate.updated_at
          ])
        }),
        flush: true
      })}
      <div class="row" style="margin-top:16px">
        ${button("审阅选中候选", { icon: "shield" })}
        ${button("标记为重复", { icon: "layers" })}
        ${button("拒绝候选", {
          kind: "danger",
          icon: "x",
          action: "danger",
          title: "确认拒绝候选",
          message: "拒绝会写入审计并保留来源链；不会删除历史。",
          confirmLabel: "拒绝",
          result: "候选拒绝已提交（mock，不生效）。"
        })}
      </div>
      ${inlineNote("推广必须由人类执行，并具备目标库权限（KNOWLEDGE_MERGE_COMMON / KNOWLEDGE_MERGE_TOOL / KNOWLEDGE_PROMOTE_ANOMALY）；自动推广始终禁止。")}
    `;
  }

  if (route.id === "KN-02") {
    const item = view.world.knowledge.find((entry) => entry.id === params.knowledgeId) || view.world.knowledge[0];
    const head = pageHeader({
      eyebrow: `Knowledge · KN-02 · ${view.scenario.id}`,
      title: item.title,
      description: `<span class="mono">${item.id}</span> · 状态 ${item.status} · 适用性 ${item.applicability}`,
      actions: button("返回知识库", { href: "/console/knowledge", kind: "quiet", icon: "arrow" })
    });
    if (generic) return head + generic;
    return `
      ${head}
      ${stateBanners(view)}
      ${item.status === "STALE" ? `<div class="banner banner-stale">${badge("STALE", "attention", "clock")}<div class="banner-body"><strong>知识已陈旧</strong> · 不得直接应用到新计划；必须重新审阅或标记替代关系。</div></div>` : ""}
      <div class="layout-2">
        <div>
          ${panel({
            title: "条目内容",
            note: "已批准知识 ≠ 当前任务结论",
            body: `
              <p class="secondary">${item.summary}</p>
              <div class="divider"></div>
              ${kv([
                ["status", statusBadge(item.status)],
                ["applicability", item.applicability],
                ["updated_at", `<span class="mono">${item.updated_at}</span>`],
                ["promotion", badge("HUMAN REQUIRED", "plain")],
                ["automatic_allowed", badge("false", "neutral")]
              ])}
            `
          })}
          ${panel({
            title: "来源链",
            note: "来源、复核与推广轨迹分离",
            body: `<ul class="list-plain">${item.source_chain.map((source) => `<li><span class="mono">${source}</span></li>`).join("")}</ul>`
          })}
          ${panel({
            title: "审阅与推广",
            note: "人工审阅，不允许自动提升",
            body: `
              ${timeline([
                { title: "候选提出", time: "2026-10-28 15:10", body: "来源链记录 run-031 与 ev-noise-run-07。", state: "done" },
                { title: "人工审阅", time: "2026-10-28 16:40", body: "适用性与冲突已检查。", state: "done" },
                { title: "批准条目", time: "2026-10-28 17:00", body: "批准不等于推广；目标库权限仍需单独校验。", state: "done" },
                { title: "推广", body: "需要 KNOWLEDGE_* 能力与审计事件。", state: "current" }
              ])}
              <div class="row" style="margin-top:12px">
                ${button("应用到草案修订", { icon: "plus", disabledReason: item.status === "STALE" ? "STALE 条目不得直接应用；需重新审阅。" : "" })}
                ${button("标记为争议", { icon: "alert" })}
              </div>
            `
          })}
        </div>
        <div>
          ${panel({
            title: "权重与边界",
            body: `
              <p class="small secondary">候选与已批准条目视觉权重必须区分。此页为已批准条目；候选只能出现在候选队列，不得自动变成知识。</p>
              <p class="small secondary" style="margin-top:8px">stale / disputed 必须在列表行可见，不能只藏在详情。</p>
            `
          })}
          ${panel({
            title: "相关任务",
            body: `<a href="#/console/tasks/tsk-voice-001/knowledge">tsk-voice-001 · Knowledge & Similar</a>`
          })}
        </div>
      </div>
    `;
  }

  const head = pageHeader({
    eyebrow: `Knowledge · KN-01 · ${view.scenario.id}`,
    title: "知识库",
    description: "检索已批准知识；候选与条目分开，冲突与陈旧状态在列表行可见。",
    actions: button("候选治理", { href: "/console/knowledge/candidates", kind: "primary", icon: "shield" })
  });
  if (generic) return head + generic;
  return `
    ${head}
    ${stateBanners(view)}
    ${panel({
      title: "已批准与佐证条目",
      note: "stale / disputed 不隐藏",
      body: table({
        head: ["条目", "状态", "适用性", "摘要", "更新时间"],
        rows: view.world.knowledge.map((item) => [
          `<a href="#/console/knowledge/${item.id}"><span class="cell-primary">${item.title}</span></a><div class="caption mono">${item.id}</div>`,
          statusBadge(item.status),
          item.applicability,
          item.summary,
          item.updated_at
        ])
      }),
      flush: true
    })}
    ${inlineNote("知识候选不会自动推广；应用到计划只生成草案修订，并需要再次审批。")}
  `;
}
