#!/usr/bin/env python3
"""探测 Atlas 静态站能否按「bundle 路径 + 精灵名」直取 FGO 官方解包图。

用法：
    python3 probe_atlas_assets.py --seed                 # 跑内置候选清单
    python3 probe_atlas_assets.py --file cand.txt        # 每行一个相对路径，如 Terminal/Info/CommonUIAtlas/icon_nplv.png
    python3 probe_atlas_assets.py --seed --download      # 命中即下载到 ~/fgo-wiki/assets/ui/atlas/
    python3 probe_atlas_assets.py --seed --region JP

产出：
    ~/fgo-wiki/assets/ui/atlas/index.json   已确认可取的路径（含尺寸/大小/来源）
    ~/fgo-wiki/assets/ui/atlas/<路径>.png    --download 时落地
"""

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "https://static.atlasacademy.io/{region}/"
OUT = Path.home() / "fgo-wiki/assets/ui/atlas"
INDEX = OUT / "index.json"
_open = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 绕开本机 mihomo
UA = {"User-Agent": "mila-probe/1.0"}

# 已知可取（2026-11 实测）：bundle 路径 + '/' + 精灵名 + '.png'
SEED = [
    "Terminal/Info/CommonUIAtlas/icon_nplv.png",
    "Terminal/Info/CommonUIAtlas/icon_class.png",
    "Terminal/Info/CommonUIAtlas/icon_item.png",
    "Terminal/Info/CommonUIAtlas/icon_skill.png",
    "Terminal/Info/CommonUIAtlas/icon_lock.png",
    "Terminal/Info/CommonUIAtlas/icon_arrow.png",
    "Terminal/Info/CommonUIAtlas/frame.png",
    "Terminal/Info/CommonUIAtlas/frame_01.png",
    "Terminal/Info/CommonUIAtlas/btn.png",
    "Terminal/Info/CommonUIAtlas/bg.png",
    "Terminal/Info/CommonUIAtlas/star.png",
    "Terminal/Info/CommonUIAtlas/star_on.png",
    "Terminal/Info/CommonUIAtlas/tab.png",
    "Terminal/Info/CommonUIAtlas/tab_on.png",
    "Terminal/Info/CommonUIAtlas/ribbon.png",
    "Terminal/Info/CommonUIAtlas/line.png",
    "Items/12.png",
    "Items/1.png",
    "Items/2000.png",
    "BuffIcons/bufficon_1014.png",
    "SkillIcons/skill_999999.png",
    "Back/back10000.png",
    "ClassIcons/img_classchart.png",
    "Image/back10000/back10000.png",
]


def head_or_get(region, rel, download=False, timeout=12):
    url = BASE.format(region=region) + rel
    try:
        req = urllib.request.Request(url, headers=UA, method="GET")
        with _open.open(req, timeout=timeout) as r:
            blob = r.read()
            code = r.status
    except urllib.error.HTTPError as e:
        return rel, url, e.code, 0, None
    except Exception:
        return rel, url, 0, 0, None
    if code == 200 and download:
        p = OUT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(blob)
    return rel, url, code, len(blob), (blob if download else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--file", default="")
    ap.add_argument("--region", default="CN")
    ap.add_argument("--download", action="store_true")
    a = ap.parse_args()

    cands = list(SEED) if a.seed else []
    if a.file:
        cands += [l.strip() for l in Path(a.file).read_text().splitlines() if l.strip() and not l.startswith("#")]
    if not cands:
        raise SystemExit("没有候选清单：用 --seed 或 --file")

    OUT.mkdir(parents=True, exist_ok=True)
    hits, miss = [], 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(head_or_get, a.region, c, a.download) for c in cands]
        for f in futs:
            rel, url, code, size, _ = f.result()
            if code == 200:
                hits.append({"path": rel, "url": url, "bytes": size})
                print(f"  200 {size:>8d}  {rel}")
            else:
                miss += 1
    old = []
    if INDEX.exists():
        try:
            old = json.loads(INDEX.read_text()).get("files", [])
        except Exception:
            old = []
    merged = {(e["path"], e.get("url")): e for e in old}
    for h in hits:
        merged[(h["path"], h["url"])] = h
    INDEX.write_text(json.dumps({
        "region": a.region,
        "rule": "https://static.atlasacademy.io/{region}/<bundle路径>/<精灵名>.png",
        "checked_at": time.strftime("%Y-%m-%d %H:%M"),
        "total_ok": len(merged),
        "files": sorted(merged.values(), key=lambda e: e["path"])}, ensure_ascii=False, indent=1))
    print(f"\n命中 {len(hits)} / 候选 {len(cands)}，未命中 {miss}；索引共 {len(merged)} 条 -> {INDEX}")


if __name__ == "__main__":
    main()
