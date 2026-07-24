#!/usr/bin/env python3
"""Fetch FGO gacha data from Mooncell and generate MD files."""
import json, os, sys, re, urllib.request, time, glob
from datetime import datetime, timezone
from urllib.parse import unquote

WIKI = os.path.expanduser("~/fgo-wiki")
RAW_DIR = os.path.join(WIKI, "raw/gacha")
ENT_DIR = os.path.join(WIKI, "entities/gacha")
DATA_DIR = os.path.join(WIKI, "data")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(ENT_DIR, exist_ok=True)

MOONCELL = "https://fgo.wiki"
HEADERS = {"User-Agent": "hermes-agent/1.0"}

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")

def extract_servants(html):
    """Extract servant IDs from a page's content."""
    ids = set()
    for m in re.findall(r'Servant_(\d+)\.png', html):
        ids.add(int(m))
    return sorted(ids)

def extract_ces(html):
    """Extract CE IDs from a page's content."""
    ids = set()
    for m in re.findall(r'礼装(\d+)\.jpg', html):
        ids.add(int(m))
    return sorted(ids)

def extract_times(html):
    """Extract start and end dates from page HTML."""
    times = re.findall(r'(\d{4})年(\d+)月(\d+)日.*?(\d{4})年(\d+)月(\d+)日', html)
    if times:
        t = times[0]
        return f"{t[0]}-{t[1].zfill(2)}-{t[2].zfill(2)}", f"{t[3]}-{t[4].zfill(2)}-{t[5].zfill(2)}"
    # Try HH:MM format
    times2 = re.findall(r'(\d{4})年(\d+)月(\d+)日\(.*?\)\s*(\d+):(\d+)', html)
    if times2:
        t = times2[0]
        return f"{t[0]}-{t[1].zfill(2)}-{t[2].zfill(2)}", ""
    return "", ""

def get_gacha_type(name):
    if "福袋" in name:
        return "福袋召唤"
    elif "推荐召唤" in name:
        return "推荐召唤"
    elif "故事" in name:
        return "故事卡池"
    elif "召唤" in name:
        return "限时召唤"
    else:
        return "卡池"

def generate_md(gacha):
    lines, h = [], lambda s="": lines.append(s)
    gacha_id = gacha["id"]
    name = gacha["name"]
    h(f"# {name}")
    h()
    h(f"> **ID**: {gacha_id} | **类型**: {gacha['type']} | **状态**: {gacha.get('status', '?')}")
    h()
    h("## 时间")
    h()
    h("| 项目 | 时间 |")
    h("|------|------|")
    h(f"| 开始 | {gacha.get('start_date', '?')} |")
    h(f"| 结束 | {gacha.get('end_date', '?')} |")
    h()
    if gacha.get("banner"):
        h("## 卡池图片")
        h(f"![卡池横幅]({gacha['banner']})")
        h()
    if gacha.get("servant_ids"):
        h("## UP 从者")
        h()
        h("| 从者 |")
        h("|---|")
        for sid in gacha["servant_ids"]:
            h(f"| [[{sid}|#{sid}]] |")
        h()
    if gacha.get("ce_ids"):
        h("## UP 礼装")
        h()
        h("| 礼装 |")
        h("|---|")
        for cid in gacha["ce_ids"]:
            h(f"| [[{cid}|#{cid}]] |")
        h()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    h("---")
    h(f"*数据来源: Mooncell* | *最后更新: {today}*")
    return "\n".join(lines)

if __name__ == "__main__":
    print("=== 从Mooncell爬取卡池数据 ===")
    html = fetch(f"{MOONCELL}/w/%E5%8D%A1%E6%B1%A0%E4%B8%80%E8%A7%88")
    
    # Find all gacha links
    gacha_links = re.findall(
        r'href="(/w/(?:%[0-9A-Fa-f]{2}|[^"])*(?:推荐召唤|召唤|福袋|卡池)[^"]*)"[^>]*>([^<]*)</a>',
        html
    )
    
    seen_names = set()
    gachas = []
    for link, name in gacha_links:
        name = name.strip()
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        
        gacha_url = f"{MOONCELL}{link}"
        gacha = {
            "name": name,
            "url": gacha_url,
            "type": get_gacha_type(name),
            "start_date": "",
            "end_date": "",
            "banner": "",
            "servant_ids": [],
            "ce_ids": [],
        }
        
        # Determine status from table context
        if "当前卡池" in html[:html.find(link)][-500:]:
            gacha["status"] = "当前"
        elif "近未来卡池" in html[:html.find(link)][-500:]:
            gacha["status"] = "未来"
        else:
            gacha["status"] = "已结束"
        
        gachas.append(gacha)
    
    print(f"找到 {len(gachas)} 个卡池")
    
    # Fetch details for each gacha
    for i, gacha in enumerate(gachas):
        try:
            page_html = fetch(gacha["url"])
            
            # Times
            st, et = extract_times(page_html)
            gacha["start_date"] = st
            gacha["end_date"] = et
            
            # Banner
            bm = re.search(r'<img[^>]*src="([^"]*banner[^"]*\.png)"', page_html, re.IGNORECASE)
            if bm:
                gacha["banner"] = bm.group(1)
            
            # Servants & CE
            gacha["servant_ids"] = extract_servants(page_html)
            gacha["ce_ids"] = extract_ces(page_html)
        except Exception as e:
            print(f"  [{i+1}/{len(gachas)}] {gacha['name'][:30]} → fetch error: {e}")
        
        # Assign ID and save
        gacha["id"] = f"gacha_{i+1:04d}"
        
        raw_path = os.path.join(RAW_DIR, f"{gacha['id']}.json")
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(gacha, f, ensure_ascii=False, indent=2)
        
        md = generate_md(gacha)
        with open(os.path.join(ENT_DIR, f"{gacha['id']}.md"), "w", encoding="utf-8") as f:
            f.write(md)
        
        if (i + 1) % 5 == 0:
            print(f"  [{i+1}/{len(gachas)}] ...")
        
        time.sleep(0.5)
    
    # Index
    lines = ["# 卡池索引", "", "| ID | 名称 | 类型 | 开始 | 结束 | 状态 |", "|---|---|---|---|---|---|"]
    for g in sorted(gachas, key=lambda x: x.get("start_date", ""), reverse=True):
        gid = g["id"]
        name = g["name"][:40]
        lines.append(f"| [{gid}]({gid}.md) | {name} | {g['type']} | {g.get('start_date','?')} | {g.get('end_date','?')} | {g.get('status','?')} |")
    with open(os.path.join(ENT_DIR, "index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    # Servant → gacha mapping
    svt_map = {}
    for g in gachas:
        for sid in g.get("servant_ids", []):
            svt_map.setdefault(sid, []).append({"gacha_id": g["id"], "name": g["name"], "start_date": g.get("start_date",""), "end_date": g.get("end_date","")})
    with open(os.path.join(DATA_DIR, "gacha_mapping.json"), "w", encoding="utf-8") as f:
        json.dump(svt_map, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 完成: {len(gachas)} 个卡池")
    print(f"   mapping: {len(svt_map)} servants mapped")
