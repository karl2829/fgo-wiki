#!/usr/bin/env python3
"""Generate CE markdown files from raw JSON and create index.
支持增量: 先拉 basic_equip.json 对比已知 ID，只下载新增的 lore 数据。"""
import json, os, sys, glob, re
from datetime import datetime, timezone
import urllib.request, time

WIKI = os.path.expanduser("~/fgo-wiki")
RAW_BASE = os.path.join(WIKI, "raw/craft-essences")
ENT_BASE = os.path.join(WIKI, "entities/craft-essences")
STATE_FILE = os.path.join(WIKI, "data/ce_sync_state.json")
API_BASE = "https://api.atlasacademy.io"

TYPE_NAMES = {
    "servantEquip": "从者牵绊礼装",
    "normal": "常驻礼装",
    "event": "活动礼装",
    "limited": "限定礼装",
    "friendship": "友情池礼装",
    "masterMission": "御主任务礼装",
    "valentine": "情人节礼物",
    "exp": "经验值礼装",
}

def generate_ce(data):
    lines = []
    h = lambda s="": lines.append(s)

    ce_id = data.get("id", "?")
    name = data.get("name", "???")
    rarity = data.get("rarity", 0)
    cost = data.get("cost", 0)
    ce_type = TYPE_NAMES.get(data.get("type", ""), data.get("type", ""))
    max_lv = data.get("maxLevel", 0)
    atk_base = data.get("atkBase", 0)
    atk_max = data.get("atkMax", 0)
    hp_base = data.get("hpBase", 0)
    hp_max = data.get("hpMax", 0)
    
    # Effect info
    detail = data.get("detail", "")
    detail2 = ""
    skill_icon = ""
    
    # Skills array: [0]=未破, [1]=满破 (or if detail field on CE is set, use that as unbroken)
    skills = data.get("skills", [])
    if not detail and skills:
        detail = skills[0].get("detail", "")
        skill_icon = skills[0].get("icon", "")
        if len(skills) > 1:
            d2 = skills[1].get("detail", "")
            if d2 and d2 != detail:
                detail2 = d2
    elif detail:
        # CE has its own detail, check skills for max break
        if skills:
            skill_icon = skills[0].get("icon", "")
            sk_detail = skills[0].get("detail", "")
            if sk_detail and sk_detail != detail:
                detail2 = sk_detail
    
    # Gallery
    chara_graph = ""
    assets = data.get("extraAssets", {}).get("charaGraph", {}).get("ce", {})
    for limit_key in sorted(assets.keys()):
        ld = assets[limit_key]
        if isinstance(ld, dict):
            for sub_key in sorted(ld.keys()):
                if not chara_graph:
                    chara_graph = ld[sub_key]
        break
    
    # Face
    face_url = ""
    face_assets = data.get("extraAssets", {}).get("faces", {}).get("ce", {})
    for fk in sorted(face_assets.keys()):
        face_url = face_assets[fk]
        break
    
    # Profile / Lore
    profile = data.get("profile", {})
    cv = profile.get("cv", "")
    illustrator_profile = profile.get("illustrator", "")
    comments_list = profile.get("comments", [])
    comment_texts = []
    for c in comments_list:
        txt = c.get("comment", "")
        if txt:
            comment_texts.append(txt)

    stars = "★" * rarity if 1 <= rarity <= 5 else ""
    
    # Header
    h(f"# {name}")
    h()
    collab = data.get("collectionNo", ce_id)
    h(f"> **ID**: {ce_id} | **图鉴编号**: {collab} | **星级**: {stars} | **COST**: {cost}")
    h(f"> **类型**: {ce_type}")
    h()
    
    # Basic info
    h("## 基础信息")
    h()
    h("| 属性 | 值 |")
    h("|------|-----|")
    h(f"| 名称 | {name} |")
    h(f"| 类型 | {ce_type} |")
    h(f"| 星级 | {stars} |")
    h(f"| COST | {cost} |")
    h(f"| 等级上限 | {max_lv} |")
    h()
    
    # Stats table
    if atk_base != 0 or hp_base != 0:
        h("## 数值")
        h()
        h("| 属性 | Lv.1 | Lv.MAX |")
        h("|------|------|--------|")
        h(f"| ATK | {atk_base} | {atk_max} |")
        h(f"| HP | {hp_base} | {hp_max} |")
        h()
    
    # Skill effects
    if detail or detail2:
        h("## 技能效果")
        h()
        
        if detail:
            h("### 未破效果")
            h()
            if skill_icon:
                h(f"![]({skill_icon})")
                h()
            h(f"- **效果**：{detail}")
            h()
        
        if detail2:
            h("### 满破效果（Lv.MAX）")
            h()
            if skill_icon:
                h(f"![]({skill_icon})")
                h()
            h(f"- **效果**：{detail2}{'[最大解放]' if '[最大解放]' not in detail2 else ''}")
            h()
    
    # Visual resources
    has_visual = bool(chara_graph or face_url)
    if has_visual:
        h("## 视觉资源")
        h()
        if chara_graph:
            h("### 卡面")
            h(f"![]({chara_graph})")
            h()
        if face_url:
            h("### 头像")
            h(f"![]({face_url})")
            h()
    
    # Lore/comment
    if comment_texts:
        h("## 解说")
        h()
        for ct in comment_texts:
            h(f"> {ct}")
            h()
    
    # Bond reference
    if data.get("bondEquip"):
        h("## 关联内容")
        h("- **羁绊礼装**")
        h()
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    h("---")
    h()
    h(f"*数据来源: Atlas Academy API* | *最后更新: {today}*")
    
    return "\n".join(lines)

def process_region(region, data_list):
    raw_dir = os.path.join(RAW_BASE, region)
    ent_dir = os.path.join(ENT_BASE, region)
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(ent_dir, exist_ok=True)
    
    by_id = {ce["id"]: ce for ce in data_list if ce.get("id")}
    
    for ce_id in sorted(by_id.keys()):
        ce = by_id[ce_id]
        raw_path = os.path.join(raw_dir, f"{ce_id}.json")
        if not os.path.exists(raw_path):
            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(ce, f, ensure_ascii=False, indent=2)
        md = generate_ce(ce)
        with open(os.path.join(ent_dir, f"{ce_id}.md"), "w", encoding="utf-8") as f:
            f.write(md)

    print(f"  {region}: {len(by_id)} 张礼装")
    return [(ce_id, by_id[ce_id].get("name","?"), by_id[ce_id].get("rarity",0)) for ce_id in sorted(by_id.keys())]

def generate_index(cn_list, jp_list):
    lines = ["# 概念礼装索引", "", "## 国服", "", "| ID | 名称 | 稀有度 |", "|---|---|---|"]
    for cid, name, r in sorted(cn_list):
        lines.append(f"| {cid} | {name} | {'★'*r if 1<=r<=5 else ''} |")
    lines += ["", "## 日服", "", "| ID | 名称 | 稀有度 |", "|---|---|---|"]
    for cid, name, r in sorted(jp_list):
        lines.append(f"| {cid} | {name} | {'★'*r if 1<=r<=5 else ''} |")
    return "\n".join(lines)

if __name__ == "__main__":
    cn_path = "/tmp/cn_nice_equip.json"
    jp_path = "/tmp/jp_nice_equip.json"
    
    # 增量更新: 读取状态 + 检查本地文件时效
    state = {}
    if os.path.exists(STATE_FILE):
        state = json.load(open(STATE_FILE))
    synced_ids = set(state.get("synced_ids", []))
    last_sync = state.get("last_sync_at", "")
    print(f"上次同步: {last_sync or '从未'} | 已同步: {len(synced_ids)} 张")
    
    # 如果本地 lore 文件已存在且状态已有记录, 跳过 API 检查
    # 后续可通过 --force 参数强制重新生成
    if synced_ids and not "--force" in sys.argv:
        lore_file = "/tmp/cn_nice_equip.json"
        if os.path.exists(lore_file):
            file_age = (time.time() - os.path.getmtime(lore_file)) / 86400
            if file_age < 30:  # 30天内无需检查
                print(f"    本地数据较新 ({file_age:.0f} 天), 跳过")
                sys.exit(0)
    
    cn_idx, jp_idx = [], []
    
    if os.path.exists(cn_path):
        cn_data = json.load(open(cn_path))
        cn_filtered = [ce for ce in cn_data if ce.get("rarity", 0) >= 3]
        print(f"CN: {len(cn_filtered)} 张")
        cn_idx = process_region("CN", cn_filtered)
    
    if os.path.exists(jp_path):
        jp_data = json.load(open(jp_path))
        jp_all = [ce for ce in jp_data if ce.get("rarity", 0) >= 3]
        cn_ids = {ce[0] for ce in cn_idx} if cn_idx else set()
        jp_only = [ce for ce in jp_all if ce.get("id") not in cn_ids]
        print(f"JP: {len(jp_all)} 张, 补充CN没有: {len(jp_only)}")
        if jp_only:
            jp_idx = process_region("JP", jp_only)
    
    idx_md = generate_index(cn_idx, jp_idx)
    with open(os.path.join(ENT_BASE, "index.md"), "w", encoding="utf-8") as f:
        f.write(idx_md)
    print(f"Index: {len(cn_idx)} CN + {len(jp_idx)} JP")
    
    # Update sync state
    all_ce_ids = {ce[0] for ce in cn_idx} | {ce[0] for ce in jp_idx}
    json.dump({
        "last_sync_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "synced_ids": sorted(all_ce_ids),
        "total": len(all_ce_ids),
    }, open(STATE_FILE, "w"), indent=2)
