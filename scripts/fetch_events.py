#!/usr/bin/env python3
"""Batch fetch & generate FGO event markdown files."""
import json, os, sys, glob, re
from datetime import datetime, timezone

WIKI = os.path.expanduser("~/fgo-wiki")
THRESHOLD_EVENT = 80549       # 因陀罗的大试炼
THRESHOLD_TIME = 1784008799   # 2026-07-14 05:59:59 UTC
REQUEST_DELAY = 0.5

RAW_BASE = os.path.join(WIKI, "raw/events")
ENT_BASE = os.path.join(WIKI, "entities/events")
DATA_DIR = os.path.join(WIKI, "data")

# ---------- Event Generation ----------
def generate_brief(ev):
    """Generate brief MD for events before threshold."""
    lines = []
    h = lambda s="": lines.append(s)
    eid = ev.get("id", "?")
    name = ev.get("name", "???")
    ev_type = ev.get("type", "")
    started = datetime.fromtimestamp(ev.get("startedAt", 0), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ended = datetime.fromtimestamp(ev.get("endedAt", 0), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    h(f"# {name}")
    h()
    h(f"> **ID**: {eid} | **类型**: {ev_type}")
    h()
    h("## 基础信息")
    h()
    h("| 属性 | 值 |")
    h("|------|-----|")
    h(f"| ID | {eid} |")
    h(f"| 名称 | {name} |")
    h(f"| 类型 | {ev_type} |")
    h(f"| 开始时间 | {started} |")
    h(f"| 结束时间 | {ended} |")
    h(f"| 状态 | **已结束（简略存档）** |")
    h()
    h("---")
    h(f"*数据来源: Atlas Academy API* | *最后更新: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}*")
    return "\n".join(lines)

def generate_full(ev_data):
    """Generate full MD for events at or after threshold."""
    lines = []
    h = lambda s="": lines.append(s)
    
    eid = ev_data.get("id", "?")
    name = ev_data.get("name", "???")
    short = ev_data.get("shortName", "")
    ev_type = ev_data.get("type", "")
    banner = ev_data.get("banner", "") or ev_data.get("noticeBanner", "")
    detail = ev_data.get("detail", "")
    started = datetime.fromtimestamp(ev_data.get("startedAt", 0), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    ended = datetime.fromtimestamp(ev_data.get("endedAt", 0), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    finished = ev_data.get("finishedAt", 0)
    if finished:
        finished_str = datetime.fromtimestamp(finished, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    else:
        finished_str = "—"
    war_ids = ev_data.get("warIds", [])
    notice = ev_data.get("noticeAt", "")
    if notice:
        notice_str = datetime.fromtimestamp(notice, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    else:
        notice_str = "—"

    h(f"# {name}")
    h()
    if short:
        h(f"> {short}")
        h()
    h(f"**ID**: {eid} | **类型**: {ev_type}")
    h()
    
    if banner:
        h(f"![Banner]({banner})")
        h()
    
    h("## 基础信息")
    h()
    h("| 属性 | 值 |")
    h("|------|-----|")
    h(f"| ID | {eid} |")
    h(f"| 名称 | {name} |")
    h(f"| 短名 | {short} |")
    h(f"| 类型 | {ev_type} |")
    h(f"| 公告时间 | {notice_str} |")
    h(f"| 开始时间 | {started} |")
    h(f"| 结束时间 | {ended} |")
    h(f"| 完全结束 | {finished_str} |")
    h()
    
    # 开放条件
    cond_msg = ev_data.get("closedMessage", "")
    if cond_msg:
        h("## 开放条件")
        h()
        h(f"< {cond_msg}")
        h()
    
    # Detail
    if detail:
        clean = re.sub(r'<[^>]+>', '', detail).strip()
        if clean:
            h("## 活动简介")
            h()
            h(clean)
            h()
    
    # War references
    if war_ids:
        h("## 地图/关卡")
        h()
        for wid in sorted(war_ids):
            h(f"- [[wars/{wid}|War #{wid}]]")
        h()
    
    # Shops
    shops = ev_data.get("shop", [])
    if shops:
        h("## 商店兑换")
        h()
        for shop in shops:
            h(f"### {shop.get('name', '商店')}")
            h()
            items = shop.get("items", [])
            if items:
                h("| 图标 | 道具 | 限购 | 所需道具 | 数量 |")
                h("|---|---|---|---|---|")
                for it in items[:20]:
                    item_name = it.get("name", "?")
                    limit = it.get("limitCount", "∞")
                    cost_items = it.get("costItems", [])
                    cost_str = "; ".join([f"{c.get('name','?')}x{c.get('num',1)}" for c in cost_items[:3]])
                    h(f"| — | {item_name} | {limit} | {cost_str} | — |")
            h()
    
    # Lotteries
    lottos = ev_data.get("lotteries", [])
    if lottos:
        h("## 抽奖池")
        h()
        for lotto in lottos:
            h(f"### {lotto.get('name', '抽奖池')}")
            h()
            gifts = lotto.get("gifts", [])
            if gifts:
                h("| 图标 | 奖品 | 类型 | 总数 |")
                h("|---|---|---|---|")
                for g in gifts[:15]:
                    h(f"| — | {g.get('name','?')} | {g.get('type','?')} | {g.get('num',1)} |")
            h()
    
    # 关联从者
    svt_ids = set()
    for add in ev_data.get("eventAdds", []):
        svt_ids.add(add.get("svt", {}).get("id", 0))
    if svt_ids:
        h("## 关联从者")
        h()
        for sid in sorted(svt_ids):
            if sid:
                h(f"- [[servants/CN/{sid}|#{sid}]]")
        h()
    
    h("---")
    h(f"*数据来源: Atlas Academy API* | *最后更新: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}*")
    return "\n".join(lines)


def save_event(region, eid, basic, full_data=None):
    """Save event MD and raw JSON."""
    raw_dir = os.path.join(RAW_BASE, region)
    ent_dir = os.path.join(ENT_BASE, region)
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(ent_dir, exist_ok=True)
    
    ts = basic.get("endedAt", 0)
    is_full = ts >= THRESHOLD_TIME
    
    if is_full and full_data:
        # Save raw JSON
        with open(os.path.join(raw_dir, f"{eid}.json"), "w", encoding="utf-8") as f:
            json.dump(full_data, f, ensure_ascii=False, indent=2)
        md = generate_full(full_data)
    else:
        md = generate_brief(basic)
    
    with open(os.path.join(ent_dir, f"{eid}.md"), "w", encoding="utf-8") as f:
        f.write(md)
    
    return is_full


def make_index(region, events):
    """Generate index.md for a region."""
    lines = [f"# 活动索引（{region}）", "", "| ID | 名称 | 类型 | 开始时间 | 结束时间 | 状态 |", "|---|---|---|---|---|---|"]
    for eid, name, ev_type, started, ended, is_full in sorted(events, key=lambda x: x[0]):
        status = "完整" if is_full else "简略"
        s = datetime.fromtimestamp(started, tz=timezone.utc).strftime("%Y-%m-%d") if started else "?"
        e = datetime.fromtimestamp(ended, tz=timezone.utc).strftime("%Y-%m-%d") if ended else "?"
        lines.append(f"| [{eid}]({eid}.md) | {name} | {ev_type} | {s} | {e} | {status} |")
    
    path = os.path.join(ENT_BASE, region, "index.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


if __name__ == "__main__":
    import time as _time
    
    region = sys.argv[1] if len(sys.argv) > 1 else None
    
    for r in (["CN", "JP"] if not region else [region]):
        basic_path = f"/tmp/{r.lower()}_basic_event.json"
        if not os.path.exists(basic_path):
            print(f"Skip {r}: basic_event not found")
            continue
        
        basic_list = json.load(open(basic_path))
        events = [e for e in basic_list if e.get("type") in ("eventQuest", "warBoard")]
        
        # Get CN synced IDs (for JP exclusion)
        cn_synced = set()
        cn_state_path = os.path.join(DATA_DIR, "event_cn_sync_state.json")
        if os.path.exists(cn_state_path):
            cn_synced = set(json.load(open(cn_state_path)).get("synced_ids", []))
        
        # Get current synced IDs for this region
        state_path = os.path.join(DATA_DIR, f"event_{r.lower()}_sync_state.json")
        synced = set()
        if os.path.exists(state_path):
            synced = set(json.load(open(state_path)).get("synced_ids", []))
        
        # Determine new events
        all_ids = {e["id"] for e in events}
        if r == "JP":
            # JP only: exclude CN existing IDs
            eligible = {eid for eid in all_ids if eid not in cn_synced}
        else:
            eligible = all_ids
        
        new_ids = sorted(eligible - synced)
        print(f"\n{r}: {len(events)} total, {len(synced)} synced, {len(new_ids)} new")
        
        if not new_ids:
            print(f"  No new events to fetch")
            # Still rebuild index
            continue
        
        # Process new events
        for i, eid in enumerate(new_ids):
            ev = next(e for e in events if e["id"] == eid)
            ts = ev.get("endedAt", 0)
            is_full = ts >= THRESHOLD_TIME
            
            if is_full:
                # Fetch full lore data
                url = f"https://api.atlasacademy.io/nice/{r}/event/{eid}?lore=true"
                try:
                    import urllib.request
                    req = urllib.request.Request(url, headers={"User-Agent": "hermes"})
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        full_data = json.loads(resp.read())
                    actual_full = save_event(r, eid, ev, full_data)
                except Exception as ex:
                    print(f"  [{i+1}/{len(new_ids)}] #{eid} {ev.get('name','')} → API error: {ex}")
                    actual_full = save_event(r, eid, ev, None)
            else:
                actual_full = save_event(r, eid, ev, None)
            
            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{len(new_ids)}] ...")
            
            _time.sleep(REQUEST_DELAY)
        
        # Update state
        new_synced = sorted(synced | set(new_ids))
        full_ids = set()
        for e in events:
            if e["id"] in new_synced and e.get("endedAt", 0) >= THRESHOLD_TIME:
                full_ids.add(e["id"])
        brief_ids = set(new_synced) - full_ids
        
        state = {
            "last_sync_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "threshold_time": THRESHOLD_TIME,
            "threshold_event_id": THRESHOLD_EVENT,
            "synced_ids": new_synced,
            "full_ids": sorted(full_ids),
            "brief_ids": sorted(brief_ids),
        }
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)
        
        # Rebuild index
        event_list = []
        for e in events:
            if e["id"] not in new_synced:
                continue
            is_f = e.get("endedAt", 0) >= THRESHOLD_TIME
            event_list.append((e["id"], e.get("name","?"), e.get("type","?"), e.get("startedAt",0), e.get("endedAt",0), is_f))
        idx = make_index(r, event_list)
        print(f"  Index: {idx}")
        print(f"  Done: {len(new_synced)} events ({len(full_ids)} full, {len(brief_ids)} brief)")
