"""预览或修改一机一码配置中的行程映射。

映射关系：0（张开）~ travel（闭合）↔ open_rad ~ close_rad。
"""

from __future__ import annotations

import argparse

from VT_TacGripper import ConfigStore
from VT_TacGripper.config import truncate_boundary


def main() -> int:
    parser = argparse.ArgumentParser(description="预览/修改夹爪配置映射。")
    parser.add_argument("--sn", required=True, help="适配器 SN。")
    parser.add_argument("--config", default=None, help="配置文件路径（默认 ~/.config/vitai-sdk/devices.json）。")
    parser.add_argument("--open-rad", type=float, help="张开限位（rad）。")
    parser.add_argument("--close-rad", type=float, help="闭合限位（rad）。")
    parser.add_argument("--travel", type=float, help="额定行程（mm 或 deg）。")
    parser.add_argument("--apply", action="store_true", help="写入配置；不加只预览。")
    args = parser.parse_args()

    store = ConfigStore(args.config) if args.config else ConfigStore()
    record = store.get(args.sn)
    if record is None:
        print(f"配置中不存在 SN={args.sn.strip().upper()}")
        return 1

    print(f"SN={record.sn}  型号={record.product_model or '-'}  单位={record.unit or '-'}")
    print(f"当前：open_rad={record.open_rad}  close_rad={record.close_rad}  travel={record.travel}")

    changed = False
    if args.open_rad is not None:
        record.open_rad = truncate_boundary(args.open_rad)
        changed = True
    if args.close_rad is not None:
        record.close_rad = truncate_boundary(args.close_rad)
        changed = True
    if args.travel is not None:
        record.travel = args.travel
        changed = True

    if not changed:
        print("未指定修改项。")
        return 0
    print(f"修改后：open_rad={record.open_rad}  close_rad={record.close_rad}  travel={record.travel}")
    if not args.apply:
        print("仅预览；加 --apply 写入。")
        return 0
    store.upsert(record)
    print(f"已写入：{store.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
