#!/usr/bin/env python3
"""sync_preview.py — 手动触发：对比 JP API 与本地 CN raw，生成「国服未实装强化」预览数据。

用法:
    python3 scripts/sync_preview.py <collectionNo 或 内部ID> [活动名]

示例:
    python3 scripts/sync_preview.py 2
    python3 scripts/sync_preview.py 2 "从者强化任务第21弹～11th Anniversary～特别篇"

逻辑:
    1. 拉 JP nice API 该从者完整数据（0.5s 间隔）
    2. 对比本地 raw/servants/CN/{sid}.json 的技能/宝具版本集
    3. 差集（JP 有、CN 无的强化后版本）= 国服未实装强化
       → 写 data/servant_preview/{sid}.json（完整 JP skill/NP dict + 强化本 Quest/日服实装日期）
    4. 差集为空（国服已实装）→ 删除预览文件
"""
import json
import os
import sys
import time
import urllib.request
import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
RAW = os.path.join(BASE, "raw", "servants", "CN")
PREVIEW = os.path.join(DATA, "servant_preview")
API_INTERVAL = 0.5  # Atlas 请求间隔


def fetch(url, retries=3):
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(2)
    return None


def resolve_sid(arg):
    """collectionNo 或内部 ID → (sid, collectionNo)"""
    m = json.load(open(os.path.join(DATA, "servant_id_map.json")))
    by_cno = {int(v["collectionNo"]): k for k, v in m.items()}
    if str(arg).isdigit():
        n = int(arg)
        if n in by_cno:
            return by_cno[n], n
        if str(n) in m:
            return str(n), int(m[str(n)]["collectionNo"])
    raise SystemExit(f"未找到图鉴编号/ID: {arg}")


def latest(versions):
    """取最高 priority 的正式版本（过滤 ??? 占位）"""
    vers = [v for v in versions if v.get("name") != "？？？"]
    if not vers:
        return None
    return max(vers, key=lambda v: v.get("priority", 0))


def diff_versions(jp_items, cn_items):
    """返回 JP 有而 CN 无的版本: {num: jp_latest_version}"""
    out = {}
    jp_by_num = {}
    for it in jp_items:
        jp_by_num.setdefault(it.get("num", 0), []).append(it)
    cn_by_num = {}
    for it in cn_items:
        cn_by_num.setdefault(it.get("num", 0), []).append(it)
    for num, vers in jp_by_num.items():
        jl = latest(vers)
        if jl is None:
            continue
        cl = latest(cn_by_num.get(num, []))
        cn_pri = cl.get("priority", 0) if cl else 0
        if jl.get("priority", 0) > cn_pri:
            out[num] = jl
    return out


def quest_opened_at(qid):
    """拉 JP Quest 的 openedAt → YYYY-MM-DD"""
    if not qid or str(qid) == "0":
        return None
    try:
        q = fetch(f"https://api.atlasacademy.io/nice/JP/quest/{qid}")
        time.sleep(API_INTERVAL)
        oa = q.get("openedAt")
        if oa:
            return datetime.datetime.utcfromtimestamp(oa).strftime("%Y-%m-%d")
    except Exception:
        pass
    return None


def main():
    if len(sys.argv) < 2:
        raise SystemExit("用法: python3 scripts/sync_preview.py <collectionNo或内部ID>")
    sid, cno = resolve_sid(sys.argv[1])
    event_name = sys.argv[2] if len(sys.argv) > 2 else None

    # 1. JP API
    jp = fetch(f"https://api.atlasacademy.io/nice/JP/servant/{sid}")
    time.sleep(API_INTERVAL)

    # 2. 本地 CN raw
    cn_path = os.path.join(RAW, f"{sid}.json")
    if not os.path.exists(cn_path):
        raise SystemExit(f"本地 CN raw 不存在: {cn_path}")
    cn = json.load(open(cn_path))

    # 3. 差集
    skill_diff = diff_versions(jp.get("skills", []), cn.get("skills", []))
    np_diff = diff_versions(jp.get("noblePhantasms", []), cn.get("noblePhantasms", []))

    preview = {
        "sid": sid,
        "collectionNo": cno,
        "servant_name": jp.get("name"),
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d"),
        "skills": {},
        "nps": {},
    }
    for num, sk in skill_diff.items():
        qid = sk.get("condQuestId") or 0
        preview["skills"][str(num)] = dict(sk)
        preview["skills"][str(num)]["condQuestId"] = qid
        preview["skills"][str(num)]["jp_opened_at"] = quest_opened_at(qid)
        preview["skills"][str(num)]["event_name"] = event_name
    for num, np_ in np_diff.items():
        qid = np_.get("condQuestId") or 0
        preview["nps"][str(num)] = dict(np_)
        preview["nps"][str(num)]["condQuestId"] = qid
        preview["nps"][str(num)]["jp_opened_at"] = quest_opened_at(qid)
        preview["nps"][str(num)]["event_name"] = event_name

    os.makedirs(PREVIEW, exist_ok=True)
    path = os.path.join(PREVIEW, f"{sid}.json")
    if skill_diff or np_diff:
        json.dump(preview, open(path, "w"), ensure_ascii=False, indent=2)
        print(f"✓ 已写入 {path}")
        print(f"  未实装技能 {len(skill_diff)} 项: {[v.get('name') for v in skill_diff.values()]}")
        print(f"  未实装宝具 {len(np_diff)} 项: {[v.get('name') for v in np_diff.values()]}")
    else:
        if os.path.exists(path):
            os.remove(path)
            print(f"✓ 国服已实装，删除预览 {path}")
        else:
            print("✓ 无未实装强化")


if __name__ == "__main__":
    main()
