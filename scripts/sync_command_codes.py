#!/usr/bin/env python3
"""FGO 指令纹章批量导入 v2 — 直接枚举 #1~200"""

import json, os, sys, time, math
from datetime import datetime
import urllib.request

WIKI = os.path.expanduser("~/fgo-wiki")
RAW_FILE = f"{WIKI}/raw/command-codes/all.json"
ENT_DIR = f"{WIKI}/entities/command-codes"
INDEX_FILE = f"{ENT_DIR}/index.md"
STATE_FILE = f"{WIKI}/data/command_code_sync_state.json"
RARITY_STARS = {1: "★", 2: "★★", 3: "★★★", 4: "★★★★", 5: "★★★★★"}
MAX_CN = 200

def fetch_cc(cn: int):
    url = f"https://api.atlasacademy.io/nice/CN/CC/{cn}"
    req = urllib.request.Request(url, headers={"User-Agent": "fgo-wiki/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except:
        return None


def generate_md(cc: dict) -> str:
    cc_id = cc.get("id", "?")
    name = cc.get("name", "?").replace("/", "·")
    stars = RARITY_STARS.get(cc.get("rarity", 1), "★")
    skills = cc.get("skills", [])
    detail = skills[0].get("detail", "") if skills else ""
    icon = skills[0].get("icon", "") if skills else ""
    extra = cc.get("extraAssets", {})
    chara_graph = extra.get("charaGraph", {}).get("cc", "")
    comment = cc.get("comment", "")
    illustrator = cc.get("illustrator", "")

    lines = [
        f"# {name}", "",
        f"> **ID**: {cc['id']} | **图鉴编号**: {cc.get('collectionNo','?')} | **稀有度**: {stars} | **画师**: {illustrator}",
        "",
        "## 基本信息", "",
        "| 属性 | 值 |",
        "|------|-----|",
        f"| 名称 | {name} |",
        f"| 日文名称 | {cc.get('originalName','—')} |",
        f"| ID | {cc['id']} |",
        f"| 图鉴编号 | {cc.get('collectionNo','?')} |",
        f"| 稀有度 | {stars} |",
        f"| 画师 | {illustrator or '—'} |",
        "",
        "## 效果", "",
        detail, "",
    ]
    if icon:
        lines += ["## 图标", "", f"![]({icon})", ""]
    if chara_graph:
        lines += ["## 卡面", "", f"![]({chara_graph})", ""]
    if comment:
        lines += ["## 背景故事", "", comment, ""]
    lines += ["---", "", f"*数据来源: Atlas Academy API* | *最后更新: {datetime.now().strftime('%Y-%m-%d')}*"]
    return "\n".join(lines)


def main():
    os.makedirs(ENT_DIR, exist_ok=True)
    os.makedirs(f"{WIKI}/raw/command-codes", exist_ok=True)
    
    # 增量更新: 读取上次同步状态
    state = {}
    if os.path.exists(STATE_FILE):
        state = json.load(open(STATE_FILE))
    last_max = state.get("last_collection_no", 0)
    last_sync = state.get("last_sync_at", "")
    synced_ids = set(state.get("synced_ids", []))
    print(f"上次同步: {last_sync or '从未'} | 已同步: {len(synced_ids)} 个 | 最大编号: {last_max}")
    
    all_cc = []
    omit = []
    start_from = max(1, last_max + 1)
    for cn in range(start_from, MAX_CN + 1):
        data = fetch_cc(cn)
        if data:
            all_cc.append(data)
        else:
            omit.append(cn)
        if cn % 50 == 0 or cn == start_from:
            print(f"  {cn}/{MAX_CN} ({len(all_cc)} 个)")
        time.sleep(0.5)

    print(f"成功: {len(all_cc)}, 空缺: {len(omit)} ({omit[:5]}...)")

    # Save raw
    with open(RAW_FILE, "w") as f:
        json.dump(all_cc, f, ensure_ascii=False)

    # Generate MD files
    by_rarity = {}
    for cc in all_cc:
        cc_id = str(cc.get("id", f"CC_{cc['id']}"))
        r = cc.get("rarity", 1)
        by_rarity.setdefault(r, []).append(cc)
        path = os.path.join(ENT_DIR, f"{cc_id}.md")
        with open(path, "w") as f:
            f.write(generate_md(cc))

    print(f"已生成 {len(all_cc)} 个纹章页面")

    # Index by rarity
    lines = ["# 指令纹章索引", "", f"> 更新时间：{datetime.now().strftime('%Y-%m-%d')} | 共 {len(all_cc)} 个纹章", ""]
    for r in sorted(by_rarity.keys()):
        lines.append(f"## {RARITY_STARS.get(r, '★')}")
        lines.append("")
        lines.append("| ID | 名称 | 图鉴编号 | 画师 |")
        lines.append("|----|------|----------|------|")
        for cc in sorted(by_rarity[r], key=lambda x: x.get("collectionNo", 0)):
            cn = cc.get("collectionNo", "?")
            ill = cc.get("illustrator", "—")
            lines.append(f"| {cc['id']} | [[{cc_id}|{cc.get('name','?')}]] | {cn} | {ill} |")
        lines.append("")
    with open(INDEX_FILE, "w") as f:
        f.write("\n".join(lines))
    print("索引页已生成")
    print(f"完成！{len(all_cc)} 个纹章")
    
    # Update sync state
    max_cn = max(cc.get("collectionNo", 0) for cc in all_cc) if all_cc else last_max
    new_ids = {cc["id"] for cc in all_cc} - synced_ids
    fresh_ids = synced_ids | {cc["id"] for cc in all_cc}
    if all_cc:
        json.dump({
            "last_collection_no": max_cn,
            "last_sync_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "synced_ids": sorted(fresh_ids),
            "total": len(fresh_ids),
        }, open(STATE_FILE, "w"), indent=2)
    print(f"新增: {len(new_ids)} 个纹章, 总计: {len(fresh_ids)}")


if __name__ == "__main__":
    main()
