// Demo role switcher. Client-side only; not an access-control implementation.

const ROLE_KEY = "naa-role";

export const ROLES = [
  { id: "OBSERVER", zh: "观察者", en: "Observer", capabilities: ["READ"] },
  { id: "APPROVER", zh: "审批者", en: "Approver", capabilities: ["READ", "CREATE_TASK", "APPROVE", "KNOWLEDGE_REVIEW", "REPORT_WRITE"] },
  { id: "SESSION_MANAGER", zh: "会话管理员", en: "Session Manager", capabilities: ["READ", "CREATE_TASK", "STOP", "RELEASE", "DEVICE_CONTROL", "EVIDENCE_RAW"] },
  { id: "ADMIN", zh: "超级管理员", en: "Super Admin", capabilities: ["*"] }
];

export function roleById(id) {
  return ROLES.find((role) => role.id === id) || ROLES[3];
}

export function getRoleId() {
  if (typeof window === "undefined" || !window.localStorage) return "ADMIN";
  const stored = window.localStorage.getItem(ROLE_KEY);
  return ROLES.some((role) => role.id === stored) ? stored : "ADMIN";
}

export function setRoleId(id) {
  if (typeof window !== "undefined" && window.localStorage) {
    window.localStorage.setItem(ROLE_KEY, roleById(id).id);
  }
}

export function currentRole() {
  return roleById(getRoleId());
}

export function can(capability) {
  if (!capability) return true;
  const role = currentRole();
  return role.capabilities.includes("*") || role.capabilities.includes(capability);
}

export function roleReason(capability) {
  const role = currentRole();
  return `角色 ${role.zh}/${role.en} 缺少 ${capability}；仅客户端演示，服务端仍 fail-closed。`;
}

const CAP_RULES = [
  { re: /请求原始访问|原始证据/, cap: "EVIDENCE_RAW" },
  { re: /导出/, cap: "EXPORT_AUDIT" },
  { re: /执行恢复演练|恢复演练/, cap: "SETTINGS" },
  { re: /批准|拒绝|请求审批/, cap: "APPROVE" },
  { re: /请求释放|释放/, cap: "RELEASE" },
  { re: /STOP|停止/, cap: "STOP" },
  { re: /隔离/, cap: "DEVICE_CONTROL" },
  { re: /审阅|推广|拒绝候选|应用到草案/, cap: "KNOWLEDGE_REVIEW" },
  { re: /保存草稿|生成修订种子|提交审阅|生成草案修订|保存设置/, cap: "CREATE_TASK" },
  { re: /更正|生成更正经版本/, cap: "REPORT_WRITE" },
  { re: /修改|分配角色/, cap: "SETTINGS" }
];

export function inferCapability(label) {
  const text = String(label || "").replace(/<[^>]+>/g, " ").trim();
  const rule = CAP_RULES.find((item) => item.re.test(text));
  return rule ? rule.cap : null;
}
