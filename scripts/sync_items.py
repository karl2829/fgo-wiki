#!/usr/bin/env python3
"""FGO 道具同步脚本 v1 — 全量拉取 + 增量更新"""

import json, os, sys, re
from datetime import datetime
import urllib.request

WIKI = os.path.expanduser("~/fgo-wiki")
RAW_FILE = f"{WIKI}/raw/items/all.json"
ACTIVE_FILE = f"{WIKI}/entities/items/active_items.json"
STATE_FILE = f"{WIKI}/data/item_sync_state.json"
INDEX_FILE = f"{WIKI}/entities/items/index.md"
CUTOFF = 1751270400  # 2025-07-01


def ts_str(ts):
    if not ts or ts == 0: return "常驻"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def generate_md(item):
    name = item["name"].replace("/", "·")
    lines = [
        f"# {name}", "",
        f"> **ID**: {item['id']} | **类型**: {item.get('type','?')} | **稀有度**: {item.get('background','?')}",
        "",
        "## 基本信息", "",
        "| 属性 | 值 |", "|------|-----|",
        f"| 名称 | {name} |",
        f"| 日文名称 | {item.get('originalName','—')} |",
        f"| ID | {item['id']} |",
        f"| 类型 | {item.get('type','?')} |",
        f"| 稀有度 | {item.get('background','?')} |",
        f"| 开始时间 | {ts_str(item.get('startedAt',0))} |",
        f"| 结束时间 | {ts_str(item.get('endedAt',0))} |",
        "",
    ]
    detail = item.get("detail", "")
    if detail:
        lines += ["## 详细说明", "", detail, ""]
    icon = item.get("icon", "")
    if icon:
        lines += ["## 图标", "", f"![{name}]({icon})", ""]
    lines += ["---", "", f"*数据来源: Atlas Academy API* | *最后更新: {datetime.now().strftime('%Y-%m-%d')}*"]
    return "\n".join(lines)


def main():
    os.makedirs(f"{WIKI}/raw/items", exist_ok=True)
    os.makedirs(f"{WIKI}/entities/items", exist_ok=True)
    os.makedirs(f"{WIKI}/data", exist_ok=True)

    # Load sync state
    synced_ids = set()
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
            synced_ids = set(state.get("synced_ids", []))
    print(f"已同步: {len(synced_ids)} 个道具")

    # Download all items
    print("拉取道具数据...")
    url = "https://api.atlasacademy.io/export/CN/nice_item.json"
    req = urllib.request.Request(url, headers={"User-Agent": "fgo-wiki/1.0"})
    all_items = []
    with urllib.request.urlopen(req, timeout=120) as resp:
        all_items = json.loads(resp.read())
    print(f"全量道具: {len(all_items)}")

    # Save raw
    with open(RAW_FILE, "w") as f:
        json.dump(all_items, f, ensure_ascii=False)

    # Filter active items
    active = [i for i in all_items
              if i.get("endedAt", 0) == 0 or i.get("endedAt", 0) > CUTOFF]
    print(f"活跃道具: {len(active)}")

    # Build active item lookup
    active_map = {i["id"]: i for i in active}
    new_ids = [iid for iid in active_map if iid not in synced_ids]
    print(f"新增道具: {len(new_ids)}")

    if not new_ids:
        print("没有新道具，跳过更新")
        return

    # Load existing active cache
    existing_active = []
    if os.path.exists(ACTIVE_FILE):
        with open(ACTIVE_FILE) as f:
            existing_active = json.load(f)

    # Merge: keep all active items
    merged = [i for i in existing_active if i["id"] in active_map]  # remove stale
    existing_ids = {i["id"] for i in merged}
    for nid in new_ids:
        merged.append(active_map[nid])
    merged.sort(key=lambda x: x["id"])

    with open(ACTIVE_FILE, "w") as f:
        json.dump(merged, f, ensure_ascii=False)

    # Generate individual MD files (use ID as filename to avoid duplicate name issues)
    item_dir = f"{WIKI}/entities/items"
    count = 0
    for nid in new_ids:
        item = active_map[nid]
        name = item["name"].replace("/", "·")
        path = os.path.join(item_dir, f"{item['id']}.md")
        try:
            with open(path, "w") as f:
                f.write(generate_md(item))
            count += 1
        except Exception as e:
            print(f"  ✗ {name}: {e}")

    print(f"生成 {count} 个道具页面")

    # Generate index
    lines = [
        "# 道具索引", "",
        f"> 更新时间：{datetime.now().strftime('%Y-%m-%d')} | 共 {len(merged)} 个活跃道具",
        "",
        "| ID | 名称 | 类型 | 稀有度 | 图标 |",
        "|----|------|------|--------|------|",
    ]
    for item in merged:
        name = item["name"]
        icon = item.get("icon", "")
        ico = f"![icon]({icon})" if icon else "—"
        lines.append(f"| {item['id']} | [[{item['id']}|{name}]] | {item.get('type','?')} | {item.get('background','?')} | {ico} |")
    with open(INDEX_FILE, "w") as f:
        f.write("\n".join(lines))

    # Update sync state
    with open(STATE_FILE, "w") as f:
        json.dump({
            "synced_ids": sorted(list(synced_ids | set(new_ids))),
            "last_sync_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_active": len(merged),
        }, f)
    print(f"完成！活跃道具: {len(merged)}, 新增: {len(new_ids)}")


if __name__ == "__main__":
    main()
