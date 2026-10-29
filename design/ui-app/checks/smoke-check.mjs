// Runtime smoke checks without a browser: routing, module imports, fixtures.
// Run: node checks/smoke-check.mjs

import { ROUTES } from "../src/route-manifest.js";
import { matchRoute, normalizePath } from "../src/router.js";
import {
  SCENARIOS,
  axesFor,
  view
} from "../src/fixtures.js";
import {
  AXIS_ORDER,
  FORMAL_PASS,
  isFormalPass,
  progressModel,
  releaseModel,
  verdictLabel,
  offlineCombination
} from "../src/semantics.js";

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

for (const message of failures) console.error(`FAIL  ${message}`);
console.log(`\n${passed} passed, ${failures.length} failed`);
if (failures.length) process.exit(1);
