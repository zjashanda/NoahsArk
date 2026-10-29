import {
  badge,
  button,
  genericState,
  kv,
  leasePanel,
  pageHeader,
  panel,
  releaseChecklist,
  stateBanners,
  stats,
  statusBadge,
  table,
  inlineNote
} from "../components.js";

function scoped(device, view) {
  if (device.id === "dev-tcl-001") return view;
  const baseLink = {
    communication_state: "ONLINE",
    occupancy_state: "OCCUPIED",
    execution_permit: "GRANTED",
    execution_status: "RUNNING",
    lease_state: "HELD",
    lease_id: device.current_lease_id,
    epoch: device.epoch,
    pool_state: device.pool_state,
    health_state: device.health_state,
    freshness: view.link.freshness
  };
  const release = { local_stop_confirmed: false, safe_cleanup_done: false, occupancy_reconciled: false, cleanup_receipt_id: null, r05: "NODE_REACHABLE" };
  if (device.pool_state === "AVAILABLE") {
    return {
      ...view,
      link: { ...baseLink, occupancy_state: "IDLE", execution_permit: "NONE", execution_status: "IDLE", lease_state: "NONE", lease_id: null, epoch: 0 },
      release: { local_stop_confirmed: true, safe_cleanup_done: true, occupancy_reconciled: true, cleanup_receipt_id: null, r05: "NODE_REACHABLE" }
    };
  }
  if (device.pool_state === "QUARANTINED") {
    return {
      ...view,
      link: { ...baseLink, execution_permit: "REVOKED", execution_status: "BLOCKED", health_state: "QUARANTINED" },
      release
    };
  }
  return {
    ...view,
    link: { ...baseLink, pool_state: "DRAINING" },
    release: { ...release, local_stop_confirmed: true }
  };
}

export function render({ route, params, view }) {
  const generic = genericState(view, "设备");

  if (route.id === "DV-01") {
    const head = pageHeader({
      eyebrow: `Devices & Nodes · DV-01 · ${view.scenario.id}`,
      title: "设备与节点",
      description: "回答在哪里执行、谁占用、能否释放。节点心跳、会话、端点、spool 与设备池状态分开显示。",
      actions: button("查看运行", { href: "/console/runs", icon: "runs" })
    });
    if (generic) return head + generic;
    const nodeCard = (node) => `
      <div class="card">
        <div class="spread"><a href="#/console/nodes/${node.id}"><span class="card-title">${node.label}</span></a>${statusBadge(view.flags.offline && node.id === "node-lab-win-01" ? "OFFLINE" : node.communication_state)}</div>
        <p class="card-note mono">${node.id}</p>
        <div style="margin-top:10px">${kv([
          ["interactive_session", statusBadge(node.interactive_session)],
          ["spool", `${statusBadge(node.spool_state)} · pending ${node.spool_pending}`],
          ["last_heartbeat", `<span class="mono">${node.last_heartbeat_at}</span>`]
        ])}</div>
      </div>`;
    return `
      ${head}
      ${stateBanners(view)}
      ${stats([
        { label: "节点在线", value: "1 / 2", note: "node-b 离线" },
        { label: "已分配设备", value: "1", note: "lease-7781 · epoch 7" },
        { label: "可用设备", value: "1", note: "TCL002" },
        { label: "隔离 / 排空", value: "1 / 1", note: "占用仍保留" }
      ])}
      <div class="section">
        <div class="section-head"><h2 class="section-title">节点</h2><span class="section-note">通信、会话、spool 分离</span></div>
        <div class="grid-cards">${view.world.nodes.map(nodeCard).join("")}</div>
      </div>
      ${panel({
        title: "设备池",
        note: "OFFLINE ≠ IDLE；缺少清理回执保持占用",
        body: table({
          head: ["设备", "pool", "health", "通信", "占用", "lease / epoch", "序列号"],
          rows: view.world.devices.map((device) => {
            const scopedView = scoped(device, view);
            return [
              `<a href="#/console/devices/${device.id}"><span class="cell-primary">${device.label}</span></a><div class="caption mono">${device.id} · ${device.firmware}</div>`,
              statusBadge(device.pool_state),
              statusBadge(device.health_state),
              statusBadge(scopedView.link.communication_state),
              statusBadge(scopedView.link.occupancy_state),
              `<span class="mono">${device.current_lease_id || "—"}</span> / ${device.epoch}`,
              `<span class="mono">${device.serial_masked}</span>`
            ];
          })
        }),
        flush: true
      })}
      ${inlineNote("序列号脱敏显示。释放只依赖 local_stop_confirmed + safe_cleanup_done + occupancy_reconciled（+ R-05），不等待大日志归档或最终判定。")}
    `;
  }

  if (route.id === "DV-03") {
    const node = view.world.nodes.find((item) => item.id === params.nodeId) || view.world.nodes[0];
    const communication = view.flags.offline && node.id === "node-lab-win-01" ? "OFFLINE" : node.communication_state;
    const head = pageHeader({
      eyebrow: `Devices & Nodes · DV-03 · ${view.scenario.id}`,
      title: node.label,
      description: `<span class="mono">${node.id}</span> · 节点事实与平台判定分开`,
      actions: button("返回设备", { href: "/console/devices", kind: "quiet", icon: "arrow" })
    });
    if (generic) return head + generic;
    return `
      ${head}
      ${stateBanners(view)}
      ${stats([
        { label: "通信", value: communication, note: "节点事实" },
        { label: "交互会话", value: node.interactive_session, note: "独立于通信" },
        { label: "spool", value: node.spool_state, note: `pending ${node.spool_pending}` },
        { label: "最后心跳", value: node.last_heartbeat_at.slice(11, 19), note: "仅事实" }
      ])}
      <div class="layout-2" style="margin-top:16px">
        ${panel({
          title: "节点元数据",
          body: kv([
            ["node_id", `<span class="mono">${node.id}</span>`],
            ["communication_state", statusBadge(communication)],
            ["interactive_session", statusBadge(node.interactive_session)],
            ["spool.state", statusBadge(node.spool_state)],
            ["spool.pending", String(node.spool_pending)],
            ["last_heartbeat_at", `<span class="mono">${node.last_heartbeat_at}</span>`],
            ["used_for_decision", badge("false", "neutral")]
          ])
        })}
        ${panel({
          title: "端点",
          note: "不展示真实端口或凭据",
          body: table({
            head: ["端点", "用途", "状态"],
            rows: node.endpoints.map((endpoint, index) => [
              `<span class="mono">${endpoint}</span>`,
              index === 0 ? "串口控制" : "音频采集",
              badge(index === 0 && communication === "OFFLINE" ? "UNREACHABLE" : "AVAILABLE", index === 0 && communication === "OFFLINE" ? "attention" : "neutral")
            ])
          }),
          flush: true
        })}
      </div>
      ${panel({
        title: "设备占用",
        note: "节点可达性不等于可释放",
        body: kv([
          ["assigned_device", `<a href="#/console/devices/dev-tcl-001">dev-tcl-001</a>`],
          ["lease", `<span class="mono">lease-7781</span> · epoch 7`],
          ["occupancy", statusBadge(view.link.occupancy_state)],
          ["R-05", badge("NODE_REACHABLE", "plain")]
        ])
      })}
    `;
  }

  const device = view.world.devices.find((item) => item.id === params.deviceId) || view.world.devices[0];
  const scopedView = scoped(device, view);
  const head = pageHeader({
    eyebrow: `Devices & Nodes · DV-02 · ${view.scenario.id}`,
    title: `${device.label} · ${device.identity}`,
    description: `<span class="mono">${device.id}</span> · 序列号 ${device.serial_masked} · firmware ${device.firmware} · pool ${device.pool_state}`,
    actions: button("返回设备列表", { href: "/console/devices", kind: "quiet", icon: "arrow" })
  });
  if (generic) return head + generic;
  const occupied = scopedView.link.occupancy_state === "OCCUPIED";
  const releaseReady = scopedView.release.local_stop_confirmed && scopedView.release.safe_cleanup_done && scopedView.release.occupancy_reconciled;
  const releaseReason = view.flags.noPermission
    ? "控制需要 ADMIN_ONLY + DEVICE_CONTROL；当前角色只读。"
    : !releaseReady
      ? "三项前置未全真（见下方清单）；缺少 cleanup_receipt 时保持 OCCUPIED。"
      : "";

  return `
    ${head}
    ${stateBanners(view)}
    <div class="layout-2">
      <div>
        ${panel({ title: "四信号、租约与新鲜度", note: "分别显示，不互相替代", body: leasePanel(scopedView) })}
        ${occupied ? panel({ title: "释放前置", note: "释放 ≠ PASS", body: releaseChecklist(scopedView) }) : panel({
          title: "释放状态",
          body: `<p class="small secondary">设备当前为 ${statusBadge(scopedView.link.occupancy_state)}，无租约可释放。OFFLINE 也不会被渲染为 IDLE。</p>`
        })}
        ${panel({
          title: "控制动作",
          note: "ADMIN_ONLY · 二次确认 · 显示前置条件",
          body: `
            <div class="row">
              ${button("请求释放", {
                kind: "danger",
                icon: "stop",
                action: "danger",
                title: "确认释放设备",
                message: "释放只取决于本地停止确认、安全清理完成、占用对账三项，并需要节点可达或现场确认（R-05）。释放不代表判定通过。",
                confirmLabel: "释放",
                result: "释放已提交（mock，不生效）；前置未满足时服务端会拒绝。",
                disabledReason: releaseReason
              })}
              ${button("隔离设备", {
                kind: "danger",
                icon: "shield",
                action: "danger",
                title: "确认隔离设备",
                message: "隔离会阻止新派发，但不会自动清除现有占用或改变业务判定。",
                confirmLabel: "隔离",
                result: "隔离已提交（mock，不生效）。",
                disabledReason: view.flags.noPermission ? "需要 ADMIN_ONLY + DEVICE_CONTROL。" : ""
              })}
              ${button("重新健康检查", { action: "mock", icon: "refresh" })}
            </div>
            <p class="caption" style="margin-top:8px">客户端按钮不构成访问控制；服务端按显式 DENY → ALLOW → 默认 DENY 求值。</p>
          `
        })}
      </div>
      <div>
        ${panel({
          title: "设备身份",
          body: kv([
            ["device_id", `<span class="mono">${device.id}</span>`],
            ["identity", device.identity],
            ["serial", `<span class="mono">${device.serial_masked}</span>`],
            ["firmware", device.firmware],
            ["pool_state", statusBadge(device.pool_state)],
            ["health_state", statusBadge(device.health_state)],
            ["current_lease_id", `<span class="mono">${device.current_lease_id || "—"}</span>`],
            ["epoch", `<span class="mono">${device.epoch}</span>`]
          ])
        })}
        ${panel({
          title: "离线语义",
          body: `<p class="small secondary">OFFLINE 只描述通信，不得改写执行、占用或许可。允许同时出现 OFFLINE + RUNNING + OCCUPIED + GRANTED；对账完成前不得重派。</p>`
        })}
        ${panel({
          title: "相关运行",
          body: `<a href="#/console/runs/run-042">run-042</a> · att-112 · retry_of att-111`
        })}
      </div>
    </div>
  `;
}
