#!/usr/bin/env python3
"""FGO 活动知识库生成器 v2 — 带表格解析、分块写入"""

import json, os, sys, re
from datetime import datetime

WIKI = os.path.expanduser("~/fgo-wiki")

ITEM_CDN = "https://static.atlasacademy.io/CN/Items/{}.png"

TYPE_LABELS = {
    "eventQuest": "限时活动",
    "eventWar": "活动",
    "campaign": "限时活动",
    "loginBonus": "登录奖励",
}

ITEM_CDN = "https://static.atlasacademy.io/CN/Items/{}.png"


def ts_str(ts: int) -> str:
    if not ts or ts < 0: return "—"
    if ts > 2000000000: return "常驻"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def status(started: int, ended: int) -> str:
    now = datetime.now().timestamp()
    if ended > 2000000000: return "常驻"
    if started > now: return "即将开始"
    if ended > now: return "进行中"
    return "已结束"


def shop_table(shop: list) -> list:
    """Parse shop items into markdown table lines."""
    lines = ["## 商店兑换", ""]
    lines.append("| 图标 | 道具 | 限购 | 所需道具 | 数量 |")
    lines.append("|------|------|------|----------|------|")
    for s in shop:
        name = s.get("name", "?")
        cost = s.get("cost", {})
        item = cost.get("item", {}) if isinstance(cost, dict) else {}
        cost_name = item.get("name", "?")
        amount = cost.get("amount", "?") if isinstance(cost, dict) else cost
        limit = s.get("limitNum", "—")
        # Icon: use cost item's icon since reward icons aren't in event data
        cost_icon = item.get("icon", "")
        icon = f"![]({cost_icon})" if cost_icon else "—"
        lines.append(f"| {icon} | {name} | {limit} | {cost_name} | {amount} |")
    lines.append("")
    return lines


def lotteries_table(lotteries: list) -> list:
    """Parse lottery boxes into summarized table by rewards."""
    lines = ["## 抽奖池", ""]

    for li, loot in enumerate(lotteries):
        name = loot.get("name", f"抽奖池 #{li+1}")
        lines.append(f"### {name}")
        lines.append("")
        boxes = loot.get("boxes", [])

        # Aggregate gifts by (type, objectId)
        from collections import Counter
        rare = Counter()
        normal = Counter()
        for b in boxes:
            is_rare = b.get("isRare", False)
            for g in b.get("gifts", []):
                key = (g.get("type", "?"), g.get("objectId", "?"))
                num = g.get("num", 1)
                maxn = b.get("maxNum", 1) or 1
                total = num * maxn
                if is_rare:
                    rare[key] += total
                else:
                    normal[key] += total

        # Rare prizes
        if rare:
            lines.append("**稀有奖品**：")
            lines.append("")
            lines.append("| 图标 | 奖品 | 类型 | 总数 |")
            lines.append("|------|------|------|------|")
            for (gtype, oid), count in rare.most_common():
                icon = f"![]({ITEM_CDN.format(oid)})"
                lines.append(f"| {icon} | #{oid} | {gtype} | {count} |")
            lines.append("")

        # Normal prizes
        if normal:
            lines.append("**普通奖品**：")
            lines.append("")
            lines.append("| 图标 | 奖品 | 类型 | 总数 |")
            lines.append("|------|------|------|------|")
            for (gtype, oid), count in normal.most_common():
                icon = f"![]({ITEM_CDN.format(oid)})"
                lines.append(f"| {icon} | #{oid} | {gtype} | {count} |")
            lines.append("")

        lines.append(f"**合计奖格**：{len(boxes)} 个")
        lines.append("")

    return lines


def chunked_write(path: str, chunks: list):
    """Write file in chunks (first chunk overwrites, rest append)."""
    for i, chunk in enumerate(chunks):
        chunk_str = "\n".join(chunk)
        if i == 0:
            with open(path, "w", encoding="utf-8") as f:
                f.write(chunk_str)
        else:
            with open(path, "a", encoding="utf-8") as f:
                f.write("\n" + chunk_str)
    return sum(len(c) for c in chunks)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_events.py <event_id>")
        sys.exit(1)

    eid = sys.argv[1]
    raw_path = os.path.join(WIKI, f"raw/events/{eid}.json")
    if not os.path.exists(raw_path):
        print(f"Error: {raw_path} not found")
        sys.exit(1)

    with open(raw_path, encoding="utf-8") as f:
        data = json.load(f)

    name = data.get("shortName") or data.get("name", "?")
    name = re.sub(r'\s+', ' ', name).strip()
    etype = data.get("type", "?")
    type_label = TYPE_LABELS.get(etype, etype)
    started = data.get("startedAt", 0)
    ended = data.get("endedAt", 0)
    st = status(started, ended)

    # Build chunks
    chunks = []

    # Chunk 1: Header + time
    c = [f"# {name}", "",
         f"> **ID**: {eid} | **类型**: {type_label} | **状态**: {st}",
         "",
         "## 活动时间", "",
         "| 项目 | 时间 |", "|------|------|",
         f"| 公告时间 | {ts_str(data.get('noticeAt', 0))} |",
         f"| 开始时间 | {ts_str(started)} |",
         f"| 结束时间 | {ts_str(ended)} |",
         f"| 完全结束 | {ts_str(data.get('finishedAt', 0))} |"]
    if data.get("materialOpenedAt"):
        c.append(f"| 素材开放 | {ts_str(data['materialOpenedAt'])} |")
    c.append("")
    chunks.append(c)

    # Chunk 2: Detail + images
    c = []
    detail = data.get("detail", "")
    if detail:
        c.append("## 活动简介"); c.append(""); c.append(detail.strip()); c.append("")
    c.append("## 视觉资源"); c.append("")
    banner = data.get("banner", "")
    if banner: c.append(f"![活动主横幅]({banner})"); c.append("")
    nb = data.get("noticeBanner", "")
    if nb and nb != banner: c.append(f"![公告横幅]({nb})"); c.append("")
    chunks.append(c)

    # Chunk 3: War IDs as wiki links
    war_ids = data.get("warIds", [])
    if war_ids:
        c = ["## 地图/关卡", ""]
        for w in war_ids: c.append(f"- [[wars/{w}|War #{w}]]")
        c.append("")
        chunks.append(c)

    # Chunk 4: Main quests (from war data, if available)
    import os as _os
    for wid in war_ids:
        war_path = f"{WIKI}/entities/wars/{wid}.md"
        if _os.path.exists(war_path):
            with open(war_path) as _f:
                _wt = _f.read()
            _mq = _wt.split("## 主线关卡")
            if len(_mq) > 1:
                _main = _mq[1].split("## 自由关卡")[0].strip()
                c = [f"## 主线关卡", ""] + _main.split("\n")[1:] + [""]
                chunks.append(c)

    # Chunk 4: Svts
    svts = data.get("svts", [])
    if svts:
        c = ["## 关联从者", ""]
        for s in svts:
            c.append(f"- **{s.get('name','?')}**（ID: {s.get('svtId','?')}）")
        c.append("")
        chunks.append(c)

    # Chunk 5: Shop (can be large, split further)
    shop = data.get("shop", [])
    if shop:
        shop_lines = shop_table(shop)
        # Split shop table if too long
        while shop_lines:
            chunk = []
            char_count = 0
            while shop_lines and char_count < 6000:
                line = shop_lines.pop(0)
                chunk.append(line)
                char_count += len(line) + 1
            if chunk:
                chunks.append(chunk)

    # Chunk 6: Lotteries
    lot = data.get("lotteries", [])
    if lot:
        lot_lines = lotteries_table(lot)
        while lot_lines:
            chunk = []
            char_count = 0
            while lot_lines and char_count < 6000:
                line = lot_lines.pop(0)
                chunk.append(line)
                char_count += len(line) + 1
            if chunk:
                chunks.append(chunk)

    # Footer
    chunks.append(["---", "", f"*数据来源: Atlas Academy API* | *最后更新: {datetime.now().strftime('%Y-%m-%d')}*"])

    # Write
    entity_dir = os.path.join(WIKI, "entities/events")
    os.makedirs(entity_dir, exist_ok=True)
    entity_path = os.path.join(entity_dir, f"{name}.md")
    total = chunked_write(entity_path, chunks)
    print(f"Generated: {entity_path} ({total} chars, {len(chunks)} chunks)")


if __name__ == "__main__":
    main()
