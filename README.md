# NoahsArk

NoahsArk 是 AI 资深测试工程师平台的方案仓库。

## 当前状态

- `docs/v2/`：总体方案与 UI 基线
- `solutions/1027V1/`：当前 V1 模块级实施设计、远程执行方案、缺口关闭方案、评审优化和总流程图
- `openspec/`：AI Test Platform v2 OpenSpec 变更
- `design/` / `assets/`：UI 原型、设计令牌、线框和方舟品牌资产
- 产品后端尚未实现；当前仓库是设计与规格交付包

## 目标 Linux 目录

```text
/home/bszheng/NoahsArk
```

## 重要边界

- Linux 是控制面和开发/运行服务器。
- Windows 节点负责本地串口、声卡、电源、设备和 lstest 执行。
- 真实执行必须有节点回执、证据 manifest、租约和 C1-C7 门禁。
- 不提交凭据、token、OpenCode 会话、缓存数据库或本地 `.omo/.opencode` 状态。
