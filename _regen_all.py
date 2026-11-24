"""全量重生成 CN 从者 MD（跳过手工维护名单），备份旧文件并统计变更。"""
import json, os, sys, glob, importlib.util, shutil

WIKI = os.path.expanduser("~/fgo-wiki")
RAW = os.path.join(WIKI, "raw/servants/CN")
ENT = os.path.join(WIKI, "entities/servants/CN")
BACKUP = "/tmp/md_backup_2"

MANUAL = {800100}

sys.path.insert(0, WIKI)
spec = importlib.util.spec_from_file_location("generate", os.path.join(WIKI, "generate.py"))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

os.makedirs(BACKUP, exist_ok=True)
changed, failed, skipped, same = [], [], 0, 0

for fp in sorted(glob.glob(os.path.join(RAW, "*.json"))):
    d = json.load(open(fp, encoding="utf-8"))
    sid = d.get("id")
    if sid in MANUAL:
        skipped += 1
        continue
    out = os.path.join(ENT, f"{sid}.md")
    old = open(out, encoding="utf-8").read() if os.path.exists(out) else None
    try:
        md = g.generate(d)
    except Exception as e:
        failed.append((d.get("collectionNo"), d.get("name"), str(e)))
        continue
    if old == md:
        same += 1
        continue
    if old is not None:
        shutil.copy2(out, os.path.join(BACKUP, f"{sid}.md"))
    open(out, "w", encoding="utf-8").write(md)
    changed.append((d.get("collectionNo"), d.get("name"), sid))

print(f"变更: {len(changed)}  无变化: {same}  跳过(手工): {skipped}  失败: {len(failed)}")
for c, n, s in changed:
    print(f"  No.{c} {n} ({s})")
if failed:
    for x in failed:
        print("  FAIL", x)
