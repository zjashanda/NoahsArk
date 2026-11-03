// Route data source selector.
//
// Fixture mode is the default and stays synchronous.  API mode is opt-in via
// ?api=1 (or localStorage) and never falls back to fixtures: a failed request
// returns an explicit error so the UI can show retry / switch-to-fixture.

import {
  apiDelete,
  apiFetch,
  apiGet,
  apiPatch,
  apiPost,
  endpointForRoute,
  isApiMode,
  sessionMessagesEndpoint,
  supervisorEndpoint,
  taskDeleteEndpoint
} from "./api.js";
import { view as fixtureView } from "./fixtures.js";
import { campaignOutcome } from "./semantics.js";

const ENTRY_MODES = ["conversation", "file", "spreadsheet", "form", "template"];
const LEAD_SESSION_KEY = "naa-lead-session";
export const DEFAULT_LEAD_AGENT_ID = "agt-planner";
// Known UUID for agt-planner; used only if the control plane rejects the
// display id on write.
export const DEFAULT_LEAD_AGENT_UUID = "f9b49965-74a8-53d0-88bc-d3f349c56f05";
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function text(value, fallback = "—") {
  if (value === undefined || value === null || value === "") return fallback;
  return String(value);
}

function randomUuid() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "00000000-0000-4000-8000-" + String(Date.now()).padStart(12, "0").slice(-12);
}

// A stable client-side lead session id lets tasks created from this browser
// share one lead session.  The control plane only stores the UUID; it does not
// treat it as an authentication credential.
export function leadSessionId() {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      const stored = window.localStorage.getItem(LEAD_SESSION_KEY);
      if (stored && UUID_RE.test(stored)) return stored;
      const created = randomUuid();
      window.localStorage.setItem(LEAD_SESSION_KEY, created);
      return created;
    }
  } catch {
    // localStorage can be unavailable in private/sandboxed contexts.
  }
  return randomUuid();
}

export const MAX_TASK_RESOURCES = 50;

// Task resources may arrive from a form as a comma string or an array; the
// control plane accepts a list of UUIDs.  Empty and duplicate entries are
// dropped so a repeated checkbox cannot inflate the request.
export function normalizeResourceIds(value) {
  const raw = Array.isArray(value)
    ? value
    : typeof value === "string"
      ? value.split(",")
      : [];
  const ids = [];
  for (const item of raw) {
    const id = String(item ?? "").trim();
    if (id && !ids.includes(id)) ids.push(id);
  }
  return ids;
}

// Pure TaskCreate builder mirroring apps/control_plane/noahsark/api/writes.py.
// Optional fields stay at their server defaults when the form omits them.
export function buildTaskCreate(input = {}) {
  return {
    title: String(input.title ?? "").trim(),
    objective: String(input.objective ?? "").trim(),
    entry_mode: ENTRY_MODES.includes(input.entry_mode) ? input.entry_mode : "form",
    task_category: "voice_interaction",
    lead_agent_id: String(input.lead_agent_id ?? "").trim() || DEFAULT_LEAD_AGENT_ID,
    lead_session_id: String(input.lead_session_id ?? "").trim() || leadSessionId(),
    prompt: String(input.prompt ?? "").trim(),
    node_ids: normalizeResourceIds(input.node_ids),
    device_ids: normalizeResourceIds(input.device_ids)
  };
}

function resourceText(value, fallback = "—") {
  if (value === undefined || value === null || value === "") return fallback;
  return String(value);
}

function resourceNode(row) {
  const id = resourceText(row.node_id ?? row.id ?? row.display_id, "").trim();
  const display = resourceText(row.display_id ?? row.hostname ?? row.label ?? id, id);
  const state = resourceText(row.communication_state ?? row.status, "UNKNOWN").toUpperCase();
  return {
    id,
    display_id: display,
    hostname: resourceText(row.hostname ?? row.label ?? display, display),
    state,
    online: state === "ONLINE"
  };
}

function resourceKind(device) {
  if (device.identity && typeof device.identity === "object") {
    return resourceText(device.identity.kind ?? device.identity.model, "—");
  }
  if (typeof device.identity === "string" && device.identity) return device.identity;
  if (Array.isArray(device.capabilities) && device.capabilities.length) {
    return device.capabilities.join(", ");
  }
  return "—";
}

function resourceDevice(row, nodesById) {
  const nestedNode = row.node && typeof row.node === "object" ? row.node : null;
  const id = resourceText(row.device_id ?? row.id ?? row.display_id, "").trim();
  const nodeId = resourceText(
    row.node_id ?? (nestedNode && (nestedNode.node_id ?? nestedNode.display_id)),
    ""
  ).trim();
  const node = nodesById.get(nodeId) || null;
  const state = resourceText(
    row.communication_state ?? row.health_state ?? (nestedNode && nestedNode.communication_state),
    "UNKNOWN"
  ).toUpperCase();
  return {
    id,
    display_id: resourceText(row.display_id ?? row.label ?? id, id),
    kind: resourceKind(row),
    node_id: nodeId || null,
    node_label: node ? node.display_id : (nestedNode && resourceText(nestedNode.display_id ?? nestedNode.hostname, nodeId)) || nodeId || "—",
    state,
    online: state === "ONLINE"
  };
}

// Execution resources for the create-task dialog.  API mode reads the live
// control-plane topology; fixture mode returns the demo topology and never
// creates a real task.  A failed read stays visible so the dialog can offer a
// retry instead of presenting an empty, misleading list.
export async function loadTaskResources() {
  if (!isApiMode()) {
    const fixture = fixtureView();
    const world = (fixture && fixture.world) || {};
    const nodes = (Array.isArray(world.nodes) ? world.nodes : [])
      .map(resourceNode)
      .filter((node) => node.id)
      .sort((a, b) => a.display_id.localeCompare(b.display_id));
    const nodesById = new Map(nodes.map((node) => [node.id, node]));
    const devices = (Array.isArray(world.devices) ? world.devices : [])
      .map((device) => resourceDevice(device, nodesById))
      .filter((device) => device.id)
      .sort((a, b) => a.display_id.localeCompare(b.display_id));
    return { ok: true, mode: "fixture", nodes, devices };
  }

  const [nodesResult, devicesResult] = await Promise.all([
    apiGet("/nodes"),
    apiGet("/devices")
  ]);
  if (!nodesResult.ok) {
    return { ok: false, mode: "api", error: { ...nodesResult.error, status: nodesResult.status } };
  }
  if (!devicesResult.ok) {
    return { ok: false, mode: "api", error: { ...devicesResult.error, status: devicesResult.status } };
  }
  const nodesData = nodesResult.payload && typeof nodesResult.payload === "object" ? nodesResult.payload.data : {};
  const devicesData = devicesResult.payload && typeof devicesResult.payload === "object" ? devicesResult.payload.data : {};
  const nodes = (Array.isArray(nodesData.items) ? nodesData.items : [])
    .map(resourceNode)
    .filter((node) => node.id)
    .sort((a, b) => a.display_id.localeCompare(b.display_id));
  const nodesById = new Map(nodes.map((node) => [node.id, node]));
  const devices = (Array.isArray(devicesData.items) ? devicesData.items : [])
    .map((device) => resourceDevice(device, nodesById))
    .filter((device) => device.id)
    .sort((a, b) => a.display_id.localeCompare(b.display_id));
  return { ok: true, mode: "api", nodes, devices };
}

// A task title derived from the free-form description. The description stays
// the objective and prompt; only the first ~60 characters become the title.
export function titleFromDescription(value) {
  const clean = String(value ?? "").replace(/\s+/g, " ").trim();
  return clean.slice(0, 60);
}

function rejectsLeadAgentIdentifier(result) {
  const error = (result && result.error) || {};
  const details = error.details && typeof error.details === "object" ? error.details : {};
  if (details.field === "lead_agent_id") return true;
  if (result && result.status === 404) return true;
  return /agent/i.test(String(error.message || ""));
}

// POST /api/v1/tasks.  apiPost mints a fresh Idempotency-Key for each call, so
// every user submission is independently replay-safe.  No fixture fallback is
// attempted: a failed write returns the server error to the caller. If the
// control plane rejects the agt-planner display id, the same request is retried
// once with its known UUID.
export async function createTask(input = {}) {
  const body = buildTaskCreate(input);
  const missing = ["title", "objective", "prompt"].filter((field) => !body[field]);
  if (missing.length) {
    return {
      ok: false,
      status: 0,
      error: {
        code: "VALIDATION_ERROR",
        message: `Missing required fields: ${missing.join(", ")}`,
        retryable: false,
        details: { fields: missing }
      }
    };
  }

  if (
    body.node_ids.length > MAX_TASK_RESOURCES
    || body.device_ids.length > MAX_TASK_RESOURCES
  ) {
    return {
      ok: false,
      status: 0,
      error: {
        code: "VALIDATION_ERROR",
        message: "At most 50 nodes and 50 devices may be selected",
        retryable: false,
        details: {
          fields: ["node_ids", "device_ids"],
          max: MAX_TASK_RESOURCES,
          node_ids: body.node_ids.length,
          device_ids: body.device_ids.length
        }
      }
    };
  }

  let result = await apiPost("/tasks", body);
  if (!result.ok && body.lead_agent_id === DEFAULT_LEAD_AGENT_ID && rejectsLeadAgentIdentifier(result)) {
    result = await apiPost("/tasks", { ...body, lead_agent_id: DEFAULT_LEAD_AGENT_UUID });
  }
  if (!result.ok) {
    return {
      ok: false,
      status: result.status,
      error: { ...(result.error || {}), status: result.status }
    };
  }

  const data = result.payload && typeof result.payload === "object" ? result.payload.data : null;
  if (!data || typeof data !== "object" || !data.task_id) {
    return {
      ok: false,
      status: result.status,
      error: {
        code: "INVALID_PAYLOAD",
        message: "Task response has no data.task_id",
        retryable: false,
        status: result.status
      }
    };
  }
  return { ok: true, status: result.status, task: data, meta: result.payload.meta || null };
}

// Pure projection of GET /tasks/{task_id}/supervisor.  The remote session id is
// only displayed when the server marks it as already masked; this module never
// reconstructs or unmasks it.
export function normalizeSupervisor(data, endpoint = null) {
  const source = data && typeof data === "object" ? data : {};
  const result = source.result && typeof source.result === "object" ? source.result : {};
  const prompt = source.prompt && typeof source.prompt === "object" ? source.prompt : {};
  const available = result.available === true;
  return {
    status: "ready",
    endpoint,
    task_id: text(source.task_id, null),
    task_display_id: text(source.task_display_id, null),
    supervisor_display_id: text(source.supervisor_display_id, null),
    created_at: text(source.created_at, null),
    state: text(source.state, "UNKNOWN"),
    state_is_terminal: source.state_is_terminal === true,
    remote_session_id: source.remote_session_id_masked === true
      ? text(source.remote_session_id, "—")
      : "—",
    remote_session_id_masked: source.remote_session_id_masked === true,
    model: text(source.model ?? source.model_id ?? source.opencode_model_id, null),
    prompt_digest: text(prompt.digest, null),
    prompt_bytes: Number.isFinite(prompt.bytes) ? prompt.bytes : null,
    result_available: available,
    result_summary: available ? text(result.summary, "—") : null,
    result_error_code: result.error_code ? text(result.error_code, null) : null,
    result_updated_at: text(result.updated_at, null),
    updated_at: text(source.updated_at, null)
  };
}

export async function loadTaskSupervisor(taskId) {
  const endpoint = supervisorEndpoint(taskId);
  if (!endpoint) return { status: "missing", task_id: null };

  const result = await apiGet(endpoint);
  if (!result.ok) {
    // A task without a supervisor binding is a legacy task, not a request
    // failure: the page falls back to the traditional detail projection.
    if (result.status === 404) {
      return { status: "absent", endpoint, task_id: String(taskId) };
    }
    return {
      status: "error",
      endpoint,
      task_id: String(taskId),
      error: { ...(result.error || {}), status: result.status }
    };
  }

  const data = result.payload && typeof result.payload === "object" ? result.payload.data : null;
  if (!data || typeof data !== "object") {
    return {
      status: "error",
      endpoint,
      task_id: String(taskId),
      error: {
        code: "INVALID_PAYLOAD",
        message: "Supervisor response has no data object",
        retryable: false,
        status: result.status
      }
    };
  }
  return normalizeSupervisor(data, endpoint);
}

// Static fixture value, clearly labeled as demo by the panel. It is never used
// in API mode and never replaces a failed request.
export function demoSupervisor() {
  return {
    status: "demo",
    task_id: "tsk-demo-0001",
    task_display_id: "tsk-demo-0001",
    supervisor_display_id: "sup-demo-0001",
    model: "fixture-demo",
    state: "COMPLETED",
    state_is_terminal: true,
    remote_session_id: "ses_***DEMO",
    remote_session_id_masked: true,
    prompt_digest: "sha256:fixture-demo",
    prompt_bytes: 49,
    result_available: true,
    result_summary: "PONG（fixture 演示）",
    result_error_code: null,
    result_updated_at: "2026-10-30T07:20:42Z",
    updated_at: "2026-10-30T07:20:42Z"
  };
}

// Convert one provider message into the chat projection the page renders.
// Only text parts survive. Empty/tool-only provider turns are dropped at the
// projection boundary instead of becoming synthetic placeholder bubbles.
export function projectSessionMessage(message) {
  const source = message && typeof message === "object" ? message : {};
  const parts = Array.isArray(source.parts) ? source.parts : [];
  const text = parts
    .filter((part) => part && part.type === "text")
    .map((part) => String(part.text || ""))
    .join("\n")
    .trim();
  if (!text) return null;
  return {
    message_id: textOrNull(source.message_id),
    role: textOrNull(source.role) || "unknown",
    created_at: textOrNull(source.created_at),
    text,
    error_code: textOrNull(source.error_code)
  };
}

function textOrNull(value) {
  if (value === undefined || value === null || value === "") return null;
  return String(value);
}

export function normalizeSessionMessages(data) {
  const source = data && typeof data === "object" ? data : {};
  const messages = Array.isArray(source.messages)
    ? source.messages.map(projectSessionMessage).filter(Boolean)
    : [];
  return {
    status: "ready",
    task_id: textOrNull(source.task_id),
    state: textOrNull(source.state) || "UNKNOWN",
    state_is_terminal: source.state_is_terminal === true,
    message_count: messages.length,
    truncated: source.truncated === true,
    messages
  };
}

// Read the bound conversation. A task whose provider session is not bound yet
// is a normal intermediate state, not an error.
export async function loadTaskSessionMessages(taskId) {
  const endpoint = sessionMessagesEndpoint(taskId);
  if (!endpoint) return { status: "missing", task_id: null, messages: [] };

  const result = await apiGet(endpoint);
  if (!result.ok) {
    const code = result.error && result.error.code;
    if (result.status === 409 && code === "SESSION_NOT_BOUND") {
      return { status: "unbound", endpoint, task_id: String(taskId), messages: [] };
    }
    if (result.status === 404) {
      return { status: "absent", endpoint, task_id: String(taskId), messages: [] };
    }
    return {
      status: "error",
      endpoint,
      task_id: String(taskId),
      messages: [],
      error: { ...(result.error || {}), status: result.status }
    };
  }

  const data = result.payload && typeof result.payload === "object" ? result.payload.data : null;
  if (!data || typeof data !== "object") {
    return {
      status: "error",
      endpoint,
      task_id: String(taskId),
      messages: [],
      error: {
        code: "INVALID_PAYLOAD",
        message: "Session messages response has no data object",
        retryable: false,
        status: result.status
      }
    };
  }
  return { ...normalizeSessionMessages(data), endpoint };
}

// POST one follow-up turn. Returns the assistant reply on success; failures are
// returned verbatim so the composer can surface SESSION_BUSY / SESSION_NOT_BOUND.
export async function sendTaskSessionMessage(taskId, value) {
  const endpoint = sessionMessagesEndpoint(taskId);
  const clean = String(value ?? "").trim();
  if (!endpoint) {
    return {
      ok: false,
      status: 0,
      error: { code: "MISSING_TASK_ID", message: "Task id is required", retryable: false }
    };
  }
  if (!clean) {
    return {
      ok: false,
      status: 0,
      error: { code: "SESSION_MESSAGE_EMPTY", message: "请输入内容后再发送。", retryable: false }
    };
  }

  // Follow-up turns are blocking: the model may need minutes.  The shared
  // apiFetch default (4s) would abort the turn and leave an empty assistant
  // message behind, so give this call a long budget.
  const result = await apiPost(endpoint, { text: clean }, { timeout: 180000 });
  if (!result.ok) {
    return {
      ok: false,
      status: result.status,
      error: { ...(result.error || {}), status: result.status }
    };
  }
  const data = result.payload && typeof result.payload === "object" ? result.payload.data : null;
  if (!data || typeof data !== "object") {
    return {
      ok: false,
      status: result.status,
      error: {
        code: "INVALID_PAYLOAD",
        message: "Session message response has no data object",
        retryable: false,
        status: result.status
      }
    };
  }
  return {
    ok: true,
    status: result.status,
    message: {
      message_id: textOrNull(data.message_id),
      role: textOrNull(data.role) || "assistant",
      created_at: textOrNull(data.created_at),
      text: String(data.text || ""),
      error_code: null
    }
  };
}

// Fixture-only conversation. Clearly demo-labeled and never sent to a server.
export function demoSessionMessages() {
  return {
    status: "demo",
    task_id: "tsk-demo-0001",
    state: "COMPLETED",
    state_is_terminal: true,
    message_count: 2,
    truncated: false,
    messages: [
      {
        message_id: "msg-demo-1",
        role: "user",
        created_at: "2026-10-30T07:20:10Z",
        text: "Reply with the single word PONG and nothing else.",
        error_code: null
      },
      {
        message_id: "msg-demo-2",
        role: "assistant",
        created_at: "2026-10-30T07:20:42Z",
        text: "PONG（fixture 演示）",
        error_code: null
      }
    ]
  };
}

// DELETE /api/v1/tasks/{task_id}. A 404 means the task is already gone, which
// is the caller's success condition; TASK_ACTIVE stays a visible failure.
export async function deleteTask(taskId) {
  const endpoint = taskDeleteEndpoint(taskId);
  if (!endpoint) {
    return {
      ok: false,
      status: 0,
      error: { code: "MISSING_TASK_ID", message: "Task id is required", retryable: false }
    };
  }

  const result = await apiDelete(endpoint);
  if (!result.ok) {
    if (result.status === 404) {
      return { ok: true, status: 404, alreadyGone: true, data: null };
    }
    return {
      ok: false,
      status: result.status,
      error: { ...(result.error || {}), status: result.status }
    };
  }

  const data = result.payload && typeof result.payload === "object" ? result.payload.data : null;
  if (!data || data.deleted !== true) {
    return {
      ok: false,
      status: result.status,
      error: {
        code: "INVALID_PAYLOAD",
        message: "Delete response has no data.deleted=true",
        retryable: false,
        status: result.status
      }
    };
  }
  return { ok: true, status: result.status, alreadyGone: false, data };
}

// ---------------------------------------------------------------------------
// Node / device topology writes (ADMIN).  The read side of DV-01 needs two
// collections, so it is loaded together here instead of through one route
// endpoint; every write keeps the shared apiPost/apiDelete error envelope.
// ---------------------------------------------------------------------------

function writeError(result) {
  return {
    ok: false,
    status: result.status,
    error: { ...(result.error || {}), status: result.status }
  };
}

function createdPayload(result, key) {
  const data = result.payload && typeof result.payload === "object" ? result.payload.data : null;
  if (!data || data.created !== true || !data[key]) {
    return {
      ok: false,
      status: result.status,
      error: {
        code: "INVALID_PAYLOAD",
        message: `Create response has no data.${key}`,
        retryable: false,
        status: result.status
      }
    };
  }
  return { ok: true, status: result.status, data };
}

export async function createNode(input = {}) {
  const body = {
    display_id: String(input.display_id || "").trim(),
    hostname: String(input.hostname || "").trim(),
    agent_version: String(input.agent_version || "").trim() || "unknown",
    status: input.status || "ACTIVE",
    communication_state: input.communication_state || "OFFLINE",
    capabilities: Array.isArray(input.capabilities) ? input.capabilities : [],
    endpoint_ids: [],
    identity: {},
    os: {},
    runtime: {}
  };
  const result = await apiPost("/nodes", body);
  if (!result.ok) return writeError(result);
  return createdPayload(result, "node_id");
}

// POST /api/v1/nodes/{node_id}/token (ADMIN).  The plaintext token is returned
// exactly once; the control plane stores only its SHA-256 digest.  Callers must
// show it and never persist it in the browser.
export async function issueNodeToken(nodeId) {
  const id = String(nodeId || "").trim();
  if (!id) {
    return {
      ok: false,
      status: 0,
      error: { code: "MISSING_ID", message: "node id is required", retryable: false }
    };
  }
  const result = await apiPost(`/nodes/${encodeURIComponent(id)}/token`, {});
  if (!result.ok) return writeError(result);
  const data = result.payload && typeof result.payload === "object" ? result.payload.data : null;
  const token = data && typeof data.token === "string" ? data.token : "";
  if (!token) {
    return {
      ok: false,
      status: result.status,
      error: {
        code: "INVALID_PAYLOAD",
        message: "Token response has no data.token",
        retryable: false,
        status: result.status
      }
    };
  }
  return {
    ok: true,
    status: result.status,
    data: { node_id: data.node_id || id, token, issued: data.issued === true }
  };
}

// POST /api/v1/nodes/{node_id}/commands (ADMIN). The UI exposes exactly one
// tool, usb.scan, and always sends an empty args object; no caller can build an
// arbitrary tool payload through this module.
export async function queueUsbScan(nodeId) {
  const id = String(nodeId || "").trim();
  if (!id) {
    return {
      ok: false,
      status: 0,
      error: { code: "MISSING_ID", message: "node id is required", retryable: false }
    };
  }
  const result = await apiPost(`/nodes/${encodeURIComponent(id)}/commands`, {
    tool_id: "usb.scan",
    args: {}
  });
  if (!result.ok) return writeError(result);
  const data = result.payload && typeof result.payload === "object" ? result.payload.data : null;
  const commandId = data && typeof data.command_id === "string" ? data.command_id : "";
  if (!commandId) {
    return {
      ok: false,
      status: result.status,
      error: {
        code: "INVALID_PAYLOAD",
        message: "Command response has no data.command_id",
        retryable: false,
        status: result.status
      }
    };
  }
  return {
    ok: true,
    status: result.status,
    data: {
      command_id: commandId,
      status: String(data.status || "QUEUED").toUpperCase()
    }
  };
}

// GET /api/v1/nodes/{node_id}/commands/{command_id}. Status is one of
// QUEUED/SENT/RUNNING/SUCCEEDED/FAILED/TIMEOUT; output is only read, never
// synthesized. The caller owns the polling cadence.
export async function getUsbScanResult(nodeId, commandId, options = {}) {
  const id = String(nodeId || "").trim();
  const command = String(commandId || "").trim();
  if (!id || !command) {
    return {
      ok: false,
      status: 0,
      error: { code: "MISSING_ID", message: "node id and command id are required", retryable: false }
    };
  }
  const result = await apiGet(
    `/nodes/${encodeURIComponent(id)}/commands/${encodeURIComponent(command)}`,
    { timeout: options.timeout ?? 8000 }
  );
  if (!result.ok) return writeError(result);
  const data = result.payload && typeof result.payload === "object" ? result.payload.data : null;
  const status = data && typeof data.status === "string" ? data.status.toUpperCase() : "";
  if (!status) {
    return {
      ok: false,
      status: result.status,
      error: {
        code: "INVALID_PAYLOAD",
        message: "Command response has no data.status",
        retryable: false,
        status: result.status
      }
    };
  }
  return {
    ok: true,
    status: result.status,
    data: {
      status,
      exit_code: data.exit_code ?? null,
      stdout: typeof data.stdout === "string" ? data.stdout : "",
      stderr: typeof data.stderr === "string" ? data.stderr : "",
      truncated: data.truncated === true,
      error_code: data.error_code || null
    }
  };
}

export async function createDevice(input = {}) {
  const body = {
    display_id: String(input.display_id || "").trim(),
    node_id: input.node_id,
    firmware_version: String(input.firmware_version || "").trim() || "unknown",
    config_digest: String(input.config_digest || "").trim() || "unknown",
    adapter_version: String(input.adapter_version || "").trim() || "unknown",
    pool_state: input.pool_state || "DISCOVERED",
    health_state: input.health_state || "UNKNOWN",
    communication_state: input.communication_state || "OFFLINE",
    capabilities: Array.isArray(input.capabilities) ? input.capabilities : [],
    endpoints: Array.isArray(input.endpoints) ? input.endpoints : [],
    identity: input.identity && typeof input.identity === "object" ? input.identity : {},
    project_scope: Array.isArray(input.project_scope) ? input.project_scope : []
  };
  const result = await apiPost("/devices", body);
  if (!result.ok) return writeError(result);
  return createdPayload(result, "device_id");
}

// PATCH /api/v1/devices/{device_id}: inline edit of identity, endpoints,
// capabilities, firmware and the independent state axes. Only the supplied
// fields are sent.
export async function updateDevice(deviceId, patch = {}) {
  const id = String(deviceId || "").trim();
  if (!id) {
    return {
      ok: false,
      status: 0,
      error: { code: "MISSING_ID", message: "device id is required", retryable: false }
    };
  }
  const body = {};
  for (const key of ["display_id", "firmware_version", "config_digest", "adapter_version", "pool_state", "health_state", "communication_state"]) {
    const value = patch[key];
    if (value === undefined || value === null) continue;
    const textValue = String(value).trim();
    if (!textValue) continue;
    body[key] = textValue;
  }
  if (patch.identity && typeof patch.identity === "object" && !Array.isArray(patch.identity)) {
    body.identity = patch.identity;
  }
  for (const key of ["endpoints", "capabilities", "project_scope"]) {
    if (Array.isArray(patch[key])) body[key] = patch[key];
  }
  if (!Object.keys(body).length) {
    return {
      ok: false,
      status: 0,
      error: { code: "EMPTY_PATCH", message: "没有可提交的修改", retryable: false }
    };
  }
  const result = await apiPatch(`/devices/${encodeURIComponent(id)}`, body);
  if (!result.ok) return writeError(result);
  const data = result.payload && typeof result.payload === "object" ? result.payload.data : null;
  if (!data || data.updated !== true) {
    return {
      ok: false,
      status: result.status,
      error: {
        code: "INVALID_PAYLOAD",
        message: "Update response has no data.updated=true",
        retryable: false,
        status: result.status
      }
    };
  }
  return { ok: true, status: result.status, data };
}

async function deleteTopology(kind, backendId) {
  const id = String(backendId || "").trim();
  if (!id) {
    return {
      ok: false,
      status: 0,
      error: { code: "MISSING_ID", message: `${kind} id is required`, retryable: false }
    };
  }
  const result = await apiDelete(`/${kind === "node" ? "nodes" : "devices"}/${encodeURIComponent(id)}`);
  if (!result.ok) {
    if (result.status === 404) {
      return { ok: true, status: 404, alreadyGone: true, data: null };
    }
    return writeError(result);
  }
  const data = result.payload && typeof result.payload === "object" ? result.payload.data : null;
  if (!data || data.deleted !== true) {
    return {
      ok: false,
      status: result.status,
      error: {
        code: "INVALID_PAYLOAD",
        message: "Delete response has no data.deleted=true",
        retryable: false,
        status: result.status
      }
    };
  }
  return { ok: true, status: result.status, alreadyGone: false, data };
}

export function deleteNode(nodeId) {
  return deleteTopology("node", nodeId);
}

export function deleteDevice(deviceId) {
  return deleteTopology("device", deviceId);
}

// DV-01 needs the full node list plus the device projection: GET /nodes keeps
// nodes without devices discoverable, while GET /devices supplies the device
// rows nested under each node.
async function loadNodesView(params) {
  const nodesEndpoint = "/nodes";
  const [nodesResult, devicesResult] = await Promise.all([
    apiGet(nodesEndpoint),
    apiGet("/devices")
  ]);
  if (!nodesResult.ok) {
    return { mode: "api", endpoint: nodesEndpoint, error: { ...nodesResult.error, status: nodesResult.status } };
  }
  if (!devicesResult.ok) {
    return { mode: "api", endpoint: "/devices", error: { ...devicesResult.error, status: devicesResult.status } };
  }
  const nodesData = nodesResult.payload && typeof nodesResult.payload === "object" ? nodesResult.payload.data : {};
  const devicesPayload = devicesResult.payload && typeof devicesResult.payload === "object" ? devicesResult.payload : {};
  const devicesData = devicesPayload.data && typeof devicesPayload.data === "object" ? devicesPayload.data : {};
  const nodeItems = Array.isArray(nodesData.items) ? nodesData.items : [];
  return {
    mode: "api",
    endpoint: `${nodesEndpoint} + /devices`,
    payload: {
      ...devicesPayload,
      data: { ...devicesData, nodes: nodeItems }
    }
  };
}


// ---------------------------------------------------------------------------
// Test campaigns
// ---------------------------------------------------------------------------
//
// Campaigns are deterministic node tests, not Tasks.  The list endpoint already
// returns the full projection (summary, round rows, artifacts), so one loader
// feeds both the list and the detail view.  API mode never falls back to a
// fixture: a failed read returns the server error and the page keeps it visible.

function countValue(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? Math.trunc(parsed) : fallback;
}

function objectValue(value) {
  if (value && typeof value === "object" && !Array.isArray(value)) return value;
  if (typeof value === "string" && value.trim()) {
    try {
      const parsed = JSON.parse(value);
      return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : null;
    } catch {
      return null;
    }
  }
  return null;
}

function normalizeRoundRow(row, index) {
  const source = row && typeof row === "object" ? row : {};
  const rawEvidence = source.evidence ?? source.evidence_refs;
  const evidence = Array.isArray(rawEvidence)
    ? rawEvidence.filter((item) => item !== undefined && item !== null).map(String)
    : rawEvidence
      ? [String(rawEvidence)]
      : [];
  return {
    round: source.round ?? source.round_number ?? index + 1,
    status: String(source.status ?? source.final_status ?? source.business_verdict ?? source.result ?? "UNKNOWN"),
    wake: source.wake ?? source.keyword ?? null,
    command: source.command ?? source.intent ?? null,
    intent: source.intent ?? null,
    evidence,
    case_id: source.case_id ?? null,
    source: source.source || (source.derived ? "summary_final.json" : "results.csv"),
    derived: Boolean(source.derived)
  };
}

function normalizeArtifactFile(source) {
  const file = source && typeof source === "object" ? source : {};
  const name = file.name ? String(file.name) : "";
  if (!name) return null;
  return {
    artifact_id: file.artifact_id ? String(file.artifact_id) : null,
    name,
    size_bytes: countValue(file.size_bytes, 0),
    digest: file.digest ? String(file.digest) : null,
    media_type: file.media_type ? String(file.media_type) : "application/octet-stream",
    uploaded_at: file.uploaded_at ? String(file.uploaded_at) : null,
    download_url: file.download_url ? String(file.download_url) : null,
    downloadable: file.downloadable !== false
  };
}

export function normalizeCampaign(source = {}) {
  const raw = source && typeof source === "object" ? source : {};
  const summary = objectValue(raw.summary_json) || objectValue(raw.summary);
  const rows = Array.isArray(raw.round_rows)
    ? raw.round_rows
    : Array.isArray(raw.rounds_data)
      ? raw.rounds_data
      : [];
  const statusCounts = objectValue(raw.status_counts)
    || objectValue(summary && summary.status_counts)
    || {};
  const artifacts = objectValue(raw.artifacts) || {};
  const artifactFiles = Array.isArray(artifacts.files)
    ? artifacts.files.map(normalizeArtifactFile).filter(Boolean)
    : [];
  const rounds = countValue(raw.rounds ?? raw.expected_rounds, rows.length);
  const roundsCount = countValue(raw.rounds_count, rows.length);
  const completed = countValue(
    raw.completed_rounds ?? (summary && summary.completed_rounds),
    roundsCount
  );
  const total = countValue(
    raw.total_rounds ?? (summary && summary.target_rounds),
    rounds
  );
  const command = objectValue(raw.command) || null;
  const campaign = {
    id: String(raw.campaign_id ?? raw.id ?? ""),
    campaign_id: String(raw.campaign_id ?? raw.id ?? ""),
    node_id: raw.node_id ? String(raw.node_id) : null,
    // Legacy campaigns were created before the owning-Task link existed and
    // stay unassociated (null); only an exact task_id match attaches a
    // campaign to a task detail page.
    task_id: raw.task_id ? String(raw.task_id) : null,
    title: raw.title ? String(raw.title) : null,
    scenario: raw.scenario ? String(raw.scenario) : "—",
    bench: raw.bench ? String(raw.bench) : "—",
    command_set: raw.command_set ? String(raw.command_set) : null,
    rounds,
    expected_rounds: total || rounds,
    rounds_count: roundsCount,
    completed_rounds: completed,
    total_rounds: total || rounds,
    status: String(raw.status || "UNKNOWN").toUpperCase(),
    command_status: raw.command_status ? String(raw.command_status).toUpperCase() : (command && command.status ? String(command.status).toUpperCase() : null),
    command_id: raw.command_id ? String(raw.command_id) : (command && command.command_id ? String(command.command_id) : null),
    command: command
      ? {
          command_id: command.command_id ? String(command.command_id) : null,
          tool_id: command.tool_id ? String(command.tool_id) : null,
          status: command.status ? String(command.status).toUpperCase() : null,
          exit_code: command.exit_code ?? null,
          error_code: command.error_code ?? null,
          truncated: Boolean(command.truncated)
        }
      : null,
    verdict: raw.verdict ?? null,
    summary,
    summary_json: summary,
    status_counts: statusCounts,
    round_rows: rows
      .filter((row) => row && typeof row === "object")
      .map(normalizeRoundRow),
    artifacts,
    artifact_files: artifactFiles,
    artifact_count: countValue(artifacts.count, artifactFiles.length),
    artifact_total_bytes: countValue(
      artifacts.total_bytes,
      artifactFiles.reduce((total, file) => total + file.size_bytes, 0)
    ),
    artifact_entries: ["result_dir", "summary_path", "rounds_path"]
      .map((key) => [key, artifacts[key]])
      .filter(([, value]) => value !== undefined && value !== null && value !== ""),
    notes: Array.isArray(raw.notes) ? raw.notes.map(String) : [],
    error_code: raw.error_code ?? (command && command.error_code) ?? null,
    created_at: raw.created_at || null,
    started_at: raw.started_at || null,
    finished_at: raw.finished_at || null,
    demo: Boolean(raw.demo)
  };
  campaign.outcome = campaignOutcome(campaign);
  return campaign;
}

function campaignApiError(result, endpoint) {
  return {
    ok: false,
    mode: "api",
    endpoint,
    status: result.status,
    error: { ...(result.error || {}), status: result.status }
  };
}

export async function loadTestCampaigns(options = {}) {
  // The task detail page passes ``taskId``; the campaign tab passes nothing and
  // therefore keeps the all/unassociated view. The server-side filter is
  // requested through ``?task_id=`` and the client re-checks the exact id so a
  // backend that has not deployed the filter yet can never attach a legacy
  // ``task_id=null`` campaign to a task.
  const taskId = String(options.taskId ?? options.task_id ?? "").trim();
  if (!isApiMode()) {
    const fixture = fixtureView();
    const world = (fixture && fixture.world) || {};
    const campaigns = (Array.isArray(world.campaigns) ? world.campaigns : [])
      .map(normalizeCampaign)
      .filter((campaign) => campaign.id)
      .filter((campaign) => !taskId || campaign.task_id === taskId);
    return {
      ok: true,
      mode: "fixture",
      endpoint: taskId ? "fixture · demo campaigns · task filter" : "fixture · demo campaigns",
      campaigns,
      task_id: taskId || null
    };
  }
  const query = new URLSearchParams({ limit: "100" });
  if (taskId) query.set("task_id", taskId);
  const endpoint = `/test-campaigns?${query.toString()}`;
  const result = await apiGet(endpoint, { timeout: 10000 });
  if (!result.ok) return campaignApiError(result, "/test-campaigns");
  const data = result.payload && typeof result.payload === "object" ? result.payload.data : {};
  const items = data && Array.isArray(data.items) ? data.items : [];
  const campaigns = items
    .map(normalizeCampaign)
    .filter((campaign) => campaign.id)
    .filter((campaign) => !taskId || campaign.task_id === taskId);
  return {
    ok: true,
    mode: "api",
    endpoint,
    campaigns,
    task_id: taskId || null,
    total: countValue(data && data.total, campaigns.length)
  };
}

export async function loadTestCampaign(campaignId) {
  const id = String(campaignId || "").trim();
  if (!id) {
    return {
      ok: false,
      mode: isApiMode() ? "api" : "fixture",
      endpoint: null,
      status: 0,
      error: { code: "MISSING_CAMPAIGN_ID", message: "campaign id is required", retryable: false }
    };
  }
  if (!isApiMode()) {
    const fixture = fixtureView();
    const world = (fixture && fixture.world) || {};
    const campaign = (Array.isArray(world.campaigns) ? world.campaigns : [])
      .map(normalizeCampaign)
      .find((item) => item.id === id) || null;
    if (!campaign) {
      return {
        ok: false,
        mode: "fixture",
        endpoint: "fixture · demo campaigns",
        status: 404,
        error: { code: "CAMPAIGN_NOT_FOUND", message: `fixture campaign ${id} not found`, retryable: false }
      };
    }
    return { ok: true, mode: "fixture", endpoint: "fixture · demo campaigns", campaign };
  }
  const endpoint = `/test-campaigns/${encodeURIComponent(id)}`;
  const result = await apiGet(endpoint, { timeout: 10000 });
  if (!result.ok) return campaignApiError(result, endpoint);
  const data = result.payload && typeof result.payload === "object" ? result.payload.data : {};
  const campaign = normalizeCampaign(data || {});
  if (!campaign.id) {
    return {
      ok: false,
      mode: "api",
      endpoint,
      status: 0,
      error: { code: "INVALID_CAMPAIGN_PAYLOAD", message: "campaign response is missing campaign_id", retryable: false }
    };
  }
  return { ok: true, mode: "api", endpoint, campaign };
}

// Fetch one uploaded campaign artifact as bytes.  The download endpoint is
// admin-guarded, so a plain <a href> would lose the dev-header identity; the
// caller uses apiFetch with the same headers as every other API request.
export async function loadTestCampaignArtifact(campaignId, name) {
  const id = String(campaignId || "").trim();
  const artifact = String(name || "").trim();
  if (!id || !artifact) {
    return {
      ok: false,
      status: 0,
      error: { code: "MISSING_ARTIFACT", message: "campaign id and artifact name are required", retryable: false }
    };
  }
  const endpoint = `/test-campaigns/${encodeURIComponent(id)}/artifacts/${encodeURIComponent(artifact)}`;
  const result = await apiFetch(endpoint, { timeout: 60000, responseType: "blob" });
  if (!result.ok) {
    return {
      ok: false,
      status: result.status,
      endpoint,
      error: { ...(result.error || {}), status: result.status }
    };
  }
  return { ok: true, status: result.status, endpoint, blob: result.payload, name: artifact };
}

// POST /api/v1/test-campaigns. A campaign is enqueued as exactly one
// ``test.run`` NodeCommand; it never creates a Task or a supervisor session.
// ``task_id`` is optional and only sent when the caller already has a task.
// Fixture mode refuses the write instead of pretending a run was queued.
const CAMPAIGN_SCENARIOS = new Set(["wake-recognition"]);
const CAMPAIGN_BENCH_RE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.json$/;

export async function createTestCampaign(input = {}) {
  const nodeId = String(input.node_id ?? input.nodeId ?? "").trim();
  const taskId = String(input.task_id ?? input.taskId ?? "").trim();
  const scenario = String(input.scenario ?? "wake-recognition").trim();
  const bench = String(input.bench ?? "").trim();
  const rounds = Number(input.rounds);
  const fields = [];
  if (!nodeId) fields.push("node_id");
  if (!CAMPAIGN_SCENARIOS.has(scenario)) fields.push("scenario");
  if (!Number.isInteger(rounds) || rounds < 1 || rounds > 1000) fields.push("rounds");
  if (!CAMPAIGN_BENCH_RE.test(bench)) fields.push("bench");

  if (fields.length) {
    return {
      ok: false,
      mode: isApiMode() ? "api" : "fixture",
      endpoint: "/test-campaigns",
      status: 0,
      error: {
        code: "INVALID_CAMPAIGN_REQUEST",
        message: `Invalid campaign fields: ${fields.join(", ")}`,
        retryable: false,
        details: { fields }
      }
    };
  }

  if (!isApiMode()) {
    return {
      ok: false,
      mode: "fixture",
      endpoint: "/test-campaigns",
      status: 0,
      error: {
        code: "FIXTURE_MODE",
        message: "fixture 演示模式不会触发真实的测试活动；请切换到 API 数据源。",
        retryable: false
      }
    };
  }

  const body = { node_id: nodeId, scenario, rounds, bench };
  if (taskId) body.task_id = taskId;
  const result = await apiPost("/test-campaigns", body);
  if (!result.ok) {
    return {
      ok: false,
      mode: "api",
      endpoint: "/test-campaigns",
      status: result.status,
      error: { ...(result.error || {}), status: result.status }
    };
  }
  const data = result.payload && typeof result.payload === "object" ? result.payload.data : null;
  return {
    ok: true,
    mode: "api",
    endpoint: "/test-campaigns",
    status: result.status,
    campaign: data && (data.campaign_id || data.id) ? normalizeCampaign(data) : null,
    data
  };
}

// POST /api/v1/test-campaigns/{campaign_id}/stop. The control plane reports the
// campaign projection plus runner_active; callers wait for a terminal status
// before attempting the optional delete-after-stop.
export async function stopTestCampaign(campaignId) {
  const id = String(campaignId || "").trim();
  const endpoint = id ? `/test-campaigns/${encodeURIComponent(id)}/stop` : null;
  if (!endpoint) {
    return {
      ok: false,
      mode: "api",
      endpoint: null,
      status: 0,
      error: { code: "MISSING_CAMPAIGN_ID", message: "campaign id is required", retryable: false }
    };
  }
  const result = await apiPost(endpoint, {});
  if (!result.ok) {
    return {
      ok: false,
      mode: "api",
      endpoint,
      status: result.status,
      error: { ...(result.error || {}), status: result.status }
    };
  }
  const data = result.payload && typeof result.payload === "object" ? result.payload.data : null;
  return {
    ok: true,
    mode: "api",
    endpoint,
    status: result.status,
    campaign: data && (data.campaign_id || data.id) ? normalizeCampaign(data) : null,
    runner_active: Boolean(data && data.runner_active),
    data
  };
}

// DELETE /api/v1/test-campaigns/{campaign_id}. Terminal campaigns return 204;
// an active campaign keeps the server's 409 CAMPAIGN_ACTIVE code. A 404 means
// the row is already gone, which is the caller's success condition.
export async function deleteTestCampaign(campaignId) {
  const id = String(campaignId || "").trim();
  const endpoint = id ? `/test-campaigns/${encodeURIComponent(id)}` : null;
  if (!endpoint) {
    return {
      ok: false,
      mode: "api",
      endpoint: null,
      status: 0,
      error: { code: "MISSING_CAMPAIGN_ID", message: "campaign id is required", retryable: false }
    };
  }
  const result = await apiDelete(endpoint);
  if (!result.ok) {
    if (result.status === 404) {
      return { ok: true, mode: "api", endpoint, status: 404, alreadyGone: true, data: null };
    }
    return {
      ok: false,
      mode: "api",
      endpoint,
      status: result.status,
      error: { ...(result.error || {}), status: result.status }
    };
  }
  return {
    ok: true,
    mode: "api",
    endpoint,
    status: result.status,
    alreadyGone: false,
    data: result.payload && typeof result.payload === "object" ? result.payload.data ?? null : null
  };
}

export async function loadRouteView(routeId, params = {}) {
  if (!isApiMode()) {
    return { mode: "fixture", view: fixtureView() };
  }

  if (routeId === "DV-01") return loadNodesView(params);

  const endpoint = endpointForRoute(routeId, params);
  if (!endpoint) {
    return {
      mode: "api",
      endpoint: null,
      error: {
        code: "NO_ENDPOINT",
        message: `No read endpoint is mapped for route ${routeId}`,
        retryable: false,
        status: 0
      }
    };
  }

  const result = await apiGet(endpoint);
  if (!result.ok) {
    return {
      mode: "api",
      endpoint,
      error: { ...result.error, status: result.status }
    };
  }

  return { mode: "api", endpoint, payload: result.payload };
}

export function isLiveRoute(routeId) {
  return ["TK-08", "RN-02", "RN-03"].includes(routeId);
}
