import {
  badge,
  button,
  genericState,
  kv,
  pageHeader,
  panel,
  releaseChecklist,
  stateBanners,
  stats,
  statusBadge,
  table,
  inlineNote
} from "../components.js";
import { isFormalPass } from "../semantics.js";

const SECTIONS = [
  "范围与目标",
  "被测对象与版本",
  "修订与冻结快照",
  "环境、节点与设备",
  "执行摘要",
  "用例与 oracle",
  "分母与采样口径",
  "结果与失败分类",
  "证据索引与核验",
  "五轴判定",
  "风险与限制",
  "发布建议",
  "附录与复现步骤",
  "审计、签署与披露"
];

export function render({ route, params, view }) {
  const generic = genericState(view, "报告");
  const formal = isFormalPass(view.axes);

  if (route.id === "RP-01") {
    const head = pageHeader({
      eyebrow: `Reports · RP-01 · ${view.scenario.id}`,
      title: "报告与交付",
      description: "冻结报告包含 14 章节、分母口径、四类记录分离与披露级别。冻结后不可原地修改。",
      actions: button("打开当前报告", { href: "/console/reports/rpt-voice-001", icon: "reports" })
    });
    if (generic) return head + generic;
    return `
      ${head}
      ${stateBanners(view)}
      ${panel({
        title: "报告版本",
        note: "版本冻结；更正走新版本",
        body: table({
          head: ["报告", "版本", "lifecycle", "分母", "章节", "披露", "创建时间"],
          rows: view.world.reports.map((report) => [
            `<a href="#/console/reports/${report.id}"><span class="cell-primary">${report.title}</span></a><div class="caption mono">${report.id}</div>`,
            `v${report.version}`,
            statusBadge(report.lifecycle),
            report.denominator == null ? "—" : String(report.denominator),
            String(report.sections),
            badge(report.disclosure, "plain"),
            report.created_at
          ])
        }),
        flush: true
      })}
      ${inlineNote("报告冻结与设备释放相互独立：缺清理回执时可以业务 PASS，但必须同时显示“释放未确认”。")}
    `;
  }

  const report = view.world.reports.find((item) => item.id === params.reportId) || view.world.reports[0];
  const head = pageHeader({
    eyebrow: `Reports · RP-02 · ${view.scenario.id}`,
    title: report.title,
    description: `<span class="mono">${report.id}</span> · v${report.version} · ${report.lifecycle} · 披露 ${report.disclosure}`,
    actions: button("返回报告列表", { href: "/console/reports", kind: "quiet", icon: "arrow" })
  });
  if (generic) return head + generic;

  return `
    ${head}
    ${stateBanners(view)}
    ${stats([
      { label: "版本", value: `v${report.version}`, note: report.lifecycle },
      { label: "分母", value: report.denominator == null ? "—" : String(report.denominator), note: "approved denominator" },
      { label: "章节", value: String(report.sections), note: "固定 14 类" },
      { label: "证据索引", value: String(report.evidence_index), note: "不内嵌原始材料" }
    ])}
    <div class="layout-2" style="margin-top:16px">
      <div>
        ${panel({
          title: "章节",
          note: "TOC 仅导航；受限章节显示访问提示，不预加载内容",
          body: `
            <div class="toc">
              ${SECTIONS.map((title, index) => `<span class="toc-item"><span>${String(index + 1).padStart(2, "0")} ${title}</span>${index < 9 ? badge("READY", "neutral") : badge("RESTRICTED", "plain", "lock")}</span>`).join("")}
            </div>
          `
        })}
        ${panel({
          title: "关键章节摘要",
          note: "mock 文本；非验收结论",
          body: `
            <div class="stack">
              <div><h3 class="card-title">01 范围与目标</h3><p class="small secondary">覆盖 TCL001 唤醒词、串口恢复与两类噪声场景；正式分母 40 次。</p></div>
              <div><h3 class="card-title">07 分母与采样口径</h3><p class="small secondary">仅 formal run 计入；smoke、simulation、replay 独立记录，不拼接。</p></div>
              <div><h3 class="card-title">10 五轴判定</h3><p class="small secondary">当前为 ${view.axes.execution_status} / ${view.axes.validity_status} / ${view.axes.business_verdict} / ${view.axes.evidence_status} / ${view.axes.verification_status}；${formal ? "精确满足正式 PASS 组合。" : "不满足正式 PASS 精确组合。"}</p></div>
              <div><h3 class="card-title">11 风险与限制</h3><p class="small secondary">${formal ? "全部证据已核验；释放前置已满足（mock）。" : "串口恢复日志已接收未核验；参考音频缺失；释放前置未满足。"}</p></div>
              <div><h3 class="card-title">14 审计与披露</h3><p class="small secondary">报告冻结后不可原地修改；更正产生新版本并写入审计。</p></div>
            </div>
          `
        })}
      </div>
      <div>
        ${panel({
          title: "记录分离",
          note: "四类记录不得混合",
          body: table({
            head: ["类别", "数量", "进入正式分母"],
            rows: [
              ["formal", "40", badge("YES", "success")],
              ["smoke", "1", badge("NO", "neutral")],
              ["simulation", "0", badge("NO", "neutral")],
              ["replay", "0", badge("NO", "neutral")]
            ]
          })
        })}
        ${panel({
          title: "披露级别",
          body: kv([
            ["summary_to_observer", badge("ALLOW", "plain")],
            ["raw_evidence", badge("DENY", "danger", "lock")],
            ["customer_copy", badge("NOT ISSUED", "neutral")],
            ["internal_notes", badge("ALLOW", "plain")]
          ])
        })}
        ${panel({ title: "释放状态（独立于报告）", body: releaseChecklist(view) })}
      </div>
    </div>
    <div class="row" style="margin-top:16px">
      ${button("导出摘要", { icon: "file", disabledReason: "导出需要 ADMIN_ONLY + EXPORT_AUDIT；原型不产生导出文件。" })}
      ${button("生成更正经版本", {
        icon: "refresh",
        action: "danger",
        title: "生成更正经版本",
        message: "冻结报告不可原地修改。将创建新版本草稿（mock），原版本保持不变，并写入审计事件。",
        confirmLabel: "创建草稿",
        result: "已创建更正经版本草稿 rpt-voice-001-v4（mock，不写入服务端）"
      })}
    </div>
  `;
}
