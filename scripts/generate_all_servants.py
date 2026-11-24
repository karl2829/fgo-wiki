#!/usr/bin/env python3
"""Generate servant MD files from raw JSON data.

默认增量：只生成 entities/servants/CN/ 中缺失的 MD（新拉取的从者）。
--full: 强制全量重新生成（generate.py 模板/规则升级后使用）。
"""
import json, os, sys, glob, importlib.util

WIKI = os.path.expanduser("~/fgo-wiki")
RAW_DIR = os.path.join(WIKI, "raw/servants/CN")
ENTITY_DIR = os.path.join(WIKI, "entities/servants/CN")
os.makedirs(ENTITY_DIR, exist_ok=True)

FULL = "--full" in sys.argv

# 手工维护名单（internalId）：不参与通用渲染，MD 全靠人工维护。
# 玛修(No.1/800100)：技能组与宝具按战斗形象(灵衣)整套切换，Atlas 数据无法可靠推导。
MANUAL_SERVANTS = {800100}

sys.path.insert(0, WIKI)
spec = importlib.util.spec_from_file_location("generate", os.path.join(WIKI, "generate.py"))
gen_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen_mod)
generate = gen_mod.generate

raw_files = sorted(glob.glob(os.path.join(RAW_DIR, "*.json")))
print(f"找到 {len(raw_files)} 个原始JSON文件")

# 已有 MD 文件（ID 命名）
existing = set()
for fp in glob.glob(os.path.join(ENTITY_DIR, "*.md")):
    existing.add(os.path.basename(fp).replace(".md", ""))
print(f"已有 {len(existing)} 个MD文件" + ("" if FULL else "，仅生成缺失项"))

count = 0
skipped = 0
errors = []

for fp in raw_files:
    sid = os.path.basename(fp).replace(".json", "")
    with open(fp, encoding="utf-8") as f:
        data = json.load(f)
    entity_id = str(data.get("id", sid))
    out_path = os.path.join(ENTITY_DIR, f"{entity_id}.md")
    if entity_id.isdigit() and int(entity_id) in MANUAL_SERVANTS:
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
        if count % 50 == 0:
            cno = data.get("collectionNo", "?")
            name = data.get("name", "?")
            print(f"  [{count}/{len(raw_files)}] #{cno} {name}")
    except Exception as e:
        cno = data.get("collectionNo", sid)
        name = data.get("name", "?")
        errors.append(f"#{cno} {name}: {e}")

print(f"\n✅ 生成完成: 新增/更新 {count} 个MD文件" + (f"，跳过已有 {skipped} 个" if skipped else ""))
if errors:
    print(f"⚠  {len(errors)} 个错误:")
    for e in errors[:10]:
        print(f"  - {e}")
