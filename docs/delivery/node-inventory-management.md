# NoahsArk 节点连接清单管理策略

> **状态：DRAFT · NOT FROZEN**
> 冻结条件：真实节点清单（含 `win009`）完成一次性导入、批量只读核验留痕、所有者签字。
> 在此之前，未经真实导入与核验的结论不得当作已验证事实引用。
>
> 实现状态（2026-10-30）：`config/node-inventory/` 下的 schema、公开清单、模板、
> 本地加密存储脚本、批量只读核验脚本和证据流程已就绪并通过静态校验；但本机缺少
> `sops` 与 `age`，且没有可用的脱敏别名清单，**真实导入与节点核验尚未开始**。
> 证据见 [`node-inventory-workflow-evidence.md`](./node-inventory-workflow-evidence.md)。
>
> 范围：节点连接资产（SSH 连接信息、节点身份、Agent 凭据引用）的分类、存储、
> 导入、核验、轮换、撤销与事故响应。
> 非范围：业务代码、UI、契约文档、部署脚本实现、`ssh.txt` 内容处理。

---

## 0. 结论先行

节点连接配置是核心资产，不是临时便签。判断标准只有一条：

- **以 `node_id` 为唯一主键**，不以 IP、主机名、备注名或人工粘贴行为为准。
- **凭据只存引用，不存明文值**。清单里出现密码或私钥即为缺陷。
- **加密清单可以进 Git，age 私钥永远不进**。
- **默认只读**。任何写操作、重启、修复都必须人工批准。
- **日志、提示词、Issue、截图、CI 输出里不出现密钥值**。

技术选型：SOPS + age 加密 YAML 清单，age 身份文件放在仓库外并 `chmod 600`，
SSH 使用 `~/.ssh/config` 别名与 `ssh-agent`，Node Agent 使用一次性注册令牌加
mTLS。理由见 §12。

真正的导入还没发生。所以本文标记为 **DRAFT · NOT FROZEN**。

---

## 1. 资产分类与归属

### 1.1 分类

| 类别 | 内容 | 敏感度 | 存放位置 | 可否进 Git |
|---|---|---|---|---|
| C0 公开 | 本策略、清单 schema、`.sops.yaml` 中的 age 公钥 | 公开 | 仓库 | 可以 |
| C1 内部元数据 | `node_id`、`ssh_alias`、OS、能力标签、`agent_id`、`device_ids`、状态时间戳、`config_version` | 内部 | 公开清单（无连接信息）或加密清单 | 可以，须通过 schema 校验 |
| C2 受限元数据 | 主机地址、登录用户名、Agent URL、所属项目、负责人 | 受限 | 仅加密清单 | 加密后可以 |
| C3 密钥材料 | SSH 私钥、age 私钥、Agent 令牌、任何密码、主机指纹私钥部分 | 机密 | 专用密钥库 / `~/.ssh` / 密码管理器 | **绝对不可以** |
| C4 源文件 | 受保护的原始连接表（例如 `ssh.txt`） | 机密 | 仓库外、权限 600 | **绝对不可以** |

判断规则：一条信息如果泄露后能直接登录、冒充或解密，就是 C3。如果泄露后能缩小
攻击面（知道内网地址、用户名、节点清单），就是 C2。C1 只用于展示和索引。

### 1.2 归属

| 角色 | 负责 | 不负责 |
|---|---|---|
| 平台所有者 | 清单 schema、加密策略、审批冻结 | 单台节点的账号 |
| 节点所有者 | 单节点 `node_id`、能力、维护窗口、下线申请 | age 私钥保管 |
| 安全负责人 | age 接收者名单、密钥轮换、事故定级 | 日常节点录入 |
| Agent 服务负责人 | 注册、证书、心跳、撤销接口 | 节点操作系统 |
| 值班操作员 | 只读核验、记录结果、上报异常 | 自行改清单或重置密码 |

原则：**一人不能同时持有 age 私钥和清单写权限而不留审计**。小团队至少要做到
写入走 Git 提交，提交信息记录操作者与变更摘要。

---

## 2. 设计原则

1. **单一主键**：`node_id` 稳定且不可复用。节点重装后沿用 `node_id`，只更新
   `host_ref`、`credential_ref` 和状态时间戳。退网节点标记 `retired`，不删除历史。
2. **别名只是指针**：`alias` 映射到 `~/.ssh/config` 的 `Host` 段，方便人用，不承担
   身份语义。改 IP 不改 `node_id`。
3. **凭据引用化**：清单写 `credential_ref`，真实私钥留在 `ssh-agent` 或 600 权限的
   密钥文件。Agent 令牌存 SOPS 的独立子树，不写进节点条目。
4. **最小权限**：每节点独立密钥或独立证书，禁止全员共用 root 口令。默认账号只读。
5. **默认失败关闭**：解析不到引用、解密失败、主机指纹不匹配时停止，不回退到密码
   登录，不自动接受新主机键。
6. **无秘密日志**：脚本只输出 `node_id` 和状态枚举。禁止 `set -x` 包住涉密命令。
7. **人在环**：批量核验只读。修复、重启、改注册表、重置密码、删除节点都必须人工确认。

---

## 3. 目录与密钥布局

仓库内（可提交，只有密文和公钥）：

```
config/node-inventory/
  .sops.yaml                              # 只含 age 公钥与 creation_rules
  public-inventory.yaml                   # 公开清单：仅 C0/C1 非敏感元数据
  nodes.enc.yaml                          # SOPS 加密清单（导入后生成，勿提交明文）
  schema/node-inventory.public.schema.json
  schema/node-inventory.private.schema.json
  templates/public-inventory.example.yaml # 导入契约模板（无真实值）
  templates/private-inventory.example.yaml
  README.md                               # 操作手册
docs/delivery/
  node-inventory-management.md
  node-inventory-workflow-evidence.md
scripts/node-inventory/
  lib.sh
  init-local-store.sh
  import-inventory.sh
  validate-inventory.py
  verify-nodes.sh
  node-agent.sh
  backup-inventory.sh
  rotate-age-recipient.sh
```

公开清单与加密清单一分为二：

- `public-inventory.yaml`：`node_id -> ssh_alias -> agent_id -> device_ids ->
  capabilities -> last_seen/status/config_version` 的稳定映射，供人读和批量核验。
- `nodes.enc.yaml`：`host_ref -> user_ref -> credential_ref -> agent_url / port`
  的连接引用，只以 SOPS 密文进 Git。

操作机本地（仓库外，权限 600/700）：

```
~/.config/noahsark/
  age/keys.txt               # age 私钥，0600，永不入 Git、永不入 CI
  agent/tokens.enc.yaml      # 可选：本地加密的 Agent 令牌副本
  logs/verify-YYYYMMDD.jsonl # 只读核验结果，0600
  logs/inventory-audit.jsonl # 追加式审计，600
  backups/inventory-<UTC>/   # 密文备份 + MANIFEST.json，700/600

~/.ssh/config                # Host 别名，0600（建议）
~/.ssh/known_hosts           # 已核验主机键，0600（verify-nodes.sh 默认读取）
```

关键约定：

- `SOPS_AGE_KEY_FILE="$HOME/.config/noahsark/age/keys.txt"`，不设默认路径，
  避免误用其他项目的年龄键。
- 目录 `700`，文件 `600`，导入期间 `umask 077`。
- Windows 操作机用 `icacls` 只授予当前用户，禁用继承：
  `icacls "%USERPROFILE%\.config\noahsark\age" /inheritance:r /grant:r "%USERNAME%:(OI)(CI)F"`。
- `known_hosts` 用带哈希的主机名（`HashKnownHosts yes`），避免泄露节点地址清单。

---

## 4. 一次性本地导入流程

目标：把受保护源文件里的连接信息搬进加密清单，**全程不回显任何值**。

### 4.1 前置条件

- 源文件在仓库外，权限 600，属主为操作员。
- 源文件没有被 Git 跟踪，也没有被任何同步盘、截图工具、剪贴板管理器监听。
- 操作机全盘加密（BitLocker / LUKS / FileVault）。
- 已安装 `sops`、`age`、`ssh`，以及带 `PyYAML` + `jsonschema` 的 `python3`。
- age 私钥已生成并验证可解密一个测试文件。

### 4.2 生成与保护 age 身份

推荐用已实现脚本（只打印公钥，不打印私钥）：

```bash
scripts/node-inventory/init-local-store.sh --generate-key --write-sops-config
scripts/node-inventory/init-local-store.sh --check
```

等价手工命令：

```bash
umask 077
mkdir -p "$HOME/.config/noahsark/age"
age-keygen -o "$HOME/.config/noahsark/age/keys.txt"
chmod 600 "$HOME/.config/noahsark/age/keys.txt"
age-keygen -y "$HOME/.config/noahsark/age/keys.txt"   # 只打印公钥，可提交
```

公钥写进 `config/node-inventory/.sops.yaml`。私钥只做两件事：本机解密、离线备份。
不粘贴到聊天、Issue、PR、CI 变量或密码提示词里。

### 4.3 导入步骤

脚本已实现下列步骤：`scripts/node-inventory/import-inventory.sh`。它拒绝
`ssh.txt` 文件名、先校验后合并、只输出节点计数，并在临时目录退出时清零明文。

1. **建骨架**：先手写 `nodes.enc.yaml` 的 `schema_version`、`inventory_id` 和空
   `nodes: []`，用 `sops -e` 加密后再提交。脚本首次导入会自动生成骨架。
2. **计数，不读取**：只统计源文件行数与列数，确认格式假设成立。
   ```bash
   wc -l < "$ARK_IMPORT_SOURCE"
   awk -F, 'NR==1{print NF}' "$ARK_IMPORT_SOURCE"
   ```
   不打印表头、不打印样例行、不 `head`、不 `grep`。
3. **本地映射**：在 `mktemp -d` 中写一个一次性脚本，把每行映射为清单字段。
   脚本只输出 `node_id -> ok|skip|error`，不输出主机、用户、密码。
4. **密钥分流**：私钥/口令写入 `ssh-agent` 或 600 权限密钥文件；清单只得到
   `credential_ref`，例如 `ssh-agent:win009-ed25519`。
5. **加密**：`sops -e -i config/node-inventory/nodes.enc.yaml`，确认文件头出现
   `sops:` 元数据且 `age` 接收者正确。
6. **自检**：
   ```bash
   python3 scripts/node-inventory/validate-inventory.py \
     --kind public --inventory config/node-inventory/public-inventory.yaml
   sops -d config/node-inventory/nodes.enc.yaml \
     | python3 scripts/node-inventory/validate-inventory.py --kind private --inventory /dev/stdin --check-refs
   ```
   两条都必须 `RESULT=OK`。
7. **清理**：`shred -u` 明文临时文件，删除 `mktemp` 目录，清空相关 shell 历史。
   SSD 上 `shred` 不保证物理擦除，因此**更强的前提是全盘加密**。
8. **留痕**：在审计记录写 `import`、日期、操作员、节点数、结果，不写任何值。

### 4.3.1 操作员一次性命令

```bash
# 0) 前置：安装 sops + age；生成本地 age 身份并写入 .sops.yaml
scripts/node-inventory/init-local-store.sh --generate-key --write-sops-config

# 1) 脱敏公开元数据（不要把主机/用户/密码/私钥放进此文件）
scripts/node-inventory/import-inventory.sh \
  --source /secure/path/sanitized-public.yaml \
  --private-source /secure/path/private-refs.yaml \
  --dry-run

# 2) 正式导入（public 明文清单 + private 密文清单）
scripts/node-inventory/import-inventory.sh \
  --source /secure/path/sanitized-public.yaml \
  --private-source /secure/path/private-refs.yaml

# 3) 后续核验：只读批量 SSH，只输出 node_id/status/error_class
scripts/node-inventory/verify-nodes.sh --dry-run
scripts/node-inventory/verify-nodes.sh
```

### 4.4 导入后立即做的事

- 对每个 `alias` 跑一次只读连通测试（§7）。
- 把源文件移入受控归档或按组织策略销毁，销毁需两人确认。
- 在 `plan.md` 记录导入完成，但只写数量与状态。

---

## 5. 清单 schema 与稳定映射

### 5.0 稳定映射

所有脚本和文档共用同一条主链，不允许另建第二套标识：

```text
node_id
  -> ssh_alias            # ~/.ssh/config Host，公开清单
  -> credential_ref       # 加密清单，指向 ssh-agent/keyfile/vault
  -> agent_id             # 公开清单，可为 null（未接入 Agent）
  -> device_ids[]         # 公开清单，可为空
  -> capabilities[]       # 公开清单，受控枚举
  -> last_seen/status     # 公开清单，只读核验或心跳更新
  -> config_version       # 公开清单，整数，每次批准变更 +1
```

`node_id` 永不因换 IP、换用户名、重装而改变；只更新引用字段与时间戳。

### 5.1 公开清单示例（`public-inventory.yaml`，可提交）

```yaml
schema_version: 1
inventory_id: noahsark-nodes-public
updated_at: 2026-10-30T00:00:00Z
updated_by: operator-id
nodes:
  - node_id: win009
    ssh_alias: win009
    os: windows-11
    agent_id: null
    device_ids: []
    capabilities: [serial, audio, dut-control, evidence-upload]
    status: pending
    last_seen_at: null
    last_verified_at: null
    last_verified_result: not_run
    config_version: 0
    owner: node-owner-id
    risk: unknown
```

公开清单**不得**出现 `host`、`host_ref`、`user`、`user_ref`、`credential_ref`、
`agent_url`、`port`、IP、`user@host`、密码、令牌或私钥。校验脚本会失败。

### 5.2 加密清单示例（`nodes.enc.yaml` 解密后的形状）

```yaml
schema_version: 1
inventory_id: noahsark-nodes-private
updated_at: 2026-10-30T00:00:00Z
updated_by: operator-id
nodes:
  - node_id: win009
    ssh_alias: win009
    port: 22
    host_ref: env:ARK_NODE_WIN009_HOST
    user_ref: env:ARK_NODE_WIN009_USER
    credential_ref: ssh-agent:win009-ed25519
    agent_url: null
```

### 5.3 字段定义

| 字段 | 所属清单 | 类型 | 必填 | 敏感度 | 说明 |
|---|---|---|---|---|---|
| `schema_version` | 两者 | int | 是 | C0 | 当前为 `1`，破坏性变更需升版 |
| `inventory_id` | 两者 | string | 是 | C0 | 固定 `noahsark-nodes-public` / `noahsark-nodes-private` |
| `updated_at` | 两者 | RFC3339 | 是 | C1 | UTC 时间，由导入脚本刷新 |
| `updated_by` | 两者 | string | 是 | C1 | 操作员标识，非邮箱也可 |
| `nodes[].node_id` | 两者 | string | 是 | C1 | 唯一主键，`^[a-z][a-z0-9-]{1,31}$` |
| `nodes[].ssh_alias` | 两者 | string | 是 | C1 | SSH 别名，全局唯一；public/private 必须一致 |
| `nodes[].os` | 公开 | enum | 是 | C1 | `windows-11`、`windows-server-2022`、`linux`、`other` |
| `nodes[].agent_id` | 公开 | string/null | 是 | C1 | 未接入 Agent 时为 `null` |
| `nodes[].device_ids` | 公开 | string[] | 是 | C1 | 设备稳定标识，可为空 |
| `nodes[].capabilities` | 公开 | string[] | 是 | C1 | 能力标签，禁止自由文本 |
| `nodes[].status` | 公开 | enum | 是 | C1 | `pending`/`active`/`blocked`/`retired` |
| `nodes[].last_seen_at` | 公开 | RFC3339/null | 是 | C1 | Agent 心跳时间，未接入为 `null` |
| `nodes[].last_verified_at` | 公开 | RFC3339/null | 是 | C1 | 最近一次只读核验时间 |
| `nodes[].last_verified_result` | 公开 | enum | 是 | C1 | `reachable`/`timeout`/`permission_denied`/`error`/`not_run` |
| `nodes[].config_version` | 公开 | int | 是 | C1 | 从 0 开始，批准变更后递增 |
| `nodes[].owner` | 公开 | string/null | 是 | C1 | 节点负责人 |
| `nodes[].risk` | 公开 | enum | 是 | C1 | `low`/`medium`/`high`/`unknown` |
| `nodes[].port` | 加密 | int | 是 | C1 | 1..65535，默认 22 |
| `nodes[].host_ref` | 加密 | string | 是 | C2 | `env:VAR`、`file:/abs/path`、`literal:` |
| `nodes[].user_ref` | 加密 | string | 是 | C2 | 同 `host_ref` 的引用语法 |
| `nodes[].credential_ref` | 加密 | string | 是 | C2 | `ssh-agent:`、`keyfile:/abs/path`、`vault:` |
| `nodes[].agent_url` | 加密 | string/null | 是 | C2 | 无 Agent 或出站长轮询时为 `null` |

### 5.4 禁止字段

以下字段名在任何层级出现即判为缺陷，校验脚本必须失败：

`password`、`passwd`、`pass`、`passphrase`、`secret`、`token`、`api_key`、
`private_key`、`private_key_path`、`ssh_password`、`identity_file`、`id_rsa`、
`id_ed25519`、`authorized_keys`。

校验脚本还会拒绝值里出现私钥块、`AGE-SECRET-KEY-`、OpenSSH 公钥 blob、
`password=`/`passphrase=` 片段；公开清单还拒绝 IPv4 与 `user@host`。

允许的只有 `credential_ref` 这类**间接引用**。Agent 令牌如果要落盘，放
`agent/tokens.enc.yaml` 的独立子树，并在清单里用 `credential_ref: vault:agent/win009`。

### 5.5 校验规则与命令

- `node_id`、`ssh_alias` 全局唯一。
- 每个 `credential_ref` 必须可解析：agent 里有对应 key，或 `keyfile:` 路径存在且 600。
- `host_ref` 解析失败时节点状态为 `blocked`，不得静默跳过。
- `updated_at` 由导入脚本刷新，历史版本由 Git 保存。
- 公开与加密清单的 `node_id -> ssh_alias` 必须完全一致。

```bash
# 公开清单：schema + 唯一性 + 禁止字段
python3 scripts/node-inventory/validate-inventory.py \
  --kind public --inventory config/node-inventory/public-inventory.yaml

# 加密清单：解密后校验（不要落明文文件）
sops -d config/node-inventory/nodes.enc.yaml \
  | python3 scripts/node-inventory/validate-inventory.py \
      --kind private --inventory /dev/stdin --check-refs
```

`--check-refs` 只报告 `node_id` 与字段名，不打印解析出的值；`vault:` 引用标记为
`unverified` 并以退出码 3 表示“合法但未完成解析”，不会假装 `OK`。

---

## 6. 权限、备份与恢复

### 6.1 权限基线

| 对象 | 权限 | 检查命令 |
|---|---|---|
| 本地目录 `~/.config/noahsark/{age,logs,agent,backups}` | `700` | `find ~/.config/noahsark -type d -perm /077` |
| age 私钥 | `600` | `stat -c '%a %n' ~/.config/noahsark/age/keys.txt` |
| SSH 配置/密钥 | `600` | `ssh -G <alias>` 不报权限警告 |
| 公开清单 | `644` | 只允许 C0/C1，schema 校验通过 |
| 加密清单 | `644` 可接受 | 内容已加密 |
| 核验日志 / 审计日志 / 备份 | `600` | 只含 `node_id`、状态枚举与计数 |

`find` 有输出即视为不合规，先修权限再继续。`init-local-store.sh --check`
会做同样的 700/600 校验，且不输出任何密钥内容。

### 6.2 备份

- **公开清单 + 加密清单 + `.sops.yaml`**：`scripts/node-inventory/backup-inventory.sh`
  只复制密文与公钥配置到 `~/.config/noahsark/backups/inventory-<UTC>/`，
  生成 `MANIFEST.json`（SHA-256 只针对密文，不是秘密）与校验回执。
  ```bash
  scripts/node-inventory/backup-inventory.sh --label monthly
  scripts/node-inventory/backup-inventory.sh --verify ~/.config/noahsark/backups/inventory-<UTC>
  ```
- **加密清单**：Git 历史即版本库，另做一份异地密文备份。备份只需要密文，
  所以可以放在普通对象存储。
- **age 私钥**：单独保管，至少两份，其中一份离线（硬件密钥、密封信封、保险柜）。
  不与清单备份放在同一账号、同一云盘、同一仓库。`backup-inventory.sh` 明确不复制
  age 私钥。
- **SSH 私钥**：由 `ssh-agent` 加载，磁盘上保留 600 权限副本，备份策略与 age 私钥同级。
- **不备份**：明文清单、导入临时目录、shell 历史、剪贴板内容。

### 6.3 恢复演练

每季度一次，任选其一：

```bash
# 1. 新机器恢复 age 私钥后能否解密
SOPS_AGE_KEY_FILE=/path/to/keys.txt sops -d config/node-inventory/nodes.enc.yaml >/dev/null && echo RECOVER_OK
# 2. 从密文备份恢复后 schema 校验（不落明文）
scripts/node-inventory/backup-inventory.sh --verify ~/.config/noahsark/backups/inventory-<UTC>
sops -d ~/.config/noahsark/backups/inventory-<UTC>/nodes.enc.yaml \
  | python3 scripts/node-inventory/validate-inventory.py --kind private --inventory /dev/stdin
```

恢复动作本身是写操作：先把备份复制回 `config/node-inventory/nodes.enc.yaml`，
再跑 `verify-nodes.sh --dry-run` 和 `git diff` 人工确认，不能自动覆盖。记录：
恢复耗时、失败点、是否需要重新导入。恢复演练不得在共享终端录屏。

### 6.4 密钥轮换

- age 接收者：成员离开、设备丢失、疑似泄露时立即轮换。
  ```bash
  # 新公钥加入 .sops.yaml 并重新加密 data key；成功解密前不删除旧键
  scripts/node-inventory/rotate-age-recipient.sh --new-recipient age1... --remove-old
  ```
  脚本先备份旧密文，`sops updatekeys` 后强制解密自检；任一步失败即停止。
  **旧 Git 历史仍可被旧键解密**，真正撤销必须同时轮换所有被引用凭据并评估
  重写历史，见 §8.5。
- SSH 操作员密钥：90 天或离职即换。
- 节点主机键：重建节点、疑似中间人、年度审计时更换。
- Agent 证书：30 到 90 天自动续期，到期前 7 天告警。

### 6.5 审计与清理回执

- 审计日志：`~/.config/noahsark/logs/inventory-audit.jsonl`，追加写、600。
  事件：`local_store_init`、`import`、`import_dry_run`、`verify_run`、
  `agent_check`、`backup`、`age_rotate`。
- 每条形如 `{"ts","actor","action","node_id","result","count"}`；**不写**主机、
  用户名、命令、密钥、令牌、完整 `stderr`。
- 核验回执：`verify-YYYYMMDD.jsonl`（逐节点状态）与
  `verify-YYYYMMDD.summary.json`（只含计数），600。
- 清理回执：导入脚本在退出时清零 `mktemp` 临时文件并在审计日志记
  `import` 结果；核对 `ls -l ~/.config/noahsark/logs` 与临时目录为空即可。
  SSD 上删除不等于物理擦除，全盘加密是前提。

---

## 7. 全节点批量只读核验

### 7.1 允许的输出

只有两种结果字段，且都来自受控枚举：

| 字段 | 取值 |
|---|---|
| `status` | `reachable`、`timeout`、`permission_denied`、`error`、`planned`、`skipped` |
| `error_class` | `none`、`timeout`、`permission_denied`、`host_key_unverified`、`connection_refused`、`dns_failure`、`network_unreachable`、`unknown`、`retired` |
| `node_id` | 清单里的标识 |
| `checked_at` | RFC3339 UTC |

**禁止输出**：主机名、IP、用户名、SSH banner、`stderr` 原文、密钥指纹以外的任何
凭据线索。

### 7.2 已实现核验脚本

```bash
# 不连接，只校验清单并列出计划
scripts/node-inventory/verify-nodes.sh --dry-run

# 真跑：BatchMode=yes + per-node timeout + StrictHostKeyChecking=yes
scripts/node-inventory/verify-nodes.sh

# 单节点
scripts/node-inventory/verify-nodes.sh --node-id win009

# 可选：把 last_verified_* 写回公开清单（只写时间与结果，不写主机）
scripts/node-inventory/verify-nodes.sh --update-status
```

脚本实现要点：

- 从 `public-inventory.yaml` 读取 `node_id`/`ssh_alias`，不需要解密清单即可核验。
- `timeout 12`（默认，可调）防止单节点挂住整批。
- `BatchMode=yes` 杜绝交互式密码提示；`PasswordAuthentication=no` 与
  `KbdInteractiveAuthentication=no` 双重关闭交互认证。
- `StrictHostKeyChecking=yes` 杜绝自动接受新主机键；未预置 `known_hosts` 的节点
  判 `error/host_key_unverified`，由人工补录指纹。
- 禁止 `ssh -v`、`-vvv`、`LogLevel=DEBUG`，这些会回显用户名、路径和配置。
- 输出写 `~/.config/noahsark/logs/verify-YYYYMMDD.jsonl`（600），另有
  `verify-YYYYMMDD.summary.json` 只含计数；两者都不含主机、用户或原始错误。
- 批次结束统计：`reachable / timeout / permission_denied / error / skipped` 各多少，
  只报数字与节点计数，不贴原始错误。
- 退出码：0 表示核验流程完成（不代表所有节点可达）；`--fail-on-unreachable`
  时，有任一不可达返回 4；清单/参数错误返回 1。

### 7.3 Agent 状态

当前 Node Agent 是**出站长轮询**，不监听入站端口，因此不存在可探测的
`/healthz`。不要为它伪造一个健康端口。只读排查走 SSH 允许列表：

```bash
# Windows: Get-Service 只读状态
scripts/node-inventory/node-agent.sh --node-id win009 --status

# Linux: systemctl is-active
scripts/node-inventory/node-agent.sh --node-id linux-node-01 --status

# 远程日志仅在明确 opt-in 时输出，可能含非公开控制面地址
scripts/node-inventory/node-agent.sh --node-id win009 --log-tail --allow-log-output
```

脚本按公开清单里的 `os` 选择只读命令，拒绝任意远程命令注入；输出只有
`node_id / platform / agent_service / agent_state / error_class / checked_at`。
`agent_url` 属于 C2，任何情况下不写进日志或屏幕。未配置 Agent 的节点记
`not_installed` 或 `unknown`，不得记成 `ok`。

---

## 8. Node Agent 生命周期

### 8.1 引导（bootstrap）

1. 清单中先登记 `node_id`，状态 `pending`。
2. 控制面签发一次性注册令牌：绑定 `node_id`、TTL 15 分钟、单次使用、绑定主机键指纹。
3. 操作员在节点本机通过本地提示或受保护文件路径注入令牌，**不经过聊天、命令行参数、
   环境变量回显**：
   ```bash
   read -rsp 'enroll token: ' ARK_ENROLL_TOKEN; echo
   ark-agent enroll --token-stdin <<<"$ARK_ENROLL_TOKEN"
   unset ARK_ENROLL_TOKEN
   ```
4. Agent 在本机生成密钥对，私钥不出节点，控制面只存公钥。
5. 建立 mTLS 通道，上报版本、能力、心跳。
6. 清单状态改为 `active`，记录 `last_seen_at` 与 `agent_id`。

### 8.2 轮换

| 对象 | 周期 | 触发条件 |
|---|---|---|
| Agent 证书 | 30 到 90 天 | 到期前 7 天、疑似泄露 |
| 注册令牌 | 一次性 | 使用后立即失效 |
| SSH 主机键 | 年度 | 重装、迁移、疑似中间人 |
| 操作员 SSH 键 | 90 天 | 离职、设备丢失 |
| age 接收者 | 成员变更时 | 私钥泄露 |

轮换必须可回滚：先加新凭据，验证通，再删旧凭据。禁止先删后加。

### 8.3 撤销

撤销顺序固定，避免留下可用后门：

1. 清单标记 `retired`，从批量核验名单移除。
2. 撤销 Agent 证书与所有未使用令牌。
3. 从节点 `authorized_keys` 移除对应公钥，或删除本地账号。
4. 从 `known_hosts` 删除主机键记录（人工确认后）。
5. 失效该节点相关会话与缓存。
6. 审计记录 `agent_revoke`，写明 `node_id`、操作员、原因码。

### 8.4 审计

必要事件：`local_store_init`、`import`、`import_dry_run`、`verify_run`、
`agent_check`、`backup`、`age_rotate`、`agent_enroll`、`agent_revoke`、
`access_denied`。

已实现脚本写入的字段：`ts`、`actor`、`action`、`node_id`、`result`、`count`。
后续接入控制面时再补 `request_id`、`reason_code`。
**不记录**：任何密钥、令牌、口令、完整主机地址、完整 `stderr`。
保留 180 天，安全事件相关保留 1 年。审计日志只追加，不改写。

### 8.5 事故响应

| 场景 | 立即动作 | 后续 |
|---|---|---|
| age 私钥疑似泄露 | 停止清单写入，轮换接收者，重加密 | 轮换所有被引用凭据，全员通知，复盘 |
| SSH 私钥泄露 | 撤销该键，禁用相关账号 | 排查登录历史，重装受影响节点 |
| Agent 令牌泄露 | 撤销令牌与证书 | 检查 Agent 操作日志，评估横向移动 |
| 原始连接表（如 `ssh.txt`）外泄 | 视同全部节点凭据泄露 | 全量轮换口令/密钥/主机键，检查边界日志 |
| 清单被未授权修改 | 回滚到上一 Git 版本，冻结写入 | 定位账号，补审计，双人复核 |

通用流程：**发现 → 遏制（撤销）→ 清除（轮换/重装）→ 恢复（只读核验）→ 复盘**。
每一步都要有人在环，禁止脚本自动“修复”。

---

## 9. Win009 接入清单

### 9.1 操作员需要提供的非敏感元数据

只收这些，且只通过工单或本地文件传递：

| 字段 | 示例 | 说明 |
|---|---|---|
| `node_id` | `win009` | 固定，不复用 |
| `ssh_alias` | `win009` | 与 `~/.ssh/config` 的 `Host` 一致，公开清单 |
| `os` | `windows-11` | 版本可在接入后只读核验 |
| `capabilities` | `serial,audio,dut-control` | 从受控枚举里选 |
| `owner` | `node-owner-id` | 负责人标识 |
| `risk` | `medium` | 初始值，核验后可调整 |
| `port` | `22` | 加密清单；非默认端口才需特别说明 |
| `agent_url` | `https://win009.agent.internal:8443` | 加密清单；出站长轮询时为 `null` |

### 9.2 敏感值只走本地通道

主机地址、登录用户名、SSH 私钥路径、Agent 注册令牌、任何口令，必须通过以下之一：

1. 本机 `read -rsp` 交互输入，不回显、不落历史。
2. 已存在的环境变量，且不 `echo`、不 `set -x`。
3. 600 权限的本地文件路径，由程序读取，不由人 `cat`。

**禁止**：贴进聊天、Issue、PR、邮件、截图、共享文档、CI 日志。
**禁止**：把 `ssh.txt` 或其中任何片段交给模型、脚本或第三方工具解析。

### 9.3 接入步骤

- [ ] 确认 `win009` 的 `node_id` 与 `ssh_alias` 未被占用。`DRAFT · NOT FROZEN`
- [ ] 在 `~/.ssh/config` 增加 `Host win009` 段，指向 600 权限密钥，禁用密码登录。`DRAFT · NOT FROZEN`
- [ ] 人工核验主机键指纹，写入 `known_hosts`，不启用 `accept-new`。`DRAFT · NOT FROZEN`
- [ ] 在公开清单新增元数据，在加密清单新增引用字段，不填任何值。`DRAFT · NOT FROZEN`
- [ ] 本机注入 Agent 注册令牌，完成引导并确认心跳。`DRAFT · NOT FROZEN`
- [ ] 跑单节点只读核验，期望 `status=reachable`；Agent 用 `--status` 单独确认。`DRAFT · NOT FROZEN`
- [ ] 记录 `last_verified_at`、`config_version`，提交密文变更。`DRAFT · NOT FROZEN`
- [ ] 在 `plan.md` 只写“win009 接入完成，只读核验通过”，不写地址与账号。`DRAFT · NOT FROZEN`

### 9.4 单节点核验命令

```bash
scripts/node-inventory/verify-nodes.sh --node-id win009
scripts/node-inventory/node-agent.sh --node-id win009 --status
```

只输出 `node_id` 与状态枚举。不要追加 `whoami`、`hostname`、`ipconfig` 等会泄露环境
信息的命令，除非有明确工单。

---

## 10. 禁止动作

以下行为**无条件禁止**，不因“赶时间”“只看一眼”“本地而已”而例外：

1. **读取或打印 `ssh.txt`**：`cat`、`less`、`more`、`head`、`tail`、`grep`、`awk`、
   `sed`、`python open()`、编辑器打开、复制到剪贴板、计算哈希、上传、截图。
   需要元数据时只统计行数/列数。
2. **把明文提交进 Git**：明文清单、`.env`、私钥、令牌、密码、解密临时文件。
   禁止 `git add -f` 绕过忽略规则。
3. **把秘密放进提示词**：不向任何模型、Agent、Issue、PR 描述里粘贴真实值。
4. **自动破坏性修复**：自动 `ssh-keygen -R`、自动重置密码、自动重启、自动改注册表
   或服务、自动重装、自动删除节点、自动 `rm -rf`。修复必须人工批准并留痕。
5. **口令喷洒/撞库**：不对多台节点用同一口令重试，不遍历用户名，不做“试到通为止”。
6. **共享凭据**：不允许多人共用同一私钥或同一 root 口令；不允许多节点共用密钥。
7. **削弱主机校验**：不全局设置 `StrictHostKeyChecking=no`，不关闭 `known_hosts`。
8. **秘密进日志**：不在 `set -x` 下执行涉密命令，不用 `ssh -v` 排查认证，
   不在 CI 打开 debug，不在共享终端录屏。
9. **绕过审批**：不直接改密文清单而不留提交记录，不跳过双人复核的撤销操作。
10. **用工具代读机密**：不让脚本、插件或子代理去“帮忙看看”密钥文件内容。

发现以上行为，按安全事故处理，先撤销凭据再复盘。

---

## 11. 验收清单与命令

### 11.1 冻结前必须全部通过

| # | 检查项 | 命令 | 期望 | 状态 |
|---|---|---|---|---|
| A1 | age 私钥在仓库外且 600 | `stat -c '%a %n' ~/.config/noahsark/age/keys.txt` | `600` | `DRAFT · NOT FROZEN` |
| A2 | 私钥未被 Git 跟踪 | `git ls-files | grep -E 'keys\.txt$'` | 无输出 | `DRAFT · NOT FROZEN` |
| A3 | 目录无多余权限 | `find ~/.config/noahsark -type d -perm /077` | 无输出 | `DRAFT · NOT FROZEN` |
| A4 | 清单可解密 | `sops -d config/node-inventory/nodes.enc.yaml >/dev/null` | 退出码 0 | `DRAFT · NOT FROZEN` |
| A5 | 公开 schema 合法 | `python3 scripts/node-inventory/validate-inventory.py --kind public --inventory config/node-inventory/public-inventory.yaml` | `RESULT=OK` | `DRAFT · NOT FROZEN` |
| A6 | 加密 schema 合法 | `sops -d ... \| python3 scripts/node-inventory/validate-inventory.py --kind private --inventory /dev/stdin` | `RESULT=OK` | `DRAFT · NOT FROZEN` |
| A7 | 主键/别名唯一 | 上述校验器内置重复检查 | 无 `duplicate_*` 错误 | `DRAFT · NOT FROZEN` |
| A8 | 无明文秘密字段 | 上述校验器内置 forbidden scan | 无 `forbidden_*` 错误 | `DRAFT · NOT FROZEN` |
| A9 | 引用可解析 | `... --kind private --inventory /dev/stdin --check-refs` | 全部 `ok`（`vault:` 计 `unverified`） | `DRAFT · NOT FROZEN` |
| A10 | 批量只读核验 | `scripts/node-inventory/verify-nodes.sh` | 仅输出 `node_id/status/error_class` | `DRAFT · NOT FROZEN` |
| A11 | `win009` 在列 | `grep -c 'node_id: win009' config/node-inventory/public-inventory.yaml` | `1` | `DRAFT · NOT FROZEN` |
| A12 | 备份可恢复 | §6.3 恢复演练 | `RECOVER_OK` | `DRAFT · NOT FROZEN` |
| A13 | 所有者签字 | 工单记录 | 有签字与日期 | `DRAFT · NOT FROZEN` |

### 11.2 一次性命令块

```bash
set -euo pipefail
export SOPS_AGE_KEY_FILE="$HOME/.config/noahsark/age/keys.txt"
PUB=config/node-inventory/public-inventory.yaml
INV=config/node-inventory/nodes.enc.yaml

test "$(stat -c '%a' "$SOPS_AGE_KEY_FILE")" = "600"
test -z "$(git ls-files | grep -E 'keys\.txt$' || true)"
test -z "$(find ~/.config/noahsark -type d -perm /077 -print -quit)"

python3 scripts/node-inventory/validate-inventory.py --kind public --inventory "$PUB"
sops -d "$INV" \
  | python3 scripts/node-inventory/validate-inventory.py --kind private --inventory /dev/stdin
sops -d "$INV" \
  | python3 scripts/node-inventory/validate-inventory.py --kind private --inventory /dev/stdin --check-refs

echo "STATIC_CHECKS_OK"
```

注意：`--check-refs` 在 `ssh-agent` 未运行或 env 变量未注入时会失败，这是
fail-closed 的预期行为；先修环境，不要用 `|| true` 掩盖。

### 11.3 冻结判定

只有同时满足以下条件，才把本文状态从 **DRAFT · NOT FROZEN** 改为 **FROZEN**：

1. 真实清单完成导入，节点数、`win009` 存在性有记录。
2. A1 到 A12 全部通过，命令输出留档（不含秘密）。
3. 批量核验对全部节点出结果，无 `error` 未解释。
4. 平台所有者与安全负责人签字。
5. 源文件已按策略归档或销毁，有两人确认记录。

在此之前，任何人不得把本文当作“已实施”引用。

---

## 12. 参考来源

以下为选型依据，均为官方文档或权威指南：

1. **SOPS（getsops/sops）README 与 `sops` 文档**：加密 YAML 的 `sops` 元数据、
   `creation_rules`、`updatekeys` 与 `SOPS_AGE_KEY_FILE` 用法。用于 §4、§6.4。
   <https://github.com/getsops/sops>
2. **age（FiloSottile/age）官方文档**：`age-keygen`、接收者/身份模型、
   私钥文件权限建议。用于 §4.2、§6。
   <https://github.com/FiloSottile/age>
3. **OpenSSH `ssh_config(5)`**：`Host` 别名、`BatchMode`、`ConnectTimeout`、
   `StrictHostKeyChecking`、`UserKnownHostsFile`、`HashKnownHosts`。用于 §7。
   <https://man.openbsd.org/ssh_config>
4. **OpenSSH `ssh-agent(1)` 与 `ssh-add(1)`**：私钥不落盘、按会话加载、
   转发风险。用于 §3、§4.3。
   <https://man.openbsd.org/ssh-agent>
5. **OWASP Secrets Management Cheat Sheet**：密钥分类、最小权限、
   轮换、审计、禁止硬编码与日志泄露。用于 §1、§2、§8、§10。
   <https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html>
6. **OWASP Logging Cheat Sheet**：日志中排除凭据与个人数据。用于 §7、§8.4。
   <https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html>

---

**文档状态：DRAFT · NOT FROZEN**
未完成真实清单导入与 `win009` 接入前，禁止对外宣称本策略已生效。
