# NoahsArk 缺口关闭方案

> 状态：设计评审版，未进入产品实现
> 对应文档：`MODULE-DESIGN.md` 第 7.1 节
> 目标：把 5 个实施缺口变成可执行的契约、任务、证据和验收条件

---

## 0. 结论

这 5 个缺口关闭后，现有 81 项计划应扩展为 **86 项**。新增的不是泛泛的“补充开发”，而是 5 个有明确输入、输出、依赖和验收证据的任务：

| 缺口 | 建议新任务 | 类型 | 是否阻塞真实 E2E |
|---|---|---|---|
| M2 执行适配器/节点 Agent 未单列 | P5-00 Execution adapter and node agent | 实现 | 是 |
| M6 方案/用例/oracle 持久化未冻结 | P0-03b Plan/case/oracle schema | 契约+迁移 | 是 |
| 证据目录与 manifest 未冻结 | P0-04b Evidence manifest contract | 契约 | 是 |
| M9 T3 真实设备窗口未落实 | P8-03b T3 real-device qualification | 验收 | 是 |
| 美的 5 个 PDF 未入库 | P3-07b PDF ingestion and OCR | 实现+数据 | 否，但影响知识完整性 |

这些任务全部依赖 M0 批准；未批准前不写产品代码。

---

## 1. G1：M2 执行适配器与节点 Agent

### 为什么缺

现有计划有 `P5-03 Real-run proof` 和 `P8-03 Real-device E2E harness`，但都假设“执行适配器已经存在”。计划没有定义：

- 节点 Agent 如何接收任务、申请租约、启动/停止 runner。
- lstest runner 如何被调用，profile 如何编译，超时/取消如何处理。
- 串口、声卡、电源端点如何稳定标识。
- 执行回执如何签名，产物 manifest 如何生成。
- 设备动作中断时如何安全暂停，如何处理重复回执。

### 需要补的内容

**A. 执行适配器契约**

- `ExecutionRequest`：task_id、plan_hash、binding_id、node_id、device_id、profile、run_mode、sample_count、timeout、evidence_root。
- `ExecutionHandle`：execution_id、lease_id、session_id、started_at、status。
- `ExecutionResult`：exit_code、status、started/ended、artifact_manifest_hash、receipt_id、evidence_refs、error_class。
- 回执签名：节点 ID、租约 ID、串口/音频端点身份、runner 退出状态、manifest 哈希、节点签名、nonce。

**B. 节点 Agent 能力**

- 注册/心跳/能力探测：OS、CPU、内存、磁盘、opencode/OMO/lstest 版本。
- 设备发现：稳定串口身份、声卡端点、电源通道；不能只依赖 COM 编号。
- 租约：acquire/renew/release；同一设备/串口只允许一个任务。
- 进程控制：启动、日志流、超时、取消、优雅停止、强制停止边界。
- 证据采集：stdout/stderr、serial log、audio、tool log、results.csv、截图。
- 断线恢复：会话中断标记、检查点、恢复或明确失败。

**C. 实现文件（目标布局）**

```text
src/noahsark/aitest/execution/
  contracts.py          # request/result/receipt/manifest schema
  adapter.py            # node + lstest adapter
  leases.py             # acquire/renew/release/CAS
  process.py            # runner launch/stop/timeout
  endpoints.py          # serial/audio stable identity
  evidence.py           # evidence writer + manifest
  receipts.py           # sign/verify/duplicate guard
  node_agent.py         # node loop: heartbeat/poll/execute
tests/execution/
  test_contracts.py
  test_leases.py
  test_process.py
  test_receipts.py
  test_manifest.py
```

**D. 远程执行边界**：Linux 只做编排/验收；Windows 节点主动出站 HTTPS 长轮询取任务；脚本、lstest、串口、声卡、电源全部在 Windows 本地执行；详细协议见 [`REMOTE-EXECUTION.md`](./REMOTE-EXECUTION.md)。

**E. 验收**

- 同一设备两个任务并发申请：只有一个获得租约，另一个 409。
- 预检失败必须产生预检证据并进入 `BLOCKED_HUMAN`，不能启动正式运行。
- `run_mode=dry_run` 不能产生 C2 证据。
- runner 超时/取消后进程被回收，租约释放，证据保留。
- 回执签名错误、重复回执、manifest 哈希不匹配全部拒绝。
- 至少一次真实节点 + 真实设备的预检和正式运行通过。

### 需要你提供

- 至少一个可执行节点：IP/Agent 通道、操作系统、已安装工具版本。
- 至少一台被测设备：型号、固件、串口、声卡端点、电源控制方式。
- 凭据只放服务端 credential ref 或环境变量，不要在聊天里贴密码。
- 该项目可用的 lstest profile 或一份真实测试脚本。

---

## 2. G2：M6 方案/用例/oracle 持久化

### 为什么缺

现有 schema 列表有 `completion_reports`、`executor_receipts` 等，但没有方案修订、用例集、oracle 集的明确存储契约。C1 需要 `plan_revision_sha256`，却未定义它从哪里来、如何不可变、如何关联用例和 oracle。

### 需要补的内容

建议采用 **数据库元数据 + 内容寻址文件**：

- `plan_revisions`：task_id、revision、status、plan_sha256、assurance_report_id、approval_id、created_by、created_at。
- `case_sets`：task_id、plan_revision_id、schema_version、cases_sha256、count、created_at。
- `oracle_sets`：case_set_id、oracle_sha256、schema_version、created_at。
- 文件：`artifacts/<task_id>/plans/<sha>/plan.json`、`cases.json`、`oracles.json`。
- 审批后只读；任何修订创建新 revision，不覆盖旧版本。

### 验收

- 方案批准后修改原文件会被拒绝。
- `plan_revision_sha256` 与 C1 报告可重算一致。
- 用例/oracle 的哈希、数量、schema 版本可追溯。
- 删除/篡改文件导致 C1/C4 失败，不静默回退。
- 旧 revision 可读取，用于复现。

### 需要你决定

- 是否接受“DB 元数据 + 文件内容寻址”方案；如果不接受，需要指定只用 DB 或只用文件。
- 方案文件保留期限和是否允许导出。

---

## 3. G3：证据目录与 manifest 契约

### 为什么缺

C3/C5 依赖 `artifact_manifest_sha256`、逐文件哈希、证据类型和分母，但现有文档没有定义目录结构、必需文件和空证据规则。没有这个契约，执行结果无法被 M7 可靠验收。

### 需要补的内容

定义 `aitest.evidence_manifest.v1`：

```json
{
  "schema": "aitest.evidence_manifest.v1",
  "task_id": "ait-...",
  "execution_id": "exec-...",
  "run_mode": "real",
  "node_id": "win009",
  "lease_id": "lease-...",
  "endpoints": {"serial": "...", "audio": "..."},
  "files": [
    {"kind": "serial_log", "path": "serial/COM7.log", "sha256": "...", "bytes": 12345},
    {"kind": "audio", "path": "audio/tcl003.wav", "sha256": "...", "bytes": 456789},
    {"kind": "results", "path": "results/results.csv", "sha256": "...", "bytes": 2048}
  ],
  "denominators": {"planned": 200, "executed": 200, "valid": 198},
  "redaction": {"applied": true, "fields": ["token"]},
  "manifest_sha256": "..."
}
```

证据目录：

```text
evidence/<task_id>/<execution_id>/
  manifest.json
  serial/
  audio/
  results/
  tool/
  screenshots/
  preview/
```

规则：

- 文件必须位于 evidence root 内，禁止路径穿越。
- 必需证据按用例类型定义；空文件、截断文件、0 字节失败。
- 分母必须来自 plan/case，不允许 runner 自报一个无法校验的分母。
- 原始敏感证据只留摘要/指针；secret/PII 脱敏。
- manifest 与文件哈希必须可重算；删除/篡改即失败。
- 归档后只读；保留策略按项目配置。

### 验收

- 构造缺失文件、hash 不匹配、路径穿越、0 字节、分母不一致五类样本，C3/C5 全部失败。
- 正常真实运行的 manifest 可重算；M7 可用它生成完成报告。
- 证据目录可由 UI 只读展示，不暴露 secret。

### 需要你提供

- 一份真实运行的证据样本，或至少确认证据类型：串口日志、音频、结果表、工具日志、截图。
- 保留期限和敏感数据规则。

---

## 4. G4：M9 T3 真实设备资格

### 为什么缺

T1/T2 可以在普通机器上完成，但 T3 需要真实设备窗口。没有 T3，工具链升级和真实 E2E 不能宣称完成。

### 需要补的内容

- 设备/节点/固件：明确型号、版本、串口、声卡、电源。
- 测试场景：一个已知 PASS 场景 + 一个已知 FAIL 场景 + 一个离线/停止场景。
- 维护窗口：开始/结束时间、负责人、回滚联系人。
- 冒烟记录：T1/T2 结果、T3 运行 ID、证据 manifest、结论。
- 升级/回滚演练：升级前后版本、运行结果、回滚是否成功。

### 验收

- T3 真实 PASS、FAIL、STOPPED/离线各至少一次。
- 升级后 T1/T2/T3 通过；漂移时真实执行关闭。
- 回滚到旧 pin 后能恢复执行。
- 记录设备、固件、工具链、模型绑定和证据哈希。

### 需要你提供

- T3 设备窗口和负责人。
- 允许的固件版本、是否允许断电/离线模拟。
- 升级审批人与回滚联系人。

---

## 5. G5：美的 PDF 摄取

### 为什么缺

知识服务当前只索引 `knowledge/` 下的 Markdown/TXT；美的源材料有 5 个 PDF 未进入正文。`PDF_STATUS.md` 只反映索引树，不能代表源材料已处理。

### 需要补的内容

- PDF 清单：路径、页数、是否扫描件、是否有表格。
- 提取方案：`PyMuPDF`/`pdfplumber` 提取文本和表格；扫描件用 OCR（Tesseract 或项目允许的 OCR）。
- 清洗：页眉页脚、重复水印、乱码、表格转 Markdown。
- 引用：保留页码/标题路径；检索结果可引用到页。
- 安全：secret/PII 扫描；不把原文二进制放入索引。
- 质量验收：每页可提取文本比例、空页清单、表格抽样、检索命中测试。

### 验收

- 5 个 PDF 全部有提取状态：成功/部分/失败，不允许静默跳过。
- 失败页和扫描页有明确清单，不生成猜测内容。
- 至少 5 个针对 PDF 内容的检索问题有正确引用。
- 原有 Markdown 检索指标不下降。

### 需要你提供

- 确认 5 个 PDF 可以本地解析/OCR。
- 是否允许安装 PDF/OCR 依赖（PyMuPDF、pdfplumber、Tesseract）。
- PDF 是否包含敏感数据，能否进入知识库。

---

## 6. 还需要补充的其他内容

### 6.1 需要你决策

1. **M0 设计批准**：是否批准总体方案、模块级设计、Apple v3/航次档案二选一或混合。
2. **M6 存储方案**：是否接受“DB 元数据 + 文件内容寻址”。
3. **M2 真实设备**：哪个节点、哪台设备、哪个 lstest profile 作为第一条真实链路。
4. **M9 T3 窗口**：时间、负责人、允许的固件/断电操作。
5. **PDF/OCR**：是否允许安装依赖和处理 5 个 PDF。
6. **GitHub 推送**：是否需要把当前文档推到 NoahsArk 空仓库；需要 Git 身份/token 配置。
7. **C8**：是否现在定义“测试之测试”，还是保持 P4-12 占位。
8. **UI 基线**：v2 航次档案、v3 Quiet Instrument，或混合。

### 6.2 我可以内部补齐，不需要你提供

- 5 个新任务的详细 checklist 和依赖。
- `plan_revisions`/`case_sets`/`oracle_sets` 的 migration 草案。
- `evidence_manifest.v1` JSON Schema 和路径守卫测试。
- 执行适配器的接口/测试骨架。
- T1/T2/T3 冒烟矩阵模板。
- PDF 解析脚本和提取质量报告模板。
- 把这些内容写入 86 项计划并保持 81 项现有编号不变。

### 6.3 不能代替你提供的

- 真实设备的物理访问和授权。
- 设备/固件/串口/声卡的实际身份。
- 真实项目的 lstest profile 和测试脚本。
- 生产凭据（只能通过 credential ref）。
- 真实 T3 维护窗口和业务验收人。

---

## 7. 建议的计划变更

在 M0 批准后，把现有 81 项扩展为 86 项：

| 新 ID | 任务 | 依赖 | 产出 |
|---|---|---|---|
| P5-00 | Execution adapter and node agent | P0-04、P5-03 | 执行适配器、节点 Agent、回执、manifest |
| P0-03b | Plan/case/oracle schema | P0-03、P4-03 | 迁移、内容寻址、C1 冻结 |
| P0-04b | Evidence manifest contract | P0-04、P5-03 | JSON Schema、路径守卫、分母规则 |
| P8-03b | T3 real-device qualification | P8-03、真实设备窗口 | T3 记录、PASS/FAIL/STOPPED 证据 |
| P3-07b | PDF ingestion and OCR | P3-07、PDF 清单 | 5 个 PDF 的提取/引用/质量报告 |

关闭顺序：**P0-03b → P0-04b → P5-00 → P3-07b → P8-03b**。前三个是真实执行的前置；PDF 可以与 W2 并行；T3 最后做。

---

## 8. 最小启动包

如果你希望我现在继续推进，不需要一次性给全部信息。最小启动包是：

1. 批准这 5 个新任务进入计划。
2. 给一个测试节点和一台设备的基本信息。
3. 确认 M6 采用“DB 元数据 + 文件内容寻址”。
4. 确认允许本地 PDF/OCR。
5. 给 T3 的可用时间窗口。

拿到这 5 项后，我可以先完成**契约、schema、接口骨架、测试清单和 PDF 解析方案**，再进入真实设备验收。
