#!/usr/bin/env python3
"""素材库统一拉取器 —— fgo-wiki 自己的出图素材，尽量不依赖外部 CDN。

素材分层（设计原则：小的进 git，大的本地缓存）：
  L1 图标层（入 git，十几 MB）
      assets/classes/   职阶图标   {class}_{gold|silver|bronze}.png
      assets/cards/     指令卡图标 quick/arts/buster/extra/np.png
      assets/stars/     星级       1star..5star.png
      assets/skills/    Atlas 技能图标 skill_XXXXX.png
      assets/items/     Atlas 道具图标 {item_id}.png
  L2 从者层（不入 git，本地缓存，~300MB）
      assets/servants/art_{id}.png        立绘（满破优先）
      assets/servants/face_{id}_{asc}.png 头像
      assets/servants/npcard_{id}.png     宝具卡图
      assets/servants/bondce_{id}.png     羁绊礼装图

用法：
    cd ~/fgo-wiki
    ./.venv/bin/python scripts/fetch_assets.py --icons          # L1 三类基础图标
    ./.venv/bin/python scripts/fetch_assets.py --skills         # MD 引用的技能图标
    ./.venv/bin/python scripts/fetch_assets.py --items          # MD 引用的道具图标
    ./.venv/bin/python scripts/fetch_assets.py --servant 100100 # 单个从者素材
    ./.venv/bin/python scripts/fetch_assets.py --all-servants   # 全部（约 300MB，慢）
    ./.venv/bin/python scripts/fetch_assets.py --report         # 只统计缺口，不下载

规则（与 RULES.md 第 7 条一致）：请求间隔 ≥0.5s，UA=fgo-wiki-updater，增量跳过已存在文件，
404 记录后跳过，失败不中断。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

WIKI = Path(os.path.expanduser("~/fgo-wiki"))
A = WIKI / "assets"
UA = "fgo-wiki-updater"
INTERVAL = 0.5
TIMEOUT = 30

ATLAS = "https://static.atlasacademy.io"

# 职阶名 → Atlas class id（图标命名统一用名字，只有兜底下载时才需要 id）
CLASS_IDS = {
    "saber": 1, "archer": 2, "lancer": 3, "rider": 4, "caster": 5, "assassin": 6,
    "berserker": 7, "shielder": 8, "ruler": 9, "alterego": 10, "avenger": 11,
    "mooncancer": 13, "foreigner": 14, "pretender": 15, "beast": 20, "unknown": 97,
}


def get(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"    HTTP {e.code}: {url}")
        return None
    except Exception as e:
        print(f"    {type(e).__name__}: {url}")
        return None


def save(dest: Path, data: bytes | None) -> bool:
    if not data:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return True


def _md_files() -> list[Path]:
    return [Path(p) for p in glob.glob(str(WIKI / "entities/**/*.md"), recursive=True)]


def _referenced(prefix: str, pattern: str) -> list[str]:
    """扫 MD 里引用过的素材文件名（去重排序）。"""
    rx = re.compile(pattern)
    seen: set[str] = set()
    for fp in _md_files():
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in rx.finditer(text):
            seen.add(m.group(1))
    return sorted(seen)


def fetch_skills() -> tuple[int, list[str]]:
    names = _referenced("SkillIcons", r"SkillIcons/([a-z0-9_]+\.png)")
    print(f"技能图标：MD 引用 {len(names)} 个唯一文件")
    ok, fail = 0, []
    for i, name in enumerate(names, 1):
        dest = A / "skills" / name
        if dest.exists():
            continue
        if save(dest, get(f"{ATLAS}/CN/SkillIcons/{name}")):
            ok += 1
        else:                                   # JP 独有的图标退到 JP
            time.sleep(INTERVAL)
            if save(dest, get(f"{ATLAS}/JP/SkillIcons/{name}")):
                ok += 1
            else:
                fail.append(name)
        if i % 25 == 0:
            print(f"  [{i}/{len(names)}]")
        time.sleep(INTERVAL)
    return ok, fail


def fetch_items() -> tuple[int, list[str]]:
    ids = _referenced("Items", r"Items/(\d+\.png)")
    print(f"道具图标：MD 引用 {len(ids)} 个唯一文件")
    ok, fail = 0, []
    for i, name in enumerate(ids, 1):
        dest = A / "items" / name
        if dest.exists():
            continue
        if save(dest, get(f"{ATLAS}/CN/Items/{name}")):
            ok += 1
        else:
            time.sleep(INTERVAL)
            if save(dest, get(f"{ATLAS}/JP/Items/{name}")):
                ok += 1
            else:
                fail.append(name)
        if i % 100 == 0:
            print(f"  [{i}/{len(ids)}]")
        time.sleep(INTERVAL)
    return ok, fail


def fetch_icons() -> tuple[int, list[str]]:
    """L1 基础图标：职阶(金银铜) / 指令卡 / 星级。全部来自 Atlas，不依赖 jsdelivr。"""
    ok, fail = 0, []
    jobs: list[tuple[Path, str]] = []
    for name in CLASS_IDS:
        for tier in ("gold", "silver", "bronze"):
            jobs.append((A / "classes" / f"{name}_{tier}.png", name))

    for dest, _ in jobs:
        if dest.exists():
            continue
        # 职阶图标 Atlas 只有一套（无金银铜），先从既有 ui/classes 复制，缺的再下
        src = A / "ui" / "classes" / dest.name
        if src.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
            ok += 1
            continue
        cls_name = dest.stem.rsplit("_", 1)[0]
        cid = CLASS_IDS.get(cls_name)
        if cid is None:
            continue
        url = f"{ATLAS}/CN/ClassIcons/class_{cid}.png"
        if save(dest, get(url)):
            ok += 1
        else:
            fail.append(dest.name)
        time.sleep(INTERVAL)

    # 指令卡图标：优先用 card-render 已下的图，缺的从 Atlas 拉
    cr = WIKI / "card-render" / "assets"
    for card in ("quick", "arts", "buster"):
        dest = A / "cards" / f"{card}.png"
        if dest.exists():
            continue
        src = cr / f"card_{card[0].upper()}.png"
        if src.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
            ok += 1
            continue
        if save(dest, get(f"{ATLAS}/CN/Servants/Commands/icon_card_{card}.png")):
            ok += 1
        else:
            fail.append(dest.name)
        time.sleep(INTERVAL)

    # 星级（本地 ui/stars 已有 1star..5star）
    for n in range(1, 6):
        dest = A / "stars" / f"{n}star.png"
        if dest.exists():
            continue
        src = A / "ui" / "stars" / f"{n}star.png"
        if src.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
            ok += 1
    return ok, fail


def _raw(sid: str, region: str = "CN") -> dict | None:
    fp = WIKI / "raw" / "servants" / region / f"{sid}.json"
    if not fp.exists():
        return None
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return None


def fetch_servant(sid: str) -> tuple[int, list[str]]:
    """单个从者：立绘（满破优先）+ 头像 + 宝具卡图 + 羁绊礼装图。"""
    out = A / "servants"
    out.mkdir(parents=True, exist_ok=True)
    ok, fail = 0, []
    targets: list[tuple[Path, str]] = [
        (out / f"art_{sid}.png", f"{ATLAS}/CN/Servants/{sid}/{sid}b@2.png"),
        (out / f"npcard_{sid}.png", f"{ATLAS}/CN/Servants/Commands/{sid}/card_servant_np.png"),
    ]
    raw = _raw(sid)
    if raw:
        faces = (raw.get("extraAssets") or {}).get("faces") or {}
        asc = faces.get("ascension") or {}
        if asc:
            k = max(asc, key=lambda x: int(x))
            targets.append((out / f"face_{sid}_{k}.png", asc[k]))
        ce = (raw.get("bondEquip") or {}) if isinstance(raw.get("bondEquip"), dict) else {}
        ce_id = ce.get("id")
        if ce_id:
            targets.append((out / f"bondce_{sid}.png", f"{ATLAS}/CN/Items/{ce_id}.png"))

    for dest, url in targets:
        if dest.exists():
            continue
        if save(dest, get(url)):
            ok += 1
        else:
            fail.append(dest.name)
        time.sleep(INTERVAL)
    return ok, fail


def report() -> None:
    def cnt(p: Path) -> int:
        return len(list(p.glob("*.png"))) if p.exists() else 0

    skills = _referenced("SkillIcons", r"SkillIcons/([a-z0-9_]+\.png)")
    items = _referenced("Items", r"Items/(\d+\.png)")
    print("素材库现状")
    for sub, need in (("classes", 44), ("cards", 3), ("stars", 5), ("skills", len(skills)),
                      ("items", len(items)), ("servants", None)):
        have = cnt(A / sub)
        if need is None:
            print(f"  {sub:<10} 已有 {have:>5}  （按需缓存，不入 git）")
        else:
            print(f"  {sub:<10} 已有 {have:>5} / 需要 {need:<5} 缺口 {max(need - have, 0)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--icons", action="store_true", help="职阶/指令卡/星级基础图标")
    ap.add_argument("--skills", action="store_true", help="MD 引用的技能图标")
    ap.add_argument("--items", action="store_true", help="MD 引用的道具图标")
    ap.add_argument("--servant", action="append", default=[], help="从者内部 ID，可重复")
    ap.add_argument("--all-servants", action="store_true", help="全部从者（约 300MB）")
    ap.add_argument("--report", action="store_true", help="只统计缺口")
    args = ap.parse_args()

    if args.report or not any([args.icons, args.skills, args.items, args.servant, args.all_servants]):
        report()
        return 0

    if args.icons:
        ok, fail = fetch_icons()
        print(f"基础图标：新增 {ok}，失败 {len(fail)}")
    if args.skills:
        ok, fail = fetch_skills()
        print(f"技能图标：新增 {ok}，失败 {len(fail)} {fail[:5]}")
    if args.items:
        ok, fail = fetch_items()
        print(f"道具图标：新增 {ok}，失败 {len(fail)} {fail[:5]}")

    sids = list(args.servant)
    if args.all_servants:
        sids += [Path(p).stem for p in glob.glob(str(WIKI / "raw/servants/CN/*.json"))]
    if sids:
        ok = fail = 0
        for i, sid in enumerate(dict.fromkeys(sids), 1):
            o, f = fetch_servant(sid)
            ok += o
            fail += len(f)
            if i % 20 == 0 or i == len(set(sids)):
                print(f"  从者素材 [{i}] 新增 {ok} 失败 {fail}")
        print(f"从者素材：新增 {ok}，失败 {fail}")
    report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
