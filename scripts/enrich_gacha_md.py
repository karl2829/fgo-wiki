#!/usr/bin/env python3
"""Enrich gacha MD files with servant class/rarity and banner images."""
import json, os, re, glob
from urllib.parse import unquote

WIKI = os.path.expanduser("~/fgo-wiki")
ENT_DIR = os.path.join(WIKI, "entities/gacha")
RAW_GACHA = os.path.join(WIKI, "raw/gacha/gacha_raw.json")

# Load servant info - build BOTH by internal ID and collectionNo
svt_info = {}
svt_by_cno = {}
for region in ["CN", "JP"]:
    dir_path = os.path.join(WIKI, f"raw/servants/{region}")
    if os.path.exists(dir_path):
        for fp in glob.glob(os.path.join(dir_path, "*.json")):
            with open(fp) as f:
                d = json.load(f)
            svt_info[d["id"]] = {"name": d.get("name","?"), "class": d.get("className","?"), "rarity": d.get("rarity",0)}
            # Also map by collectionNo (Mooncell uses collectionNo in image filenames)
            cno = d.get("collectionNo")
            if cno:
                svt_by_cno[cno] = svt_info[d["id"]]

# Load CE info from basic list
basic_cn = json.load(open("/tmp/cn_basic_equip.json"))
ce_info = {}
for ce in basic_cn:
    ce_info[ce["id"]] = {"name": ce["name"], "rarity": ce.get("rarity",0)}

# Load cached Mooncell page for banners
with open("/home/karl/.hermes/cache/web/fgo.wiki-8375a12bfb.md") as f:
    html = f.read()

# Extract banner image URLs from the page
all_images = re.findall(r'\[!\[[^\]]*\]\(([^)]+)\)\]\(https://fgo\.wiki/w/([^)]+)\)', html)
page_images = {}
for img_url, page_path in all_images:
    page_name = unquote(page_path)
    page_images[page_name] = img_url

raw_gacha = json.load(open(RAW_GACHA))
updates = banner_hits = missing_svt = missing_ce = 0

for gid, gacha in raw_gacha["gachas"].items():
    md_path = os.path.join(ENT_DIR, f"{gid}.md")
    if not os.path.exists(md_path):
        continue
    
    name = gacha["name"]
    
    # Find banner - match by name in page URL
    banner = ""
    for page, img in page_images.items():
        # Match: if the gacha URL name appears in the page name
        for kw in name.split()[:5]:
            if len(kw) >= 3 and kw in page:
                # Get full size (remove thumb)
                banner = re.sub(r'/thumb(.*?)/\d+px-', r'\1/', img)
                if not banner.startswith("http"):
                    banner = "https://media.fgo.wiki" + banner
                break
        if banner:
            break
    
    if banner:
        banner_hits += 1
        gacha["banner"] = banner
    else:
        gacha["banner"] = ""
    
    # Build MD
    lines, h = [], lambda s="": lines.append(s)
    h(f"# {name}")
    h(f"> **ID**: {gid} | **类型**: {gacha['type']} | **状态**: {gacha['status']} | **区服**: {gacha.get('region','?')}")
    h("## 时间\n| 项目 | 时间 |\n|------|------|")
    h(f"| 开始 | {gacha.get('start_date','?')} |\n| 结束 | {gacha.get('end_date','?')} |")
    if banner:
        h("## 卡池图片\n" + f"![{name}]({banner})")
    if gacha.get("servant_ids"):
        h("## UP 从者\n| 从者 | 职阶 | 星级 |\n|---|---|---|")
        for sid in gacha["servant_ids"]:
            # Mooncell images use collectionNo, so try collectionNo mapping first
            info = svt_by_cno.get(sid) or svt_info.get(sid)
            if info:
                stars = "★" * info["rarity"]
                h(f"| [[{sid}|{info['name']}]] | {info['class']} | {stars} |")
            else:
                missing_svt += 1
                h(f"| [[{sid}|#{sid}]] | ? | ? |")
    if gacha.get("ce_ids"):
        h("## UP 礼装\n| 礼装 | 稀有度 |\n|---|---|")
        for cid in gacha["ce_ids"]:
            info = ce_info.get(cid)
            if info:
                h(f"| [[{cid}|{info['name']}]] | {'★'*info['rarity']} |")
            else:
                missing_ce += 1
                h(f"| [[{cid}|#{cid}]] | ? |")
    h("---\n*数据来源: Mooncell* | *遵循 CC BY-NC-SA 4.0 协议*")
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    updates += 1

json.dump(raw_gacha, open(RAW_GACHA, "w"), ensure_ascii=False, indent=2)

print(f"✅ 已更新 {updates} 个卡池MD")
print(f"   横幅匹配: {banner_hits}/{updates}")
print(f"   未能补全的: 从者 {missing_svt} 个, 礼装 {missing_ce} 个")

# Summary of what can't be done
print("\n=== 无法完成项汇总 ===")
print("1. 关联活动: 卡池一览页面不含活动ID映射, 需从活动页面或请求API")
print("2. gacha_event_mapping.json: 同上, 活动→卡池关联数据缺失")
print("3. 增量更新 _meta.last_sync_at: 当前脚本为一次性解析, 未实现时间戳判断")
print("4. 横幅部分未匹配: 页面URL名与卡池名不完全一致, 部分漏配")
