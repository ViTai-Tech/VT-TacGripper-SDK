"""夹爪运动时同步打印两颗视触觉传感器的滑移状态。

需要额外安装 ViTai 视触觉传感器 SDK（pyvitaisdk）：
https://github.com/ViTai-Tech/ViTai-SDK-Release

两颗传感器放在一个工作线程里循环采集（collect_sensor_data 在无新数据时会
阻塞，约 30 Hz）；主线程只负责夹爪开合，因此不会阻塞电机指令流。
"""

from __future__ import annotations

import argparse
import threading
import time

from VT_TacGripper import VTacGripper

SLIP_LABELS = {
    "NO_OBJ": "无物体",
    "CONTACT": "接触",
    "INCIPIENT_SLIP": "初期滑移",
    "PARTIAL_SLIP": "部分滑移",
    "COMPLETE_SLIP": "完全滑移",
    "STEADY_HOLD": "稳定夹持",
}


def slip_text(state) -> str:
    """把 VTSlipState 转成简短中文。"""
    return SLIP_LABELS.get(getattr(state, "name", ""), str(state))


def sensor_loop(sensors, sns, data_type, error_type, gripper, stop) -> None:
    """单线程轮询两颗传感器；状态变化或每 1 秒打印一行。"""
    last = {}
    last_print = 0.0
    started = time.monotonic()
    while not stop.is_set():
        values = {}
        changed = False
        try:
            for sn, sensor in zip(sns, sensors):
                data = sensor.collect_sensor_data(data_type.SLIP_STATE)
                state = data[data_type.SLIP_STATE]
                values[sn] = state
                if last.get(sn) != state:
                    changed = True
        except error_type as exc:
            print(f"传感器采集失败：{exc}；建议：{getattr(exc, 'suggestion', '-')}", flush=True)
            stop.set()
            return
        now = time.monotonic()
        if values and (changed or now - last_print >= 1.0):
            try:
                position = f"{gripper.position:+.2f}{gripper.unit}"
            except Exception:
                position = "?"
            parts = "  ".join(
                f"S{i + 1}={slip_text(values[sn])}" for i, sn in enumerate(sns) if sn in values
            )
            print(f"[{now - started:7.2f}s] pos={position}  {parts}", flush=True)
            last = values
            last_print = now
        time.sleep(0.001)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="夹爪运动 + 视触觉滑移状态示例。")
    parser.add_argument("--sn", default=None, help="夹爪适配器 SN；单适配器可省略。")
    parser.add_argument("--config", default=None, help="一机一码配置路径。")
    parser.add_argument("--vel", type=float, default=50.0, help="速度百分比 0–100。")
    parser.add_argument("--force", type=float, default=50.0, help="力上限百分比 0–100。")
    parser.add_argument("--loops", type=int, default=50, help="开合循环次数，默认 50。")
    parser.add_argument("--hold", type=float, default=0.2, help="两端停留秒数。")
    args = parser.parse_args(argv)

    try:
        from pyvitaisdk import VTSDataType, VTSDeviceFinder, VTSError, VTSensor
    except ImportError:
        print("需要额外安装 ViTai 视触觉传感器 SDK pyvitaisdk：")
        print("  https://github.com/ViTai-Tech/ViTai-SDK-Release")
        print("请从该仓库 Releases 下载对应 wheel 安装后重试。")
        return 2

    try:
        finder = VTSDeviceFinder()
        sns = list(finder.get_sns())[:2]
    except VTSError as exc:
        print(f"视触觉传感器初始化失败：{exc}；建议：{getattr(exc, 'suggestion', '-')}")
        return 1
    if not sns:
        print("未发现视触觉传感器。")
        return 1

    try:
        gripper = VTacGripper(args.sn, config_path=args.config)
    except Exception as exc:  # noqa: BLE001
        print(f"创建夹爪失败：{exc}")
        return 1

    sensors = []
    stop = threading.Event()
    thread = None
    try:
        gripper.enable(hold=True)
        for sn in sns:
            sensor = VTSensor(config=finder.get_device_by_sn(sn))
            sensor.calibrate()
            sensors.append(sensor)
        print("传感器：" + "  ".join(f"S{i + 1}={sn}" for i, sn in enumerate(sns)))
        print(f"开始 {args.loops} 次开合；按 Ctrl-C 退出。")

        thread = threading.Thread(
            target=sensor_loop,
            args=(sensors, sns, VTSDataType, VTSError, gripper, stop),
            daemon=True,
        )
        thread.start()

        for _ in range(max(1, args.loops)):
            if stop.is_set():
                break
            gripper.open(vel=args.vel, force=args.force, block=True)
            time.sleep(max(0.0, args.hold))
            if stop.is_set():
                break
            gripper.close(vel=args.vel, force=args.force, block=True)
            time.sleep(max(0.0, args.hold))
        return 0
    except KeyboardInterrupt:
        print("\n已中断。")
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"运行失败：{exc}")
        return 1
    finally:
        stop.set()
        if thread is not None:
            thread.join(timeout=1.0)
        for sensor in sensors:
            try:
                sensor.release()
            except Exception:
                pass
        try:
            gripper.disable()
        except Exception:
            pass
        gripper.release()


if __name__ == "__main__":
    raise SystemExit(main())
