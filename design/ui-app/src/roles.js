// Permission presentation. Server authorization remains authoritative.

const ROLE_KEY = "naa-role";

export const ROLES = [
  { id: "OBSERVER", zh: "观察者", en: "Observer", capabilities: ["READ"] },
  { id: "APPROVER", zh: "审批者", en: "Approver", capabilities: ["READ", "CREATE_TASK", "APPROVE"] },
  { id: "SESSION_MANAGER", zh: "会话管理员", en: "Session Manager", capabilities: ["READ", "CREATE_TASK", "STOP", "RELEASE", "DEVICE_CONTROL"] },
  { id: "ADMIN", zh: "超级管理员", en: "Super Admin", capabilities: ["*"] }
];

let authoritativePrincipal = null;

export function roleById(id) {
  return ROLES.find((role) => role.id === id) || ROLES[0];
}

export function getRoleId() {
  if (authoritativePrincipal?.role) return authoritativePrincipal.role;
  // Without a browser session there is no local role selection, so fail closed
  // to OBSERVER. The browser entry point still defaults to ADMIN for local dev.
  if (typeof window === "undefined" || !window.localStorage) return "OBSERVER";
  const stored = window.localStorage.getItem(ROLE_KEY);
  // Local development defaults to ADMIN so create/delete controls work out of
  // the box; the server remains authoritative and the role switcher can still
  // downgrade to OBSERVER/APPROVER/SESSION_MANAGER.
  return ROLES.some((role) => role.id === stored) ? stored : "ADMIN";
}

export function setRoleId(id) {
  if (authoritativePrincipal) return;
  if (typeof window !== "undefined" && window.localStorage) {
    window.localStorage.setItem(ROLE_KEY, roleById(id).id);
  }
}

export function setAuthoritativePrincipal(principal) {
  authoritativePrincipal = principal?.role
    ? { role: roleById(principal.role).id, capabilities: Array.isArray(principal.capabilities) ? principal.capabilities : null }
    : null;
}

export function isAuthoritativePrincipal() {
  return Boolean(authoritativePrincipal);
}

export function currentRole() {
  return roleById(getRoleId());
}

export function can(capability) {
  if (!capability) return true;
  if (authoritativePrincipal?.capabilities) {
    return authoritativePrincipal.capabilities.includes("*") || authoritativePrincipal.capabilities.includes(capability);
  }
  const role = currentRole();
  return role.capabilities.includes("*") || role.capabilities.includes(capability);
}

export function roleReason(capability) {
  const role = currentRole();
  const source = authoritativePrincipal ? "服务端会话" : "开发角色预览";
  return `${source}中的 ${role.zh}/${role.en} 缺少 ${capability}；服务端仍 fail-closed。`;
}

const CAP_RULES = [
  { re: /请求原始访问|原始证据/, cap: "EVIDENCE_RAW" },
  { re: /导出/, cap: "READ" },
  { re: /执行恢复演练|恢复演练/, cap: "SETTINGS" },
  { re: /批准|拒绝|请求审批/, cap: "APPROVE" },
  { re: /请求释放|释放/, cap: "RELEASE" },
  { re: /STOP|停止/, cap: "STOP" },
  { re: /隔离/, cap: "DEVICE_CONTROL" },
  { re: /审阅|推广|拒绝候选|应用到草案/, cap: "KNOWLEDGE_PROMOTE" },
  { re: /保存草稿|生成修订种子|提交审阅|生成草案修订|保存设置/, cap: "CREATE_TASK" },
  { re: /更正|生成更正经版本/, cap: "REPORT_WRITE" },
  { re: /修改|分配角色/, cap: "SETTINGS" }
];

export function inferCapability(label) {
  const text = String(label || "").replace(/<[^>]+>/g, " ").trim();
  const rule = CAP_RULES.find((item) => item.re.test(text));
  return rule ? rule.cap : null;
}
