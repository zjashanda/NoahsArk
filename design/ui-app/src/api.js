// API client for the candidate UI. Fixture mode remains the default.
// The real control-plane API is opt-in via ?api=1 or localStorage.naa-api=1.

import { currentRole } from "./roles.js";

const MODE_KEY = "naa-api";

// The candidate UI is served by checks/serve.mjs, which proxies /api/v1 to the
// control plane on 127.0.0.1:8000. Same-origin keeps browser CORS out of the
// picture while ?apiBase= and window.NAA_API_BASE remain explicit overrides.
export function getApiBase() {
  if (typeof window === "undefined") return ["http:", "//", "127.0.0.1:8000"].join("");
  const params = new URLSearchParams(window.location.search);
  return params.get("apiBase")
    || window.NAA_API_BASE
    || window.location.origin;
}

export function isApiMode() {
  if (typeof window === "undefined") return false;
  const params = new URLSearchParams(window.location.search);
  if (params.get("api") === "1") return true;
  if (params.get("api") === "0") return false;
  return window.localStorage.getItem(MODE_KEY) === "1";
}

export function setApiMode(enabled) {
  if (typeof window !== "undefined" && window.localStorage) {
    window.localStorage.setItem(MODE_KEY, enabled ? "1" : "0");
  }
}

function newIdempotencyKey() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `idem-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export async function apiFetch(path, options = {}) {
  const base = getApiBase().replace(/\/+$/, "");
  const url = `${base}/api/v1${path}`;
  const role = currentRole();
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), options.timeout ?? 4000);
  try {
    const response = await fetch(url, {
      method: options.method || "GET",
      headers: {
        Accept: "application/json",
        "X-NoahsArk-Role": role.id,
        "X-NoahsArk-Actor": `demo-${role.id.toLowerCase()}`,
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.idempotencyKey ? { "Idempotency-Key": options.idempotencyKey } : {}),
        ...(options.headers || {})
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: controller.signal
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        error: (payload && payload.error) || {
          code: "HTTP_ERROR",
          message: `HTTP ${response.status}`,
          retryable: response.status >= 500
        }
      };
    }
    return { ok: true, status: response.status, payload };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      error: {
        code: error && error.name === "AbortError" ? "API_TIMEOUT" : "API_UNREACHABLE",
        message: error && error.name === "AbortError"
          ? "API request timed out"
          : "API is unreachable",
        retryable: true
      }
    };
  } finally {
    window.clearTimeout(timer);
  }
}

export function apiGet(path, options = {}) {
  return apiFetch(path, { ...options, method: "GET" });
}

export function apiPost(path, body, options = {}) {
  return apiFetch(path, {
    ...options,
    method: "POST",
    body,
    idempotencyKey: options.idempotencyKey || newIdempotencyKey()
  });
}

// Route ID -> read endpoint. Kept in one place so W4 can wire pages incrementally.
export function endpointForRoute(routeId, params = {}) {
  const task = params.taskId || "tsk-voice-001";
  const run = params.runId || "run-042";
  const attempt = params.attemptId || "att-112";
  const map = {
    "MC-01": "/mission",
    "IN-01": "/intake/drafts",
    "IN-02": "/intake/drafts",
    "IN-03": `/intake/drafts/${params.draftId || "drf-009"}`,
    "TK-01": "/tasks",
    "TK-02": `/tasks/${task}/overview`,
    "TK-03": `/tasks/${task}/revisions`,
    "TK-04": `/tasks/${task}/plan`,
    "TK-05": `/tasks/${task}/runs`,
    "TK-06": `/tasks/${task}/evidence`,
    "TK-07": `/tasks/${task}/verdict`,
    "TK-08": `/tasks/${task}/live`,
    "TK-09": `/tasks/${task}/knowledge`,
    "RN-01": "/runs",
    "RN-02": `/runs/${run}`,
    "RN-03": `/runs/${run}/attempts/${attempt}`,
    "EV-01": "/evidence",
    "EV-02": `/evidence/${params.evidenceId || "ev-voice-trace-01"}`,
    "EV-03": "/verdicts",
    "DV-01": "/devices",
    "DV-02": `/devices/${params.deviceId || "dev-tcl-001"}`,
    "DV-03": `/nodes/${params.nodeId || "node-lab-win-01"}`,
    "RP-01": "/reports",
    "RP-02": `/reports/${params.reportId || "rpt-voice-001"}`,
    "KN-01": "/knowledge",
    "KN-02": `/knowledge/${params.knowledgeId || "kn-wake-false-trigger"}`,
    "KN-03": "/knowledge/candidates",
    "RT-01": "/runtime/models",
    "RT-02": "/runtime/toolchain",
    "AG-01": "/agents",
    "AG-02": `/agents/${params.agentId || "agt-planner"}`,
    "AG-03": "/reviews",
    "AU-01": "/audit",
    "AU-02": `/audit/${params.eventId || "aud-20261029-041"}`,
    "AU-03": "/recovery",
    "ST-01": "/settings",
    "ST-02": "/settings/access",
    "ST-03": "/settings/notifications",
    "ST-04": "/settings/retention"
  };
  return map[routeId] || null;
}
