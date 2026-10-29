// Hash router for the 39 canonical routes. Exact paths win over parameter routes.

import { ROUTES } from "./route-manifest.js";

export function normalizePath(raw) {
  let value = raw == null
    ? (typeof window !== "undefined" ? window.location.hash : "")
    : raw;
  if (value.startsWith("#")) value = value.slice(1);
  if (!value || !value.startsWith("/")) value = "/console";
  if (value.startsWith("/aitest")) value = `/console${value.slice("/aitest".length)}`;
  const path = value.split("?")[0].replace(/\/+$/, "");
  return path || "/console";
}

function compile(pattern) {
  const keys = [];
  const clean = pattern.split("/").map((segment) => {
    if (segment.startsWith(":")) {
      keys.push(segment.slice(1));
      return "([^/]+)";
    }
    return segment.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }).join("/");
  return { regex: new RegExp(`^${clean}$`), keys };
}

const COMPILED = new Map(ROUTES.map((route) => [route.path, { route, ...compile(route.path) }]));
const PARAM_ROUTES = ROUTES
  .filter((route) => route.path.includes(":"))
  .map((route) => ({ route, ...compile(route.path) }));

export function matchRoute(path) {
  const exact = COMPILED.get(path);
  if (exact) return { route: exact.route, params: {} };
  for (const entry of PARAM_ROUTES) {
    const match = entry.regex.exec(path);
    if (match) {
      const params = {};
      entry.keys.forEach((key, index) => {
        params[key] = decodeURIComponent(match[index + 1]);
      });
      return { route: entry.route, params };
    }
  }
  return null;
}

export function routeHref(path) {
  return `#${path}`;
}

export function navigate(path, options = {}) {
  const target = `#${path}`;
  if (options.replace && typeof window !== "undefined") {
    window.history.replaceState(null, "", target);
    return;
  }
  if (typeof window !== "undefined") window.location.hash = target;
}

export function currentRoute() {
  const path = normalizePath();
  return { path, ...(matchRoute(path) || { route: null, params: {} }) };
}

export function onRouteChange(handler) {
  window.addEventListener("hashchange", () => handler(currentRoute()));
}
