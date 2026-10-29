// Application shell: persistent candidate ribbon, sidebar, topbar, mobile nav.

import { AREAS, OPERATIONS_AREAS, PRIMARY_AREAS, areaEntryPath } from "./route-manifest.js";
import { icon } from "./icons.js";
import { SCENARIOS } from "./fixtures.js";
import { esc } from "./components.js";
import { ROLES, getRoleId } from "./roles.js";
import { getLang } from "./i18n.js";
import { isApiMode } from "./api.js";

function navCounts(view) {
  const f = view.flags;
  return {
    MC: (f.blocked ? 1 : 0) + (f.reconciling || f.pendingStop ? 1 : 0) + (f.stale ? 1 : 0) + (f.quarantined ? 1 : 0) + (f.offline ? 1 : 0),
    RN: f.reconciling || f.offline ? 1 : 0,
    DV: (f.quarantined ? 1 : 0) + (f.draining ? 1 : 0)
  };
}

function navItem(area, activeArea, counts) {
  const meta = AREAS[area];
  const count = counts[area];
  const current = area === activeArea ? ' aria-current="page"' : "";
  return `<a class="nav-item" href="#${areaEntryPath(area)}" data-area="${area}" data-nav aria-label="${esc(meta.label)}"${current}>
    ${icon(meta.icon, "nav-icon")}
    <span class="nav-label">${esc(meta.label)}</span>
    ${count ? `<span class="nav-count" aria-label="${count} 项需要处理">${count}</span>` : ""}
  </a>`;
}

export function navMarkup(activeArea, counts) {
  const primary = PRIMARY_AREAS.map((area) => navItem(area, activeArea, counts)).join("");
  const operations = OPERATIONS_AREAS.map((area) => navItem(area, activeArea, counts)).join("");
  return `
    <div class="nav-group">
      <div class="nav-group-label">工作区</div>
      ${primary}
    </div>
    <div class="nav-group">
      <div class="nav-group-label">Operations</div>
      ${operations}
    </div>
  `;
}

function globalFlags(view) {
  const { flags, link } = view;
  const communication = link.communication_state;
  const connection = communication === "OFFLINE"
    ? { cls: "is-danger", text: "连接 · 离线", glyph: "offline" }
    : communication === "DEGRADED"
      ? { cls: "is-attention", text: "连接 · 降级", glyph: "alert" }
      : communication === "UNKNOWN"
        ? { cls: "is-neutral", text: "连接 · 未知", glyph: "info" }
        : { cls: "", text: "连接 · 实时", glyph: "dot" };
  const pendingStop = flags.pendingStop || flags.reconciling ? 1 : 0;
  const reconcile = flags.reconciling ? 1 : 0;
  return `
    <span class="flag ${connection.cls}" title="${connection.text}">${icon(connection.glyph)}<span class="flag-label">${connection.text}</span></span>
    <span class="flag ${pendingStop ? "is-attention" : ""}" title="待 STOP ${pendingStop} 项">${icon("stop")}<span class="flag-label">待 STOP · ${pendingStop}</span></span>
    <span class="flag ${reconcile ? "is-attention" : ""}" title="对账中 ${reconcile} 项">${icon("refresh")}<span class="flag-label">对账中 · ${reconcile}</span></span>
    <span class="flag ${flags.stale ? "is-attention" : "is-neutral"}" title="投影新鲜度">${icon("clock")}<span class="flag-label">${flags.stale ? "STALE" : "FRESH"}</span></span>
  `;
}

function scenarioOptions(view) {
  return SCENARIOS.map((item) => `<option value="${item.id}"${item.id === view.scenario.id ? " selected" : ""}>${esc(item.label)}</option>`).join("");
}

function roleOptions() {
  const current = getRoleId();
  return ROLES.map((role) => `<option value="${role.id}"${role.id === current ? " selected" : ""}>${esc(role.zh)} · ${esc(role.en)}</option>`).join("");
}

function demoControls(view, prefix) {
  const lang = getLang();
  const api = isApiMode();
  return `
    <div class="demo-controls">
      <div class="demo-mode">
        <span class="badge ${api ? "tone-action" : "tone-neutral"}" data-mode-chip>${api ? "API · server_authoritative" : "FIXTURE · local"}</span>
      </div>
      <label class="demo-control"><span>数据源</span>
        <select id="mode-select-${prefix}" aria-label="数据源模式">
          <option value="fixture"${api ? "" : " selected"}>FIXTURE · 本地</option>
          <option value="api"${api ? " selected" : ""}>API · 控制面</option>
        </select>
      </label>
      <label class="demo-control"><span>状态预览</span>
        <select id="scenario-select-${prefix}" aria-label="状态 fixture 预览">${scenarioOptions(view)}</select>
      </label>
      <label class="demo-control"><span>角色</span>
        <select id="role-select-${prefix}" aria-label="演示角色">${roleOptions()}</select>
      </label>
      <button class="demo-lang" type="button" data-action="lang" aria-label="Switch language">
        ${lang === "zh" ? "EN · English" : "中文 · Chinese"}
      </button>
      <p class="demo-note">${api ? "API 模式：失败显式报错，不回退 fixture。" : "客户端角色演示，不构成访问控制。"}</p>
    </div>
  `;
}

function langButton() {
  return `<button class="icon-button lang-button" type="button" data-action="lang" aria-label="Switch language" title="Switch language">${getLang() === "zh" ? "EN" : "中"}</button>`;
}

export function renderShell(view, activeArea) {
  const counts = navCounts(view);
  const api = isApiMode();
  return `
    <a class="skip-link" href="#main-content">跳到主内容</a>
    <div class="app-shell">
      <div class="ribbon" role="note">
        <span class="ribbon-dot" aria-hidden="true"></span>
        <strong>CANDIDATE UI</strong>
        <span aria-hidden="true">·</span><span>PROTOTYPE</span>
        <span aria-hidden="true">·</span><span>NOT FROZEN</span>
        <span class="ribbon-extra" aria-hidden="true">·</span><span class="ribbon-extra">${api ? "SERVER DATA" : "MOCK DATA"}</span>
      </div>

      <aside class="sidebar" aria-label="主导航">
        <a class="brand" href="#/console" aria-label="NoahsArk 控制台首页">
          <img class="brand-mark" src="./favicon.svg" alt="">
          <span class="brand-name"><strong>NoahsArk</strong><span>Console · Cloudline</span></span>
        </a>
        <div class="sidebar-scroll">${navMarkup(activeArea, counts)}</div>
        <div class="sidebar-foot">${demoControls(view, "sidebar")}</div>
      </aside>

      <div class="app-main">
        <header class="topbar">
          <button class="icon-button topbar-menu" type="button" data-action="open-drawer" aria-controls="nav-drawer" aria-expanded="false" aria-label="打开导航">${icon("menu")}</button>
          <div class="search">
            ${icon("search")}
            <input id="nav-filter" type="search" placeholder="筛选导航（按名称）" aria-label="筛选导航" autocomplete="off">
          </div>
          <div class="topbar-spacer"></div>
          <div class="global-flags" aria-label="全局指示器">${globalFlags(view)}</div>
          ${langButton()}
          <button class="icon-button" id="theme-toggle" type="button" data-action="theme" aria-label="切换浅色或深色主题" title="切换浅色/深色">
            ${icon("moon")}
          </button>
          <a class="btn btn-primary" href="#/console/intake/new" aria-label="新建任务">${icon("plus")}<span>新建任务</span></a>
        </header>

        <main id="main-content" class="content" tabindex="-1">
          <div class="content-inner" id="route-view"></div>
        </main>
      </div>
    </div>

    <nav class="mobile-nav" aria-label="移动导航">
      <a href="#/console" data-area="MC" ${activeArea === "MC" ? 'aria-current="page"' : ""}>${icon("mission")}<span>Mission</span></a>
      <a href="#/console/tasks" data-area="TK" ${activeArea === "TK" ? 'aria-current="page"' : ""}>${icon("tasks")}<span>Tasks</span></a>
      <a href="#/console/runs" data-area="RN" ${activeArea === "RN" ? 'aria-current="page"' : ""}>${icon("runs")}<span>Runs</span></a>
      <a href="#/console/devices" data-area="DV" ${activeArea === "DV" ? 'aria-current="page"' : ""}>${icon("devices")}<span>Devices</span></a>
      <button type="button" data-action="open-more" aria-controls="more-sheet" aria-expanded="false">${icon("menu")}<span>More</span></button>
    </nav>

    <div class="nav-drawer" id="nav-drawer" hidden>
      <button class="sheet-backdrop" type="button" data-action="close-drawer" aria-label="关闭导航"></button>
      <div class="sheet-panel" role="dialog" aria-modal="true" aria-label="主导航">
        <div class="sheet-head">
          <span class="sheet-title">NoahsArk Console</span>
          <button class="icon-button" type="button" data-action="close-drawer" aria-label="关闭导航">${icon("close")}</button>
        </div>
        ${navMarkup(activeArea, counts)}
        <div class="nav-group">
          <div class="nav-group-label">预览设置</div>
          ${demoControls(view, "drawer")}
        </div>
      </div>
    </div>

    <div class="more-sheet" id="more-sheet" hidden>
      <button class="sheet-backdrop" type="button" data-action="close-more" aria-label="关闭更多菜单"></button>
      <div class="sheet-panel" role="dialog" aria-modal="true" aria-label="更多导航与设置">
        <div class="sheet-head">
          <span class="sheet-title">更多</span>
          <button class="icon-button" type="button" data-action="close-more" aria-label="关闭更多菜单">${icon("close")}</button>
        </div>
        ${navMarkup(activeArea, counts)}
        <div class="nav-group">
          <div class="nav-group-label">预览设置</div>
          ${demoControls(view, "mobile")}
          <button class="nav-item" type="button" data-action="theme" style="width:100%;border:0;background:transparent">
            ${icon("moon", "nav-icon")}<span class="nav-label">切换浅色/深色</span>
          </button>
        </div>
        <p class="caption" style="padding:12px">
          ${api ? "control-plane API" : "prototype-fixture"} · schema 0.1 · server_authoritative=${api ? "true" : "false"}<br>
          候选原型，非冻结，不代表真实执行。
        </p>
      </div>
    </div>

    <div id="global-feedback" class="global-feedback" role="status" aria-live="polite" hidden></div>

    <dialog id="confirm-dialog" class="confirm-dialog" aria-labelledby="dialog-title">
      <div class="dialog-body">
        <h2 class="dialog-title" id="dialog-title">确认操作</h2>
        <div id="dialog-message" class="secondary small"></div>
      </div>
      <div class="dialog-actions">
        <button class="btn btn-quiet" type="button" data-action="dialog-cancel">取消</button>
        <button class="btn btn-danger" type="button" data-action="dialog-confirm" id="dialog-confirm">确认</button>
      </div>
    </dialog>
  `;
}
