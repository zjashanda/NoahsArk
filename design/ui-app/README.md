# NoahsArk Console — Cloudline Candidate UI

**CANDIDATE UI · PROTOTYPE · NOT FROZEN · MOCK DATA**

静态、可交互、无依赖的 Phase 1 候选原型，用于评审 NoahsArk AI 资深测试工程师平台的完整 Web 信息架构。它不是后端实现、验收证据或 UI 冻结件；所有数据来自本地 fixture，`server_authoritative=false`。

## 运行

```bash
node checks/serve.mjs 8100
```

`checks/serve.mjs` 同时提供静态文件与同源 `/api/v1` 代理（默认转发到
`127.0.0.1:8000`，可用 `NAA_API_UPSTREAM` 覆盖），浏览器不会触碰跨域。
纯静态查看也可继续使用：

```bash
python3 -m http.server 8100 --bind 0.0.0.0 -d design/ui-app
```

- 本机：`http://127.0.0.1:8100/`
- 三方向对比 Demo 仍使用 8099：`python3 -m http.server 8099 --bind 0.0.0.0 -d design/ui-demos`

## 数据源

默认是本地 fixture（`server_authoritative=false`）。控制面只读 API 需要显式开启：

- `?api=1` 开启 API，`?api=0` 强制 fixture；
- 侧栏 / 抽屉 / More 面板中的“数据源”选择器会写入 `localStorage.naa-api`；
- API 失败时显示显式错误面板（重试 / 切换到 fixture），不会静默回退；
- 五轴、expected/received/verified 与 release 前置保持独立，
  `NOT_EVALUATED` / `NOT_RUN` 不会被改写成 PASS。

## 范围

- 12 个区域、39 条规范路由，任务详情 8 个子视图。
- 四条关键旅程：Intake→审批→门禁、Task→Run→Attempt、离线 STOP-first 对账、证据→Linux 判定→报告。
- 五轴独立显示；只有 `COMPLETED / VALID / PASS / COMPLETE / PASS` 显示正式 PASS。
- `expected / received / verified` 三列分离；通信、占用、执行许可、执行状态、新鲜度分离。
- 释放三前置分离；`OFFLINE + RUNNING + OCCUPIED + GRANTED` 允许同时存在。
- 浅色/深色、四档响应式、键盘焦点、reduced motion、强制颜色基础兼容。

## 状态预览

顶栏“状态预览”提供 fixture 场景：

| ID | 场景 |
|---|---|
| FX-01 | 正常候选流程 |
| FX-02 | blocked |
| FX-03 | stale + running |
| FX-04 | offline + running + occupied + granted |
| FX-05 | reconciling + pending STOP |
| FX-06 | unknown-progress |
| FX-07 | partial evidence + business PASS |
| FX-08 | quarantined + occupied |
| FX-09 | draining + running |
| FX-10 | no-permission |
| FX-11E | empty |
| FX-11L | loading |
| FX-11X | error |
| FX-12 | complete formal PASS（唯一正式 PASS 正例） |

场景只改变投影状态，不改写权威事实，也不代表任何真实执行。

## 结构

```text
index.html, favicon.svg
styles/   tokens, base, shell, components
src/      app, router, route-manifest, shell, fixtures, semantics, icons, components
src/pages mission, intake, tasks, runs, evidence, devices, reports, knowledge, runtime, agents, audit, settings
checks/   contract-check.mjs, smoke-check.mjs
```

## 边界

- fixture 模式不连接后端、不写数据库、不发起远程请求、不加载外部字体或 CDN；`?api=1` 只读调用控制面 `/api/v1`。
- 仍不写数据库、不发写请求；所有写按钮均为标注的 mock 交互。
- RT/AG 的写入能力仍待 Q-09 裁决，界面只读并显示禁用原因。
- 本目录不得替代 `design/ui-demos/` 的三方向对比演示。

## 验证

```bash
node checks/contract-check.mjs
node checks/smoke-check.mjs
git diff --check
```
