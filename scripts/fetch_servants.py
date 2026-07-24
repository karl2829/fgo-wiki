#!/usr/bin/env python3
"""Incremental fetch: download only new servant raw JSON files."""
import json, os, time, glob, urllib.request, sys
from datetime import datetime, timezone

WIKI = os.path.expanduser("~/fgo-wiki")
RAW_DIR = os.path.join(WIKI, "raw/servants/CN")
STATE_PATH = os.path.join(WIKI, "data", "servant_sync_state.json")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)

# Load existing IDs
disk_ids = set()
for fp in glob.glob(os.path.join(RAW_DIR, "*.json")):
    try: disk_ids.add(int(os.path.basename(fp).replace(".json","")))
    except: pass

print(f"磁盘已有: {len(disk_ids)} 个JSON文件")

# Load state if exists
synced = set()
if os.path.exists(STATE_PATH):
    with open(STATE_PATH) as f:
        synced = set(json.load(f).get("synced_ids", []))
known = disk_ids | synced

# Fetch full servant list
print("获取全量从者ID列表...")
url = "https://api.atlasacademy.io/export/CN/basic_servant.json"
req = urllib.request.Request(url, headers={"User-Agent": "hermes-agent"})
with urllib.request.urlopen(req, timeout=120) as resp:
    basic_list = json.loads(resp.read())

all_ids = sorted(set(s["id"] for s in basic_list))
new_ids = sorted(set(all_ids) - known)
print(f"API: {len(all_ids)} 个, 新增: {len(new_ids)} 个")

if not new_ids:
    print("✅ 无需拉取")
    sys.exit(0)

# Fetch each
total = len(new_ids)
success = 0
failed = 0
for i, sid in enumerate(new_ids):
    url = f"https://api.atlasacademy.io/nice/CN/servant/{sid}?lore=true"
    path = os.path.join(RAW_DIR, f"{sid}.json")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "hermes-agent"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        cno = data.get("collectionNo", "?")
        name = data.get("name", "?")
        print(f"  [{i+1}/{total}] {sid} (#{cno} {name})")
        success += 1
    except urllib.error.HTTPError as e:
        print(f"  [{i+1}/{total}] {sid} → HTTP {e.code}")
        failed += 1
    except Exception as e:
        print(f"  [{i+1}/{total}] {sid} → {e}")
        failed += 1
    if i < total - 1:
        time.sleep(0.5)

# Save state
all_synced = sorted(known | set(new_ids))
with open(STATE_PATH, "w", encoding="utf-8") as f:
    json.dump({
        "synced_ids": all_synced,
        "last_sync_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": len(all_synced),
    }, f, ensure_ascii=False, indent=2)

print(f"\n✅ 完成: 成功{success}, 失败{failed}, 总计{len(all_synced)}")
