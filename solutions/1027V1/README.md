# NoahsArk 1027V1

> 版本目录：`noahsark/solutions/1027V1`
> 基线方案：`../../docs/v2/SOLUTION.md`、`../../docs/v2/IMPLEMENTATION-PLAN.md`
> 状态：M0 设计评审版，不包含产品实现

## 本版本内容

| 文件 | 内容 |
|---|---|
| `MODULE-DESIGN.md` / `.pdf` | 13 个模块、逐步骤执行契约、耦合矩阵、13 张核心时序图 |
| `REMOTE-EXECUTION.md` / `.pdf` | Linux 控制面 + Windows 节点 + 设备本地执行 + 证据回传 |
| `GAP-CLOSURE.md` / `.pdf` | 5 个缺口、外部输入、建议新增任务 |
| `REVIEW-OPTIMIZATION.md` / `.pdf` | 对 gpt6sol 12 节评审的采纳/调整/暂缓 |
| `CHANGELOG.md` | 本版本新增、修改、仅建议未并入计划 |
| `NOAHSARK-V1-TOTAL-FLOW.svg/.png/.pdf` | V1 总流程：阶段、Linux/Windows 边界、回环、门禁、异常与接管 |
| `sequences/` | 14 张时序图 + 1 张远程拓扑图，含 `.mmd` 与 PNG |

## 每版固定产物

从 V1 开始，每个版本目录必须包含：

- `NOAHSARK-V*-TOTAL-FLOW.svg`
- `NOAHSARK-V*-TOTAL-FLOW.png`
- `NOAHSARK-V*-TOTAL-FLOW.pdf`
- 对应版本的 `README.md` 和 `CHANGELOG.md`

总流程图只画该版本的主流程、边界、回环和异常；细节时序图仍放 `sequences/`。

## 版本规则

- 每个新方案/优化单独建目录：`1027V2`、`1027V3`……
- 不覆盖旧版本；旧版本保留评审证据。
- 新版本必须写清基线、差异、验收状态和未关闭缺口。
- 本目录不包含后端代码、真实执行结果或生产凭据。

