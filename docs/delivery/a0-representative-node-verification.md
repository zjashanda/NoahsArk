# A-0 代表性 Windows 节点与 DUT 只读验证

> 日期：2026-10-29  
> 状态：**代表性节点事实已验证；A-0 仍未整体通过**。  
> 范围：仅验证一台由所有者指定的 Windows 节点和一套 TCL/ListenAI DUT 链路；结论不得外推到其他节点或设备。  
> 安全边界：凭据仅在进程内使用；本文不记录主机地址、用户名、口令、原始设备序列号或完整 PnP Instance ID；未刷机、未重启、未改配置、未执行破坏性动作。

## 1. 验证结论

| 项目 | 结果 | 证据范围 |
|---|---|---|
| SSH 只读连通 | PASS | 受限连接记录 + 一次只读远程命令；敏感值不落仓库 |
| Windows | PASS | Windows 11 专业版，64 位，version/build `10.0.26200` / `26200` |
| 运行形态 | PASS（有风险） | QEMU `Standard PC (Q35 + ICH9, 2009)`；16 GiB 内存；属于虚拟机事实，不代表物理节点 |
| 交互式桌面会话 | PASS | 发现 1 个活动 Explorer session；只证明采集时刻可用 |
| Python | NEEDS-FIX | `py` / `python` 均为 `3.10.11`，低于方案目标 `3.11/3.12`；正式节点运行时必须升级或重建受控 venv |
| D: 证据/spool 盘 | PASS | NTFS，200 GiB，采集时约 199.3 GiB 可用 |
| 时区 | PASS（部分） | `China Standard Time`，采集时为 UTC+08:00；NTP 源与偏差尚未验证 |
| 串口枚举 | PASS | COM3/4/5/6/7 均为 `OK`；见 §2 |
| ListenAI 音频端点 | PASS | 当前活动麦克风与扬声器各 1 个为 `OK`；另有历史残留的 Unknown 端点，禁止自动绑定 |
| 真机唤醒 | PENDING | 本轮未播放“小T小T”、未录音、未读取业务日志；需所有者明确非破坏性测试许可和 formal profile/script |

## 2. 当前端点事实

### 2.1 串口与 USB

| 端口 | 当前枚举 | 状态 | VID/PID | 用途来源 |
|---|---|---|---|---|
| COM3 | USB-SERIAL-A CH344 | OK | `VID_1A86&PID_55D5` | 所有者：CSK 日志，921600 |
| COM4 | USB-SERIAL-C CH344 | OK | `VID_1A86&PID_55D5` | 所有者：Hisilicon 日志，921600 |
| COM5 | USB-SERIAL-D CH344 | OK | `VID_1A86&PID_55D5` | 用途待确认 |
| COM6 | USB 串行设备 | OK | `VID_8765&PID_5678` | 所有者：ListenAI VCOM |
| COM7 | USB-SERIAL-B CH344 | OK | `VID_1A86&PID_55D5` | 用途待确认 |

节点还保留 COM8–COM11 的历史 `Unknown` 枚举。实现必须只绑定当前 `OK` 端点及其受控身份摘要，不能按友好名或历史 COM 号自动选择。

### 2.2 音频

- 当前活动 Capture：`麦克风 (ListenAI Audio)`，状态 `OK`；所有者声明 8 声道、`VID_8765&PID_5678`。
- 当前活动 Render：`扬声器 (ListenAI Audio)`，状态 `OK`；所有者声明 2 声道、`VID_8765&PID_5678`。
- 节点存在带 `2-` / `3-` 前缀的历史 `Unknown` 麦克风与扬声器端点；这些端点不得作为候选自动回退。
- 稳定绑定必须使用当前 PnP/endpoint 身份的脱敏摘要，并与项目/设备/固件绑定；不得只使用友好名。

## 3. DUT 所有者输入

| 字段 | 当前值 | 状态边界 |
|---|---|---|
| 项目 | TCL | 所有者确认 |
| 代表性 DUT | `TCL001` | 所有者确认；作为首个正式 DUT |
| ListenAI 板卡/功能标识 | `ListenAIVCOM` | 所有者确认；是否为精确硬件料号仍待确认 |
| 当前固件 | `V038` | 所有者确认 |
| 允许固件白名单 | `V038` | 所有者确认 |
| 数量 | 1 | 本轮代表性验证范围 |
| 唤醒词 | “小T小T” | 所有者确认；尚未执行唤醒测试 |

## 4. 仍未关闭的代表节点/DUT 输入

1. 服务账户/Node Agent/adapter/lstest pin 尚未构建或验证。
2. Python 3.10.11 不满足目标 3.11/3.12。
3. COM5 与 COM7 已确认当前不使用；后续适配器必须以“不打开这两个端口”作为负向检查。
4. DUT 硬件版本、脱敏序列号/identity digest 仍未确认。普通恢复可通过 A/COM3 串口重启；硬件复位存在但当前不作为常规动作。
5. 正式 profile、TCL 任务脚本、正式命令/参数/阈值尚未提供。
6. mTLS 节点证书、节点主动出站到控制面的链路、NTP 偏差、STOP/租约/清理状态尚未验证。
7. 本轮未执行音频播放、录音、唤醒、串口日志读取或任何业务判定。

## 5. A-0 边界

本报告将“没有任何真实 Windows/设备事实”推进为“已有一台代表节点和一套 DUT 的部分直接证据”，但不能关闭 A-0。正式进入 L3 仍需 Node Agent/运行时、证书与出站链路、formal profile/script、证据根、负责人和真机窗口；L4/L5 还需要 NAS/第二服务器和恢复演练。
