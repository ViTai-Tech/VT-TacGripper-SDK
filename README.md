# VT-TacGripper-SDK

[English](README_EN.md) | 简体中文

VT-TacGripper（VT 视触觉夹爪）的 Python SDK。自带厂商运行库（含
`libusb`/`libstdc++`），**零 pip 依赖**，wheel 安装后即可枚举适配器、配置电机、
标定夹爪并读写寄存器。

## 支持环境

| 项目 | 支持范围 |
|---|---|
| Python | 3.10 / 3.12 |
| 系统 | Linux x86_64（Ubuntu 22.04 实测） |
| 适配器 | USB2CANFD |
| 夹爪 | VT-TacGripper-85-S / VT-TacGripper-85-L / VT-TacGripper-Slim |

## 安装

从 [Releases](../../releases) 下载与 Python 版本匹配的 wheel：

- Python 3.10：`vt_tacgripper_sdk-1.0.0-cp310-cp310-linux_x86_64.whl`
- Python 3.12：`vt_tacgripper_sdk-1.0.0-cp312-cp312-linux_x86_64.whl`

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install ./vt_tacgripper_sdk-1.0.0-cp310-cp310-linux_x86_64.whl
```

## 快速开始

```python
from VT_TacGripper import VTacGripper

gripper = VTacGripper("<适配器 SN>")
try:
    gripper.open(block=True)
    gripper.close(block=True)
finally:
    gripper.shutdown()
```

首次使用需要先配置电机通信并标定；详见下面的工具说明。

## 命令行工具

```bash
# 枚举 USB2CANFD 适配器
python -m VT_TacGripper.tools.list_devices

# 新电机首次配置（默认目标：CAN ID 0x01 / Master 0x11 / MIT / 5 Mbps）
python -m VT_TacGripper.tools.configure_motor --sn <SN> --check
python -m VT_TacGripper.tools.configure_motor --sn <SN>   # 回车默认确认写入

# 自动标定开闭限位（默认重设零点、1% 安全边距、3.0 Nm 扫描力）
python -m VT_TacGripper.tools.calibrate --sn <SN> --config ./devices.json

# 同步开合演示；--blocking 为阻塞并发模式
python -m VT_TacGripper.tools.demo --config ./devices.json --blocking

# 诊断 / 实时监视 / 手动示教
python -m VT_TacGripper.tools.diagnose --sn <SN>
python -m VT_TacGripper.tools.monitor --sn <SN>
python -m VT_TacGripper.tools.teach --sn <SN> --config ./devices.json
```

## 示例

`examples/` 目录：

| 文件 | 说明 |
|---|---|
| `config_edit.py` | 预览/修改一机一码配置映射 |
| `check_devices.py` | 枚举适配器，检查夹爪配置与运行状态 |
| `motion.py` | 创建夹爪实例执行开/合/移动/循环 |

先安装上面的 wheel，并把 `--config` 指向你的 `devices.json`：

```bash
python examples/check_devices.py --config ./devices.json
python examples/config_edit.py --sn <SN> --config ./devices.json
python examples/motion.py --sn <SN> --config ./devices.json --action cycle
```

## 配置与权限

- 一机一码配置默认在 `~/.config/vitai-sdk/devices.json`，也可用
  `--config` 或环境变量 `VITAI_SDK_CONFIG` 指定；旧默认路径不会自动迁移，请用 `--config` 指向已有 `devices.json`。
- Linux 下若设备节点权限不足：

```bash
python -m VT_TacGripper.tools.install_udev --status
sudo -E python -m VT_TacGripper.tools.install_udev --install
```

## 已知限制

- 厂商 v1.1.0 运行库的 `dmcan_device_close` 在电机使用后可能崩溃；SDK 关闭适配器
  时只停通道/解绑回调，不调用该接口。因此**同一进程内 `close()` 后不能再次打开
  同一适配器**，需要重启进程；电机使能与运动不受影响。
- 本页 wheel 为 Linux x86_64；其他平台需单独构建。

## 反馈

欢迎在 GitHub Issues 反馈问题；请附上系统版本、Python 版本、适配器 SN 与复现步骤。
