#!/usr/bin/env python3
"""gen_gacha_md.py — 从 gacha_raw.json 生成卡池 MD（按区服分目录 + 按日期自动归档）。

目录结构:
  entities/gacha/CN/{id}.md        # 国服当前/未来卡池
  entities/gacha/CN/index.md
  entities/gacha/JP/{id}.md        # 未来视卡池（region=JP & estimated）
  entities/gacha/JP/index.md
  entities/gacha/未来视.md          # 国服未来一年卡池预测时间线
  entities/gacha/expired_gacha.md  # 过期卡池汇总（四大章节）

分类规则:
  end_date < today            → 过期（只进 expired_gacha.md 汇总，不生成单 MD）
  estimated=True              → 未来视（JP/ 目录，⚠预估）
  start_date <= today <= end  → 当前；start_date > today → 未来（CN/ 目录）

用法:
    python3 scripts/gen_gacha_md.py [--full]
"""
import json
import os
import sys
import glob
import datetime

WIKI = os.path.expanduser("~/fgo-wiki")
ENT_DIR = os.path.join(WIKI, "entities/gacha")
RAW_GACHA = os.path.join(WIKI, "raw/gacha/gacha_raw.json")
TODAY = datetime.date.today().isoformat()

FOOTER = "\n---\n*数据来源: Mooncell* | *遵循 CC BY-NC-SA 4.0 协议*"


def load_svt_by_cno():
    """collectionNo → {name, class, rarity}（CN + JP raw）"""
    svt = {}
    for region in ["CN", "JP"]:
        for fp in glob.glob(os.path.join(WIKI, f"raw/servants/{region}/*.json")):
            try:
                d = json.load(open(fp))
            except Exception:
                continue
            cno = d.get("collectionNo")
            if cno:
                svt[cno] = {"name": d.get("name", "?"), "class": d.get("className", "?"),
                            "rarity": d.get("rarity", 0)}
    return svt


def load_ce_names():
    """礼装图鉴号 → 名称（CN raw craft-essences，id 即图鉴号）"""
    ce = {}
    for fp in glob.glob(os.path.join(WIKI, "raw/craft-essences/CN/*.json")):
        try:
            d = json.load(open(fp))
        except Exception:
            continue
        cid = d.get("collectionNo") or d.get("id")
        if cid:
            ce[cid] = d.get("name", f"#{cid}")
    return ce


def svt_name(svt_by_cno, cno):
    info = svt_by_cno.get(cno)
    return info["name"] if info else f"#{cno}"


def render_detail(g, svt_by_cno, ce_names):
    """单个卡池 MD 内容"""
    region_tag = "JP（未来视）" if g.get("estimated") else g.get("region", "CN")
    status = g.get("status", "?")
    est = " ⚠预估" if g.get("estimated") else ""
    L = []
    L.append(f"# {g.get('name', '?')}")
    L.append(f"> **ID**: {g.get('id')} | **类型**: {g.get('type', '?')} | **状态**: {status}{est} | **区服**: {region_tag}")
    L.append("")
    L.append("## 时间")
    L.append("")
    L.append("| 项目 | 时间 |")
    L.append("|------|------|")
    L.append(f"| 开始 | {g.get('start_date', '?')}{'（预估）' if g.get('estimated') else ''} |")
    L.append(f"| 结束 | {g.get('end_date', '?')}{'（预估）' if g.get('estimated') else ''} |")
    if g.get("estimated"):
        L.append("")
        L.append("> ⚠ 此卡池时间为 **Mooncell 未来视预测**（依据日服进度推算），仅供参考，实际以国服公告为准")
    L.append("")
    banner = g.get("banner", "")
    if banner:
        L.append("## 卡池图片")
        L.append("")
        L.append(f"![{g.get('name', '?')}]({banner})")
        L.append("")
    L.append("## UP 从者")
    L.append("")
    svts = g.get("servant_ids", [])
    up_note = g.get("up_note", "")
    if up_note:
        L.append(f"- **{up_note}**：共 {len(svts)} 骑（全职阶从者）")
    elif svts:
        L.append("| 从者 | 职阶 | 星级 |")
        L.append("|---|---|---|")
        for cno in svts:
            info = svt_by_cno.get(cno)
            if info:
                L.append(f"| [[{cno}|{info['name']}]] | {info['class']} | {'★' * info['rarity']} |")
            else:
                L.append(f"| #?{cno} | ? | ? |")
    else:
        L.append("待补充（Mooncell 未在页面列出，或从者数 >15 需查卡池详情页）")
    L.append("")
    ces = g.get("ce_ids", [])
    if ces:
        L.append("## UP 礼装")
        L.append("")
        L.append("| 礼装 |")
        L.append("|---|")
        for cid in ces:
            L.append(f"| {ce_names.get(cid, f'#{cid}')} |")
        L.append("")
    L.append(FOOTER)
    return "\n".join(L)


def render_index(items, title="卡池索引", note=""):
    L = [f"# {title}", ""]
    if note:
        L.append(f"> {note}")
        L.append("")
    L.append("| ID | 名称 | 类型 | 开始 | 结束 | 状态 |")
    L.append("|---|---|---|---|---|---|")
    for g in sorted(items, key=lambda x: x.get("start_date", ""), reverse=True):
        L.append(f"| [{g['id']}]({g['id']}.md) | {g.get('name', '?')[:35]} | {g.get('type', '?')} | "
                 f"{g.get('start_date', '?')} | {g.get('end_date', '?')} | {g.get('status', '?')}{'⚠预估' if g.get('estimated') else ''} |")
    L.append("")
    return "\n".join(L)


def render_future_timeline(fv_items, svt_by_cno):
    """未来视.md — 国服未来一年卡池预测时间线"""
    L = ["# 国服未来一年卡池预测（未来视）", "",
         "> ⚠ 数据来源 [Mooncell 未来视卡池](https://fgo.wiki/w/卡池一览/未来视卡池)：预计时间为用户根据日服进度推算的**个人预测**，仅供参考，与国服实际实装可能不符。",
         "", "| 卡池 | 预估开始 | 预估结束 | UP 从者 |", "|---|---|---|---|"]
    for g in sorted(fv_items, key=lambda x: x.get("start_date", "")):
        up_note = g.get("up_note", "")
        if up_note:
            names = [f"{up_note}({len(g.get('servant_ids', []))}骑)"]
        else:
            names = []
            for cno in g.get("servant_ids", [])[:8]:
                info = svt_by_cno.get(cno)
                names.append(info["name"] if info else f"#{cno}")
            if len(g.get("servant_ids", [])) > 8:
                names.append("…")
            if not names:
                names.append("待补充")
        L.append(f"| [{g['name']}](JP/{g['id']}.md) | {g.get('start_date', '?')} | {g.get('end_date', '?')} | {'、'.join(names)} |")
    L.append("")
    L.append(FOOTER)
    return "\n".join(L)


def render_expired(expired, svt_by_cno, ce_names, last_sync):
    """过期汇总（四大章节）"""
    from collections import defaultdict
    svt_up = defaultdict(lambda: {"count": 0, "last_up": "", "pools": []})
    for g in expired.values():
        for cno in g.get("servant_ids", []):
            nm = svt_name(svt_by_cno, cno)
            svt_up[cno]["name"] = nm
            svt_up[cno]["count"] += 1
            start = g.get("start_date", "")
            if start > svt_up[cno]["last_up"]:
                svt_up[cno]["last_up"] = start
            svt_up[cno]["pools"].append({"name": g.get("name", "?"), "start": start,
                                         "end": g.get("end_date", ""), "type": g.get("type", "推荐召唤")})
    sorted_svt = sorted(svt_up.values(), key=lambda x: (-x["count"], x["name"]))

    ce_up = defaultdict(list)
    for g in expired.values():
        for cid in g.get("ce_ids", []):
            nm = ce_names.get(cid, f"#{cid}")
            ce_up[nm].append({"pool": g.get("name", "?"), "start": g.get("start_date", ""), "end": g.get("end_date", "")})

    yearly = defaultdict(int)
    for g in expired.values():
        y = g.get("start_date", "")[:4]
        if y:
            yearly[y] += 1

    L = []
    L.append("# 过期卡池汇总")
    L.append("")
    L.append(f"**数据更新时间**: {last_sync} | **过期卡池总数**: {len(expired)}")
    L.append("")
    L.append("## 从者 UP 次数统计")
    L.append("")
    L.append("| 从者 | UP 次数 | 最近一次 UP |")
    L.append("|---|---|---|")
    for s in sorted_svt:
        L.append(f"| {s['name']} | {s['count']} | {s['last_up']} |")
    L.append("")
    L.append("## 从者 UP 历史明细")
    L.append("")
    L.append("| 从者 | 卡池 | 类型 | 开始 | 结束 |")
    L.append("|---|---|---|---|---|")
    for s in sorted_svt:
        for p in sorted(s["pools"], key=lambda x: x["start"], reverse=True):
            L.append(f"| {s['name']} | {p['name'][:40]} | {p.get('type', '?')} | {p['start']} | {p['end']} |")
    L.append("")
    L.append("## 礼装 UP 历史")
    L.append("")
    L.append("| 礼装 | 卡池 | 开始 | 结束 |")
    L.append("|---|---|---|---|")
    for cname, pools in sorted(ce_up.items()):
        for p in sorted(pools, key=lambda x: x["start"], reverse=True):
            L.append(f"| {cname} | {p['pool'][:40]} | {p['start']} | {p['end']} |")
    L.append("")
    L.append("## 按年份统计")
    L.append("")
    L.append("| 年份 | 卡池数量 |")
    L.append("|---|---|")
    for year in sorted(yearly.keys(), reverse=True):
        L.append(f"| {year} | {yearly[year]} |")
    L.append("")
    L.append(FOOTER)
    return "\n".join(L)


def main():
    raw = json.load(open(RAW_GACHA))
    all_g = raw["gachas"]
    svt_by_cno = load_svt_by_cno()
    ce_names = load_ce_names()
    last_sync = raw.get("last_sync_at", "?")

    expired = {}
    cn_items = {}
    jp_items = {}
    for gid, g in all_g.items():
        if g.get("estimated"):
            jp_items[gid] = g
        elif g.get("end_date", "") < TODAY:
            expired[gid] = g
        else:
            cn_items[gid] = g

    # 目录
    cn_dir = os.path.join(ENT_DIR, "CN")
    jp_dir = os.path.join(ENT_DIR, "JP")
    os.makedirs(cn_dir, exist_ok=True)
    os.makedirs(jp_dir, exist_ok=True)

    # 详情 MD
    for gid, g in cn_items.items():
        with open(os.path.join(cn_dir, f"{gid}.md"), "w", encoding="utf-8") as f:
            f.write(render_detail(g, svt_by_cno, ce_names))
    for gid, g in jp_items.items():
        with open(os.path.join(jp_dir, f"{gid}.md"), "w", encoding="utf-8") as f:
            f.write(render_detail(g, svt_by_cno, ce_names))

    # 索引
    with open(os.path.join(cn_dir, "index.md"), "w", encoding="utf-8") as f:
        f.write(render_index(cn_items.values(), "国服卡池索引",
                             note=f"当前/未来卡池 {len(cn_items)} 个，过期见 [expired_gacha.md](../expired_gacha.md)"))
    with open(os.path.join(jp_dir, "index.md"), "w", encoding="utf-8") as f:
        f.write(render_index(jp_items.values(), "未来视卡池索引（国服未来一年预测）",
                             note="⚠ 预估时间仅供参考，来源 Mooncell 未来视"))

    # 未来视时间线
    with open(os.path.join(ENT_DIR, "未来视.md"), "w", encoding="utf-8") as f:
        f.write(render_future_timeline(jp_items.values(), svt_by_cno))

    # 过期汇总
    with open(os.path.join(ENT_DIR, "expired_gacha.md"), "w", encoding="utf-8") as f:
        f.write(render_expired(expired, svt_by_cno, ce_names, last_sync))

    print(f"✅ CN 卡池: {len(cn_items)} | 未来视(JP): {len(jp_items)} | 过期: {len(expired)}")
    print(f"   输出: {cn_dir} ({len(cn_items)}+index) / {jp_dir} ({len(jp_items)}+index) / 未来视.md / expired_gacha.md")


if __name__ == "__main__":
    main()
