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
  inlineNote
} from "../components.js";

const ADMIN_NOTE = "仅 SUPER_ADMIN 可见与可写；永不显示私钥、证书、令牌或真实凭据。";

export function render({ route, view }) {
  const generic = genericState(view, "设置");
  const settings = view.world.settings;

  if (route.id === "ST-02") {
    const head = pageHeader({
      eyebrow: `Settings & Access · ST-02 · ${view.scenario.id}`,
      title: "访问与角色",
      description: "展示角色、任务关系与能力映射；策略版本与生效时间可见。",
      actions: button("返回设置", { href: "/console/settings", kind: "quiet", icon: "arrow" })
    });
    if (generic) return head + generic;
    return `
      ${head}
      ${stateBanners(view)}
      ${panel({
        title: "角色",
        note: "服务端求值：显式 DENY → 显式 ALLOW → 默认 DENY",
        body: table({
          head: ["role", "范围", "access_level", "capability", "策略版本"],
          rows: settings.roles.map((role) => [
            `<span class="cell-primary mono">${role.role}</span>`,
            role.scope,
            badge(role.access, role.access === "ADMIN_ONLY" ? "attention" : "plain"),
            `<span class="mono">${role.capability}</span>`,
            `<span class="mono">acl-2026.10</span>`
          ])
        }),
        flush: true
      })}
      ${panel({
        title: "任务关系",
        note: "无关系默认 DENY",
        body: table({
          head: ["关系", "可见范围", "可执行动作"],
          rows: [
            ["Submitter", "任务摘要 + 草稿", "创建草稿、提交审阅"],
            ["Approver", "任务摘要 + 冻结内容", "批准 / 拒绝（APPROVE_TASK）"],
            ["Session Manager", "设备元数据 + 控制", "租约、节点控制（ADMIN_ONLY）"],
            ["Observer", "只读摘要", "无原始证据访问；显式 DENY"]
          ]
        })
      })}
      <div class="row" style="margin-top:16px">
        ${button("分配角色", { icon: "user", action: "danger", title: "确认角色变更", message: "角色变更写入 ROLE_CHANGE 审计；策略版本与生效时间必须可见。", confirmLabel: "变更", result: "角色变更已提交（mock，不生效）。" })}
        ${button("编辑能力映射", { icon: "lock", disabledReason: ADMIN_NOTE })}
      </div>
      ${inlineNote(ADMIN_NOTE)}
    `;
  }

  if (route.id === "ST-03") {
    const head = pageHeader({
      eyebrow: `Settings & Access · ST-03 · ${view.scenario.id}`,
      title: "通知",
      description: "显示投递状态与死信数量；目标地址脱敏，不含凭据。",
      actions: button("返回设置", { href: "/console/settings", kind: "quiet", icon: "arrow" })
    });
    if (generic) return head + generic;
    return `
      ${head}
      ${stateBanners(view)}
      ${panel({
        title: "通道与投递",
        note: "死信不会静默丢弃",
        body: table({
          head: ["通道", "目标（脱敏）", "投递", "死信", "测试"],
          rows: settings.notifications.map((item) => [
            `<span class="cell-primary">${item.channel}</span>`,
            item.target,
            statusBadge(item.delivery),
            item.dead_letter ? badge(String(item.dead_letter), "attention") : badge("0", "neutral"),
            button("发送测试", { small: true, disabledReason: "原型不发送真实通知。" })
          ])
        }),
        flush: true
      })}
      <div class="layout-2" style="margin-top:16px">
        ${panel({
          title: "通知规则",
          body: kv([
            ["待 STOP 升级", badge("ENABLED", "neutral")],
            ["对账超时提醒", badge("ENABLED", "neutral")],
            ["审批超时", badge("提醒 / 升级", "neutral")],
            ["自动拒绝", badge("FORBIDDEN", "danger")]
          ])
        })}
        ${panel({
          title: "投递边界",
          body: `<p class="small secondary">通知只承载提醒，不替代权威状态；超时不自动拒绝审批。目标地址与凭据在服务端脱敏后再下发。</p>`
        })}
      </div>
      ${inlineNote(ADMIN_NOTE)}
    `;
  }

  if (route.id === "ST-04") {
    const head = pageHeader({
      eyebrow: `Settings & Access · ST-04 · ${view.scenario.id}`,
      title: "保留与删除",
      description: "展示保留策略、版本与生效时间；危险变更需要二次确认并写入审计。",
      actions: button("返回设置", { href: "/console/settings", kind: "quiet", icon: "arrow" })
    });
    if (generic) return head + generic;
    return `
      ${head}
      ${stateBanners(view)}
      ${panel({
        title: "保留策略",
        note: "审计事件不可原地修改",
        body: table({
          head: ["对象", "策略", "版本", "生效时间", "动作"],
          rows: settings.retention.map((policy) => [
            `<span class="cell-primary">${policy.object}</span>`,
            policy.policy,
            `<span class="mono">${policy.version}</span>`,
            policy.effective_at,
            button("修改", {
              small: true,
              action: "danger",
              title: "确认修改保留策略",
              message: `将修改「${policy.object}」的保留策略。变更写入 DATA_RETENTION_CHANGE 审计，并可能影响历史数据可读性。`,
              confirmLabel: "确认变更",
              result: "保留策略变更已提交（mock，不生效）。"
            })
          ])
        }),
        flush: true
      })}
      ${panel({
        title: "危险区",
        note: "删除与保留变更不可撤销",
        body: `
          <p class="small secondary">删除请求不会立即清除审计与证据链；必须走补偿事件与保留策略。原型不执行任何删除。</p>
          <div class="row" style="margin-top:10px">
            ${button("删除任务数据", {
              kind: "danger",
              icon: "x",
              action: "danger",
              title: "确认删除任务数据",
              message: "删除请求会进入保留策略评估，不会立即物理删除；审计事件保留。",
              confirmLabel: "提交删除请求",
              result: "删除请求已登记（mock，不执行删除）。",
              disabledReason: ADMIN_NOTE
            })}
          </div>
        `
      })}
      ${inlineNote("保留策略变更与删除都写入审计；客户端隐藏不构成访问控制。")}
    `;
  }

  const head = pageHeader({
    eyebrow: `Settings & Access · ST-01 · ${view.scenario.id}`,
    title: "设置与访问",
    description: "配置角色、关系、通知与保留策略；永不显示密钥或真实凭据。",
    actions: button("访问与角色", { href: "/console/settings/access", kind: "primary", icon: "user" })
  });
  if (generic) return head + generic;
  const cards = [
    { title: "访问与角色", note: "角色、任务关系、能力映射", href: "/console/settings/access", badgeText: "ADMIN_ONLY" },
    { title: "通知", note: "投递、死信、升级规则", href: "/console/settings/notifications", badgeText: "2 DEAD LETTER" },
    { title: "保留与删除", note: "保留策略、版本、危险区", href: "/console/settings/retention", badgeText: "3 POLICIES" }
  ];
  return `
    ${head}
    ${stateBanners(view)}
    <div class="banner banner-blocked">
      ${statusBadge("ADMIN_ONLY")}
      <div class="banner-body"><strong>仅 SUPER_ADMIN 可写</strong> · 当前原型只读；所有设置变更均为 mock，不产生真实效果。</div>
    </div>
    ${stats([
      { label: "角色", value: String(settings.roles.length), note: "显式能力映射" },
      { label: "保留策略", value: String(settings.retention.length), note: "版本化" },
      { label: "通知死信", value: "2", note: "邮件通道降级" },
      { label: "策略版本", value: "acl-2026.10", note: "生效时间可见" }
    ])}
    <div class="grid-cards" style="margin-top:16px">
      ${cards.map((card) => `
        <div class="card">
          <div class="spread"><a href="#${card.href}"><span class="card-title">${card.title}</span></a>${badge(card.badgeText, "plain")}</div>
          <p class="card-note">${card.note}</p>
          <p style="margin-top:12px"><a class="btn btn-sm" href="#${card.href}">打开</a></p>
        </div>`).join("")}
    </div>
    ${inlineNote(ADMIN_NOTE)}
  `;
}
