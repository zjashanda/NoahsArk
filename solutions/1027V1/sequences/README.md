# Module Sequence Diagrams

本目录是 `MODULE-DESIGN.md` 第 6 节的时序图源文件与渲染产物。

| 文件 | 回答的问题 | 主要模块 |
|---|---|---|
| `seq-01-task-intake` | 任务如何受理、检索并生成检索快照 | M1、M5、M4 |
| `seq-02-plan-approval` | 方案/用例/oracle 如何评审、批准并冻结 C1 | M6、M10、M0 |
| `seq-03-real-execution` | 预检、设备租约、正式执行、签名回执如何闭环 | M2、M9、M7 |
| `seq-04-completion-archive` | C1–C7、独立重算、C6 写回、归档如何闭合 | M7、M5、M4 |
| `seq-05-model-switch` | 三层模型策略如何解析、切换和回退 | M3、M0 |
| `seq-06-event-push` | 事件落库、outbox、SSE/文件/Webhook 如何解耦 | M4、M11 |
| `seq-07-takeover` | 人工接管如何用 epoch CAS 防双控制 | M8、M2 |
| `seq-08-toolchain` | 版本漂移如何阻断真实执行并升级 | M9、M2 |
| `seq-09-agent-openspec` | Agent 注册表、配置渲染、写守卫如何工作 | M10、M6 |
| `seq-10-ui-projection` | UI 如何只读投影并在 SSE 断线时降级 | M11、M1、M7 |
| `seq-11-discussion` | 讨论插件如何返回候选共识而不是验收结论 | M12、M3 |
| `seq-12-kb-retrieval` | 知识检索如何排序、过滤、引用和报 no_history | M5、M6 |
| `seq-13-failure-repair` | 失败如何分类、修复、重跑或保留最终 FAIL | M2、M5、M7 |
| `seq-14-remote-windows-node` | Linux 如何把任务交给 Windows 节点，节点如何本地执行并回传证据 | M2、M7、M9 |
| `remote-execution-topology` | Linux 控制面、Windows 节点、设备和证据存储的拓扑 | M2、M11 |

## Render

```powershell
$env:PUPPETEER_EXECUTABLE_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"
npx -y @mermaid-js/mermaid-cli@11.4.2 `
  -i seq-01-task-intake.mmd `
  -o seq-01-task-intake.png -b white -s 2
```

`MODULE-DESIGN.md` 直接引用同名 `.png`；`.mmd` 是可编辑源文件。PDF 由 `MODULE-DESIGN.pdf` 提供，不依赖查看器的 Mermaid 插件。
