#!/usr/bin/env python3
"""拉取全部日服从者原始数据（规则 2026-11 变更：JP 从者全量存储，不再只存国服未实装）。

规则（改前务必对齐 RULES.md）：
- 列表源：https://api.atlasacademy.io/export/JP/basic_servant.json
- 单条：https://api.atlasacademy.io/nice/JP/servant/{id}?lore=true   ← 只用 lore=true，不存非 lore 副本
- UA：fgo-wiki-updater
- 请求间隔 ≥ 0.6s（RULES 下限 0.5s，留余量防限流）
- 增量：只拉 raw/servants/JP/ 里没有的 id，可随时中断重跑
- 404 / 5xx：记录并跳过，不中断；失败 id 最后重试 1 轮
- 输出：raw/servants/JP/{id}.json（ensure_ascii=False）

用法：
    cd ~/fgo-wiki && ./.venv/bin/python scripts/fetch_jp_servants.py [--dry-run]
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

WIKI = os.path.expanduser("~/fgo-wiki")
RAW_DIR = os.path.join(WIKI, "raw/servants/JP")
BASIC_URL = "https://api.atlasacademy.io/export/JP/basic_servant.json"
NICE_URL = "https://api.atlasacademy.io/nice/JP/servant/{sid}?lore=true"
UA = "fgo-wiki-updater"
INTERVAL = 0.6
TIMEOUT = 60


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def main() -> int:
    dry = "--dry-run" in sys.argv
    os.makedirs(RAW_DIR, exist_ok=True)

    print("① 拉 JP basic_servant 列表")
    basic = json.loads(_get(BASIC_URL).decode("utf-8"))
    jp_ids = sorted({int(s["id"]) for s in basic})
    info = {int(s["id"]): s for s in basic}

    have = {int(f[:-5]) for f in os.listdir(RAW_DIR) if f.endswith(".json")}
    todo = [sid for sid in jp_ids if sid not in have]
    print(f"   API {len(jp_ids)} 个 / 本地 {len(have)} 个 / 待拉 {len(todo)} 个")
    if dry or not todo:
        return 0

    ok, fail = 0, []
    for i, sid in enumerate(todo, 1):
        meta = info.get(sid, {})
        tag = f"#{meta.get('collectionNo','?')} {meta.get('name','?')}"
        path = os.path.join(RAW_DIR, f"{sid}.json")
        try:
            data = json.loads(_get(NICE_URL.format(sid=sid)).decode("utf-8"))
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            ok += 1
            if i % 20 == 0 or i == len(todo):
                print(f"   [{i}/{len(todo)}] {sid} {tag} ✅")
        except urllib.error.HTTPError as e:
            print(f"   [{i}/{len(todo)}] {sid} {tag} → HTTP {e.code}")
            fail.append(sid)
        except Exception as e:                      # 网络抖动等
            print(f"   [{i}/{len(todo)}] {sid} {tag} → {type(e).__name__}")
            fail.append(sid)
        time.sleep(INTERVAL)

    if fail:                                        # 失败重试一轮
        print(f"\n② 重试 {len(fail)} 个失败条目")
        for sid in list(fail):
            path = os.path.join(RAW_DIR, f"{sid}.json")
            time.sleep(INTERVAL * 3)
            try:
                data = json.loads(_get(NICE_URL.format(sid=sid)).decode("utf-8"))
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                fail.remove(sid)
                ok += 1
                print(f"   {sid} ✅ (retry)")
            except Exception as e:
                print(f"   {sid} → 仍失败 {type(e).__name__}")

    print(f"\n完成：成功 {ok} / 失败 {len(fail)}")
    if fail:
        print("失败 id:", fail)
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
