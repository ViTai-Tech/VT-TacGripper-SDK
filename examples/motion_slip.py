"""张开夹爪，标定视触觉传感器，闭合到接触并观察滑移状态。

需要额外安装 ViTai 视触觉传感器 SDK（pyvitaisdk）：
https://github.com/ViTai-Tech/ViTai-SDK-Release

流程：
1. 张开夹爪；
2. 在无接触状态标定两颗传感器；
3. 启动单线程滑移检测；
4. 缓慢闭合，直到接触物体（或到达闭合限位）；
5. 在接触位置保持并持续打印滑移状态；
6. 张开释放，按 --loops 重复。

运行中按 Ctrl-C 退出：会停止采集、张开释放、失能并释放资源。
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


def sensor_loop(sensors, sns, data_type, gripper, stop, sensor_error) -> None:
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
        except Exception as exc:
            print(f"传感器采集失败：{exc}；建议：{getattr(exc, 'suggestion', '-')}", flush=True)
            sensor_error.set()
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
    parser = argparse.ArgumentParser(description="夹爪接触夹持 + 视触觉滑移状态示例。")
    parser.add_argument("--sn", default=None, help="夹爪适配器 SN；单适配器可省略。")
    parser.add_argument("--config", default=None, help="一机一码配置路径。")
    parser.add_argument("--vel", type=float, default=30.0, help="闭合速度百分比 0–100。")
    parser.add_argument("--force", type=float, default=30.0, help="夹持力上限百分比 0–100。")
    parser.add_argument("--loops", type=int, default=1, help="夹持轮数，默认 1。")
    parser.add_argument("--hold", type=float, default=2.0, help="接触后保持观察秒数，默认 2。")
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

    gripper = None
    sensors = []
    stop = threading.Event()
    sensor_error = threading.Event()
    thread = None
    code = 0
    try:
        gripper = VTacGripper(args.sn, config_path=args.config)
        gripper.enable(hold=True)
        gripper.open(vel=args.vel, force=args.force, block=True)
        time.sleep(0.2)

        for sn in sns:
            sensor = VTSensor(config=finder.get_device_by_sn(sn))
            sensor.calibrate()
            sensors.append(sensor)

        print("传感器：" + "  ".join(f"S{i + 1}={sn}" for i, sn in enumerate(sns)))
        print(f"开始 {max(1, args.loops)} 轮夹持；接触后保持 {args.hold:g}s；按 Ctrl-C 退出。")

        thread = threading.Thread(
            target=sensor_loop,
            args=(sensors, sns, VTSDataType, gripper, stop, sensor_error),
            daemon=True,
        )
        thread.start()

        for _ in range(max(1, args.loops)):
            if stop.is_set():
                break
            result = gripper.move(
                gripper.close_value, vel=args.vel, force=args.force, block=True
            )
            if result is not None and result.blocked:
                print(f"检测到物体：夹持力约 {result.force_nm:.2f} Nm，保持观察。", flush=True)
                hold_pos = gripper.position
                gripper.move(hold_pos, vel=args.vel, force=args.force, block=False)
                deadline = time.monotonic() + max(0.0, args.hold)
                while not stop.is_set() and time.monotonic() < deadline:
                    time.sleep(0.01)
            else:
                print("未检测到物体（已到达闭合限位），张开。", flush=True)
            if stop.is_set():
                break
            gripper.open(vel=args.vel, force=args.force, block=True)

        if sensor_error.is_set():
            code = 1
    except KeyboardInterrupt:
        print("\n已中断。", flush=True)
        code = 130
    except Exception as exc:  # noqa: BLE001
        print(f"运行失败：{exc}", flush=True)
        code = 1
    finally:
        stop.set()
        if thread is not None:
            thread.join(timeout=3.0)
        thread_alive = thread is not None and thread.is_alive()
        if thread_alive:
            print("采集线程未停止；跳过传感器释放，直接退出。", flush=True)

        # Demo 退出时释放物体；如果线程仍卡在采集，也只做 gripper 侧清理。
        if gripper is not None:
            try:
                gripper.open(vel=args.vel, force=args.force, block=True)
            except Exception:
                pass
            if not thread_alive:
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

    return code


if __name__ == "__main__":
    from VT_TacGripper.tools._exit import run_main

    run_main(main)
