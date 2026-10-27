# 12 · Agent

- 路由：`/aitest/agents`
- 目标：看清每个 Agent 的模型、OpenSpec 上下文、写范围、审查要求与配置漂移。
- 权限：1 至 4 可读；编辑/渲染/漂移检查 4。
- 能力：agent registry、OpenSpec context、write scope、review、render drift。

## 桌面 1440

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Agent | 8 个角色，1 项渲染漂移                [渲染配置]  [漂移检查]         │
│ registry.yaml 是唯一源；生成文件手改会被拒绝。                               │
├──────────────────────────────────────────────────────────────────────────────┤
│ 角色              模型绑定        上下文 写范围        工具 审查 漂移  最近渲染│
│ lead              G deepseek-v4  4      .aitest/**    6    是   ✓     13:10  │
│ planner           A gpt-5.6      3      .aitest/plans 4    是   ✓     13:10  │
│ case_writer       G deepseek-v4  3      .aitest/**    4    是   ✓     13:10  │
│ script_implementer G deepseek-v4 4      src/**, tasks 7    是   ⚠     13:10  │
│ reviewer          A glm-5        2      —             3    是   ✓     13:10  │
│ oracle            G deepseek-v4  2      —             3    是   ✓     13:10  │
│ device            G qwen3-max    2      —             5    是   ✕ 缺 13:10  │
│ knowledge_curator G deepseek-v4  2      kb/**         4    是   ✓     13:10  │
├──────────────────────────────────────────────────────────────┬───────────────┤
│ 选中：script_implementer                                     │ 权限矩阵      │
│ 职责 实现测试脚本、运行预检、修复 test_logic                  │ ───────────── │
│ 模型策略 agent_role=script_implementer requires=tool_calling  │ 角色 read write│
│ OpenSpec context test-plan-apply / test-plan-validate        │ lead   ✓    —  │
│ 允许命令 apply, validate                                     │ planner ✓   ✓  │
│ 写范围 openspec/changes/<change>/tasks.md, src/**            │ case   ✓   ✓  │
│ 工具 read, grep, glob, bash, write                           │ script ✓   ✓  │
│ 技能 lstest, trails                                          │ review ✓   —  │
│ 审查 required · reviewer_must_differ_family=true             │ oracle ✓   —  │
│ 漂移 registry 与生成文件不一致 → [查看差异] [重新渲染]        │ device ✓   —  │
│ 最近审计 10-25 王工 修改 write_scope · 成功                  │ kb     ✓   ✓  │
└──────────────────────────────────────────────────────────────┴───────────────┘
```

## 漂移差异抽屉

```
registry.yaml vs .opencode/agent/script_implementer.md
- write_scope: ["src/**"]
+ write_scope: ["openspec/changes/<change>/tasks.md","src/**"]
原因：registry 已更新，生成文件未渲染
[重新渲染]（4）  [下载差异]
```

## 状态

```
加载：    表格骨架；详情骨架
空：      “尚未初始化 Agent 注册表” + [下载模板]（4）
错误：    registry 无效：氧化红横幅 + 校验路径；禁止渲染
阻塞：    漂移未解决：赭石横幅；真实执行可能受影响
陈旧：    最近渲染 >7 天：灰“配置可能过期”
禁用：    非 4 编辑/渲染/漂移检查
```

## 手机 390

```
┌────────────────────────────┐
│ ☰ Agent            [渲染]  │
│ 8 角色 · 1 漂移            │
├────────────────────────────┤
│ script_implementer   ⚠     │
│ G deepseek-v4 · 审查 是    │
│ 写范围 src/** · 工具 7     │
│ [详情]                     │
├────────────────────────────┤
│ …… 角色卡                  │
└────────────────────────────┘
详情：全屏；权限矩阵容器内横向滚动
```

## 边界

- 不提供直接编辑 `.opencode/agent/*.md`；只能改 registry。
- 审查要求不可单个关闭，必须改策略并审计。
- 生成文件写操作需 review receipt，UI 显示回执号。
