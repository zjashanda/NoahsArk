// Application bootstrap and event wiring.

import { currentScenario, setScenarioId, view } from "./fixtures.js";
import { currentRoute, normalizePath, onRouteChange } from "./router.js";
import { renderShell } from "./shell.js";
import { icon } from "./icons.js";
import { esc, kv, pageHeader, panel, stateBlock } from "./components.js";
import { applyLanguage, getLang, setLang, t } from "./i18n.js";
import { currentRole, setRoleId } from "./roles.js";
import { setApiMode } from "./api.js";
import { loadRouteView } from "./data-source.js";
import { adaptRouteView } from "./api-adapter.js";

import * as mission from "./pages/mission.js?v=2";
import * as intake from "./pages/intake.js";
import * as tasks from "./pages/tasks.js";
import * as runs from "./pages/runs.js";
import * as evidence from "./pages/evidence.js";
import * as devices from "./pages/devices.js";
import * as reports from "./pages/reports.js";
import * as knowledge from "./pages/knowledge.js";
import * as runtime from "./pages/runtime.js";
import * as agents from "./pages/agents.js";
import * as audit from "./pages/audit.js";
import * as settings from "./pages/settings.js";

const PAGES = { mission, intake, tasks, runs, evidence, devices, reports, knowledge, runtime, agents, audit, settings };
const THEME_KEY = "naa-theme";
let lastTrigger = null;
let feedbackTimer = null;
let rendered = false;
let renderToken = 0;

function resolvedTheme() {
  const stored = window.localStorage.getItem(THEME_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  window.localStorage.setItem(THEME_KEY, theme);
  const button = document.getElementById("theme-toggle");
  if (button) {
    const dark = theme === "dark";
    button.innerHTML = icon(dark ? "sun" : "moon");
    button.setAttribute("aria-label", dark ? "切换到浅色主题" : "切换到深色主题");
  }
}

function toggleTheme() {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  applyTheme(next);
  showFeedback(next === "dark" ? "已切换为深色主题（本地偏好）。" : "已切换为浅色主题（本地偏好）。");
}

function toggleLanguage() {
  const next = getLang() === "zh" ? "en" : "zh";
  setLang(next);
  mount({ focus: false });
  showFeedback(next === "en"
    ? "Language switched to English. UI chrome is translated; mock fixture data stays as authored."
    : "已切换为中文。界面文案已恢复；mock 数据保持不变。");
}

function changeRole(value) {
  setRoleId(value);
  mount({ focus: false });
  const role = currentRole();
  showFeedback(getLang() === "en"
    ? `Role switched to ${role.en}. Client-side demo only; the server still fail-closes.`
    : `已切换为角色 ${role.zh}/${role.en}。仅客户端演示，服务端仍 fail-closed。`);
}

function setDataSource(enabled) {
  setApiMode(enabled);
  if (typeof window === "undefined" || !window.history || !window.location) return;
  const url = new URL(window.location.href);
  url.searchParams.set("api", enabled ? "1" : "0");
  window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
}

function changeDataSource(enabled) {
  setDataSource(enabled);
  mount({ focus: false });
  showFeedback(getLang() === "en"
    ? (enabled ? "Data source: control-plane API. Errors stay visible and never fall back to fixtures." : "Data source: local fixtures. server_authoritative=false.")
    : (enabled ? "数据源已切换为控制面 API。请求失败会显式报错，不会静默回退 fixture。" : "数据源已切换为本地 fixture。server_authoritative=false。"));
}

function showFeedback(text) {
  const node = document.getElementById("global-feedback");
  if (!node) return;
  node.textContent = t(text);
  node.hidden = false;
  window.clearTimeout(feedbackTimer);
  feedbackTimer = window.setTimeout(() => {
    node.hidden = true;
  }, 3200);
}

function updateNav(area) {
  document.querySelectorAll("[data-area]").forEach((item) => {
    if (item.getAttribute("data-area") === area) item.setAttribute("aria-current", "page");
    else item.removeAttribute("aria-current");
  });
}

function notFound(path) {
  return `
    ${pageHeader({
      eyebrow: "ROUTE · NOT FOUND",
      title: "未登记的路由",
      description: `路径 <span class="mono">${esc(path)}</span> 不在 39 条规范路由中。请从导航进入已登记区域。`
    })}
    ${stateBlock("empty", { title: "路由不存在", note: "未登记入口不会获得隐式页面；旧 /aitest/* 仅作实现期兼容别名。" })}
    <p><a class="btn" href="#/console">${icon("arrow")}返回 Mission Control</a></p>
  `;
}

function apiErrorPanel(info, result) {
  const error = result.error || {};
  const retryable = error.retryable !== false;
  return `
    ${pageHeader({
      eyebrow: `API · ${info.route.id} · ERROR`,
      title: "控制面数据不可用",
      description: `读取 <span class="mono">${esc(result.endpoint || info.route.id)}</span> 失败。API 模式不会静默回退到 fixture，页面保留失败事实与重试入口。`
    })}
    ${stateBlock("error", {
      title: `API 请求失败 · ${error.code || "ERROR"}`,
      note: error.message || "控制面请求未成功。"
    })}
    ${panel({
      title: "请求事实",
      note: "失败不会被渲染为空数据或成功；切换到 fixture 是显式操作",
      body: kv([
        ["HTTP status", `<span class="mono">${esc(String(error.status ?? result.status ?? "—"))}</span>`],
        ["endpoint", `<span class="mono">${esc(result.endpoint || "—")}</span>`],
        ["retryable", `<span class="mono">${retryable ? "true" : "false"}</span>`],
        ["correlation_id", `<span class="mono">${esc(error.correlation_id || "—")}</span>`]
      ])
    })}
    <div class="row" style="margin-top:16px">
      ${retryable ? `<button class="btn btn-primary" type="button" data-action="retry-api">${icon("refresh")}重试</button>` : ""}
      <button class="btn" type="button" data-action="switch-fixture">${icon("file")}切换到 fixture</button>
    </div>
  `;
}

async function renderView(options = {}) {
  const info = currentRoute();
  const host = document.getElementById("route-view");
  if (!host) return;
  if (!info.route) {
    host.innerHTML = notFound(info.path);
    applyLanguage(host);
    updateNav(null);
    document.title = getLang() === "en" ? "Route not found · NoahsArk Console" : "未登记路由 · NoahsArk Console";
    return;
  }
  const page = PAGES[info.route.family];
  if (!page || typeof page.render !== "function") {
    host.innerHTML = notFound(info.path);
    applyLanguage(host);
    return;
  }

  const token = ++renderToken;
  const result = await loadRouteView(info.route.id, info.params);
  if (token !== renderToken) return;

  let state;
  if (result.mode === "api" && result.error) {
    host.innerHTML = apiErrorPanel(info, result);
    applyLanguage(host);
    updateNav(info.route.area);
    document.title = `${info.route.id} · API error · NoahsArk Console`;
    if (options.focus) {
      const main = document.getElementById("main-content");
      if (main) {
        main.scrollTop = 0;
        main.focus({ preventScroll: true });
      }
    }
    return;
  }

  state = result.mode === "api"
    ? adaptRouteView(info.route, info.params, result.payload, view())
    : view();

  host.innerHTML = page.render({ route: info.route, params: info.params, view: state });
  applyLanguage(host);
  updateNav(info.route.area);
  document.title = `${info.route.id} · ${info.route.title} · NoahsArk Console`;
  if (options.focus) {
    const main = document.getElementById("main-content");
    if (main) {
      main.scrollTop = 0;
      main.focus({ preventScroll: true });
    }
  }
}

function mount(options = {}) {
  const state = view();
  const info = currentRoute();
  const activeArea = info.route ? info.route.area : null;
  const app = document.getElementById("app");
  app.innerHTML = renderShell(state, activeArea);
  applyTheme(document.documentElement.dataset.theme || resolvedTheme());
  renderView(options);
  applyLanguage(app);
}

function refreshAfterScenario() {
  const info = currentRoute();
  mount({ focus: false });
  if (info.route) updateNav(info.route.area);
}

function openOverlay(id, trigger) {
  const overlay = document.getElementById(id);
  if (!overlay) return;
  overlay.hidden = false;
  lastTrigger = trigger || null;
  if (lastTrigger) lastTrigger.setAttribute("aria-expanded", "true");
  const focusTarget = overlay.querySelector(".sheet-panel button, .sheet-panel select, .sheet-panel a");
  if (focusTarget) focusTarget.focus();
}

function closeOverlay(id) {
  const overlay = document.getElementById(id);
  if (!overlay) return;
  overlay.hidden = true;
  if (lastTrigger) {
    lastTrigger.setAttribute("aria-expanded", "false");
    lastTrigger.focus();
    lastTrigger = null;
  }
}

function openConfirm(trigger) {
  const dialog = document.getElementById("confirm-dialog");
  if (!dialog || typeof dialog.showModal !== "function") {
    showFeedback(`${trigger.dataset.label || "危险动作"}：当前浏览器不支持确认对话框，操作未提交。`);
    return;
  }
  document.getElementById("dialog-title").textContent = trigger.dataset.title || "确认危险动作";
  document.getElementById("dialog-message").innerHTML = trigger.dataset.message || "请确认前置条件与影响范围。";
  const confirmButton = document.getElementById("dialog-confirm");
  confirmButton.textContent = trigger.dataset.confirmLabel || "确认";
  confirmButton.dataset.result = trigger.dataset.result || `${trigger.dataset.label || "动作"}已提交（mock，不生效）`;
  applyLanguage(dialog);
  dialog.showModal();
}

function wireEvents() {
  document.addEventListener("click", (event) => {
    const skipLink = event.target.closest(".skip-link");
    if (skipLink) {
      event.preventDefault();
      const main = document.getElementById("main-content");
      if (main) {
        main.scrollTop = 0;
        main.focus({ preventScroll: true });
      }
      return;
    }
    const actionEl = event.target.closest("[data-action]");
    if (!actionEl) return;
    const action = actionEl.dataset.action;
    if (action === "theme") {
      toggleTheme();
      return;
    }
    if (action === "lang") {
      toggleLanguage();
      return;
    }
    if (action === "retry-api") {
      renderView({ focus: false });
      showFeedback(getLang() === "en" ? "Retrying the control-plane request." : "正在重试控制面请求。");
      return;
    }
    if (action === "switch-fixture") {
      changeDataSource(false);
      return;
    }
    if (action === "open-drawer") {
      event.preventDefault();
      openOverlay("nav-drawer", actionEl);
      return;
    }
    if (action === "close-drawer") {
      closeOverlay("nav-drawer");
      return;
    }
    if (action === "open-more") {
      event.preventDefault();
      openOverlay("more-sheet", actionEl);
      return;
    }
    if (action === "close-more") {
      closeOverlay("more-sheet");
      return;
    }
    if (action === "dialog-cancel") {
      document.getElementById("confirm-dialog").close();
      return;
    }
    if (action === "dialog-confirm") {
      const dialog = document.getElementById("confirm-dialog");
      const result = document.getElementById("dialog-confirm").dataset.result || "动作已提交（mock，不生效）";
      dialog.close();
      showFeedback(result);
      return;
    }
    if (action === "danger") {
      openConfirm(actionEl);
      return;
    }
    if (action === "mock") {
      showFeedback(`${actionEl.dataset.label || actionEl.textContent.trim()}：原型只读，未调用服务端；数据未改变。`);
      return;
    }
    if (action === "clear-filter") {
      const input = document.getElementById("nav-filter");
      if (input) {
        input.value = "";
        input.dispatchEvent(new Event("input"));
        input.focus();
      }
    }
  });

  document.addEventListener("change", (event) => {
    if (event.target.matches("#mode-select-sidebar, #mode-select-mobile, #mode-select-drawer")) {
      changeDataSource(event.target.value === "api");
      return;
    }
    if (event.target.matches("#scenario-select, #scenario-select-sidebar, #scenario-select-mobile, #scenario-select-drawer")) {
      setScenarioId(event.target.value);
      refreshAfterScenario();
      return;
    }
    if (event.target.matches("#role-select-sidebar, #role-select-mobile, #role-select-drawer")) {
      changeRole(event.target.value);
    }
  });

  document.addEventListener("input", (event) => {
    if (event.target.id !== "nav-filter") return;
    const query = event.target.value.trim().toLowerCase();
    document.querySelectorAll("[data-nav]").forEach((item) => {
      const label = (item.getAttribute("aria-label") || "").toLowerCase();
      item.style.display = !query || label.includes(query) ? "" : "none";
    });
    document.querySelectorAll(".nav-group").forEach((group) => {
      const items = Array.from(group.querySelectorAll("[data-nav]"));
      const visible = items.some((item) => item.style.display !== "none");
      group.style.display = visible ? "" : "none";
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      const dialog = document.getElementById("confirm-dialog");
      if (dialog && dialog.open) {
        dialog.close();
        return;
      }
      if (!document.getElementById("more-sheet").hidden) {
        closeOverlay("more-sheet");
        return;
      }
      if (!document.getElementById("nav-drawer").hidden) {
        closeOverlay("nav-drawer");
        return;
      }
      const input = document.getElementById("nav-filter");
      if (document.activeElement === input) {
        input.value = "";
        input.dispatchEvent(new Event("input"));
      }
    }
    if (event.key === "Enter" && event.target.id === "nav-filter") {
      const firstVisible = Array.from(document.querySelectorAll("[data-nav]")).find((item) => item.style.display !== "none");
      if (firstVisible) {
        const href = firstVisible.getAttribute("href");
        if (href) window.location.hash = href;
      }
    }
  });
}

function boot() {
  document.documentElement.dataset.theme = resolvedTheme();
  mount();
  wireEvents();
  onRouteChange(() => {
    renderView({ focus: true });
  });
  rendered = true;
  void rendered;
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot, { once: true });
} else {
  boot();
}

void currentScenario;
