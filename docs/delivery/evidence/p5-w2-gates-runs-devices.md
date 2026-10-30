# P5-W2 门禁、运行、租约、设备、投影证据

> 状态：DONE（开发基线）· 非生产冻结
> 日期：2026-10-29
> 范围：`apps/control_plane/`

## 交付

- `noahsark/services/domain_rules.py`（739 行）：
  - G0–G7 顺序、门禁 run mode、G4 永不计入正式分母
  - Run 状态转移、Attempt 分母资格/重试/守卫
  - Lease 转移、释放三前置、信号投影（通信/占用/许可/执行分离）
  - Device 可用性、进度投影（仅 COUNTS + 已批准分母显示百分比）
- `noahsark/services/read_models.py`：TaskCard/verdict/device 投影接入 domain rules。
- `tests/test_p5_w2_domain_rules.py`：G4 排除、正式分母精确条件、OFFLINE+RUNNING+OCCUPIED+GRANTED 分离、进度未知/定性不显示百分比。

## 关键修复

1. `_upper()` 返回大写，但分母常量是小写，导致正式分母永远不成立；改为大小写一致比较。
2. 释放状态 `held_pending_cleanup` 符合 `evidence-verdict.md`，更新旧测试期望（原 `held`）。
3. mypy 类型窄化（`completed/total`）、ruff 导入与嵌套 if 清理。

## 验证

```text
$ pytest --disable-warnings -q
87 passed

$ ruff check noahsark tests
All checks passed!

$ mypy noahsark
Success: no issues found in 42 source files
```

## 缺口

- W2 以纯函数/投影测试为主；完整 API 场景仍复用 `test_api_batch*`。
- 真实设备 spool/session 事实未接入，W6 真机阶段补。
- 未执行 L2/L3 集成演练。

## 下一步

W3：证据接收、内容寻址、digest 复算、manifest、访问审计、保留。
