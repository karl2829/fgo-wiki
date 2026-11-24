import json, glob, re, os, sys
WIKI = "/home/mila/fgo-wiki"
sys.path.insert(0, WIKI)
import generate as gen

RAW = os.path.join(WIKI, "raw/servants/CN")
tot = 0
fail = []
for fp in glob.glob(os.path.join(RAW, "*.json")):
    d = json.load(open(fp, encoding="utf-8"))
    best = {}
    for s in d.get("skills", []):
        n = s.get("num", 0)
        p = s.get("priority", 1)
        if n not in best or p > best[n].get("priority", 1):
            best[n] = s
    for n, sk in sorted(best.items()):
        det = sk.get("detail") or ""
        if not det:
            continue
        if re.search(r"【[^】]*(?:再临形象|阶段形象|灵基)[^】]*】", det):
            continue
        tot += 1
        funcs = sk.get("functions", [])
        segs = [x.strip() for x in re.split(r"[＆&＋+]", det) if x.strip()]
        used = set()
        miss = []
        for seg in segs:
            fi = gen.match_func_to_segment(seg, funcs, used)
            if fi is None:
                miss.append(seg)
            else:
                used.add(fi)
        if miss:
            fail.append((d.get("collectionNo"), d.get("name"), sk["name"], miss, len(segs), len(funcs)))

print("单形态生效技能:", tot)
print("存在未匹配段的技能:", len(fail), f"{len(fail)/tot*100:.1f}%")
for f in fail[:20]:
    print("  ", f)
