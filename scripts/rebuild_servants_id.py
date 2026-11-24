#!/usr/bin/env python3
"""Rebuild servant ID map + generate missing servant MD files.

默认：映射文件全量重建（必须包含全部条目），MD 仅生成缺失项（增量）。
--full: 强制全量重新生成所有 MD（generate.py 模板/规则升级后使用）。
"""
import json, os, sys, glob, importlib.util

WIKI = os.path.expanduser("~/fgo-wiki")
RAW_DIR = os.path.join(WIKI, "raw/servants/CN")
ENTITY_DIR = os.path.join(WIKI, "entities/servants/CN")
DATA_DIR = os.path.join(WIKI, "data")
MAP_PATH = os.path.join(DATA_DIR, "servant_id_map.json")
os.makedirs(ENTITY_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

FULL = "--full" in sys.argv

# 手工维护名单（internalId）：这些从者不参与通用渲染，MD 全靠人工维护。
# 玛修(No.1/800100)：技能组与宝具按战斗形象(灵衣)整套切换，Atlas 数据结构无法可靠推导。
MANUAL_SERVANTS = {800100}

# Load generate module
sys.path.insert(0, WIKI)
spec = importlib.util.spec_from_file_location("generate", os.path.join(WIKI, "generate.py"))
gen_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen_mod)
generate = gen_mod.generate

raw_files = sorted(glob.glob(os.path.join(RAW_DIR, "*.json")))
print(f"找到 {len(raw_files)} 个原始JSON文件")

# Build ID map + regenerate missing MD
id_map = {}
count = 0
skipped = 0
errors = []

for fp in raw_files:
    sid = os.path.basename(fp).replace(".json", "")
    with open(fp, encoding="utf-8") as f:
        data = json.load(f)

    # Save mapping（映射必须全量）
    name = data.get("name", "?")
    cno = data.get("collectionNo", "?")
    cls = data.get("className", "?")
    sid_int = data.get("id", sid)
    id_map[str(sid_int)] = {"name": name, "collectionNo": cno, "className": cls}

    # Generate MD with ID-based filename（默认增量，只补缺失）
    out_path = os.path.join(ENTITY_DIR, f"{sid_int}.md")
    # 手工维护名单：这些从者不参与通用渲染（MD 全靠人工维护）
    if sid_int in MANUAL_SERVANTS:
        skipped += 1
        continue
    if not FULL and os.path.exists(out_path):
        skipped += 1
        continue
    try:
        md = generate(data)
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

print(f"\n✅ 生成完成: 新增/更新 {count} 个MD文件 (ID命名)" + (f"，跳过已有 {skipped} 个" if skipped else ""))
print(f"✅ 映射文件: {MAP_PATH} ({len(id_map)} 条目)")
if errors:
    print(f"⚠  {len(errors)} 个错误:")
    for e in errors[:10]:
        print(f"  - {e}")
