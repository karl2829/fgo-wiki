#!/usr/bin/env python3
"""FGO 御主礼装同步脚本 v2 — 步长 +10 探测"""

import json, os, time
from datetime import datetime
import urllib.request

WIKI = os.path.expanduser("~/fgo-wiki")
RAW_FILE = f"{WIKI}/raw/mystic-codes/all.json"
ENT_DIR = f"{WIKI}/entities/mystic-codes"
INDEX_FILE = f"{ENT_DIR}/index.md"
STATE_FILE = f"{WIKI}/data/mystic_code_sync_state.json"


def fetch(id):
    url = f"https://api.atlasacademy.io/nice/CN/MC/{id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "fgo-wiki/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404: return None
        raise
    except: return None


def generate_md(mc):
    name = mc.get("name", "?").replace("/", "·")
    skills = mc.get("skills", [])
    extra = mc.get("extraAssets", {})
    icon = ""
    if isinstance(extra, dict):
        icon = extra.get("icon", "")
        if isinstance(icon, dict):
            icon = next(iter(icon.values()), "")

    lines = [
        f"# {name}", "",
        f"> **ID**: {mc['id']}",
        "", "## 基本信息", "",
        "| 属性 | 值 |", "|------|-----|",
        f"| 名称 | {name} |",
        f"| 日文名 | {mc.get('originalName','—')} |",
        f"| ID | {mc['id']} |", "",
    ]
    if skills:
        lines += ["## 技能列表", "",
                  "| 技能名 | 效果 | 冷却 |",
                  "|--------|------|------|"]
        for sk in skills:
            detail = sk.get("detail", "").replace("\n", " ")
            cd = "→".join(str(c) for c in sk.get("coolDown", []))
            lines.append(f"| {sk.get('name','?')} | {detail} | {cd} |")
        lines.append("")
    if icon:
        lines += ["## 图标", "", f"![]({icon})", ""]
    lines += ["---", "", f"*数据来源: Atlas Academy API* | *最后更新: {datetime.now().strftime('%Y-%m-%d')}*"]
    return "\n".join(lines)


def main():
    os.makedirs(ENT_DIR, exist_ok=True)
    os.makedirs(f"{WIKI}/raw/mystic-codes", exist_ok=True)
    os.makedirs(f"{WIKI}/data", exist_ok=True)

    state = {"max_id": 0, "last_sync_at": "", "total": 0}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
    last_max = state.get("max_id", 0)
    print(f"上次同步到 ID: {last_max}")

    all_mc = []
    if os.path.exists(RAW_FILE):
        with open(RAW_FILE) as f:
            all_mc = json.load(f)
    existing_ids = {m["id"] for m in all_mc}

    # Probe by +10 step, starting from last_max+10
    # (1 is a special case; after that, all IDs are multiples of 10)
    print("探测新御主礼装 (步长+10)...")
    new_ids = []
    for i in range(max(10, last_max + 10), max(201, last_max + 110), 10):
        data = fetch(i)
        if data:
            new_ids.append(i)
            print(f"  ✓ #{i} {data.get('name','?')}")
        else:
            print(f"  ✗ #{i} 不存在")
        time.sleep(0.5)

    if not new_ids:
        print("没有新御主礼装")
    else:
        # Fetch details and generate MD
        for nid in new_ids:
            if nid in existing_ids:
                continue
            data = fetch(nid)
            if data:
                all_mc.append(data)
                name = data.get("name", f"MC_{nid}").replace("/", "·")
                path = os.path.join(ENT_DIR, f"{name}.md")
                with open(path, "w") as f:
                    f.write(generate_md(data))
        all_mc.sort(key=lambda x: x["id"])
        with open(RAW_FILE, "w") as f:
            json.dump(all_mc, f, ensure_ascii=False)
        print(f"新增 {len(new_ids)} 个礼装")

    # Index
    lines = [
        "# 御主礼装索引", "",
        f"> 更新时间：{datetime.now().strftime('%Y-%m-%d')} | 共 {len(all_mc)} 个御主礼装",
        "", "| ID | 名称 | 技能数量 |",
        "|----|------|----------|",
    ]
    for m in all_mc:
        lines.append(f"| {m['id']} | [[{m.get('name','?')}]] | {len(m.get('skills',[]))} |")
    with open(INDEX_FILE, "w") as f:
        f.write("\n".join(lines))

    with open(STATE_FILE, "w") as f:
        json.dump({
            "max_id": max(m["id"] for m in all_mc),
            "last_sync_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total": len(all_mc),
        }, f, indent=2)

    print(f"完成！共 {len(all_mc)} 个御主礼装")


if __name__ == "__main__":
    main()
