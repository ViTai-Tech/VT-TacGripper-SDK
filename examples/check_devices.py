"""枚举适配器，并检查对应夹爪的配置与运行状态。"""

from __future__ import annotations

import argparse

from VT_TacGripper import ConfigStore, VTacGripper, list_devices


def main() -> int:
    parser = argparse.ArgumentParser(description="枚举适配器并检查夹爪状态。")
    parser.add_argument("--config", default=None, help="配置文件路径（默认 ~/.config/vitai-sdk/devices.json）。")
    args = parser.parse_args()

    store = ConfigStore(args.config) if args.config else ConfigStore()
    records = store.load()
    devices = list_devices()
    if not devices:
        print("未发现 USB2CANFD 适配器。")
        return 1

    connected = set()
    for adapter in devices:
        connected.add(adapter.sn)
        record = records.get(adapter.sn)
        if record is None:
            print(f"[{adapter.sn}] {adapter.type_name}：没有夹爪配置")
            continue

        print(
            f"[{adapter.sn}] {adapter.type_name}：型号={record.product_model or '-'} "
            f"已标定={record.calibrated}"
        )
        try:
            # 创建实例只打开设备；显式 enable 读取实时状态，结束后 disable。
            with VTacGripper(adapter.sn, store=store) as gripper:
                try:
                    gripper.enable(hold=True)
                    info = gripper.describe()
                    position = info.get("unit_position")
                    firmware = info.get("error")
                    if firmware in ("失能", "使能"):
                        firmware = "正常"
                    print(
                        f"  在线={info.get('online')}  使能={gripper.enabled}  "
                        f"位置={position}  力矩={info.get('torque_nm'):+.3f} Nm  "
                        f"固件状态={firmware}"
                    )
                finally:
                    try:
                        gripper.disable()
                    except Exception:
                        pass
        except Exception as exc:  # noqa: BLE001
            print(f"  状态读取失败：{exc}")

    missing = sorted(set(records) - connected)
    if missing:
        print("配置存在但未连接的夹爪：")
        for sn in missing:
            print(f"  {sn}  型号={records[sn].product_model or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
