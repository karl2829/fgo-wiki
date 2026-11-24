"""立绘随机选择：从 assets/art/ 里随机取一张（4 张再临立绘 + 1 张灵衣），
复制为 assets/art_current.png 供模板引用。

用法：
  python pick_art.py                # 随机
  python pick_art.py --art asc2     # 指定
  python pick_art.py --list         # 看池子里有什么
"""
from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POOL = ROOT / "assets" / "art"
TARGET = ROOT / "assets" / "art_current.png"


def list_arts() -> list[Path]:
    if not POOL.is_dir():
        return []
    return sorted(p for p in POOL.glob("*.png") if p.is_file())


def pick(name: str | None, seed: int | None) -> Path:
    arts = list_arts()
    if not arts:
        sys.exit(f"立绘目录为空：{POOL}")
    if name:
        hit = [p for p in arts if p.stem == name]
        if not hit:
            sys.exit(f"没有这张立绘：{name}（可选：{', '.join(p.stem for p in arts)}）")
        return hit[0]
    rng = random.Random(seed)
    return rng.choice(arts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--art", help="指定立绘名（asc1..asc4 / costume）")
    ap.add_argument("--seed", type=int, help="固定随机种子，便于复现")
    ap.add_argument("--list", action="store_true", help="列出可选立绘")
    args = ap.parse_args()

    if args.list:
        for p in list_arts():
            print(p.stem)
        return

    chosen = pick(args.art, args.seed)
    shutil.copyfile(chosen, TARGET)
    print(f"art: {chosen.stem} -> {TARGET.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
