# NoahsArk V0.0.1 环境、设备与 lstest 输入清单（P0-10）

> 版本：v1（2026-10-28）
> 归属：`.omo/plans/noahsark-platform-delivery.md` P0-10（建立环境/设备/lstest 输入清单）
> 状态：**清单已建立；一台代表性 Windows 节点与一套 TCL/ListenAI DUT 已完成只读事实采集；环境仍未就绪，A-0 未通过**。本文只登记输入、状态、责任方和阻塞关系，不构成实现、测试、部署、验收或发布授权。
> 范围：Linux 控制面、证据与备份存储、Windows 节点、真实设备、lstest 工具链、网络与信任、真机窗口。
> 硬规则：**不虚构任何 IP、主机名、凭据、证书值、设备序列号或固件版本**。仓库内不写主机名/IP/口令；此类值登记在受限运维记录中，正文只写“已确认存在”。

## 0. 状态口径与事实源

### 0.1 三种状态

| 状态 | 定义 | 可否作为实现/配置依据 |
|---|---|---|
| `known` | 已由批准文档、已评审契约或本次本地实测确认；真实值存在且可核验（敏感值可只在受限渠道记录） | 可以，但仅限其确认范围 |
| `placeholder` | 文档中的候选值、默认值、示例值或尚未在目标环境验证的推荐值 | **不可以**当作真实值；必须替换或由负责人确认 |
| `unknown` | 尚未取得任何真实值 | **不可以**；相关配置必须留空或 fail-closed |

规则：

1. 任何 `placeholder` 不得进入生产配置、证书、设备清单或验收证据，也不得在报告中写成“已具备”。
2. 任何 `unknown` 不得用“合理默认值”静默填充；接口可先支持，但真实值缺失时相关门禁必须阻断。
3. `known` 只证明该输入已确认，不证明环境已就绪、链路已通或验收已通过。
4. 示例值（如 `TCL000`、`COM7`、`speaker-1`、`0.9.14`）只是文档示例，本文一律标为 `placeholder` 或直接不采用。

### 0.2 事实源优先级

冲突时从高到低：

1. `.omo/drafts/00-baseline/noahsark-v0.0.1-requirements-baseline.md`（已批准需求基线）。
2. 根 `plan.md` 中已确认的架构/模块/字段级评审记录。
3. `.omo/drafts/01-design/`、`.omo/drafts/02-delivery/`、`.omo/drafts/05-decisions/` 中已同步批准边界的正文。
4. `docs/contracts/`（字段级候选契约）。
5. `solutions/`、`docs/v2/`、`openspec/`：同步前仅作历史参考，不得把其中的旧拓扑或示例值当作现行事实。

### 0.3 敏感值规则

- 主机名、IP、用户名、口令、证书私钥、注册 token、真实设备序列号**不写入本仓库**。
- 设备序列号只允许以 `serial_number_masked` 和 `identity_digest` 形式进入契约与日志（`docs/contracts/schemas/domain/device.schema.json`）。
- 原始音频、日志和证据按需求基线第 12 节限制访问；远程可读不等于备份。

### 0.4 来源编号

正文与汇总表使用 `S1`–`S20`，完整路径与章节见第 14 节。

## 1. 结论摘要

### 1.1 已确认（`known`）

- **数据库引擎**：PostgreSQL 是唯一正式数据库，SQLite 仅作历史参考（S8 §2 P0-01）。
- **备份拓扑**：第二台服务器做 PostgreSQL 异步从库 + 证据增量同步；局域网 NAS 做 WAL 归档/每日全量/证据归档；本机 `NoahsArkdata` 只作本地暂存，不是唯一副本（S8 §1.3）。
- **保留**：原始音频、日志和证据本地热存 30 天；没有已验证且可恢复的归档路径不得自动删除（S11 §12；S8 §1.1）。
- **证据存储形态**：本地内容寻址，SHA-256 摘要（S9 §2 P0-10）。
- **节点通信**：Windows 节点仅出站，TLS 1.3 + mTLS，X.509/Ed25519，证书 90 天、第 60 天续期（S12 §1）。
- **语言与运行时**：Python 3.11/3.12，venv 锁定；节点固定解释器与依赖（S8 §1.2）。
- **lstest 基线**：本地 `/home/bszheng/aitest/vendor/lstest` 工作树 `main` HEAD 为 `f32aebc`（2026-10-14）；实际 `origin/main` 为 `7190ab6`（2026-08-18），本地领先 1 个提交，本次复核本地 HEAD 未变（S10 §8.4；S18）。引用基线时必须区分“本地 main”与“远端 origin/main”。
- **lstest 结果与命令契约**：CLI 入口、7 个顶层子命令（`list`、`tts`、`tts-manifest`、`audio`、`preflight`、`init`、`smoke`）加 `audio` 下 5 个嵌套子命令（`ensure-laid`、`scan`、`probe`、`play`、`dual-play`）、结果目录、`tool.log` 北京时间、五轴状态已从代码核实（S10 §8.4；S18）。
- **本机（当前开发/控制主机）**：Ubuntu 24.04.4 LTS、kernel 6.17.0-35-generic、i5-1340P（16 线程）、约 15 GiB 内存、根分区 468 GiB ext4（剩余约 296 GiB）、NTP 已同步、systemd 可用、Asia/Shanghai；**未安装 PostgreSQL**（S18）。
- **RPO/RTO 目标**：DB ≤1 分钟 / ≤30 分钟；证据 ≤15 分钟 / ≤1 小时；整机 ≤4 小时；均为**待恢复演练验证的目标值**（S8 §1.3）。

### 1.2 关键缺口（当前 top blockers）

| # | 缺口 | 影响 |
|---|---|---|
| 1 | 代表节点已确认 OS/build、交互会话、D:、串口和音频；但服务账户、Node Agent/adapter/lstest pin、证书与主动出站链路未完成，Python 3.10.11 不符合 3.11/3.12 目标 | L3 仍阻塞 |
| 2 | 首个 DUT 已确认项目、设备标识、固件白名单、数量、端点、普通重启与恢复边界；但硬件版本、脱敏序列号及真实 PASS/FAIL/离线证据缺失 | L3/L4 仍阻塞 |
| 3 | 证据根路径、容量、NAS/第二服务器端点与恢复演练均未落地 | L4、AC-14 无法证明 |
| 4 | 真实 formal profile 与真实任务脚本未登记（仅有 framework 基线） | L3/L4 无正式判定输入 |
| 5 | 节点/控制面证书、CA、注册 token 签发人未定 | 节点无法注册，L3 阻断 |
| 6 | T3（旧编号）/T5/T6 真机窗口、负责人、允许固件、回滚联系人未定 | 无法排期真机验收 |

### 1.3 “可开工”与“可真机验收”的区别（摘要）

- **可开工**：只要求语言/运行时、lstest 基线、契约骨架、本地可用的占位存储与测试证书。当前多数 `unknown` 不阻塞编码，但必须以 fail-closed 占位实现。
- **可真机验收**：要求第 8 节真机窗口、第 4 节节点事实、第 5 节设备事实、第 3 节证据与备份端点、第 7 节信任链全部为 `known` 并有证据。
- 本文**不**声称 A-0 通过；A-0 与 L3/L4/L5 的判定分别见第 11、12 节。

## 2. Linux 控制面

依据：S1 §5.1；S17（环境准入）；S12 §1；S18（本地实测）。

| 输入 | 现状 | 状态 | 说明 |
|---|---|---|---|
| 主机身份（hostname/IP） | 身份已口头确认，值未登记；按 P0-01 分诊策略不写入仓库 | `placeholder` | 受限运维记录建立并登记记录 ID/日期/核验人后才可转 `known`；届时确认是否就是生产控制面 |
| OS 与内核 | Ubuntu 24.04.4 LTS；6.17.0-35-generic | `known` | 当前开发机实测；若生产控制面另有机，需重新登记 |
| CPU / 内存 | i5-1340P，16 线程；约 15 GiB | `known` | 足够 Phase 0–2 开发；是否满足并发压测未评估 |
| 系统盘 | 468 GiB ext4，已用 149 GiB，剩余约 296 GiB | `known` | 不等于证据容量，见第 3 节 |
| PostgreSQL 引擎 | PostgreSQL | `known` | SQLite 仅历史参考 |
| PostgreSQL 版本 | 候选 PostgreSQL 16，未锁定 | `placeholder` | S20 明确“版本待 P1-01”；本机 `psql` 不存在 |
| PostgreSQL 实例/连接/备份模式 | 未提供 | `unknown` | 需 DSN、端口、流复制/归档配置；本机未安装 |
| 控制面监听端口/反向代理 | 节点出站默认 443；控制面入站端口未定 | `placeholder` | S12 §1 只冻结“节点仅出站 HTTPS”；API/UI 端口待定 |
| 进程拓扑 | 建议单机三进程 | `placeholder` | S9 §2 P0-11 为建议值，不是部署事实 |
| TLS 基线 | TLS 1.3 + mTLS；X.509；Ed25519 | `known` | 契约默认值，见 S12 §1 |
| 服务管理器 | systemd 可用 | `known` | 本机实测 |
| 时间同步 | NTP active，`System clock synchronized: yes`，Asia/Shanghai（+0800） | `known` | 本机实测；生产控制面需单独确认 |
| 节点仅出站规则 | 已确认 | `known` | S12 §1；不存在入站管理端口 |
| 防火墙/代理放行清单 | 未提供 | `unknown` | 需明确控制面出站到 NAS/第二服务器、节点出站到控制面的 allowlist |
| 备份拓扑 | 第二服务器 + NAS + 本地暂存 | `known` | S8 §1.3 |
| 第二服务器/NAS 端点与容量 | 未提供 | `unknown` | 见 E05/E06 |
| DB RPO/RTO 目标 | ≤1 分钟 / ≤30 分钟 | `known` | 目标值，未演练 |
| 恢复演练记录 | 未执行 | `unknown` | 未演练不得声称达标 |

**责任方问题（不阻塞本清单成立）**

1. 当前这台 Ubuntu 主机是否就是 V0.0.1 的正式 Linux 控制面？若不是，正式主机何时提供？
2. PostgreSQL 目标版本是否锁定 16？是否允许在控制面本机安装，还是使用既有实例？
3. 控制面 API/UI 是否统一走 443 反向代理？是否已有域名/内网 DNS？
4. 第二服务器与 NAS 的地址、容量、协议、挂载点由谁提供？是否允许安装 PostgreSQL 从库？

## 3. 证据存储与备份

依据：S1 §5.4；S8 §1.3；S9 §2 P0-10；S11 §12；S13 §7；S14（设备释放/证据分离）。

| 输入 | 现状 | 状态 | 说明 |
|---|---|---|---|
| 证据根路径 | 未提供 | `unknown` | 需 Linux 绝对路径；不得用节点 D: 代替 |
| 证据容量 | 未提供 | `unknown` | 需按 30 天热存与单任务 GB 级日志估算 |
| 证据文件系统 | 未提供 | `unknown` | 本机根分区为 ext4，但证据目录可能另挂载 |
| 本机暂存 `NoahsArkdata` | 文档写作 `/home/bszheng/NoahsArkdata`，待确认主机；本机当前不存在 | `placeholder` | S8 §1.1；只是暂存，不是唯一副本 |
| 第二服务器角色/配置 | 已确认“有第二台服务器可存数据”，配置未提供 | `unknown` | 需 OS、磁盘、是否允许装从库 |
| NAS 协议/路径/容量 | 未提供 | `unknown` | SMB 或 NFS、导出路径、配额均未定 |
| 挂载协议 | D: 共享首选 SMB；NAS 未定 | `placeholder` | S17 明确“首选候选，不是已冻结契约” |
| 权限模型 | 最高权限 + 仅提交任务；原始材料限任务授权角色 | `known` | S8 §1.1；S11 §11 |
| 备份加密要求 | 必须加密存储，仅最高权限账户可访问 | `known` | S8 §1.3 |
| 加密算法与密钥保管/轮换 | 未提供 | `unknown` | 需 KMS/离线密钥方案与恢复演练 |
| 30 天热保留 | 确认 30 天 | `known` | S8 §1.1；S11 §12 |
| 内容寻址 | SHA-256，本地内容寻址 | `known` | S9 §2 P0-10；S10 §8.4 的 `sha256` 字段 |
| 证据同步频率 | 第二服务器约 15 分钟增量 | `known` | S8 §1.3；观察实际数据量后调整 |
| 到期处置/归档验证 | 无已验证归档路径，不得自动删除 | `unknown` | 归档目标、验证方式、删除审批流未定（Q-EV-03） |

**责任方问题**

1. 证据根目录放在哪块盘、多大容量、是否与系统盘分离？
2. NAS 用 SMB 还是 NFS？导出路径、可用容量、快照能力是什么？
3. 第二服务器是否允许安装 PostgreSQL 从库？磁盘容量与网段？
4. 备份加密密钥由谁保管？恢复演练由谁在什么窗口执行？
5. `NoahsArkdata` 是否与 Linux 控制面同一主机？是否只是导出暂存？

## 4. Windows 节点

依据：S2 §5.2；S16 §2.2/§3；S12 §1；S13 §7；S17。

| 输入 | 现状 | 状态 | 说明 |
|---|---|---|---|
| 节点主机身份 | 一台代表节点已通过受限记录和 SSH 只读采集确认 | `known` | 地址、用户名与凭据不落仓库；只代表该节点 |
| Windows 版本与 build | Windows 11 专业版，64 位，version/build `10.0.26200` / `26200` | `known` | 代表节点实测；QEMU 虚拟机 |
| Node Agent 版本 | 尚未构建，目标 V0.0.1 | `placeholder` | 构建后以实际版本替换 |
| 服务账户与权限 | 未提供 | `unknown` | Session 0 服务账户 + 登录会话账户需分开 |
| 交互式会话 | 采集时发现 1 个活动 Explorer session | `known` | 只证明采集时刻可用；Node Agent 仍须独立检查 |
| Python 版本 | 代表节点 `3.10.11` | `known` | **不符合**目标 3.11/3.12；正式运行前升级或重建受控 venv |
| lstest 固定版本 | 目标 `f32aebc` | `placeholder` | Linux 侧已确认；节点侧尚未 pin |
| 适配器版本 | 未构建 | `unknown` | 与 Node Agent/契约版本绑定 |
| 音频回放端点 | 当前活动 `扬声器 (ListenAI Audio)` 为 OK；所有者声明 2ch、`VID_8765&PID_5678` | `known` | 存在历史 Unknown 端点，不得按友好名回退 |
| 音频采集端点 | 当前活动 `麦克风 (ListenAI Audio)` 为 OK；所有者声明 8ch、`VID_8765&PID_5678` | `known` | 稳定绑定使用脱敏 endpoint identity |
| 串口/USB 端点 | COM3/4/5/7 = CH344 `VID_1A86&PID_55D5`；COM6 = ListenAI `VID_8765&PID_5678`，均为 OK | `known` | COM3=CSK、COM4=Hisilicon；COM5/COM7 当前不使用，适配器不得打开 |
| GUI/桌面会话 | 采集时存在活动 Explorer session | `known` | 只代表采集时刻 |
| D: 容量与可用空间 | NTFS 200 GiB，采集时约 199.3 GiB 可用 | `known` | 代表节点实测；spool 尚未配置 |
| spool 有效上限 | 默认 `min(2 GiB, D: 10%)`；70% 预警、95% 保护 | `placeholder` | S13 §7；有效值取决于真实 D: 容量 |
| 节点证书身份 | 方案已知；实际证书/指纹未知 | `unknown` | X.509/Ed25519，90 天；需签发与注册 |
| 节点出站连通/代理 | 未提供 | `unknown` | 只能出站到控制面 443，不能入站 |
| D: SMB 只读共享 | 首选候选 | `placeholder` | S17；最终挂载、权限、故障处理未确认 |
| 节点时区/时钟源 | 代表节点为 `China Standard Time`、UTC+08:00；时钟源/偏差未测 | `unknown` | 时区已知但 NTP 与偏差仍缺；硬限 120 秒/紧急 300 秒 |
| 待 STOP/残留租约/未完成清理 | 未验证 | `unknown` | 真机准入必须清空，否则 BLOCKED |

**责任方问题**

1. 提供哪台 Windows 主机？OS build、是否可创建/保持交互式登录会话？
2. 服务账户用什么身份？是否允许安装 Windows 服务与本地 venv？
3. D: 盘容量、可用空间、是否允许 Linux 通过 SMB 只读映射？
4. 音频/串口端点是否稳定？是否有多套设备需要区分？
5. 节点证书由哪个 CA 签发？注册 token 由谁签发？

## 5. 设备

依据：S3 §5.3；S15 §4/§6.3/§8；S14（设备等价与 `device_requirements`）；S11 §6/§10。

| 输入 | 现状 | 状态 | 说明 |
|---|---|---|---|
| 厂商/型号 | TCL 项目，代表性 DUT `TCL001`；ListenAI 标识 `ListenAIVCOM` | `known` | 所有者确认；精确硬件料号仍可后补 |
| 固件版本 | 当前 `V038`；允许白名单 `V038` | `known` | 所有者确认 |
| 硬件版本 | 未提供 | `unknown` | 与等价性相关 |
| 序列号（脱敏） | 未提供 | `unknown` | 只入 `serial_number_masked`/`identity_digest` |
| 音频端点绑定 | ListenAI Capture 8ch / Render 2ch；当前活动端点均为 OK | `known` | `VID_8765&PID_5678`；历史 Unknown 端点不得绑定 |
| 串口/USB 绑定 | COM6=ListenAI VCOM；CH344 A/COM3=CSK、C/COM4=Hisilicon，均 921600；COM5/COM7 当前不使用 | `known` | 实测 VID/PID 与当前 OK 状态；适配器不得打开 COM5/COM7 |
| 电源控制方式 | 当前不做断电/上电；允许通过 A/COM3 串口发送普通重启命令 | `known` | 所有者确认；命令值仍须由生成工件审批冻结，不在清单中登记 |
| 恢复方式 | 首选 A/COM3 普通重启；硬件复位存在，但当前不作为常规动作 | `known` | 所有者确认；硬件复位仅在后续批准场景使用 |
| 设备池/数量 | TCL 代表性 DUT 1 台，首个正式 DUT | `known` | 不外推到其他节点/设备 |
| 等价组字段值 | 字段已定义：`equivalence_group_id`、`conditions_digest`、`verified_at`、`verified_by` | `placeholder` | 结构 known，值 unknown；Q-08 未关闭 |
| 项目范围 | TCL，唤醒词“小T小T” | `known` | 所有者确认；尚未执行唤醒测试 |
| 已知 PASS/FAIL/离线场景 | 未提供 | `unknown` | T3/T5 至少各一次真实 PASS、FAIL、STOPPED/离线 |

**责任方问题**

1. 第一条真实链路用哪台设备？型号、固件、硬件版本、序列号（脱敏）？
2. 设备的音频与串口如何稳定绑定？电源/恢复由现场谁操作？
3. 是否有多台同型号设备？等价字段与跨设备替代由谁批准？
4. 哪个项目/固件版本作为 V0.0.1 首个真实任务？

## 6. lstest

依据：S10 §8.4；S8 §1.2/§2 P0-04；S18（本地复核）。

| 输入 | 现状 | 状态 | 说明 |
|---|---|---|---|
| 基线 commit | 本地 `main` `f32aebc`（2026-10-14）；`origin/main` 为 `7190ab6`（2026-08-18），本地领先 1 个提交 | `known` | 本次复核本地 HEAD 未变；远端未包含该提交 |
| formal profile 文件 | 未登记真实路径 | `unknown` | 曾对 21 条 `event_rules` 的 formal profile 跑过 preflight PASS，但路径未留档；`m0_min_profile.json` 是 debug 且 0 条规则，不能替代 |
| 真实脚本/任务配置 | 未提供 | `unknown` | 历史 v1 配置只能只读导入 |
| 预期产物 | `serial_logs/`、`evidence/`（tools/serial/audio/recorder）、`verification/`、`tool.log`、`cases.csv`、`results.csv`、`run_manifest.json` | `known` | S10 §8.4 结果目录契约 |
| CLI 入口 | `python3 scripts/lstest.py <subcommand>` | `known` | 7 个顶层子命令 + `audio` 下 5 个嵌套子命令（见第 1.1 节） |
| 正式执行命令/参数 | 未提供 | `unknown` | 需 profile 路径、任务配置、设备绑定、超时与证据参数 |
| 已知限制 | v1 配置缺 `profile_id` 即 BLOCKED；绝对路径/`..` 被拒；legacy `rounds.csv` 只读；`tool.log` 北京时间 | `known` | S10 §8.4 |
| 能力集 | 9 项：dynamic-serial、profile、evidence、basic-smoke、safe-stop、edge-tts、audio-device-scan、laid-installer、device-key-playback | `known` | `list --json` |

**责任方问题**

1. 首个真实任务使用哪个 formal profile？请给绝对路径、`profile_id`、规则数与摘要。
2. 真实脚本/任务配置在哪？是否允许平台只读引用并纳入冻结包？
3. 节点侧 lstest 是否就是 `f32aebc` 的副本？是否允许固定 venv？
4. 预期产物是否与 S10 §8.4 一致？是否有项目特有产物？

## 7. 网络与信任

依据：S5 §5.5；S12 §1；S11 §10；S17。

| 输入 | 现状 | 状态 | 说明 |
|---|---|---|---|
| CA 信任锚/签发主体 | 未提供 | `unknown` | 需节点证书与控制面证书的签发链 |
| 节点注册 token 签发人/流程 | 流程已知：一次性 256-bit、15 分钟、只存哈希；签发人未知 | `placeholder` | 流程 known，责任人与实际 token 未知 |
| DNS 名称解析 | 未提供 | `unknown` | 控制面域名、节点解析路径 |
| 控制面对外证书 | 未提供 | `unknown` | 证书主题、SAN、有效期、指纹 |
| 时钟偏差实测 | 未提供 | `unknown` | 硬限 120 秒；紧急 300 秒 |
| 代理/防火墙放行工单 | 未提供 | `unknown` | 节点出站 443；控制面到 NAS/第二服务器 |
| 节点仅出站 | 已确认 | `known` | 无入站管理端口，不用 SSH/WinRM/反向 shell |

**责任方问题**

1. 是否有现成 CA？证书由谁签发、谁轮换、谁撤销？
2. 节点注册 token 由哪个人/系统签发？
3. 控制面是否已有内网域名与证书？节点能否解析？
4. 现场防火墙/代理是否需要单独工单？审批周期多长？

## 8. 真机窗口（T3/T5/T6）

依据：S15 §4/§6.3/§8；S1 §3/§4（L3/L4/L5 与 AC-11..AC-14）；S7（T1–T6 分层）。

> 编号说明：`GAP-CLOSURE` 使用旧编号 **T3 = 真实设备资格**；现行测试策略使用 **T5 = 真机烟测、T6 = 正式验收**。旧 T3 对应现行 T5/T6 的真机阶段，排期时必须写清使用哪套编号。

| 输入 | 现状 | 状态 | 说明 |
|---|---|---|---|
| 旧 T3 集成/资格窗口 | 未提供 | `unknown` | 至少覆盖真实 PASS、FAIL、STOPPED/离线各一次 |
| T5 真机烟测窗口 | 未提供 | `unknown` | 独立 `run_id`，不入正式分母 |
| T6 正式验收窗口 | 未提供 | `unknown` | 需冻结样本量、阈值与判据 |
| 窗口负责人 | 未提供 | `unknown` | 现场操作与见证人 |
| 允许的固件白名单 | 未提供 | `unknown` | 禁止未批准固件 |
| 离线/断网模拟许可 | 未提供 | `unknown` | 断线续跑与 STOP-first 验收需要 |
| 升级审批人 | 未提供 | `unknown` | 工具链/Agent 升级审批 |
| 回滚联系人 | 未提供 | `unknown` | 回滚到旧 pin 的执行人 |

**责任方问题**

1. T5 与 T6 分别安排在什么时间？每次多长？
2. 谁在现场负责设备、断电/断网模拟和恢复？
3. 允许哪些固件版本？升级与回滚由谁批准？
4. 断网模拟是否允许？允许到什么程度（拔网线/关 Wi-Fi/防火墙阻断）？

## 9. 汇总表

> 说明：`用于` 列表示该输入在哪一层被真正需要；`阻塞` 列只表示“缺该值会阻断对应层”，不表示本清单整体阻塞。`A-0` 列指编码/准入所需，`L3` = 真机烟测，`L4` = 正式采样，`L5` = 端到端业务闭环。

| ID | 输入 | 用于 | 当前值 / 登记 | 状态 | 负责人 | 阻塞 | 来源与备注 |
|---|---|---|---|---|---|---|---|
| L01 | Linux 控制面主机身份 | L3/L4/L5 | 身份已口头确认；值未登记，不落仓库 | `placeholder` | 所有者/运维 | 是（L3） | S1 §5.1；P0-01 分诊策略；受限记录建立前不得转 `known` |
| L02 | 控制面 OS 与内核 | A-0/L3/L4/L5 | Ubuntu 24.04.4 LTS；6.17.0-35-generic | `known` | 运维 | 否 | S18 本机实测 |
| L03 | 控制面 CPU/内存 | A-0/L3/L4/L5 | i5-1340P 16 线程；约 15 GiB | `known` | 运维 | 否 | S18 |
| L04 | 系统盘容量/文件系统 | A-0/L3/L4/L5 | 468 GiB ext4，剩余约 296 GiB | `known` | 运维 | 否 | S18；不等于证据容量 |
| L05 | 数据库引擎 | A-0/L3/L4/L5 | PostgreSQL | `known` | 所有者 | 否 | S8 §2 P0-01 |
| L06 | PostgreSQL 版本 | A-0/L3/L4/L5 | 候选 16，未锁定 | `placeholder` | 所有者/运维 | 否（部署前锁定） | S20 P2-4 |
| L07 | PostgreSQL 实例/连接/备份模式 | A-0/L3/L4/L5 | 未提供；本机未安装 | `unknown` | 运维 | 是（A-0 联调） | S1 §5.1；S18 |
| L08 | 控制面监听端口/反代 | A-0/L3/L4/L5 | 节点出站默认 443；入站未定 | `placeholder` | 架构/运维 | 是（A-0 契约） | S12 §1 |
| L09 | 进程拓扑 | A-0/L3/L4/L5 | 建议单机三进程 | `placeholder` | 架构 | 否 | S9 §2 P0-11 |
| L10 | TLS/mTLS 基线 | A-0/L3/L4/L5 | TLS 1.3 + mTLS；X.509/Ed25519 | `known` | 安全 | 否 | S12 §1 |
| L11 | 服务管理器 | A-0/L3/L4/L5 | systemd 可用 | `known` | 运维 | 否 | S18 |
| L12 | 控制面时间同步 | A-0/L3/L4/L5 | NTP active，Asia/Shanghai | `known` | 运维 | 否 | S18 |
| L13 | 节点仅出站规则 | L3/L4/L5 | 已确认 | `known` | 安全 | 否 | S12 §1 |
| L14 | 防火墙/代理 allowlist | L3/L4/L5 | 未提供 | `unknown` | 运维 | 是（L3） | S5 §5.5 |
| L15 | 备份拓扑 | L4/L5 | 第二服务器 + NAS + 本地暂存 | `known` | 所有者 | 否 | S8 §1.3 |
| L16 | 第二服务器/NAS 端点与容量 | L4/L5 | 未提供 | `unknown` | 所有者/运维 | 是（L4） | S8 §1.3 |
| L17 | DB RPO/RTO 目标 | L4 | ≤1 分钟 / ≤30 分钟 | `known` | 所有者 | 否 | S8 §1.3；未演练 |
| L18 | 恢复演练记录 | L4/L5 | 未执行 | `unknown` | 运维 | 是（L4） | S1 §5.4；AC-14 |
| E01 | 证据根路径 | A-0/L3/L4/L5 | 未提供 | `unknown` | 架构/运维 | 是（A-0 存储接口） | S1 §5.1 |
| E02 | 证据容量 | L4 | 未提供 | `unknown` | 所有者/运维 | 是（L4） | S1 §5.1；S11 §12 |
| E03 | 证据文件系统 | A-0/L3/L4/L5 | 未提供 | `unknown` | 运维 | 否 | S1 §5.4；S11 §12；本机根为 ext4，证据路径未定 |
| E04 | 本机暂存 `NoahsArkdata` | L4 | `/home/bszheng/NoahsArkdata` 待确认；本机不存在 | `placeholder` | 所有者 | 否 | S8 §1.1 |
| E05 | 第二服务器配置 | L4 | 未提供 | `unknown` | 运维 | 是（L4） | S8 §1.3 |
| E06 | NAS 协议/路径/容量 | L4 | 未提供 | `unknown` | 运维 | 是（L4） | S8 §1.3 |
| E07 | 挂载协议 | L3/L4 | D: 共享首选 SMB；NAS 未定 | `placeholder` | 架构/运维 | 否 | S17 |
| E08 | 权限模型 | A-0/L3/L4/L5 | 最高权限 + 仅提交任务；原始材料限授权角色 | `known` | 所有者 | 否 | S8 §1.1；S11 §11 |
| E09 | 备份加密要求 | L4 | 必须加密，仅最高权限可访问 | `known` | 安全 | 否 | S8 §1.3 |
| E10 | 加密算法与密钥保管/轮换 | L4 | 未提供 | `unknown` | 安全/运维 | 是（L4） | S8 §1.3 |
| E11 | 30 天热保留 | A-0/L3/L4/L5 | 确认 30 天 | `known` | 所有者 | 否 | S8 §1.1；S11 §12 |
| E12 | 内容寻址算法 | A-0/L3/L4/L5 | SHA-256 本地内容寻址 | `known` | 架构 | 否 | S9 §2 P0-10；S10 §8.4 |
| E13 | 证据同步频率 | L4 | 约 15 分钟增量 | `known` | 架构 | 否 | S8 §1.3 |
| E14 | 到期处置/归档验证 | L4/L5 | 未提供 | `unknown` | 所有者 | 是（L4） | S11 §12；Q-EV-03 |
| W01 | 节点主机身份 | L3/L4/L5 | 一台代表节点已通过受限记录和 SSH 只读采集确认 | `known` | 节点负责人 | 否（该节点身份） | S2 §5.2；`a0-representative-node-verification.md` |
| W02 | Windows 版本/build | L3/L4/L5 | Windows 11 Pro 64-bit，`10.0.26200` / build `26200` | `known` | 节点负责人 | 否 | 代表节点实测；QEMU 虚拟机 |
| W03 | Node Agent 版本 | L3/L4/L5 | 目标 V0.0.1，未构建 | `placeholder` | 平台 | 是（L3） | S2 §5.2 |
| W04 | 服务账户与权限 | L3/L4/L5 | 未提供 | `unknown` | 节点负责人 | 是（L3） | S2 §5.2 |
| W05 | 交互式会话状态 | L3/L4/L5 | 采集时 1 个活动 Explorer session | `known` | 节点负责人 | 否（采集时刻） | S2 §5.2；S16 §3；后续仍需 Agent 持续检查 |
| W06 | 节点 Python 版本 | A-0/L3/L4/L5 | `3.10.11` | `known` | 平台/节点 | 是（运行时整改） | 代表节点实测；低于 3.11/3.12 目标 |
| W07 | 节点 lstest pin | L3/L4/L5 | 目标 `f32aebc` | `placeholder` | 节点负责人 | 是（L3） | S10 §8.4；未在节点验证 |
| W08 | 适配器版本 | L3/L4/L5 | 未构建 | `unknown` | 平台 | 是（L3） | S2 §5.2 |
| W09 | 音频回放端点 | L3/L4/L5 | 当前活动 ListenAI 扬声器 OK；2ch，`VID_8765&PID_5678` | `known` | 节点负责人 | 否（该端点） | 稳定身份摘要见后续验证报告 |
| W10 | 音频采集端点 | L3/L4/L5 | 当前活动 ListenAI 麦克风 OK；8ch，`VID_8765&PID_5678` | `known` | 节点负责人 | 否（该端点） | 稳定身份摘要见后续验证报告 |
| W11 | 串口/USB 端点 | L3/L4/L5 | COM3/4/5/7 CH344 + COM6 ListenAI 均 OK，VID/PID 已采集 | `known` | 节点负责人 | 否（枚举） | COM5/COM7 当前不使用，适配器不得打开 |
| W12 | GUI/桌面会话 | L3/L4/L5 | 活动 Explorer session 1 个 | `known` | 节点负责人 | 否（采集时刻） | S17；持续可用性待 Agent 验证 |
| W13 | D: 容量与可用空间 | L3/L4/L5 | NTFS 200 GiB；采集时约 199.3 GiB 可用 | `known` | 节点负责人 | 否 | 代表节点实测 |
| W14 | spool 有效上限 | L4 | 默认 `min(2 GiB, D: 10%)`，70%/95% | `placeholder` | 节点负责人 | 是（L4） | S13 §7 TH-S-07..10 |
| W15 | 节点证书身份 | L3/L4/L5 | 方案已知；实际证书未知 | `unknown` | 安全/节点 | 是（L3） | S12 §1 |
| W16 | 节点出站连通/代理 | L3/L4/L5 | 未提供 | `unknown` | 网络/节点 | 是（L3） | S12 §1 |
| W17 | D: SMB 只读共享 | L3/L4/L5 | 首选候选 | `placeholder` | 架构/节点 | 否（L3 前确认） | S17 |
| W18 | 节点时区/时钟源 | L3/L4/L5 | `China Standard Time` / UTC+08:00；NTP 源与偏差未测 | `unknown` | 节点负责人 | 是（L3） | 时区部分已实测；仍需 `w32tm` 证据 |
| W19 | 待 STOP/残留租约/未完成清理 | L3/L4/L5 | 未验证 | `unknown` | 节点负责人 | 是（L3） | S1 §5.6 |
| D01 | 设备厂商/型号 | L3/L4/L5 | TCL `TCL001`；ListenAI 标识 `ListenAIVCOM` | `known` | 设备负责人 | 否（首个 DUT） | 所有者确认；精确板卡料号可后补 |
| D02 | 固件版本 | L3/L4/L5 | 当前/允许版本均为 `V038` | `known` | 设备负责人 | 否 | 所有者确认 |
| D03 | 硬件版本 | L3/L4/L5 | 未提供 | `unknown` | 设备负责人 | 是（L3） | S14 设备身份 |
| D04 | 序列号（脱敏） | L3/L4/L5 | 未提供 | `unknown` | 设备负责人 | 是（L3） | S14；只入 masked/digest |
| D05 | 音频端点绑定 | L3/L4/L5 | ListenAI Capture 8ch / Render 2ch，活动端点 OK | `known` | 设备负责人 | 否（首个 DUT） | `VID_8765&PID_5678`；历史 Unknown 端点排除 |
| D06 | 串口/USB 绑定 | L3/L4/L5 | COM6 ListenAI；COM3 CSK / COM4 Hisilicon @ 921600；COM5/COM7 当前不使用 | `known` | 设备负责人 | 否（已知绑定） | CH344 `VID_1A86&PID_55D5`；COM5/COM7 为负向检查 |
| D07 | 电源控制方式 | L3/L4/L5 | 当前不做断电/上电；允许通过 A/COM3 串口普通重启 | `known` | 设备负责人 | 否（当前范围） | 所有者确认；具体命令由冻结工件提供 |
| D08 | 恢复方式 | L3/L4/L5 | 首选 A/COM3 普通重启；硬件复位存在但当前不常规使用 | `known` | 设备负责人 | 否（当前范围） | 所有者确认；硬件复位需后续场景授权 |
| D09 | 设备池/数量 | L3/L4/L5 | TCL 代表性 DUT 1 台；首个正式 DUT | `known` | 设备负责人 | 否（本轮范围） | 不外推到其他设备 |
| D10 | 等价组字段值 | L4/L5 | 字段已定义，值未提供 | `placeholder` | 设备负责人 | 是（L4） | S14 D-4；Q-08 |
| D11 | 项目范围 | A-0/L3/L4/L5 | TCL；唤醒词“小T小T” | `known` | 所有者 | 否 | 所有者确认；未执行真实唤醒 |
| D12 | 已知 PASS/FAIL/离线场景 | L3/L4 | 未提供 | `unknown` | 设备负责人 | 是（L3） | S15 §4 |
| T01 | lstest 基线 commit | A-0/L3/L4/L5 | 本地 `main` `f32aebc`（2026-10-14）；`origin/main` `7190ab6`（2026-08-18） | `known` | 平台 | 否 | S10 §8.4；S18；本地领先 1 个提交 |
| T02 | formal profile 文件 | L3/L4 | 未登记真实路径 | `unknown` | lstest 负责人 | 是（L4） | S10 §8.4；21 条规则样例未留档 |
| T03 | 真实脚本/任务配置 | L3/L4 | 未提供 | `unknown` | lstest 负责人 | 是（L3） | S15 §6.3 |
| T04 | 预期产物 | A-0/L3/L4/L5 | 结果目录契约已核实 | `known` | 平台 | 否 | S10 §8.4 |
| T05 | CLI 入口/子命令 | A-0/L3/L4/L5 | `python3 scripts/lstest.py <subcommand>`；7 个顶层 + `audio` 5 个嵌套 | `known` | 平台 | 否 | S10 §8.4；S18 |
| T06 | 正式执行命令/参数 | L3/L4/L5 | 未提供 | `unknown` | lstest 负责人 | 是（L3） | S10 §8.4；S15 §6.3；需 profile/设备/超时参数 |
| T07 | 已知限制 | A-0/L3/L4/L5 | v1 缺 `profile_id` 即 BLOCKED；legacy 只读；绝对路径被拒；北京时间 | `known` | 平台 | 否 | S10 §8.4 |
| T08 | 能力集 | A-0/L3/L4/L5 | 9 项能力 | `known` | 平台 | 否 | S10 §8.4 |
| N01 | CA 信任锚/签发主体 | L3/L4/L5 | 未提供 | `unknown` | 安全 | 是（L3） | S12 §1 |
| N02 | 注册 token 签发人/流程 | L3/L4/L5 | 流程已知；签发人未知 | `placeholder` | 安全/运维 | 是（L3） | S12 §1 |
| N03 | DNS 名称解析 | L3/L4/L5 | 未提供 | `unknown` | 网络 | 是（L3） | S5 §5.5 |
| N04 | 控制面对外证书 | L3/L4/L5 | 未提供 | `unknown` | 安全 | 是（L3） | S12 §1 |
| N05 | 时钟偏差实测 | L3/L4 | 未提供 | `unknown` | 运维 | 是（L3） | S12 §1；120 秒硬限 |
| N06 | 代理/防火墙放行工单 | L3/L4/L5 | 未提供 | `unknown` | 网络 | 是（L3） | S5 §5.5 |
| R01 | 旧 T3 集成/资格窗口 | L3 | 未提供 | `unknown` | 所有者 | 是（L3） | S15 §4 |
| R02 | T5 真机烟测窗口 | L3 | 未提供 | `unknown` | 所有者 | 是（L3） | S7 T5 分层 |
| R03 | T6 正式验收窗口 | L4/L5 | 未提供 | `unknown` | 所有者 | 是（L4） | S7 T6 分层 |
| R04 | 窗口负责人 | L3/L4/L5 | 未提供 | `unknown` | 所有者 | 是（L3） | S15 §4 |
| R05 | 允许固件白名单 | L3/L4/L5 | `V038` | `known` | 设备负责人 | 否（当前 DUT） | 所有者确认 |
| R06 | 离线/断网模拟许可 | L3/L4 | 未提供 | `unknown` | 所有者 | 是（L3） | S1 §4（AC-11/AC-12）；S7 |
| R07 | 升级审批人 | L3/L4/L5 | 未提供 | `unknown` | 所有者 | 是（L3） | S15 §4 |
| R08 | 回滚联系人 | L3/L4/L5 | 未提供 | `unknown` | 所有者 | 是（L3） | S15 §4 |

### 9.1 计数

| 状态 | 数量 |
|---|---|
| `known` | 38 |
| `placeholder` | 12 |
| `unknown` | 35 |
| 合计 | 85 |

## 10. 最小可开工 vs 最小可真机验收

### 10.1 最小可开工（编码/契约/模拟）

满足以下条件即可开始 Phase 0–2 的代码与契约工作，**不需要真实设备**：

1. 语言与运行时：Python 3.12（或 3.11）锁定；节点/控制面 venv 方案确定（S8 §1.2）。
2. lstest 基线：`f32aebc` 可只读引用；`preflight` 可无设备运行（S10 §8.4）。
3. 数据库：先按 PostgreSQL 16 的 SQL 方言与迁移编写；目标版本在部署前锁定（S20）。
4. 存储：证据接口按内容寻址 + `relative_path` 设计；根路径用配置项，不硬编码。
5. 安全：按 TLS 1.3 + mTLS、X.509/Ed25519 写契约；本地测试证书可以自签，**不得**冒充生产证书。
6. 契约：`docs/contracts/` 的 task/revision/run/case/attempt/bundle/lease/device/node/receipt 字段作为编码依据（仍为 frozen-candidate）。
7. 缺失值处理：所有 `unknown` 必须以 `BLOCKED`/`capacity_unknown`/`UNKNOWN` 显式表示，禁止默认填充。

结论：**编码可以在不解决 L3 真机输入的情况下开始**，但不得声称环境就绪。

### 10.2 最小可真机验收（L3/L4/L5）

以下全部为 `known` 且有证据，才可进入 L3：

1. 至少一台 Windows 节点：主机、OS build、服务账户、交互式会话、Agent 版本、Python/lstest/adapter pin、证书、出站连通、时区（W01–W08、W15–W18）。
2. 至少一台设备：型号、固件、硬件版本、脱敏序列号、音频/串口端点、电源/恢复方式、设备池（D01–D09）。
3. lstest：真实 formal profile、真实脚本/配置、正式执行命令（T02/T03/T06）。
4. 证据与网络：证据根路径与容量、D: 容量/spool、CA/证书/DNS/防火墙（E01/E02/W13/W15/N01–N06）。
5. 真机窗口：T5/T6 时间、负责人、允许固件、离线模拟许可、升级/回滚联系人（R01–R08）。
6. 备份与恢复：第二服务器/NAS 可达，恢复演练完成；否则 AC-14 不能通过（E05/E06/E10/E14/L18）。

## 11. A-0 签署清单

> A-0 = 施工准入确认。勾选只表示“该输入项已登记/已决定”，**不表示 A-0 已通过**。最终由主控/所有者另行签署。

- [ ] 8 类输入（Linux、证据、Windows、设备、lstest、网络、真机窗口、汇总）全部登记。
- [ ] 每个输入有唯一 ID、状态、责任方、阻塞层与来源。
- [ ] 已确认项（PostgreSQL 引擎、第二服务器 + NAS 拓扑、30 天保留、lstest 基线）有正文引用。
- [ ] 所有 `placeholder` 明确标注“不是真实值”，且未写入任何配置/证书/设备清单。
- [ ] 所有 `unknown` 有责任方和补录计划；未用默认值静默填充。
- [ ] “可开工最小集”已确认（第 10.1 节）。
- [ ] 编码阻塞项（L07 PostgreSQL 实例、L08 端口、E01 证据根路径）已有决定或明确以配置项占位。
- [ ] 未把设备、节点、证书的示例值（`TCL000`、`COM7`、`0.9.14` 等）当作真实值。
- [ ] 本清单之外的契约/环境冲突已转 P0-03/P0-11 处理。
- [ ] 主控/所有者记录 A-0 结论；**本文不代替该结论**。

## 12. L3/L4/L5 就绪清单

### 12.1 L3 真机烟测

- [ ] 节点心跳稳定；`interactive_session.state = AVAILABLE`。
- [ ] 设备与音频/串口端点识别稳定；端点 binding 可复现。
- [ ] 固定 lstest/adapter 版本可在交互式会话执行；工件摘要校验通过。
- [ ] Node Agent 注册、回传、异常上报、白名单日志读取可用。
- [ ] 证书、时间、网络、审计通过；节点仅出站。
- [ ] D: 可用空间高于保护阈值；spool 未达预警。
- [ ] 无待 STOP、无冲突租约、无未完成清理。
- [ ] 烟测使用独立 `run_id`，不产生正式 PASS，不入正式分母。

### 12.2 L4 正式采样

- [ ] 真实 formal profile 与脚本已冻结并纳入 Execution Bundle；摘要可复算。
- [ ] 设备型号/固件/硬件版本/等价组已登记；跨设备不合并。
- [ ] 样本量、阈值、重试、预算已按任务修订冻结。
- [ ] 证据根路径、容量、内容寻址、manifest 校验可用。
- [ ] 第二服务器与 NAS 可达；备份加密与密钥保管已确认。
- [ ] 恢复演练按“数据库 → manifest/摘要 → 任务/运行/占用对账”通过；未通过不得声称 RPO/RTO。
- [ ] 30 天热保留与到期不删策略已配置；归档验证路径存在。
- [ ] Linux 独立复核可执行；PASS 需五轴同时满足。

### 12.3 L5 端到端业务闭环

- [ ] 第二任务可在授权审核后复用项目/硬件经验，且显示来源与适用条件。
- [ ] 报告区分自动判定与人工补充；原始材料访问有审计。
- [ ] 跨设备结果隔离；单设备通过不外推。
- [ ] 断线续跑、STOP-first、重连对账、设备释放分别有记录（AC-11..AC-13）。
- [ ] 任务卡/UI/报告与 Linux 权威状态一致（AC-10）。

## 13. 待所有者/责任方回答的问题（不阻塞本文成立）

1. 正式 Linux 控制面是否就是当前 Ubuntu 主机？若不是，何时提供？
2. PostgreSQL 目标版本是否锁定 16？实例由谁运维？
3. 证据根路径与容量、第二服务器、NAS 的协议/路径/容量分别是什么？
4. 第一条真实链路的 Windows 节点是哪台？OS build、服务账户、交互式会话是否可用？
5. 第一条真实链路的设备型号/固件/硬件版本/脱敏序列号/端点是什么？
6. 首个 formal profile 与真实脚本的绝对路径、`profile_id`、规则数是什么？
7. 证书由哪个 CA 签发？注册 token 由谁签发？
8. T5/T6 的具体时间窗、现场负责人、允许固件、是否允许断网模拟？
9. 升级审批人与回滚联系人是谁？
10. 备份加密密钥由谁保管？恢复演练何时执行？

## 14. 来源索引

| 编号 | 文件与章节 |
|---|---|
| S1 | `.omo/drafts/02-delivery/noahsark-v0.0.1-delivery-acceptance.md` §1、§2.1、§3、§5.1、§5.4、§5.6 |
| S2 | 同上 §5.2 |
| S3 | 同上 §5.3 |
| S4 | 同上 §5.4 |
| S5 | 同上 §5.5 |
| S6 | 同上 §5.6 |
| S7 | 同上 §3、§4（L0–L5、AC-1..AC-14） |
| S8 | `.omo/drafts/05-decisions/noahsark-v0.0.1-decision-register.md` §1、§1.1、§1.2、§1.3、§2 P0-01..P0-11 |
| S9 | 同上 §2 P0-01..P0-11 |
| S10 | `.omo/drafts/01-design/noahsark-v0.0.1-architecture-proposal.md` §8.4 |
| S11 | `.omo/drafts/00-baseline/noahsark-v0.0.1-requirements-baseline.md` §5、§6、§10、§11、§12 |
| S12 | `docs/contracts/security-node.md` §1、§8.1、§8.3 |
| S13 | `docs/contracts/thresholds.md` §7（TH-S-01..TH-S-11） |
| S14 | `docs/contracts/domain.md` §设备身份/等价（D-4、Q-08）；`docs/contracts/schemas/domain/device.schema.json` |
| S15 | `solutions/1027V1/GAP-CLOSURE.md` §1、§4、§6.3、§8 |
| S16 | `solutions/1027V1/REMOTE-EXECUTION.md` §2.2、§3、§4 |
| S17 | 根 `plan.md`“第四、五步补充分组审核：环境就绪与节点配置”（2026-10-28）及“Windows 节点 / 真机准入”条目 |
| S18 | 本次本地实测（2026-10-28；2026-10-29 复核）：`/etc/os-release`、`uname -r`、`/proc/cpuinfo`、`free -g`、`df -h /`、`findmnt /`、`timedatectl`、`command -v psql`、`git -C /home/bszheng/aitest/vendor/lstest rev-parse --short HEAD`、`git -C ... branch -vv`、`git -C ... for-each-ref refs/heads refs/remotes`、`python3 /home/bszheng/aitest/vendor/lstest/scripts/lstest.py --help`、`... audio --help` |
| S19 | `.omo/plans/noahsark-platform-delivery.md` P0-10 |
| S20 | `.omo/drafts/00-VARIANT-B-AUDIT.md` P2-4（“PostgreSQL 16”未锁定） |

## 15. 变更记录

| 日期 | 变更 |
|---|---|
| 2026-10-28 | 建立 P0-10 输入清单：8 类输入、85 条登记（21 known / 13 placeholder / 51 unknown）、A-0 与 L3/L4/L5 两套清单；未虚构任何真实值，未宣称 A-0 通过。 |
| 2026-10-29 | 按独立验证报告 F1–F4 修正：区分本地 `main` `f32aebc` 与实际 `origin/main` `7190ab6`；命令清单改为 7 个顶层 + 5 个 `audio` 嵌套子命令；L01 因无受限记录指针由 `known` 降为 `placeholder`（保留 L3 阻塞）；补齐 E03/D07/T06/R06 行级来源。计数更新为 85 条（20 known / 14 placeholder / 51 unknown）；A-0 仍未通过。 |
| 2026-10-29 | 录入代表节点/DUT 后续确认：COM5/COM7 当前不使用；允许 A/COM3 普通重启；硬件复位存在但不作常规动作。当前计数为 85 条（38 known / 12 placeholder / 35 unknown）；A-0 仍未通过。 |
