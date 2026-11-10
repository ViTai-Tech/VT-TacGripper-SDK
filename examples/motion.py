"""创建夹爪实例并执行运动控制。

``--vel``/``--force`` 为 0–100 百分比；``force`` 仅 POS_FORCE 模式有效。
"""

from __future__ import annotations

import argparse

from VT_TacGripper import VTacGripper


def main() -> int:
    parser = argparse.ArgumentParser(description="夹爪运动控制示例。")
    parser.add_argument("--sn", default=None, help="适配器 SN；单适配器可省略。")
    parser.add_argument("--config", default=None, help="配置文件路径（默认 ~/.config/vitai-sdk/devices.json）。")
    parser.add_argument("--action", choices=("open", "close", "move", "cycle"), default="cycle", help="动作。")
    parser.add_argument("--value", type=float, help="move 目标行程（mm 或 deg）。")
    parser.add_argument("--vel", type=float, default=100.0, help="速度百分比 0–100。")
    parser.add_argument("--force", type=float, default=100.0, help="力上限百分比 0–100（POS_FORCE）。")
    parser.add_argument("--loops", type=int, default=3, help="cycle 轮数。")
    args = parser.parse_args()

    try:
        gripper = VTacGripper(args.sn, config_path=args.config)
    except Exception as exc:  # noqa: BLE001
        print(f"创建夹爪失败：{exc}")
        return 1
    try:
        gripper.enable(hold=True)
        kwargs = {"vel": args.vel, "force": args.force, "block": True}
        if args.action == "open":
            gripper.open(**kwargs)
        elif args.action == "close":
            gripper.close(**kwargs)
        elif args.action == "move":
            if args.value is None:
                print("move 动作需要 --value。")
                return 2
            gripper.move(args.value, **kwargs)
        else:
            for _ in range(max(1, args.loops)):
                gripper.open(**kwargs)
                gripper.close(**kwargs)
        print(f"完成：位置={gripper.position:+.2f}{gripper.unit}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"运动失败：{exc}")
        return 1
    finally:
        try:
            gripper.disable()
        except Exception:
            pass
        gripper.release()


if __name__ == "__main__":
    raise SystemExit(main())
