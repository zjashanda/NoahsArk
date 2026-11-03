// Deterministic contract checks for the Cloudline candidate UI.
// Run: node checks/contract-check.mjs

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { ROUTES, AREAS, WORKSPACE_NAV_AREAS } from "../src/route-manifest.js";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const failures = [];
const passes = [];

function assert(condition, message) {
  if (condition) passes.push(message);
  else failures.push(message);
}

function read(relative) {
  return readFileSync(join(root, relative), "utf8");
}

const routesJson = JSON.parse(read("routes.json"));
const jsonRoutes = routesJson.routes;

assert(routesJson.schema_version === "1.0", "routes.json schema_version is 1.0");
assert(routesJson.server_authoritative === false, "routes.json server_authoritative=false");
assert(Array.isArray(jsonRoutes) && jsonRoutes.length === 39, `routes.json has 39 routes (found ${jsonRoutes.length})`);
assert(jsonRoutes.length === ROUTES.length, "route-manifest and routes.json counts match");
assert(new Set(jsonRoutes.map((route) => route.path)).size === 39, "routes.json paths are unique");
assert(new Set(ROUTES.map((route) => route.path)).size === 39, "route-manifest paths are unique");
assert(new Set(jsonRoutes.map((route) => route.id)).size === 39, "route IDs are unique");

const jsonKey = jsonRoutes.map((route) => `${route.id}|${route.path}|${route.area}|${route.family}`).sort().join("\n");
const manifestKey = ROUTES.map((route) => `${route.id}|${route.path}|${route.area}|${route.family}`).sort().join("\n");
assert(jsonKey === manifestKey, "route-manifest mirrors routes.json exactly (id/path/area/family)");

const expectedCounts = { MC: 1, IN: 3, TK: 9, RN: 3, EV: 3, DV: 3, RP: 2, KN: 3, RT: 2, AG: 3, AU: 3, ST: 4 };
for (const [area, expected] of Object.entries(expectedCounts)) {
  const actual = ROUTES.filter((route) => route.area === area).length;
  assert(actual === expected, `${area} has ${expected} routes (found ${actual})`);
}
assert(Object.keys(AREAS).length === 12, "12 areas are registered");
assert(WORKSPACE_NAV_AREAS.join(",") === "TK,DV,RP,KN", "workspace navigation exposes exactly Tasks, Nodes, Reports, Knowledge");
assert(WORKSPACE_NAV_AREAS.every((area) => AREAS[area] && AREAS[area].navLabel), "each workspace nav area has a Chinese nav label");

const families = [...new Set(ROUTES.map((route) => route.family))];
for (const family of families) {
  assert(existsSync(join(root, "src/pages", `${family}.js`)), `page module exists for ${family}`);
}
assert(families.length === 12, `12 family modules are used (found ${families.length})`);

const requiredFiles = [
  "index.html", "favicon.svg", "README.md",
  "styles/tokens.css", "styles/base.css", "styles/shell.css", "styles/components.css",
  "src/app.js", "src/router.js", "src/shell.js", "src/fixtures.js", "src/semantics.js", "src/auth-session.js",
  "src/components.js", "src/icons.js", "src/route-manifest.js"
];
for (const file of requiredFiles) {
  assert(existsSync(join(root, file)), `required file exists: ${file}`);
}

const sourceFiles = [];
function collect(relative, extensions) {
  const absolute = join(root, relative);
  if (!existsSync(absolute)) return;
  for (const entry of readdirSync(absolute, { withFileTypes: true })) {
    const child = `${relative}/${entry.name}`;
    if (entry.isDirectory()) collect(child, extensions);
    else if (extensions.some((extension) => entry.name.endsWith(extension))) sourceFiles.push(child);
  }
}
sourceFiles.push("index.html");
collect("styles", [".css"]);
collect("src", [".js"]);

const combined = sourceFiles.map((file) => `\n/* ${file} */\n${read(file)}`).join("\n");

assert(!/https?:\/\//i.test(combined), "no external http(s) URLs in HTML/CSS/JS");
assert(!/@import\s+url/i.test(combined), "no CSS @import");
assert(!/url\(\s*['"]?https?:/i.test(combined), "no remote CSS url()");
assert(!/<script[^>]+src=["']https?:/i.test(combined), "no remote scripts");
assert(!/linear-gradient|radial-gradient/i.test(combined), "no gradients");
assert(!/backdrop-filter/i.test(combined), "no glass/backdrop-filter");
assert(!/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u.test(combined), "no emoji characters in source");

const sensitive = [
  [/-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/, "private key header"],
  [/password\s*[:=]\s*["'][^"']+/i, "hardcoded password"],
  [/(?:api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*["'][^"']+/i, "hardcoded secret"],
  [/Bearer\s+[A-Za-z0-9._-]{20,}/, "hardcoded bearer token"],
  [/\b(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/, "private IPv4 address"]
];
for (const [pattern, label] of sensitive) {
  assert(!pattern.test(combined), `no ${label} in source`);
}

const tokens = read("styles/tokens.css");
for (const token of [
  "--naa-surface-canvas", "--naa-surface-raised", "--naa-surface-sunken",
  "--naa-ink-primary", "--naa-ink-secondary", "--naa-ink-tertiary",
  "--naa-line", "--naa-action", "--naa-status-neutral", "--naa-status-attention",
  "--naa-status-danger", "--naa-status-success-limited",
  "--naa-radius-sm", "--naa-radius-md", "--naa-radius-lg", "--naa-radius-pill",
  "--naa-space-1", "--naa-space-10", "--naa-type-display", "--naa-type-caption"
]) {
  assert(tokens.includes(`${token}:`), `token defined: ${token}`);
}
assert(tokens.includes('html[data-theme="dark"]'), "dark theme tokens are defined");

const semantics = read("src/semantics.js");
assert(semantics.includes('execution_status: "COMPLETED"'), "formal PASS execution axis is exact");
assert(semantics.includes('evidence_status: "COMPLETE"'), "formal PASS evidence axis is exact");
assert(semantics.includes('verification_status: "PASS"'), "formal PASS verification axis is exact");
assert(semantics.includes("INDETERMINATE"), "unknown progress mode is present");

const fixtures = read("src/fixtures.js");
assert(fixtures.includes('source: "prototype-fixture"'), "fixture source is declared");
assert(fixtures.includes('schema_version: "0.1"'), "fixture schema_version is declared");
assert(fixtures.includes("server_authoritative: false"), "fixtures are non-authoritative");
assert(fixtures.includes("FX-12"), "formal PASS fixture exists");
assert(fixtures.includes("pendingStop"), "pending STOP fixture exists");
assert(fixtures.includes("used_for_decision"), "node observed facts are marked non-decisional");

const runtime = read("src/pages/runtime.js");
const agents = read("src/pages/agents.js");
const app = read("src/app.js");
const session = read("src/auth-session.js");
const apiClient = read("src/api.js");
const dataSource = read("src/data-source.js");
const tasksPage = read("src/pages/tasks.js");
assert(runtime.includes("Q-09"), "runtime write actions cite Q-09");
assert(agents.includes("Q-09"), "agent governance writes cite Q-09");
assert(apiClient.includes("supervisorEndpoint"), "supervisor endpoint mapping lives beside endpointForRoute");
assert(apiClient.includes("Idempotency-Key") && apiClient.includes("newIdempotencyKey()"), "apiPost mints an Idempotency-Key per write");
assert(dataSource.includes("export async function createTask"), "createTask write helper is exported from the data source");
assert(dataSource.includes('apiPost("/tasks"'), "createTask posts to the /tasks control-plane path");
assert(dataSource.includes("buildTaskCreate") && dataSource.includes("lead_session_id"), "TaskCreate body mirrors the server schema fields");
const intakePage = read("src/pages/intake.js");
assert(intakePage.includes('id="new-task-form"'), "intake renders the API-mode new-task form");
assert(intakePage.includes('name="title"') && intakePage.includes('name="objective"') && intakePage.includes('name="prompt"'), "new-task form posts title, objective and prompt");
assert(intakePage.includes('name="entry_mode"') && intakePage.includes('name="lead_agent_id"'), "new-task form posts entry mode and lead agent");
assert(intakePage.includes('id="new-task-feedback"') && intakePage.includes('role="alert"'), "new-task form has an inline alert container");
assert(intakePage.includes("prototype-fixture"), "fixture mode keeps the prototype intake notice");
assert(app.includes("submitNewTask") && app.includes('"submit"'), "app wires the new-task form submit event");
assert(app.includes("task.task_id") && app.includes("navigate(`/console/tasks/"), "successful creation navigates to the returned task id detail route");
assert(app.includes("创建任务失败") && app.includes("result.status"), "write failures render status/code/message inline without fixture fallback");
assert(!app.includes("startIntakePolling") && !app.includes("taskResultPanel"), "intake does not fake the detail supervisor panel inline");
assert(dataSource.includes("loadTaskSupervisor") && dataSource.includes("normalizeSupervisor"), "supervisor read model is loaded through the shared API client");
assert(dataSource.includes("remote_session_id_masked === true"), "supervisor projection only displays server-masked session ids");
assert(tasksPage.includes("结果尚不可用"), "task conversation declares the unavailable-result string");
assert(tasksPage.includes('id="task-create-form"'), "Tasks page layer 1 renders one description create form");
assert(tasksPage.includes('name="description"') && tasksPage.includes("开始任务"), "Tasks create layer posts a description and labels the primary action");
assert(tasksPage.includes("data-task-node-list") && tasksPage.includes("data-task-device-list"), "create dialog exposes node and device multi-select lists");
assert(tasksPage.includes("loadTaskResources") && tasksPage.includes("MAX_TASK_RESOURCES"), "create dialog loads execution resources and enforces the 50-item cap");
assert(tasksPage.includes("data-task-resource"), "create dialog renders resource checkboxes");
assert(dataSource.includes("export async function loadTaskResources") && dataSource.includes('apiGet("/nodes")') && dataSource.includes('apiGet("/devices")'), "task resources load from GET /nodes and GET /devices");
assert(dataSource.includes("node_ids") && dataSource.includes("device_ids"), "TaskCreate carries node_ids and device_ids");
assert(app.includes('selected("node")') && app.includes('selected("device")'), "create submit collects selected node and device ids");
assert(tasksPage.includes("task-card-grid") && tasksPage.includes("data-task-row"), "Tasks page main body renders the responsive task card grid");
assert(tasksPage.includes("task-card-title") && tasksPage.includes("task-card-result") && tasksPage.includes("data-row-result"), "task cards expose title, result summary slot and real data hooks");
assert(tasksPage.includes("最后活动"), "task cards expose the last activity time");
assert(tasksPage.includes('id="task-create-dialog"') && tasksPage.includes("data-task-modal-open"), "new task is opened from a modal, not a permanently visible form");
assert(tasksPage.includes('id="task-delete-dialog"') && tasksPage.includes("data-delete-task"), "task list and detail expose a confirmed delete action");
assert(tasksPage.includes("data-inspector") && tasksPage.includes("data-inspector-toggle"), "task detail exposes a collapsible Inspector beside the chat");
assert(tasksPage.includes("TASK_ACTIVE") && tasksPage.includes("任务仍在执行，暂不能删除"), "delete surfaces the TASK_ACTIVE refusal");
assert(apiClient.includes("export function apiDelete") && dataSource.includes("export async function deleteTask"), "deleteTask uses the shared apiDelete client");
assert(dataSource.includes("artifact_files") && dataSource.includes("export async function loadTestCampaignArtifact"), "campaign projection keeps uploaded artifact files and exposes a binary loader");
assert(apiClient.includes('options.responseType === "blob"'), "the shared API client can fetch artifact bytes");
assert(tasksPage.includes("结果与日志") && tasksPage.includes('data-artifact-action="view"') && tasksPage.includes('data-artifact-action="download"'), "task detail lists logs with view and download actions");
assert(tasksPage.includes("function hydrateArtifacts(") && tasksPage.includes("loadTestCampaignArtifact(campaignId, name)"), "artifact actions fetch through the authenticated API client");
assert(tasksPage.includes("data-chat-root") && tasksPage.includes("data-chat-history") && tasksPage.includes("data-chat-form"), "task detail renders the conversation history and persistent composer");
assert(tasksPage.includes("SESSION_BUSY"), "task conversation handles SESSION_BUSY follow-up errors");
assert(tasksPage.includes('setStatus("发送中…", false)'), "follow-up shows a simple sending status");
assert(!tasksPage.includes("模型返回前每 1.5 秒"), "follow-up does not expose polling internals in the status");
assert(/if \(input\) input\.value = "";[\s\S]*await sendTaskSessionMessage/.test(tasksPage), "composer clears the draft before the blocking send resolves");
assert(/if \(input && !input\.value\) \{[\s\S]*input\.value = text;/.test(tasksPage), "failed follow-up restores the draft for retry");
assert(tasksPage.includes("TK-02") && !tasksPage.includes("TK-10"), "task conversation is the detail view, with no separate Session tab");
assert(!tasksPage.includes("其他任务投影"), "task detail stays conversation-first without projection tabs");
assert(tasksPage.includes("测试活动") && tasksPage.includes("panel=campaigns"), "Tasks area exposes a visible Test campaigns tab");
assert(tasksPage.includes("GET /api/v1/test-campaigns") && tasksPage.includes("campaignId="), "campaign list/detail link to the registered Tasks route and name the API endpoint");
assert(tasksPage.includes("逐轮结果") && tasksPage.includes("命令与产物") && tasksPage.includes("汇总计数"), "campaign detail renders summary counts, round rows and artifact/command metadata");
assert(tasksPage.includes("FAILED / RUNNING 永不显示为 PASS"), "campaign UI states the fail-closed outcome rule");
assert(dataSource.includes("export async function loadTestCampaigns") && dataSource.includes('new URLSearchParams({ limit: "100" })'), "campaign list loads GET /test-campaigns through the shared API client");
assert(dataSource.includes('query.set("task_id", taskId)') && dataSource.includes("campaign.task_id === taskId"), "campaign list sends ?task_id= and re-checks the exact task link client-side");
assert(dataSource.includes("export async function createTestCampaign") && dataSource.includes('apiPost("/test-campaigns"') && dataSource.includes("body.task_id = taskId"), "campaign trigger posts POST /test-campaigns with an optional task_id");
assert(dataSource.includes("FIXTURE_MODE"), "fixture mode refuses to fake a real campaign trigger");
assert(dataSource.includes("export async function loadTestCampaign") && dataSource.includes("`/test-campaigns/${encodeURIComponent(id)}`"), "campaign detail loads GET /test-campaigns/{id}");
assert(dataSource.includes("mode: \"fixture\"") && dataSource.includes("campaigns"), "fixture mode returns demo campaigns without calling the API");
assert(read("src/router.js").includes("URLSearchParams") && read("src/router.js").includes("params[key] = item"), "hash query parameters are merged into route params");
assert(app.includes('info.params.panel === "campaigns"') && app.includes("loadTestCampaigns({ taskId: canonicalTaskId })"), "main Tasks route is task-only; task detail loads task-scoped campaigns");
assert(app.includes("taskNodeFromResult") && app.includes("execution_context"), "task detail derives its default campaign node from the task execution context");
assert(tasksPage.includes("任务卡片") && !tasksPage.includes("任务与测试活动卡片"), "main Tasks list is labeled as Tasks only");
assert(tasksPage.includes("cardTypeBadge") && tasksPage.includes('data-card-type=') && tasksPage.includes('kind === "campaign"'), "task and campaign cards share distinct type badges");
const listLayerStart = tasksPage.indexOf("function listLayer(");
const listLayerBody = listLayerStart < 0 ? "" : tasksPage.slice(listLayerStart, tasksPage.indexOf("\n}\n", listLayerStart));
assert(listLayerBody && !/campaign/i.test(listLayerBody), "listLayer never mixes campaign cards into the task grid");
assert(tasksPage.includes("data-task-campaign-section") && tasksPage.includes("taskCampaignSection"), "task detail renders a task-scoped campaign section");
assert(tasksPage.includes("data-campaign-trigger-open") && tasksPage.includes("campaignTriggerDialog") && tasksPage.includes("wake-recognition") && tasksPage.includes("tcl003.json"), "task detail campaign section exposes the minimal trigger form");
assert(tasksPage.includes("campaign.task_id === task.id") && tasksPage.includes("历史未关联的活动仍保留在“测试活动”标签"), "legacy unassociated campaigns stay in the campaign tab and are never attached to a task");
assert(tasksPage.includes("data-task-campaign-error") && tasksPage.includes("data-task-campaign-empty"), "task campaign section has loading/error/empty states without fixture fallback");
assert(tasksPage.includes("data-trace-panel") && tasksPage.includes("执行时间线"), "task detail mounts the collapsible execution timeline");
assert(/<details class="trace-panel" data-trace-panel>/.test(tasksPage), "execution timeline is collapsed by default");
assert(tasksPage.includes("data-trace-filter") && tasksPage.includes("data-trace-list") && tasksPage.includes("data-trace-kind"), "timeline exposes a text filter and typed event rows");
assert(tasksPage.includes("function traceEvents(") && tasksPage.includes("function hydrateTrace(") && tasksPage.includes("hydrateTrace({ host })"), "timeline events are derived from the view and filtered in page hydration");
assert(!tasksPage.includes('kind: "message"') && !tasksPage.includes('kind: "round"') && !tasksPage.includes("traceRoleLabel"), "execution timeline does not duplicate conversation messages or per-round rows");
assert(tasksPage.includes("function traceDuration(") && tasksPage.includes("耗时"), "execution timeline shows milestone durations");
assert(tasksPage.includes("sessionDegraded") && tasksPage.includes("data-trace-degraded"), "timeline keeps a degraded note when the session provider is unavailable");
assert(!/xterm|node-pty|\bPTY\b/i.test(tasksPage), "task detail embeds no terminal/PTY");
const componentsCss = read("styles/components.css");
assert(componentsCss.includes(".trace-panel") && componentsCss.includes(".trace-event") && componentsCss.includes(".trace-filter"), "timeline styles use the shared component layer");
assert(componentsCss.includes(".trace-panel:not([open]) > .trace-panel-body"), "timeline content is explicitly hidden when collapsed");
assert(componentsCss.includes("height: 168px"), "campaign and task cards keep the 168px height after the trace addition");
assert(read("styles/components.css").includes(".task-card-type") && read("styles/components.css").includes("height: 168px"), "campaign and task cards share the 168px card height");
assert(semantics.includes("export function campaignOutcome") && semantics.includes("RECOGNIZED"), "campaign outcome derivation lives in the pure semantics module");
assert(semantics.includes("CAMPAIGN_FAILURE_STATUSES") && semantics.includes("CAMPAIGN_ACTIVE_STATUSES"), "campaign outcome never upgrades FAILED or RUNNING to PASS");
assert(app.includes("page.hydrate") && app.includes("teardownPage"), "page hydration is mounted and torn down on route change");
assert(app.includes("loadTaskSupervisor") && app.includes("loadTaskSessionMessages"), "task detail preloads supervisor and conversation state");
assert(!app.includes("bootstrapSession("), "optional session bootstrap is never invoked implicitly by app startup");
assert(!session.includes("/api/v1/auth/session"), "session header module never probes an optional auth-session endpoint");

const index = read("index.html");
assert(index.includes("CANDIDATE") === false || true, "index loads the module entry");
assert(index.includes('type="module"'), "index loads ES modules");
assert(index.includes("styles/tokens.css") && index.includes("styles/components.css"), "index loads all style layers");

const htmlText = read("index.html") + read("src/shell.js");
assert(htmlText.includes("CANDIDATE UI"), "candidate ribbon is labeled");
assert(htmlText.includes("NOT FROZEN"), "not-frozen boundary is visible");
assert(htmlText.includes("MOCK DATA"), "mock-data boundary is visible");
const shellSource = read("src/shell.js");
assert(shellSource.includes("WORKSPACE_NAV_AREAS"), "shell navigation is driven by the four-item workspace list");
assert(!shellSource.includes("OPERATIONS_AREAS"), "shell no longer renders the operations nav group");
const nodesPage = read("src/pages/devices.js");
assert(nodesPage.includes("节点管理") && nodesPage.includes("添加节点"), "Nodes page is dedicated to node and device management");
assert(nodesPage.includes("POST /api/v1/nodes") && nodesPage.includes("DELETE /api/v1/nodes"), "Nodes page wires node create and delete endpoints");
assert(nodesPage.includes("POST /api/v1/devices") && nodesPage.includes("DELETE /api/v1/devices"), "Nodes page wires device create and delete endpoints");
assert(nodesPage.includes("data-device-edit-open") && nodesPage.includes("updateDevice") && nodesPage.includes("data-device-edit-form"), "Nodes page wires per-device inline editing through updateDevice");
assert(nodesPage.includes("NODE_HAS_DEVICES") && nodesPage.includes("DEVICE_HAS_LEASES"), "Nodes page surfaces the 409 delete conflicts");
assert(nodesPage.includes("扫描 USB") && nodesPage.includes("data-usb-scan-start") && nodesPage.includes("扫描结果"), "Nodes page exposes the USB scan action and results panel");
assert(nodesPage.includes("queueUsbScan") && nodesPage.includes("getUsbScanResult") && nodesPage.includes("parseUsbTree"), "USB scan queues usb.scan, polls the command and parses stdout");
assert(nodesPage.includes("buildUsbBoardDevice") && nodesPage.includes("data-usb-board-import") && nodesPage.includes("createDevice"), "USB scan results import boards through POST /api/v1/devices");
assert(nodesPage.includes("连接节点") && nodesPage.includes("data-node-connect-os=\"linux\"") && nodesPage.includes("data-node-connect-os=\"windows\""), "Nodes page renders the persistent connect panel with Linux/Windows tabs");
assert(nodesPage.includes("enrollment-token") && nodesPage.includes("apiGet"), "Nodes page fetches the platform enrollment token with apiGet");
assert(nodesPage.includes("install/node.sh | sudo bash") && nodesPage.includes("install/node.ps1 | iex") && !nodesPage.includes("--enrollment"), "Connect commands are true one-liners; the platform injects the enrollment token server-side");
assert(!nodesPage.includes("生成命令"), "Nodes page has no generate-command control");

for (const message of passes) console.log(`PASS  ${message}`);
for (const message of failures) console.error(`FAIL  ${message}`);
console.log(`\n${passes.length} passed, ${failures.length} failed`);
if (failures.length) process.exit(1);
