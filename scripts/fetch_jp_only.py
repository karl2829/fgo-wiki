#!/usr/bin/env python3
"""Fetch JP-only servants not in CN, 0.5s interval, resumable."""
import json, urllib.request, time, os, glob

home = os.path.expanduser("~/fgo-wiki")
raw_dir = os.path.join(home, "raw/servants/JP")
os.makedirs(raw_dir, exist_ok=True)

# Load ID lists
jp = json.load(open("/tmp/jp_basic_servant.json"))
cn = json.load(open("/tmp/basic_servant.json"))
jp_ids = set(s["id"] for s in jp)
cn_ids = set(s["id"] for s in cn)
jp_only = sorted(jp_ids - cn_ids)
jp_map = {s["id"]: s for s in jp}

# Check already fetched on disk
disk_ids = set()
for fp in glob.glob(os.path.join(raw_dir, "*.json")):
    try: disk_ids.add(int(os.path.basename(fp).replace(".json","")))
    except: pass

remaining = [sid for sid in jp_only if sid not in disk_ids]
print(f"JP-only total: {len(jp_only)}")
print(f"Already fetched: {len(disk_ids)}")
print(f"Remaining: {len(remaining)}")

if not remaining:
    print("All done!")
    exit(0)

success = 0
for i, sid in enumerate(remaining):
    s = jp_map[sid]
    cno = s.get("collectionNo", "?")
    name = s.get("name", "?")
    path = os.path.join(raw_dir, f"{sid}.json")
    url = f"https://api.atlasacademy.io/nice/JP/servant/{sid}?lore=true"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "hermes-agent"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  [{i+1}/{len(remaining)}] {sid} #{cno} {name} ✅")
        success += 1
    except Exception as e:
        print(f"  [{i+1}/{len(remaining)}] {sid} #{cno} {name} → {e}")
    if i < len(remaining) - 1:
        time.sleep(0.5)

print(f"\nDone: {success}/{len(remaining)}")
