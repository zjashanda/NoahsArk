# 节点清单工作流：证据与决策记录

- 日期：2026-10-30
- 范围：本地节点清单、加密存储、一次性导入、只读批量核验、Agent 只读排查
- 状态：**工作流骨架已验证；真实节点未导入、未核验**
- 关联策略：`docs/delivery/node-inventory-management.md`
- 操作手册：`config/node-inventory/README.md`
- 未读文件：`ssh.txt`（未打开、未统计、未复制、未哈希）

## 1. 结论

1. 节点资产采用**双清单**：`config/node-inventory/public-inventory.yaml` 只放
   `node_id -> ssh_alias -> agent_id -> device_ids -> capabilities ->
   last_seen/status/config_version`；`nodes.enc.yaml` 用 SOPS + age 加密保存
   `port -> host_ref -> user_ref -> credential_ref -> agent_url`。
2. 凭据只允许引用（`ssh-agent:` / `keyfile:` / `vault:`），schema 与校验器都会
   拒绝明文密码、私钥、令牌、公网/内网地址（公开清单）和 `user@host`。
3. 导入、核验、Agent 排查、备份、轮换全部有脚本；脚本默认只读、fail-closed、
   只输出标识与枚举。
4. 当前没有真实清单，因此公开清单保持 `nodes: []`，**没有声称任何节点可达**。

## 2. 工具检查结果

| 工具 | 结果 | 用途 | 影响 |
|---|---|---|---|
| `sops` | **MISSING** | 加密/解密清单、`updatekeys` | 加密清单无法生成；导入器会 `missing_tool=sops` |
| `age` / `age-keygen` | **MISSING** | 生成本地身份、加解密 | `init-local-store.sh --generate-key` 失败；`.sops.yaml` 仍是占位接收者 |
| `ssh` | 存在 `/usr/bin/ssh` | 批量只读核验 | 可用 |
| `ssh-agent` / `ssh-add` | 存在 `/usr/bin/...` | 凭据引用与解析 | 可用；本机未确认已加载 key |
| `ssh-keygen` | 存在 | 主机键/操作员键管理 | 可用 |
| `python3` | 3.12.3 | 校验器 | 可用 |
| `PyYAML` | 6.0.1 | YAML 解析 | 可用 |
| `jsonschema` | 4.10.3 | JSON Schema 校验 | 可用 |
| `jq` / `curl` / `timeout` | 存在 | 辅助 | 可用 |
| `yq` | MISSING | 旧文档示例使用 | 已从必需路径移除；校验器不依赖 `yq` |

## 3. 已落地文件

| 路径 | 作用 |
|---|---|
| `config/node-inventory/public-inventory.yaml` | 公开清单，当前 `nodes: []` |
| `config/node-inventory/schema/node-inventory.public.schema.json` | 公开清单 schema |
| `config/node-inventory/schema/node-inventory.private.schema.json` | 加密清单 schema |
| `config/node-inventory/.sops.yaml` | age 公钥占位 + creation rule |
| `config/node-inventory/templates/public-inventory.example.yaml` | 导入契约：公开元数据 |
| `config/node-inventory/templates/private-inventory.example.yaml` | 导入契约：连接引用 |
| `config/node-inventory/README.md` | 操作员手册 |
| `scripts/node-inventory/lib.sh` | 路径、审计、拒绝 `ssh.txt`、安全边界 |
| `scripts/node-inventory/init-local-store.sh` | 本地 700/600 存储 + age 身份 |
| `scripts/node-inventory/import-inventory.sh` | 一次性/重复导入，原子写入 |
| `scripts/node-inventory/validate-inventory.py` | schema/唯一性/禁止字段/引用解析 |
| `scripts/node-inventory/verify-nodes.sh` | 批量只读 SSH 核验 |
| `scripts/node-inventory/node-agent.sh` | 按 `node_id` 只读排查 Agent 服务 |
| `scripts/node-inventory/backup-inventory.sh` | 密文备份 + 校验回执 |
| `scripts/node-inventory/rotate-age-recipient.sh` | age 接收者轮换 |

## 4. 实际执行过的命令与结果

```text
bash -n scripts/node-inventory/*.sh            -> BASH_SYNTAX_OK
python3 -m py_compile validate-inventory.py    -> PY_COMPILE_OK
validate public-inventory.yaml                 -> KIND=public NODES=0 RESULT=OK
validate templates/public-inventory.example    -> KIND=public NODES=1 RESULT=OK
validate templates/private-inventory.example   -> KIND=private NODES=1 RESULT=OK
validate leaky public sample (host + IP)       -> FAIL: additionalProperties,
                                                  public_forbidden_key:host,
                                                  forbidden_value:ipv4_literal
validate sample with password key              -> FAIL: forbidden_key:password
validate private refs (600 keyfile + literal)  -> RESULT=OK (rc=0)
same refs with keyfile mode 644                -> FAIL ref=credential_ref (rc=1)
import --source <symlink named inventory.yaml>  -> refused_raw_connection_source
                                                  resolved_basename=ssh.txt
verify-nodes.sh --dry-run (empty inventory)    -> total=0, rc=0
verify-nodes.sh --dry-run (template)           -> win009 planned/none, rc=0
import-inventory.sh --source ssh.txt           -> refused_raw_connection_source, rc=1
import-inventory.sh --source <template> --dry-run -> DRY_RUN=ok public_nodes=1
init-local-store.sh --check (temp store)       -> LOCAL_STORE=OK age_key=absent
init-local-store.sh --generate-key             -> missing_tool=age-keygen, rc=1
backup-inventory.sh --label test               -> BACKUP_VERIFY=ok files=2
backup-inventory.sh --verify <dir>             -> BACKUP_VERIFY=ok files=2
node-agent.sh (no args)                        -> missing_argument=--node-id
node-agent.sh --log-tail (no opt-in)           -> log_output_requires=--allow-log-output
node-agent.sh --node-id nope                   -> node_id_not_found=nope
```

说明：

- `--dry-run` 的 `win009 planned` 来自模板文件，只验证脚本分支，**不代表已连接**。
- 失败样例在 `/tmp` 临时目录生成并在同一条命令内删除，未写入仓库。
- 所有命令均未连接远程节点、未安装/修改远程服务、未创建账号、未改凭据。

## 5. 关键决策

1. **双清单而非单文件**：公开元数据需要被批量核验脚本和后续 UI 读取，不应强制解密；
   连接引用与主机地址只在加密清单。两者用 `node_id`/`ssh_alias` 强一致校验。
2. **SOPS + age 仍是目标方案**：虽然本机缺工具，但脚本已按该方案实现并 fail-closed；
   不退回明文 YAML 或 `.env`。
3. **导入器不接受 `ssh.txt`**：只接受用户提供的脱敏公开文件 + 引用文件。Agent 不读
   原始连接表；`lib.sh` 在读取前按 basename 拒绝。
4. **`yq` 降级为非必需**：校验器用 Python + `jsonschema`，减少工具依赖和版本漂移。
5. **Agent 健康不探测 `/healthz`**：Node Agent 是出站长轮询，不监听入站端口。
   排查改为 SSH 允许列表（服务状态/日志），避免伪造不存在的健康端点。
6. **核验不自动改状态**：默认输出回执；只有显式 `--update-status` 才写
   `last_verified_*`，且只写时间与结果。
7. **备份只含密文**：`backup-inventory.sh` 明确不复制 age 私钥；恢复是人工写操作。

## 6. 阻塞与下一步

### 阻塞 1：缺少加密工具

- 现象：`sops`、`age`、`age-keygen` 均 MISSING。
- 影响：`nodes.enc.yaml` 无法生成；`.sops.yaml` 仍是
  `age1REPLACE_WITH_OPERATOR_PUBLIC_KEY` 占位。
- 解除：操作员安装 `sops` 与 `age`，然后执行
  `scripts/node-inventory/init-local-store.sh --generate-key --write-sops-config`。
- 未解除前不得声称加密清单已建立。

### 阻塞 2：没有脱敏别名清单

- 现象：没有用户提供 `sanitized-public.yaml` / `private-refs.yaml`；`win009` 仅存在
  于模板，公开清单为空。
- 影响：无法进行真实导入，也无法产生任何 `reachable` 结果。
- 解除：用户提供脱敏公开元数据，并通过本机受保护通道提供引用文件；或用户自行运行
  `import-inventory.sh`。
- 未解除前 `verify-nodes.sh` 只能 `--dry-run`，输出 `total=0`。

### 阻塞 3：主机键与 SSH 别名未由本任务核验

- 现象：未读取 `~/.ssh/config` 内容，未连接任何节点，未核对 `known_hosts` 指纹。
- 影响：即使清单导入，节点也可能返回 `host_key_unverified` 或
  `permission_denied`，这是预期结果，不是脚本缺陷。
- 解除：操作员人工核验指纹、写入 `known_hosts`，再跑
  `verify-nodes.sh --node-id <id>`。

## 7. 操作员最短路径

```bash
# 1. 安装 sops + age 后
scripts/node-inventory/init-local-store.sh --generate-key --write-sops-config

# 2. 准备仓库外脱敏文件后
scripts/node-inventory/import-inventory.sh \
  --source /secure/sanitized-public.yaml \
  --private-source /secure/private-refs.yaml

# 3. 核验
scripts/node-inventory/verify-nodes.sh --dry-run
scripts/node-inventory/verify-nodes.sh

# 4. 备份
scripts/node-inventory/backup-inventory.sh --label first-import
```

本记录不包含任何主机、用户名、密码、私钥、令牌或 SSH 行。`ssh.txt` 全程未被读取。
