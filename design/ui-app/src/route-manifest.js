// Canonical route manifest — mirror of routes.json (39 routes, 12 areas).
// Machine-readable source: design/ui-app/routes.json

export const AREAS = {
  MC: { label: "Mission Control", icon: "mission", group: "primary" },
  IN: { label: "Intake", icon: "intake", group: "primary" },
  TK: { label: "Tasks", icon: "tasks", group: "primary" },
  RN: { label: "Runs & Attempts", icon: "runs", group: "primary" },
  EV: { label: "Evidence & Verdict", icon: "evidence", group: "primary" },
  DV: { label: "Devices & Nodes", icon: "devices", group: "primary" },
  RP: { label: "Reports", icon: "reports", group: "primary" },
  KN: { label: "Knowledge", icon: "knowledge", group: "primary" },
  RT: { label: "Runtime & Toolchain", icon: "runtime", group: "operations" },
  AG: { label: "Agents & Reviews", icon: "agents", group: "operations" },
  AU: { label: "Audit & Recovery", icon: "audit", group: "operations" },
  ST: { label: "Settings & Access", icon: "settings", group: "operations" }
};

export const ROUTES = [
  { id: "MC-01", path: "/console", title: "Mission Control", area: "MC", family: "mission" },
  { id: "IN-01", path: "/console/intake", title: "Intake", area: "IN", family: "intake" },
  { id: "IN-02", path: "/console/intake/new", title: "New intake", area: "IN", family: "intake" },
  { id: "IN-03", path: "/console/intake/:draftId", title: "Draft review", area: "IN", family: "intake" },
  { id: "TK-01", path: "/console/tasks", title: "Tasks", area: "TK", family: "tasks" },
  { id: "TK-02", path: "/console/tasks/:taskId/overview", title: "Task overview", area: "TK", family: "tasks" },
  { id: "TK-03", path: "/console/tasks/:taskId/revisions", title: "Revisions & approval", area: "TK", family: "tasks" },
  { id: "TK-04", path: "/console/tasks/:taskId/plan", title: "Plan & cases", area: "TK", family: "tasks" },
  { id: "TK-05", path: "/console/tasks/:taskId/runs", title: "Task runs", area: "TK", family: "tasks" },
  { id: "TK-06", path: "/console/tasks/:taskId/evidence", title: "Task evidence", area: "TK", family: "tasks" },
  { id: "TK-07", path: "/console/tasks/:taskId/verdict", title: "Verdict & gates", area: "TK", family: "tasks" },
  { id: "TK-08", path: "/console/tasks/:taskId/live", title: "Live run", area: "TK", family: "tasks" },
  { id: "TK-09", path: "/console/tasks/:taskId/knowledge", title: "Task knowledge", area: "TK", family: "tasks" },
  { id: "RN-01", path: "/console/runs", title: "Runs", area: "RN", family: "runs" },
  { id: "RN-02", path: "/console/runs/:runId", title: "Run detail", area: "RN", family: "runs" },
  { id: "RN-03", path: "/console/runs/:runId/attempts/:attemptId", title: "Attempt detail", area: "RN", family: "runs" },
  { id: "EV-01", path: "/console/evidence", title: "Evidence", area: "EV", family: "evidence" },
  { id: "EV-02", path: "/console/evidence/:evidenceId", title: "Evidence detail", area: "EV", family: "evidence" },
  { id: "EV-03", path: "/console/verdicts", title: "Verdicts", area: "EV", family: "evidence" },
  { id: "DV-01", path: "/console/devices", title: "Devices & nodes", area: "DV", family: "devices" },
  { id: "DV-02", path: "/console/devices/:deviceId", title: "Device detail", area: "DV", family: "devices" },
  { id: "DV-03", path: "/console/nodes/:nodeId", title: "Node detail", area: "DV", family: "devices" },
  { id: "RP-01", path: "/console/reports", title: "Reports", area: "RP", family: "reports" },
  { id: "RP-02", path: "/console/reports/:reportId", title: "Report detail", area: "RP", family: "reports" },
  { id: "KN-01", path: "/console/knowledge", title: "Knowledge", area: "KN", family: "knowledge" },
  { id: "KN-02", path: "/console/knowledge/:knowledgeId", title: "Knowledge detail", area: "KN", family: "knowledge" },
  { id: "KN-03", path: "/console/knowledge/candidates", title: "Knowledge candidates", area: "KN", family: "knowledge" },
  { id: "RT-01", path: "/console/runtime/models", title: "Runtime models", area: "RT", family: "runtime" },
  { id: "RT-02", path: "/console/runtime/toolchain", title: "Toolchain", area: "RT", family: "runtime" },
  { id: "AG-01", path: "/console/agents", title: "Agents", area: "AG", family: "agents" },
  { id: "AG-02", path: "/console/agents/:agentId", title: "Agent detail", area: "AG", family: "agents" },
  { id: "AG-03", path: "/console/reviews", title: "Reviews", area: "AG", family: "agents" },
  { id: "AU-01", path: "/console/audit", title: "Audit", area: "AU", family: "audit" },
  { id: "AU-02", path: "/console/audit/:eventId", title: "Audit event", area: "AU", family: "audit" },
  { id: "AU-03", path: "/console/recovery", title: "Recovery", area: "AU", family: "audit" },
  { id: "ST-01", path: "/console/settings", title: "Settings", area: "ST", family: "settings" },
  { id: "ST-02", path: "/console/settings/access", title: "Access", area: "ST", family: "settings" },
  { id: "ST-03", path: "/console/settings/notifications", title: "Notifications", area: "ST", family: "settings" },
  { id: "ST-04", path: "/console/settings/retention", title: "Retention", area: "ST", family: "settings" }
];

export const PRIMARY_AREAS = ["MC", "IN", "TK", "RN", "EV", "DV", "RP", "KN"];
export const OPERATIONS_AREAS = ["RT", "AG", "AU", "ST"];

export function areaEntryPath(area) {
  const route = ROUTES.find((item) => item.area === area);
  return route ? route.path : "/console";
}

export function routeById(id) {
  return ROUTES.find((item) => item.id === id) || null;
}
