#!/usr/bin/env python3
"""Batch fetch all FGO servant data from Atlas Academy API (incremental)."""
import json, os, sys, time, glob, re
from datetime import datetime, timezone

WIKI = os.path.expanduser("~/fgo-wiki")
RAW_DIR = os.path.join(WIKI, "raw/servants")
STATE_PATH = os.path.join(WIKI, "data", "servant_sync_state.json")
INCREMENTAL = "--incremental" in sys.argv

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)

# ── Step 1: Load existing state ──
synced_ids = set()
if os.path.exists(STATE_PATH):
    with open(STATE_PATH) as f:
        state = json.load(f)
    synced_ids = set(state.get("synced_ids", []))
    print(f"已有状态: {len(synced_ids)} 个已拉取从者")

# Also check raw JSON files on disk
disk_ids = set()
for fp in glob.glob(os.path.join(RAW_DIR, "*.json")):
    try:
        sid = int(os.path.basename(fp).replace(".json", ""))
        disk_ids.add(sid)
    except ValueError:
        pass
print(f"磁盘上: {len(disk_ids)} 个JSON文件")

all_known = synced_ids | disk_ids
print(f"合并后: {len(all_known)} 个已知从者")

# ── Step 2: Fetch full servant ID list ──
print("\n获取全量从者ID列表...")
import urllib.request
url = "https://api.atlasacademy.io/export/CN/basic_servant.json"
req = urllib.request.Request(url, headers={"User-Agent": "hermes-agent"})
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        basic_list = json.loads(resp.read())
except Exception as e:
    print(f"获取basic_servant失败: {e}")
    sys.exit(1)

all_ids = sorted(set(s["id"] for s in basic_list))
print(f"API返回: {len(all_ids)} 个从者ID (min={min(all_ids)}, max={max(all_ids)})")

# ── Step 3: Find new IDs ──
new_ids = sorted(set(all_ids) - all_known)
print(f"新增: {len(new_ids)} 个 (已有 {len(all_known)} 个)")

if not new_ids:
    print("✅ 无需拉取新数据")
else:
    print(f"\n新增ID样本: {new_ids[:10]}...")
    total = len(new_ids)
    
    # ── Step 4: Fetch each servant ──
    for i, sid in enumerate(new_ids):
        url = f"https://api.atlasacademy.io/nice/CN/servant/{sid}?lore=true"
        path = os.path.join(RAW_DIR, f"{sid}.json")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "hermes-agent"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            cno = data.get("collectionNo", "?")
            name = data.get("name", "?")
            print(f"  [{i+1}/{total}] {sid} (#{cno} {name}) ✅")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"  [{i+1}/{total}] {sid} → 404 跳过")
            else:
                print(f"  [{i+1}/{total}] {sid} → HTTP {e.code} 跳过")
        except Exception as e:
            print(f"  [{i+1}/{total}] {sid} → {e} 跳过")
        
        if i < total - 1:
            time.sleep(0.8)
    
    # ── Step 5: Update state ──
    new_state = {
        "synced_ids": sorted(all_known | set(new_ids)),
        "last_sync_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": len(all_known | set(new_ids)),
    }
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(new_state, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 状态已更新: {new_state['total']} 个从者")

# ── Step 6: Generate MD files ──
print("\n=== 生成从者MD文件 ===")
sys.path.insert(0, WIKI)
import importlib.util
spec = importlib.util.spec_from_file_location("generate", os.path.join(WIKI, "generate.py"))
gen_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen_mod)
generate = gen_mod.generate

entity_dir = os.path.join(WIKI, "entities/servants")
os.makedirs(entity_dir, exist_ok=True)

count = 0
for fp in sorted(glob.glob(os.path.join(RAW_DIR, "*.json"))):
    sid = os.path.basename(fp).replace(".json", "")
    with open(fp, encoding="utf-8") as f:
        data = json.load(f)
    try:
        md = generate(data)
        name = data.get("name", str(sid)).replace("/", "·").replace("\\", "")
        entity_path = os.path.join(entity_dir, f"{name}.md")
        with open(entity_path, "w", encoding="utf-8") as f:
            f.write(md)
        count += 1
        if count % 10 == 0:
            print(f"  ... {count} files generated")
    except Exception as e:
        cno = data.get("collectionNo", sid)
        print(f"  ERR #{cno} {data.get('name','?')}: {e}")

print(f"\n✅ 已生成 {count} 个从者MD文件")
