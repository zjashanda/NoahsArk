# NoahsArk 节点清单（本地加密存储）

> 状态：可执行骨架 · 真实节点尚未导入
> 策略全文：`docs/delivery/node-inventory-management.md`
> 证据与决策：`docs/delivery/node-inventory-workflow-evidence.md`

本目录只放**可提交**内容：公开清单、JSON Schema、SOPS 公钥配置、无真实值的模板。
连接信息密文 `nodes.enc.yaml` 在首次导入后生成；明文和 age 私钥永远不在此目录。

## 1. 文件职责

| 路径 | 内容 | 进 Git |
|---|---|---|
| `public-inventory.yaml` | `node_id -> ssh_alias -> agent_id -> device_ids -> capabilities -> last_seen/status/config_version` | 可以 |
| `nodes.enc.yaml` | `port -> host_ref -> user_ref -> credential_ref -> agent_url` 的 SOPS 密文 | 可以（仅密文） |
| `.sops.yaml` | age **公钥**与 creation rule | 可以 |
| `schema/*.schema.json` | 公开/加密清单 JSON Schema | 可以 |
| `templates/*.yaml` | 导入契约样例，无真实值 | 可以 |
| `~/.config/noahsark/age/keys.txt` | age 私钥 | **绝对不可以** |
| `~/.config/noahsark/logs/*` | 审计与核验回执 | 不适用（仓库外） |

## 2. 一次性准备

前置：`sops`、`age`、`ssh`、`python3`、`pyyaml`、`jsonschema`。

```bash
# 只打印 age 公钥，不打印私钥
scripts/node-inventory/init-local-store.sh --generate-key --write-sops-config

# 校验目录/密钥权限
scripts/node-inventory/init-local-store.sh --check

# 工具自检（缺失会明确报 missing_tool）
scripts/node-inventory/validate-inventory.py --kind public \
  --inventory config/node-inventory/public-inventory.yaml
```

若 `sops` / `age` 缺失，先由操作员安装，不要用未加密文件替代。脚本会 fail-closed。

## 3. 导入

准备两个仓库外文件：

1. `sanitized-public.yaml`：只含公开元数据，形状见
   `templates/public-inventory.example.yaml`。
2. `private-refs.yaml`：只含引用，形状见
   `templates/private-inventory.example.yaml`。**不要写密码、私钥、令牌全文。**

```bash
# 先 dry-run：只校验和合并，不写文件、不连接节点
scripts/node-inventory/import-inventory.sh \
  --source /secure/path/sanitized-public.yaml \
  --private-source /secure/path/private-refs.yaml \
  --dry-run

# 正式写入：公开清单明文，连接引用 SOPS 密文
scripts/node-inventory/import-inventory.sh \
  --source /secure/path/sanitized-public.yaml \
  --private-source /secure/path/private-refs.yaml
```

导入器行为：

- 按 basename 拒绝 `ssh.txt`，永远不会打开原始连接表。
- 校验 schema、`node_id`/`ssh_alias` 唯一性、禁止字段/值。
- 公开与加密清单的 `node_id -> ssh_alias` 必须一致。
- 只输出节点计数与 `IMPORT=ok`，不输出任何字段值。
- 已存在的加密清单先解密、按 `node_id` 合并、再重新加密；旧密文自动备份。
- 临时明文只存在于 700 的 `mktemp -d`，退出时 `shred`/删除。

## 4. 后续核验

```bash
# 不连接节点
scripts/node-inventory/verify-nodes.sh --dry-run

# 批量只读 SSH；BatchMode=yes + timeout + StrictHostKeyChecking=yes
scripts/node-inventory/verify-nodes.sh

# 单节点
scripts/node-inventory/verify-nodes.sh --node-id win009

# 可选写回 last_verified_*（只写时间/结果）
scripts/node-inventory/verify-nodes.sh --update-status

# Agent 只读排查（Node Agent 是出站长轮询，没有入站 /healthz）
scripts/node-inventory/node-agent.sh --node-id win009 --status
```

输出只允许 `node_id / status / error_class / checked_at`。若 `known_hosts` 未预置，
节点会得到 `error / host_key_unverified`，这是正确结果，需人工核验指纹后再重跑。

## 5. 备份、轮换、撤销

```bash
# 只备份密文 + 公开清单 + .sops.yaml，含 SHA-256 回执
scripts/node-inventory/backup-inventory.sh --label monthly
scripts/node-inventory/backup-inventory.sh --verify ~/.config/noahsark/backups/inventory-<UTC>

# 轮换 age 接收者（先加新键，成功解密后再移除旧键）
scripts/node-inventory/rotate-age-recipient.sh --new-recipient age1... --remove-old
```

撤销顺序与事故响应见策略文档 §8.3/§8.5。脚本不会自动重置密码、重启节点或修改
远程服务。

## 6. 当前阻塞

- 本机未安装 `sops`、`age`/`age-keygen`，加密清单尚未生成。
- 没有用户提供的脱敏别名清单，公开清单保持 `nodes: []`。
- 因此**没有任何节点被声称可达**；`verify-nodes.sh` 只做过 `--dry-run`。
