#!/usr/bin/env python3
"""Incremental gacha sync from Mooncell.

Usage:
  python3 scripts/fetch_mooncell_gacha.py              # 增量更新
  python3 scripts/fetch_mooncell_gacha.py --full        # 全量重拉（慎用）

流程：
  1. 读取 raw/gacha/gacha_raw.json 中的 last_sync_at
  2. 从 Mooncell 卡池一览页抓取当前 + 未来卡池
  3. 跳过已有 ID 的卡池，只新增不存在的
  4. 更新 last_sync_at
"""
import json, os, re, sys, glob
from datetime import datetime, timezone
from urllib.parse import quote, unquote

WIKI = os.path.expanduser("~/fgo-wiki")
RAW_DIR = os.path.join(WIKI, "raw/gacha")
ENT_DIR = os.path.join(WIKI, "entities/gacha")
DATA_DIR = os.path.join(WIKI, "data")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(ENT_DIR, exist_ok=True)

RAW_GACHA = os.path.join(RAW_DIR, "gacha_raw.json")
MOONCELL = "https://fgo.wiki"

# --- 工具函数 ---

def load_raw():
    if os.path.exists(RAW_GACHA):
        return json.load(open(RAW_GACHA))
    return {"last_sync_at": "", "_meta": {"source": "Mooncell"}, "gachas": {}}

def save_raw(raw):
    raw["last_sync_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    json.dump(raw, open(RAW_GACHA, "w"), ensure_ascii=False, indent=2)

def make_gacha_id(start, name):
    ds = start.replace("-", "")[:8] if start else ""
    short = re.sub(r'[「」『』""【】《》<>（），。！？\s]', '', name)[:25]
    short = re.sub(r'[\\/:*?"<>|]', '_', short)
    return f"{ds}_{short}" if ds else f"gacha_{short}"

def extract_sids(text):
    return sorted(set(int(m) for m in re.findall(r'Servant0*(\d+)\.(?:jpg|png)', text)))

def extract_cids(text):
    return sorted(set(int(m) for m in re.findall(r'礼装0*(\d+)\.jpg', text)))

def fetch_mooncell(url):
    """Fetch a Mooncell page and return text. Uses urllib for reliability."""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "fgo-wiki/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="ignore")

# --- 解析函数 ---

def parse_main_page(html, region="CN"):
    """Parse 卡池一览 main page for current + future pools."""
    gachas = []
    section = ""
    for line in html.split("\n"):
        l = line.strip()
        if "国服当前卡池" in l and "|" in l: section = "CN_current"
        elif "日服当前卡池" in l and "|" in l: section = "JP_current"
        elif "国服近未来卡池" in l and "|" in l: section = "CN_future"
        
        if not l.startswith("| [") or "|---" in l: continue
        cell = l.split("|")
        if len(cell) < 2: continue
        
        # Get gacha name from links
        names = re.findall(r'\[([^\]]+)\]\([^)]+\)', cell[0] + "|" + cell[1])
        name = ""
        for n in names:
            if "推荐召唤" in n or "福袋" in n or "召唤" in n or len(n) > 5:
                name = n
        if not name or "推荐召唤从者数" in name or "推荐召唤礼装数" in name:
            continue
        
        # Deduplicate
        if any(g.get("name") == name for g in gachas): continue
        
        # Extract dates
        time_text = cell[2] if len(cell) > 2 else ""
        cn_dates = re.findall(r'(\d{4})年(\d+)月(\d+)日', time_text)
        start, end = "", ""
        if cn_dates:
            start = f"{cn_dates[0][0]}-{cn_dates[0][1].zfill(2)}-{cn_dates[0][2].zfill(2)}"
            end = f"{cn_dates[-1][0]}-{cn_dates[-1][1].zfill(2)}-{cn_dates[-1][2].zfill(2)}"
        
        svt_ids = extract_sids(cell[3] if len(cell) > 3 else "" + l)
        ce_ids = extract_cids(cell[4] if len(cell) > 4 else "" + l)
        
        status = "当前" if "current" in section else "未来"
        rgn = "CN" if "CN_" in section else "JP"
        gtype = "福袋召唤" if "福袋" in name else "推荐召唤"
        
        gachas.append({
            "id": make_gacha_id(start, name),
            "name": name, "type": gtype, "status": status,
            "region": rgn, "start_date": start, "end_date": end,
            "servant_ids": svt_ids, "ce_ids": ce_ids,
        })
    return gachas

# --- 主流程 ---

def run_incremental():
    raw = load_raw()
    existing = set(raw["gachas"].keys())
    new_count = 0
    
    print(f"当前数据库: {len(existing)} 个卡池")
    print(f"上次同步: {raw.get('last_sync_at', '从未')}")
    
    # 1. Fetch main page
    print("\n拉取卡池一览页...")
    main_html = fetch_mooncell(f"{MOONCELL}/w/%E5%8D%A1%E6%B1%A0%E4%B8%80%E8%A7%88")
    
    new_gachas = parse_main_page(main_html)
    for g in new_gachas:
        if g["id"] not in existing:
            raw["gachas"][g["id"]] = g
            existing.add(g["id"])
            new_count += 1
            print(f"  + {g['id']}: {g['name'][:40]}")
    
    # 2. Check ended pools yearly pages (current year only for incremental)
    # Only check if the previous sync was more than 1 day ago
    if raw.get("last_sync_at"):
        last_time = datetime.fromisoformat(raw["last_sync_at"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days_diff = (now - last_time).days
        
        if days_diff >= 1:
            print(f"\n距上次同步已 {days_diff} 天，检查已结束页面...")
            current_year = now.year
            for year in range(max(2016, current_year - 1), current_year + 1):
                try:
                    yr_html = fetch_mooncell(
                        f"{MOONCELL}/w/%E5%8D%A1%E6%B1%A0%E4%B8%80%E8%A7%88/%E5%B7%B2%E7%BB%93%E6%9D%9F%E5%8D%A1%E6%B1%A0/{year}"
                    )
                    # Convert HTML to markdown-like lines
                    lines = []
                    for m in re.finditer(r'<tr[^>]*>(.*?)</tr>', yr_html, re.DOTALL):
                        cells = re.findall(r'<td[^>]*>(.*?)</td>', m.group(1), re.DOTALL)
                        if cells:
                            row = "|"
                            for c in cells:
                                c = re.sub(r'<img[^>]*src="([^"]+)"[^>]*>', r'![](\1)', c)
                                c = re.sub(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r'[\2](\1)', c)
                                c = re.sub(r'<[^>]+>', '', c)
                                row += f" {c.replace(chr(10), '<br>')} |"
                            lines.append(row)
                    
                    # Parse like normal
                    section = "CN_ended"
                    for line in lines:
                        l = line.strip()
                        if not l.startswith("| [!") or "|---" in l: continue
                        cell = l.split("|")
                        if len(cell) < 2: continue
                        
                        names = re.findall(r'\[([^\]]+)\]\([^)]+\)', cell[0] + "|" + cell[1])
                        name = ""
                        for n in names:
                            if "推荐召唤" in n or "福袋" in n or "召唤" in n or len(n) > 5:
                                name = n
                        if not name or "推荐召唤从者数" in name: continue
                        
                        time_text = cell[2] if len(cell) > 2 else ""
                        cn_dates = re.findall(r'(\d{4})年(\d+)月(\d+)日', time_text)
                        start, end = "", ""
                        if cn_dates:
                            start = f"{cn_dates[0][0]}-{cn_dates[0][1].zfill(2)}-{cn_dates[0][2].zfill(2)}"
                            end = f"{cn_dates[-1][0]}-{cn_dates[-1][1].zfill(2)}-{cn_dates[-1][2].zfill(2)}"
                        
                        gid = make_gacha_id(start, name)
                        if gid not in existing:
                            svt_ids = extract_sids(cell[3] + l if len(cell) > 3 else "")
                            ce_ids = extract_cids(cell[4] + l if len(cell) > 4 else "")
                            raw["gachas"][gid] = {
                                "id": gid, "name": name, "type": "福袋召唤" if "福袋" in name else "推荐召唤",
                                "status": "已结束", "region": "CN",
                                "start_date": start, "end_date": end,
                                "servant_ids": svt_ids, "ce_ids": ce_ids,
                            }
                            existing.add(gid)
                            new_count += 1
                            print(f"  + [{year}] {gid}: {name[:40]}")
                    
                    import time
                    time.sleep(0.5)
                except:
                    print(f"  - {year}: 跳过（不可用）")
    
    # Save
    save_raw(raw)
    print(f"\n✅ 增量更新完成: 新增 {new_count} 个卡池")
    print(f"   当前总计: {len(existing)} 个卡池")
    print(f"   同步时间: {raw['last_sync_at']}")
    
    # Update summary (regenerate expired_gacha.md)
    update_summary()

def update_summary():
    """Regenerate expired_gacha.md and index.md."""
    raw = load_raw()
    all_g = raw["gachas"]
    expired = {gid: g for gid, g in all_g.items() if g.get("status") == "已结束"}
    current = {gid: g for gid, g in all_g.items() if g.get("status") != "已结束"}
    
    # Load mappings
    from collections import defaultdict
    svt_by_cno = {}
    for region in ["CN", "JP"]:
        for fp in glob.glob(os.path.join(WIKI, f"raw/servants/{region}/*.json")):
            with open(fp) as f:
                d = json.load(f)
            cno = d.get("collectionNo")
            if cno: svt_by_cno[cno] = {"name": d.get("name","?"), "class": d.get("className","?"), "rarity": d.get("rarity",0)}
    
    ce_info = {}
    basic = json.load(open("/tmp/cn_basic_equip.json"))
    for ce in basic: ce_info[ce["id"]] = ce.get("name", f"#{ce['id']}")
    
    # Servant stats
    svt_up = defaultdict(lambda: {"count": 0, "last_up": "", "pools": []})
    for gid, g in expired.items():
        for sid in g.get("servant_ids", []):
            info = svt_by_cno.get(sid)
            name = info["name"] if info else f"#{sid}"
            svt_up[sid]["name"] = name
            svt_up[sid]["count"] += 1
            start = g.get("start_date","")
            if start > svt_up[sid]["last_up"]: svt_up[sid]["last_up"] = start
            svt_up[sid]["pools"].append({"name": g.get("name","?"), "start": start, "end": g.get("end_date",""), "type": g.get("type","推荐召唤")})
    sorted_svt = sorted(svt_up.values(), key=lambda x: (-x["count"], x["name"]))
    
    # CE
    from collections import defaultdict as dd
    ce_up = dd(list)
    for gid, g in expired.items():
        for cid in g.get("ce_ids", []):
            name = ce_info.get(cid, f"#{cid}")
            ce_up[name].append({"pool": g.get("name","?"), "start": g.get("start_date",""), "end": g.get("end_date","")})
    
    # Yearly
    yearly = defaultdict(int)
    for gid, g in expired.items():
        y = g.get("start_date","")[:4]
        if y: yearly[y] += 1
    
    lines, h = [], lambda s="": lines.append(s)
    h("# 过期卡池汇总"); h()
    h(f"**数据更新时间**: {raw.get('last_sync_at','?')} | **过期卡池总数**: {len(expired)}"); h()
    h("## 从者 UP 次数统计"); h("| 从者 | UP 次数 | 最近一次 UP |\n|---|---|---|")
    for s in sorted_svt: h(f"| {s['name']} | {s['count']} | {s['last_up']} |")
    h(); h("## 从者 UP 历史明细"); h("| 从者 | 卡池 | 类型 | 开始 | 结束 |\n|---|---|---|---|---|")
    for s in sorted_svt:
        for p in sorted(s["pools"], key=lambda x: x["start"], reverse=True):
            h(f"| {s['name']} | {p['name'][:40]} | {p.get('type','?')} | {p['start']} | {p['end']} |")
    h(); h("## 礼装 UP 历史"); h("| 礼装 | 卡池 | 开始 | 结束 |\n|---|---|---|---|")
    for cname, pools in sorted(ce_up.items()):
        for p in sorted(pools, key=lambda x: x["start"], reverse=True):
            h(f"| {cname} | {p['pool'][:40]} | {p['start']} | {p['end']} |")
    h(); h("## 按年份统计"); h("| 年份 | 卡池数量 |\n|---|---|")
    for year in sorted(yearly.keys(), reverse=True): h(f"| {year} | {yearly[year]} |")
    h(); h("---"); h("*数据来源: Mooncell* | *遵循 CC BY-NC-SA 4.0 协议*")
    
    with open(os.path.join(ENT_DIR, "expired_gacha.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    # Index
    idx = ["# 卡池索引", "", "| ID | 名称 | 类型 | 区服 | 开始 | 结束 | 状态 |", "|---|---|---|---|---|---|---|"]
    for g in sorted(current.values(), key=lambda x: x.get("start_date",""), reverse=True):
        idx.append(f"| [{g['id']}]({g['id']}.md) | {g.get('name','?')[:35]} | {g.get('type','?')} | {g.get('region','?')} | {g.get('start_date','?')} | {g.get('end_date','?')} | {g.get('status','?')} |")
    idx.append(""); idx.append(f"> [过期卡池汇总 →](expired_gacha.md)（共 {len(expired)} 个）")
    with open(os.path.join(ENT_DIR, "index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(idx))
    
    print(f"   过期汇总: {len(lines)} 行, 索引: {len(current)} 条目")

if __name__ == "__main__":
    if "--full" in sys.argv:
        # Full refresh - for development only
        print("⚠️ 全量模式: 从零开始拉取所有数据（慎用）")
        confirm = input("确认? (yes/no): ")
        if confirm == "yes":
            import shutil
            if os.path.exists(RAW_GACHA):
                os.remove(RAW_GACHA)
            run_incremental()
        sys.exit(0)
    
    run_incremental()
