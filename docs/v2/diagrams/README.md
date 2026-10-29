# 流程图渲染产物

> **历史说明（历史/已取代 2026-10-28，P0-03）**：本目录是旧方案 `SOLUTION.md` 第 5 节的渲染产物，保留用于追溯。图中的旧终态集合与门禁口径已被五轴判定 + 执行/设备/证据/最终判定分离取代；当前流程以 [NoahsArk 平台交付总计划](../../../.omo/plans/noahsark-platform-delivery.md) 和 [openspec 与 docs/v2 规范同步记录](../../delivery/openspec-v2-sync.md) 为准，Phase 1/3 将重绘。

本目录保存 `../SOLUTION.md` 第 5 节两张 Mermaid 图的源文件与渲染产物。

| 文件 | 内容 | 来源 | 尺寸 |
|---|---|---|---|
| `main-workflow.mmd` | 图 5-1：12 个阶段、6 个阶段带（`flowchart LR`） | `SOLUTION.md` 5.1.1 | 12 节点 / 11 边 |
| `main-workflow.svg` | 图 5-1 矢量渲染 | 由 `main-workflow.mmd` 生成 | 1078 × 318 |
| `main-workflow.png` | 图 5-1 位图（2x） | 由 `main-workflow.mmd` 生成 | 1568 × 464 |
| `decision-boundaries.mmd` | 图 5-2：判定与失败边界（`flowchart TD`） | `SOLUTION.md` 5.1.2 | 15 节点 / 17 边 |
| `decision-boundaries.svg` | 图 5-2 矢量渲染 | 由 `decision-boundaries.mmd` 生成 | 944 × 1474 |
| `decision-boundaries.png` | 图 5-2 位图（2x） | 由 `decision-boundaries.mmd` 生成 | 1568 × 2450 |

## 唯一真相

Mermaid 代码块以 `../SOLUTION.md` 为准，本目录的 `.mmd` 是从文档代码块抽取的副本，便于离线渲染与校验。修改图示时先改文档，再从文档重新抽取并覆盖 `.mmd`，保证两者逐字一致。

## 渲染命令

```powershell
$env:PUPPETEER_EXECUTABLE_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"

npx -y @mermaid-js/mermaid-cli@11.4.2 `
  -i docs/v2/diagrams/main-workflow.mmd `
  -o docs/v2/diagrams/main-workflow.svg -b white

npx -y @mermaid-js/mermaid-cli@11.4.2 `
  -i docs/v2/diagrams/decision-boundaries.mmd `
  -o docs/v2/diagrams/decision-boundaries.png -b white -s 2
```

## 校验结果（2026-10-26）

- Mermaid CLI 11.4.2：两张图渲染成功，退出码 0。
- Mermaid CLI 12.0.0：两张图解析、渲染成功（用于跨版本语法兼容性检查）。
- 几何校验（本地 Chrome 读取 SVG）：
  - 节点重叠：0
  - 边穿过非端点节点：0
  - 边与边交叉：0
  - 边标签压节点：0
- 复杂度：图 5-1 为 12 节点 / 11 边；图 5-2 为 15 节点 / 17 边，均在 15 / 18 预算内。

## 已知限制

- Mermaid 12 的默认 `neo` 外观与 ELK 布局会把图 5-1 拉宽到约 1785px；GitHub/VS Code 当前多使用 11.x，产物按 11.4.2 生成。
- `%%{init}%%` 中的字号与间距可能被宿主忽略；忽略后布局变宽，但节点、边与语义不变。
- 图 5-1 在 GitHub 约 900px 正文栏下会缩放到约 84%，文字约 10px；需要逐字阅读时请打开 SVG 原图。
