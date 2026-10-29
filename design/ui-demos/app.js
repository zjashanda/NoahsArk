import { fixture } from "./fixtures.js";

const modes = {
  cloudline: { name:"Cloudline", subtitle:"Spacious left rail", desc:"A quiet editorial shell for deciding where attention is needed." },
  precision: { name:"Precision Desk", subtitle:"Dense instrument table", desc:"A compact scan surface for operators comparing many runs." },
  focus: { name:"Focus Flow", subtitle:"Workspace + inspector", desc:"A focused queue that keeps the current task and its context together." }
};

const icon = () => "";
const params = new URLSearchParams(location.search);
const bodyData = document.body.dataset;
let demo = modes[params.get("demo")] ? params.get("demo") : (modes[bodyData.direction] ? bodyData.direction : null);
let view = params.get("view") === "detail" ? "detail" : (bodyData.view === "detail" ? "detail" : "mission");
let theme = localStorage.getItem("noahsark-demo-theme") || "light";
const app = document.querySelector("#app");

function statusClass(value) {
  if (["PASS","PASSED","COMPLETE","ONLINE"].includes(value)) return "pass";
  if (["BLOCKED","PENDING","INCOMPLETE","STALE"].includes(value)) return "warn";
  if (["OFFLINE","NOT_RUN","UNKNOWN","UNVERIFIED","NOT_EVALUATED"].includes(value)) return "neutral";
  return "action";
}
function status(value) { return `<span class="status ${statusClass(value)}">${value}</span>`; }
function taskCard(task) {
  return `<article class="task-card">
    <div><div class="task-meta">${task.id} · R-04 · ${task.mode}</div><h3>${task.title}</h3><p class="task-meta">${task.stage}</p></div>
    <div class="signal-row">${status(task.state)}${status(task.stale)}${status(task.progress)}</div>
    <div class="signal-row"><span class="signal"><strong>${task.gate}</strong> Gate G6 · ${task.gateOwner}</span><span class="signal"><strong>Evidence</strong> ${task.evidence[1]} received · ${task.evidence[2]} verified</span></div>
    <a class="button subtle" href="?demo=${demo}&view=detail" data-action="detail">${icon("detail")} Open detail</a>
  </article>`;
}
function axisTable(task) {
  const labels = ["Execution", "Validity", "Business verdict", "Evidence", "Verification"];
  return `<table class="axis-table"><caption>Five independent verdict axes · Linux control-plane projection</caption><thead><tr><th scope="col">Axis</th><th scope="col">Value</th><th scope="col">Reading</th></tr></thead><tbody>${labels.map((label, index) => `<tr><td>${label}</td><td class="axis-value">${status(task.axes[index])}</td><td>${["Execution ended; not a verdict.","Input validity is independently read.","Business signal is not evidence completeness.","Received and verified remain separate.","Independent review has not run."][index]}</td></tr>`).join("")}</tbody></table>`;
}
function evidence(task) { return `<div class="evidence-grid"><div class="evidence-cell"><b>${task.evidence[0]}</b><span>Expected</span></div><div class="evidence-cell"><b>${task.evidence[1]}</b><span>Received</span></div><div class="evidence-cell"><b>${task.evidence[2]}</b><span>Verified</span></div></div>`; }
function header(title, description) { return `<header class="topline"><div><p class="eyebrow">${modes[demo].name} · ${view === "mission" ? "Mission Control" : "Task Detail"}</p><h1>${title}</h1><p class="lede">${description}</p></div><div class="topline-actions"><div class="view-toggle" role="group" aria-label="View selector"><a class="nav-button ${view === "mission" ? "active" : ""}" aria-current="${view === "mission" ? "page" : "false"}" href="?demo=${demo}">${icon("grid")} Mission Control</a><a class="nav-button ${view === "detail" ? "active" : ""}" aria-current="${view === "detail" ? "page" : "false"}" href="?demo=${demo}&view=detail">${icon("detail")} Task Detail</a></div><button class="theme-button" data-action="theme" aria-label="Switch color theme">${theme === "light" ? icon("moon") : icon("sun")} ${theme === "light" ? "Dark" : "Light"}</button></div></header>`; }
function nav(compact = false) { return `<nav class="side-nav" aria-label="Primary navigation"><div class="brand">NoahsArk<small>direction lab</small></div><div class="nav-list"><a class="nav-button" aria-current="page" href="?demo=${demo}">${icon("grid")}<span>Mission Control</span></a><a class="nav-button" href="?demo=${demo}&view=detail">${icon("detail")}<span>Task Detail</span></a></div><div class="nav-spacer"></div><a class="back-link" href="index.html">${icon("back")} Back to directions</a></nav>`; }
function mission() { return `<section class="content-grid"><div class="panel"><div class="panel-header"><div><h2>Attention queue</h2><p>Three fixture tasks, one shared fact model.</p></div><span class="status warn">3 NEED REVIEW</span></div><div class="task-list">${fixture.tasks.map(taskCard).join("")}</div></div><aside class="panel panel-pad"><p class="section-label">Shared vocabulary</p><h2>Facts stay separate</h2><p class="lede">The same fixture makes layout—not invented status semantics—the variable between directions.</p><div class="signal-row"><span class="signal"><strong>Offline</strong> still occupied</span><span class="signal"><strong>Stale</strong> last authority shown</span><span class="signal"><strong>Partial</strong> evidence visible</span></div><div class="callout"><strong>Formal PASS requires all five axes.</strong><p>COMPLETED, RELEASED, and a business PASS do not become a formal PASS by themselves.</p></div></aside></section>`; }
function detail() { const task = fixture.tasks[0]; return `<section class="content-grid"><div class="panel panel-pad"><div class="detail-header"><div><p class="section-label">${task.id} · revision R-04</p><h2>${task.title}</h2><p>${task.stage} · ${task.mode} run · source: ${fixture.source}</p></div><span class="status warn">${task.gate}</span></div>${axisTable(task)}<div class="callout"><strong>Why this is not formal PASS</strong><p>Business verdict is PASS, but evidence is INCOMPLETE and verification is NOT_RUN. Execution COMPLETED is deliberately shown as a different fact.</p></div></div><aside class="panel panel-pad"><p class="section-label">Evidence ledger</p><h2>Required items</h2>${evidence(task)}<p class="lede">Received evidence is not verified evidence. The partial state remains visible.</p><div class="signal-row">${status(task.state)}${status(task.stale)}<span class="signal"><strong>Progress</strong>${task.progress}</span></div></aside></section>`; }
function render() {
  document.documentElement.dataset.theme = theme;
  if (!demo) { app.innerHTML = `<section class="selector"><header class="selector-head"><div><p class="eyebrow">NoahsArk · direction lab</p><h1>Three ways to hold the same truth.</h1><p class="lede">A bounded comparison of navigation, density, and spatial grammar before the full UI is designed.</p></div><button class="theme-button" data-action="theme">${theme === "light" ? icon("moon") : icon("sun")} ${theme === "light" ? "Dark" : "Light"}</button></header><div class="direction-grid">${Object.entries(modes).map(([key, mode]) => `<a class="direction-link" href="?demo=${key}"><strong>${mode.name}</strong><small>${mode.subtitle}<br>${mode.desc}</small><span>Explore direction ${icon("detail")}</span></a>`).join("")}</div></section>`; return; }
  const body = view === "mission" ? mission() : detail();
  if (demo === "focus") app.innerHTML = `<div class="shell focus"><header class="top-nav"><div class="brand">NoahsArk <small>Focus Flow</small></div><nav aria-label="Workspace navigation"><a class="nav-button" aria-current="${view === "mission" ? "page" : "false"}" href="?demo=focus">Mission Control</a><a class="nav-button" href="?demo=focus&view=detail">Task Detail</a><a class="back-link" href="index.html">Back</a></nav><button class="theme-button" data-action="theme">${theme === "light" ? icon("moon") : icon("sun")} Theme</button></header><main class="workspace"><div class="app-main">${header(view === "mission" ? "Focus the next decision" : "Inspect the blocked run", modes.focus.desc)}${body}</div><aside class="panel panel-pad inspector"><p class="section-label">Right inspector</p><h3>Current context</h3><p>NA-2048 · Node W-07</p><div class="signal-row">${status("OFFLINE")}${status("OCCUPIED")}</div><p class="lede">The inspector has one job: keep communication, occupancy, and permit visible without turning them into a single device status.</p></aside></main></div>`;
  else app.innerHTML = `<div class="shell app-shell ${demo}">${nav()}<main class="app-main">${header(view === "mission" ? (demo === "precision" ? "Precision at a glance" : "A calm view of attention") : "Task detail without the noise", modes[demo].desc)}${body}</main></div>`;
}
document.addEventListener("click", (event) => { const action = event.target.closest("[data-action]")?.dataset.action; if (action === "theme") { theme = theme === "light" ? "dark" : "light"; localStorage.setItem("noahsark-demo-theme", theme); render(); } });
render();
