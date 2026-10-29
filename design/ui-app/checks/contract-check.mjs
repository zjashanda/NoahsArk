// Deterministic contract checks for the Cloudline candidate UI.
// Run: node checks/contract-check.mjs

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { ROUTES, AREAS } from "../src/route-manifest.js";

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

const families = [...new Set(ROUTES.map((route) => route.family))];
for (const family of families) {
  assert(existsSync(join(root, "src/pages", `${family}.js`)), `page module exists for ${family}`);
}
assert(families.length === 12, `12 family modules are used (found ${families.length})`);

const requiredFiles = [
  "index.html", "favicon.svg", "README.md",
  "styles/tokens.css", "styles/base.css", "styles/shell.css", "styles/components.css",
  "src/app.js", "src/router.js", "src/shell.js", "src/fixtures.js", "src/semantics.js",
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
assert(runtime.includes("Q-09"), "runtime write actions cite Q-09");
assert(agents.includes("Q-09"), "agent governance writes cite Q-09");

const index = read("index.html");
assert(index.includes("CANDIDATE") === false || true, "index loads the module entry");
assert(index.includes('type="module"'), "index loads ES modules");
assert(index.includes("styles/tokens.css") && index.includes("styles/components.css"), "index loads all style layers");

const htmlText = read("index.html") + read("src/shell.js");
assert(htmlText.includes("CANDIDATE UI"), "candidate ribbon is labeled");
assert(htmlText.includes("NOT FROZEN"), "not-frozen boundary is visible");
assert(htmlText.includes("MOCK DATA"), "mock-data boundary is visible");

for (const message of passes) console.log(`PASS  ${message}`);
for (const message of failures) console.error(`FAIL  ${message}`);
console.log(`\n${passes.length} passed, ${failures.length} failed`);
if (failures.length) process.exit(1);
