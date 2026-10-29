import {
  badge,
  button,
  evidenceLedger,
  genericState,
  kv,
  pageHeader,
  panel,
  stateBanners,
  stats,
  statusBadge,
  table,
  verdictBanner
} from "../components.js";
import { verdictLabel } from "../semantics.js";

const VERDICTS = [
  { id: "vrd-042", subject: "tsk-voice-001 · rev-003", execution: "COMPLETED", validity: "VALID", business: "PASS", evidence: "INCOMPLETE", verification: "NEEDS_REVIEW", scope: "40 formal samples", updated: "2026-10-29 14:05 +08:00" },
  { id: "vrd-031", subject: "tsk-voice-000 · rev-006", execution: "COMPLETED", validity: "VALID", business: "PASS", evidence: "COMPLETE", verification: "PASS", scope: "32 formal samples", updated: "2026-10-28 16:02 +08:00" }
];

function axesFrom(verdict) {
  return {
    execution_status: verdict.execution,
    validity_status: verdict.validity,
    business_verdict: verdict.business,
    evidence_status: verdict.evidence,
    verification_status: verdict.verification
  };
}

export function render({ route, params, view }) {
  const generic = genericState(view, "证据");

  if (route.id === "EV-01") {
    const head = pageHeader({
      eyebrow: `Evidence & Verdict · EV-01 · ${view.scenario.id}`,
      title: "证据索引",
      description: "浏览证据索引与 manifest 元数据；原始内容按 EVIDENCE_AUTHORIZED 二次鉴权，允许与拒绝均审计。",
      actions: button("打开判定", { href: "/console/verdicts", icon: "shield" })
    });
    if (generic) return head + generic;
    return `
      ${head}
      ${stateBanners(view)}
      ${panel({
        title: "证据台账",
        note: "expected / received / verified 三列独立",
        body: evidenceLedger(view)
      })}
      <p class="caption" style="margin-top:16px">默认载荷不含绝对路径、凭据、原始音视频；“已接收”不等于“已核验”。</p>
    `;
  }

  if (route.id === "EV-03") {
    const verdicts = Array.isArray(view.world.verdicts) && view.world.verdicts.length
      ? view.world.verdicts
      : VERDICTS;
    const head = pageHeader({
      eyebrow: `Evidence & Verdict · EV-03 · ${view.scenario.id}`,
      title: "判定",
      description: "只显示五轴与 fail-closed 原因；正式 PASS 仅允许唯一精确组合。",
      actions: button("任务判定", { href: "/console/tasks/tsk-voice-001/verdict", icon: "tasks" })
    });
    if (generic) return head + generic;
    return `
      ${head}
      ${stateBanners(view)}
      ${verdictBanner(view.axes)}
      ${panel({
        title: "判定列表",
        note: "历史判定只读；报告与释放独立",
        body: table({
          head: ["判定", "对象", "execution", "validity", "business", "evidence", "verification", "结论", "更新时间"],
          rows: verdicts.map((verdict) => {
            const axes = axesFrom(verdict);
            const formal = verdictLabel(axes) === "正式 PASS";
            return [
              `<span class="cell-primary mono">${verdict.id}</span>`,
              verdict.subject,
              statusBadge(verdict.execution),
              statusBadge(verdict.validity),
              statusBadge(verdict.business),
              statusBadge(verdict.evidence),
              statusBadge(verdict.verification),
              formal ? badge("正式 PASS", "success", "check") : badge(verdictLabel(axes), "attention"),
              verdict.updated
            ];
          })
        }),
        flush: true
      })}
      <p class="caption" style="margin-top:16px">当前任务在 FX-01 下为“不可正式 PASS”；FX-12 才提供唯一完整正例。</p>
    `;
  }

  const item = view.evidence.find((entry) => entry.id === params.evidenceId) || view.evidence[0];
  const head = pageHeader({
    eyebrow: `Evidence & Verdict · EV-02 · ${view.scenario.id}`,
    title: item.label,
    description: `<span class="mono">${item.id}</span> · ${item.kind} · 访问级别 ${item.access_level}`,
    actions: button("返回证据索引", { href: "/console/evidence", kind: "quiet", icon: "arrow" })
  });
  if (generic) return head + generic;
  const disabledReason = view.flags.noPermission
    ? "当前角色无 EVIDENCE_AUTHORIZED；只读摘要保留。"
    : item.access_level === "SUMMARY_INDEX"
      ? "该证据仅为摘要索引，原始访问需 EVIDENCE_AUTHORIZED。"
      : "";
  return `
    ${head}
    ${stateBanners(view)}
    ${stats([
      { label: "expected", value: item.expected ? "YES" : "NO", note: "是否声明要求" },
      { label: "received", value: item.received ? "YES" : "NO", note: "已接收 ≠ 已核验" },
      { label: "verified", value: item.verified ? "YES" : "NO", note: "复核结果" },
      { label: "state", value: item.state, note: "证据项状态" }
    ])}
    <div class="layout-2" style="margin-top:16px">
      ${panel({
        title: "manifest 元数据",
        note: "只展示引用、大小、digest 与时间",
        body: kv([
          ["evidence_id", `<span class="mono">${item.id}</span>`],
          ["kind", `<span class="mono">${item.kind}</span>`],
          ["size", `<span class="mono">${item.size}</span>`],
          ["digest", `<span class="digest">${item.digest}</span>`],
          ["collected_at", `<span class="mono">${item.collected_at}</span>`],
          ["access_level", badge(item.access_level, item.access_level === "NO_ACCESS" ? "neutral" : "plain")],
          ["display_path_hint", "已脱敏；默认载荷不提供绝对路径"]
        ])
      })}
      ${panel({
        title: "核验状态",
        note: "三态分离",
        body: `
          <div class="checks">
            <div class="check-item ${item.expected ? "is-done" : "is-unknown"}"><div><strong>expected</strong><span class="check-note">${item.expected ? "已声明为要求" : "未声明"}</span></div></div>
            <div class="check-item ${item.received ? "is-done" : "is-missing"}"><div><strong>received</strong><span class="check-note">${item.received ? "已接收，进入校验队列" : "未接收"}</span></div></div>
            <div class="check-item ${item.verified ? "is-done" : "is-unknown"}"><div><strong>verified</strong><span class="check-note">${item.verified ? "已通过复核" : "未核验或隔离"}</span></div></div>
          </div>
          <div class="row" style="margin-top:14px">
            ${button("请求原始访问", { icon: "lock", disabledReason })}
            ${button("查看访问审计", { href: "/console/audit/aud-20261029-039", small: true })}
          </div>
          <p class="caption" style="margin-top:8px">原始访问的允许与拒绝都会产生审计事件；OBSERVER 对原始材料显式 DENY。</p>
        `
      })}
    </div>
    ${panel({
      title: "证据与判定边界",
      note: "缺 cleanup_receipt 不等于证据不完整",
      body: `
        <p class="small secondary">当前证据的 verification 状态为 ${badge(item.verified ? "VERIFIED" : "UNVERIFIED", item.verified ? "success" : "attention")}；
        它不直接决定 release_state，也不把 received 升格为 verified。判定与释放分别由 Linux 写入。</p>
      `
    })}
  `;
}
