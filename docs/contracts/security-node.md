# NoahsArk V0.0.1 节点身份、注册与消息安全契约（security-node.md）

> 状态：`frozen-candidate v1.1`，等待 Orchestrator/所有者评审。**不是已批准契约**，不构成实现、测试、部署或发布授权。**not production-frozen; Phase 0 not closed**。
> 契约版本：`1.0`；线协议版本：`noahsark.node/v1`。
> 形成日期：2026-10-28。
> 适用版本：NoahsArk V0.0.1。
> 依据：已批准需求基线；`.omo/plans/noahsark-platform-delivery.md` 的 P0-05；`.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md` 的 CP-05/06/07、EN-01..EN-08；`.omo/drafts/01-design/noahsark-v0.0.1-module-design.md` 的 M-05/06/07 与作业信封；`.omo/drafts/02-delivery/noahsark-v0.0.1-delivery-acceptance.md` 的 AC-11/AC-12/AC-13；`.omo/drafts/05-decisions/noahsark-v0.0.1-decision-register.md` 的 P0-02/P0-03/P0-07。
> 本文只冻结身份、注册、消息认证、防重放、节点协议字段与运行默认值；不实现代码、不生成真实证书/私钥/令牌、不替代任务级数值批准。

## 1. 结论摘要

V0.0.1 的节点安全基线如下，全部为**默认值**，可在任务级或节点级收紧，但不得突破第 16 节的硬上限：

| 决策 | v1 默认 |
|---|---|
| 节点身份 | 每节点独立 X.509 设备证书；证书公钥算法 Ed25519；禁用仅 bearer token 的长期身份 |
| 传输 | 节点**仅出站** TLS 1.3 + mTLS；节点主动长轮询控制面，不监听任何入站管理端口 |
| 消息认证 | 双向 Ed25519 签名信封 + SHA-256 payload hash；控制面签名密钥与节点签名密钥分离 |
| 规范化 | RFC 8785 JSON Canonicalization Scheme（JCS） |
| 注册 | 管理员签发一次性 256-bit enrollment token（15 分钟、单次、只存哈希）+ 节点本地生成密钥 + 人工/策略批准 |
| 证书有效期 | 90 天；第 60 天续期；新旧证书重叠 7 天 |
| 轮换 | 计划内双密钥重叠轮换；`node_id` 不变，`key_id` 变化；旧公钥保留用于历史回执验签 |
| 撤销 | 控制面即时撤销 + 签名撤销列表；按 `revoked_at` 与 `compromise_time` 做前向/回溯判定 |
| nonce | 128-bit 随机，base64url 22 字符；按 `(key_id, nonce)` 去重，保留 900 秒 |
| epoch | 每节点单调递增的租约 fencing token；新工作/STOP 必须匹配当前 epoch |
| 时钟偏差 | 最大 120 秒；紧急阈值 300 秒 |
| 消息 TTL | Job/Lease/STOP 300 秒；Heartbeat 90 秒；Enrollment 300 秒 |
| 心跳 | 30 秒；连续 2 次丢失（60 秒）标记通信离线 |
| 租约 | 60 秒；过期宽限 30 秒；租约到期不等于设备空闲 |
| 重试/退避 | 初始 1 秒，倍增，上限 60 秒，20% 抖动；连续 10 次失败标记离线 |
| 消息大小 | 控制消息 1 MiB；日志查询请求 64 KiB；日志结果分片 256 KiB；manifest 上传 4 MiB |
| 离线 | 已启动的冻结压测继续；不接新作业；本地安全 STOP 可用；重连 STOP-first |
| 命令面 | **闭集枚举**；不存在 shell / PowerShell / cmd / SSH / argv / 自由脚本字段 |

**硬边界**：Windows Node Agent 只执行 Linux 冻结的 `NoahsArk Execution Bundle` 并通过固定处理器返回事实；它不接受任意 Shell、PowerShell、cmd、SSH、WMI 远程执行或自由命令字符串。控制面也不向节点暴露通用远程执行入口。

## 2. 范围与非目标

### 2.1 本文覆盖

1. 节点身份、注册/引导、证书与密钥生命周期、轮换、撤销。
2. 信封字段、签名、payload hash、nonce、epoch、时钟偏差、防重放。
3. Job、Lease、Heartbeat、STOP、Receipt、Log Query、Anomaly Event 的 v1 字段与语义。
4. 离线续跑、STOP-first 重连、对账、去重。
5. 日志查询白名单、路径约束、范围限制、脱敏与审计。
6. 失败行为、审计事件、配置默认值与优先级、任务级覆盖点。
7. Session 0 服务与交互式执行器之间的本地信任边界。

### 2.2 明确非目标（禁止实现为“以后再说”的灰色通道）

- 通用远程 shell、任意 PowerShell、cmd、SSH、SCP、WinRM、WMI、RPC 远程过程调用。
- 任意 `argv`、`command`、`script`、`entrypoint`、`exec`、`invoke` 字段或“自定义脚本”扩展点。
- 入站监听的管理端口、反向 shell、远程桌面自动化作为执行路径。
- 节点生成或修改测试方案、脚本、音频、异常规则、判据或最终判定。
- 固件打包/烧录、控制串口上电、断电（沿用需求基线排除项）。
- 在日志查询中读取任意文件、目录遍历、UNC 路径、ADS、注册表任意键或事件日志任意通道。
- 用 bearer token 单独承担长期节点身份；token 只允许作为一次性注册凭据。

## 3. 威胁模型

### 3.1 资产

| 资产 | 说明 |
|---|---|
| 设备安全 | 被测设备、串口、音频、USB、供电边界不被未授权动作破坏 |
| 测试完整性 | 冻结工件、用例、判据、运行与证据不被篡改或替换 |
| 证据可信度 | 回执、manifest、日志、音频的来源、完整性与时间可信 |
| 身份与密钥 | 节点私钥、控制面签名密钥、注册 token、CA 私钥 |
| 隐私 | 原始音频、日志、设备标识、用户会话信息 |
| 可用性 | 长时压测不被错误 STOP、重放、租约抢占或 DoS 中断 |

### 3.2 信任边界与角色

```text
[管理员/操作者] --HTTPS--> [Linux 控制面]
                              |  出站长轮询（节点发起）
                              v
                    [Windows Session 0 节点服务]  <--本地命名管道-->  [登录会话执行器]
                              |  固定适配器
                              v
                    [lstest / 设备端点 / 音频 / 串口]
```

| 边界 | 信任假设 | 不信任的内容 |
|---|---|---|
| 控制面 ↔ 节点 | 控制面持有权威身份、租约、判定；节点只回传事实 | 节点自报 PASS、节点本地时钟、节点本地脚本 |
| Session 0 服务 ↔ 交互式执行器 | 服务已验证控制面签名；执行器只接受固定 Job 描述符 | 任意本地进程、未签名 IPC、远程命名管道客户端 |
| 节点 ↔ 设备 | 设备动作只能由固定适配器在交互会话执行 | 任意串口命令、任意 PowerShell、任意 USB 控制 |
| 控制面 ↔ 操作者 | 操作者经控制面授权；STOP 需控制面签名 | 直接连接节点的“运维后门” |

### 3.3 威胁与缓解

| ID | 威胁 | 缓解 | 验证点 |
|---|---|---|---|
| T-01 | 网络攻击者注入命令 | 仅出站 mTLS + 签名信封 + 闭集 action；无入站 shell | 未知 action/字段被 schema 拒绝 |
| T-02 | 重放旧 Job/STOP/Receipt | nonce 去重 + 时间窗 + epoch fencing + message_id 幂等 | 重复 nonce/旧 epoch 被拒绝并审计 |
| T-03 | MITM 或降级 | TLS 1.3、内部 CA、主机名校验、禁用弱协议/弱套件 | 非法证书/降级握手失败 |
| T-04 | 节点私钥被盗 | 每节点独立密钥；TPM/CNG 优先；DPAPI + ACL 兜底；快速撤销 | 撤销后新消息被拒 |
| T-05 | 被控节点伪造回执 | 控制面独立复核证据、digest、关联与判定；节点不能写最终判定 | 节点自报 PASS 不产生平台 PASS |
| T-06 | 证据/工件替换 | bundle/artifact digest 在 Job 中签名；节点执行前重算 | digest 不匹配即拒绝并上报 |
| T-07 | 日志查询变成任意文件读取 | source 白名单、路径规范化、run root 约束、扩展名/深度/大小限制 | `..`、绝对路径、UNC、ADS 被拒 |
| T-08 | 日志泄露隐私 | 默认标准脱敏；`none` 需特权审批；审计与告警 | 未审批 raw 查询被拒 |
| T-09 | Session 0 提权到交互会话 | 命名管道 ACL、仅本地、拒绝远程客户端、执行器二次校验 | 非授权进程无法提交 Job |
| T-10 | 无交互会话时静默降级 | 无会话即 `BLOCKED_NO_INTERACTIVE_SESSION`，不降级为服务会话采集音频 | 回执为 BLOCKED，不产生 PASS |
| T-11 | 时钟操控绕过时间窗 | 双向偏差检查 + 控制面时间权威 + 超阈值异常/阻断 | 未来/过期消息被拒 |
| T-12 | 注册 token 被盗 | 256-bit 一次性、15 分钟、只存哈希、限速、人工批准、绑定公钥 | token 重用/过期失败 |
| T-13 | 证书过期导致停摆 | 60 天续期、过期前告警、离线宽限、旧回执仍可验签 | 续期与历史验签测试 |
| T-14 | 长时压测被误停 | 已启动冻结压测离线继续；STOP 只在安全点生效；本地安全停止优先降风险 | 断线运行不中断、不重播 |
| T-15 | DoS/资源耗尽 | 消息大小、并发、速率、磁盘/内存上限；spool 上限与背压 | 超限返回 413/429 并审计 |
| T-16 | 供应链工件替换 | 固定 lstest 版本/commit、bundle 签名、manifest digest、只读工件缓存 | 版本/哈希漂移告警 |

### 3.4 安全属性

1. **认证**：每条消息都能追溯到 `node_id` 与 `key_id`；控制面消息由控制面密钥签名。
2. **完整性**：payload 改动会导致 `payload_hash` 或签名验证失败。
3. **不可否认**：节点回执带签名与 key 历史；控制面保留验签材料。
4. **新鲜性**：nonce + `issued_at`/`expires_at` + epoch 共同保证。
5. **最小权限**：节点只执行闭集 action；日志查询只读白名单。
6. **失效安全**：任何验证失败都 fail-closed；本地 STOP 只降低风险，不需要远端授权。
7. **可审计**：安全决策、拒绝、轮换、撤销、查询、STOP、重连全部写审计。

## 4. 身份方案

### 4.1 候选对比

| 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| **X.509 设备证书 + 应用层签名 + mTLS** | 可撤销、可轮换、双向认证、非否认、与 TLS 信任链一致 | 需要内部 CA/证书分发与续期 | **v1 默认** |
| 长期签名 token（JWT/自签 token） | 实现简单、无 CA | bearer 泄露即可重放；撤销/轮换困难；难做非否认 | 仅可作为一次性注册凭据，不作长期身份 |
| 预共享密钥（PSK） | 简单 | 难轮换、难归因、泄露影响面大；无法满足多节点审计 | 不采用 |
| TPM 远程证明 | 强绑定硬件 | 依赖硬件与证明服务；V0.0.1 环境未保证 | 可选增强，不阻塞 v1 |

### 4.2 选定默认

- 每节点一对 **Ed25519** 密钥；私钥本地生成，永不出节点。
- 控制面内部 CA 为节点签发 **X.509 设备证书**，证书公钥即节点签名公钥。
- 传输层使用 **TLS 1.3 + mTLS**：节点用设备证书作为客户端证书；控制面用内部服务证书。
- 应用层再对每条消息做 **Ed25519 detached signature**，与 mTLS 形成纵深防御。
- 控制面使用独立的 **control-plane Ed25519 signing key** 签名下行消息；该密钥不与节点密钥、CA 密钥混用。
- `sender_role` 区分签名者；`key_id` 前缀区分 `cp-ed25519:` 与 `ed25519:`。

### 4.3 为什么不是 signed-token

长期 bearer token 一旦泄露，攻击者可在有效期内重放；服务端只能靠撤销列表补救，且无法提供与私钥绑定的非否认。证书 + 私钥签名把“持有者”与“密钥”绑定，支持 mTLS、证书序列号、CRL/撤销列表和密钥历史。注册 token 只承担“首次把公钥绑定到 node_id”的一次性引导职责，有效期 15 分钟且单次使用。

### 4.4 ID 派生

```text
key_id   = "ed25519:" + lowerhex(SHA-256(SPKI DER))[0:32]
node_fp  = lowerhex(SHA-256(SPKI DER))[0:32]                    # 128-bit 公钥指纹
node_id  = uuid_from_hex(node_fp)                               # 首次注册时确定，canonical UUID
cp key   = "cp-ed25519:" + lowerhex(SHA-256(SPKI DER))[0:32]
```

- 首次注册时 `node_id` 由节点公钥指纹的 128-bit 值格式化为 canonical UUID；控制面校验唯一性，冲突时分配新的 `node_id` 并在 `node_identity` 中返回，节点以后者为准。
- 计划内轮换后 `node_id` **保持不变**，`key_id` 变化；`node_identity.previous_key_id` 记录前一把密钥。
- `node_id` 不是秘密；`key_id` 不是秘密；私钥、注册 token、CA 私钥永远不写入日志、回执或证据。

### 4.5 实体 ID 表示（v1 唯一表示）

v1 的所有实体 ID 只有一种表示：**canonical UUID**（小写 RFC 9562 文本）。`schemas/domain/`、`schemas/security/`、`schemas/evidence/`、`schemas/experience/` 对同一实体使用同一 UUID：

| 实体 | 唯一 ID 字段 | 表示 |
|---|---|---|
| Task / Revision / Run | `task_id` / `revision_id` / `run_id` | canonical UUID |
| Case / Attempt | `case_id` / `attempt_id` | canonical UUID（`attempt` 序号是整数，不是 ID） |
| Node / Device / Lease | `node_id` / `device_id` / `lease_id` | canonical UUID |
| Evidence / Receipt / Manifest | `evidence_id` / `receipt_id` / `manifest_id` / `cleanup_receipt_id` | canonical UUID |
| Message / Boot / Stop / Query / Anomaly | `message_id` / `boot_id` / `stop_id` / `query_id` / `anomaly_id` | canonical UUID 或显式命名空间 ID（见下） |

- **禁止前缀解析**：`node_<hex>`、`job_<hex>`、`lease_<hex>` 等旧前缀形式不再是线协议身份，不得由消费者通过 `split("_")` 还原 UUID。
- **显式 `wire_id` 规则**：若部署或日志展示确实需要带前缀别名，必须把它放在独立的 `wire_id` 字段中，并与同一对象的 UUID 在同一结构内显式成对出现（例如 `{"task_id": "<uuid>", "wire_id": "task_<hex>"}`）；`wire_id` 只用于展示/追溯，不参与外键、幂等键或权限判断。
- **非实体消息 ID**：`stop_id`、`query_id`、`anomaly_id`、`enrollment_id` 是控制/审计消息的命名空间 ID，不映射到领域实体，也不得当作 `task_id`/`run_id` 使用；它们可以保留显式前缀，但必须在字段名和文档中标记为消息级 ID。
- API 边界只暴露 UUID；若响应同时包含 `wire_id`，必须显式标注其为展示别名，不得让消费者误认为两个对象。
- `node_id` 的 128-bit 值在首次注册时来自公钥指纹；轮换后 `node_id` 不变，`key_id` 变化。

## 5. 注册与引导（Enrollment）

### 5.1 两阶段流程

```text
管理员在控制面创建 enrollment（绑定预期节点/设备/环境）
  → 控制面生成 256-bit 一次性 token，仅存 SHA-256(token)，TTL 15 分钟
  → 管理员通过带外渠道把 token 交给节点操作者（不写入仓库/日志/聊天记录）
  → 节点本地生成 Ed25519 密钥对（TPM/CNG 优先，DPAPI+ACL 兜底）
  → 节点出站 HTTPS 提交 signed node_enrollment（含 token、公钥、device_facts）
  → 控制面校验 TLS、token 哈希/单次/TTL、签名、公钥与 node_id、限速
  → 人工批准（生产默认）或显式策略自动批准（仅限隔离的 staging）
  → 控制面签发设备证书 + signed node_identity
  → 节点校验 node_identity 签名、证书链、node_id/key_id 绑定
  → 节点进入 active；开始出站长轮询
```

### 5.2 Enrollment token 规则

| 规则 | 值 |
|---|---|
| 熵 | 256-bit（base64url 43 字符） |
| 存储 | 控制面只存 SHA-256 哈希；不存明文 |
| TTL | 15 分钟（硬上限 60 分钟） |
| 使用次数 | 1 次；消费后立即失效 |
| 绑定 | 绑定创建者、预期环境、可选预期 node_id/设备、公钥指纹 |
| 传输 | 仅带外；禁止写入仓库、日志、URL query、审计详情 |
| 限速 | 每 IP/节点 10 分钟内最多 5 次；失败锁定 15 分钟 |
| 失败 | 过期/重用/公钥不匹配 → `ENROLLMENT_TOKEN_INVALID`，审计，不签发 |

### 5.3 节点密钥存储

1. 优先使用 **TPM 2.0 / Windows CNG** 生成不可导出密钥；`tpm_status=available` 时，私钥不得导出为文件。
2. 无 TPM 时，使用 **DPAPI（LocalMachine 或服务账户 scope）** 保护私钥文件，并设置 ACL：仅节点服务 SID 与 Administrators 可读。
3. 私钥文件不得位于仓库、共享目录、可被交互用户任意读取的路径。
4. 私钥不得进入崩溃转储、日志、环境变量、命令行参数或遥测。
5. 节点服务账户使用最小权限：默认专用虚拟服务账户；仅当设备/驱动要求时使用 LocalSystem，并记录理由。

### 5.4 注册状态机

```text
CREATED → TOKEN_ISSUED → REQUESTED → PENDING_APPROVAL
        → APPROVED → IDENTITY_ISSUED → ACTIVE
        → REJECTED / EXPIRED / CONSUMED
ACTIVE → SUSPENDED / REVOKED / RETIRED
```

- `REQUESTED` 只表示收到合法签名与 token；不表示已信任。
- 生产默认 `PENDING_APPROVAL`；自动批准只允许在隔离 staging 且显式配置 `enrollment.auto_approve=true`。
- 拒绝、过期、重放都要审计；被拒绝的节点不得获得证书。

### 5.5 重新注册

- 证书过期且无法续期、密钥丢失、节点重装：创建新的 enrollment，签发新证书。
- 若保留原 `node_id`，必须由管理员显式绑定；否则按新节点注册。
- 旧 `key_id` 进入 `retired`，公钥保留用于历史回执验签；若怀疑泄露，按第 6.5 节撤销。

## 6. 证书与密钥生命周期

### 6.1 签发

- 控制面内部 CA（离线根 + 在线中间 CA）签发设备证书。
- 证书 `subject` 至少包含 `CN=<node_id>`；SAN 使用 `URI:noahsark://node/<node_id>`；不得使用通配符或共享证书。
- 证书扩展：`keyUsage=digitalSignature`、`extendedKeyUsage=clientAuth`；禁止 `serverAuth`。
- 证书序列号唯一、不可重用；控制面记录 `serial_number`、`key_id`、`node_id`、`issued_at`、`not_after`。
- 签发必须绑定已批准的 enrollment；不得仅凭 token 自动签发生产证书。

### 6.2 有效期与续期

| 项 | 默认 |
|---|---|
| 设备证书有效期 | 90 天 |
| 续期启动 | 第 60 天（到期前 30 天） |
| 续期窗口 | 到期前 30 天至到期；到期后只能重新注册 |
| 续期认证 | 旧私钥签名 + 有效 mTLS；必要时人工批准 |
| 续期重叠 | 新证书生效后旧证书保留 7 天用于在途消息 |

- 到期前 14/7/3/1 天产生 `identity.expiring` 告警。
- 证书过期后，节点停止接受新 Job；已启动的冻结压测在安全点完成或 STOP；回执仍可用历史公钥验签。
- 续期不得改变 `node_id`；可以复用同一密钥或生成新密钥（推荐生成新密钥，见 6.3）。

### 6.3 轮换

**计划内轮换（推荐每 90 天或证书续期时）**

1. 节点生成新密钥对（新 `key_id`），保留旧密钥。
2. 节点用旧密钥签名 `node_enrollment`/轮换请求，内含新公钥、`previous_key_id`、新 `key_id`。
3. 控制面校验旧密钥仍有效、未撤销、epoch/租约状态允许，签发新证书与 `node_identity`。
4. 节点先启用新密钥签名，再进入 7 天重叠期；控制面同时接受新旧 `key_id`。
5. 重叠期后旧密钥标记 `retired`；旧公钥保留用于历史回执验签。
6. 轮换写审计：`identity.rotated`，记录前后 `key_id`、`key_generation`、操作者/策略。

**强制轮换**：怀疑泄露、设备重装、管理员要求时，立即签发新密钥并撤销旧密钥；旧回执按 6.5 节判定。

### 6.4 撤销

| 撤销原因 | 代码 | 生效方式 |
|---|---|---|
| 私钥泄露 | `key_compromise` | 从 `compromise_time` 起拒绝；之前回执可保留有效性 |
| 节点退役 | `cessation_of_operation` | 从 `revoked_at` 起拒绝新消息 |
| 证书被替换 | `superseded` | 重叠期后拒绝旧证书 |
| 管理员暂停 | `certificate_hold` | 立即拒绝新 Job/STOP 之外的变更，保留只读对账 |
| 违规/隔离 | `affiliation_ended` / `policy_violation` | 立即拒绝新消息，节点 drain |

- 控制面维护签名撤销列表（CRL 或等价的签名列表），包含 `serial_number`、`key_id`、`node_id`、`revoked_at`、`reason`、`compromise_time`。
- 节点在每次长轮询响应中收到自身 `identity_status`；被撤销时停止接新 Job，完成/安全停止已启动工作，进入 `retired`。
- 撤销传播目标：控制面即时生效（数据库权威）；节点在下一个心跳/轮询周期获知；最长 30 秒。
- 撤销不可“撤销”；误撤销只能重新注册并签发新证书，审计保留原记录。

### 6.5 旧回执仍可验签

- 回执包含 `key_id`；控制面保留每个 `key_id` 的公钥、证书链、有效期、撤销记录。
- 验签规则：
  1. 用 `key_id` 找到历史公钥，验证 Ed25519 签名与 `payload_hash`。
  2. 若 `key_id` 已 `retired`/`superseded`，只要 `issued_at` 落在该密钥有效期内且撤销不回溯，回执仍可验证。
  3. 若 `key_compromise` 且 `issued_at >= compromise_time`，回执标记 `INVALID_EVIDENCE`/`NEEDS_REVIEW`，不得用于 PASS。
  4. 若 `issued_at < compromise_time`，回执可保留有效性，但报告必须标注该密钥后来泄露。
- 公钥历史保留期：至少 **密钥退役后 2 年**，且不短于任何引用该回执/审计的记录寿命；两者取较长者。私钥历史不保留（节点侧只保留当前与重叠期密钥）。

## 7. 消息信封与签名

### 7.1 统一信封字段

所有协议消息都是“信封 + payload”的 JSON 对象。以下字段参与签名；`payload` 通过 `payload_hash` 间接绑定：

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `schema_version` | const `"1.0"` | 消息 schema 版本 |
| `protocol_version` | const `"noahsark.node/v1"` | 线协议版本 |
| `message_type` | 闭集枚举 | 见 7.6 |
| `sender_role` | `control_plane` / `node` | 区分签名者角色 |
| `message_id` | UUID（小写） | 全局唯一；幂等键的一部分 |
| `node_id` | `^node_[0-9a-f]{32}$` | 节点身份；下行时为接收方，上行时为发送方 |
| `job_id` | `^job_[0-9a-f]{32}$` 或 `null` | 非作业消息为 `null` |
| `lease_id` | `^lease_[0-9a-f]{32}$` 或 `null` | 非租约消息为 `null` |
| `epoch` | 非负整数；v1 JSON 上限 2^63-1 | 租约 fencing epoch；非租约消息为 `0` 或当前最高活跃 epoch |
| `nonce` | 22 字符 base64url | 128-bit 随机；每条消息唯一 |
| `issued_at` | RFC3339 UTC，`Z` | 签名者时钟 |
| `expires_at` | RFC3339 UTC，`Z` | 必须晚于 `issued_at` 且不超过 TTL |
| `payload_hash` | `^sha256:[0-9a-f]{64}$` | `SHA-256(JCS(payload))` |
| `signature` | 86 字符 base64url | Ed25519 签名；不含 padding |
| `key_id` | `^(ed25519|cp-ed25519):[0-9a-f]{32}$` | 签名公钥标识 |

`payload` 是消息特定对象，见第 9 节与 schema。

### 7.2 规范化

- 使用 **RFC 8785 JCS** 规范化 JSON；数字必须为有限值；禁止 `NaN`/`Infinity`；禁止重复键。
- 字符串统一 UTF-8；时间统一 UTC `Z`；ID 统一小写。
- `payload_hash = "sha256:" + lowerhex(SHA-256(UTF8(JCS(payload))))`。
- 签名输入：

```text
SIGNING_INPUT = UTF8("noahsark-envelope-v1\n" + JCS(envelope_without_signature))
```

`envelope_without_signature` 是除 `signature` 外的全部信封字段（含 `payload_hash`，不含 `payload`）。验证方必须重算 `payload_hash`，不能信任来信值。

### 7.3 签名算法

- v1 默认 **Ed25519**（RFC 8032），纯签名，无外部 hash 参数。
- 迁移备选：**ECDSA P-256 / SHA-256（ES256）**；仅当目标 Windows TLS/CNG 环境不支持 Ed25519 证书时，由控制面配置切换；切换必须双算法重叠期并记录 `key_algorithm`。
- 禁止：RSA-1024、SHA-1、MD5、`none`、HMAC 共享密钥作为长期节点身份。
- 签名验证失败一律拒绝，不得“降级为仅 mTLS”。

### 7.4 签名者与密钥角色

| 方向 | `sender_role` | `key_id` 前缀 | 验证密钥 |
|---|---|---|---|
| 控制面 → 节点 | `control_plane` | `cp-ed25519:` | 控制面 signing key 信任集（支持轮换重叠） |
| 节点 → 控制面 | `node` | `ed25519:` | 该 `node_id` 的 key 历史 |
| 注册请求（首次） | `node` | `ed25519:` | payload 内自断言公钥 + token 绑定 |
| 本地安全 STOP | `node` | `ed25519:` | 节点 key；控制面只审计，不需预先授权 |

### 7.5 幂等与去重

- 幂等键：`message_id`；作业级幂等键：`(job_id, attempt)`；回执级：`(job_id, attempt, sequence)`。
- 相同 `message_id` 且相同 `payload_hash` 的重发 → 返回首次结果，不重复执行。
- 相同 `message_id` 但不同 `payload_hash` → `MESSAGE_ID_CONFLICT`，安全告警。
- 作业重发必须沿用同一 `job_id`/`attempt`；不得用新 ID 绕过幂等。

### 7.6 消息类型闭集

```text
node_enrollment
node_identity
job
lease
heartbeat
stop
receipt
log_query
anomaly_event
```

任何未知 `message_type` 或未知顶层字段（`additionalProperties: false`）一律拒绝。

## 8. Nonce、epoch、时钟与防重放

### 8.1 Nonce

- 128-bit CSPRNG，base64url 无 padding（22 字符）。
- 去重键：`(signer_key_id, nonce)`；控制面缓存 900 秒（≥ 最大消息 TTL + 2×最大时钟偏差）。
- 节点也缓存控制面下行 nonce，防止把旧 STOP/Job 重放给节点；缓存 900 秒。
- 重复 nonce：
  - 同 `message_id` + 同 `payload_hash` → 幂等重发，返回首次 ACK。
  - 不同 `message_id` 或不同 `payload_hash` → `REPLAY_DUPLICATE_NONCE`，拒绝并审计。
- nonce 不得由时间戳、计数器或可预测值代替。

### 8.2 Epoch（fencing token）

- `epoch` 是每节点单调递增的 64-bit 租约 fencing token。
- 授予新租约、设备所有权变化、强制收回、节点重新注册后首次租约时递增。
- 规则：
  1. 新 Job、Lease 续约、远程 STOP 必须携带**当前** epoch。
  2. `epoch < current_epoch` → `EPOCH_STALE`，拒绝变更；不得回退。
  3. `epoch > current_epoch` → `EPOCH_AHEAD`，拒绝并告警（可能节点被克隆或控制面状态不一致）。
  4. 终态回执在 `receipt_grace`（默认 24 小时）内允许携带该 Job 的原 epoch 入库；只能幂等记录，不得改变租约/设备所有权。
  5. 旧 epoch 的回执不得覆盖新 epoch 的运行状态；对账时以 Job/Lease 记录为准。
- 节点重启不重置 epoch；控制面 epoch 持久化。节点 `boot_id` 用于识别重启，不替代 epoch。

### 8.3 时钟偏差

| 项 | 默认 |
|---|---|
| 最大允许偏差 | 120 秒 |
| 紧急阈值 | 300 秒 |
| 判定 | 若 `issued_at > now + 120s` 或 `now > expires_at + 120s` → `CLOCK_SKEW` |
| 消息年龄 | 默认拒绝 `issued_at < now - 600s` 的消息（heartbeat 为 180s） |
| 时间源 | 控制面 NTP/PTP；节点 w32time；心跳上报 `offset_ms` 与 `source` |
| 超限处理 | 拒绝消息，返回控制面时间；节点重同步；连续超限上报 `clock_skew` 异常 |
| 紧急处理 | 偏差 >300s：节点停止接受新 Job，已启动压测在安全点继续；本地 STOP 可用 |

- `expires_at` 必须满足 `issued_at < expires_at <= issued_at + message_ttl`；否则 `INVALID_TTL`。
- 控制面时间权威；节点不得因为本地时钟偏差而延长租约或接受过期 STOP。

### 8.4 防重放决策

| 条件 | 结果 | 审计 |
|---|---|---|
| 签名有效、nonce 新、时间窗内、epoch 匹配 | 接受 | `security.message.accepted` |
| 同 message_id + 同 payload_hash | 幂等 ACK | `security.message.idempotent` |
| 同 nonce + 不同内容 | 拒绝 `REPLAY_DUPLICATE_NONCE` | `security.replay.detected` |
| `issued_at` 过旧/`expires_at` 已过 | 拒绝 `MESSAGE_EXPIRED` | `security.message.rejected` |
| `issued_at` 超前 > skew | 拒绝 `CLOCK_SKEW` | `security.clock_skew` |
| epoch 过旧/超前 | 拒绝 `EPOCH_STALE`/`EPOCH_AHEAD` | `security.epoch.rejected` |
| payload hash 不匹配 | 拒绝 `PAYLOAD_TAMPERED` | `security.tamper.detected` |
| 签名不匹配 | 拒绝 `SIGNATURE_INVALID` | `security.message.rejected` |
| 未知 key_id | 拒绝 `AUTH_UNKNOWN_KEY` | `security.key.unknown` |

## 9. 传输与网络边界

### 9.1 仅出站

- Windows Node Agent **只发起出站连接**到控制面允许列表中的 HTTPS 端点（默认 443）。
- 节点不监听入站管理端口；不运行 SSH/SCP/WinRM 服务作为协议依赖；不开启反向 shell。
- 控制面不主动连接节点；所有下行消息作为长轮询响应返回。
- 节点侧防火墙默认拒绝入站；仅允许必要的设备/系统端口，且不暴露给控制面。

### 9.2 TLS / mTLS

- TLS 1.3 优先；最低 TLS 1.2（若必须），禁用 SSLv3/TLS 1.0/1.1、RC4、3DES、NULL、EXPORT、匿名套件。
- 节点验证控制面证书链、主机名、有效期；信任锚为内部 CA。可选 SPKI pin 仅作为额外策略，默认关闭以避免轮换故障。
- 控制面验证节点客户端证书链、`node_id` 绑定、撤销状态；mTLS 通过后再验证应用层签名。
- 证书错误、主机名不匹配、撤销、过期 → 连接失败；不得 `verify=False` 或跳过主机名校验。
- 代理环境必须显式配置；不得通过不透明代理绕过证书校验。

### 9.3 长轮询

```text
节点 ── POST /v1/node/poll (mTLS, signed heartbeat/lease state) ──> 控制面
控制面 ── 200 {job|lease|stop|identity|noop} (signed) ──> 节点
节点 ── POST /v1/node/receipt (signed) ──> 控制面
```

- 长轮询超时 25 秒；空闲轮询间隔 5 秒；失败退避见第 16 节。
- 控制面每次响应最多返回一条控制消息（或 `noop`），避免大响应与顺序歧义。
- 响应必须签名；节点验证后才处理。
- 不支持 WebSocket 作为 v1 必需通道；未来可在不改变语义的前提下增加。

### 9.4 本地 IPC（Session 0 ↔ 交互式执行器）

- 使用 Windows 命名管道：`\\.\pipe\noahsark-agent-<node_id>`；设置 `PIPE_REJECT_REMOTE_CLIENTS`。
- ACL 仅允许节点服务 SID、交互式执行器用户 SID、Administrators；拒绝 Everyone/Anonymous/Network。
- 只传固定 Job 描述符与结果事实；不传自由命令、脚本或 PowerShell。
- 执行器二次校验 Job 签名、bundle digest、action 枚举与 epoch；校验失败拒绝执行。
- 管道消息有长度上限、超时、序号与 nonce；防本地重放。
- 无交互会话时，执行器不启动；节点返回 `BLOCKED_NO_INTERACTIVE_SESSION`，不得降级到 Session 0 采集音频。

## 10. 协议消息

所有消息 schema 位于 `docs/contracts/schemas/security/`，均为 JSON Schema Draft 2020-12，`additionalProperties: false`。字段以文档与 schema 为准；冲突时以本文第 1、16、17 节与已批准需求基线为准。

### 10.1 Job（控制面 → 节点）

- Schema：`job.schema.json`；`message_type=job`，`sender_role=control_plane`。
- 只表达“执行哪个冻结 action + 哪些冻结工件”，不表达自由命令。
- 关键字段：`job_id`、`attempt`、`action`、`task_id`/`revision_id`/`run_id`、`mode`、`lease_id`/`epoch`、`execution_bundle`（bundle_id/digest/artifact_refs）、`case_plan`、`device`、`constraints`、`stop_policy`。
- `action` 闭集：`static_check`、`smoke`、`formal`、`diagnostics`、`cleanup`。`stop_safe` 只经 STOP 消息；`log_query` 只经日志查询消息。
- `stop_policy.on_lease_loss` 固定为 `continue_started_job`：续约截止（`expires_at`）与通信离线**永不**停止已启动的冻结作业。需要安全停止时只能使用独立原因：`stop_policy.on_explicit_revoke=stop_safe`（控制面显式撤销租约/设备所有权变更）或 `stop_policy.on_safety_incident=stop_safe`（明确安全事件，含本地安全 STOP）。二者不得合并为 `on_lease_loss`。
- 节点执行前必须：
  1. 验证签名、nonce、时间窗、epoch、租约状态；
  2. 校验 bundle/artifact digest 与大小；并**分别**校验 bundle 格式标识（`noahsark.execution-bundle/v1`）与载荷 `schema_version`（`"1.0"`），见 §19.2（R-01）；
  3. 校验 action 在允许集合且与 mode/任务类型一致；
  4. 校验设备/端点仍在租约内；
  5. 无交互会话时返回 BLOCKED，不降级。
- 任一失败 → 拒绝并回执/异常；不得“尽力执行”。
- **禁止相等比较（R-01，2026-10-29）**：节点不得要求 bundle 格式标识等于载荷 `schema_version`，也不得用其一推导另一个。二者任一不在当前支持集合即拒绝执行，保留原始值，不猜测、不回退。

### 10.2 Lease（控制面 → 节点）

- Schema：`lease.schema.json`；`message_type=lease`。
- 关键字段：`lease_id`、`device_id`、`endpoint_set`、`job_id`、`run_id`、`epoch`、`state`、`granted_at`、`expires_at`、`heartbeat_interval_seconds`、`lease_duration_seconds`、`previous_epoch`、`allowed_actions`、`cleanup_required`。
- `state` 闭集：`granted`、`renewed`、`released`、`expired`、`revoked`、`reclaimed`。
- **`expired` 语义**：仅表示 `expires_at` 续约截止已过，**不表示设备所有权到期**，也不表示 run 失败。设备必须保持 `OCCUPIED`，直到本地停止、安全清理与占用对账完成；不得据 `expired` 重派设备或判 run 失败。
- 控制面在确认本地停止、安全清理与占用对账后才重新分配设备。
- 续约通过心跳触发；心跳响应携带 `renewed` Lease 或 `EPOCH_STALE`。
- **接收映射（C-03，2026-10-29）**：`state` 是传输事实，不是领域所有权状态。控制面按 §19.2 固定表映射到领域 `Lease.state`/`occupancy_state`；节点不得自行映射。`endpoint_set` 此处是 `endpoint_id` 身份集合，不是 kind 集合（C-04）。

### 10.3 Heartbeat（节点 → 控制面）

- Schema：`heartbeat.schema.json`；`message_type=heartbeat`。
- 同时承担：存活、租约续约请求、资源/端点/会话/时钟/身份/spool 事实上报。
- 关键字段：`boot_id`、`sequence`、`state`、`active_leases[]`、`resources`、`endpoints[]`、`interactive_session`、`clock`、`pending_stop_ack[]`、`identity`、`anomalies`。
- 心跳 `epoch` = 当前最高活跃租约 epoch；无活跃租约时为 0。
- 连续 2 次（60 秒）未收到 → 控制面标记 `communication_offline`；`expires_at` 过后线协议租约状态为 `expired`，但它只表示续约截止，不表示设备所有权到期；设备保持 `OCCUPIED` 直到对账完成。不得据 `expired` 重派设备或判 run 失败。
- 心跳不得携带原始音频、完整日志或自由文本命令。

### 10.4 STOP（双向）

- Schema：`stop.schema.json`；`message_type=stop`。
- 控制面发起的 STOP：`sender_role=control_plane`，需签名、nonce、当前 epoch。
- 本地安全 STOP：`sender_role=node`，`trigger=local_fail_safe|watchdog`，无需控制面预先授权；节点记录并尽快上报。
- 关键字段：`stop_id`、`trigger`、`mode`（`graceful|immediate_safe`）、`scope`（`current_job|all_jobs|node_drain`）、`target`、`reason_code`、`ack_deadline_seconds`、`finish_current_atomic_action`。
- 语义：STOP 不强行中断正在进行的设备原子动作；默认在当前原子动作的安全点停止。`immediate_safe` 仍只执行预定义的设备安全动作，不执行任意命令。
- 重连时 **STOP-first**：节点先拉取/处理待处理 STOP，再补传回执/证据，再去重与对账。
- 过期 STOP 不得执行；控制面在重连时用新 nonce/时间重新签名下发。离线期间本地安全 STOP 仍有效。

### 10.5 Receipt（节点 → 控制面）

- Schema：`receipt.schema.json`；`message_type=receipt`。
- 关键字段：`receipt_id`、`job_id`、`attempt`、`lease_id`、`epoch`、`sequence`、`status`、`started_at`/`finished_at`、`outcome`（节点观察事实）、`facts`、`error`、`evidence_manifest`、`cleanup_receipt`、`artifacts[]`、`log_query_result`、`idempotency_key`、`node_boot_id`。
- 节点只能回传事实：`outcome` 的五个字段**全部**命名为 `node_observed_execution_status`、`node_observed_validity_status`、`node_observed_business_verdict`、`node_observed_evidence_status`、`node_observed_verification_status`，并固定 `used_for_decision: false`。这些字段不是平台轴，`node_observed_verification_status` 固定 `NOT_RUN`；最终 `business_verdict`/`verification_status` 由 Linux 独立复核。
- `evidence_manifest.schema_version` 必须为 `"1.0"`，与权威 evidence manifest 一致；`predicate_type: "noahsark.test-evidence/v1"` 只版本化 predicate 词汇，不是载荷 schema 版本。未知版本 fail-closed。
- `cleanup_receipt` 是设备释放前置条件的**最小投影的安全侧超集**（R-02，2026-10-29）：与 `schemas/domain/receipt.schema.json` 共享的必填字段及 `cleanup_status` 词表（`completed`/`completed_with_warnings`/`failed`/`not_required`/`unknown`）必须逐字一致：`cleanup_receipt_id`、`cleanup_status`、`local_stop_confirmed`、`safe_cleanup_done`、`occupancy_reconciled`、`completed_at`，可选 `notes`。
  - `operational_detail` 只是**传输期便捷载体**，入域前必须裁剪；domain 以 `additionalProperties: false` 显式拒绝该字段。
  - 清理步骤/资源等详细运维信息的**唯一权威位置**是 `schemas/evidence/cleanup-receipt.schema.json`，由 `cleanup_receipt_id` 引用。
  - 消费方不得假设两侧可互相反序列化；跨侧转换按 `evidence-verdict.md` §12.1.1 逐字段进行，未知字段丢弃并审计。
  - 历史记录（2026-10-28，已被本日裁决取代）：原文曾称两侧为“同一最小释放投影”，并暗示详细字段可放 `operational_detail`；该表述自 2026-10-29 起不再作为规范。
- 回执的 `status` 是线协议回执生命周期，不是领域 `job_kind`/`run.status`；映射见 §19.2。
- 回执可 spool 在本地；重连后按 `(job_id, attempt, sequence)` 去重补传。
- 旧回执用 `key_id` 历史验签；见 6.5。

### 10.6 Log Query（控制面 → 节点）

- Schema：`log-query.schema.json`；`message_type=log_query`。
- 只读、白名单、范围受限；结果通过 Receipt 的 `log_query_result` 分片返回。
- 关键字段：`query_id`、`task_id`/`revision_id`/`run_id`、`cursor`、`lease_id`/`epoch`、`requested_by`、`purpose`、`sources[]`、`path`、`windows_event`、`time_range`、`limits`、`redaction`、`approval`、`delivery`、`audit`。
- 详见第 12 节。

### 10.7 Anomaly Event（节点 → 控制面）

- Schema：`anomaly-event.schema.json`；`message_type=anomaly_event`。
- 关键字段：`anomaly_id`、`category`、`severity`、`detected_at`、任务/运行/作业/租约/设备/端点引用、`summary`、`facts`、`evidence_refs[]`、`recommended_action`、`local_action_taken`、`dedupe_key`、`occurrence_count`。
- `recommended_action` 是建议，不是命令；控制面决定是否 STOP/隔离/人工复核。
- 节点可主动上报，也可由控制面日志查询读取；两条路径按 `dedupe_key` 关联去重。

### 10.8 Enrollment / Identity

- `node-enrollment.schema.json`：节点 → 控制面，`message_type=node_enrollment`，自签名 + 一次性 token。
- `node-identity.schema.json`：控制面 → 节点，`message_type=node_identity`，含证书、`key_id`、`key_generation`、`identity_status`、协议参数、撤销信息。
- `node_identity` 是节点后续信任控制面参数的来源；节点必须校验签名与 `node_id`/`key_id` 绑定。

## 11. 允许命令闭集（Command Catalog v1）

节点没有通用命令解释器。`job.action` 与固定处理器一一对应，**不存在 `command`/`argv`/`script` 字段**：

| `action` | 固定处理器 | 允许的副作用 | 禁止 |
|---|---|---|---|
| `static_check` | `lstest preflight/probe` 只读检查 | 读文件、编译 profile、探测端点存在 | 设备动作、音频播放/采集、写注册表 |
| `smoke` | 固定 smoke runner + 适配器 | 有界真实设备动作、短时音频、证据采集 | 进入正式分母、生成/修改脚本、长期压测 |
| `formal` | 固定 formal runner + 冻结 bundle | 按批准样本执行、证据采集、长时压测 | 改判据、改音频、改异常规则、跳过 preflight |
| `diagnostics` | 固定只读探针 | 端点/版本/健康/容量/会话检查 | 设备动作、任意文件读取、任意事件日志通道 |
| `cleanup` | 固定清理器 | 清理 run 工作区、终止本 run 子进程、释放句柄 | 删除 run root 外文件、格式化、改系统配置 |

补充规则：

1. `stop_safe` 只通过 STOP 消息触发，属于固定安全例程；不是 Job action。
2. `log_query` 只通过日志查询消息触发，属于只读白名单读取；不是 Job action。
3. 适配器操作（如 `play`、`dual-play`、`tts`、`scan`）由冻结 bundle 内的固定步骤调用，不能由控制面自由拼接为命令字符串。
4. 任何未知 action、未知 adapter、未知 bundle 版本 → 拒绝并审计；不得猜测或回退到 shell。“未知 bundle 版本”必须拆成两个独立判断：bundle 格式标识未知、载荷 `schema_version` 未知；任一未知即拒绝（R-01）。
5. 节点侧禁止 `subprocess` 拼接未白名单参数、禁止 `powershell -Command`、禁止 `cmd /c`、禁止 `ssh`。
6. 节点回执若因版本轴拒绝，使用 `SCHEMA_INVALID`，并在 `facts` 写 `bundle_format_supported`、`bundle_payload_schema_supported` 两个 boolean；不得假设回执 `error` 存在 `subject`，也不得把控制面 `SCHEMA_VERSION_UNSUPPORTED` 直接写入节点闭集（E-05）。
7. 端点 kind 只作能力匹配；`endpoint_set` 的元素必须是稳定 `endpoint_<32hex>` 身份。`audio_input`/`audio_output` 只是入站别名，入域前归一为 `audio_capture`/`audio_playback`；写出方只发权威词（C-04）。

## 12. 日志查询白名单、路径、范围、脱敏与审计

### 12.1 数据源白名单

| `source` | 解析到 | 说明 |
|---|---|---|
| `tool_log` | run 根下 `tool.log` | 唯一人读账本 |
| `serial_log` | `serial_logs/*.log` | 连续串口原始证据；可用 `path` 指定具体文件 |
| `results_csv` | `results.csv` | 结构化的逐 case 结果 |
| `cases_csv` | `cases.csv` | 设备动作前冻结的 case 清单 |
| `run_manifest` | `evidence/run_manifest.json` | 运行 manifest |
| `runner_stdout` | `logs/runner-stdout.log` | 固定 runner 标准输出 |
| `runner_stderr` | `logs/runner-stderr.log` | 固定 runner 标准错误 |
| `windows_event_log` | 固定通道/提供程序 | 只允许 `System`、`Application`、`NoahsArk-Agent` 与白名单 provider |

不在白名单的 source、任意路径、任意事件日志通道一律拒绝。

### 12.2 路径约束

若提供 `path`，必须同时满足：

1. 相对路径；正斜杠分隔；长度 ≤512；深度 ≤8。
2. 禁止绝对路径、盘符（`C:`）、UNC（`\\`）、备用数据流（`:`）、`..` 段、`.` 段、空段、双斜杠。
3. 字符集仅 `[A-Za-z0-9._/-]`；禁止通配符、环境变量、`~`、控制字符。
4. 规范化（realpath）后必须位于该 `run_id` 的 run root 内；拒绝符号链接/junction 穿越。
5. 扩展名仅 `.log`、`.txt`、`.json`、`.jsonl`、`.csv`、`.xml`。
6. 仅允许读取普通文件；拒绝设备、管道、目录、注册表、ADS、内存映射。
7. `windows_event_log` 不使用 `path`，只接受 `channel` 与 `provider` 白名单。

### 12.3 范围与配额

| 限制 | 默认 |
|---|---|
| 时间范围 | 默认 ≤24 小时；硬上限 7 天 |
| 单次最大行数 | 默认 50,000；硬上限 200,000 |
| 单分片最大字节 | 256 KiB（base64 后 ≤350 KiB） |
| 单次查询总字节 | 默认 8 MiB；硬上限 64 MiB |
| 分片大小 | 默认 256 KiB；硬上限 256 KiB，只能收紧 |
| 并发查询/节点 | 默认 5；硬上限 20 |
| 查询超时 | 默认 30 秒；硬上限 120 秒 |
| 最大文件 | 由 run 证据策略决定；超出则流式分片，不一次性读入 |
| 游标 | 请求用 `cursor` 续取分片；节点生成 opaque token，绑定 `query_id`，≤256 字符；不得由客户端构造任意偏移 |
| 编码 | `utf-8` / `utf-16le`；按 BOM 或显式声明 |

- 查询按行/字节双上限截断；返回 `truncated=true` 与 `next_cursor`。
- 不允许 `follow`/`tail -f` 长期挂起；只读快照。
- 日志查询不得触发设备动作、不得执行日志中的任何内容。

### 12.4 脱敏

| `profile` | 行为 | 授权 |
|---|---|---|
| `standard` | 默认；按命名规则脱敏邮箱、IP、SID、用户名、主机名、路径、token-like、手机号、MAC | 任务授权角色 |
| `strict` | 额外脱敏设备标识、文件名、音频文件名、自由文本中的长数字 | 任务授权角色 |
| `none` | 不脱敏；仅限特权账户 + 审批 + 高审计 | 最高权限 + `approval_ref` |

- `profile=none` 时必须同时满足：`allow_privileged_raw=true`、提供 `approval_ref`/`approved_by`、请求者具备最高权限；否则拒绝并审计。
- 脱敏规则以**命名规则 ID 闭集**传递，不接受任意正则，避免 ReDoS 与绕过。
- 默认返回脱敏后内容；`content_sha256` 对返回内容计算。
- `none` 必须记录 `approval_ref`、`approved_by`、`reason`，触发高优先级审计与告警。
- 原始音频不通过日志查询返回；只返回音频文件元数据/证据引用。

### 12.5 日志查询审计

每次查询记录：

```text
query_id, requested_by, purpose, reason_code,
task_id/revision_id/run_id/node_id/lease_id/epoch,
sources[], resolved_path (redacted), time_range,
limits, redaction_profile, redaction_rules,
approval_ref, bytes_returned, lines_returned,
truncated, result (allowed/denied/error), error_code,
started_at, finished_at, audit_event_id
```

- 拒绝、越权、路径越界、未审批 `none` 必须写高优先级安全审计。
- 审计保留不短于被访问记录的寿命；安全审计至少 400 天。

## 13. 离线行为与重连

### 13.1 离线定义

- 控制面连续 2 次心跳（60 秒）未收到 → `communication_offline`。
- `expires_at` 续约截止已过 → 线协议租约状态 `expired`（仅表示续约截止，不表示所有权到期）；**设备仍视为 `OCCUPIED`**，不得分配给其他任务，也不得据此判 run 失败，直到本地停止、安全清理与对账完成。
- 节点侧无法连接控制面 → 进入 `offline`；本地继续已启动的冻结压测。

### 13.2 离线规则

| 场景 | 行为 |
|---|---|
| 已启动的冻结压测 | **继续执行**到完成/安全点；不因通信中断而中止；不重播音频、不重复采样 |
| 新 Job | **不接受**；控制面不派发；节点不自行创建 |
| 新 STOP（远端） | 无法送达；控制面排队，重连后重签下发 |
| 本地安全 STOP | **可用**；操作者/看门狗可在本地触发固定安全停止；签名记录，重连上报 |
| 设备占用 | 保持；不因租约过期而释放给其他任务 |
| 证据/回执 | 本地 spool；重连后补传、去重、对账 |
| 时钟 | 继续本地计时；记录 offset；不延长租约 |
| 身份 | 证书过期/撤销无法即时获知；重连后立即校验，必要时 drain |

### 13.3 重连顺序（STOP-first）

```text
1. 建立 mTLS + 校验控制面签名/时间
2. 拉取并处理 pending STOP（按 stop_id 去重；过期 STOP 请求重签）
3. 上报 heartbeat + identity + pending_stop_ack
4. 补传 spool 回执/证据引用（按 job_id/attempt/sequence 去重）
5. 对账：lease/epoch/device occupancy/run 状态
6. 仅在控制面确认后接受新 Job
```

- 重连期间不得重跑已完成 Job；不得把旧 epoch 回执当作新状态。
- 若控制面发现节点 epoch 落后/超前，先对账再决定是否继续；不得静默重置。
- 对账结果写 `offline.reconciled` 审计，包含差异与处理。

## 14. 消息大小、深度与资源限制

| 项 | 默认 | 超限行为 |
|---|---|---|
| 控制消息（信封+payload） | 1 MiB | 413 `MESSAGE_TOO_LARGE` |
| 日志查询请求 | 64 KiB | 413 |
| 日志结果分片（base64 前） | 256 KiB | 截断/分片 |
| Receipt facts | 1 MiB | 413；证据走独立上传 |
| Manifest 上传 | 4 MiB | 413 |
| JSON 深度 | 32 | 400 `JSON_TOO_DEEP` |
| 单对象属性数 | 256 | 400 |
| 单数组元素数 | 10,000 | 400 |
| 单字符串长度 | 64 KiB | 400 |
| HTTP 请求体 | 4 MiB | 413 |
| 长轮询响应 | 1 MiB | 控制面分页/单消息 |
| 压缩 | 可选 gzip；解压后 ≤4 MiB；压缩比 ≤20:1 | 400/413 |

- 所有限制在解析前后都检查，防止压缩炸弹/深度攻击。
- 节点对本地 spool 设置上限（默认 2 GiB 或 D: 容量的 10%，取较小者）；达到上限停止接新 Job 并上报 `spool_overflow`。

## 15. 失败行为

| 失败 | 错误码 | 控制面/节点行为 | 审计 |
|---|---|---|---|
| 未知 `key_id` | `AUTH_UNKNOWN_KEY` | 拒绝；不改变状态；10 分钟内 5 次 → 临时封禁 15 分钟 | `security.key.unknown` |
| 证书过期 | `AUTH_CERT_EXPIRED` | 拒绝新 Job；节点进入续期；已启动工作在安全点完成/STOP | `identity.expired` |
| 证书/密钥撤销 | `AUTH_KEY_REVOKED` | 拒绝新消息；节点 drain；完成/安全停止 | `identity.revoked` |
| 签名不匹配 | `SIGNATURE_INVALID` | 拒绝；不执行；重复则告警 | `security.message.rejected` |
| payload 被篡改 | `PAYLOAD_TAMPERED` | 拒绝；告警；重复/疑似泄露 → 撤销密钥 | `security.tamper.detected` |
| nonce 重复（不同内容） | `REPLAY_DUPLICATE_NONCE` | 拒绝；告警；累计触发封禁 | `security.replay.detected` |
| 消息过期 | `MESSAGE_EXPIRED` | 拒绝；STOP 可由控制面重签 | `security.message.rejected` |
| 时钟偏差超限 | `CLOCK_SKEW` | 拒绝；返回控制面时间；节点重同步；>300s 停新 Job | `security.clock_skew` |
| epoch 过旧 | `EPOCH_STALE` | 拒绝变更；终态回执在 grace 内可幂等记录 | `security.epoch.rejected` |
| epoch 超前 | `EPOCH_AHEAD` | 拒绝；告警；对账 | `security.epoch.rejected` |
| 未知 action | `ACTION_NOT_ALLOWED` | 拒绝；绝不解释为 shell/命令 | `security.action.rejected` |
| 未知字段/类型 | `SCHEMA_INVALID` | 拒绝；不部分执行 | `security.message.rejected` |
| 消息过大/过深 | `MESSAGE_TOO_LARGE` / `JSON_TOO_DEEP` | 拒绝 | `security.message.rejected` |
| 租约不活跃/不属于该节点 | `LEASE_NOT_ACTIVE` | 拒绝 Job/STOP | `lease.rejected` |
| 设备被占用 | `DEVICE_BUSY` | 拒绝新租约/Job | `lease.conflict` |
| 工件 digest 不匹配 | `ARTIFACT_MISMATCH` | 拒绝执行；上报异常；不重试同一工件 | `artifact.mismatch` |
| 无交互会话 | `BLOCKED_NO_INTERACTIVE_SESSION` | 回执 BLOCKED；不降级；不产生 PASS | `session.unavailable` |
| 重复 Job（同 job_id/attempt） | 幂等 | 返回首次结果；不重复执行 | `job.idempotent` |
| 节点本地 STOP | `LOCAL_SAFE_STOP` | 执行固定安全停止；重连上报 | `stop.local` |
| 控制面不可达 | `CONTROL_PLANE_UNREACHABLE` | 节点离线继续已启动工作；不接新 Job | `offline.detected` |

## 16. 运行默认值与配置优先级

### 16.1 默认值

| 配置 | v1 默认 | 硬上限/下限 | 任务级可覆盖 |
|---|---|---|---|
| 身份模式 | X.509 + Ed25519 + mTLS | 不得关闭 mTLS/签名 | 否 |
| 证书有效期 | 90 天 | 1–365 天 | 否（节点级） |
| 续期启动 | 第 60 天 | 不得晚于到期前 7 天 | 否 |
| 轮换重叠 | 7 天 | 0–30 天 | 否 |
| 签名算法 | Ed25519 | 允许 ES256 迁移重叠 | 否 |
| payload hash | SHA-256 | 不得弱于 SHA-256 | 否 |
| nonce 保留 | 900 秒 | ≥600 秒 | 否 |
| 消息 TTL（Job/Lease/STOP） | 300 秒 | 30–600 秒 | 可缩短 |
| 心跳 TTL | 90 秒 | 30–180 秒 | 可缩短 |
| Enrollment 消息 TTL | 300 秒 | 60–600 秒 | 否 |
| Enrollment token TTL | 900 秒（15 分钟） | 60–3600 秒 | 否 |
| 最大时钟偏差 | 120 秒 | 30–180 秒 | 可收紧 |
| 紧急时钟阈值 | 300 秒 | 120–600 秒 | 否 |
| 心跳间隔 | 30 秒 | 10–60 秒 | 可缩短 |
| 租约时长 | 60 秒 | 30–300 秒 | 可延长至 300 秒 |
| 租约过期宽限 | 30 秒 | 0–60 秒 | 可收紧 |
| 长轮询超时 | 25 秒 | 10–50 秒 | 否 |
| 空闲轮询间隔 | 5 秒 | 1–30 秒 | 可缩短 |
| 重试初始/上限 | 1 秒 / 60 秒 | 上限 ≤300 秒 | 可收紧 |
| 重试抖动 | 20% | 0–50% | 可收紧 |
| 连续失败离线阈值 | 10 次 | 3–20 次 | 可收紧 |
| Receipt spool 重试 | 24 小时 | ≤7 天 | 可延长 |
| Receipt 重试最大退避 | 300 秒 | ≤600 秒 | 可收紧 |
| STOP ACK 期限 | 30 秒 | 5–120 秒 | 可收紧 |
| Enrollment token 熵 | 256-bit | ≥128-bit | 否 |
| 控制消息大小 | 1 MiB | ≤4 MiB | 可收紧 |
| 日志查询请求 | 64 KiB | ≤256 KiB | 可收紧 |
| 日志分片 | 256 KiB | ≤256 KiB | 可收紧 |
| Manifest 上传 | 4 MiB | ≤16 MiB | 可收紧 |
| 日志时间范围 | 24 小时 | ≤7 天 | 可收紧 |
| 日志行数 | 50,000 | ≤200,000 | 可收紧 |
| 日志总字节 | 8 MiB | ≤64 MiB | 可收紧 |
| 并发日志查询 | 5 | ≤20 | 可收紧 |
| 日志查询超时 | 30 秒 | ≤120 秒 | 可收紧 |
| Job 最大执行时长 | 24 小时 | ≤7 天 | 可延长至 7 天 |
| Job 最大 attempt | 10 | ≤20 | 可收紧 |
| 审计保留（安全事件） | max(记录寿命, 400 天) | 不得短于记录寿命 | 否 |
| 公钥历史保留 | max(退役后 2 年, 引用记录寿命) | 不得短 | 否 |

### 16.2 优先级

1. **硬安全边界（H）** 永远最高；任何配置不得放宽 H。
2. **统一六层优先级（从低到高）**：`schema_default < global_default < environment < task_revision < run_override < hard_safety_floor`。`schema_default` 是显式最低层（本文 §16.1 的默认值）；`node` 与 `environment` 是**同一层**（节点配置文件即环境层），不是独立的一层。历史写法 `task > node > global > schema_default` 仅作为层间语义说明保留（`task_revision` 高于 `environment`，`node` 即 `environment`），不再作为独立的活动优先级列表。
3. **安全类限制**（时钟偏差、nonce/TTL、消息大小、日志范围、脱敏、证书有效期）：`effective = most_restrictive(schema_default, global_default, environment, task_revision, run_override) ∩ hard_safety_floor`。只能收紧。
4. **运行类参数**（心跳、租约、重试、轮询、Job 最大时长）：按上述六层顺序解析，`task_revision`/`run_override` 高于 `environment` 与 `global_default`；`run_override` 仅限冻结修订 `run_override_allowlist` 显式声明的运维键，且仍受 H 约束。
5. **节点身份文档** 中的协议参数由控制面签发；节点不得本地放宽，只能选择更严格值。
6. **未知/缺失配置**：fail-closed 使用 H 或默认安全值，不得“关闭校验”。
7. **任务级覆盖** 必须写入冻结修订或任务批准记录；不得在运行时由节点临时覆盖。
8. **优先级冲突**：以更严格值为准；若任务要求更宽松但超过 H → 拒绝任务冻结/派发并记录 `CONFIG_OUT_OF_BOUNDS`。

### 16.3 任务级覆盖点

允许任务级覆盖的项：

- 单 Job 最大执行时长（≤7 天）、最大 attempt（≤10）。
- 日志查询时间范围/行数/字节/并发（只能收紧）。
- 重试次数/预算（只能收紧）。
- STOP ACK 期限（只能收紧）。
- 脱敏 profile（`strict` 可强制；`none` 仍需特权审批）。
- 证据必要集合与保留策略（不得低于基线）。

不允许任务级覆盖的项：

- 关闭 mTLS/签名/nonce/epoch/时钟检查。
- 放宽 H、证书有效期、nonce 保留、最大消息大小、路径白名单。
- 引入 shell/PowerShell/SSH/自由命令。
- 让节点写最终 `business_verdict`/`verification_status`。

## 17. 审计事件

所有审计事件追加写入，UTC，带 `event_id`、`occurred_at`、`actor`、`action`、`object`、`before`、`after`、`reason`、`correlation`（`task_id`/`revision_id`/`run_id`/`job_id`/`node_id`/`lease_id`/`message_id`）、`result`。节点本地审计 spool 后上传；控制面审计为权威。安全审计事件建议使用哈希链（`prev_event_hash` + `event_hash`）防篡改。

| 事件 | 触发 | 关键字段 |
|---|---|---|
| `node.enrollment.created` | 管理员创建 enrollment | enrollment_id, created_by, expires_at |
| `node.enrollment.requested` | 收到注册请求 | node_id, key_id, token_hash_prefix, source_ip |
| `node.enrollment.approved` / `.rejected` | 审批 | approver, reason |
| `node.enrollment.expired` / `.consumed` | token 状态 | enrollment_id |
| `identity.issued` | 签发证书 | node_id, key_id, serial, not_after |
| `identity.renewed` | 续期 | old/new serial, not_after |
| `identity.rotated` | 轮换 | previous_key_id, new_key_id, key_generation |
| `identity.revoked` | 撤销 | key_id, reason, revoked_at, compromise_time |
| `identity.expired` | 证书过期 | node_id, key_id |
| `identity.expiring` | 到期告警 | days_remaining |
| `security.message.accepted` | 验签通过 | message_type, message_id, key_id |
| `security.message.rejected` | 验签/结构失败 | error_code, message_type |
| `security.message.idempotent` | 重发命中 | message_id |
| `security.key.unknown` | 未知 key_id | key_id, node_id |
| `security.replay.detected` | nonce 重放 | key_id, nonce, message_id |
| `security.tamper.detected` | payload 篡改 | message_id, expected/actual hash |
| `security.clock_skew` | 时钟超限 | offset_ms, threshold |
| `security.epoch.rejected` | stale/ahead | expected_epoch, got_epoch |
| `security.action.rejected` | 未知 action | action, message_id |
| `lease.granted` / `.renewed` / `.expired` / `.released` | 租约生命周期 | lease_id, device_id, epoch |
| `lease.rejected` / `.conflict` | 租约失败 | reason, device_id |
| `job.dispatched` / `.accepted` / `.started` / `.completed` / `.failed` / `.rejected` | 作业生命周期 | job_id, attempt, action |
| `job.idempotent` | 重复作业 | job_id, attempt |
| `stop.requested` / `.acknowledged` / `.completed` | STOP | stop_id, trigger, scope |
| `stop.local` | 本地安全停止 | stop_id, operator_present |
| `artifact.mismatch` | 工件哈希不符 | artifact_id, expected/actual |
| `log.query.requested` / `.completed` / `.denied` / `.error` | 日志查询 | query_id, sources, path, redaction, bytes |
| `log.query.raw_accessed` | `none` 脱敏查询 | query_id, approval_ref |
| `anomaly.reported` / `.acknowledged` | 异常 | anomaly_id, category, severity |
| `session.unavailable` | 无交互会话 | job_id, session_type |
| `offline.detected` / `.reconnected` / `.reconciled` | 断线/重连/对账 | node_id, lease_id, diff |
| `spool.overflow` | spool 满 | bytes, limit |
| `config.out_of_bounds` | 配置超界 | key, requested, hard_limit |

## 18. 决策记录（Decisions Taken）

| ID | 决策 | 理由 | 被拒绝的替代方案 | 任务级覆盖点 |
|---|---|---|---|---|
| SN-01 | 采用 X.509 设备证书 + Ed25519 应用签名 + mTLS | 可撤销、可轮换、非否认、与 TLS 信任链一致 | 长期 bearer token（泄露可重放）、PSK（难轮换/难归因） | 无；仅允许 ES256 迁移重叠 |
| SN-02 | 仅出站长轮询；无入站管理端口 | 穿 NAT、减少攻击面、符合 Windows 节点部署 | WebSocket 双向（v1 非必需）、入站 RPC（扩大攻击面） | 无 |
| SN-03 | 命令闭集 + 固定处理器；无自由命令字段 | 从协议层消除远程 shell/命令注入 | 通用 `command`/`argv`（被明确拒绝） | 无 |
| SN-04 | 一次性 enrollment token + 本地密钥 + 人工批准 | 避免预共享长期密钥；token 泄露影响有限 | 自动信任首次连接（TOFU）、共享 PSK | staging 可显式自动批准；生产不可 |
| SN-05 | nonce 128-bit，保留 900 秒 | 覆盖 TTL + 时钟偏差，成本低 | 仅时间戳（可重放）、仅 message_id（碰撞/重放窗口） | 可延长，不可缩短到 <600s |
| SN-06 | epoch 作为租约 fencing token | 防止旧节点/旧租约写入新状态 | 仅 lease_id（无法区分旧持有者） | 无 |
| SN-07 | 最大时钟偏差 120 秒，紧急 300 秒 | 容忍 NTP 抖动，同时限制重放窗口 | 无限制（重放风险）、<30 秒（运维脆弱） | 可收紧 |
| SN-08 | 心跳 30 秒、租约 60 秒 | 与架构“心跳为租约一半”一致；快速发现离线 | 心跳 5 秒（开销大）、租约 300 秒（发现慢） | 可缩短/延长至硬上限 |
| SN-09 | 消息 TTL 300 秒（heartbeat 90 秒） | 限制重放窗口；STOP 可由控制面重签 | 永久有效（重放）、极短（时钟敏感） | 可缩短 |
| SN-10 | 离线已启动压测继续；STOP-first 重连 | 满足 AC-11/AC-12；避免重跑与重复采样 | 断线即失败（丢长时压测）、重连即重跑（重复采样） | 无 |
| SN-11 | 本地安全 STOP 无需远端授权 | 失效安全；断线时仍能降低设备风险 | 必须远端批准（断线无法停止） | 无 |
| SN-12 | 日志查询白名单 + 命名脱敏规则 + 审计 | 防止任意文件读取与隐私泄露 | 任意路径读取（越权）、任意正则（ReDoS/绕过） | 可收紧；`none` 需特权审批 |
| SN-13 | 旧公钥保留 ≥2 年/引用寿命 | 旧回执仍可验签；满足审计追溯 | 轮换即删旧公钥（历史回执不可验） | 无 |
| SN-14 | 安全类配置取最严格值 | 防止任务级放宽破坏基线 | 任务级覆盖一切（可关闭校验） | 只能收紧 |
| SN-15 | Session 0 服务与交互执行器用本地命名管道 + 二次校验 | 满足 Windows 会话隔离；不暴露远程 IPC | 服务直接采集音频（Session 0 不可用）、TCP 本地端口（扩大攻击面） | 无 |

## 19. 与其它契约的关系

- 领域对象（Task/Revision/Run/Case/Attempt/Gate/Device/Node）见 `docs/contracts/domain.md` 与 `schemas/domain/`。
- 本文的 `Lease`、`Receipt`、`Job` 是**节点协议消息**，与领域 `ResourceLease`/`Receipt` 实体字段对齐但不互相替代：领域实体是控制面事实，协议消息是传输中的签名信封。
- 证据 manifest 结构由证据契约冻结；本文只定义 `evidence_manifest_ref` 与 digest 校验点。
- 五轴判定与 fail-closed 规则见领域契约；节点回执的 `verification_status` 固定 `NOT_RUN`。

### 19.1 与领域契约的对齐点（Orchestrator 评审确认）

1. **ID 表示**：本文线协议 `node_<hex>`/`job_<hex>`/`lease_<hex>` 与 `schemas/domain/` 的 canonical UUID 是一对一别名，映射见 4.5；不得为同一对象维护第二套身份。
2. **租约到期语义**：`expired` 仅表示续约截止，不是所有权到期；设备保持 `OCCUPIED`，直到本地停止、安全清理与占用对账完成；不得据 `expired` 重派设备或判 run 失败。`state` 到领域状态的固定接收映射见 §19.2（C-03）。
3. **回执字段**：`receipt.outcome` 是节点观察事实，不是平台判定；API/报告必须映射为 `node_observed`，不得直接写入 `business_verdict`/`verification_status`。
4. **cleanup 回执**：`receipt.cleanup_receipt` 是 domain 最小释放投影的**安全侧超集**；`schemas/evidence/cleanup-receipt.schema.json` 是清理步骤/资源/状态的唯一权威定义。共享必填字段与 `cleanup_status` 词表逐字一致；`operational_detail` 仅传输期存在，入域前裁剪（R-02）。
5. **证据与判定**：本文不定义 manifest 细节和最终判定算法；以证据/判定契约为准。节点只提供事实引用与 digest。
6. **Bundle 版本轴（R-01）**：`noahsark.execution-bundle/v1`（格式标识）与 `"1.0"`（载荷 schema 版本）是两个独立轴，节点分别校验，禁止相等比较或互相推导。

### 19.2 协议词汇与领域词汇映射（v1）

线协议消息的 `action`/`mode`/`status` 是节点作业与传输生命周期词汇；领域 `Receipt.job_kind`、`Run.mode`、`Run.lifecycle_status` 是控制面事实词汇。二者不得混用；固定映射如下。

**Job action / mode → 领域 Receipt.job_kind / Run.mode**

| 协议 `job.action` | 协议 `job.mode` | 领域 `Receipt.job_kind` | 领域 `Run.mode` | 说明 |
|---|---|---|---|---|
| `static_check` | `static` | `static_check` | `static` | 静态检查运行。 |
| `smoke` | `smoke` | `smoke` | `smoke` | 烟测独立 run，不计入正式分母。 |
| `formal` | `formal` | `formal` | `formal` | 正式采样运行。 |
| `diagnostics` | `diagnostics` | `diagnostics` | 不改变 | 辅助作业；不得新建或改写 Run.mode。 |
| `cleanup` | `cleanup` | `cleanup` | 不改变 | 清理作业；产出 cleanup_receipt，不改变 Run.mode，也不产生新的 Run。 |
| （STOP 路径，无 `job.action`） | — | `stop_safe` | 不改变 | STOP 指令或本地安全停止产生的回执归为 `stop_safe`，不是 `cleanup`。 |

- `cleanup` 与 `diagnostics` 是辅助作业，永远不得改变 `Run.mode`；`Run.mode` 仍只有 `static`/`smoke`/`formal`。
- 节点不得自行把 `action` 映射为领域判定；映射由控制面在接收、验证回执时完成。

**线协议 `receipt.status` → evidence manifest `node_receipt.status`**

| `security/receipt.status` | `evidence-manifest.node_receipt.status` | 说明 |
|---|---|---|
| `accepted` | `received` | 作业已接收，尚未开始执行。 |
| `started` | `started` | 节点已开始执行。 |
| `completed` | `completed` | 执行正常结束（不等于 PASS）。 |
| `failed` | `failed` | 执行失败；业务判定仍由 Linux 独立计算。 |
| `stopped` | `aborted` | 显式停止；不得写成 `completed`。 |
| `blocked` | `aborted` | 因前置条件/交互会话等阻塞而未完成；原因保留在 `error`/facts。 |
| `infra_error` | `failed` | 基础设施错误，不是业务 FAIL；错误类别保留在 `error.code`。 |
| `cleanup_complete` | `completed` | 清理作业结束；清理结果以 `cleanup_receipt.cleanup_status` 表达。 |
| `rejected` | `unknown` | 回执未通过校验，不得作为可信生命周期事实。 |

- 映射只用于证据清单的只读投影；原始线协议 `status` 必须保留在回执中，便于追溯。
- 未知或无法映射的值一律投影为 `unknown`，并按 fail-closed 标记，不得猜测为 `completed`。
- evidence 的 `node_receipt.status` 不是领域 `Receipt.chain_status`；后者按 `RECEIVED → VALIDATED → RECONCILED` / `REJECTED` 独立维护。
- 同一映射在 `domain.md` §12.3 与 `evidence-verdict.md` §12.5 中被引用，三处不得出现不同取值。

**线协议 `lease.state` → 领域 `Lease.state` / `occupancy_state`（C-03，2026-10-29）**

仅由控制面执行；节点不得自行映射。完整守卫见 `domain.md` §11.2。

| 线协议 `lease.state` | 领域 `Lease.state` | `occupancy_state` | 说明 |
|---|---|---|---|
| `granted` | `GRANTED` | `OCCUPIED` | 领取确认后才 `HELD`；确认不是线协议状态值。 |
| `renewed` | `HELD` | `OCCUPIED` | 只延长 `expires_at`；当前 `RECLAIM_PENDING` 时保持不恢复。 |
| `released` | `RELEASING`，三项前置条件通过后 `RELEASED` | `OCCUPIED`，通过后 `IDLE` | 线协议值只是释放主张。 |
| `expired` | 不降级不升级；`HELD`+离线→`RECLAIM_PENDING` | `OCCUPIED` | 永不映射 `RELEASED`/`IDLE`。 |
| `revoked` | `RELEASING` | `OCCUPIED` | STOP-first；清理失败/安全事件可 `QUARANTINED`。 |
| `reclaimed` | `RECLAIM_PENDING` | `OCCUPIED` | 不得直接跳 `RELEASED`。 |
| 表外值 | 不改变当前状态 | 保持原值 | 审计告警；不释放、不重派、不停止已启动 run。 |

**端点 kind 双向映射与身份规则（C-04，2026-10-29）**

| 线协议/入站别名 | 权威 domain `endpoint_kind` | 方向 |
|---|---|---|
| `audio_input` | `audio_capture` | 入站别名 → 权威 |
| `audio_output` | `audio_playback` | 入站别名 → 权威 |
| `audio_capture` / `audio_playback` / `serial` / `usb` | 同名 | 双向一致 |
| `network` / `display` | 无（仅节点能力标识） | V0.0.1 不可占用，待 T-10 |
| `gpio` | `gpio`（domain 能力） | 线协议暂无；新增需 T-10 |

- `endpoint_set` = **端点身份集合**，元素为稳定 `endpoint_<32hex>`；`endpoint_kind` 只用于能力匹配与 `required_kinds`。
- 占用键 `(node_id, device_id, endpoint_set)` 中的 `endpoint_set` 是身份集合；同设备同类两个不同 `endpoint_id` 不构成冲突。
- 未知 kind 或未知端点身份 → fail-closed，不授予占用、不生成租约。

**节点错误词表与版本轴拒绝（R-01/E-05，2026-10-29）**

`security/receipt.schema.json` 的 `error.code` 是节点侧独立闭集，`additionalProperties: false` 且没有 `subject`；它与控制面 `domain.md` §18 的错误码不是同一词表。版本轴拒绝使用 `SCHEMA_INVALID`，并在 `facts` 写：

| facts 键 | 类型 | 含义 |
|---|---|---|
| `bundle_format_supported` | boolean | bundle 格式标识是否在当前支持集合。 |
| `bundle_payload_schema_supported` | boolean | 载荷 `schema_version` 是否在当前支持集合。 |

不得用 `message` 文本表达机器语义；如未来需要一等错误码，只能走 `error.code` 枚举扩展并同步控制面映射。

## 20. 未决问题

1. 目标 Windows 版本/CNG 是否全面支持 Ed25519 X.509；若不支持，ES256 迁移窗口与双算法重叠期需在实施前确认。
2. 是否具备 TPM 2.0；无 TPM 时的 DPAPI scope（LocalMachine vs 服务账户）需按节点部署方式确认。
3. 内部 CA 的根/中间 CA 托管方式（离线根、HSM/软件 CA）与撤销列表分发机制需在部署方案中确认。
4. 日志脱敏命名规则目录的最终清单与隐私审批口径需所有者确认。
5. 生产环境是否允许任何形式的 enrollment 自动批准；默认仅 staging 且需显式配置。
6. 长时压测的最大执行时长（默认 24 小时，任务级可至 7 天）需按业务样本量确认。
7. 控制面 signing key 是否入 HSM、轮换周期与重叠期需在密钥管理方案中确认。
8. `windows_event_log` 的 provider 白名单与字段映射需在实施前按实际驱动/工具确认。
9. 节点本地审计哈希链的存储位置、容量与上传策略需在节点部署方案中确认。
10. 旧回执/公钥保留期与证据 30 天保留、判定长期保留之间的最终对齐需在归档方案中确认。

## 21. 非声明

本文是 `frozen-candidate v1.1`，不是已批准契约，不表示任何需求已实现、测试已通过、部署已完成或获得发布授权。仍**未生产冻结，Phase 0 未关闭**。文中所有数值均为 v1 默认/候选值，任务级覆盖必须按第 16 节记录；不得把默认值当作已批准的生产参数。文中不包含真实证书、私钥、token、密码或设备凭据；示例字段名与占位符不得用于生产。
