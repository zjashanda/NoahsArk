# NoahsArk

NoahsArk 是 AI 资深测试工程师平台的方案仓库。

## 当前状态

- `docs/VERSIONING.md`：目录总览、材料状态和后续每版独立目录的三段式方案版本规则
- `docs/v2/`：总体方案与 UI 基线
- `solutions/1027V1/`：当前 V1 模块级实施设计、远程执行方案、缺口关闭方案、评审优化和总流程图
- `openspec/`：AI Test Platform v2 OpenSpec 变更
- `design/` / `assets/`：UI 原型、设计令牌、线框和方舟品牌资产
- `docs/references/`：保留的跨版本参考图和资料，不等同于已批准方案
- 产品后端尚未实现；当前仓库是设计与规格交付包

## 现有入口

- [版本与目录指南](docs/VERSIONING.md)
- [事实源冲突登记](docs/delivery/source-reconciliation.md)
- [保留的参考资料](docs/references/README.md)
- [v2 文档索引](docs/v2/README.md)
- [1027V1 方案索引](solutions/1027V1/README.md)
- [OpenSpec 变更说明](openspec/changes/ai-test-platform-v2/README.md)
- [设计线框索引](design/wireframes/README.md)

## 目标 Linux 目录

```text
/home/bszheng/NoahsArk
```

## 重要边界

- Linux 是控制面和开发/运行服务器。
- Windows 节点负责本地串口、声卡、电源、设备和 lstest 执行。
- 真实执行必须有节点回执、证据 manifest、租约和 C1-C7 门禁。
- 不提交凭据、token、OpenCode 会话、缓存数据库或本地 `.omo/.opencode` 状态。
