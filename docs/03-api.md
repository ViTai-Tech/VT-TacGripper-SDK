# 📚 API 文档

本页只覆盖高层控制类 `VTacGripper`。`Bus`、`OpenDevice`、`DmMotor` 等底层接口属于进阶用法，不在本手册展开。

> 💡 **阅读前提**
> 示例假设夹爪已经完成标定，并且 `devices.json` 中存在对应 SN 的记录。未标定时，`position`、`move()`、`open()`、`close()` 等行程接口会报错。

---

## 🧭 导入

```python
from VT_TacGripper import VTacGripper
```

`VTacGripper` 是上下文管理器：`with` 退出时自动调用 `release()`。

---

## 🏗️ 构造

### 📝 语法

```python
VTacGripper(
    sn=None,
    *,
    bus=None,
    store=None,
    config_path=None,
    product_model=None,
    control_hz=None,
    travel=None,
    control_mode="pos_force",
    auto_register=False,
    auto_enable=False,
    channel=0,
)
```

### 🔧 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `sn` | `None` | 适配器 SN；`None` 时自动检测（仅单适配器可用，多适配器会报错） |
| `bus` | `None` | 复用的总线对象；一般不需要传 |
| `store` | `None` | 复用的配置存储对象；一般不需要传 |
| `config_path` | `None` | 一机一码配置路径；`None` 使用 `~/.config/vitai-sdk/devices.json` |
| `product_model` | `None` | VT 产品型号；首次注册必需，之后从配置读取 |
| `control_hz` | `None` | 本次运行的控制频率覆盖值；非默认值会写入 `overrides` |
| `travel` | `None` | 本次运行的额定行程覆盖值；非默认值会写入 `overrides` |
| `control_mode` | `"pos_force"` | 控制模式：`"pos_force"`（默认）或 `"pos_vel"` |
| `auto_register` | `False` | 配置中无该 SN 时是否自动注册 |
| `auto_enable` | `False` | 构造完成后是否立即使能并保持当前位置；默认不使能 |
| `channel` | `0` | CAN 通道号 |

### ⚠️ 构造行为

- 按 SN 读取配置，打开适配器并读取实机量程。
- 按 `product_model` 推导 geometry/电机型号；实机与产品型号不一致时直接报错（S/L 可校验；S/Slim 依靠标定跨度检查）。
- 显式写入并读回校验 `control_mode`；固件不支持时抛 `MotorModeError`，不会静默回退。
- **默认不使能**；构造后需调用 `enable()`，或传 `auto_enable=True` 立即使能并保持。
- 配置中不存在 SN 且未开启 `auto_register` 时，会抛出 `RuntimeError`。

### 💡 示例

```python
from VT_TacGripper import VTacGripper

with VTacGripper("<SN>", config_path="./devices.json") as g:
    g.enable()
    try:
        print(g.sn, g.unit, g.is_calibrated)
    finally:
        g.disable()
```

首次注册：

```python
with VTacGripper(
    "<SN>",
    product_model="VT-TacGripper-85-S",
    config_path="./devices.json",
    auto_register=True,
) as g:
    g.enable()
    ...
```

---

## 🎛️ 属性

| 属性 | 类型 | 说明 |
| --- | --- | --- |
| `g.sn` | `str` | 适配器 SN |
| `g.unit` | `str` | 行程单位：`mm` 或 `deg` |
| `g.is_calibrated` | `bool` | 是否已有张开/闭合限位 |
| `g.state` | `MotorState` | 最新反馈快照，字段见下方 |
| `g.age` | `float` | 最近反馈年龄（秒）；从未收到反馈时为 `inf` |
| `g.error()` | `str` | 当前固件状态中文文本，如 `使能`、`过载` |
| `g.mapping()` | `RangeMap` | 当前行程↔弧度映射；未标定时抛 `RuntimeError` |
| `g.open_value` | `float` | 张开位行程值（平行 0 mm；圆弧为最大角度） |
| `g.close_value` | `float` | 闭合位行程值（平行为最大行程；圆弧 0°） |
| `g.position` | `float` | 当前行程位置（mm 或 deg）；未标定时抛 `RuntimeError` |
| `g.position_rad` | `float` | 当前电机位置（rad） |
| `g.velocity` | `float` | 当前电机速度（rad/s） |
| `g.torque` | `float` | 当前电机力矩（Nm） |
| `g.control_mode` | `ControlMode` | 构造时确认的控制模式 |
| `g.enabled` | `bool` | 电机当前是否处于使能状态 |
| `g.is_online(timeout=0.5)` | `bool` | 最近反馈是否在 `timeout` 秒内 |

---

## 🔌 使能、失能与关闭

### `enable()` / `disable()`

```python
g.enable(hold=True)   # 使能；默认保持当前位置
g.disable()           # 显式失能
```

| 方法 | 说明 |
| --- | --- |
| `g.enable(hold=True)` | 使能电机；`hold=True` 时随后保持当前位置。无反馈导致无法保持时会抛异常 |
| `g.disable()` | 失能电机；不会自动重新使能 |
| `g.enabled` | 当前软件记录的使能状态 |

> 💡 **显式生命周期**
> 构造默认不使能。`move/open/close/jog/hold/move_rad` 在未使能时会抛出 `RuntimeError`；先调用 `g.enable()`。`release()` 不改变使能状态，需要失能时显式调用 `g.disable()`。

### `release()` / `with`

```python
g.release()
```

停止发送流、补发保持帧并释放电机对象；**不改变使能状态**，重复调用无副作用。使用 `with` 时自动调用 `release()`，但不会自动 `disable()`。

---

## 🏃 运动控制

### `move()`

```python
g.move(
    value,
    *,
    vel=None,
    force=None,
    block=False,
    timeout=None,
    position_tolerance=None,
    velocity_tolerance=...,
) -> MoveResult | None
```

| 参数 | 说明 |
| --- | --- |
| `value` | 目标行程位置（mm 或 deg）；超出范围时按端点夹紧 |
| `vel` | 速度百分比 0–100；`None`=100%，0 使用最小持续速度 |
| `force` | 力上限百分比 0–100；`None`=100%，`-1`=不设上限；仅 POS_FORCE 有效 |
| `block` | `True` 等待到位或接触停止；`False` 下发后立即返回 |
| `timeout` | 阻塞等待超时（秒）；`None` 按距离/速度估算 |
| `position_tolerance` | 到位位置容差（rad）；`None` 用默认值，端点目标自动放宽到 1% 行程 |
| `velocity_tolerance` | 到位速度容差（rad/s） |

返回：

- `block=False`：返回 `None`。
- `block=True`：返回 `MoveResult`，字段见下方。

> 💡 **百分比语义**
> `force=50` 表示“配置力矩上限的 50%”，不是 50 Nm。`vel=50` 同理。端点 `open()`/`close()` 会使用 1% 行程的接触容差，压到机械限位即视为到位。

示例：

```python
g = VTacGripper("<SN>", config_path="./devices.json")
try:
    g.enable()
    result = g.move(40, vel=50, force=40, block=True)
    print(result.reached, result.blocked, result.force_nm)
finally:
    g.disable()
    g.release()
```

### `open()` / `close()`

```python
g.open(**kwargs)
g.close(**kwargs)
```

参数与 `move()` 相同；分别运动到 `g.open_value` / `g.close_value`。

```python
g.enable()
g.open(block=True)
g.close(vel=50, force=50, block=True)
```

### `jog()`

```python
g.jog(vel=None, *, force=None, direction="open") -> None
```

| 参数 | 说明 |
| --- | --- |
| `vel` | 速度百分比 0–100；`None`=100% |
| `force` | 力上限百分比；仅 POS_FORCE 有效 |
| `direction` | `open`/`close`（也接受 `1`/`-1`）；默认 `open` |

点动下发“远目标 + 限速”，需要用 `hold()` 或 `stop()` 停止：

```python
g.jog(30, direction="open")
g.hold()

g.jog(30, direction="close", force=40)
g.stop()
```

### `hold()` / `stop()`

```python
g.hold()
g.stop(*, disable=False)
```

- `hold()`：保持当前位置；POS_FORCE 使用配置力矩上限，POS_VEL 使用最小保持速度。
- `stop()`：默认保持当前位置；`disable=True` 直接失能。

### `move_rad()`（进阶）

```python
g.move_rad(target_rad, **kwargs) -> None
```

直接按电机弧度目标运动，`**kwargs` 透传给底层电机接口（如 `speed`）。除非需要绕过行程映射，否则优先使用 `move()`。

---

## 🎯 标定与示教

### `calibrate()`

```python
g.calibrate(
    *,
    speed=...,
    force_nm=None,
    scan_rad=None,
    min_travel_rad=...,
    min_span_rad=...,
    timeout=None,
    settle_s=...,
    open_direction=None,
    center_zero=True,
    margin_rad=None,
    margin_ratio=None,
    save=True,
) -> dict
```

| 参数 | 说明 |
| --- | --- |
| `speed` | 扫描速度（rad/s，绝对值） |
| `force_nm` | 扫描力上限（Nm）；`None` 使用默认 3.0 Nm |
| `scan_rad` | 单侧最大扫描行程（rad）；`None` 按几何参考行程估算 |
| `min_travel_rad` | 判定边界可信所需的最小位移（rad） |
| `min_span_rad` | 开闭跨度下限（rad） |
| `timeout` | 单侧扫描超时（秒） |
| `settle_s` | 顶住边界后的稳定等待时间（秒） |
| `open_direction` | 张开方向：`positive`/`negative`/`±1`；`None` 按几何预设 |
| `center_zero` | 是否把零点重设到行程中点；默认 `True` |
| `margin_rad` | 显式限位内缩量（rad）；给定后忽略 `margin_ratio` |
| `margin_ratio` | 按实测跨度比例内缩；默认按产品表（通常 1%） |
| `save` | 是否写入配置；默认 `True` |

返回字典包含：

```text
sn, geometry, unit, open_rad, close_rad, span_rad,
force_nm, speed, zero_rad, margin_rad, margin_ratio,
margin_unit, saved
```

> ⚠️ **标定会运动并顶住机械限位**
> 调用前必须已使能、有反馈、夹爪空载且行程无阻挡。常规使用建议通过 CLI `calibrate` 执行，见 [使用指南](./02-usage.md#-标定)。

示例：

```python
g = VTacGripper("<SN>", config_path="./devices.json")
try:
    g.enable()
    result = g.calibrate(force_nm=3.0, save=True)
    print(result["open_rad"], result["close_rad"], result["saved"])
finally:
    g.disable()
    g.release()
```

### `teach_open()` / `teach_close()`

```python
g.teach_open()
g.teach_close()
```

把当前位置记录为张开/闭合限位并写入配置，返回更新后的配置记录。要求有有效反馈，否则抛 `RuntimeError`。

### `set_zero()`

```python
g.set_zero()
```

把当前位置设为电机零点，并清除标定/示教标志。该方法会先失能电机。常规流程请使用 `calibrate()`；不要在未确认机械位置时手动置零。

---

## 🧠 状态、配置与关闭

### `describe()`

```python
g.describe() -> dict
```

返回配置与实时状态合并后的字典，适合日志或 JSON 输出。包含在线状态、控制模式、位置、速度、力矩、错误文本、反馈年龄和行程位置等。

### `register()`

```python
g.register(**overrides)
```

修改并保存当前 SN 的配置字段；`travel`、`control_hz`、`speed_limit_rad_s`、`torque_limit_nm` 会写入 `overrides`，字段名不存在时抛 `AttributeError`。

### `clear_error()`

```python
g.clear_error() -> bool
```

发送清错命令，返回当前是否已无故障。**清错不会自动使能**；清错后需要重新使能：

```python
if g.clear_error():
    g.enable()
```

CLI 的 `teach` 中可直接输入 `r` 完成“清错 + 使能 + 保持”。

### 高级电机接口

以下方法用于寄存器级调试，常规应用不需要：

```python
g.read_register(register, *, timeout=0.3)
g.write_register(register, value, *, timeout=0.3)
g.save_flash(*, timeout=1.0)
```

---

## 📦 返回对象

### `MoveResult`

`move(block=True)` 的返回：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `reached` | `bool` | 是否在容差内到达目标 |
| `blocked` | `bool` | 是否因接触/阻挡停止 |
| `force_nm` | `float` | 返回时的反馈力矩绝对值（Nm） |

### `MotorState`

`g.state` 返回的最新反馈快照：

| 字段 | 说明 |
| --- | --- |
| `pos` | 输出轴位置（rad） |
| `vel` | 输出轴速度（rad/s） |
| `tau` | 输出轴力矩（Nm） |
| `t_mos` | MOS 温度（°C） |
| `t_rotor` | 线圈温度（°C） |
| `err` | 固件状态码（`0x0`–`0xE`） |
| `seq` | 反馈帧计数 |
| `last_update` | 最近反馈时间戳（`time.monotonic()`） |
| `interval` | 与上一帧的间隔（秒） |
| `age` | 距最近反馈的秒数（属性） |
| `error` | 状态码中文文本（属性） |
| `faulted` | 是否为保护故障（属性） |

---

## ⚠️ 异常

| 异常 | 何时出现 |
| --- | --- |
| `MotorFaultError` | 电机固件保护锁存；带 `err`、`can_id`、`sn` |
| `MotorModeError` | 接口与当前控制模式不匹配，或模式未读回确认 |
| `TimeoutError` | 运动等待、寄存器读写或模式切换超时 |
| `RuntimeError` | 无适配器、配置缺失、未标定、无反馈、运动受阻等 |
| `ValueError` | 参数非法（百分比、方向、速度等） |

完整的用户可见报错、电机状态码和恢复步骤见 [错误码与异常](./04-errors.md)。
