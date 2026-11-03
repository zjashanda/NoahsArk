import {
  badge,
  button,
  esc,
  genericState,
  kv,
  pageHeader,
  panel,
  stateBanners,
  stats,
  statusBadge,
  table,
  inlineNote
} from "../components.js";

function draftRows(view) {
  return view.world.intake.drafts.map((draft) => [
    `<a href="#/console/intake/${draft.id}"><span class="cell-primary">${draft.title}</span></a><div class="caption mono">${draft.id}</div>`,
    badge(draft.entry_mode, "plain"),
    statusBadge(draft.stage),
    String(draft.sources),
    draft.conflicts ? badge(String(draft.conflicts), "attention") : badge("0", "neutral"),
    draft.gaps ? badge(String(draft.gaps), "attention") : badge("0", "neutral"),
    draft.updated_at
  ]);
}

function list01(view) {
  const empty = view.flags.empty;
  const body = empty
    ? `<p class="muted small">暂无草稿。空态不代表已有任务；可从“新建任务”开始。</p>`
    : table({
      head: ["草稿", "入口", "阶段", "来源", "冲突", "缺口", "更新时间"],
      rows: draftRows(view)
    });
  return `
    ${pageHeader({
      eyebrow: `Intake · IN-01 · ${view.scenario.id}`,
      title: "Intake 草稿",
      description: "把会话、文件、表单三类入口归一为任务草稿。Intake 是唯一流程入口，但主路径由全局“新建任务”进入。",
      actions: button("新建任务", { href: "/console/intake/new", kind: "primary", icon: "plus" })
    })}
    ${stateBanners(view)}
    ${panel({
      title: "草稿队列",
      note: "冲突与缺口必须在生成修订种子前显式处理",
      body,
      flush: !empty
    })}
    ${inlineNote("<strong>G0 受理审阅</strong>：三入口来源、字段来源、冲突/缺口与 blocker owner 必须可见；不得静默择一来源，也不得未审阅即冻结。")}
  `;
}

const PROVENANCE = [
  ["任务标题", "TCL001 低温启动回归", "表单 · 入口", "抽取"],
  ["目标设备", "TCL 系列 · V038", "文件 · 规格说明", "继承"],
  ["采样次数", "40", "会话 · 需求澄清", "推导"],
  ["噪声类型", "2 类：稳态 + 突发", "文件 · 测试计划", "抽取"],
  ["验收口径", "误唤醒 ≤ 1 / 40", "会话 + 表单", "冲突"]
];

const SOURCES = [
  { id: "src-conv-01", kind: "CONVERSATION", label: "需求澄清会话", digest: "sha256:8a10…c3e2", collected_at: "2026-10-29 13:20 +08:00", status: "PARSED" },
  { id: "src-file-02", kind: "FILE", label: "低温测试计划 v2", digest: "sha256:12bb…9d71", collected_at: "2026-10-29 13:24 +08:00", status: "PARSED" },
  { id: "src-form-03", kind: "FORM", label: "任务申请表", digest: "sha256:71fe…0a44", collected_at: "2026-10-29 13:31 +08:00", status: "PARSED" }
];

function fixtureSourcesBody(view) {
  const disabledReason = view.flags.noPermission
    ? "当前角色无 TASK_AUTHORIZED；仅可查看摘要。"
    : "";
  return `
    <div class="grid-cards">
      <div class="card"><div class="spread"><span class="card-title">会话</span>${badge("CONVERSATION", "plain")}</div><p class="card-note">从澄清对话抽取意图、范围与验收口径。</p></div>
      <div class="card"><div class="spread"><span class="card-title">文件</span>${badge("FILE", "plain")}</div><p class="card-note">上传计划、规格或日志摘要；保留 digest，不展示原始绝对路径。</p></div>
      <div class="card"><div class="spread"><span class="card-title">表单</span>${badge("FORM", "action")}</div><p class="card-note">当前入口：结构化字段最完整，作为主来源。</p></div>
    </div>
    <div class="form-grid" style="margin-top:16px">
      <div class="field field-full"><label for="draft-title">任务标题</label><input class="input" id="draft-title" value="TCL001 低温启动回归"></div>
      <div class="field"><label for="draft-device">目标设备</label><input class="input" id="draft-device" value="TCL 系列 · V038"></div>
      <div class="field"><label for="draft-count">采样次数</label><input class="input" id="draft-count" value="40"></div>
      <div class="field field-full"><label for="draft-note">补充说明</label><textarea class="textarea" id="draft-note">低温 0–5°C，稳态与突发两类噪声；验收口径待裁决。</textarea></div>
    </div>
    <p class="caption" style="margin-top:8px">表单字段为 prototype-fixture，不会提交到服务端。</p>
    ${disabledReason ? `<p class="caption">${disabledReason}</p>` : ""}
  `;
}

function apiCreateForm(view) {
  const disabledReason = view.flags.noPermission
    ? "当前角色无 CREATE_TASK；可切换到具备该能力的演示角色后重试。"
    : "";
  const disabled = disabledReason
    ? ` disabled aria-disabled="true" title="${esc(disabledReason)}"`
    : "";
  return `
    <form class="form-grid" id="new-task-form" data-api-mode="true" aria-describedby="new-task-form-note">
      <div class="field field-full">
        <label for="new-task-title">任务标题</label>
        <input class="input" id="new-task-title" name="title" type="text" required maxlength="200" autocomplete="off" placeholder="例如：TCL001 低温启动回归">
      </div>
      <div class="field field-full">
        <label for="new-task-objective">任务目标</label>
        <textarea class="textarea" id="new-task-objective" name="objective" required maxlength="20000" placeholder="描述本次任务要验证的目标与验收口径。"></textarea>
        <span class="hint">Supervisor 使用本字段作为执行指令。</span>
      </div>
      <div class="field">
        <label for="new-task-entry-mode">入口模式</label>
        <select class="select" id="new-task-entry-mode" name="entry_mode">
          <option value="form" selected>表单 form</option>
          <option value="conversation">会话 conversation</option>
          <option value="file">文件 file</option>
          <option value="spreadsheet">表格 spreadsheet</option>
          <option value="template">模板 template</option>
        </select>
      </div>
      <div class="field">
        <label for="new-task-lead-agent">负责 Agent</label>
        <input class="input" id="new-task-lead-agent" name="lead_agent_id" type="text" value="agt-planner" maxlength="120" autocomplete="off">
        <span class="hint">Agent display_id，默认 agt-planner（规划 Agent）。</span>
      </div>
      <div class="field field-full">
        <label for="new-task-prompt">Supervisor 提示词</label>
        <textarea class="textarea" id="new-task-prompt" name="prompt" required maxlength="200000">Reply with the single word PONG and nothing else.</textarea>
        <span class="hint">绑定只保留提示词 digest 与字节数；执行指令取“任务目标”字段。</span>
      </div>
      <div class="field-full">
        <div class="row">
          <button class="btn btn-primary" type="submit" data-label="创建任务"${disabled}>创建任务</button>
          ${disabledReason ? `<span class="btn-reason">${esc(disabledReason)}</span>` : ""}
        </div>
        <p class="caption" id="new-task-form-note" style="margin-top:8px">提交使用当前演示角色请求头；创建需要 CREATE_TASK。失败时保留输入并显示服务端状态/代码/消息，成功后进入任务详情查看 Supervisor。</p>
        <div class="form-feedback" id="new-task-feedback" role="alert" aria-live="assertive" hidden></div>
      </div>
    </form>
  `;
}

function wizardBody(view) {
  const apiMode = Boolean(view.meta && view.meta.server_authoritative);
  const disabledReason = view.flags.noPermission
    ? "当前角色无 TASK_AUTHORIZED；仅可查看摘要。"
    : "";
  return `
    ${stats([
      { label: "步骤 1", value: "来源", note: "会话 / 文件 / 表单" },
      { label: "步骤 2", value: "澄清", note: "字段来源 · 冲突 · 缺口" },
      { label: "步骤 3", value: "修订种子", note: "生成可审阅草稿" }
    ])}
    <div class="section">
      ${panel({
        title: "1 · 来源",
        note: apiMode
          ? "真实写入：POST /api/v1/tasks；成功后由控制面绑定 Supervisor 会话"
          : "三入口共用归一化管线；不展示代理内部推理或未脱敏原文",
        body: apiMode ? apiCreateForm(view) : fixtureSourcesBody(view)
      })}
    </div>
    <div class="section">
      ${panel({
        title: "2 · 澄清",
        note: "每个字段标明抽取 / 继承 / 推导；冲突不得静默择一",
        body: `
          ${table({ head: ["字段", "值", "来源", "标记"], rows: PROVENANCE.map(([field, value, source, marker]) => [
            `<span class="cell-primary">${field}</span>`, value, source, badge(marker, marker === "冲突" ? "attention" : "plain")
          ]) })}
          <div class="layout-2-even" style="margin-top:16px">
            <div>
              <h3 class="card-title">冲突（1）</h3>
              <div class="checks" style="margin-top:8px">
                <div class="check-item is-missing"><div><strong>采样次数</strong><span class="check-note">表单写 30 次，会话写 40 次；未静默择一，需提交者裁决。</span></div></div>
                <div class="check-item is-missing"><div><strong>适用版本</strong><span class="check-note">文件写 V037，设备当前 V038；继承前需确认。</span></div></div>
              </div>
            </div>
            <div>
              <h3 class="card-title">缺口（2）</h3>
              <div class="checks" style="margin-top:8px">
                <div class="check-item is-unknown"><div><strong>参考音频 digest</strong><span class="check-note">未提供，无法声明 expected。</span></div></div>
                <div class="check-item is-unknown"><div><strong>低温范围上限</strong><span class="check-note">仅写“低温”，未给出边界。</span></div></div>
              </div>
            </div>
          </div>
        `
      })}
    </div>
    <div class="section">
      ${panel({
        title: "3 · 修订种子",
        note: apiMode ? "本步骤仍为原型预览；真实任务提交后进入任务详情" : "生成后仍为 DRAFT；进入冻结需 G0/G1",
        body: `
          ${kv([
            ["建议 task_id", `<span class="mono">tsk-voice-002</span>`],
            ["阶段", statusBadge("DRAFT")],
            ["来源归一化 digest", `<span class="digest">sha256:0f31c2…e8a7</span>`],
            ["预计范围", "40 次采样 · 2 类噪声 · 低温 0–5°C"],
            ["待处理", `${badge("2 冲突", "attention")} ${badge("2 缺口", "attention")}`]
          ])}
          <div class="row" style="margin-top:16px">
            ${button("保存草稿", { icon: "file", disabledReason })}
            ${button("生成修订种子", { kind: "primary", icon: "plus", disabledReason })}
            ${button("提交审阅", { icon: "arrow", disabledReason })}
          </div>
          <p class="caption" style="margin-top:8px">${apiMode ? "真实创建入口为第 1 步；本步骤按钮仍为 prototype mock。" : "所有按钮均为 prototype mock；冲突未处理前不得生成可冻结修订。"}</p>
        `
      })}
    </div>
    ${inlineNote("<strong>G0 受理审阅</strong>：冲突不得静默择一；未审阅不得冻结。跨任务无关系默认 DENY。")}
  `;
}

function detailBody(view, draft) {
  const disabledReason = view.flags.noPermission
    ? "当前角色无 TASK_AUTHORIZED；仅可查看摘要。"
    : "";
  return `
    ${pageHeader({
      eyebrow: `Intake · IN-03 · ${view.scenario.id}`,
      title: draft.title,
      description: `草稿 <span class="mono">${draft.id}</span> · 入口 ${draft.entry_mode} · ${draft.sources} 个来源 · 归一化后可生成修订种子。`,
      actions: badge(draft.stage, "neutral")
    })}
    ${stateBanners(view)}
    ${panel({
      title: "来源与 digest",
      note: "原始材料不进入默认载荷；只显示引用与摘要",
      body: table({
        head: ["来源", "类型", "digest", "采集时间", "状态"],
        rows: SOURCES.map((source) => [
          `<span class="cell-primary">${source.label}</span><div class="caption mono">${source.id}</div>`,
          badge(source.kind, "plain"),
          `<span class="digest">${source.digest}</span>`,
          source.collected_at,
          badge(source.status, "neutral")
        ])
      }),
      flush: true
    })}
    ${panel({
      title: "字段来源与冲突",
      note: "抽取 / 继承 / 推导逐项可见",
      body: `
        ${table({ head: ["字段", "值", "来源", "标记"], rows: PROVENANCE.map(([field, value, source, marker]) => [
          `<span class="cell-primary">${field}</span>`, value, source, badge(marker, marker === "冲突" ? "attention" : "plain")
        ]) })}
        <div class="checks" style="margin-top:12px">
          <div class="check-item is-missing"><div><strong>冲突未裁决</strong><span class="check-note">采样次数 30 vs 40；提交者必须在生成种子前选择。</span></div></div>
          <div class="check-item is-unknown"><div><strong>缺口未补齐</strong><span class="check-note">参考音频 digest、低温上限。</span></div></div>
        </div>
        <p class="caption" style="margin-top:8px">normalization_digest: <span class="mono">sha256:0f31c2…e8a7</span></p>
      `
    })}
    ${panel({
      title: "修订种子预览",
      note: "生成后仍为草稿，不自动冻结",
      body: `
        ${kv([
          ["建议任务", "TCL001 低温启动回归"],
          ["阶段", statusBadge("DRAFT")],
          ["修订", `<span class="mono">R-0</span> · seed`],
          ["冻结范围", "40 次采样 · 2 类噪声"],
          ["审批", badge("NOT REQUESTED", "neutral")],
          ["blocker.owner", "Submitter · 需求澄清"]
        ])}
        <div class="row" style="margin-top:16px">
          ${button("生成修订种子", { kind: "primary", icon: "plus", disabledReason })}
          ${button("丢弃草稿", { kind: "danger", icon: "x", disabledReason })}
        </div>
      `
    })}
    ${inlineNote("生成修订种子只产生可审阅草稿；冻结批准（G1）必须由具备 APPROVE_TASK 的审批者完成。")}
  `;
}

export function render({ route, params, view }) {
  const generic = genericState(view, "Intake");
  const path = params.draftId;
  if (path) {
    const draft = view.world.intake.drafts.find((item) => item.id === path) || view.world.intake.drafts[0];
    if (generic) {
      return pageHeader({ eyebrow: `Intake · IN-03 · ${view.scenario.id}`, title: draft.title, description: "草稿审阅" }) + generic;
    }
    return detailBody(view, draft);
  }
  if (route.id === "IN-02") {
    const apiMode = Boolean(view.meta && view.meta.server_authoritative);
    const description = apiMode
      ? "创建真实任务：填写标题、目标与提示词，提交后由控制面绑定 Supervisor 并进入任务详情。"
      : "三步向导把会话、文件与表单归一为可审阅草稿；任何冲突或缺口必须显式处理。";
    if (generic) {
      return pageHeader({ eyebrow: `Intake · IN-02 · ${view.scenario.id}`, title: "新建任务", description }) + generic;
    }
    return `
      ${pageHeader({
        eyebrow: `Intake · IN-02 · ${view.scenario.id}`,
        title: "新建任务",
        description,
        actions: button("返回草稿列表", { href: "/console/intake", kind: "quiet", icon: "arrow" })
      })}
      ${stateBanners(view)}
      ${wizardBody(view)}
    `;
  }
  return list01(view);
}
