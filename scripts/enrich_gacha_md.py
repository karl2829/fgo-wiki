#!/usr/bin/env python3
"""enrich_gacha_md.py — 从 Mooncell 缓存页面补全卡池横幅（banner）到 gacha_raw.json。

只更新 raw 的 banner 字段，**不生成 MD**（MD 由 gen_gacha_md.py 统一生成）。
用法: python3 scripts/enrich_gacha_md.py
"""
import json
import os
import re
from urllib.parse import unquote

WIKI = os.path.expanduser("~/fgo-wiki")
RAW_GACHA = os.path.join(WIKI, "raw/gacha/gacha_raw.json")
CACHE = "/home/mila/.hermes/cache/web/fgo.wiki-8375a12bfb.md"

raw_gacha = json.load(open(RAW_GACHA))
if not os.path.exists(CACHE):
    print(f"⚠ 缓存页面不存在: {CACHE}")
    raise SystemExit(1)

html = open(CACHE).read()
all_images = re.findall(r'\[!\[[^\]]*\]\(([^)]+)\)\]\(https://fgo\.wiki/w/([^)]+)\)', html)
page_images = {}
for img_url, page_path in all_images:
    page_images[unquote(page_path)] = img_url

hits = 0
for gid, g in raw_gacha["gachas"].items():
    if g.get("banner") and "cdn.jsdelivr.net" in g["banner"]:
        continue
    name = g.get("name", "")
    banner = ""
    for page, img in page_images.items():
        for kw in name.split()[:5]:
            if len(kw) >= 3 and kw in page:
                banner = re.sub(r'/thumb(.*?)/\d+px-', r'\1/', img)
                if not banner.startswith("http"):
                    banner = "https://media.fgo.wiki" + banner
                banner = re.sub(r'(https?://media\.fgo\.wiki/[^/]+/[^/]+/[^?]+)/[^?]+(\?[^)]+)?', r'\1', banner)
                break
        if banner:
            break
    if banner:
        g["banner"] = banner
        hits += 1

json.dump(raw_gacha, open(RAW_GACHA, "w"), ensure_ascii=False, indent=2)
print(f"✅ 补全 banner {hits} 个（共 {len(raw_gacha['gachas'])} 卡池）")
print("提示: 新 banner 需手动上传 CDN（karl2829/fgo-images）后更新 gacha_raw 的 banner 字段")
