#!/usr/bin/env python3
"""Generate all servant MD files from raw JSON data."""
import json, os, sys, glob, importlib.util

WIKI = os.path.expanduser("~/fgo-wiki")
RAW_DIR = os.path.join(WIKI, "raw/servants/CN")
ENTITY_DIR = os.path.join(WIKI, "entities/servants/CN")
os.makedirs(ENTITY_DIR, exist_ok=True)

sys.path.insert(0, WIKI)
spec = importlib.util.spec_from_file_location("generate", os.path.join(WIKI, "generate.py"))
gen_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen_mod)
generate = gen_mod.generate

raw_files = sorted(glob.glob(os.path.join(RAW_DIR, "*.json")))
print(f"找到 {len(raw_files)} 个原始JSON文件")

count = 0
errors = []

for fp in raw_files:
    sid = os.path.basename(fp).replace(".json", "")
    with open(fp, encoding="utf-8") as f:
        data = json.load(f)
    try:
        md = generate(data)
        entity_id = data.get("id", sid)
        out_path = os.path.join(ENTITY_DIR, f"{entity_id}.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)
        count += 1
        if count % 50 == 0:
            cno = data.get("collectionNo", "?")
            name = data.get("name", "?")
            print(f"  [{count}/{len(raw_files)}] #{cno} {name}")
    except Exception as e:
        cno = data.get("collectionNo", sid)
        name = data.get("name", "?")
        errors.append(f"#{cno} {name}: {e}")

print(f"\n✅ 生成完成: {count} 个MD文件")
if errors:
    print(f"⚠  {len(errors)} 个错误:")
    for e in errors[:10]:
        print(f"  - {e}")
