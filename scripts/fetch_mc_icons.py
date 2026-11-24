#!/usr/bin/env python3
"""从 Mooncell（fgo.wiki）抓魔术礼装官方图标。

用法：
    python3 fetch_mc_icons.py "魔术礼装·极地用迦勒底制服" "万圣节王室成员"

产出：
    ~/fgo-wiki/assets/ui/mooncell/<名字>.png
    ~/fgo-wiki/assets/ui/mooncell/index.json   {"<礼装名>": {"file": "...", "w": 150, "h": 150}}
规则：
    Mooncell 文件名不统一：有的带「魔术礼装·」前缀，有的把「真说」写作「真实」。
    先试直接标题，失败再用 list=search（namespace 6）兜底。
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request

API = "https://fgo.wiki/api.php"
OUT = os.path.expanduser("~/fgo-wiki/assets/ui/mooncell")
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 绕过本机代理


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (mila-fgo)"})
    with OPENER.open(req, timeout=30) as r:
        return r.read()


def api(params):
    q = urllib.parse.urlencode(params, safe="|")
    return json.loads(get(f"{API}?{q}&format=json").decode("utf-8"))


def imageinfo(titles):
    if not titles:
        return {}
    d = api({"action": "query", "titles": "|".join(titles),
             "prop": "imageinfo", "iiprop": "url|size"})
    res = {}
    for p in d.get("query", {}).get("pages", {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("url"):
            res[p["title"]] = ii
    return res


def variants(name):
    base = name.replace("魔术礼装·", "")
    alt = base.replace("真说", "真实")
    out = []
    for n in [name, base, alt, "魔术礼装·" + alt]:
        for suf in ["图标1.png", "图标2.png", "图标.png"]:
            out.append("文件:" + n + suf)
    return list(dict.fromkeys(out))


def resolve(name):
    info = imageinfo(variants(name))
    if info:
        return list(info.values())[0]
    base = name.replace("魔术礼装·", "")
    alt = base.replace("真说", "真实")
    for q_term in (base, alt, base[:6], alt[:6]):
        d = api({"action": "query", "list": "search", "srsearch": q_term,
                 "srnamespace": "6", "srlimit": "20"})
        titles = [s["title"] for s in d.get("query", {}).get("search", []) if "图标" in s["title"]]
        info = imageinfo(titles)
        if info:
            return list(info.values())[0]
    return None


def main():
    names = sys.argv[1:]
    if not names:
        raise SystemExit(__doc__)
    os.makedirs(OUT, exist_ok=True)
    idx_path = os.path.join(OUT, "index.json")
    idx = json.load(open(idx_path)) if os.path.exists(idx_path) else {}
    for name in names:
        if name in idx and os.path.exists(os.path.join(OUT, idx[name]["file"])):
            print(f"cached  {name}")
            continue
        ii = resolve(name)
        if not ii:
            print(f"MISS    {name}")
            continue
        fn = re.sub(r'[\\/:*?"<>|]', "_", name) + ".png"
        data = get(ii["url"])
        with open(os.path.join(OUT, fn), "wb") as f:
            f.write(data)
        idx[name] = {"file": fn, "w": ii["width"], "h": ii["height"], "src": ii["url"]}
        print(f"ok      {name}  {ii['width']}x{ii['height']}")
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
