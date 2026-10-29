// Lightweight bilingual presentation layer. The source render is Chinese;
// English mode translates UI chrome, labels, controls and semantic notices.
// Mock fixture values (IDs, titles, narrative data) remain as authored.

const LANG_KEY = "naa-lang";

export const LANGS = [
  { id: "zh", label: "中文", short: "中" },
  { id: "en", label: "English", short: "EN" }
];

export function getLang() {
  if (typeof window === "undefined" || !window.localStorage) return "zh";
  return window.localStorage.getItem(LANG_KEY) === "en" ? "en" : "zh";
}

export function setLang(lang) {
  if (typeof window !== "undefined" && window.localStorage) {
    window.localStorage.setItem(LANG_KEY, lang === "en" ? "en" : "zh");
  }
}

const DICT = [
  ["跳到主内容", "Skip to main content"],
  ["主导航", "Main navigation"],
  ["工作区", "Workspace"],
  ["状态预览", "State preview"],
  ["筛选导航（按名称）", "Filter navigation by name"],
  ["筛选导航", "Filter navigation"],
  ["打开导航", "Open navigation"],
  ["关闭导航", "Close navigation"],
  ["更多导航与设置", "More navigation and settings"],
  ["更多菜单", "More menu"],
  ["预览设置", "Preview settings"],
  ["切换浅色/深色", "Toggle light/dark"],
  ["切换浅色或深色主题", "Toggle light or dark theme"],
  ["切换到浅色主题", "Switch to light theme"],
  ["切换浅色主题", "Switch to light theme"],
  ["切换到深色主题", "Switch to dark theme"],
  ["切换深色主题", "Switch to dark theme"],
  ["新建任务", "New task"],
  ["连接 · 实时", "Connection · Live"],
  ["连接 · 离线", "Connection · Offline"],
  ["连接 · 降级", "Connection · Degraded"],
  ["连接 · 未知", "Connection · Unknown"],
  ["待 STOP", "Pending STOP"],
  ["对账中", "Reconciling"],
  ["项需要处理", "items need attention"],
  ["演示控制", "Demo controls"],
  ["客户端角色演示，不构成访问控制。", "Client-side role demo; not access control."],
  ["候选原型，非冻结，不代表真实执行。", "Candidate prototype, not frozen, not real execution."],
  ["确认操作", "Confirm action"],
  ["确认危险动作", "Confirm dangerous action"],
  ["请确认前置条件与影响范围。", "Confirm the preconditions and impact."],
  ["取消", "Cancel"],
  ["确认", "Confirm"],
  ["关闭", "Close"],
  ["移动导航", "Mobile navigation"],
  ["语言", "Language"],
  ["角色", "Role"],
  ["状态", "State"],
  ["观察者 · Observer", "Observer"],
  ["审批者 · Approver", "Approver"],
  ["会话管理员 · Session Manager", "Session Manager"],
  ["超级管理员 · Super Admin", "Super Admin"],
  ["观察者", "Observer"],
  ["审批者", "Approver"],
  ["会话管理员", "Session Manager"],
  ["超级管理员", "Super Admin"],

  ["平台健康与需要我处理", "Platform health and what needs me"],
  ["需求受理", "Intake"],
  ["任务与修订", "Tasks and revisions"],
  ["运行与 Attempt", "Runs and attempts"],
  ["证据索引", "Evidence index"],
  ["判定", "Verdict"],
  ["设备与节点", "Devices and nodes"],
  ["报告与交付", "Reports and delivery"],
  ["知识库", "Knowledge"],
  ["运行时与工具链", "Runtime and toolchain"],
  ["Agent 注册表", "Agent registry"],
  ["评审会话", "Review sessions"],
  ["恢复与对账", "Recovery and reconciliation"],
  ["设置与访问", "Settings and access"],
  ["访问与角色", "Access and roles"],
  ["通知", "Notifications"],
  ["保留与删除", "Retention and deletion"],
  ["模型绑定", "Model bindings"],
  ["工具链锁定", "Toolchain locks"],
  ["草稿审阅", "Draft review"],
  ["任务详情", "Task detail"],

  ["只呈现异常、待决断、离线、对账中与隔离设备，不做全量监控墙。完整清单下钻到任务、运行与设备。", "Shows only exceptions, decisions, offline, reconciling and quarantined devices; not a full monitoring wall. Drill into tasks, runs and devices."],
  ["把会话、文件、表单三类入口归一为任务草稿。Intake 是唯一流程入口，但主路径由全局“新建任务”进入。", "Normalizes conversation, file and form entries into task drafts. Intake is the only flow entry, while the global “New task” action is the main path."],
  ["三步向导把会话、文件与表单归一为可审阅草稿；任何冲突或缺口必须显式处理。", "A three-step wizard normalizes conversation, files and forms into a reviewable draft; every conflict or gap must be handled explicitly."],
  ["三步向导：来源 → 澄清 → 修订种子", "Three-step wizard: sources → clarification → revision seed"],
  ["以持续运营对象组织任务；详情包含 8 个固定子视图、修订谱系与门禁。", "Tasks are organized around operating objects; details include 8 fixed subviews, revision lineage and gates."],
  ["显示在跑、停止、断线、待对账的运行；mode 与正式分母严格分离。", "Shows running, stopped, disconnected and reconciling runs; mode and the formal denominator stay strictly separate."],
  ["浏览证据索引与 manifest 元数据；原始内容按 EVIDENCE_AUTHORIZED 二次鉴权，允许与拒绝均审计。", "Browses evidence indexes and manifest metadata; raw content requires EVIDENCE_AUTHORIZED and both allow and deny are audited."],
  ["只显示五轴与 fail-closed 原因；正式 PASS 仅允许唯一精确组合。", "Shows the five axes and fail-closed reasons; formal PASS allows only the single exact tuple."],
  ["回答在哪里执行、谁占用、能否释放。节点心跳、会话、端点、spool 与设备池状态分开显示。", "Answers where execution happens, who occupies it and whether it can be released. Heartbeat, session, endpoints, spool and pool state stay separate."],
  ["冻结报告包含 14 章节、分母口径、四类记录分离与披露级别。冻结后不可原地修改。", "A frozen report contains 14 sections, denominator basis, four separated record classes and disclosure level. Frozen reports are immutable in place."],
  ["检索已批准知识；候选与条目分开，冲突与陈旧状态在列表行可见。", "Searches approved knowledge; candidates and items are separated, and conflicts or stale states are visible in the list row."],
  ["候选必须人工审阅并具备目标库权限；不存在 PROPOSED → PROMOTED 捷径。", "Candidates require human review and target-library permission; there is no PROPOSED → PROMOTED shortcut."],
  ["回答谁在执行、绑定是否锁定、哪里发生漂移。写入能力等待 Q-09。", "Answers who executes, whether bindings are locked and where drift occurs. Write capability awaits Q-09."],
  ["展示 lock 与 drift；任何写入动作等待 Q-09 访问级别裁决。", "Shows locks and drift; every write action awaits the Q-09 access decision."],
  ["回答谁负责什么、绑定是否锁定；治理写入等待 Q-09。", "Answers who owns what and whether bindings are locked; governance writes await Q-09."],
  ["呈现评审共识与未决风险；评审结果不替代 Linux 判定或人工审批。", "Shows review consensus and open risks; review results do not replace Linux verdicts or human approval."],
  ["回答谁做了什么、允许或拒绝、before/after 与哈希链；审计不可编辑。", "Answers who did what, allow or deny, before/after and the hash chain; audit is immutable."],
  ["固定恢复顺序与 STOP-first 六步；未演练不得声称 RPO/RTO。", "Fixes the recovery order and the six STOP-first steps; no RPO/RTO claim without a drill."],
  ["配置角色、关系、通知与保留策略；永不显示密钥或真实凭据。", "Configures roles, relations, notifications and retention; never shows keys or real credentials."],
  ["展示角色、任务关系与能力映射；策略版本与生效时间可见。", "Shows roles, task relations and capability mapping; policy version and effective time are visible."],
  ["显示投递状态与死信数量；目标地址脱敏，不含凭据。", "Shows delivery state and dead-letter counts; destinations are masked and contain no credentials."],
  ["展示保留策略、版本与生效时间；危险变更需要二次确认并写入审计。", "Shows retention policies, versions and effective time; dangerous changes need confirmation and are audited."],

  ["需要我处理", "Needs my attention"],
  ["运行中", "Running"],
  ["平台健康", "Platform health"],
  ["全局指示器", "Global indicators"],
  ["任务快照", "Task snapshot"],
  ["待 STOP 队列", "Pending STOP queue"],
  ["对账范围", "Reconciliation scope"],
  ["隔离设备", "Quarantined devices"],
  ["最近审计", "Recent audit"],
  ["关键事实", "Key facts"],
  ["五轴状态", "Five-axis state"],
  ["门禁 G0–G7", "Gates G0–G7"],
  ["冻结与审批", "Freeze and approval"],
  ["修订谱系", "Revision lineage"],
  ["计划与用例", "Plan and cases"],
  ["运行矩阵", "Run matrix"],
  ["证据台账", "Evidence ledger"],
  ["判定与门禁", "Verdict and gates"],
  ["实时运行", "Live run"],
  ["相关知识", "Related knowledge"],
  ["设备池", "Device pool"],
  ["节点", "Nodes"],
  ["租约与占用", "Lease and occupancy"],
  ["释放前置", "Release preconditions"],
  ["报告章节", "Report sections"],
  ["分母与记录分离", "Denominator and record separation"],
  ["披露范围", "Disclosure scope"],
  ["候选队列", "Candidate queue"],
  ["已批准知识", "Approved knowledge"],
  ["工具链 lock", "Toolchain locks"],
  ["漂移", "Drift"],
  ["审计事件", "Audit events"],
  ["哈希链", "Hash chain"],
  ["恢复六步", "Six recovery steps"],
  ["备份演练", "Backup drill"],
  ["角色与关系", "Roles and relations"],
  ["通知投递", "Notification delivery"],
  ["保留策略", "Retention policies"],

  ["任务", "Task"],
  ["阶段", "Stage"],
  ["版本", "Version"],
  ["来源", "Source"],
  ["对象", "Object"],
  ["更新时间", "Updated"],
  ["当前修订", "Current revision"],
  ["采样次数", "Samples"],
  ["期望", "Expected"],
  ["已接收", "Received"],
  ["已核验", "Verified"],
  ["未核验", "Not verified"],
  ["证据项", "Evidence item"],
  ["大小 / digest", "Size / digest"],
  ["采集时间", "Collected at"],
  ["访问级别", "Access level"],
  ["执行", "Execution"],
  ["有效性", "Validity"],
  ["业务判定", "Business verdict"],
  ["证据", "Evidence"],
  ["复核", "Verification"],
  ["模式", "Mode"],
  ["生命周期", "Lifecycle"],
  ["正式分母", "Formal denominator"],
  ["尝试", "Attempts"],
  ["操作", "Action"],
  ["范围", "Scope"],
  ["能力", "Capability"],
  ["通道", "Channel"],
  ["目标", "Target"],
  ["投递", "Delivery"],
  ["死信", "Dead letters"],
  ["策略", "Policy"],
  ["生效时间", "Effective at"],

  ["返回列表", "Back to list"],
  ["派生新修订", "Derive new revision"],
  ["请求审批", "Request approval"],
  ["批准", "Approve"],
  ["拒绝", "Reject"],
  ["请求 STOP", "Request STOP"],
  ["请求释放", "Request release"],
  ["隔离设备", "Quarantine device"],
  ["导出审计", "Export audit"],
  ["导出摘要", "Export summary"],
  ["请求原始访问", "Request raw access"],
  ["保存草稿", "Save draft"],
  ["生成修订种子", "Generate revision seed"],
  ["提交审阅", "Submit for review"],
  ["生成草案修订", "Create draft revision"],
  ["审阅选中候选", "Review selected candidate"],
  ["拒绝候选", "Reject candidate"],
  ["应用到草案修订", "Apply to draft revision"],
  ["生成更正经版本", "Create correction version"],
  ["执行恢复演练", "Run recovery drill"],
  ["修改绑定", "Edit binding"],
  ["分配角色", "Assign role"],
  ["重试", "Retry"],
  ["查看全部", "View all"],
  ["查看", "View"],
  ["打开", "Open"],
  ["复制 digest", "Copy digest"],
  ["筛选", "Filter"],
  ["清空筛选", "Clear filters"],
  ["修改", "Edit"],

  ["已完成", "Completed"],
  ["已阻断", "Blocked"],
  ["未知", "Unknown"],
  ["陈旧", "Stale"],
  ["离线", "Offline"],
  ["隔离", "Quarantined"],
  ["排空中", "Draining"],
  ["待处理", "Pending"],
  ["通过", "Passed"],
  ["失败", "Failed"],
  ["部分", "Partial"],

  ["任务在 G3 资源资格被阻塞，责任方为资源调度 · Session Manager。解除前禁止派发或标记通过。", "The task is blocked at G3 resource eligibility; the owner is Resource Scheduling · Session Manager. No dispatch or pass marking before unblocking."],
  ["通信离线，但执行仍在 RUNNING、设备仍 OCCUPIED、执行许可 GRANTED。离线不等于停止、空闲或可重派。", "Communication is OFFLINE, but execution is still RUNNING, the device is still OCCUPIED and the permit is GRANTED. Offline does not mean stopped, idle or reassignable."],
  ["投影已陈旧：", "Projection is stale: "],
  ["最后权威更新", "last authoritative update"],
  ["最后已知活动", "last known activity"],
  ["陈旧徽章只追加，不改写执行或占用。", "The stale badge is additive and does not rewrite execution or occupancy."],
  ["存在待送达 STOP。固定顺序：处理待 STOP → 停止后续动作 → 补传 → 去重 → 对账 → 恢复领取。对账完成前保持占用。", "A STOP is pending delivery. Fixed order: handle pending STOP → stop subsequent actions → upload → dedupe → reconcile → resume claiming. Keep occupancy until reconciliation completes."],
  ["设备已隔离且仍被占用；释放前置未满足，必须人工恢复并完成清理回执。", "The device is quarantined and still occupied; release preconditions are unmet. Manual recovery and a cleanup receipt are required."],
  ["设备进入排空：不再接受新任务，已有运行继续，直到停止与对账完成。", "The device is draining: no new tasks, existing runs continue until stop and reconciliation complete."],
  ["进度模式为 INDETERMINATE；总量未知，不显示 0%、99% 或阶段序号百分比。", "Progress mode is INDETERMINATE; total is unknown, so no 0%, 99% or stage-index percentage is shown."],
  ["证据已接收但未全部核验；received 不等于 verified，业务 PASS 也不能形成正式 PASS。", "Evidence was received but not fully verified; received is not verified, and a business PASS cannot become a formal PASS."],
  ["当前角色只能查看只读摘要；受限动作保留可见但禁用，并显示原因。客户端隐藏不构成访问控制。", "This role can only view the read-only summary; restricted actions remain visible but disabled with a reason. Client-side hiding is not access control."],
  ["当前五轴不满足正式 PASS 的唯一精确组合；判定为「未形成正式判定」。 正式 PASS 仅允许", "The five axes do not match the single exact formal-PASS tuple; verdict is “no formal verdict formed.” Formal PASS requires only"],
  ["业务判定为 PASS，但证据未 COMPLETE，因此不可显示正式 PASS。", "Business verdict is PASS, but evidence is not COMPLETE, so formal PASS cannot be shown."],
  ["正式 PASS · 五轴精确满足", "Formal PASS · five axes exactly satisfied"],
  ["不可正式 PASS", "Not eligible for formal PASS"],
  ["未形成正式判定", "No formal verdict formed"],
  ["非正式判定", "Informal verdict"],

  ["暂无记录", "No records"],
  ["当前筛选范围没有可显示的投影。空态不代表平台无数据。", "No projection matches the current filter. Empty does not mean the platform has no data."],
  ["正在加载投影", "Loading projection"],
  ["等待 Linux 控制面返回只读快照；不推断成功。", "Waiting for a read-only snapshot from the Linux control plane; success is not inferred."],
  ["投影加载失败", "Projection failed to load"],
  ["保留错误状态和重试入口，不把失败写成空数据。", "Keeps the error state and retry entry; failure is not written as empty data."],
  ["仅可查看摘要", "Summary-only access"],
  ["原始证据需要 EVIDENCE_AUTHORIZED；拒绝访问也会写入审计。", "Raw evidence requires EVIDENCE_AUTHORIZED; denials are also audited."],
  ["路由不存在", "Route not found"],
  ["未登记的路由", "Unregistered route"],
  ["未登记入口不会获得隐式页面；旧 /aitest/* 仅作实现期兼容别名。", "Unregistered entries get no implicit page; legacy /aitest/* is only an implementation alias."],

  ["仅计数模式显示百分比，不作为完成度承诺", "Percent is shown only in COUNTS mode and is not a completion promise"],
  ["未知总量，禁止显示百分比", "Unknown total; percentages are forbidden"],
  ["定性阶段", "Qualitative stage"],
  ["服务端未提供已批准分母", "No approved denominator from the server"],
  ["本地停止已确认", "Local stop confirmed"],
  ["安全清理完成", "Safe cleanup complete"],
  ["占用已对账", "Occupancy reconciled"],
  ["等待节点停止回执", "Waiting for node stop receipt"],
  ["清理回执已记录", "Cleanup receipt recorded"],
  ["缺少 cleanup_receipt，保持占用", "Missing cleanup_receipt; occupancy is retained"],
  ["对账完成前不得释放或重派", "No release or reassignment before reconciliation"],
  ["lease / epoch / occupancy 已对账", "lease / epoch / occupancy reconciled"],
  ["释放仅取决于三项前置与 R-05；释放不等于 PASS，也不等待最终判定。", "Release depends only on the three preconditions and R-05; release is not PASS and does not wait for the final verdict."],
  ["节点观察事实 · node_observed_*", "Node-observed facts · node_observed_*"],
  ["Linux 平台判定", "Linux platform verdict"],
  ["used_for_decision=false · 仅回传事实，不写平台判定。", "used_for_decision=false · facts only; no platform verdict is written."],
  ["唯一权威写入方；节点回执不得渲染为 business_verdict 或 verification_status。", "The sole authoritative writer; node receipts must not render as business_verdict or verification_status."],
  ["五轴不折叠", "Five axes are never collapsed"],
  ["三列独立：expected 是要求，received 是到达，verified 是复核结果。", "Three independent columns: expected is the requirement, received is arrival, verified is the review result."],
  ["received 与 verified 分离：已接收不等于已核验；缺失项 fail-closed。", "received and verified are separate: received is not verified; missing items fail closed."],
  ["门禁 PASSED 不等于业务 PASS；G4 烟测永不进入正式分母。", "A gate PASSED is not a business PASS; G4 smoke never enters the formal denominator."],
  ["Q-09 未裁决：只读候选 TASK_AUTHORIZED、写入候选 ADMIN_ONLY；裁决前不得实现写入。", "Q-09 undecided: candidate read TASK_AUTHORIZED, candidate write ADMIN_ONLY; no write implementation before the decision."],
  ["Q-09 未裁决：只读候选 TASK_AUTHORIZED、写入候选 ADMIN_ONLY；裁决前不得实现治理写入。", "Q-09 undecided: candidate read TASK_AUTHORIZED, candidate write ADMIN_ONLY; no governance write before the decision."],
  ["仅 SUPER_ADMIN 可见与可写；永不显示私钥、证书、令牌或真实凭据。", "Visible and writable only by SUPER_ADMIN; never show private keys, certificates, tokens or real credentials."],
  ["角色变更写入 ROLE_CHANGE 审计；策略版本与生效时间必须可见。", "Role changes write ROLE_CHANGE audit; policy version and effective time must be visible."],
  ["跨任务导出需要 ADMIN_ONLY + EXPORT_AUDIT，且导出本身产生审计。", "Cross-task export requires ADMIN_ONLY + EXPORT_AUDIT; the export itself is audited."],
  ["客户端权限演示，不构成访问控制。", "Client-side permission demo; not access control."],
  ["客户端权限演示，不构成访问控制", "Client-side permission demo; not access control"]
];

const ORDERED = [...DICT].sort((a, b) => b[0].length - a[0].length);
const SKIP_SELECTOR = ".mono, .digest, .scenario-chip, code, pre, [data-no-i18n], .ribbon";

function cleanup(text) {
  return text
    .replaceAll("。", ". ")
    .replaceAll("；", "; ")
    .replaceAll("，", ", ")
    .replaceAll("：", ": ")
    .replaceAll("（", " (")
    .replaceAll("）", ") ")
    .replaceAll("、", ", ")
    .replaceAll("「", '"')
    .replaceAll("」", '"')
    .replace(/[ \t]{2,}/g, " ");
}

export function translateString(text) {
  if (getLang() !== "en" || !text) return text;
  let out = String(text);
  for (const [zh, en] of ORDERED) {
    if (out.includes(zh)) out = out.replaceAll(zh, en);
  }
  return cleanup(out);
}

export function t(text) {
  return translateString(text);
}

function shouldSkip(node) {
  const el = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
  return Boolean(el && el.closest(SKIP_SELECTOR));
}

function translateAttributes(root) {
  const attrs = ["aria-label", "title", "placeholder", "alt"];
  root.querySelectorAll("*").forEach((el) => {
    if (el.closest(SKIP_SELECTOR)) return;
    for (const attr of attrs) {
      if (el.hasAttribute(attr)) {
        const value = el.getAttribute(attr);
        const next = translateString(value);
        if (next !== value) el.setAttribute(attr, next);
      }
    }
  });
}

export function applyLanguage(root = document.body) {
  const lang = getLang();
  document.documentElement.lang = lang === "en" ? "en" : "zh-CN";
  if (!root || lang !== "en") return;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  for (const node of nodes) {
    if (shouldSkip(node) || !/[\u4e00-\u9fff]/.test(node.nodeValue)) continue;
    const next = translateString(node.nodeValue);
    if (next !== node.nodeValue) node.nodeValue = next;
  }
  translateAttributes(root);
}
