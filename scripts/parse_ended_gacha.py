#!/usr/bin/env python3
"""Parse Mooncell ended gacha pages and generate MD files."""
import json, os, re, glob
from datetime import datetime, timezone

WIKI = os.path.expanduser("~/fgo-wiki")
ENT_DIR = os.path.join(WIKI, "entities/gacha")
RAW_DIR = os.path.join(WIKI, "raw/gacha")
DATA_DIR = os.path.join(WIKI, "data")
os.makedirs(ENT_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)

RAW_GACHA = os.path.join(RAW_DIR, "gacha_raw.json")

# Load existing raw gacha data
if os.path.exists(RAW_GACHA):
    raw_gacha = json.load(open(RAW_GACHA))
else:
    raw_gacha = {"last_sync_at": "", "_meta": {"source": "Mooncell"}, "gachas": {}}

# Load servant mapping (collectionNo → info)
svt_by_cno = {}
for region in ["CN", "JP"]:
    dir_path = os.path.join(WIKI, f"raw/servants/{region}")
    if os.path.exists(dir_path):
        for fp in glob.glob(os.path.join(dir_path, "*.json")):
            with open(fp) as f:
                d = json.load(f)
            cno = d.get("collectionNo")
            if cno:
                svt_by_cno[cno] = {
                    "name": d.get("name", "?"),
                    "class": d.get("className", "?"),
                    "rarity": d.get("rarity", 0)
                }

# Load CE info
ce_info = {}
basic_cn = json.load(open("/tmp/cn_basic_equip.json"))
for ce in basic_cn:
    ce_info[ce["id"]] = {"name": ce["name"], "rarity": ce.get("rarity", 0)}

def make_gacha_id(start, name):
    ds = start.replace("-", "")[:8] if start else ""
    short = re.sub(r'[「」『』""【】《》<>（），。！？\s]', '', name)[:25]
    short = re.sub(r'[\\/:*?"<>|]', '_', short)
    return f"{ds}_{short}" if ds else f"ended_{short}"

def extract_sids(text):
    return sorted(set(int(m) for m in re.findall(r'Servant_(\d+)\.png', text)))

def extract_cids(text):
    return sorted(set(int(m) for m in re.findall(r'礼装(\d+)\.jpg', text)))

def parse_ended_page(fp, year_label):
    """Parse an ended gacha page file."""
    with open(fp) as f:
        content = f.read()
    
    lines = content.split('\n')
    gachas = []
    
    for i, line in enumerate(lines):
        l = line.strip()
        if not l.startswith("| [") or "|---" in l:
            continue
        
        cell = l.split("|")
        if len(cell) < 2:
            continue
        
        first_cell = cell[0] + "|" + cell[1]
        names = re.findall(r'\[([^\]]+)\]\([^)]+\)', first_cell)
        
        name = ""
        for n in names:
            if "推荐召唤" in n or "福袋" in n or "召唤" in n or len(n) > 5:
                name = n
        
        if not name or "推荐召唤礼装数" in name or "推荐召唤从者数" in name:
            continue
        
        if any(g.get('name') == name for g in gachas):
            continue
        
        time_text = cell[2] if len(cell) > 2 else ""
        cn_dates = re.findall(r'(\d{4})年(\d+)月(\d+)日', time_text)
        start, end = "", ""
        if cn_dates:
            start = f"{cn_dates[0][0]}-{cn_dates[0][1].zfill(2)}-{cn_dates[0][2].zfill(2)}"
            end = f"{cn_dates[-1][0]}-{cn_dates[-1][1].zfill(2)}-{cn_dates[-1][2].zfill(2)}"
        
        svt_cell = cell[3] if len(cell) > 3 else ""
        svt_ids = extract_sids(svt_cell + l)
        
        ce_cell = cell[4] if len(cell) > 4 else ""
        ce_ids = extract_cids(ce_cell + l)
        
        status = "已结束"
        gtype = "福袋召唤" if "福袋" in name else "推荐召唤"
        
        gid = make_gacha_id(start, name)
        
        gachas.append({
            "id": gid,
            "name": name,
            "type": gtype,
            "status": status,
            "region": "CN",
            "start_date": start,
            "end_date": end,
            "servant_ids": svt_ids,
            "ce_ids": ce_ids,
            "_year": year_label,
        })
    
    return gachas

def gen_md(g):
    lines, h = [], lambda s="": lines.append(s)
    h(f"# {g['name']}")
    h(f"> **ID**: {g['id']} | **类型**: {g['type']} | **状态**: {g['status']} | **区服**: {g.get('region','?')}")
    h("## 时间\n| 项目 | 时间 |\n|------|------|")
    h(f"| 开始 | {g.get('start_date','?')} |\n| 结束 | {g.get('end_date','?')} |")
    if g.get("servant_ids"):
        h("## UP 从者\n| 从者 | 职阶 | 星级 |\n|---|---|---|")
        for sid in g["servant_ids"]:
            info = svt_by_cno.get(sid)
            if info:
                h(f"| [[{sid}|{info['name']}]] | {info['class']} | {'★'*info['rarity']} |")
            else:
                h(f"| [[{sid}|#{sid}]] | ? | ? |")
    if g.get("ce_ids"):
        h("## UP 礼装\n| 礼装 | 稀有度 |\n|---|---|")
        for cid in g["ce_ids"]:
            info = ce_info.get(cid)
            if info:
                h(f"| [[{cid}|{info['name']}]] | {'★'*info['rarity']} |")
            else:
                h(f"| [[{cid}|#{cid}]] | ? |")
    h("---\n*数据来源: Mooncell* | *遵循 CC BY-NC-SA 4.0 协议*")
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    files = sys.argv[1:] if len(sys.argv) > 1 else []
    
    if not files:
        print("Usage: python3 parse_ended_gacha.py <file1> [file2 ...]")
        print("Or: python3 parse_ended_gacha.py --all")
        sys.exit(1)
    
    all_new = []
    existing_count = len(raw_gacha["gachas"])
    
    for fp in files:
        year_label = os.path.basename(fp).replace("mooncell_ended_", "").replace(".md", "")
        new_gachas = parse_ended_page(fp, year_label)
        
        for g in new_gachas:
            gid = g["id"]
            if gid in raw_gacha["gachas"]:
                continue  # skip duplicate
            raw_gacha["gachas"][gid] = g
            all_new.append(g)
            
            # Generate MD
            md = gen_md(g)
            with open(os.path.join(ENT_DIR, f"{gid}.md"), "w", encoding="utf-8") as f:
                f.write(md)
        
        print(f"  {year_label}: {len(new_gachas)} 个 (新增{sum(1 for g in new_gachas if g['id'] not in raw_gacha['gachas'] or g['id'] not in [x['id'] for x in all_new])})")
    
    # Save updated raw
    raw_gacha["last_sync_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    json.dump(raw_gacha, open(RAW_GACHA, "w"), ensure_ascii=False, indent=2)
    
    # Rebuild index
    all_gachas = list(raw_gacha["gachas"].values())
    idx = ["# 卡池索引", "", "| ID | 名称 | 类型 | 区服 | 开始 | 结束 | 状态 |", "|---|---|---|---|---|---|---|"]
    for g in sorted(all_gachas, key=lambda x: x.get("start_date",""), reverse=True):
        idx.append(f"| [{g['id']}]({g['id']}.md) | {g.get('name','?')[:35]} | {g.get('type','?')} | {g.get('region','?')} | {g.get('start_date','?')} | {g.get('end_date','?')} | {g.get('status','?')} |")
    with open(os.path.join(ENT_DIR, "index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(idx))
    
    # Update mapping
    svt_map = {}
    for g in all_gachas:
        for sid in g.get("servant_ids", []):
            svt_map.setdefault(sid, []).append({"gacha_id": g["id"], "name": g.get("name","?"),
                "start_date": g.get("start_date",""), "end_date": g.get("end_date","")})
    with open(os.path.join(DATA_DIR, "gacha_mapping.json"), "w", encoding="utf-8") as f:
        json.dump(svt_map, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 总计: {len(raw_gacha['gachas'])} 个卡池 (原有{existing_count}, 新增{len(all_new)})")
    print(f"   index: {len(all_gachas)} entries")
    print(f"   mapping: {len(svt_map)} servants")
