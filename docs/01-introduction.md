# 🦾 SDK 介绍

**VT-TacGripper SDK** 是 VT 视触觉夹爪的 Python 控制 SDK。它通过 USB2CANFD 适配器连接夹爪电机，完成从设备发现、通信配置、夹爪标定到位置/力控运动的全过程。

> **适用版本**：1.2.0
> **运行平台**：Linux x86_64（Ubuntu 22.04 实测）
> **Python**：3.10 / 3.12

---

## 🚀 核心能力

| 能力 | 说明 |
| --- | --- |
| 🎛️ **位置与力控** | POS_FORCE 下按行程位置运动，同时设置力上限；POS_VEL 下按位置-速度运动 |
| 🎯 **自动标定** | 自动扫描开闭机械限位，写入行程映射，并可把零点重设到行程中点 |
| 🕹️ **手动示教** | 通过 `teach` 点动到边界，记录张开/闭合限位 |
| 📊 **状态反馈** | 读取位置、速度、力矩、温度、固件状态与反馈时延 |
| 🧩 **零 pip 依赖** | wheel 自带运行库，安装后即可使用 |
| 🗂️ **一机一码** | 按适配器 SN 保存夹爪型号、行程、限位和标定数据 |
| 🔌 **多适配器** | 同一进程可管理多台适配器与夹爪 |
| 🛡️ **安全边界** | 标定限位默认向内收缩 1% 行程，避免常规动作顶死机械限位 |

---

## 🧩 系统组成

```text
应用代码 / teach / demo
        │
        ▼
VT-TacGripper SDK（Python）
        │
        ▼
USB2CANFD 适配器
        │  CAN / FDCAN
        ▼
夹爪电机 + 夹爪机构
```

| 层级 | 作用 |
| --- | --- |
| **应用层** | 调用 `VTacGripper` 的 `open()`、`close()`、`move()`、`jog()` 等方法 |
| **SDK 层** | 配置管理、行程映射、标定、运动指令、反馈解析、故障检测 |
| **适配器层** | USB2CANFD 设备枚举与 CAN/FDCAN 收发 |
| **执行层** | 电机驱动夹爪开合，反馈位置、速度、力矩和状态码 |

---

## 🖥️ 支持环境

| 项目 | 支持范围 |
| --- | --- |
| Python | 3.10、3.12 |
| 操作系统 | Linux x86_64；Ubuntu 22.04 实测 |
| 适配器 | USB2CANFD |
| 夹爪 | VT-TacGripper-85-S、VT-TacGripper-85-L、VT-TacGripper-Slim |
| 运行依赖 | 无额外 pip 运行依赖；运行库随 wheel 提供 |
| 分发格式 | Linux x86_64 wheel（cp310 / cp312） |

> ⚠️ **平台限制**
> 当前 1.2.0 wheel 仅支持 Linux x86_64。Windows、macOS、ARM64 暂不提供预编译 wheel。

---

## 📦 安装包内容

| 内容 | 说明 |
| --- | --- |
| `VT_TacGripper` | SDK 主包，核心模块以编译扩展形式提供 |
| `VT_TacGripper.tools` | `list_devices`、`configure_motor`、`calibrate`、`teach`、`diagnose`、`demo`、`install_udev` |
| `examples/` | 设备检查、配置编辑、运动控制和滑移状态示例 |
| `dist/` | 本地构建的 wheel 与校验文件（正式发布后同步到 Releases） |

`examples/motion_slip.py` 额外使用 ViTai 视触觉传感器 SDK `pyvitaisdk`。该 SDK 不在本仓库 wheel 内，需要从 [ViTai-SDK-Release](https://github.com/ViTai-Tech/ViTai-SDK-Release) 单独安装。

---

## 🔄 首次使用流程

1. **安装 wheel**：选择与 Python 版本匹配的 cp310/cp312 wheel。
2. **配置设备权限**：安装 udev 规则，确保非 root 用户可访问适配器。
3. **发现设备**：运行 `list_devices`，确认适配器 SN。
4. **首次配置**：新电机或通信参数不一致时，运行 `configure_motor`；一致则零写入，有差异直接写入。
5. **标定夹爪**：运行 `calibrate`，或使用 `teach` 手动示教。
6. **验证动作**：用 `teach` 或 Python 代码执行一次完整开合。

详细命令见 [使用指南](./02-usage.md)。

---

## 🗂️ 配置方式

- 默认配置路径：`~/.config/vitai-sdk/devices.json`
- 可用 `--config` 或环境变量 `VITAI_SDK_CONFIG` 指定其他路径。
- 配置按适配器 SN 保存，一台夹爪一条记录。
- 默认只保存 `product_model`、`open_rad`/`close_rad`；只有显式修改的 `travel`、`control_hz`、速度/力限才写入 `overrides`。
- `geometry`/`motor_type`/CAN ID/波特率由产品型号和代码推导，不落盘。
- 旧版完整配置会自动迁移；无 `product_model` 的旧记录需要重新指定产品型号。
- 标定、示教和 `register()` 会更新对应 SN 的记录。

---

## ⚠️ 已知限制

- **仅 Linux x86_64**：当前 wheel 不支持 Windows、macOS 或 ARM64。
- **关闭后不能在同一进程重新打开同一适配器**：厂商运行库的关闭路径存在已知崩溃风险，SDK 关闭时只停止通道并解绑回调。需要重新打开时请重启进程。
- **同一适配器不能同时被两个进程占用**：不要同时运行 `teach`、`demo` 和其他控制程序。
- **构造默认不使能**：`VTacGripper` 构造只完成初始化；需要运动时调用 `enable()`。`release()` 不改变使能状态，需要失能时显式调用 `disable()`。
- **teach 退出默认保持使能**：`teach` 退出时不会自动失能；需要退出失能请加 `--disable-on-exit`，或在交互中输入 `d`。
- **85-S/Slim 需人工选择产品型号**：两者都是 DM3507，无法从电机寄存器区分；必须按机构选择 `product_model`，标定跨度检查会拦截明显错误。
- **POS_VEL 没有力参数**：该模式下 `force` 会被忽略并给出警告；需要力上限时使用 POS_FORCE。
- **反馈存在突发延迟**：反馈平均速率正常，但应用层可能看到 0–300 ms 的到达间隔；判断状态时以 `age` 和最新快照为准。
- **温度/实时状态需要使能**：`t_mos`、`t_rotor`、位置、速度、力矩来自反馈帧；未使能时无实时数据。诊断时用 `diagnose --enable`（诊断结束后自动失能）。
- **标定会产生机械受力**：标定会让夹爪在两端限位处短时顶住，必须空载、无阻挡并确保机构牢固。
- **默认标定力为 3.0 Nm**：软胶夹头或软工件场景不要随意降低，否则可能无法进入力限区；正式标定前可先用 `--dry-run` 检查。
