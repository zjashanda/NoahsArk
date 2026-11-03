// Parser for the Windows node's `usbTree-cli --all --format csv` stdout.
//
// The tool prints an indented tree (2 spaces per level in the reference
// output). The parser deliberately derives structure from indentation levels
// instead of hard-coded column widths, so 2- and 4-space variants both work:
//
//   物理 USB 板卡（2 个）          level 0 (summary)
//     ListenAI 板卡                level 1 (board)
//       ListenAI VCOM  (1 个串口)  level 2 (function)
//         COM6                     level 3 (serial port)
//       音频端点  (2 个)            level 2 (audio function)
//         Capture  8ch  VID_...    level 3 (audio endpoint)
//
// Nothing here invents data: missing counts, serial numbers or container ids
// stay null and are reported as absent instead of being guessed.

const ANSI_PATTERN = /\u001b\[[0-9;?]*[ -/]*[@-~]/g;
const GUID_PATTERN = /\{[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}\}/i;
const DEVICE_INSTANCE_PATTERN = /(?:USB[\\/])?VID_[0-9A-F]{4}&PID_[0-9A-F]{4}(?:[:\\][^\s]+)?/i;

export function stripAnsi(value) {
  return String(value == null ? "" : value).replace(ANSI_PATTERN, "");
}

function trailingCount(text) {
  const match = text.match(/[（(]\s*(\d+)\s*个[^）)]*[）)]\s*$/u);
  return match ? Number.parseInt(match[1], 10) : null;
}

function stripTrailingCount(text) {
  return text.replace(/[（(]\s*\d+\s*个[^）)]*[）)]\s*$/u, "").trim();
}

function collapse(text) {
  return String(text || "").replace(/\s+/g, " ").trim();
}

function readIdentity(text) {
  const vid = text.match(/VID[_=: ]?([0-9A-F]{4})/i);
  const pid = text.match(/PID[_=: ]?([0-9A-F]{4})/i);
  const guid = text.match(GUID_PATTERN);
  const labelledSerial = text.match(/(?:S\/N|SN|serial(?:[_ ]?(?:number|no\.?))?)[\s:=#-]+([A-Za-z0-9._-]{3,})/i);
  const instancePath = text.match(/VID_[0-9A-F]{4}&PID_[0-9A-F]{4}[\\/]([^\\/\s]+)/i);
  let serial = labelledSerial ? labelledSerial[1] : null;
  // A Windows instance suffix such as 8_2A847557_0_0000 is a bus-generated
  // path component, not a manufacturer serial number.
  if (!serial && instancePath && !/^\d+_[0-9A-F]+_\d+_\d+$/i.test(instancePath[1])) {
    serial = instancePath[1];
  }
  return {
    vid: vid ? vid[1].toUpperCase() : null,
    pid: pid ? pid[1].toUpperCase() : null,
    serial,
    container_id: guid ? guid[0] : null,
    device_key: (text.match(DEVICE_INSTANCE_PATTERN) || [null])[0]
  };
}

function mergeIdentity(board, identity) {
  if (!board || !identity) return;
  if (!board.vid && identity.vid) board.vid = identity.vid;
  if (!board.pid && identity.pid) board.pid = identity.pid;
  if (!board.serial && identity.serial) board.serial = identity.serial;
  if (!board.container_id && identity.container_id) board.container_id = identity.container_id;
}

function looksLikeSerialFunction(name, text) {
  if (/串口|serial|com\s*port/i.test(name)) return true;
  return /COM\d+/i.test(text);
}

function looksLikeAudioFunction(name, text) {
  if (/音频|audio|sound|endpoint/i.test(name)) return true;
  return /(?:capture|render)\s+\d+\s*ch\b/i.test(text);
}

function parseSerialEntry(text) {
  const portMatch = text.match(/\b(COM\d+)\b/i);
  if (!portMatch) return null;
  const prefix = collapse(text.slice(0, portMatch.index)).replace(/[：:]+$/, "").trim();
  let role = "";
  if (prefix) {
    const tokens = prefix.split(" ");
    const last = tokens[tokens.length - 1] || "";
    role = /^[A-Za-z0-9_-]{1,12}$/.test(last) ? last : "";
  }
  return { role: role || null, com: portMatch[1].toUpperCase() };
}

function serialRole(entry, groupName) {
  if (entry.role) return entry.role;
  if (/VCOM/i.test(groupName || "")) return "VCOM";
  return "serial";
}

function audioDirection(text, name) {
  const lower = `${text} ${name || ""}`.toLowerCase();
  if (/\bcapture\b|麦克风|采集|输入/.test(lower)) return "capture";
  if (/\brender\b|扬声器|播放|输出/.test(lower)) return "render";
  return null;
}

function parseAudioEntry(text) {
  const tokens = text.split(/\s{2,}|\t+/).map((token) => token.trim()).filter(Boolean);
  const keyMatch = text.match(DEVICE_INSTANCE_PATTERN);
  const deviceKey = keyMatch ? keyMatch[0] : null;
  const channelsMatch = text.match(/(\d+)\s*(?:ch|channels?|声道|通道)\b/i);
  const channels = channelsMatch ? Number.parseInt(channelsMatch[1], 10) : null;
  const nameTokens = tokens.filter((token) => {
    if (/^(capture|render)$/i.test(token)) return false;
    if (/\d+\s*(?:ch|channels?|声道|通道)\b/i.test(token) && token.length <= 16) return false;
    if (deviceKey && token.includes(deviceKey)) return false;
    return true;
  });
  const name = collapse(nameTokens.join(" ")) || null;
  const direction = audioDirection(text, name);
  if (!direction) return null;
  return { direction, channels, deviceKey, name };
}

// Convert one indented usbTree block into boards. Returns [] when the output
// has no recognisable board level; callers must treat that as a parse failure,
// never as "no USB boards attached".
export function parseUsbTree(stdout) {
  const text = stripAnsi(stdout).replace(/\r\n?/g, "\n");
  const lines = text
    .split("\n")
    .map((raw) => {
      const expanded = raw.replace(/\t/g, "  ").replace(/\s+$/, "");
      return { text: expanded, trimmed: expanded.trim(), indent: expanded.length - expanded.trimStart().length };
    })
    .filter((line) => line.trimmed);
  if (!lines.length) return [];

  const indents = [...new Set(lines.map((line) => line.indent))].sort((a, b) => a - b);
  if (indents.length < 2) return [];
  const levelOf = (indent) => indents.indexOf(indent);

  const first = lines[0].trimmed;
  const hasSummaryRoot = /物理|设备树|USB\s*设备|共\s*\d+\s*个/.test(first);
  const boardLevel = hasSummaryRoot ? 1 : 0;
  const functionLevel = boardLevel + 1;
  const entryLevel = boardLevel + 2;

  const boards = [];
  let board = null;
  let currentFunction = null;

  for (const line of lines) {
    const level = levelOf(line.indent);
    if (level < boardLevel) continue;

    if (level === boardLevel) {
      board = {
        label: stripTrailingCount(line.trimmed),
        functions: [],
        audio: [],
        vid: null,
        pid: null,
        serial: null,
        container_id: null
      };
      boards.push(board);
      currentFunction = null;
      continue;
    }
    if (!board) continue;

    if (level === functionLevel) {
      const name = stripTrailingCount(line.trimmed);
      const isAudio = looksLikeAudioFunction(name, line.trimmed) && !looksLikeSerialFunction(name, line.trimmed);
      currentFunction = { name, type: isAudio ? "audio" : "serial" };
      if (!isAudio) board.functions.push({ name, ports: [] });
      continue;
    }

    if (level < entryLevel) continue;

    const identity = readIdentity(line.trimmed);
    mergeIdentity(board, identity);

    if (currentFunction && currentFunction.type === "audio") {
      const audio = parseAudioEntry(line.trimmed);
      if (audio) board.audio.push(audio);
      continue;
    }

    const entry = parseSerialEntry(line.trimmed);
    if (!entry) continue;
    let group = board.functions[board.functions.length - 1];
    if (!group) {
      group = { name: currentFunction ? currentFunction.name : "串口", ports: [] };
      board.functions.push(group);
    }
    group.ports.push({ role: serialRole(entry, group.name), com: entry.com });
  }

  return boards;
}

// display_id base derived from the board label. ASCII-only slugs keep the id
// usable on every platform; a repeated base gets a numeric suffix upstream.
export function usbBoardDisplayBase(label) {
  const slug = String(label == null ? "" : label)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  const base = !slug ? "board" : (/^usb(-|$)/.test(slug) ? slug : `usb-${slug}`);
  return base.slice(0, 64);
}

export function usbBoardSerialCount(board) {
  return (board && Array.isArray(board.functions) ? board.functions : [])
    .reduce((total, group) => total + (Array.isArray(group.ports) ? group.ports.length : 0), 0);
}

export function usbBoardAudioCount(board) {
  return board && Array.isArray(board.audio) ? board.audio.length : 0;
}

export function usbBoardRoles(board) {
  const roles = [];
  for (const group of board && Array.isArray(board.functions) ? board.functions : []) {
    for (const port of Array.isArray(group.ports) ? group.ports : []) {
      if (port.role && !roles.includes(port.role)) roles.push(port.role);
    }
  }
  return roles;
}

export function usbBoardEndpoints(board) {
  const endpoints = [];
  for (const group of board && Array.isArray(board.functions) ? board.functions : []) {
    for (const port of Array.isArray(group.ports) ? group.ports : []) {
      if (!port.com) continue;
      endpoints.push({ kind: "serial", role: port.role || "serial", port: port.com });
    }
  }
  for (const audio of board && Array.isArray(board.audio) ? board.audio : []) {
    const endpoint = { kind: "audio", direction: audio.direction };
    if (audio.channels) endpoint.channels = audio.channels;
    if (audio.deviceKey) endpoint.device_key = audio.deviceKey;
    if (audio.name) endpoint.name = audio.name;
    endpoints.push(endpoint);
  }
  return endpoints;
}

export function usbBoardCapabilities(board) {
  const capabilities = [];
  if (usbBoardSerialCount(board) > 0) capabilities.push("serial");
  if (usbBoardAudioCount(board) > 0) capabilities.push("audio");
  return capabilities;
}

// Only non-empty identity fields are sent; the server stores exactly what the
// USB tree proved, never null placeholders.
export function usbBoardIdentity(board) {
  const identity = { kind: "usb-board" };
  const label = board && board.label ? String(board.label).trim() : "";
  if (label) identity.board = label;
  for (const [key, value] of [
    ["container_id", board && board.container_id],
    ["vid", board && board.vid],
    ["pid", board && board.pid],
    ["serial", board && board.serial]
  ]) {
    const clean = value ? String(value).trim() : "";
    if (clean) identity[key] = clean;
  }
  return identity;
}

export function buildUsbBoardDevice(board, nodeId) {
  return {
    display_id: board.display_id,
    node_id: nodeId,
    identity: usbBoardIdentity(board),
    endpoints: usbBoardEndpoints(board),
    capabilities: usbBoardCapabilities(board)
  };
}
