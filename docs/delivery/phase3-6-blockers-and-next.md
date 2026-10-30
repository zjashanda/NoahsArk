# Phase 3–6 未完成任务与阻塞清单

> 日期：2026-10-29
> 依据：`.omo/plans/phase3-6-execution.md`
> 当前：18/34 已完成；7 项待执行；9 项因依赖/外部输入标记 `[~]`。

## 一、需要所有者处理的真正阻塞

### B1：真实 TCL/Windows 设备

需要提供：

- 可用 Windows 节点与节点网络地址/出站权限
- TCL001 实际设备、固件版本、音频与串口端点
- `lstest`/工具链安装路径与版本
- 设备控制权限、账号/证书或受控凭据路径
- 真机烟测和正式采样时间窗口

影响：P5-W6、P6-03、P6-04、P6-05、P6-06。

### B2：生产认证

开发期已采用 `X-NoahsArk-Role`。生产前需要：

- OIDC/企业身份提供商或本地账号方案
- issuer、audience、JWKS/client 配置
- 角色与能力映射、会话 TTL、撤销策略

影响：P5-W1 生产化、P5-W7、P5-W9、P6。

### B3：生产证据存储

开发期使用本地内容寻址目录。生产前需要：

- NAS 或对象存储地址/桶/凭据注入方式
- 加密方式、保留期限、删除审批、备份策略
- 下载/上传短期授权句柄策略

影响：P5-W3、P5-W9、P6-04/05/06。

### B4：生产部署与恢复

开发基线采用单 Linux + systemd + Caddy。生产前需要：

- 正式域名/DNS
- TLS 证书策略
- 防火墙与反向代理端口
- 第二服务器/NAS/备份目标
- RPO/RTO 目标与恢复演练窗口

影响：P5-W9、P6-06、P6-08。

### B5：Node Agent 证书与协议

代码可先用 simulator；生产前需要：

- 注册 CA/证书签发与轮换
- 节点撤销机制
- 版本兼容策略
- 出站长轮询或消息网关地址

影响：P5-W5 生产化、P5-W6、P6-03/06。

## 二、没有外部阻塞、应继续执行的任务

### P5-W3：证据接收/manifest/访问/保留

当前已有 `services/evidence_storage.py` 部分产物，但尚无完整测试和证据。继续完成：

- 内容寻址写入与 digest 复算
- manifest expected/received/verified
- 原始证据权限与访问审计
- 保留策略 dry-run
- 篡改、缺失、路径泄露测试

### P5-W4：判定/报告/知识

- Linux 五轴判定服务
- 正式 PASS 精确元组
- 14 章节报告与版本冻结
- 知识候选人工审阅/推广
- TaskCard 投影

### P5-W5：Node Agent simulator

当前 `apps/node_agent/` 已有部分文件，但证据未收口。先完成：

- 心跳/租约/epoch
- STOP-first spool
- digest/工件校验
- cleanup receipt
- `node_observed_*` facts-only 测试

真实 Windows 服务和设备链路等 B1/B5 输入。

### P5-W7：生产 UI 接入

- API/事件/权限渲染
- 错误边界、双语、a11y
- 39 路由生产读模型
- API/fixture 边界

### P5-W8：端到端模拟集成

- Intake → Approval → Gates
- Run → Attempt → Evidence → Verdict
- STOP-first → Reconcile → Release
- 使用 simulator，不等待真实 TCL。

### P5-W9：开发部署/安全证据

可以先完成：

- systemd/Caddy 配置静态验证
- 秘密扫描、最小权限、日志/健康检查
- 本地备份/恢复 dry-run
- 性能基线

真实域名、TLS、第二服务器等 B4 输入到位后再做生产部署。

### P5-W10：验收准备

- 环境清单
- 责任矩阵
- 缺陷模板
- L1–L5 证据目录
- 执行脚本与报告模板

## 三、Phase 6 依赖关系

- P6-01/P6-02：P5-W8 后可执行，主要是静态/模拟验收。
- P6-03：依赖 B1/B5，真实设备烟测。
- P6-04：依赖 B1/B3，正式采样与 Linux 独立判定。
- P6-05：依赖报告/知识/证据闭环。
- P6-06：依赖 B3/B4/B5，恢复与备份演练。
- P6-07：依赖前述验收结果。
- P6-08：所有验收证据齐全后才能归档冻结。

## 四、当前执行顺序

```text
P5-W3 → P5-W4 → P5-W5 simulator → P5-W7 → P5-W8
→ P5-W9 开发安全/部署 → P5-W10
→ P6-01/P6-02
→ 等 B1/B2/B3/B4/B5 输入
→ P6-03/P6-04/P6-05/P6-06
→ P6-07/P6-08
```

## 五、处理完成后的回复格式

用户可一次性回复：

```text
B1: 已提供 Windows/TCL/工具链/时间窗
B2: 认证方案与配置来源
B3: 证据存储方案
B4: 域名/TLS/备份/RPO/RTO
B5: Node Agent CA/协议/网关
```

没有提供真实值的项目继续保持 `[~]`，不以 mock 数据冒充生产输入。
