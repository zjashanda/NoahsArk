import {
  badge,
  button,
  esc,
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
import { icon } from "../icons.js";
import { apiGet } from "../api.js";
import {
  createDevice,
  createNode,
  deleteDevice,
  deleteNode,
  getUsbScanResult,
  issueNodeToken,
  queueUsbScan,
  updateDevice
} from "../data-source.js";
import {
  buildUsbBoardDevice,
  parseUsbTree,
  usbBoardAudioCount,
  usbBoardDisplayBase,
  usbBoardRoles,
  usbBoardSerialCount
} from "../usb-tree.js";

const NODE_STATUS_OPTIONS = ["ACTIVE", "DRAINING", "QUARANTINED", "RETIRED"];
const NODE_COMMUNICATION_OPTIONS = ["ONLINE", "STALE", "OFFLINE"];
const DEVICE_KIND_OPTIONS = [
  ["serial", "串口设备"],
  ["audio", "音频设备"],
  ["power", "电源设备"],
  ["lstest", "lstest 设备"],
  ["other", "其他"]
];

// USB scan results survive an in-app route refresh so the import flow can
// reload the device list without losing the board the user just imported.
// Keyed by the node's backend id because that is what the command endpoint takes.
const usbScanStates = new Map();
let pendingUsbDialogReopen = null;

function usbScanStorageKey(nodeId) {
  return `naa-usb-scan:${String(nodeId || "")}`;
}

function persistUsbScanState(nodeId, state) {
  if (!nodeId || typeof window === "undefined" || !window.localStorage) return;
  try {
    window.localStorage.setItem(usbScanStorageKey(nodeId), JSON.stringify({
      status: state.status,
      statusText: state.statusText,
      error: state.error,
      boards: state.boards,
      truncated: state.truncated,
      commandId: state.commandId,
      lastStatus: state.lastStatus
    }));
  } catch {
    // Session storage can be unavailable; in-memory state still works.
  }
}

function restoreUsbScanState(nodeId) {
  if (!nodeId || typeof window === "undefined" || !window.localStorage) return null;
  try {
    const raw = window.localStorage.getItem(usbScanStorageKey(nodeId));
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    return {
      status: parsed.status || "idle",
      statusText: parsed.statusText || "",
      error: parsed.error || null,
      boards: Array.isArray(parsed.boards) ? parsed.boards : null,
      truncated: parsed.truncated === true,
      commandId: parsed.commandId || null,
      lastStatus: parsed.lastStatus || null
    };
  } catch {
    return null;
  }
}

function usbScanStateFor(nodeId) {
  const key = String(nodeId || "");
  let state = usbScanStates.get(key);
  if (!state) {
    const restored = restoreUsbScanState(key);
    state = {
      status: "idle",
      statusText: "",
      error: null,
      boards: null,
      truncated: false,
      running: false,
      importing: false,
      commandId: null,
      lastStatus: null,
      ...(restored || {})
    };
    usbScanStates.set(key, state);
  }
  return state;
}

// A board is already imported when the same container id or the same derived
// display_id exists. A re-scan of the same label keeps the original id rather
// than allocating a fresh -2 suffix.
function sameUsbBoard(device, board) {
  if (!device || !board) return false;
  const identity = deviceIdentityBase(device);
  const container = board.container_id ? String(board.container_id) : "";
  if (container && identity.container_id && String(identity.container_id) === container) return true;
  return String(identity.kind || "") === "usb-board"
    && String(identity.board || "") === String(board.label || "");
}

function assignUsbBoardDisplayIds(boards, devices) {
  const used = new Set();
  const existing = Array.isArray(devices) ? devices : [];
  for (const board of boards) {
    const match = existing.find((device) => sameUsbBoard(device, board));
    if (match && match.id) {
      board.display_id = String(match.id);
      board.imported = true;
      used.add(board.display_id);
      continue;
    }
    const base = usbBoardDisplayBase(board.label);
    let candidate = base;
    let suffix = 2;
    const taken = (id) => used.has(id) || existing.some((device) => String(device.id) === id);
    while (taken(candidate)) {
      candidate = `${base}-${suffix}`;
      suffix += 1;
    }
    used.add(candidate);
    board.display_id = candidate;
    board.imported = false;
  }
  return boards;
}

function usbBoardDetailMarkup(board) {
  const serialRows = (Array.isArray(board.functions) ? board.functions : [])
    .flatMap((fn) => (Array.isArray(fn.ports) ? fn.ports : []).map((port) => [
      esc(fn.name || "—"),
      `<span class="mono">${esc(port.com || "—")}</span>`,
      esc(port.role || "—")
    ]));
  const audioRows = (Array.isArray(board.audio) ? board.audio : []).map((item) => [
    esc(item.direction || "—"),
    esc(item.channels ?? "—"),
    esc(item.name || "—"),
    `<span class="mono cell-path">${esc(item.deviceKey || "—")}</span>`
  ]);
  return `
    ${kv([
      ["板卡名称", esc(board.label || "未命名板卡")],
      ["设备 ID", `<span class="mono">${esc(board.display_id || "—")}</span>`],
      ["容器 ID", `<span class="mono cell-path">${esc(board.container_id || "—")}</span>`],
      ["VID / PID", `<span class="mono">${esc(board.vid || "—")} / ${esc(board.pid || "—")}</span>`],
      ["序列号", `<span class="mono">${esc(board.serial || "—")}</span>`],
      ["串口 / 音频", `${esc(usbBoardSerialCount(board))} / ${esc(usbBoardAudioCount(board))}`]
    ])}
    ${serialRows.length
      ? table({ head: ["功能", "端口", "角色"], rows: serialRows })
      : `<p class="muted small">该板卡没有串口端点。</p>`}
    ${audioRows.length
      ? table({ head: ["方向", "声道", "端点", "设备键"], rows: audioRows })
      : `<p class="muted small">该板卡没有音频端点。</p>`}
  `;
}

function usbBoardDetailDialog(slug, backendId) {
  return `
    <dialog class="task-delete-dialog usb-board-detail-dialog" id="usb-board-detail-${esc(slug)}" data-usb-board-detail-dialog data-node-backend-id="${esc(backendId)}" role="dialog" aria-modal="true" aria-labelledby="usb-board-detail-title-${esc(slug)}">
      <div class="task-dialog-card">
        <div class="task-dialog-head">
          <div>
            <h2 class="task-dialog-title" id="usb-board-detail-title-${esc(slug)}" data-usb-board-detail-title>板卡详情</h2>
            <p class="caption">确认板卡身份、串口与音频端点后再导入。</p>
          </div>
          <button class="icon-button" type="button" data-usb-board-detail-close aria-label="关闭">${icon("close")}</button>
        </div>
        <div class="usb-board-detail-body" data-usb-board-detail-body></div>
        <div class="row task-dialog-actions">
          <button class="btn" type="button" data-usb-board-detail-close>关闭</button>
        </div>
      </div>
    </dialog>
  `;
}

function usbBoardMarkup(board, index) {
  const serialCount = usbBoardSerialCount(board);
  const audioCount = usbBoardAudioCount(board);
  const roles = usbBoardRoles(board);
  const serialText = roles.length
    ? `串口 ${serialCount}（${roles.join(" / ")}）`
    : `串口 ${serialCount}`;
  const imported = board.imported === true;
  return `
    <li class="usb-board${imported ? " is-imported" : ""}" data-usb-board data-usb-board-index="${index}">
      <div class="usb-board-line">
        <div class="usb-board-main" data-usb-board-open data-usb-board-index="${index}" role="button" tabindex="0" title="查看板卡详情">
          <span class="usb-board-label">${esc(board.label || "未命名板卡")}</span>
          <span class="usb-board-meta">${esc(serialText)} · 音频 ${audioCount}</span>
          <span class="usb-board-id mono">${esc(board.display_id || "—")}</span>
        </div>
        <div class="usb-board-side">
          ${imported
            ? `<span class="badge badge-plain" data-usb-imported>已导入</span>`
            : `<button class="btn btn-sm" type="button" data-usb-board-import data-usb-board-index="${index}">导入为设备</button>`}
        </div>
      </div>
      <p class="form-error" data-usb-import-error role="alert" hidden></p>
    </li>
  `;
}


function options(values, selected) {
  return values
    .map((value) => `<option value="${esc(value)}"${value === selected ? " selected" : ""}>${esc(value)}</option>`)
    .join("");
}

function kindOptions(selected) {
  const options = DEVICE_KIND_OPTIONS.map(([value, label]) =>
    `<option value="${esc(value)}"${value === selected ? " selected" : ""}>${esc(label)} · ${esc(value)}</option>`
  );
  if (selected && !DEVICE_KIND_OPTIONS.some(([value]) => value === selected)) {
    options.push(`<option value="${esc(selected)}" selected>${esc(selected)}</option>`);
  }
  return options.join("");
}

function splitList(value) {
  return String(value == null ? "" : value)
    .split(/[,，]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function writeAttrs(apiMode, reason) {
  return apiMode ? "" : ` disabled aria-disabled="true" title="${esc(reason)}"`;
}

function actionButton(label, attrs, apiMode, reason, kind = "") {
  return `<button class="btn btn-sm${kind ? ` ${kind}` : ""}" type="button" ${attrs}${writeAttrs(apiMode, reason)}>${esc(label)}</button>`;
}

// The UI origin is the control plane the page was served from. The installer
// scripts sit on that same static server, so commands never hardcode a host.
function controlPlaneOrigin() {
  if (typeof window === "undefined" || !window.location) return "";
  return String(window.location.origin || "").replace(/\/+$/, "");
}

function buildInstallCommands(nodeId, token) {
  const origin = controlPlaneOrigin();
  return {
    origin,
    linux: `curl -fsSL ${origin}/install/node.sh | sudo bash -s -- --control-plane ${origin} --node-id ${nodeId} --token ${token}`,
    windows: `irm ${origin}/install/node.ps1 -OutFile node.ps1; .\\node.ps1 -ControlPlane ${origin} -NodeId ${nodeId} -Token ${token}`
  };
}

// Platform-wide enrollment commands. The enrollment token auto-creates a node
// from the hostname on first /node/v1/enroll, so no node_id is needed here.
export function buildNodeConnectCommands(token, origin = controlPlaneOrigin()) {
  return {
    origin,
    linux: `curl -fsSL ${origin}/install/node.sh | sudo bash`,
    windows: `irm ${origin}/install/node.ps1 | iex`
  };
}

// Always-visible connect panel for API mode. The token is fetched on hydrate;
// the markup ships empty command blocks so nothing is invented when the
// enrollment-token endpoint is unavailable.
function nodeConnectPanel(apiMode) {
  if (!apiMode) return "";
  return `
    <div class="section node-connect" data-node-connect aria-label="连接节点">
      ${panel({
        title: "连接节点",
        note: "平台接入令牌 · 目标机器执行一条命令即可安装并注册",
        body: `
          <div class="node-connect-body">
            <p class="caption node-connect-note">命令使用本页面来源 <span class="mono" data-node-connect-origin>${esc(controlPlaneOrigin() || "本页面来源")}</span> 与平台接入令牌；令牌由控制面签发，无需先创建节点。</p>
            <div class="install-os-tabs node-connect-tabs" role="tablist" aria-label="连接命令的操作系统">
              <button class="install-os-tab is-active" type="button" role="tab" aria-selected="true" data-node-connect-os="linux" id="node-connect-tab-linux" aria-controls="node-connect-pane-linux">Linux</button>
              <button class="install-os-tab" type="button" role="tab" aria-selected="false" data-node-connect-os="windows" id="node-connect-tab-windows" aria-controls="node-connect-pane-windows">Windows</button>
            </div>
            <div id="node-connect-pane-linux" role="tabpanel" aria-labelledby="node-connect-tab-linux" data-node-connect-pane="linux">
              <div class="install-command" data-node-connect-block hidden>
                <div class="install-command-head">
                  <span class="install-command-label">Linux · bash（sudo）</span>
                  <button class="btn btn-sm" type="button" data-copy-target="node-connect-command-linux" disabled>复制</button>
                </div>
                <pre class="install-code mono" id="node-connect-command-linux" data-node-connect-command="linux"></pre>
              </div>
            </div>
            <div id="node-connect-pane-windows" role="tabpanel" aria-labelledby="node-connect-tab-windows" data-node-connect-pane="windows" hidden>
              <div class="install-command" data-node-connect-block hidden>
                <div class="install-command-head">
                  <span class="install-command-label">Windows · 管理员 PowerShell</span>
                  <button class="btn btn-sm" type="button" data-copy-target="node-connect-command-windows" disabled>复制</button>
                </div>
                <pre class="install-code mono" id="node-connect-command-windows" data-node-connect-command="windows"></pre>
              </div>
            </div>
            <p class="node-install-warning">接入令牌可注册任意节点，请只发送给可信机器，不要写入工单或聊天记录。读取失败时刷新页面重试；不会显示伪造命令。</p>
            <p class="form-error" data-node-connect-error role="alert" hidden></p>
            <span class="caption" data-node-connect-status role="status" aria-live="polite">正在读取平台接入令牌…</span>
          </div>
        `
      })}
    </div>
  `;
}

function communicationBadge(state) {
  const value = String(state || "UNKNOWN").toUpperCase();
  if (value === "ONLINE") return badge("ONLINE", "success", "dot");
  if (value === "STALE") return badge("STALE", "attention", "clock");
  if (value === "OFFLINE") return badge("OFFLINE", "neutral", "offline");
  return badge(value, "neutral");
}

function chips(values, empty = "—") {
  const items = Array.isArray(values) ? values.filter((item) => item !== null && item !== undefined && item !== "") : [];
  if (!items.length) return `<span class="caption">${esc(empty)}</span>`;
  return items.map((item) => `<span class="badge tone-plain mono">${esc(item)}</span>`).join("");
}

function safeKey(value) {
  return String(value == null ? "" : value).replace(/[^A-Za-z0-9_-]/g, "-");
}

function nodeTitle(node) {
  const hostname = String(node.hostname || "").trim();
  if (hostname && hostname !== "—") return hostname;
  return String(node.display_id || node.label || node.id || "");
}

function nodeDisplayId(node) {
  return String(node.display_id || node.id || "");
}

function nodeBackendId(node) {
  return String(node.backend_id || node.id || "");
}

// The compact card only needs the device kind. Live projections sometimes omit
// identity.kind, so fall back to the endpoint kinds that describe the same
// hardware without surfacing endpoint detail.
function deviceKindLabel(device) {
  const explicit = String(device.kind && device.kind !== "—"
    ? device.kind
    : (device.identity && typeof device.identity === "object" ? device.identity.kind : "") || "").trim();
  if (explicit) return explicit;
  const kinds = (Array.isArray(device.endpoints) ? device.endpoints : [])
    .map((endpoint) => String(endpoint && endpoint.kind ? endpoint.kind : ""))
    .map((kind) => (kind.startsWith("audio") ? "audio" : kind))
    .filter(Boolean);
  const unique = [...new Set(kinds)];
  return unique.length ? unique.join("+") : "other";
}

function parseChannels(value) {
  const parsed = Number.parseInt(String(value == null ? "" : value), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function audioEndpoints(device) {
  return (Array.isArray(device.endpoints) ? device.endpoints : []).filter(
    (endpoint) => endpoint && String(endpoint.kind || "") === "audio"
  );
}

function buildEndpoints(data, audioMeta = []) {
  const endpoints = [];
  for (const role of ["control", "csk", "upper"]) {
    const port = String(data.get(`serial_${role}`) || "").trim();
    if (port) endpoints.push({ kind: "serial", role, port });
  }
  for (const direction of ["capture", "render"]) {
    const channels = parseChannels(data.get(`audio_${direction}_channels`));
    if (!channels) continue;
    const existing = audioMeta.find(
      (endpoint) => String(endpoint.direction || "") === direction
    );
    const key = String(data.get(`audio_${direction}_device_key`) || "").trim();
    const name = String(data.get(`audio_${direction}_name`) || "").trim();
    endpoints.push({
      ...(existing || {}),
      kind: "audio",
      direction,
      channels,
      ...(key ? { device_key: key } : {}),
      ...(name ? { name } : {})
    });
  }
  return endpoints;
}

// The UI projection keeps a normalized identity label, but PATCH identity is a
// whole-object write. api-adapter also carries the server identity dict as
// identity_data so editing kind never drops serial_number_masked/model fields.
function deviceIdentityBase(device) {
  for (const candidate of [device.identity_data, device.identity]) {
    if (candidate && typeof candidate === "object" && !Array.isArray(candidate)) {
      return { ...candidate };
    }
  }
  return {};
}

function deviceSerialPort(device, role) {
  const endpoints = Array.isArray(device.endpoints) ? device.endpoints : [];
  const endpoint = endpoints.find((item) =>
    item && String(item.kind || "") === "serial" && String(item.role || "") === role
  );
  return endpoint ? String(endpoint.port || "") : "";
}

function deviceAudioChannels(device, direction) {
  const endpoints = Array.isArray(device.endpoints) ? device.endpoints : [];
  const endpoint = endpoints.find((item) =>
    item && String(item.kind || "") === "audio" && String(item.direction || "") === direction
  );
  const channels = endpoint ? parseChannels(endpoint.channels) : null;
  return channels ? String(channels) : "";
}

function deviceKindValue(device) {
  const explicit = String(
    (device.kind && device.kind !== "—" ? device.kind : "") ||
    deviceIdentityBase(device).kind ||
    ""
  ).trim();
  if (explicit) return explicit;
  return deviceKindLabel(device) || "other";
}

// Endpoints outside the editable serial roles / audio directions are carried
// through untouched so editing capabilities never deletes unmanaged wiring.
function isManagedEndpoint(endpoint) {
  if (!endpoint || typeof endpoint !== "object") return false;
  const kind = String(endpoint.kind || "");
  if (kind === "serial") return ["control", "csk", "upper"].includes(String(endpoint.role || ""));
  if (kind === "audio") return ["capture", "render"].includes(String(endpoint.direction || ""));
  return false;
}

function extraEndpoints(device) {
  return (Array.isArray(device.endpoints) ? device.endpoints : []).filter((endpoint) => !isManagedEndpoint(endpoint));
}

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

function nodeDevices(node, devices) {
  return (devices || []).filter((device) => {
    const owner = String(device.node_id || "");
    return owner && (owner === String(node.id) || owner === String(node.backend_id));
  });
}

function deviceEditForm(device, apiMode, slug) {
  const backendId = device.backend_id || device.id;
  const editKey = safeKey(backendId);
  const formId = `device-edit-${slug}-${editKey}`;
  const fieldId = (name) => `device-edit-${slug}-${editKey}-${name}`;
  const identity = deviceIdentityBase(device);
  const capabilities = (Array.isArray(device.capabilities) ? device.capabilities : []).join(", ");
  const captureAudio = audioEndpoints(device).find((item) => String(item.direction || "") === "capture") || {};
  const renderAudio = audioEndpoints(device).find((item) => String(item.direction || "") === "render") || {};
  const disabled = writeAttrs(apiMode, "仅在 API 模式下可编辑设备。");
  return `
    <form class="device-edit-form" id="${esc(formId)}" data-device-edit-form data-device-id="${esc(backendId)}" data-device-identity="${esc(JSON.stringify(identity))}" data-device-extra-endpoints="${esc(JSON.stringify(extraEndpoints(device)))}" data-device-audio-endpoints="${esc(JSON.stringify(audioEndpoints(device)))}" hidden>
      <div class="form-grid">
        <div class="field"><label for="${esc(fieldId("display"))}">设备标识 display_id</label><input class="input" id="${esc(fieldId("display"))}" name="display_id" value="${esc(device.id)}" maxlength="80" required${disabled}></div>
        <div class="field"><label for="${esc(fieldId("kind"))}">类型 kind</label><select class="select" id="${esc(fieldId("kind"))}" name="kind"${disabled}>${kindOptions(deviceKindValue(device))}</select></div>
      </div>
      <fieldset class="device-fieldset">
        <legend>串口端点 control / csk / upper</legend>
        <div class="form-grid">
          <div class="field"><label for="${esc(fieldId("serial-control"))}">control 串口</label><input class="input" id="${esc(fieldId("serial-control"))}" name="serial_control" value="${esc(deviceSerialPort(device, "control"))}" placeholder="COM6" maxlength="40"${disabled}></div>
          <div class="field"><label for="${esc(fieldId("serial-csk"))}">csk 串口</label><input class="input" id="${esc(fieldId("serial-csk"))}" name="serial_csk" value="${esc(deviceSerialPort(device, "csk"))}" placeholder="COM7" maxlength="40"${disabled}></div>
          <div class="field"><label for="${esc(fieldId("serial-upper"))}">upper 串口</label><input class="input" id="${esc(fieldId("serial-upper"))}" name="serial_upper" value="${esc(deviceSerialPort(device, "upper"))}" placeholder="COM8" maxlength="40"${disabled}></div>
        </div>
      </fieldset>
      <fieldset class="device-fieldset">
        <legend>音频端点</legend>
        <div class="form-grid">
          <div class="field"><label for="${esc(fieldId("audio-capture"))}">采集通道 capture channels</label><input class="input" id="${esc(fieldId("audio-capture"))}" name="audio_capture_channels" type="number" min="1" max="64" value="${esc(deviceAudioChannels(device, "capture"))}" placeholder="8"${disabled}></div>
          <div class="field"><label for="${esc(fieldId("audio-capture-key"))}">采集 DeviceKey</label><input class="input" id="${esc(fieldId("audio-capture-key"))}" name="audio_capture_device_key" value="${esc(captureAudio.device_key || "")}" maxlength="200"${disabled}></div>
          <div class="field"><label for="${esc(fieldId("audio-capture-name"))}">采集名称</label><input class="input" id="${esc(fieldId("audio-capture-name"))}" name="audio_capture_name" value="${esc(captureAudio.name || "")}" maxlength="200"${disabled}></div>
          <div class="field"><label for="${esc(fieldId("audio-render"))}">播放通道 render channels</label><input class="input" id="${esc(fieldId("audio-render"))}" name="audio_render_channels" type="number" min="1" max="64" value="${esc(deviceAudioChannels(device, "render"))}" placeholder="2"${disabled}></div>
          <div class="field"><label for="${esc(fieldId("audio-render-key"))}">播放 DeviceKey</label><input class="input" id="${esc(fieldId("audio-render-key"))}" name="audio_render_device_key" value="${esc(renderAudio.device_key || "")}" maxlength="200"${disabled}></div>
          <div class="field"><label for="${esc(fieldId("audio-render-name"))}">播放名称</label><input class="input" id="${esc(fieldId("audio-render-name"))}" name="audio_render_name" value="${esc(renderAudio.name || "")}" maxlength="200"${disabled}></div>
        </div>
      </fieldset>
      <div class="field field-wide"><label for="${esc(fieldId("capabilities"))}">能力 capabilities（逗号分隔）</label><input class="input" id="${esc(fieldId("capabilities"))}" name="capabilities" value="${esc(capabilities)}" placeholder="serial, audio_capture" maxlength="500"${disabled}><span class="field-hint">写入 capabilities 数组；空白项会被忽略。</span></div>
      <p class="form-error" data-device-edit-error role="alert" hidden></p>
      <div class="row task-dialog-actions device-edit-actions">
        <button class="btn btn-primary" type="submit" data-device-edit-submit${disabled}>保存</button>
        <button class="btn" type="button" data-device-edit-cancel>取消</button>
        <span class="caption" data-device-edit-status role="status" aria-live="polite"></span>
      </div>
    </form>
  `;
}

function deviceEndpointSummary(device) {
  const endpoints = Array.isArray(device.endpoints) ? device.endpoints : [];
  const serial = endpoints
    .filter((item) => item && String(item.kind || "") === "serial")
    .map((item) => `${String(item.role || "serial").toUpperCase()}=${String(item.port || "")}`)
    .filter((item) => !item.endsWith("="));
  const audio = endpoints
    .filter((item) => item && String(item.kind || "") === "audio")
    .map((item) => {
      const channels = parseChannels(item.channels);
      return `${String(item.direction || "audio")}${channels ? ` ${channels}ch` : ""}`;
    });
  const parts = [];
  if (serial.length) parts.push(`serial ${serial.join(" / ")}`);
  if (audio.length) parts.push(`audio ${audio.join(" / ")}`);
  return parts.join(" · ") || "未配置端点";
}

function deviceRow(device, apiMode, slug) {
  const backendId = device.backend_id || device.id;
  const editId = `device-edit-${slug}-${safeKey(backendId)}`;
  return `
    <li class="node-device-row" data-device-row data-device-id="${esc(backendId)}">
      <div class="node-device-line">
        <div class="node-device-main">
          <span class="node-device-display mono">${esc(device.id)}</span>
          <span class="badge badge-plain">${esc(deviceKindLabel(device))}</span>
        </div>
        <div class="node-device-side">
          ${actionButton("编辑", `data-device-edit-open aria-expanded="false" aria-controls="${esc(editId)}"`, apiMode, "仅在 API 模式下可编辑设备。")}
          ${actionButton("删除", `data-device-delete data-device-id="${esc(backendId)}" data-device-display="${esc(device.id)}"`, apiMode, "仅在 API 模式下可删除设备。", "btn-danger")}
        </div>
      </div>
      <span class="node-device-endpoints mono">${esc(deviceEndpointSummary(device))}</span>
      ${deviceEditForm(device, apiMode, slug)}
    </li>
  `;
}

function nodeCard(node, view, apiMode) {
  const devices = nodeDevices(node, view.world.devices || []);
  const title = nodeTitle(node);
  const displayId = nodeDisplayId(node);
  const backendId = nodeBackendId(node);
  const manageTarget = `node-manage-${safeKey(node.id)}`;
  return `
    <article class="node-card" data-node-card data-node-id="${esc(node.id)}" data-node-backend-id="${esc(backendId)}">
      <button class="node-card-main" type="button" data-node-manage-open data-node-manage-target="${esc(manageTarget)}" aria-haspopup="dialog" aria-label="管理节点 ${esc(title)} 的设备">
        <span class="node-card-head">
          <span class="node-card-title">${esc(title)}</span>
          ${communicationBadge(node.communication_state)}
        </span>
        <span class="node-card-meta mono">${esc(displayId)} · ${devices.length} 台设备</span>
      </button>
    </article>
  `;
}

function nodeDeviceCreateForm(node, apiMode, slug) {
  const backendId = nodeBackendId(node);
  return `
    <form class="device-create-form" id="device-create-${esc(slug)}" data-device-create-form data-node-id="${esc(backendId)}" data-node-display="${esc(nodeDisplayId(node))}" hidden>
      <input type="hidden" name="node_id" value="${esc(backendId)}">
      <div class="form-grid">
        <div class="field"><label for="device-display-${esc(slug)}">设备标识 display_id</label><input class="input" id="device-display-${esc(slug)}" name="display_id" placeholder="dev-tcl-005" maxlength="80" required></div>
        <div class="field"><label for="device-kind-${esc(slug)}">类型 kind</label><select class="select" id="device-kind-${esc(slug)}" name="kind" data-device-kind>${kindOptions("serial")}</select></div>
      </div>
      <div class="node-device-endpoints" data-device-endpoint-fields>
        <fieldset class="device-fieldset" data-device-serial-group>
          <legend>串口端点 control / csk / upper</legend>
          <div class="form-grid">
            <div class="field"><label for="device-serial-control-${esc(slug)}">control 串口</label><input class="input" id="device-serial-control-${esc(slug)}" name="serial_control" placeholder="COM6" maxlength="40"></div>
            <div class="field"><label for="device-serial-csk-${esc(slug)}">csk 串口</label><input class="input" id="device-serial-csk-${esc(slug)}" name="serial_csk" placeholder="COM7" maxlength="40"></div>
            <div class="field"><label for="device-serial-upper-${esc(slug)}">upper 串口</label><input class="input" id="device-serial-upper-${esc(slug)}" name="serial_upper" placeholder="COM8" maxlength="40"></div>
          </div>
        </fieldset>
        <fieldset class="device-fieldset" data-device-audio-group hidden>
          <legend>音频端点</legend>
          <div class="form-grid">
            <div class="field"><label for="device-audio-capture-${esc(slug)}">采集通道 capture channels</label><input class="input" id="device-audio-capture-${esc(slug)}" name="audio_capture_channels" type="number" min="1" max="64" placeholder="8"></div>
            <div class="field"><label for="device-audio-render-${esc(slug)}">播放通道 render channels</label><input class="input" id="device-audio-render-${esc(slug)}" name="audio_render_channels" type="number" min="1" max="64" placeholder="2"></div>
          </div>
        </fieldset>
      </div>
      <div class="field field-wide"><label for="device-capabilities-${esc(slug)}">能力 capabilities（逗号分隔）</label><input class="input" id="device-capabilities-${esc(slug)}" name="capabilities" placeholder="serial, audio_capture" maxlength="500"><span class="field-hint">写入 capabilities 数组；不会自动推导。</span></div>
      <p class="form-error" data-device-create-error role="alert" hidden></p>
      <div class="row task-dialog-actions">
        <button class="btn btn-primary" type="submit" data-device-create-submit${writeAttrs(apiMode, "仅在 API 模式下可添加设备。")}>创建设备</button>
        <button class="btn" type="button" data-device-add-cancel>取消</button>
        <span class="caption" data-device-create-status role="status" aria-live="polite"></span>
      </div>
    </form>
  `;
}

function nodeManageDialog(node, view, apiMode) {
  const devices = nodeDevices(node, view.world.devices || []);
  const slug = safeKey(node.id);
  const title = nodeTitle(node);
  const displayId = nodeDisplayId(node);
  const backendId = nodeBackendId(node);
  const deviceRows = devices.length
    ? devices.map((device) => deviceRow(device, apiMode, slug)).join("")
    : `<li class="node-device-empty"><span>该节点下暂无设备。手动添加一台即可开始管理。</span></li>`;
  return `
    <dialog class="task-create-dialog node-manage-dialog" id="node-manage-${esc(slug)}" data-node-manage-dialog data-node-backend-id="${esc(backendId)}" role="dialog" aria-modal="true" aria-labelledby="node-manage-title-${esc(slug)}">
      <div class="task-dialog-card">
        <div class="task-dialog-head">
          <div>
            <div class="node-manage-headline">
              <h2 class="task-dialog-title" id="node-manage-title-${esc(slug)}">${esc(title)}</h2>
              ${communicationBadge(node.communication_state)}
            </div>
            <p class="caption mono">${esc(displayId)} · ${devices.length} 台设备</p>
          </div>
          <button class="icon-button" type="button" data-node-manage-close aria-label="关闭">${icon("close")}</button>
        </div>
        <div class="node-manage-devices">
          <div class="node-devices-head">
            <h3 class="node-devices-title">设备</h3>
            <div class="node-devices-actions">
              ${actionButton("扫描 USB", "data-usb-scan-start", apiMode, "仅在 API 模式下可扫描 USB。")}
              ${actionButton("添加设备", "data-device-add-open aria-expanded=\"false\"", apiMode, "仅在 API 模式下可添加设备。")}
            </div>
          </div>
          <ul class="node-device-list" data-node-manage-list>${deviceRows}</ul>
        </div>
        <div class="usb-scan" data-usb-scan hidden>
          <div class="usb-scan-head">
            <h3 class="node-devices-title">扫描结果</h3>
            <span class="usb-scan-status caption" data-usb-scan-status role="status" aria-live="polite"></span>
          </div>
          <p class="form-error" data-usb-scan-error role="alert" hidden></p>
          <ul class="usb-board-list" data-usb-board-list></ul>
        </div>
        ${nodeDeviceCreateForm(node, apiMode, slug)}
      </div>
    </dialog>
    ${usbBoardDetailDialog(slug, backendId)}
  `;
}

function nodeCreateDialog(apiMode) {
  const origin = controlPlaneOrigin();
  return `
    <dialog class="task-create-dialog node-connect-dialog" id="node-create-dialog" role="dialog" aria-modal="true" aria-labelledby="node-connect-title">
      <div class="task-dialog-card">
        <div class="task-dialog-head">
          <div>
            <h2 class="task-dialog-title" id="node-connect-title">连接节点</h2>
            <p class="caption">在目标机器上执行对应命令，Agent 会自动注册并出现在节点列表中。</p>
          </div>
          <button class="icon-button" type="button" data-node-add-close aria-label="关闭">${icon("close")}</button>
        </div>
        <div class="install-os-tabs" role="tablist" aria-label="连接命令的操作系统">
          <button class="install-os-tab is-active" type="button" role="tab" aria-selected="true" data-node-install-os="linux">Linux</button>
          <button class="install-os-tab" type="button" role="tab" aria-selected="false" data-node-install-os="windows">Windows</button>
        </div>
        <div data-node-install-pane="linux">
          <div class="install-command">
            <div class="install-command-head">
              <span class="install-command-label">Linux · bash（sudo）</span>
              <button class="btn btn-sm" type="button" data-copy-target="node-connect-linux">复制</button>
            </div>
            <pre class="install-code mono" id="node-connect-linux">curl -fsSL ${origin}/install/node.sh | sudo bash</pre>
          </div>
        </div>
        <div data-node-install-pane="windows" hidden>
          <div class="install-command">
            <div class="install-command-head">
              <span class="install-command-label">Windows · 管理员 PowerShell</span>
              <button class="btn btn-sm" type="button" data-copy-target="node-connect-windows">复制</button>
            </div>
            <pre class="install-code mono" id="node-connect-windows">irm ${origin}/install/node.ps1 | iex</pre>
          </div>
        </div>
        <p class="node-install-warning">命令中的平台地址使用当前页面来源；加入令牌由平台在脚本中注入，命令本身不需要参数。</p>
      </div>
    </dialog>
  `;
}

function deleteDialog(apiMode) {
  return `
    <dialog class="task-delete-dialog" id="topology-delete-dialog" role="dialog" aria-modal="true" aria-labelledby="topology-delete-title">
      <div class="task-dialog-card">
        <div class="task-dialog-head">
          <h2 class="task-dialog-title" id="topology-delete-title">删除确认</h2>
          <button class="icon-button" type="button" data-topology-delete-cancel aria-label="关闭">${icon("close")}</button>
        </div>
        <p class="task-dialog-note" data-topology-delete-note>该操作不可恢复。</p>
        <p class="task-dialog-target mono" data-topology-delete-target>—</p>
        <p class="form-error" data-topology-delete-error role="alert" hidden></p>
        <div class="row task-dialog-actions">
          <button class="btn" type="button" data-topology-delete-cancel>取消</button>
          <button class="btn btn-danger" type="button" data-topology-delete-confirm${writeAttrs(apiMode, "仅在 API 模式下可删除。")}>确认删除</button>
          <span class="caption" data-topology-delete-status role="status" aria-live="polite"></span>
        </div>
      </div>
    </dialog>
  `;
}

function errorText(result, fallback) {
  const code = result && result.error && result.error.code;
  const message = result && result.error && result.error.message;
  return `${code || fallback}${message ? `：${message}` : ""}`;
}

export function render({ route, params, view }) {
  const generic = genericState(view, "设备");

  if (route.id === "DV-01") {
    const nodes = view.world.nodes || [];
    const devices = view.world.devices || [];
    const apiMode = Boolean(view.meta && view.meta.server_authoritative);
    const online = nodes.filter((node) => node.communication_state === "ONLINE").length;
    const occupied = devices.filter((device) => device.pool_state === "ASSIGNED" || device.pool_state === "ATTACHED" || device.pool_state === "DRAINING").length;
    const head = pageHeader({
      eyebrow: `Nodes · DV-01 · ${view.scenario.id}`,
      title: "节点管理",
      description: "紧凑节点卡展示主机名、在线状态与设备数；点击节点进入该节点的设备管理。点击“添加节点”查看 Linux/Windows 连接命令。",
      actions: `<button class="btn btn-primary" type="button" data-node-add-open${writeAttrs(apiMode, "仅在 API 模式下可添加节点。")}>${icon("plus")}添加节点</button>`
    });
    if (generic) return head + generic;
    return `
      ${head}
      ${stateBanners(view)}
      ${stats([
        { label: "节点", value: String(nodes.length), note: `${online} 在线` },
        { label: "设备", value: String(devices.length), note: "来自 GET /api/v1/devices" },
        { label: "已分配 / 排空", value: String(occupied), note: "占用状态独立于通信" },
        { label: "写操作", value: apiMode ? "ADMIN" : "只读", note: apiMode ? "POST / DELETE" : "fixture 模式不提交" }
      ])}
      <div class="section">
        <div class="section-head"><h2 class="section-title">节点</h2><span class="section-note">点击卡片管理该节点下的设备</span></div>
        ${nodes.length
          ? `<div class="node-list">${nodes.map((node) => nodeCard(node, view, apiMode)).join("")}</div>`
          : `<p class="muted small" role="status">当前没有节点。点击“添加节点”创建第一个节点。</p>`}
      </div>
      ${inlineNote("写路径：POST /api/v1/nodes、POST /api/v1/devices、DELETE /api/v1/nodes/{node_id}、DELETE /api/v1/devices/{device_id}。节点仍有设备时返回 409 NODE_HAS_DEVICES；设备仍有租约时返回 409 DEVICE_HAS_LEASES。")}
      ${nodeCreateDialog(apiMode)}
      ${nodes.map((node) => nodeManageDialog(node, view, apiMode)).join("")}
      ${deleteDialog(apiMode)}
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

// Node/device management hydration. All writes go through data-source.js so
// this page never assembles control-plane URLs; a successful write closes the
// dialog and asks the shell to re-read GET /nodes + GET /devices.
export function hydrate({ route, host, mode, refresh } = {}) {
  if (!host || route.id !== "DV-01") return null;
  const apiMode = mode === "api";
  const nodeDialog = host.querySelector("#node-create-dialog");
  const deleteDialogEl = host.querySelector("#topology-delete-dialog");
  const manageDialogs = Array.from(host.querySelectorAll("[data-node-manage-dialog]"));
  const connectPanel = host.querySelector("[data-node-connect]");
  if (!nodeDialog && !deleteDialogEl && !manageDialogs.length && !connectPanel) return null;

  const controller = new AbortController();
  let disposed = false;
  let nodeBusy = false;
  let deviceBusy = false;
  let deleteBusy = false;
  let editBusy = false;
  let pendingDelete = null;

  function openDialog(dialog, focusTarget) {
    if (!dialog) return;
    if (typeof dialog.showModal === "function") {
      if (!dialog.open) dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
    window.setTimeout(() => {
      if (focusTarget) focusTarget.focus();
    }, 0);
  }

  function closeDialog(dialog) {
    if (!dialog) return;
    if (typeof dialog.close === "function" && dialog.open) dialog.close();
    else dialog.removeAttribute("open");
  }

  function showError(element, message) {
    if (!element) return;
    element.textContent = message;
    element.hidden = false;
  }

  function clearError(element) {
    if (!element) return;
    element.hidden = true;
    element.textContent = "";
  }

  function setBusy(buttons, statusEl, busy, text) {
    buttons.forEach((node) => {
      if (node) node.disabled = busy || !apiMode;
    });
    if (statusEl) statusEl.textContent = busy ? text : "";
  }

  function showInstallCommands(visible) {
    nodeCommandBlocks.forEach((block) => { block.hidden = !visible; });
    if (nodeDialog) {
      nodeDialog.querySelectorAll("[data-node-command-block] [data-copy-target]").forEach((button) => {
        button.disabled = !visible;
      });
    }
  }

  function resetInstallPanel() {
    pendingNode = null;
    if (nodeForm) nodeForm.hidden = false;
    if (nodeInstall) nodeInstall.hidden = true;
    if (nodeCommandLinux) nodeCommandLinux.textContent = "";
    if (nodeCommandWindows) nodeCommandWindows.textContent = "";
    if (nodeInstallDisplay) nodeInstallDisplay.textContent = "—";
    if (nodeInstallId) nodeInstallId.textContent = "—";
    if (nodeInstallOrigin) nodeInstallOrigin.textContent = "本页面来源";
    if (nodeInstallStatus) nodeInstallStatus.textContent = "";
    if (nodeTokenRetry) nodeTokenRetry.hidden = true;
    clearError(nodeInstallError);
    showInstallCommands(false);
    if (nodeDialog) {
      nodeDialog.querySelectorAll("[data-node-command-block] [data-copy-target]").forEach((button) => {
        button.textContent = "复制";
      });
    }
  }

  function showInstallPanel(display, nodeId) {
    pendingNode = { display, nodeId };
    if (nodeForm) nodeForm.hidden = true;
    if (nodeInstall) nodeInstall.hidden = false;
    if (nodeInstallDisplay) nodeInstallDisplay.textContent = display || "—";
    if (nodeInstallId) nodeInstallId.textContent = nodeId;
    if (nodeInstallOrigin) nodeInstallOrigin.textContent = controlPlaneOrigin() || "本页面来源";
    if (nodeInstallStatus) nodeInstallStatus.textContent = "正在签发一次性令牌…";
    if (nodeTokenRetry) nodeTokenRetry.hidden = true;
    clearError(nodeInstallError);
    showInstallCommands(false);
    window.setTimeout(() => {
      if (nodeInstallDone && !disposed) nodeInstallDone.focus();
    }, 0);
  }

  function tokenErrorMessage(result) {
    const code = result && result.error && result.error.code;
    const status = result && result.status;
    if (status === 403 || code === "FORBIDDEN" || code === "PERMISSION_DENIED") {
      return "当前角色无权签发节点令牌（403）。请切换到 ADMIN / 超级管理员后点击“重新签发令牌”；节点已创建。";
    }
    if (status === 404) return "节点不存在或已被删除（404），无法签发令牌。请关闭后刷新节点列表。";
    if (code === "API_TIMEOUT") return "令牌签发请求超时，请点击“重新签发令牌”。";
    if (code === "API_UNREACHABLE") return "控制面不可达，请检查服务状态后点击“重新签发令牌”。";
    return errorText(result, "令牌签发失败");
  }

  async function requestNodeToken() {
    if (!pendingNode || disposed) return;
    const nodeId = pendingNode.nodeId;
    clearError(nodeInstallError);
    showInstallCommands(false);
    if (nodeTokenRetry) nodeTokenRetry.hidden = true;
    if (nodeInstallStatus) nodeInstallStatus.textContent = "正在签发一次性令牌…";
    const result = await issueNodeToken(nodeId);
    if (disposed) return;
    if (!result.ok) {
      if (nodeInstallStatus) nodeInstallStatus.textContent = "";
      if (nodeTokenRetry) nodeTokenRetry.hidden = false;
      showError(nodeInstallError, tokenErrorMessage(result));
      return;
    }
    const commands = buildInstallCommands(result.data.node_id || nodeId, result.data.token);
    if (nodeCommandLinux) nodeCommandLinux.textContent = commands.linux;
    if (nodeCommandWindows) nodeCommandWindows.textContent = commands.windows;
    if (nodeInstallOrigin) nodeInstallOrigin.textContent = commands.origin || "本页面来源";
    showInstallCommands(true);
    if (nodeInstallStatus) nodeInstallStatus.textContent = "令牌已签发；关闭弹窗后不再显示。";
  }

  async function writeClipboard(value) {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(value);
        return true;
      }
    } catch {
      // Non-secure origins reject the async clipboard API; fall through.
    }
    try {
      const area = document.createElement("textarea");
      area.value = value;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.top = "-1000px";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      const copied = document.execCommand("copy");
      area.remove();
      return copied;
    } catch {
      return false;
    }
  }

  async function copyCommand(button) {
    const targetId = button.getAttribute("data-copy-target");
    const target = targetId ? document.getElementById(targetId) : null;
    const value = target ? target.textContent || "" : "";
    if (!value) return;
    const statusEl = copyStatusFor(button);
    const copied = await writeClipboard(value);
    if (disposed) return;
    if (!copied) {
      if (statusEl) statusEl.textContent = "复制失败，请手动选中命令复制。";
      return;
    }
    button.textContent = "已复制";
    if (statusEl) statusEl.textContent = "命令已复制到剪贴板。";
    copyTimers.push(window.setTimeout(() => { button.textContent = "复制"; }, 1500));
  }

  function createErrorMessage(result, label) {
    const code = result && result.error && result.error.code;
    const status = result && result.status;
    if (status === 403 || code === "FORBIDDEN" || code === "PERMISSION_DENIED") {
      return `当前角色无权创建${label}（403）。请切换到 ADMIN / 超级管理员后重试；客户端按钮不构成访问控制。`;
    }
    if (code === "DISPLAY_ID_CONFLICT" || code === "NODE_ALREADY_EXISTS" || code === "DEVICE_ALREADY_EXISTS") {
      return `${label}标识已存在，请换一个 display_id（409 ${code}）。`;
    }
    if (status === 404) {
      return `所属节点不存在或已被删除（404）。请刷新节点列表后重试。`;
    }
    if (status === 422 || code === "VALIDATION_ERROR" || code === "REQUEST_VALIDATION_ERROR") {
      return errorText(result, `${label}参数校验未通过（422）`);
    }
    if (code === "API_TIMEOUT") return "请求超时，请稍后重试。";
    if (code === "API_UNREACHABLE") return "控制面不可达，请检查服务状态。";
    return errorText(result, `${label}创建失败`);
  }

  function deleteErrorMessage(result) {
    const code = result && result.error && result.error.code;
    if (result && result.status === 403 || code === "FORBIDDEN" || code === "PERMISSION_DENIED") {
      return "当前角色无权删除（403）。请切换到 ADMIN / 超级管理员后重试。";
    }
    if (code === "NODE_HAS_DEVICES") {
      return "该节点仍有设备，无法删除。请先删除或移走该节点下的设备后再试（409 NODE_HAS_DEVICES）。";
    }
    if (code === "DEVICE_HAS_LEASES") {
      return "该设备仍被租约引用，无法删除。请先释放租约后再试（409 DEVICE_HAS_LEASES）。";
    }
    if (code === "RESOURCE_IN_USE") {
      const details = result.error && result.error.details;
      if (details && details.has_devices) return "该节点仍有设备，无法删除（409 RESOURCE_IN_USE）。";
      if (details && details.has_leases) return "该节点仍被租约引用，无法删除（409 RESOURCE_IN_USE）。";
      return "资源仍被引用，无法删除（409 RESOURCE_IN_USE）。";
    }
    if (code === "API_TIMEOUT") return "请求超时，请稍后重试。";
    if (code === "API_UNREACHABLE") return "控制面不可达，请检查服务状态。";
    return errorText(result, "删除失败");
  }

  const nodeForm = nodeDialog ? nodeDialog.querySelector("[data-node-create-form]") : null;
  const nodeError = nodeDialog ? nodeDialog.querySelector("[data-node-create-error]") : null;
  const nodeStatus = nodeDialog ? nodeDialog.querySelector("[data-node-create-status]") : null;
  const nodeSubmit = nodeDialog ? nodeDialog.querySelector("[data-node-create-submit]") : null;
  const nodeButtons = nodeDialog
    ? Array.from(nodeDialog.querySelectorAll("button"))
    : [];

  const nodeInstall = nodeDialog ? nodeDialog.querySelector("[data-node-install]") : null;
  const nodeInstallDisplay = nodeDialog ? nodeDialog.querySelector("[data-node-install-display]") : null;
  const nodeInstallId = nodeDialog ? nodeDialog.querySelector("[data-node-install-id]") : null;
  const nodeInstallOrigin = nodeDialog ? nodeDialog.querySelector("[data-node-install-origin]") : null;
  const nodeInstallError = nodeDialog ? nodeDialog.querySelector("[data-node-install-error]") : null;
  const nodeInstallStatus = nodeDialog ? nodeDialog.querySelector("[data-node-install-status]") : null;
  const nodeInstallDone = nodeDialog ? nodeDialog.querySelector("[data-node-install-done]") : null;
  const nodeTokenRetry = nodeDialog ? nodeDialog.querySelector("[data-node-token-retry]") : null;
  const nodeCommandLinux = nodeDialog ? nodeDialog.querySelector("[data-node-command-linux]") : null;
  const nodeCommandWindows = nodeDialog ? nodeDialog.querySelector("[data-node-command-windows]") : null;
  if (nodeDialog) {
    nodeDialog.addEventListener("click", (event) => {
      const tab = event.target.closest("[data-node-install-os]");
      if (!tab) return;
      const os = tab.getAttribute("data-node-install-os");
      nodeDialog.querySelectorAll("[data-node-install-os]").forEach((el) => {
        const active = el === tab;
        el.classList.toggle("is-active", active);
        el.setAttribute("aria-selected", active ? "true" : "false");
      });
      nodeDialog.querySelectorAll("[data-node-install-pane]").forEach((pane) => {
        pane.hidden = pane.getAttribute("data-node-install-pane") !== os;
      });
    });
  }
  const nodeCommandBlocks = nodeDialog
    ? Array.from(nodeDialog.querySelectorAll("[data-node-command-block]"))
    : [];
  const copyTimers = [];
  let pendingNode = null;
  let nodeCreatedNeedsRefresh = false;

  const connectError = connectPanel ? connectPanel.querySelector("[data-node-connect-error]") : null;
  const connectStatus = connectPanel ? connectPanel.querySelector("[data-node-connect-status]") : null;
  const connectOrigin = connectPanel ? connectPanel.querySelector("[data-node-connect-origin]") : null;
  const connectLinux = connectPanel ? connectPanel.querySelector("[data-node-connect-command='linux']") : null;
  const connectWindows = connectPanel ? connectPanel.querySelector("[data-node-connect-command='windows']") : null;
  const connectBlocks = connectPanel
    ? Array.from(connectPanel.querySelectorAll("[data-node-connect-block]"))
    : [];
  const connectCopyButtons = connectPanel
    ? Array.from(connectPanel.querySelectorAll("[data-copy-target]"))
    : [];

  const deleteTarget = deleteDialogEl ? deleteDialogEl.querySelector("[data-topology-delete-target]") : null;
  const deleteNote = deleteDialogEl ? deleteDialogEl.querySelector("[data-topology-delete-note]") : null;
  const deleteError = deleteDialogEl ? deleteDialogEl.querySelector("[data-topology-delete-error]") : null;
  const deleteStatus = deleteDialogEl ? deleteDialogEl.querySelector("[data-topology-delete-status]") : null;
  const deleteConfirm = deleteDialogEl ? deleteDialogEl.querySelector("[data-topology-delete-confirm]") : null;
  const deleteButtons = deleteDialogEl
    ? Array.from(deleteDialogEl.querySelectorAll("button"))
    : [];

  async function submitNode(event) {
    event.preventDefault();
    if (!apiMode || nodeBusy || !nodeForm) return;
    const data = new FormData(nodeForm);
    const payload = {
      display_id: String(data.get("display_id") || "").trim(),
      hostname: String(data.get("hostname") || "").trim(),
      agent_version: String(data.get("agent_version") || "").trim(),
      status: String(data.get("status") || "ACTIVE"),
      communication_state: String(data.get("communication_state") || "OFFLINE"),
      capabilities: splitList(data.get("capabilities"))
    };
    if (!payload.display_id || !payload.hostname) {
      showError(nodeError, "节点标识与主机名不能为空。");
      return;
    }
    nodeBusy = true;
    clearError(nodeError);
    setBusy(nodeButtons, nodeStatus, true, "正在创建…");
    const result = await createNode(payload);
    if (disposed) return;
    nodeBusy = false;
    setBusy(nodeButtons, nodeStatus, false, "");
    if (!result.ok) {
      showError(nodeError, createErrorMessage(result, "节点"));
      return;
    }
    // The node exists now; refresh the list when this dialog closes even if
    // token issuance fails.
    nodeCreatedNeedsRefresh = true;
    showInstallPanel(result.data.display_id || payload.display_id, result.data.node_id);
    await requestNodeToken();
  }

  async function submitDevice(form, event) {
    event.preventDefault();
    if (!apiMode || deviceBusy || !form) return;
    const data = new FormData(form);
    const kind = String(data.get("kind") || "serial");
    const identity = { kind };
    const endpoints = buildEndpoints(data);
    const nodeId = String(data.get("node_id") || form.getAttribute("data-node-id") || "").trim();
    const payload = {
      display_id: String(data.get("display_id") || "").trim(),
      node_id: nodeId,
      identity,
      endpoints,
      capabilities: splitList(data.get("capabilities"))
    };
    const errorEl = form.querySelector("[data-device-create-error]");
    const statusEl = form.querySelector("[data-device-create-status]");
    const submitBtn = form.querySelector("[data-device-create-submit]");
    if (!payload.display_id) {
      showError(errorEl, "设备标识不能为空。");
      return;
    }
    if (!payload.node_id) {
      showError(errorEl, "缺少所属节点的 node_id，无法创建设备。");
      return;
    }
    if (kind === "serial" && !endpoints.some((endpoint) => endpoint.kind === "serial")) {
      showError(errorEl, "串口设备至少需要填写一个串口端口（control / csk / upper）。");
      return;
    }
    if (kind === "audio" && !endpoints.some((endpoint) => endpoint.kind === "audio")) {
      showError(errorEl, "音频设备至少需要填写采集或播放通道数。");
      return;
    }
    deviceBusy = true;
    clearError(errorEl);
    if (submitBtn) submitBtn.disabled = true;
    if (statusEl) statusEl.textContent = "正在创建…";
    const result = await createDevice(payload);
    if (disposed) return;
    deviceBusy = false;
    if (!result.ok) {
      if (submitBtn) submitBtn.disabled = false;
      if (statusEl) statusEl.textContent = "";
      showError(errorEl, createErrorMessage(result, "设备"));
      return;
    }
    if (statusEl) statusEl.textContent = "";
    const dialog = form.closest("dialog");
    if (dialog) closeDialog(dialog);
    if (typeof refresh === "function") refresh();
  }

  async function confirmDelete() {
    if (!apiMode || deleteBusy || !pendingDelete) return;
    deleteBusy = true;
    clearError(deleteError);
    setBusy(deleteButtons, deleteStatus, true, "正在删除…");
    const target = pendingDelete;
    const result = target.kind === "node"
      ? await deleteNode(target.id)
      : await deleteDevice(target.id);
    if (disposed) return;
    deleteBusy = false;
    if (!result.ok) {
      setBusy(deleteButtons, deleteStatus, false, "");
      showError(deleteError, deleteErrorMessage(result));
      return;
    }
    pendingDelete = null;
    closeDialog(deleteDialogEl);
    if (typeof refresh === "function") refresh();
  }

  function openNodeDialog() {
    if (!apiMode || !nodeDialog) return;
    if (nodeForm) nodeForm.reset();
    resetInstallPanel();
    clearError(nodeError);
    if (nodeStatus) nodeStatus.textContent = "";
    nodeButtons.forEach((node) => {
      if (node) node.disabled = false;
    });
    const first = nodeDialog.querySelector("input[name='display_id']");
    openDialog(nodeDialog, first);
  }

  function syncDeviceGroups(form) {
    if (!form) return;
    const kind = String(new FormData(form).get("kind") || "serial");
    const serialGroup = form.querySelector("[data-device-serial-group]");
    const audioGroup = form.querySelector("[data-device-audio-group]");
    const serialOn = kind === "serial";
    const audioOn = kind === "audio";
    if (serialGroup) {
      serialGroup.hidden = !serialOn;
      serialGroup.querySelectorAll("input").forEach((input) => { input.disabled = !serialOn; });
    }
    if (audioGroup) {
      audioGroup.hidden = !audioOn;
      audioGroup.querySelectorAll("input").forEach((input) => { input.disabled = !audioOn; });
    }
  }

  // Devices already rendered in this dialog, projected into the shape the USB
  // helpers expect. Imported-state checks therefore use the live DOM instead of
  // a stale render snapshot.
  function dialogDevices(dialog) {
    return Array.from(dialog.querySelectorAll("[data-device-row]")).map((row) => {
      const id = row.getAttribute("data-device-id") || "";
      const form = row.querySelector("[data-device-edit-form]");
      let identity = {};
      try {
        const parsed = JSON.parse((form && form.getAttribute("data-device-identity")) || "{}");
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) identity = parsed;
      } catch {
        identity = {};
      }
      return { id, backend_id: id, identity, identity_data: identity };
    }).filter((device) => device.id);
  }

  function renderUsbDialog(dialog) {
    if (!dialog) return;
    const nodeId = dialog.getAttribute("data-node-backend-id") || "";
    if (!nodeId) return;
    const state = usbScanStateFor(nodeId);
    const root = dialog.querySelector("[data-usb-scan]");
    const list = dialog.querySelector("[data-usb-board-list]");
    const statusEl = dialog.querySelector("[data-usb-scan-status]");
    const errorEl = dialog.querySelector("[data-usb-scan-error]");
    const scanButton = dialog.querySelector("[data-usb-scan-start]");
    if (!root || !list) return;

    const boards = Array.isArray(state.boards) ? state.boards : [];
    if (boards.length) assignUsbBoardDisplayIds(boards, dialogDevices(dialog));
    list.innerHTML = boards.length ? boards.map((board, index) => usbBoardMarkup(board, index)).join("") : "";
    const visible = state.running || Boolean(state.error) || boards.length > 0;
    root.hidden = !visible;
    if (state.error) showError(errorEl, state.error);
    else clearError(errorEl);
    if (statusEl) statusEl.textContent = state.statusText || "";
    if (scanButton) {
      scanButton.disabled = !apiMode || state.running;
      scanButton.textContent = state.running ? "扫描中…" : (boards.length ? "重新扫描" : "扫描 USB");
    }
    persistUsbScanState(nodeId, state);
  }

  function usbScanErrorMessage(result) {
    const code = result && result.error && result.error.code;
    const status = result && result.status;
    if (status === 403 || code === "FORBIDDEN" || code === "PERMISSION_DENIED") {
      return "当前角色无权执行 USB 扫描（403）。请切换到 ADMIN / 超级管理员后重试。";
    }
    if (status === 404) return "节点不存在或命令接口不可用（404）。请刷新节点列表后重试。";
    if (status === 422 || code === "VALIDATION_ERROR" || code === "REQUEST_VALIDATION_ERROR") {
      return errorText(result, "USB 扫描参数校验未通过（422）");
    }
    if (code === "COMMAND_TIMEOUT") return "节点命令超时，请稍后重试。";
    if (code === "API_TIMEOUT") return "请求超时，请稍后重试。";
    if (code === "API_UNREACHABLE") return "控制面不可达，请检查服务状态。";
    return errorText(result, "USB 扫描请求失败");
  }

  function usbWait(ms) {
    return new Promise((resolve) => {
      window.setTimeout(resolve, ms);
    });
  }

  async function runUsbScan(trigger) {
    const dialog = trigger.closest("[data-node-manage-dialog]");
    const nodeId = dialog ? dialog.getAttribute("data-node-backend-id") || "" : "";
    if (!apiMode || !dialog || !nodeId) return;
    const state = usbScanStateFor(nodeId);
    if (state.running) return;

    state.running = true;
    state.error = null;
    state.truncated = false;
    state.commandId = null;
    state.lastStatus = null;
    state.statusText = "正在扫描 USB…";
    renderUsbDialog(dialog);

    const queued = await queueUsbScan(nodeId);
    if (disposed) {
      state.running = false;
      return;
    }
    if (!queued.ok) {
      state.running = false;
      state.statusText = "";
      state.error = usbScanErrorMessage(queued);
      renderUsbDialog(dialog);
      return;
    }

    state.commandId = queued.data.command_id;
    const startedAt = Date.now();
    const deadline = startedAt + 45000;
    while (Date.now() < deadline) {
      await usbWait(1000);
      if (disposed) {
        state.running = false;
        return;
      }
      const result = await getUsbScanResult(nodeId, state.commandId);
      if (disposed) {
        state.running = false;
        return;
      }
      if (!result.ok) {
        state.running = false;
        state.statusText = "";
        state.error = usbScanErrorMessage(result);
        renderUsbDialog(dialog);
        return;
      }
      const data = result.data;
      state.lastStatus = data.status;
      if (data.status === "SUCCEEDED" || data.status === "FAILED" || data.status === "TIMEOUT") {
        state.running = false;
        if (data.status === "SUCCEEDED") {
          const boards = parseUsbTree(data.stdout);
          if (!boards.length) {
            state.boards = [];
            state.statusText = "";
            state.error = "扫描已完成，但输出中没有可识别的 USB 板卡。";
          } else {
            state.boards = boards;
            state.truncated = data.truncated === true;
            state.statusText = `扫描完成 · ${boards.length} 块板卡${state.truncated ? " · 输出已截断" : ""}`;
          }
        } else {
          const details = [data.stderr, data.error_code].filter(Boolean).join(" · ");
          state.statusText = "";
          state.error = `扫描${data.status === "TIMEOUT" ? "超时" : "失败"}（${data.status}）${details ? `：${details}` : ""}`;
        }
        renderUsbDialog(dialog);
        return;
      }
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      state.statusText = `正在扫描 USB… ${data.status} · ${elapsed}s`;
      renderUsbDialog(dialog);
    }

    state.running = false;
    state.statusText = "";
    state.error = "扫描超时：45 秒内未返回终态。";
    renderUsbDialog(dialog);
  }

  async function importUsbBoard(trigger) {
    const dialog = trigger.closest("[data-node-manage-dialog]");
    const nodeId = dialog ? dialog.getAttribute("data-node-backend-id") || "" : "";
    if (!apiMode || !dialog || !nodeId) return;
    const state = usbScanStateFor(nodeId);
    if (state.importing) return;
    const index = Number.parseInt(trigger.getAttribute("data-usb-board-index") || "", 10);
    const board = Number.isFinite(index) && Array.isArray(state.boards) ? state.boards[index] : null;
    if (!board) return;
    const row = trigger.closest("[data-usb-board]");
    const errorEl = row ? row.querySelector("[data-usb-import-error]") : null;

    assignUsbBoardDisplayIds(state.boards, dialogDevices(dialog));
    const duplicate = dialogDevices(dialog).some((device) => device.id === board.display_id || sameUsbBoard(device, board));
    if (duplicate || board.imported) {
      board.imported = true;
      renderUsbDialog(dialog);
      return;
    }

    state.importing = true;
    clearError(errorEl);
    trigger.disabled = true;
    trigger.textContent = "正在导入…";
    const result = await createDevice(buildUsbBoardDevice(board, nodeId));
    if (disposed) {
      state.importing = false;
      return;
    }
    state.importing = false;
    if (!result.ok) {
      trigger.disabled = false;
      trigger.textContent = "导入为设备";
      if (errorEl) showError(errorEl, createErrorMessage(result, "设备"));
      return;
    }
    board.imported = true;
    pendingUsbDialogReopen = nodeId;
    if (typeof refresh === "function") refresh();
    else renderUsbDialog(dialog);
  }

  function openUsbBoardDetail(trigger) {
    const manage = trigger.closest("[data-node-manage-dialog]");
    const nodeId = manage ? manage.getAttribute("data-node-backend-id") || "" : "";
    const state = usbScanStateFor(nodeId);
    const index = Number.parseInt(trigger.getAttribute("data-usb-board-index") || "", 10);
    const board = Number.isFinite(index) && Array.isArray(state.boards) ? state.boards[index] : null;
    if (!board) return;
    const detail = Array.from(document.querySelectorAll("[data-usb-board-detail-dialog]"))
      .find((item) => item.getAttribute("data-node-backend-id") === nodeId);
    if (!detail) return;
    const title = detail.querySelector("[data-usb-board-detail-title]");
    const body = detail.querySelector("[data-usb-board-detail-body]");
    if (title) title.textContent = board.label || "板卡详情";
    if (body) body.innerHTML = usbBoardDetailMarkup(board);
    openDialog(detail, detail.querySelector("[data-usb-board-detail-close]"));
  }

  function openManageDialog(trigger) {
    const targetId = trigger.getAttribute("data-node-manage-target") || "";
    const dialog = targetId ? document.getElementById(targetId) : null;
    if (!dialog) return;
    const form = dialog.querySelector("[data-device-create-form]");
    if (form) {
      form.hidden = true;
      form.reset();
      syncDeviceGroups(form);
      clearError(form.querySelector("[data-device-create-error]"));
      const status = form.querySelector("[data-device-create-status]");
      if (status) status.textContent = "";
    }
    const addTrigger = dialog.querySelector("[data-device-add-open]");
    if (addTrigger) addTrigger.setAttribute("aria-expanded", "false");
    dialog.querySelectorAll("[data-device-edit-form]").forEach((editForm) => closeDeviceEdit(editForm));
    renderUsbDialog(dialog);
    openDialog(dialog, dialog.querySelector("[data-node-manage-close]"));
  }

  function closeDeviceEdit(form, focusTrigger = false) {
    if (!form) return;
    form.hidden = true;
    form.reset();
    clearError(form.querySelector("[data-device-edit-error]"));
    const status = form.querySelector("[data-device-edit-status]");
    if (status) status.textContent = "";
    const submitBtn = form.querySelector("[data-device-edit-submit]");
    if (submitBtn) submitBtn.disabled = !apiMode;
    const row = form.closest("[data-device-row]");
    const trigger = row ? row.querySelector("[data-device-edit-open]") : null;
    if (trigger) {
      trigger.setAttribute("aria-expanded", "false");
      if (focusTrigger) trigger.focus();
    }
  }

  function editErrorMessage(result) {
    const code = result && result.error && result.error.code;
    const status = result && result.status;
    if (status === 403 || code === "FORBIDDEN" || code === "PERMISSION_DENIED") {
      return "当前角色无权编辑设备（403）。请切换到 ADMIN / 超级管理员后重试。";
    }
    if (status === 404) return "设备不存在或已被删除（404）。请刷新后重试。";
    if (code === "DEVICE_ALREADY_EXISTS") {
      return `设备标识已存在，请换一个 display_id（409 ${code}）。`;
    }
    if (status === 422) return errorText(result, "修改参数校验未通过（422）");
    if (code === "EMPTY_PATCH") return "没有可提交的修改。";
    if (code === "API_TIMEOUT") return "请求超时，请稍后重试。";
    if (code === "API_UNREACHABLE") return "控制面不可达，请检查服务状态。";
    return errorText(result, "设备修改失败");
  }

  async function submitDeviceEdit(form, event) {
    event.preventDefault();
    if (!apiMode || editBusy || !form) return;
    const data = new FormData(form);
    const displayId = String(data.get("display_id") || "").trim();
    const kind = String(data.get("kind") || "serial").trim() || "serial";
    let identityBase = {};
    let extra = [];
    try {
      const parsed = JSON.parse(form.getAttribute("data-device-identity") || "{}");
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) identityBase = parsed;
    } catch {
      identityBase = {};
    }
    try {
      const parsed = JSON.parse(form.getAttribute("data-device-extra-endpoints") || "[]");
      if (Array.isArray(parsed)) extra = parsed;
    } catch {
      extra = [];
    }
    let audioMeta = [];
    try {
      const parsed = JSON.parse(form.getAttribute("data-device-audio-endpoints") || "[]");
      if (Array.isArray(parsed)) audioMeta = parsed;
    } catch {
      audioMeta = [];
    }
    const payload = {
      display_id: displayId,
      identity: { ...identityBase, kind },
      endpoints: [...buildEndpoints(data, audioMeta), ...extra],
      capabilities: splitList(data.get("capabilities"))
    };
    const errorEl = form.querySelector("[data-device-edit-error]");
    const statusEl = form.querySelector("[data-device-edit-status]");
    const submitBtn = form.querySelector("[data-device-edit-submit]");
    if (!displayId) {
      showError(errorEl, "设备标识不能为空。");
      return;
    }
    editBusy = true;
    clearError(errorEl);
    if (submitBtn) submitBtn.disabled = true;
    if (statusEl) statusEl.textContent = "正在保存…";
    const result = await updateDevice(form.getAttribute("data-device-id") || "", payload);
    if (disposed) return;
    editBusy = false;
    if (!result.ok) {
      if (submitBtn) submitBtn.disabled = false;
      if (statusEl) statusEl.textContent = "";
      showError(errorEl, editErrorMessage(result));
      return;
    }
    if (statusEl) statusEl.textContent = "";
    closeDeviceEdit(form);
    if (typeof refresh === "function") refresh();
  }

  function enrollmentErrorMessage(result) {
    const code = result && result.error && result.error.code;
    const status = result && result.status;
    if (status === 403 || code === "FORBIDDEN" || code === "PERMISSION_DENIED") {
      return "当前角色无权读取平台接入令牌（403）。请切换到 ADMIN / 超级管理员后刷新页面；不会显示伪造命令。";
    }
    if (status === 404) return "控制面未提供平台接入令牌接口（404）。请确认控制面版本后再试。";
    if (code === "API_TIMEOUT") return "平台接入令牌读取超时，请刷新页面重试。";
    if (code === "API_UNREACHABLE") return "控制面不可达，无法读取平台接入令牌，请检查服务状态后刷新页面。";
    return errorText(result, "平台接入令牌读取失败");
  }

  function switchConnectOs(os) {
    if (!connectPanel) return;
    connectPanel.querySelectorAll("[data-node-connect-os]").forEach((tab) => {
      const active = tab.getAttribute("data-node-connect-os") === os;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", active ? "true" : "false");
    });
    connectPanel.querySelectorAll("[data-node-connect-pane]").forEach((pane) => {
      pane.hidden = pane.getAttribute("data-node-connect-pane") !== os;
    });
  }

  function showConnectUnavailable(message) {
    connectBlocks.forEach((block) => { block.hidden = true; });
    connectCopyButtons.forEach((button) => { button.disabled = true; });
    if (connectStatus) connectStatus.textContent = "";
    showError(connectError, message);
  }

  function applyConnectCommands(commands) {
    if (connectLinux) connectLinux.textContent = commands.linux;
    if (connectWindows) connectWindows.textContent = commands.windows;
    if (connectOrigin) connectOrigin.textContent = commands.origin || "本页面来源";
    connectBlocks.forEach((block) => { block.hidden = false; });
    connectCopyButtons.forEach((button) => { button.disabled = false; });
    clearError(connectError);
    if (connectStatus) connectStatus.textContent = "平台接入令牌已就绪；目标机器执行命令即可注册。";
  }

  async function loadConnectCommands() {
    if (!connectPanel || !apiMode || disposed) return;
    clearError(connectError);
    if (connectStatus) connectStatus.textContent = "正在读取平台接入令牌…";
    const result = await apiGet("/nodes/enrollment-token");
    if (disposed) return;
    if (!result.ok) {
      showConnectUnavailable(enrollmentErrorMessage(result));
      return;
    }
    const data = result.payload && typeof result.payload === "object" ? result.payload.data : null;
    const token = data && typeof data.token === "string" ? data.token.trim() : "";
    if (!token) {
      showConnectUnavailable("平台接入令牌接口未返回 token（INVALID_PAYLOAD），请刷新页面重试。");
      return;
    }
    applyConnectCommands(buildNodeConnectCommands(token));
  }

  function copyStatusFor(button) {
    const connect = button.closest("[data-node-connect]");
    if (connect) return connect.querySelector("[data-node-connect-status]");
    return nodeInstallStatus;
  }

  function openDeleteDialog(trigger, kind) {
    if (!apiMode || !deleteDialogEl) return;
    pendingDelete = {
      kind,
      id: trigger.getAttribute(kind === "node" ? "data-node-backend-id" : "data-device-id") || "",
      display: trigger.getAttribute(kind === "node" ? "data-node-display" : "data-device-display") || ""
    };
    clearError(deleteError);
    if (deleteStatus) deleteStatus.textContent = "";
    deleteButtons.forEach((node) => {
      if (node) node.disabled = false;
    });
    if (deleteTarget) deleteTarget.textContent = `${kind === "node" ? "节点" : "设备"} · ${pendingDelete.display} · ${pendingDelete.id}`;
    if (deleteNote) {
      deleteNote.textContent = kind === "node"
        ? "删除节点不可恢复；若节点下仍有设备，服务端会返回 409 NODE_HAS_DEVICES。"
        : "删除设备不可恢复；若设备仍被租约引用，服务端会返回 409 DEVICE_HAS_LEASES。";
    }
    const cancel = deleteDialogEl.querySelector("[data-topology-delete-cancel]");
    openDialog(deleteDialogEl, cancel);
  }

  async function onClick(event) {
    const copyButton = event.target.closest("[data-copy-target]");
    if (copyButton) {
      event.preventDefault();
      void copyCommand(copyButton);
      return;
    }
    const connectTab = event.target.closest("[data-node-connect-os]");
    if (connectTab) {
      event.preventDefault();
      switchConnectOs(connectTab.getAttribute("data-node-connect-os"));
      return;
    }
    if (event.target.closest("[data-node-token-retry]")) {
      event.preventDefault();
      void requestNodeToken();
      return;
    }
    if (event.target.closest("[data-node-install-done]")) {
      event.preventDefault();
      closeDialog(nodeDialog);
      return;
    }
    const usbScanStart = event.target.closest("[data-usb-scan-start]");
    if (usbScanStart) {
      event.preventDefault();
      void runUsbScan(usbScanStart);
      return;
    }
    const usbImport = event.target.closest("[data-usb-board-import]");
    if (usbImport) {
      event.preventDefault();
      void importUsbBoard(usbImport);
      return;
    }
    const usbBoardOpen = event.target.closest("[data-usb-board-open]");
    if (usbBoardOpen) {
      event.preventDefault();
      openUsbBoardDetail(usbBoardOpen);
      return;
    }
    const editOpen = event.target.closest("[data-device-edit-open]");
    if (editOpen) {
      event.preventDefault();
      const row = editOpen.closest("[data-device-row]");
      const form = row ? row.querySelector("[data-device-edit-form]") : null;
      if (!form) return;
      const opening = form.hidden;
      if (opening) {
        const dialog = form.closest("[data-node-manage-dialog]");
        if (dialog) {
          dialog.querySelectorAll("[data-device-edit-form]").forEach((other) => {
            if (other !== form) closeDeviceEdit(other);
          });
        }
      }
      form.hidden = !opening;
      editOpen.setAttribute("aria-expanded", String(opening));
      if (opening) {
        const first = form.querySelector("input[name='display_id']");
        if (first) first.focus();
      }
      return;
    }
    if (event.target.closest("[data-device-edit-cancel]")) {
      event.preventDefault();
      closeDeviceEdit(event.target.closest("[data-device-edit-form]"), true);
      return;
    }
    if (event.target.closest("[data-node-add-open]")) {
      event.preventDefault();
      openNodeDialog();
      return;
    }
    const deviceAddOpen = event.target.closest("[data-device-add-open]");
    if (deviceAddOpen) {
      event.preventDefault();
      const dialog = deviceAddOpen.closest("[data-node-manage-dialog]");
      const form = dialog ? dialog.querySelector("[data-device-create-form]") : null;
      if (!form) return;
      const opening = form.hidden;
      form.hidden = !opening;
      deviceAddOpen.setAttribute("aria-expanded", String(opening));
      if (opening) {
        syncDeviceGroups(form);
        const first = form.querySelector("input[name='display_id']");
        if (first) first.focus();
      }
      return;
    }
    if (event.target.closest("[data-device-add-cancel]")) {
      event.preventDefault();
      const form = event.target.closest("[data-device-create-form]");
      if (form) {
        form.hidden = true;
        clearError(form.querySelector("[data-device-create-error]"));
        const status = form.querySelector("[data-device-create-status]");
        if (status) status.textContent = "";
        const dialog = form.closest("[data-node-manage-dialog]");
        const trigger = dialog ? dialog.querySelector("[data-device-add-open]") : null;
        if (trigger) trigger.setAttribute("aria-expanded", "false");
      }
      return;
    }
    const manageOpen = event.target.closest("[data-node-manage-open]");
    if (manageOpen) {
      event.preventDefault();
      openManageDialog(manageOpen);
      return;
    }
    const nodeDelete = event.target.closest("[data-node-delete]");
    if (nodeDelete) {
      event.preventDefault();
      openDeleteDialog(nodeDelete, "node");
      return;
    }
    const deviceDelete = event.target.closest("[data-device-delete]");
    if (deviceDelete) {
      event.preventDefault();
      openDeleteDialog(deviceDelete, "device");
      return;
    }
    if (event.target.closest("[data-topology-delete-cancel]")) {
      event.preventDefault();
      pendingDelete = null;
      closeDialog(deleteDialogEl);
      return;
    }
    if (event.target.closest("[data-topology-delete-confirm]")) {
      event.preventDefault();
      void confirmDelete();
    }
  }

  function closeOnBackdrop(dialog) {
    return (event) => {
      if (event.target === dialog) closeDialog(dialog);
    };
  }

  function bindClosers(dialog, selector) {
    if (!dialog) return;
    dialog.querySelectorAll(selector).forEach((node) => {
      node.addEventListener("click", () => closeDialog(dialog), { signal: controller.signal });
    });
    dialog.addEventListener("click", closeOnBackdrop(dialog), { signal: controller.signal });
  }

  host.addEventListener("click", (event) => { void onClick(event); }, { signal: controller.signal });
  // Escape inside an inline edit form collapses that form instead of closing
  // the whole node dialog; focus returns to the row's edit button.
  host.addEventListener("keydown", (event) => {
    const boardOpen = event.target instanceof Element ? event.target.closest("[data-usb-board-open]") : null;
    if (boardOpen && (event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      openUsbBoardDetail(boardOpen);
      return;
    }
    if (event.key !== "Escape") return;
    const target = event.target instanceof Element ? event.target : null;
    const form = target ? target.closest("[data-device-edit-form]") : null;
    if (!form || form.hidden) return;
    event.preventDefault();
    event.stopPropagation();
    closeDeviceEdit(form, true);
  }, { signal: controller.signal });
  bindClosers(nodeDialog, "[data-node-add-close]");
  // Every close path (完成 / 关闭 / backdrop / Escape) lands here, so the node
  // list refresh is deferred until after the one-time token has been read.
  if (nodeDialog) {
    nodeDialog.addEventListener("close", () => {
      if (disposed || !nodeCreatedNeedsRefresh) return;
      nodeCreatedNeedsRefresh = false;
      if (typeof refresh === "function") refresh();
    }, { signal: controller.signal });
  }
  manageDialogs.forEach((dialog) => bindClosers(dialog, "[data-node-manage-close]"));
  document.querySelectorAll("[data-usb-board-detail-dialog]").forEach((dialog) => bindClosers(dialog, "[data-usb-board-detail-close]"));
  bindClosers(deleteDialogEl, "[data-topology-delete-cancel]");

  if (nodeForm) nodeForm.addEventListener("submit", submitNode, { signal: controller.signal });
  host.addEventListener("submit", (event) => {
    const createForm = event.target.closest("[data-device-create-form]");
    if (createForm) {
      void submitDevice(createForm, event);
      return;
    }
    const editForm = event.target.closest("[data-device-edit-form]");
    if (editForm) void submitDeviceEdit(editForm, event);
  }, { signal: controller.signal });
  host.addEventListener("change", (event) => {
    if (event.target && event.target.matches("[data-device-kind]")) {
      syncDeviceGroups(event.target.closest("[data-device-create-form]"));
    }
  }, { signal: controller.signal });
  // An import refreshes the whole route. Re-open the same node dialog once the
  // refreshed DOM exists so the imported board is visible in place.
  if (pendingUsbDialogReopen) {
    const reopenId = pendingUsbDialogReopen;
    pendingUsbDialogReopen = null;
    window.setTimeout(() => {
      if (disposed) return;
      const trigger = Array.from(host.querySelectorAll("[data-node-manage-target]")).find((el) => {
        const targetId = el.getAttribute("data-node-manage-target") || "";
        const dialog = targetId ? document.getElementById(targetId) : null;
        return dialog && dialog.getAttribute("data-node-backend-id") === reopenId;
      });
      if (trigger) openManageDialog(trigger);
    }, 0);
  }
  void loadConnectCommands();

  return () => {
    disposed = true;
    controller.abort();
    copyTimers.forEach((timer) => window.clearTimeout(timer));
    usbScanStates.forEach((state) => {
      if (state.running) state.running = false;
    });
    [nodeDialog, deleteDialogEl, ...manageDialogs].forEach((dialog) => {
      if (dialog && dialog.open && typeof dialog.close === "function") dialog.close();
    });
  };
}
