#!/usr/bin/env python3
"""把 CDN 的菱形职阶图标做成「透明底」版本。

原图是菱形 + 深色内底 + 金框 → 出图时深色内底会挡住头像。
这里把内部「暗且低饱和」的像素挖成透明，只留金框与职阶纹章。

用法：python3 class_icon_transparent.py [--dir ~/fgo-wiki/assets/ui/classes] [--test]
"""

import argparse
import os
import urllib.request

import numpy as np
from PIL import Image

SRC = "https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main/fgo/classes/{key}_{tier}.png"
KEYS = ["saber", "archer", "lancer", "rider", "caster", "assassin", "berserker",
        "shielder", "ruler", "avenger", "alterego", "mooncancer", "foreigner",
        "pretender", "beast", "beastii", "beasti", "beastiiir", "beastiiil", "beastiv",
        "mooncancer", "grandcaster", "unknown"]
TIERS = ["gold", "silver", "bronze"]
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def fetch(key, tier):
    req = urllib.request.Request(SRC.format(key=key, tier=tier),
                                headers={"User-Agent": "Mozilla/5.0"})
    with OPENER.open(req, timeout=30) as r:
        return r.read()


def keyout(im, tol=52):
    """从菱形内部几个种子点泛洪，把内底色挖透明，纹章与金框保持不动。"""
    arr = np.array(im.convert("RGBA")).astype(np.int16)
    h, w = arr.shape[:2]
    rgb = arr[..., :3]
    alpha = arr[..., 3]
    seen = np.zeros((h, w), bool)
    stack = []
    for fx, fy in ((0.26, 0.5), (0.74, 0.5), (0.5, 0.28), (0.5, 0.72), (0.32, 0.32)):
        x, y = int(w * fx), int(h * fy)
        if alpha[y, x] > 60:
            stack.append((x, y))
    holes = []
    while stack:
        x, y = stack.pop()
        if not (0 <= x < w and 0 <= y < h) or seen[y, x]:
            continue
        seen[y, x] = True
        if alpha[y, x] < 60:
            continue
        # 种子色：取队列里第一颗的颜色不现实，改用与邻居比较的局部扩散
        holes.append((x, y))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not seen[ny, nx]:
                if abs(int(rgb[ny, nx, 0]) - int(rgb[y, x, 0])) <= tol and \
                   abs(int(rgb[ny, nx, 1]) - int(rgb[y, x, 1])) <= tol and \
                   abs(int(rgb[ny, nx, 2]) - int(rgb[y, x, 2])) <= tol:
                    stack.append((nx, ny))
    for x, y in holes:
        alpha[y, x] = 0
    arr[..., 3] = alpha
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.expanduser("~/fgo-wiki/assets/ui/classes"))
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.dir, exist_ok=True)
    made = 0
    for k in dict.fromkeys(KEYS):
        for t in TIERS:
            fp = os.path.join(a.dir, f"{k}_{t}.png")
            if os.path.exists(fp):
                continue
            try:
                raw = fetch(k, t)
            except Exception:
                continue
            im = Image.open(__import__("io").BytesIO(raw))
            keyout(im).save(fp)
            made += 1
            print("ok", f"{k}_{t}")
    print("made", made)


if __name__ == "__main__":
    main()
