// Runtime smoke checks without a browser: routing, module imports, fixtures.
// Run: node checks/smoke-check.mjs

import { ROUTES, WORKSPACE_NAV_AREAS } from "../src/route-manifest.js";
import { currentRoute, matchRoute, normalizePath } from "../src/router.js";
import {
  SCENARIOS,
  axesFor,
  view
} from "../src/fixtures.js";
import {
  AXIS_ORDER,
  FORMAL_PASS,
  campaignOutcome,
  isFormalPass,
  progressModel,
  releaseModel,
  verdictLabel,
  offlineCombination
} from "../src/semantics.js";
import { can, currentRole, roleById } from "../src/roles.js";
import { endpointForRoute, supervisorEndpoint } from "../src/api.js";
import {
  buildTaskCreate,
  createTask,
  createTestCampaign,
  DEFAULT_LEAD_AGENT_ID,
  deleteTask,
  loadTaskResources,
  loadTestCampaigns,
  MAX_TASK_RESOURCES,
  normalizeCampaign,
  normalizeResourceIds,
  demoSessionMessages,
  demoSupervisor,
  normalizeSessionMessages,
  normalizeSupervisor,
  projectSessionMessage,
  sendTaskSessionMessage,
  titleFromDescription
} from "../src/data-source.js";
import { adaptRouteView } from "../src/api-adapter.js";
import { buildUsbBoardDevice, parseUsbTree } from "../src/usb-tree.js";
import { LANGS, translateString } from "../src/i18n.js";

import * as mission from "../src/pages/mission.js";
import * as intake from "../src/pages/intake.js";
import * as tasks from "../src/pages/tasks.js";
import * as runs from "../src/pages/runs.js";
import * as evidence from "../src/pages/evidence.js";
import * as devices from "../src/pages/devices.js";
import * as reports from "../src/pages/reports.js";
import * as knowledge from "../src/pages/knowledge.js";
import * as runtime from "../src/pages/runtime.js";
import * as agents from "../src/pages/agents.js";
import * as audit from "../src/pages/audit.js";
import * as settings from "../src/pages/settings.js";

const PAGES = { mission, intake, tasks, runs, evidence, devices, reports, knowledge, runtime, agents, audit, settings };
const SAMPLE = {
  taskId: "tsk-voice-001",
  draftId: "drf-009",
  runId: "run-042",
  attemptId: "att-112",
  evidenceId: "ev-voice-trace-01",
  deviceId: "dev-tcl-001",
  nodeId: "node-lab-win-01",
  reportId: "rpt-voice-001",
  knowledgeId: "kn-wake-false-trigger",
  agentId: "agt-planner",
  eventId: "aud-20261029-041"
};

const failures = [];
let passed = 0;
function check(condition, message) {
  if (condition) {
    passed += 1;
  } else {
    failures.push(message);
  }
}

function concrete(path) {
  return path.replace(/:([A-Za-z]+)/g, (_, key) => SAMPLE[key] || "sample");
}

check(normalizePath("#/console") === "/console", "normalizePath strips hash");
check(normalizePath("#/aitest/tasks") === "/console/tasks", "legacy /aitest alias normalizes");
check(matchRoute("/console/intake/new").route.id === "IN-02", "literal route wins over :draftId");
check(matchRoute("/console/knowledge/candidates").route.id === "KN-03", "literal route wins over :knowledgeId");

for (const route of ROUTES) {
  const path = concrete(route.path);
  const matched = matchRoute(path);
  check(matched && matched.route.id === route.id, `route match ${route.id} (${path})`);
}

for (const route of ROUTES) {
  const params = {};
  for (const match of route.path.matchAll(/:([A-Za-z]+)/g)) params[match[1]] = SAMPLE[match[1]];
  check(Boolean(endpointForRoute(route.id, params)), `API endpoint exists for ${route.id}`);
}

check(currentRole().id === "OBSERVER", "serverless role default fails closed to OBSERVER");
check(!can("STOP"), "observer cannot request STOP");
check(!can("CREATE_TASK"), "observer cannot create a task");
check(roleById("NOT_A_ROLE").id === "OBSERVER", "unknown role fails closed to OBSERVER");

const liveRoute = ROUTES.find((route) => route.id === "TK-08");
const apiLive = adaptRouteView(liveRoute, { taskId: SAMPLE.taskId }, {
  data: {
    axes: { execution_status: "RUNNING", validity_status: "NOT_EVALUATED", business_verdict: "NOT_RUN", evidence_status: "UNVERIFIED", verification_status: "NOT_RUN" },
    events: [{ event_type: "NODE_HEARTBEAT", occurred_at: "2026-10-30T14:06:19Z", message: "Node reported heartbeat", status: "received" }]
  },
  meta: { correlation_id: "smoke-live" }
}, view("FX-01"));
check(apiLive.meta.server_authoritative === true, "API view is marked server authoritative");
check(apiLive.axes.validity_status === "NOT_EVALUATED", "API adapter preserves NOT_EVALUATED");
check(apiLive.axes.business_verdict === "NOT_RUN", "API adapter preserves NOT_RUN");
check(apiLive.liveEvents.length === 1 && apiLive.liveEvents[0].state === "done", "API live events are projected as read-only timeline facts");
check(LANGS.map((language) => language.id).join(",") === "zh,en", "Chinese and English presentation choices are registered");
check(translateString("五轴状态") === "五轴状态", "Chinese remains the serverless default language");

for (const route of ROUTES) {
  const page = PAGES[route.family];
  check(page && typeof page.render === "function", `page module exports render for ${route.family}`);
  const params = {};
  for (const match of route.path.matchAll(/:([A-Za-z]+)/g)) params[match[1]] = SAMPLE[match[1]];
  let html = "";
  try {
    html = page.render({ route, params, view: view("FX-01") });
  } catch (error) {
    failures.push(`render crashed for ${route.id}: ${error.message}`);
    continue;
  }
  check(typeof html === "string" && html.length > 200, `render produces markup for ${route.id} (${html.length} chars)`);
  check(!html.includes("undefined"), `render has no undefined text for ${route.id}`);
  check(html.includes('class="page-head"') || html.includes("state-block"), `render has a page header or state for ${route.id}`);
}

check(SCENARIOS.length === 14, "14 scenario fixtures are defined");
for (const scenario of SCENARIOS) {
  const axes = axesFor(scenario.id);
  check(AXIS_ORDER.every((key) => typeof axes[key] === "string"), `five axes complete for ${scenario.id}`);
  check(isFormalPass(axes) === (scenario.id === "FX-12"), `formal PASS only for FX-12 (${scenario.id})`);
}

check(isFormalPass(FORMAL_PASS), "exact tuple is a formal PASS");
check(!isFormalPass({ ...FORMAL_PASS, evidence_status: "INCOMPLETE" }), "incomplete evidence is not formal PASS");
check(!isFormalPass({ ...FORMAL_PASS, execution_status: "RUNNING" }), "running execution is not formal PASS");

const normal = view("FX-01");
check(progressModel(normal.progress).percent === 45, "FX-01 shows 18/40 = 45%");
const unknown = view("FX-06");
check(progressModel(unknown.progress).percent === null, "FX-06 never shows a percent");
check(progressModel(unknown.progress).label === "未知", "FX-06 progress is labeled unknown");
const full = view("FX-12");
check(progressModel(full.progress).percent === 100, "FX-12 shows 40/40 = 100%");

check(releaseModel(normal.release).state === "HELD", "FX-01 release is held");
check(releaseModel(full.release).state === "RELEASED", "FX-12 release preconditions are complete");
check(verdictLabel(normal.axes) === "未形成正式判定", "FX-01 is running and not a formal verdict");
check(verdictLabel(view("FX-07").axes) === "不可正式 PASS", "FX-07 business PASS with incomplete evidence is not formal PASS");
check(verdictLabel(full.axes) === "正式 PASS", "FX-12 is formal PASS");
check(offlineCombination({ communication_state: "OFFLINE", execution_status: "RUNNING", occupancy_state: "OCCUPIED", execution_permit: "GRANTED" }), "offline combination is detectable");
check(offlineCombination(view("FX-04").link), "FX-04 keeps offline+running+occupied+granted");

check(view("FX-10").axes.evidence_status === "UNKNOWN", "FX-10 fails closed to UNKNOWN");

const verdictHtml = tasks.render({
  route: ROUTES.find((item) => item.id === "TK-07"),
  params: { taskId: "tsk-voice-001" },
  view: view("FX-12")
});
check(verdictHtml.includes("正式 PASS"), "FX-12 verdict page renders formal PASS");
check(!verdictHtml.includes("不可正式 PASS"), "FX-12 verdict page has no fail-closed verdict label");

const evidenceHtml = evidence.render({
  route: ROUTES.find((item) => item.id === "EV-01"),
  params: {},
  view: view("FX-07")
});
check(evidenceHtml.includes("received") && evidenceHtml.includes("verified"), "evidence page separates received and verified");
check(evidenceHtml.includes("不等于"), "evidence page states received is not verified");

const offlineHtml = runs.render({
  route: ROUTES.find((item) => item.id === "RN-02"),
  params: { runId: "run-042" },
  view: view("FX-04")
});
check(offlineHtml.includes("OFFLINE") && offlineHtml.includes("RUNNING"), "offline run renders OFFLINE and RUNNING together");
check(offlineHtml.includes("OCCUPIED") && offlineHtml.includes("GRANTED"), "offline run keeps occupancy and permit visible");

// Supervisor read model: endpoint mapping, server-masked ids, and UI states.
const SUPERVISOR_TASK = "060ee2c3-1f38-42f2-9531-e0008d71303f";
check(
  supervisorEndpoint(SUPERVISOR_TASK) === `/tasks/${SUPERVISOR_TASK}/supervisor`,
  "supervisor endpoint maps a task id through the shared API client"
);
check(supervisorEndpoint("") === null, "supervisor endpoint refuses an empty task id");

const SUPERVISOR_PAYLOAD = {
  task_id: SUPERVISOR_TASK,
  task_display_id: "tsk-060ee2c3",
  supervisor_session_id: "sup-session",
  supervisor_display_id: "sup-060ee2c3",
  state: "COMPLETED",
  state_is_terminal: true,
  remote_session_id: "ses_***T10y",
  remote_session_id_masked: true,
  prompt: { digest: "sha256:abc123", bytes: 49 },
  result: { available: true, summary: "PONG", error_code: null, updated_at: "2026-10-30T07:20:42Z" },
  created_at: "2026-10-30T07:10:00Z",
  updated_at: "2026-10-30T07:20:42Z"
};
const supervisor = normalizeSupervisor(SUPERVISOR_PAYLOAD, supervisorEndpoint(SUPERVISOR_TASK));
check(supervisor.status === "ready" && supervisor.state === "COMPLETED", "supervisor projection keeps the server state");
check(supervisor.result_summary === "PONG", "supervisor projection exposes result.summary");
check(supervisor.prompt_bytes === 49 && supervisor.prompt_digest === "sha256:abc123", "supervisor projection keeps prompt digest and bytes");
check(supervisor.remote_session_id === "ses_***T10y", "supervisor projection shows the server-masked remote session id");
const unmasked = normalizeSupervisor({
  ...SUPERVISOR_PAYLOAD,
  remote_session_id: "ses_plain_session",
  remote_session_id_masked: false
});
check(unmasked.remote_session_id === "—", "unmasked remote session ids are never displayed");
check(!JSON.stringify(unmasked).includes("ses_plain_session"), "raw remote session ids never leave the projection");

const tk01 = ROUTES.find((route) => route.id === "TK-01");
const fixtureTasks = tasks.render({ route: tk01, params: {}, view: view("FX-01") });
check(fixtureTasks.includes('id="task-create-form"'), "Tasks layer 1 renders the single-description create form");
check(fixtureTasks.includes('name="description"') && fixtureTasks.includes("开始任务"), "Tasks create layer posts one description with a primary start action");
check(fixtureTasks.includes("task-card-grid"), "Tasks main body renders the task card grid");
check(fixtureTasks.includes("task-card-title") && fixtureTasks.includes("最后活动"), "task cards expose title and last activity");
check(fixtureTasks.includes("data-row-result"), "task cards reserve a result summary slot");
check(fixtureTasks.includes('id="task-create-dialog"') && fixtureTasks.includes("data-task-modal-open"), "Tasks page opens creation from a modal");
check(fixtureTasks.includes("data-task-node-list") && fixtureTasks.includes("data-task-device-list"), "create dialog renders node and device multi-select sections");
check(fixtureTasks.includes("节点") && fixtureTasks.includes("设备") && fixtureTasks.includes("最多 50 个"), "create dialog labels resource sections and the 50-item cap");
check(!fixtureTasks.includes("1 · 创建任务"), "Tasks page no longer renders a permanently visible create form");
check(fixtureTasks.includes('id="task-delete-dialog"') && fixtureTasks.includes("data-delete-task"), "Tasks page has a confirmed delete dialog and row actions");
check(fixtureTasks.includes("FIXTURE · DEMO") || fixtureTasks.includes("fixture 演示卡片"), "fixture Tasks page is clearly labeled as a demo");
check(fixtureTasks.includes("data-task-row") && fixtureTasks.includes("DEMO"), "fixture card is a labeled demo card");
check(fixtureTasks.includes("测试活动") && fixtureTasks.includes("panel=campaigns"), "Tasks page exposes the Test campaigns tab");
check(fixtureTasks.includes("data-task-row") && !fixtureTasks.includes("data-campaign-row"), "main Tasks list renders Tasks only");
check(fixtureTasks.includes('data-card-type="task"') && !fixtureTasks.includes('data-card-type="campaign"'), "main Tasks list never labels a campaign card");
const mainListWithCampaigns = tasks.render({
  route: tk01,
  params: {},
  view: { ...view("FX-01"), campaigns: view("FX-01").world.campaigns, campaignError: { code: "API_UNREACHABLE", message: "API is unreachable", status: 0 } }
});
check(mainListWithCampaigns.includes("data-task-row") && !mainListWithCampaigns.includes("data-campaign-row"), "campaigns present in view state never leak into the main task grid");
check(!mainListWithCampaigns.includes("测试活动读取失败"), "main task list has no campaign read error note");

// Test campaigns: fixture mode is demo-only, API payloads normalize without
// inventing PASS, and FAILED/RUNNING can never be upgraded.
const campaignFixture = await loadTestCampaigns();
check(campaignFixture.ok && campaignFixture.mode === "fixture", "campaign fixture mode loads without the API");
check(campaignFixture.campaigns.length === 3, "fixture exposes the three demo campaigns");
const scopedFixture = await loadTestCampaigns({ taskId: "tsk-voice-001" });
check(scopedFixture.ok && scopedFixture.campaigns.length === 0, "task-scoped fixture read never attaches unlinked demo campaigns");
check(scopedFixture.task_id === "tsk-voice-001" && scopedFixture.endpoint.includes("task filter"), "task-scoped fixture read records the requested task id");
const linkedCampaign = normalizeCampaign({ campaign_id: "linked-1", task_id: "tsk-voice-001", node_id: "node-1", status: "QUEUED" });
const legacyCampaign = normalizeCampaign({ campaign_id: "legacy-1", status: "QUEUED" });
check(linkedCampaign.task_id === "tsk-voice-001" && legacyCampaign.task_id === null, "campaign normalization preserves task_id and keeps legacy rows null");
const fixtureTrigger = await createTestCampaign({ node_id: "node-lab-win-01", task_id: "tsk-voice-001", scenario: "wake-recognition", rounds: 5, bench: "tcl003.json" });
check(!fixtureTrigger.ok && fixtureTrigger.error.code === "FIXTURE_MODE", "fixture mode refuses to fake a campaign trigger");
const invalidTrigger = await createTestCampaign({ node_id: "", task_id: "tsk-voice-001", scenario: "no-such-scenario", rounds: 3, bench: "not-a-json" });
check(!invalidTrigger.ok && invalidTrigger.error.code === "INVALID_CAMPAIGN_REQUEST" && invalidTrigger.error.details.fields.includes("node_id"), "campaign trigger validates node/scenario/rounds/bench before writing");
const fixturePass = campaignFixture.campaigns.find((item) => item.id === "demo-campaign-pass");
const fixtureRunning = campaignFixture.campaigns.find((item) => item.id === "demo-campaign-running");
const fixtureFailed = campaignFixture.campaigns.find((item) => item.id === "demo-campaign-failed");
check(fixturePass.outcome.verdict === "PASS" && fixturePass.rounds_count === 5 && fixturePass.rounds === 5, "fixture completed campaign shows 5/5 PASS");
check(fixtureRunning.outcome.verdict === null && fixtureRunning.outcome.label !== "PASS" && fixtureRunning.rounds === 489, "fixture RUNNING 489 never shows PASS");
check(fixtureFailed.outcome.verdict === "FAIL" && fixtureFailed.error_code === "SUMMARY_TOO_LARGE", "fixture FAILED campaign keeps FAIL and its error code");

const apiPass = normalizeCampaign({
  campaign_id: "api-pass-5",
  status: "SUCCEEDED",
  command_status: "SUCCEEDED",
  rounds: 5,
  rounds_count: 5,
  summary: { outcome: "COMPLETED", completed_rounds: 5, target_rounds: 5, status_counts: { RECOGNIZED: 5 } },
  round_rows: [1, 2, 3, 4, 5].map((round) => ({ round, status: "RECOGNIZED", derived: true, source: "summary_final.json" }))
});
check(apiPass.outcome.verdict === "PASS" && apiPass.round_rows.length === 5, "SUCCEEDED 5/5 with RECOGNIZED summary derives PASS");
const apiRunning = normalizeCampaign({ campaign_id: "api-running-489", status: "RUNNING", command_status: "SENT", rounds: 489, rounds_count: 0 });
check(apiRunning.outcome.verdict === null && apiRunning.outcome.label === "进行中", "RUNNING 489 stays in progress without a verdict");
const apiFailed = normalizeCampaign({ campaign_id: "api-failed-489", status: "FAILED", command_status: "FAILED", rounds: 489, rounds_count: 0, error_code: "SUMMARY_TOO_LARGE" });
check(apiFailed.outcome.verdict === "FAIL" && apiFailed.error_code === "SUMMARY_TOO_LARGE", "FAILED 489 stays FAIL");
const apiSucceededNoSummary = normalizeCampaign({ campaign_id: "api-succeeded-no-summary", status: "SUCCEEDED", rounds: 5, rounds_count: 0 });
check(apiSucceededNoSummary.outcome.verdict === null, "SUCCEEDED without a complete summary never derives PASS");
check(campaignOutcome({ status: "FAILED", verdict: "PASS" }).verdict === "FAIL", "explicit verdict cannot turn FAILED into PASS");
check(campaignOutcome({ status: "RUNNING", summary: { status_counts: { RECOGNIZED: 5 } }, rounds: 5, rounds_count: 5 }).verdict === null, "summary counts cannot turn RUNNING into PASS");

const campaignRoute = ROUTES.find((route) => route.id === "TK-01");
const fixtureCampaignList = tasks.render({ route: campaignRoute, params: { panel: "campaigns" }, view: view("FX-01") });
check(fixtureCampaignList.includes("GET /api/v1/test-campaigns"), "campaign list names GET /api/v1/test-campaigns");
check(fixtureCampaignList.includes("demo-campaign-pass") && fixtureCampaignList.includes("demo-campaign-failed"), "campaign list renders fixture campaigns");
check(fixtureCampaignList.includes("5 / 5") && fixtureCampaignList.includes("PASS"), "campaign list shows 5/5 PASS for the completed campaign");
check(fixtureCampaignList.includes("0 / 489") && fixtureCampaignList.includes("进行中"), "campaign list shows RUNNING 489 progress without PASS");
check(fixtureCampaignList.includes("FAIL") && fixtureCampaignList.includes("FIXTURE · DEMO"), "campaign list keeps FAIL and labels fixture data as demo");
check(!fixtureCampaignList.includes("data-task-row"), "campaign tab does not double-render the task list");
const fixtureCampaignDetail = tasks.render({ route: campaignRoute, params: { panel: "campaigns", campaignId: "demo-campaign-pass" }, view: view("FX-01") });
check(fixtureCampaignDetail.includes("RECOGNIZED") && fixtureCampaignDetail.includes("summary.status_counts"), "campaign detail renders summary counts");
check(fixtureCampaignDetail.includes("逐轮结果") && fixtureCampaignDetail.includes("summary_final.json"), "campaign detail renders round rows and evidence");
check(fixtureCampaignDetail.includes("命令与产物") && fixtureCampaignDetail.includes("result_dir"), "campaign detail renders command and artifact metadata");
const fixtureCampaignFailed = tasks.render({ route: campaignRoute, params: { panel: "campaigns", campaignId: "demo-campaign-failed" }, view: view("FX-01") });
check(fixtureCampaignFailed.includes("FAIL") && fixtureCampaignFailed.includes("SUMMARY_TOO_LARGE"), "failed campaign detail keeps FAIL and error code");
const fixtureCampaignRunning = tasks.render({ route: campaignRoute, params: { panel: "campaigns", campaignId: "demo-campaign-running" }, view: view("FX-01") });
check(fixtureCampaignRunning.includes("0 / 489") && !fixtureCampaignRunning.includes(">PASS<"), "running campaign detail shows 0/489 and no PASS badge");
const emptyCampaigns = tasks.render({ route: campaignRoute, params: { panel: "campaigns" }, view: { ...view("FX-01"), campaigns: [] } });
check(emptyCampaigns.includes("暂无测试活动"), "campaign list renders an empty state");
const failedCampaigns = tasks.render({ route: campaignRoute, params: { panel: "campaigns" }, view: { ...view("FX-01"), campaigns: [], campaignError: { code: "API_UNREACHABLE", message: "API is unreachable", status: 0 } } });
check(failedCampaigns.includes("测试活动读取失败") && failedCampaigns.includes("API_UNREACHABLE"), "campaign list renders the API error state without fixture fallback");

// The campaign tab/detail use hash query parameters on the registered TK-01
// route, so the route manifest keeps its 39 entries.
const previousWindow = globalThis.window;
globalThis.window = { location: { hash: "#/console/tasks?panel=campaigns&campaignId=demo-campaign-pass" } };
const campaignRouteInfo = currentRoute();
check(campaignRouteInfo.route && campaignRouteInfo.route.id === "TK-01", "campaign query still resolves the registered TK-01 route");
check(campaignRouteInfo.params.panel === "campaigns" && campaignRouteInfo.params.campaignId === "demo-campaign-pass", "campaign query parameters reach the page");
if (previousWindow === undefined) delete globalThis.window;
else globalThis.window = previousWindow;
check(normalizePath("/console/tasks?panel=campaigns") === "/console/tasks", "campaign query does not change the registered path");

const { navMarkup } = await import("../src/shell.js");
const navHtml = navMarkup("TK", {});
check(WORKSPACE_NAV_AREAS.join(",") === "TK,DV,RP,KN", "workspace nav has exactly four areas");
for (const area of WORKSPACE_NAV_AREAS) {
  check(navHtml.includes(`data-area="${area}"`), `workspace nav renders ${area}`);
}
for (const area of ["MC", "IN", "RN", "EV", "RT", "AG", "AU", "ST"]) {
  check(!navHtml.includes(`data-area="${area}"`), `workspace nav hides ${area}`);
}
check(navHtml.includes("任务") && navHtml.includes("节点管理") && navHtml.includes("报告") && navHtml.includes("知识库"), "workspace nav uses the four Chinese labels");
check(!navHtml.includes("Operations"), "workspace nav has no operations group");

const dv01 = ROUTES.find((route) => route.id === "DV-01");
const fixtureNodes = devices.render({ route: dv01, params: {}, view: view("FX-01") });
check(fixtureNodes.includes("节点管理") && fixtureNodes.includes("添加节点"), "Nodes page manages node creation and devices");
check(fixtureNodes.includes("data-node-add-open") && fixtureNodes.includes("node-create-dialog"), "Nodes page exposes the add-node entry and dialog");
check(fixtureNodes.includes("POST /api/v1/nodes") && fixtureNodes.includes("POST /api/v1/devices"), "Nodes page submits real node and device creation");
check(fixtureNodes.includes("node-device-row") && fixtureNodes.includes("node-device-display"), "Nodes page nests devices under each node");
check(fixtureNodes.includes("NODE_HAS_DEVICES") && fixtureNodes.includes("DEVICE_HAS_LEASES"), "Nodes page surfaces delete conflicts");
check(fixtureNodes.includes("data-device-add-open") && fixtureNodes.includes("data-device-delete"), "Nodes page exposes add-device and delete actions");
check(fixtureNodes.includes("node-card-main") && fixtureNodes.includes("node-card-meta") && fixtureNodes.includes("data-node-manage-open"), "Nodes page renders compact cards with a device-management action");
check(fixtureNodes.includes("data-node-manage-dialog") && fixtureNodes.includes("data-device-add-open") && fixtureNodes.includes("data-device-edit-open") && fixtureNodes.includes("data-device-edit-form"), "Device management lives in a node dialog with add and inline edit forms");
check(fixtureNodes.includes("data-device-serial-group") && fixtureNodes.includes("data-device-audio-group"), "Add-device dialog exposes serial roles and audio channels");
check(fixtureNodes.includes("disabled aria-disabled=\"true\""), "fixture mode keeps topology writes disabled");
check(fixtureNodes.includes("扫描 USB") && fixtureNodes.includes("data-usb-scan-start") && fixtureNodes.includes("扫描结果"), "Nodes dialog exposes the USB scan action and result container");
check(fixtureNodes.includes("data-usb-board-detail-dialog") && fixtureNodes.includes("板卡详情"), "Nodes dialog mounts a board detail dialog");
check(typeof devices.hydrate === "function", "Nodes page exports the add-node dialog hydration");

// The live WIN009 usbTree output is the parser contract: boards, serial roles,
// audio endpoints and VID/PID all come from the tree, never from fixtures.
const USB_TREE_SAMPLE = [
  "物理 USB 板卡（2 个）",
  "  ListenAI 板卡",
  "    ListenAI VCOM  (1 个串口)",
  "      COM6",
  "    音频端点  (2 个)",
  "      Capture  8ch  VID_8765&PID_5678:8_2A847557_0_0000  麦克风 (ListenAI Audio)",
  "      Render   2ch  VID_8765&PID_5678:8_2A847557_0_0000  扬声器 (ListenAI Audio)",
  "  USB 板卡",
  "    CH344 Quad_Serial  (4 个串口)",
  "      A  COM3",
  "      B  COM7",
  "      C  COM4",
  "      D  COM5",
  "",
  "声卡列表（2 个端点）",
  "Direction  State    DeviceKey                            Ch  FriendlyName             Board",
  "Capture    Active   VID_8765&PID_5678:8_2A847557_0_0000  8   麦克风 (ListenAI Audio)  ListenAI 板卡",
  "Render     Active   VID_8765&PID_5678:8_2A847557_0_0000  2   扬声器 (ListenAI Audio)  ListenAI 板卡"
].join("\n");
const usbBoards = parseUsbTree(USB_TREE_SAMPLE);
check(usbBoards.length === 2, "USB tree parser finds both live boards");
check(usbBoards[0].label === "ListenAI 板卡" && usbBoards[0].functions[0].ports[0].com === "COM6", "USB tree parser reads the bare COM6 serial");
check(usbBoards[0].audio.length === 2 && usbBoards[0].audio[0].direction === "capture" && usbBoards[0].audio[0].channels === 8, "USB tree parser reads both audio endpoints");
check(usbBoards[1].functions[0].ports.map((port) => `${port.role}:${port.com}`).join(",") === "A:COM3,B:COM7,C:COM4,D:COM5", "USB tree parser reads the CH344 role ports");
const usbDevice = buildUsbBoardDevice({ ...usbBoards[0], display_id: "usb-listenai" }, "node-win009");
check(usbDevice.identity.kind === "usb-board" && usbDevice.identity.vid === "8765" && usbDevice.identity.pid === "5678" && !("serial" in usbDevice.identity), "USB board identity carries only non-empty VID/PID");
check(usbDevice.capabilities.join(",") === "serial,audio", "USB board capabilities are serial,audio");
check(usbDevice.endpoints.some((endpoint) => endpoint.kind === "serial" && endpoint.port === "COM6") && usbDevice.endpoints.filter((endpoint) => endpoint.kind === "audio").length === 2, "USB board endpoints carry serial and both audio directions");
check(parseUsbTree("").length === 0, "USB tree parser returns no boards for empty output instead of inventing one");

const apiNodesView = {
  ...view("FX-01"),
  meta: { ...view("FX-01").meta, server_authoritative: true }
};
const apiNodes = devices.render({ route: dv01, params: {}, view: apiNodesView });
check(apiNodes.includes("连接节点") && apiNodes.includes("data-node-install-os=\"linux\"") && apiNodes.includes("data-node-install-os=\"windows\""), "API Nodes page renders the connect dialog with two OS tabs");
check(apiNodes.includes("node-connect-linux") && apiNodes.includes("node-connect-windows"), "Connect dialog ships both OS command slots");
check(apiNodes.includes("install/node.sh | sudo bash") && apiNodes.includes("install/node.ps1 | iex") && !apiNodes.includes("生成命令"), "Connect dialog uses one-line enrollment commands with no generate control");
check(!fixtureNodes.includes("data-node-connect"), "Fixture Nodes page keeps the connect panel hidden");
const connectOrigin = "http://10.11.63.42:8200";
const connectCommands = devices.buildNodeConnectCommands("tok-test", connectOrigin);
check(connectCommands.linux === `curl -fsSL ${connectOrigin}/install/node.sh | sudo bash`, "Linux connect command is a one-liner");
check(connectCommands.windows === `irm ${connectOrigin}/install/node.ps1 | iex`, "Windows connect command is a one-liner");

const apiTasksView = {
  ...view("FX-01"),
  meta: { ...view("FX-01").meta, server_authoritative: true },
  world: {
    ...view("FX-01").world,
    taskRows: [
      { id: SUPERVISOR_TASK, display_id: "tsk-060ee2c3", title: "PONG smoke task", updated_at: "2026-10-30T07:20:42Z" }
    ]
  }
};
const apiTasks = tasks.render({ route: tk01, params: {}, view: apiTasksView });
check(apiTasks.includes('data-task-id="' + SUPERVISOR_TASK + '"'), "API Tasks list renders the real task id");
check(apiTasks.includes("PONG smoke task") && apiTasks.includes("tsk-060ee2c3"), "API Tasks list renders title and display_id");
check(apiTasks.includes("data-row-supervisor") && apiTasks.includes("读取中"), "API Tasks list reserves a supervisor state slot");
check(apiTasks.includes("GET /api/v1/tasks"), "API Tasks list states its real endpoint");

const tk02 = ROUTES.find((route) => route.id === "TK-02");
function renderSupervisor(supervisorState, options = {}) {
  const base = view("FX-01");
  return tasks.render({
    route: tk02,
    params: { taskId: SUPERVISOR_TASK },
    view: {
      ...base,
      meta: { ...base.meta, server_authoritative: options.apiMode !== false },
      supervisor: supervisorState,
      session: options.session || null
    }
  });
}

const readyHtml = renderSupervisor(supervisor, { session: normalizeSessionMessages({
  task_id: SUPERVISOR_TASK,
  state: "COMPLETED",
  state_is_terminal: true,
  messages: [
    { message_id: "m1", role: "user", created_at: "2026-10-30T07:20:10Z", parts: [{ type: "text", text: "Reply with the single word PONG and nothing else." }] },
    { message_id: "m2", role: "assistant", created_at: "2026-10-30T07:20:42Z", parts: [{ type: "text", text: "PONG" }] }
  ]
})});
check(readyHtml.includes("data-chat-root") && readyHtml.includes("data-chat-history"), "task detail mounts the conversation history");
check(readyHtml.includes('class="badge tone-success">COMPLETED'), "COMPLETED supervisor state uses the success tone");
check(readyHtml.includes("PONG"), "task conversation renders result.summary and the assistant reply");
check(readyHtml.includes("Reply with the single word PONG and nothing else."), "task conversation renders the user prompt");
check(readyHtml.includes("data-chat-form") && readyHtml.includes("data-chat-input"), "task conversation has a persistent composer");
check(readyHtml.includes("data-chat-run-status") && readyHtml.includes("chat-run-dots"), "task conversation mounts an in-thread running indicator");
check(readyHtml.includes('id="run-details-dialog"') && readyHtml.includes("data-run-tab") && readyHtml.includes("运行详情"), "task conversation mounts the run-details dialog with tabs");
check(readyHtml.includes('id="task-result"') && !readyHtml.includes("run-summary-raw"), "run details show the acceptance summary directly in the fixed pane");
check(readyHtml.includes("data-inspector") && readyHtml.includes("data-inspector-toggle"), "task detail mounts the collapsible Inspector");
check(readyHtml.includes("Supervisor ID") && readyHtml.includes("消息数") && readyHtml.includes("模型"), "Inspector exposes supervisor id, message count and model");
check(readyHtml.includes("data-delete-task"), "task detail header exposes delete");
check(readyHtml.includes('id="task-delete-dialog"'), "task detail mounts the delete confirmation dialog");
check(readyHtml.includes("refresh-chat"), "task conversation exposes a single refresh action");
check(readyHtml.includes("不构成任务判定"), "supervisor state is labeled as lifecycle-only, not a task verdict");
check(!readyHtml.includes("TK-10"), "task detail has no separate Session tab");
check(readyHtml.includes("data-task-campaign-section") && readyHtml.includes("data-campaign-trigger-open"), "task detail always mounts the campaign section and trigger button");

const taskCampaignBase = {
  ...view("FX-01"),
  meta: { ...view("FX-01").meta, server_authoritative: true },
  supervisor: { status: "absent", task_id: "tsk-voice-001" },
  taskNode: { id: "9c8677b2-3bcc-42ce-9428-cdfa4b98eae4", display_id: "win009" },
  taskCampaignEndpoint: "GET /api/v1/test-campaigns?task_id=tsk-voice-001"
};
const taskCampaignHtml = tasks.render({
  route: tk02,
  params: { taskId: "tsk-voice-001" },
  view: { ...taskCampaignBase, taskCampaigns: [linkedCampaign], taskCampaignError: null }
});
check(taskCampaignHtml.includes("data-task-campaign-section") && taskCampaignHtml.includes("data-campaign-row"), "task detail renders campaigns that carry this exact task_id");
check(taskCampaignHtml.includes("linked-1") && taskCampaignHtml.includes("data-campaign-trigger-open"), "task detail shows the linked campaign card and trigger action");
check(taskCampaignHtml.includes('data-default-node-id="9c8677b2-3bcc-42ce-9428-cdfa4b98eae4"') && taskCampaignHtml.includes('data-default-node-display="win009"'), "trigger form defaults to the task execution node");
check(taskCampaignHtml.includes('value="wake-recognition"') && taskCampaignHtml.includes('value="5"') && taskCampaignHtml.includes('value="489"') && taskCampaignHtml.includes('value="tcl003.json"'), "trigger form exposes scenario, 5/489 rounds and benchmark defaults");
const legacyTaskCampaignHtml = tasks.render({
  route: tk02,
  params: { taskId: "tsk-voice-001" },
  view: { ...taskCampaignBase, taskCampaigns: [legacyCampaign], taskCampaignError: null }
});
check(!legacyTaskCampaignHtml.includes("data-campaign-row") && legacyTaskCampaignHtml.includes("历史未关联的活动仍保留在“测试活动”标签"), "legacy task_id=null campaigns are never falsely attached to a task");
const taskCampaignErrorHtml = tasks.render({
  route: tk02,
  params: { taskId: "tsk-voice-001" },
  view: { ...taskCampaignBase, taskCampaigns: [], taskCampaignError: { code: "API_UNREACHABLE", message: "API is unreachable", status: 0, endpoint: "/test-campaigns?task_id=tsk-voice-001" } }
});
check(taskCampaignErrorHtml.includes("data-task-campaign-error") && taskCampaignErrorHtml.includes("API_UNREACHABLE") && taskCampaignErrorHtml.includes("data-campaign-trigger-open"), "task campaign failure stays visible while the trigger action remains reachable");

// Read-only Trace panel: every row derives from task/supervisor/session/campaign projections.
const traceCampaign = normalizeCampaign({
  campaign_id: "e7f0f35b-65a9-48f9-89ed-d7d73d490310",
  task_id: "tsk-voice-001",
  node_id: "node-1",
  scenario: "wake-recognition",
  rounds: 5,
  rounds_count: 5,
  status: "SUCCEEDED",
  command_status: "SUCCEEDED",
  command_id: "cmd-1",
  command: { command_id: "cmd-1", tool_id: "test.run", status: "SUCCEEDED", exit_code: 0 },
  summary: { completed_rounds: 5, target_rounds: 5, status_counts: { RECOGNIZED: 5 } },
  round_rows: [1, 2, 3, 4, 5].map((round) => ({ round, status: "RECOGNIZED", command: "打开空调", source: "results.csv" })),
  artifacts: {
    files: [
      {
        artifact_id: "art-1",
        name: "summary_final.json",
        size_bytes: 1203,
        digest: "sha256:abc",
        media_type: "application/json",
        uploaded_at: "2026-11-02T10:13:03Z",
        download_url: "/api/v1/test-campaigns/e7f0f35b-65a9-48f9-89ed-d7d73d490310/artifacts/summary_final.json",
        downloadable: true
      },
      {
        artifact_id: "art-2",
        name: "COM3_csk_ap.log",
        size_bytes: 109290,
        digest: "sha256:def",
        media_type: "text/plain",
        uploaded_at: "2026-11-02T10:13:04Z",
        download_url: "/api/v1/test-campaigns/e7f0f35b-65a9-48f9-89ed-d7d73d490310/artifacts/COM3_csk_ap.log",
        downloadable: true
      }
    ],
    count: 2,
    total_bytes: 110493,
    all_downloadable: true,
    summary_path: "C:\\result\\summary_final.json"
  },
  created_at: "2026-11-02T10:10:54.587742Z",
  started_at: "2026-11-02T10:10:54.587742Z",
  finished_at: "2026-11-02T10:13:02.061416Z"
});
const traceView = {
  ...taskCampaignBase,
  supervisor: normalizeSupervisor({
    ...SUPERVISOR_PAYLOAD,
    state: "COMPLETED",
    created_at: "2026-11-02T10:10:00Z",
    updated_at: "2026-11-02T10:13:48.374187Z",
    result: { available: true, summary: "执行完成。结果：5/5 RECOGNIZED", updated_at: "2026-11-02T10:13:48.374187Z" }
  }),
  session: {
    status: "error",
    endpoint: "/tasks/tsk-voice-001/session/messages",
    task_id: "tsk-voice-001",
    messages: [],
    error: { code: "PROVIDER_UNAVAILABLE", message: "OpenCode provider is not configured", status: 502 }
  },
  taskCampaigns: [traceCampaign],
  taskCampaignError: null
};
const traceHtml = tasks.render({ route: tk02, params: { taskId: "tsk-voice-001" }, view: traceView });
check(traceHtml.includes("data-trace-panel") && traceHtml.includes("执行时间线"), "task detail mounts the collapsible execution timeline");
check(/<details class="trace-panel" data-trace-panel>/.test(traceHtml), "execution timeline is collapsed by default");
check(traceHtml.includes('data-trace-filter') && traceHtml.includes("data-trace-list"), "timeline exposes text filtering and a chronological list");
check((traceHtml.match(/data-trace-kind="round"/g) || []).length === 0, "timeline does not repeat per-round rows from the campaign table");
check(!traceHtml.includes("第 3 轮 · RECOGNIZED"), "timeline omits detailed round entries");
check(traceHtml.includes("绑定 · COMPLETED") && traceHtml.includes("开始执行") && traceHtml.includes("执行结束 · SUCCEEDED"), "timeline keeps supervisor, campaign start and campaign finish milestones");
check(traceHtml.includes("耗时 02:07") && traceHtml.includes("Supervisor 耗时 03:48"), "timeline shows campaign and supervisor durations");
check(traceHtml.includes("产物 · 2 项"), "timeline consolidates uploaded artifacts into one milestone");
check(traceHtml.includes("结果与日志") && traceHtml.includes("summary_final.json") && traceHtml.includes("COM3_csk_ap.log"), "task detail lists uploaded logs and artifacts");
check(traceHtml.includes('data-artifact-action="view"') && traceHtml.includes('data-artifact-action="download"'), "task artifacts expose view and download actions");
check(traceHtml.includes('data-artifact-campaign="e7f0f35b-65a9-48f9-89ed-d7d73d490310"') && traceHtml.includes("wake-recognition"), "artifact files are grouped under their campaign name");
check(!traceHtml.includes('data-trace-kind="message"'), "timeline does not duplicate conversation messages");
check(traceHtml.includes("data-trace-degraded") && traceHtml.includes("PROVIDER_UNAVAILABLE") && traceHtml.includes("HTTP 502"), "timeline shows a degraded note for a 502 session and keeps the campaign events");
check(traceHtml.includes("5/5") && traceHtml.includes("5 / 5"), "timeline surfaces the 5/5 campaign outcome and round count");
const traceStart = traceHtml.indexOf("data-trace-panel");
const traceEnd = traceHtml.indexOf("data-task-campaign-section");
const traceFragment = traceStart < 0 || traceEnd < 0 ? "" : traceHtml.slice(traceStart, traceEnd);
check(traceFragment && !/data-chat-form|data-chat-input|data-chat-send|textarea|xterm|node-pty/i.test(traceFragment), "timeline contains no composer, textarea or terminal");
check(traceHtml.includes("data-chat-form") && traceHtml.includes("data-chat-input"), "result and conversation composer stay outside the timeline");


const failedHtml = renderSupervisor(normalizeSupervisor({
  ...SUPERVISOR_PAYLOAD,
  state: "FAILED",
  result: { available: false, summary: null, error_code: "SUPERVISOR_FAILED", updated_at: "2026-10-30T07:20:42Z" }
}));
check(failedHtml.includes('class="badge tone-danger">FAILED'), "FAILED supervisor state uses the danger tone");
check(failedHtml.includes("结果尚不可用"), "unavailable supervisor result is stated explicitly");
check(failedHtml.includes("SUPERVISOR_FAILED"), "supervisor result.error_code is rendered when present");

const runningHtml = renderSupervisor(normalizeSupervisor({ ...SUPERVISOR_PAYLOAD, state: "RUNNING", result: { available: false } }));
check(runningHtml.includes('class="badge tone-action">RUNNING'), "RUNNING supervisor state uses the info/action tone");
const stoppedHtml = renderSupervisor(normalizeSupervisor({ ...SUPERVISOR_PAYLOAD, state: "STOPPED", result: { available: false } }));
check(stoppedHtml.includes('class="badge tone-neutral">STOPPED'), "STOPPED supervisor state uses the neutral tone");

// A task without a supervisor keeps the traditional detail projection.
const legacyHtml = renderSupervisor({ status: "absent", task_id: SUPERVISOR_TASK });
check(!legacyHtml.includes("data-chat-root"), "legacy task without a supervisor does not mount a chat");
check(legacyHtml.includes("五轴状态") || legacyHtml.includes("任务身份"), "legacy task keeps the existing detail rendering");
check(legacyHtml.includes("该任务没有 Supervisor 绑定"), "legacy task states that no supervisor is bound");
check(legacyHtml.includes("data-supervisor-slot"), "legacy detail keeps the supervisor read-only panel");

const loadingHtml = renderSupervisor({ status: "loading" });
check(loadingHtml.includes("正在读取 Supervisor 状态"), "legacy supervisor panel renders a loading state");
const missingHtml = renderSupervisor({ status: "missing" });
check(missingHtml.includes("缺少 task_id"), "supervisor panel renders a missing-task-id state");
const errorHtml = renderSupervisor({
  status: "error",
  endpoint: supervisorEndpoint(SUPERVISOR_TASK),
  task_id: SUPERVISOR_TASK,
  error: { code: "API_TIMEOUT", message: "API request timed out", retryable: true, status: 0 }
});
check(errorHtml.includes("Supervisor 读取失败"), "task detail renders supervisor request errors");
check(errorHtml.includes("API_TIMEOUT") && errorHtml.includes("不回落 fixture"), "supervisor request errors stay visible without fixture fallback");
check(!errorHtml.includes("PONG"), "supervisor request errors never render fixture success data");

const demoHtml = renderSupervisor(demoSupervisor(), { apiMode: false, session: demoSessionMessages() });
check(demoHtml.includes("DEMO") && demoHtml.includes("PONG"), "fixture mode renders a clearly-labeled conversation demo");
check(demoHtml.includes("fixture 演示"), "fixture conversation is labeled as non-live");
check(demoHtml.includes("data-chat-input") && /data-chat-input[^>]*disabled|disabled[^>]*data-chat-input/.test(demoHtml), "fixture conversation composer is disabled (no fake send)");
check(!demoHtml.includes("refresh-chat"), "fixture conversation demo has no live refresh action");

// Intake new-task form: TaskCreate body and API-mode markup.
const LEAD_SESSION = "11111111-2222-4333-8444-555555555555";
const built = buildTaskCreate({
  title: "  Smoke task  ",
  objective: "  Reply with PONG  ",
  entry_mode: "form",
  lead_agent_id: "",
  lead_session_id: LEAD_SESSION,
  prompt: "  Reply with the single word PONG and nothing else.  "
});
check(built.title === "Smoke task" && built.objective === "Reply with PONG", "TaskCreate builder trims title and objective");
check(built.prompt === "Reply with the single word PONG and nothing else.", "TaskCreate builder trims the prompt");
check(built.entry_mode === "form" && built.task_category === "voice_interaction", "TaskCreate builder keeps server defaults");
check(built.lead_agent_id === DEFAULT_LEAD_AGENT_ID, "TaskCreate builder defaults the lead agent display id");
check(built.lead_session_id === LEAD_SESSION, "TaskCreate builder keeps an explicit lead session id");
check(buildTaskCreate({ entry_mode: "bogus" }).entry_mode === "form", "TaskCreate builder rejects an unknown entry mode");
const missingBody = buildTaskCreate({ title: "", objective: "", prompt: "" });
check(!missingBody.title && !missingBody.objective && !missingBody.prompt, "TaskCreate builder leaves missing fields empty for validation");
const rejectedWrite = await createTask({ title: "", objective: "", prompt: "" });
check(rejectedWrite.ok === false && rejectedWrite.error.code === "VALIDATION_ERROR", "createTask rejects an incomplete TaskCreate before any request");
check(rejectedWrite.status === 0 && rejectedWrite.error.retryable === false, "createTask validation failure carries status/code/message for inline rendering");
const rejectedDelete = await deleteTask("");
check(rejectedDelete.ok === false && rejectedDelete.error.code === "MISSING_TASK_ID", "deleteTask rejects a missing task id before any request");

const resourceBody = buildTaskCreate({
  title: "Resources",
  objective: "Use the selected resources",
  prompt: "PONG",
  node_ids: [" node-1 ", "node-1", "node-2"],
  device_ids: [" device-1 ", ""]
});
check(resourceBody.node_ids.join(",") === "node-1,node-2", "TaskCreate trims and dedupes node_ids");
check(resourceBody.device_ids.join(",") === "device-1", "TaskCreate drops empty device_ids");
check(normalizeResourceIds("a, b, a").join(",") === "a,b", "resource id normalization accepts comma strings");
const tooManyResources = await createTask({
  title: "Too many",
  objective: "Over the cap",
  prompt: "PONG",
  node_ids: Array.from({ length: MAX_TASK_RESOURCES + 1 }, (_, index) => `node-${index}`)
});
check(tooManyResources.ok === false && tooManyResources.error.code === "VALIDATION_ERROR", "createTask rejects more than 50 nodes before any request");
check(tooManyResources.status === 0 && tooManyResources.error.retryable === false, "resource cap failure carries status/code for inline rendering");
const fixtureResources = await loadTaskResources();
check(fixtureResources.ok && fixtureResources.mode === "fixture", "fixture mode loads demo execution resources");
check(fixtureResources.nodes.length > 0 && fixtureResources.devices.length > 0, "fixture execution resources expose demo nodes and devices");
check(fixtureResources.devices.every((device) => device.node_id), "fixture devices retain their owning node id");

const in02 = ROUTES.find((route) => route.id === "IN-02");
const fixtureIntake = intake.render({ route: in02, params: {}, view: view("FX-01") });
check(fixtureIntake.includes("prototype-fixture"), "fixture intake keeps the prototype form and demo notice");
check(fixtureIntake.includes('id="draft-title"'), "fixture intake keeps the three-step prototype fields");
check(!fixtureIntake.includes('id="new-task-form"'), "fixture intake does not render the live write form");

const fx01 = view("FX-01");
const apiIntakeView = {
  ...fx01,
  meta: { ...fx01.meta, server_authoritative: true },
  flags: { ...fx01.flags, noPermission: false }
};
const apiIntake = intake.render({ route: in02, params: {}, view: apiIntakeView });
check(apiIntake.includes('id="new-task-form"'), "API-mode intake renders the real new-task form");
check(apiIntake.includes('name="title"') && apiIntake.includes('name="objective"') && apiIntake.includes('name="prompt"'), "API-mode form exposes the required TaskCreate fields");
check(apiIntake.includes('name="entry_mode"') && apiIntake.includes('name="lead_agent_id"'), "API-mode form exposes entry mode and lead agent");
check(apiIntake.includes('for="new-task-title"') && apiIntake.includes('id="new-task-title"'), "API-mode form labels are associated with inputs");
check(apiIntake.includes('id="new-task-feedback"') && apiIntake.includes('role="alert"'), "API-mode form has an inline error alert");
check(apiIntake.includes("创建任务") && apiIntake.includes("POST /api/v1/tasks"), "API-mode form submits a real task creation");
check(apiIntake.includes("Reply with the single word PONG and nothing else."), "API-mode prompt defaults to a deterministic smoke prompt");
check(apiIntake.includes("进入任务详情"), "API-mode form states the success destination");

const blockedIntake = intake.render({
  route: in02,
  params: {},
  view: { ...apiIntakeView, flags: { ...apiIntakeView.flags, noPermission: true } }
});
check(blockedIntake.includes("disabled") && blockedIntake.includes("CREATE_TASK"), "API-mode form disables submit without CREATE_TASK and states why");

for (const message of failures) console.error(`FAIL  ${message}`);
console.log(`\n${passed} passed, ${failures.length} failed`);
if (failures.length) process.exit(1);
