#!/usr/bin/env python3
"""素材库访问层 —— 所有出图脚本统一走这里，别再各写一套下载逻辑。

设计：本地优先，缺失自动补（下载到 ~/fgo-wiki/assets/ 对应目录），返回本地绝对路径。

    from assetlib import class_icon, card_icon, star, skill_icon, item_icon, servant_art, servant_face, np_card, bond_ce

    class_icon("saber", rarity=5)     # → Path('~/fgo-wiki/assets/classes/saber_gold.png')
    skill_icon("skill_00300")         # → assets/skills/skill_00300.png（缺则从 Atlas 拉）
    item_icon(6512)                   # → assets/items/6512.png
    servant_art(100100)               # → assets/servants/art_100100.png（L2 缓存）

约定（与 RULES.md 第 7 条一致）：请求间隔 0.5s，UA=fgo-wiki-updater，404 返回 None 不抛异常。
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

WIKI = Path(os.path.expanduser("~/fgo-wiki"))
A = WIKI / "assets"
ATLAS = "https://static.atlasacademy.io"
UA = "fgo-wiki-updater"
INTERVAL = 0.5

CLASS_IDS = {
    "saber": 1, "archer": 2, "lancer": 3, "rider": 4, "caster": 5, "assassin": 6,
    "berserker": 7, "shielder": 8, "ruler": 9, "alterego": 10, "avenger": 11,
    "mooncancer": 13, "foreigner": 14, "pretender": 15, "beast": 20, "unknown": 97,
}


def _tier(rarity: int | str | None) -> str:
    try:
        r = int(rarity or 5)
    except Exception:
        r = 5
    return "gold" if r >= 4 else ("silver" if r == 3 else "bronze")


def _download(url: str, dest: Path) -> bool:
    if not url:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            dest.write_bytes(r.read())
        time.sleep(INTERVAL)
        return True
    except Exception:
        time.sleep(INTERVAL)
        return False


def class_icon(cls: str, rarity: int | str | None = 5) -> Path | None:
    """职阶图标（按星级取金/银/铜）。返回 None 表示该职阶本地没有素材。"""
    name = (cls or "").lower()
    for cand in (A / "classes" / f"{name}_{_tier(rarity)}.png",
                 A / "ui" / "classes" / f"{name}_{_tier(rarity)}.png",
                 A / "classes" / f"{name}_gold.png"):
        if cand.exists():
            return cand
    return None


def card_icon(kind: str) -> Path | None:
    """指令卡图标：quick / arts / buster。"""
    p = A / "cards" / f"{kind.lower()}.png"
    if p.exists():
        return p
    return p if _download(f"{ATLAS}/CN/Servants/Commands/icon_card_{kind.lower()}.png", p) else None


def star(n: int) -> Path | None:
    p = A / "stars" / f"{int(n)}star.png"
    return p if p.exists() else None


def skill_icon(icon_name: str) -> Path | None:
    """技能图标：可传 'skill_00300' 或带 .png。本地缺失则从 Atlas 补。"""
    name = icon_name if icon_name.endswith(".png") else f"{icon_name}.png"
    p = A / "skills" / name
    if p.exists():
        return p
    for region in ("CN", "JP"):
        if _download(f"{ATLAS}/{region}/SkillIcons/{name}", p):
            return p
    return None


def item_icon(item_id: int | str) -> Path | None:
    name = f"{item_id}.png"
    p = A / "items" / name
    if p.exists():
        return p
    for region in ("CN", "JP"):
        if _download(f"{ATLAS}/{region}/Items/{name}", p):
            return p
    return None


def _raw(sid: int | str, region: str = "CN") -> dict | None:
    fp = WIKI / "raw" / "servants" / region / f"{sid}.json"
    if not fp.exists():
        return None
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return None


def servant_art(sid: int | str, asc: int | None = None) -> Path | None:
    """从者立绘。asc=None 取满破，asc=1..4 取指定再临；缺则从 Atlas 补（落 L2 缓存）。"""
    sid = str(sid)
    p = A / "servants" / f"art_{sid}.png"
    if p.exists() and asc is None:
        return p
    if asc is not None:
        p2 = A / "servants" / f"art_{sid}_{asc}.png"
        if p2.exists():
            return p2
        if _download(f"{ATLAS}/CN/CharaGraph/{sid}/{sid}b@{asc}.png", p2):
            return p2
        if _download(f"{ATLAS}/CN/CharaGraph/{sid}/{sid}{asc}@2.png", p2):
            return p2
        return None
    if _download(f"{ATLAS}/CN/Servants/{sid}/{sid}b@2.png", p):
        return p
    if _download(f"{ATLAS}/CN/CharaGraph/{sid}/{sid}b@2.png", p):
        return p
    return None


def servant_face(sid: int | str, asc: int = 0) -> Path | None:
    """从者头像 f_{id}{asc}.png（默认灵基 0）。"""
    sid = str(sid)
    p = A / "servants" / f"face_{sid}_{asc}.png"
    if p.exists():
        return p
    return p if _download(f"{ATLAS}/CN/Faces/f_{sid}{asc}.png", p) else None


def np_card(sid: int | str) -> Path | None:
    """宝具卡图（指令卡样式的 NP 图）。"""
    sid = str(sid)
    p = A / "servants" / f"npcard_{sid}.png"
    if p.exists():
        return p
    return p if _download(f"{ATLAS}/CN/Servants/Commands/{sid}/card_servant_np.png", p) else None


def bond_ce(sid: int | str) -> Path | None:
    """羁绊礼装图（按从者 id 反查 bondEquip）。"""
    sid = str(sid)
    p = A / "servants" / f"bondce_{sid}.png"
    if p.exists():
        return p
    raw = _raw(sid)
    ce = (raw or {}).get("bondEquip")
    ce_id = ce.get("id") if isinstance(ce, dict) else None
    if not ce_id:
        return None
    return p if _download(f"{ATLAS}/CN/Items/{ce_id}.png", p) else None


__all__ = ["class_icon", "card_icon", "star", "skill_icon", "item_icon",
           "servant_art", "servant_face", "np_card", "bond_ce"]
