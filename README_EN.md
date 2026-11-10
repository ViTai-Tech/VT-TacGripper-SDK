# VT-TacGripper-SDK

English | [简体中文](README.md)

Python SDK for VT-TacGripper. The wheel bundles the vendor runtime
(`libusb`/`libstdc++` included); there are **no pip runtime dependencies**. It lets
you enumerate adapters, configure motors, calibrate grippers, and access
registers.

📖 **User manual (Chinese)**: [Introduction](docs/01-introduction.md) · [Usage](docs/02-usage.md) · [API](docs/03-api.md) · [Errors](docs/04-errors.md)

## Requirements

| Item | Supported |
|---|---|
| Python | 3.10 / 3.12 |
| OS | Linux x86_64 (tested on Ubuntu 22.04) |
| Adapter | USB2CANFD |
| Gripper | VT-TacGripper-85-S / VT-TacGripper-85-L / VT-TacGripper-Slim |

## Installation

Download the wheel matching your Python version from
[Releases](https://github.com/ViTai-Tech/VT-TacGripper-SDK/releases):

- Python 3.10: `vt_tacgripper_sdk-1.2.0-cp310-cp310-linux_x86_64.whl`
- Python 3.12: `vt_tacgripper_sdk-1.2.0-cp312-cp312-linux_x86_64.whl`

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install ./vt_tacgripper_sdk-1.2.0-cp310-cp310-linux_x86_64.whl
```

## Quick start

```python
from VT_TacGripper import VTacGripper

gripper = VTacGripper("<adapter SN>")
try:
    gripper.enable()  # constructor does not enable; enable before motion
    gripper.open(block=True)
    gripper.close(block=True)
finally:
    gripper.disable()  # omit to keep the motor enabled
    gripper.release()
```

For first-time use, configure the motor communication and calibrate the
gripper first (see below). `release()` does not change the enabled state;
call `disable()` explicitly when needed.

## Command-line tools

```bash
# List USB2CANFD adapters
python -m VT_TacGripper.tools.list_devices

# Configure a new motor (default: CAN ID 0x01 / Master 0x11 / MIT / 5 Mbps)
python -m VT_TacGripper.tools.configure_motor --sn <SN>   # compare; write only on differences

# Calibrate both travel limits (re-center zero, 1% margin, 3.0 Nm scan force)
python -m VT_TacGripper.tools.calibrate --sn <SN> --product-model VT-TacGripper-85-S --config ./devices.json

# Synchronized open/close demo; --blocking for concurrent blocking moves
python -m VT_TacGripper.tools.demo --config ./devices.json --blocking

# Diagnostics / manual teach
python -m VT_TacGripper.tools.diagnose --sn <SN>
python -m VT_TacGripper.tools.teach --sn <SN> --config ./devices.json
```

## Examples

The `examples/` directory contains:

| File | Purpose |
|---|---|
| `config_edit.py` | Preview/edit the per-device mapping |
| `check_devices.py` | Enumerate adapters and check gripper configuration/status |
| `motion.py` | Instantiate a gripper and open/close/move/cycle |
| `motion_slip.py` | Gripper motion + two-channel visuotactile slip states (requires pyvitaisdk) |

Install the wheel above first, and point `--config` at your `devices.json`:

```bash
python examples/check_devices.py --config ./devices.json
python examples/config_edit.py --sn <SN> --config ./devices.json
python examples/motion.py --sn <SN> --config ./devices.json --action cycle
python examples/motion_slip.py --sn <SN> --config ./devices.json
```

`motion_slip` requires the ViTai visuotactile sensor SDK `pyvitaisdk` (not bundled in this wheel):
https://github.com/ViTai-Tech/ViTai-SDK-Release
Download the matching wheel from its Releases and install it first.

## Configuration and permissions

- The per-device configuration defaults to `~/.config/vitai-sdk/devices.json`.
  Override it with `--config` or the `VITAI_SDK_CONFIG` environment variable;
  the old default path is not migrated automatically; point `--config` at your existing `devices.json`.
- If USB device permissions are missing on Linux:

```bash
python -m VT_TacGripper.tools.install_udev --status
sudo -E python -m VT_TacGripper.tools.install_udev --install
```

## Known limitations

- The vendor v1.1.0 runtime may crash in `dmcan_device_close` after motors have
  been used. The SDK therefore stops channels and unhooks callbacks without
  calling that vendor function. As a result, **an adapter cannot be reopened in
  the same process after `close()`**; start a new process instead. Motor
  enable/motion are unaffected.
- The wheels on this page target Linux x86_64. Other platforms require separate
  builds.

## Feedback

Please open a GitHub Issue with your OS, Python version, adapter SN, and
reproduction steps.
