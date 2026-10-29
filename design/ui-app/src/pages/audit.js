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
  const generic = genericState(view, "审计");

  if (route.id === "AU-03") {
    const head = pageHeader({
      eyebrow: `Audit & Recovery · AU-03 · ${view.scenario.id}`,
      title: "恢复与对账",
      description: "固定恢复顺序与 STOP-first 六步；未演练不得声称 RPO/RTO。",
      actions: button("返回审计", { href: "/console/audit", kind: "quiet", icon: "arrow" })
    });
    if (generic) return head + generic;
    return `
      ${head}
      ${stateBanners(view)}
      ${stats([
        { label: "恢复演练", value: "未演练", note: "不得声称 RPO/RTO" },
        { label: "对账范围", value: view.flags.reconciling ? "1 run" : "0", note: "run-042" },
        { label: "待 STOP", value: String(view.flags.pendingStop ? 1 : 0), note: "先处理" },
        { label: "备份结论", value: "NOT PROVEN", note: "仅静态记录" }
      ])}
      <div class="layout-2" style="margin-top:16px">
        ${panel({
          title: "STOP-first 重连顺序",
          note: "顺序固定，不可跳步",
          body: timeline([
            { title: "1 · 处理待 STOP", time: "14:02:44", body: "先送达并确认 STOP，未送达前不得显示已停止。", state: "current" },
            { title: "2 · 停止后续动作", body: "节点回执 local_stop_confirmed。", state: "blocked" },
            { title: "3 · 补传", body: "补传离线期间事实。", state: "blocked" },
            { title: "4 · 去重", body: "按 attempt 与 evidence digest 去重。", state: "blocked" },
            { title: "5 · 对账", body: "占用、lease、epoch 对账。", state: "blocked" },
            { title: "6 · 恢复领取", body: "仅在此后恢复新派发。", state: "blocked" }
          ])
        })}
        <div>
          ${panel({
            title: "恢复顺序",
            note: "数据库 → manifest/摘要 → 任务/运行 → 设备占用",
            body: `
              <ul class="list-plain">
                <li>1. 数据库恢复</li>
                <li>2. manifest / 摘要恢复</li>
                <li>3. 任务 / 运行恢复</li>
                <li>4. 设备占用对账</li>
              </ul>
              <p class="caption" style="margin-top:8px">顺序不可交换；未对账前不得恢复派发。</p>
            `
          })}
          ${panel({
            title: "对账范围",
            body: table({
              head: ["对象", "本地停止", "清理回执", "占用对账"],
              rows: [[
                `<a class="mono" href="#/console/runs/run-042">run-042</a>`,
                view.flags.pendingStop ? badge("PENDING", "attention") : badge("CONFIRMED", "neutral"),
                badge("MISSING", "danger"),
                badge("PENDING", "attention")
              ]]
            })
          })}
          ${panel({
            title: "备份演练",
            body: `<p class="small secondary">静态记录显示备份存在，但恢复演练尚未执行。不得写成达到 RPO/RTO，也不得把未演练写成已恢复。</p>`
          })}
        </div>
      </div>
      <div class="row" style="margin-top:16px">
        ${button("执行恢复演练", {
          kind: "danger",
          icon: "refresh",
          action: "danger",
          title: "确认恢复演练",
          message: "演练固定顺序：数据库 → manifest/摘要 → 任务/运行 → 设备占用对账。未完成对账前禁止恢复派发。",
          confirmLabel: "开始演练",
          result: "恢复演练已登记（mock，不执行真实恢复）。",
          disabledReason: "需要 ADMIN_ONLY；原型不执行恢复。"
        })}
        ${button("导出审计", { disabledReason: "跨任务导出需要 ADMIN_ONLY + EXPORT_AUDIT，且导出本身产生审计。" })}
      </div>
      ${inlineNote("恢复与对账只处理事实与占用，不改变业务判定；PASS 与 release 仍相互独立。")}
    `;
  }

  if (route.id === "AU-02") {
    const event = view.world.audit.find((item) => item.id === params.eventId) || view.world.audit[0];
    const head = pageHeader({
      eyebrow: `Audit & Recovery · AU-02 · ${view.scenario.id}`,
      title: `Audit ${event.id}`,
      description: `${event.action} · ${event.object} · ${event.occurred_at}`,
      actions: button("返回审计", { href: "/console/audit", kind: "quiet", icon: "arrow" })
    });
    if (generic) return head + generic;
    return `
      ${head}
      ${stateBanners(view)}
      <div class="layout-2">
        ${panel({
          title: "事件事实",
          body: kv([
            ["event_id", `<span class="mono">${event.id}</span>`],
            ["occurred_at", `<span class="mono">${event.occurred_at}</span>`],
            ["actor_role", `<span class="mono">${event.actor_role}</span>`],
            ["action", `<span class="mono">${event.action}</span>`],
            ["object", `<span class="mono">${event.object}</span>`],
            ["access_decision", statusBadge(event.access_decision)],
            ["reason", "策略求值：显式 DENY 优先于 ALLOW；默认 DENY。"],
            ["integrity", badge("HASH_CHAIN_OK", "success", "shield")]
          ])
        })}
        ${panel({
          title: "变更前后",
          note: "受限字段脱敏，不展示凭据",
          body: table({
            head: ["字段", "before", "after"],
            rows: [
              ["revision_content_digest", "—", `<span class="digest">sha256:5ac1…8b41</span>`],
              ["scope_snapshot", "—", "40 formal samples"],
              ["role", event.actor_role, event.actor_role],
              ["secret", badge("REDACTED", "plain", "lock"), badge("REDACTED", "plain", "lock")]
            ]
          })
        })}
      </div>
      ${panel({
        title: "不可变性与更正",
        body: `<p class="small secondary">审计事件不可编辑或删除；更正必须写入补偿事件，保留原事件与哈希链。此页面为只读投影。</p>`
      })}
      ${inlineNote("允许与拒绝都审计；客户端隐藏不构成访问控制。")}
    `;
  }

  const head = pageHeader({
    eyebrow: `Audit & Recovery · AU-01 · ${view.scenario.id}`,
    title: "审计",
    description: "回答谁做了什么、允许或拒绝、before/after 与哈希链；审计不可编辑。",
    actions: button("恢复与对账", { href: "/console/recovery", kind: "primary", icon: "refresh" })
  });
  if (generic) return head + generic;
  return `
    ${head}
    ${stateBanners(view)}
    ${panel({
      title: "审计事件",
      note: "任务范围默认可见；跨任务导出受限",
      body: table({
        head: ["事件", "时间", "actor", "action", "对象", "决策", "完整性"],
        rows: view.world.audit.map((event) => [
          `<a href="#/console/audit/${event.id}"><span class="cell-primary mono">${event.id}</span></a>`,
          event.occurred_at,
          `<span class="mono">${event.actor_role}</span>`,
          `<span class="mono">${event.action}</span>`,
          `<span class="mono">${event.object}</span>`,
          statusBadge(event.access_decision),
          badge(event.integrity, "success", "shield")
        ])
      }),
      flush: true
    })}
    ${inlineNote("审计不可编辑或删除；更正走补偿事件。跨任务导出需要 ADMIN_ONLY + EXPORT_AUDIT，导出本身也产生审计。")}
  `;
}
