#!/usr/bin/env python3
"""FGO 特殊奖励时段（Campaign）同步脚本 v1

拉取 Atlas Academy basic_event.json（CN + JP），筛选 campaign 类型
（强化大成功/经验2倍/AP减半/牵绊/开放条件缓和 等），生成：
  entities/mechanics/campaign_timeline.md
支持增量（state 记录 synced_ids + last_sync_at）。
"""
import json, os, sys
from datetime import datetime, timezone, timedelta
import urllib.request

WIKI = os.path.expanduser("~/fgo-wiki")
OUT_FILE = f"{WIKI}/entities/mechanics/campaign_timeline.md"
INDEX_FILE = f"{WIKI}/entities/mechanics/index.md"
STATE_FILE = f"{WIKI}/data/campaign_sync_state.json"
RAW_DIR = f"{WIKI}/raw/campaigns"

# campaign 类型 → 中文分类
TYPE_LABEL = {
    "combineCampaign": "强化",
    "svtequipCombineCampaign": "礼装强化",
    "questCampaign": "AP/关卡",
    "interludeCampaign": "幕间/条件",
    "questCampaignRepeat": "AP/关卡",
}
# 需要排除的永久/测试时间戳（2037/2038 大纪元标记）
FOREVER = 4100000000
# Atlas 用 2038-01-01 作为"无有效日期"的哨兵值，排除
SENTINEL = 2145916800  # 2038-01-01 UTC

BEIJING = timezone(timedelta(hours=8))


def ts_str(ts, mark=None):
    if not ts or ts > FOREVER:
        return "常驻"
    s = datetime.fromtimestamp(ts, tz=BEIJING).strftime("%Y-%m-%d")
    return f"{s}{mark}" if mark else s


def clean_name(name):
    """清理富文本颜色标记 [FFFF00]...[-] 及换行"""
    if not name:
        return ""
    import re as _re
    name = _re.sub(r"\[[0-9A-Fa-f]{6}\]", "", name)
    name = name.replace("[-]", "").replace("\n", " ")
    return name.strip()


def fetch_basic(region):
    url = f"https://api.atlasacademy.io/export/{region}/basic_event.json"
    req = urllib.request.Request(url, headers={"User-Agent": "fgo-wiki/1.0"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())


def filter_campaigns(events):
    return [e for e in events
            if e.get("type") in TYPE_LABEL
            and e.get("startedAt") and e.get("endedAt")]


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

    now = datetime.now(tz=timezone.utc).timestamp()
    horizon = now + 365 * 86400  # 未来一年

    # 载入 state
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
    last_sync = state.get("last_sync_at")
    print(f"上次同步: {last_sync or '无'}")

    # 拉取 CN + JP
    print("拉取 CN basic_event.json ...")
    cn_all = fetch_basic("CN")
    print(f"CN 事件总数: {len(cn_all)}")
    print("拉取 JP basic_event.json ...")
    jp_all = fetch_basic("JP")
    print(f"JP 事件总数: {len(jp_all)}")

    # 保存 raw 备份（全量）
    for region, data in [("CN", cn_all), ("JP", jp_all)]:
        with open(f"{RAW_DIR}/{region.lower()}_basic_event.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    cn_camps = filter_campaigns(cn_all)
    jp_camps = filter_campaigns(jp_all)

    # CN：今天之后有效（进行中或已公告未来）
    # 排除无日期遗留（startedAt 也是 2037+ 哨兵），保留永久条目（startedAt 真实、endedAt 哨兵）
    cn_future = [c for c in cn_camps
                 if c.get("endedAt", 0) > now
                 and c.get("startedAt", 0) > 0
                 and c.get("startedAt", 0) < 2130000000  # 2037-07-01 之前（排除2037哨兵遗留）
                 and c.get("endedAt", 0) < SENTINEL]
    cn_future.sort(key=lambda c: c.get("startedAt", 0))

    # JP：未来一年预估 = 日服过去一年 campaign 排期 +365 天映射
    # （Atlas 只收录已公告事件，无未来数据；日服领先国服约一年，
    #   用去年同期档期推算未来一年，日期标注"预估"）
    past_year = [c for c in jp_camps
                 if now - 366 * 86400 <= c.get("startedAt", 0) <= now
                 and c.get("endedAt", 0) < FOREVER]
    jp_future = []
    for c in past_year:
        est = dict(c)
        est["id"] = f"{c.get('id')}E"  # E=Estimate 预估标记
        est["startedAt"] = c.get("startedAt", 0) + 365 * 86400
        est["endedAt"] = c.get("endedAt", 0) + 365 * 86400
        jp_future.append(est)
    jp_future.sort(key=lambda c: c.get("startedAt", 0))

    print(f"CN 有效 campaign: {len(cn_future)} 条")
    print(f"JP 未来一年预估（基于过去一年+365天映射）: {len(jp_future)} 条")

    # 生成 MD
    today = datetime.now(tz=BEIJING).strftime("%Y-%m-%d")
    lines = [
        "# FGO 特殊奖励时段表（Campaign）",
        "",
        f"> 来源：Atlas Academy API `basic_event.json` | 最后更新：{today} | 时间为北京时间",
        "",
        "涵盖：强化『大成功＆极大成功』率提升、从者/额外职阶获得经验值提升、AP消耗减半/0、牵绊获得量提升、风暴罐使用、开放条件缓和等特殊奖励时段。",
        "登录奖励类（loginCampaign）不在收录范围。",
        "",
        "## 一、国服（CN）当前及已公告",
        "",
        "| 类型 | ID | 名称 | 开始 | 结束 |",
        "|---|---|---|---|---|",
    ]
    if not cn_future:
        lines.append("| — | — | （暂无） | — | — |")
    for c in cn_future:
        lines.append(f"| {TYPE_LABEL.get(c.get('type'), c.get('type'))} | {c.get('id')} | {clean_name(c.get('name'))} | {ts_str(c.get('startedAt'))} | {ts_str(c.get('endedAt'))} |")

    lines += [
        "",
        "## 二、日服（JP）未来一年前瞻（预估）",
        "",
        "> 日服领先国服约一年。Atlas API 仅收录已公告事件（日服最新到 2026-08-15），本表为**日服过去一年 campaign 排期 +365 天映射**的预估档期，国服实际安排可能有差异，**仅供参考**。",
        "",
        "| 类型 | ID(预估) | 名称 | 开始（预估） | 结束（预估） |",
        "|---|---|---|---|---|",
    ]
    if not jp_future:
        lines.append("| — | — | （暂无） | — | — |")
    for c in jp_future:
        lines.append(f"| {TYPE_LABEL.get(c.get('type'), c.get('type'))} | {c.get('id')} | {clean_name(c.get('name'))} | {ts_str(c.get('startedAt'), ' ⚠预估')} | {ts_str(c.get('endedAt'), ' ⚠预估')} |")

    lines += [
        "",
        "---",
        "",
        "*数据来源: [Atlas Academy API](https://api.atlasacademy.io) | 游戏素材版权归 TYPE-MOON / FGO PROJECT 所有*",
        "",
    ]
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"已生成: {OUT_FILE}")

    # 更新索引（找到 campaign_timeline 行，更新说明/时间戳）
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, encoding="utf-8") as f:
            idx = f.read()
        new_row = f"| [特殊奖励时段表](./campaign_timeline.md) | 强化大成功/经验2倍/AP减半/牵绊等 Campaign（CN当前+JP未来一年预估） |"
        if "campaign_timeline.md" in idx:
            import re
            idx = re.sub(r"\| \[特殊奖励时段表\]\(\./campaign_timeline\.md\) \|[^\n]*", new_row, idx)
        else:
            # 插到「基础数据」分类表格末尾（从者集星权重排名之后）
            anchor = "| [从者集星权重排名](./star_weight_ranking.md) |"
            if anchor in idx:
                idx = idx.replace(anchor, anchor + "\n" + new_row)
            else:
                idx = idx.replace("## 📂 按主题分类", new_row + "\n\n## 📂 按主题分类")
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            f.write(idx)
        print(f"已更新索引: {INDEX_FILE}")

    # 更新 state
    state = {
        "last_sync_at": datetime.now(tz=BEIJING).strftime("%Y-%m-%d %H:%M:%S"),
        "cn_future_count": len(cn_future),
        "jp_future_count": len(jp_future),
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"已更新状态: {STATE_FILE}")


if __name__ == "__main__":
    main()
