#!/usr/bin/env python3
"""Regenerate all servant MD files with ID-based naming + create mapping."""
import json, os, sys, glob, importlib.util

WIKI = os.path.expanduser("~/fgo-wiki")
RAW_DIR = os.path.join(WIKI, "raw/servants/CN")
ENTITY_DIR = os.path.join(WIKI, "entities/servants/CN")
DATA_DIR = os.path.join(WIKI, "data")
MAP_PATH = os.path.join(DATA_DIR, "servant_id_map.json")
os.makedirs(ENTITY_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Load generate module
sys.path.insert(0, WIKI)
spec = importlib.util.spec_from_file_location("generate", os.path.join(WIKI, "generate.py"))
gen_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen_mod)
generate = gen_mod.generate

raw_files = sorted(glob.glob(os.path.join(RAW_DIR, "*.json")))
print(f"找到 {len(raw_files)} 个原始JSON文件")

# Build ID map + regenerate
id_map = {}
count = 0
errors = []

for fp in raw_files:
    sid = os.path.basename(fp).replace(".json", "")
    with open(fp, encoding="utf-8") as f:
        data = json.load(f)
    
    # Save mapping
    name = data.get("name", "?")
    cno = data.get("collectionNo", "?")
    cls = data.get("className", "?")
    sid_int = data.get("id", sid)
    id_map[str(sid_int)] = {"name": name, "collectionNo": cno, "className": cls}
    
    # Generate MD with ID-based filename
    try:
        md = generate(data)
        out_path = os.path.join(ENTITY_DIR, f"{sid_int}.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)
        count += 1
        if count % 100 == 0:
            print(f"  [{count}/{len(raw_files)}] ...")
    except Exception as e:
        errors.append(f"#{cno} {name} (id={sid_int}): {e}")

# Write mapping
with open(MAP_PATH, "w", encoding="utf-8") as f:
    json.dump(id_map, f, ensure_ascii=False, indent=2)

print(f"\n✅ 生成完成: {count} 个MD文件 (ID命名)")
print(f"✅ 映射文件: {MAP_PATH} ({len(id_map)} 条目)")
if errors:
    print(f"⚠  {len(errors)} 个错误:")
    for e in errors[:10]:
        print(f"  - {e}")
