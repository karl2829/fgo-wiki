#!/usr/bin/env python3
"""FGO 知识库更新：一键跑完整链路（CN 增量 + JP-only + MD 生成 + alias + 特性统计）

用法:
    python3 scripts/update_kb.py            # 全自动：拉取 + 生成 + 联动
    python3 scripts/update_kb.py --dry-run  # 只算差集，不拉不写

必须用装了 fgo_api_types 的 Python 跑：
    ~/.hermes/hermes-agent/.venv/bin/python3
"""
import json, os, sys, subprocess, urllib.request, importlib.util, glob

WIKI = os.path.expanduser("~/fgo-wiki")
PY = sys.executable
RAW = os.path.join(WIKI, "raw", "servants")
API = "https://api.atlasacademy.io/export/{srv}/basic_servant.json"


def fetch_json(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "fgo-wiki-updater"})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.loads(r.read().decode("utf-8"))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return data


def load_gen():
    spec = importlib.util.spec_from_file_location("gen", os.path.join(WIKI, "generate.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, WIKI)
    spec.loader.exec_module(mod)
    return mod


def run(cmd):
    print(f"$ {cmd}")
    p = subprocess.run(cmd, shell=True, cwd=WIKI, capture_output=True, text=True, timeout=600)
    out = (p.stdout or "") + (p.stderr or "")
    print("\n".join(out.strip().splitlines()[-8:]))
    if p.returncode != 0:
        print(f"❌ exit {p.returncode}")
    return p.returncode


def main():
    dry = "--dry-run" in sys.argv
    os.chdir(WIKI)

    print("== 1. 拉 Atlas basic 列表 ==")
    cn = fetch_json(API.format(srv="CN"), "/tmp/cn_basic.json")
    jp = fetch_json(API.format(srv="JP"), "/tmp/jp_basic.json")
    cn_ids = {s["id"] for s in cn}
    jp_ids = {s["id"] for s in jp}

    have_cn = {int(f[:-5]) for f in os.listdir(f"{RAW}/CN") if f.endswith(".json")}
    have_jp = {int(f[:-5]) for f in os.listdir(f"{RAW}/JP") if f.endswith(".json")}

    new_cn = sorted(cn_ids - have_cn)
    # 2026-11 规则变更：JP 从者全量存储（日文名/宝具名/技能名以日服为准），不再只存 JP-only
    new_jp = sorted(jp_ids - have_jp)
    cn_map = {s["id"]: s for s in cn}
    jp_map = {s["id"]: s for s in jp}

    print(f"CN: API {len(cn_ids)} / 本地 {len(have_cn)} / 新增 {len(new_cn)}")
    for i in new_cn:
        s = cn_map[i]
        print(f"  + #{s.get('collectionNo')} {s.get('name')} (id={i})")
    print(f"JP 待补全: {len(new_jp)}")
    for i in new_jp:
        s = jp_map[i]
        print(f"  + #{s.get('collectionNo')} {s.get('name')} (id={i})")

    if not new_cn and not new_jp:
        print("\n✅ 无新增，无需更新")
        return 0
    if dry:
        print("\n(dry-run，未写入)")
        return 0

    print("\n== 2. 拉 CN 从者数据 ==")
    if new_cn:
        run(f"{PY} scripts/fetch_servants.py --incremental")

    print("\n== 3. 拉 JP 从者数据（全量补全）==")
    if new_jp:
        run(f"{PY} scripts/fetch_jp_servants.py")

    print("\n== 4. 生成 CN 实体 MD（增量）==")
    run(f"{PY} scripts/rebuild_servants_id.py")

    print("\n== 5. 生成 JP 实体 MD（缺失即补，已有文件不覆盖）==")
    gen = load_gen()
    os.makedirs("entities/servants/JP", exist_ok=True)
    ok = fail = skip = 0
    for fp in sorted(glob.glob(f"{RAW}/JP/*.json")):
        sid = os.path.basename(fp)[:-5]
        out = f"entities/servants/JP/{sid}.md"
        if os.path.exists(out):                     # 保留人工修订（如中文名）的既有文件
            skip += 1
            continue
        try:
            md = gen.generate(json.load(open(fp, encoding="utf-8")))
            open(out, "w", encoding="utf-8").write(md)
            ok += 1
        except Exception as e:
            fail += 1
            print(f"  ❌ {sid}: {type(e).__name__}: {str(e)[:120]}")
    print(f"  JP 生成: 新建 {ok} / 跳过 {skip} / 失败 {fail}")

    print("\n== 6. 补 alias_map ==")
    am_path = "data/alias_map.json"
    am = json.load(open(am_path, encoding="utf-8"))
    added = []
    for sid in list(new_cn) + list(new_jp):
        s = cn_map.get(sid) or jp_map.get(sid)
        name = s.get("name")
        if name and name not in am:
            am[name] = {"id": str(sid), "name": name}
            added.append(name)
    if added:
        json.dump(am, open(am_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"  新增别名 {len(added)}: {added if added else '无'}")
    print("  ⚠ JP 从者中文名需人工补（Mooncell 英灵图鉴），补完改 raw.name + 重生成 + 再加 alias")

    print("\n== 7. 特性统计联动 ==")
    run(f"{PY} scripts/gen_trait_stats.py")

    print("\n== 8. 特攻一览联动 ==")
    run(f"{PY} scripts/gen_tokou_overview.py")

    print("\n== 9. 数量核对 ==")
    for srv in ("CN", "JP"):
        raw = len(glob.glob(f"{RAW}/{srv}/*.json"))
        md = len(glob.glob(f"entities/servants/{srv}/*.md"))
        flag = "✅" if raw == md else "❌ 不一致"
        print(f"  {srv}: raw {raw} / md {md} {flag}")

    print("\n✅ 完成。注意：git 提交需用户明确要求")
    return 0


if __name__ == "__main__":
    sys.exit(main())
