#!/usr/bin/env python3
"""FGO 知识库全量同步编排器 v1

按顺序执行各数据类型的增量同步脚本，统一处理：
  1. 预下载依赖文件（generate_ce.py / fetch_events.py 需要 /tmp 预置文件）
  2. 按类型依次运行增量脚本（失败不中断，继续后续）
  3. 汇总运行报告

用法:
  python3 scripts/sync_all.py                 # 默认: 跳过卡池（Mooncell 爬虫）
  python3 scripts/sync_all.py --with-gacha    # 包含卡池同步（banner 需人工确认）
  python3 scripts/sync_all.py --only servants # 只跑指定类型（逗号分隔）
"""
import json, os, subprocess, sys, time
from datetime import datetime, timezone

WIKI = os.path.expanduser("~/fgo-wiki")
SCRIPTS = os.path.join(WIKI, "scripts")

# 各类型: (脚本名, 需要预下载的 /tmp 依赖文件, 说明)
STEPS = [
    ("servants", "fetch_servants.py", [], "CN从者拉取(增量)"),
    ("servants_gen", "generate_all_servants.py", [], "从者MD生成"),
    ("servants_map", "rebuild_servants_id.py", [], "从者ID映射重建"),
    ("craft_essences", "generate_ce.py",
     ["/tmp/cn_nice_equip.json", "/tmp/jp_nice_equip.json"], "礼装(CN+JP)"),
    ("events", "fetch_events.py",
     ["/tmp/cn_basic_event.json", "/tmp/jp_basic_event.json"], "活动(CN+JP)"),
    ("items", "sync_items.py", [], "道具"),
    ("mystic_codes", "sync_mystic_codes.py", [], "御主礼装"),
    ("command_codes", "sync_command_codes.py", [], "指令纹章"),
    ("campaigns", "sync_campaigns.py", [], "特殊奖励时段(Campaign)"),
]
GACHA_STEP = ("gacha", "fetch_mooncell_gacha.py", [], "卡池(Mooncell, banner人工确认)")

# 预下载: 需要 /tmp 依赖的脚本所需基础文件
PREREQ = {
    "/tmp/cn_nice_equip.json": "https://api.atlasacademy.io/export/CN/nice_equip_lore.json",
    "/tmp/jp_nice_equip.json": "https://api.atlasacademy.io/export/JP/nice_equip_lore.json",
    "/tmp/cn_basic_event.json": "https://api.atlasacademy.io/export/CN/basic_event.json",
    "/tmp/jp_basic_event.json": "https://api.atlasacademy.io/export/JP/basic_event.json",
}


def download(url, dest, timeout=300):
    import urllib.request
    if os.path.exists(dest):
        age = (time.time() - os.path.getmtime(dest)) / 86400
        if age < 1:  # 24小时内已有则跳过
            print(f"  ✓ {dest} 已存在({age:.1f}天前)")
            return True
    print(f"  ↓ 下载 {url} → {dest}")
    req = urllib.request.Request(url, headers={"User-Agent": "fgo-wiki/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
        print(f"  ✓ {dest} ({len(data)/1024/1024:.1f}MB)")
        return True
    except Exception as e:
        print(f"  ✗ 下载失败 {url}: {e}")
        return False


def run_step(name, script, deps, desc, enabled=True):
    if not enabled:
        print(f"\n⏭ [{name}] {desc} — 跳过")
        return None
    print(f"\n▶ [{name}] {desc}")
    # 预下载依赖
    ok = True
    for dep in deps:
        if dep in PREREQ:
            if not download(PREREQ[dep], dep):
                ok = False
    if not ok:
        print(f"  ✗ 依赖下载失败，跳过 {name}")
        return False
    # 运行脚本
    script_path = os.path.join(SCRIPTS, script)
    if not os.path.exists(script_path):
        print(f"  ✗ 脚本不存在: {script_path}")
        return False
    try:
        r = subprocess.run(
            [sys.executable, script_path],
            cwd=WIKI, capture_output=True, text=True, timeout=1800)
        out = (r.stdout or "") + (r.stderr or "")
        # 只显示尾部关键信息
        lines = [l for l in out.splitlines() if l.strip()]
        tail = "\n".join(lines[-8:])
        print(f"  退出码: {r.returncode}")
        print(f"  --- 尾部输出 ---\n{tail}")
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  ✗ 超时(30min)")
        return False
    except Exception as e:
        print(f"  ✗ 运行异常: {e}")
        return False


def main():
    args = sys.argv[1:]
    with_gacha = "--with-gacha" in args
    only = None
    if "--only" in args:
        i = args.index("--only")
        only = set(args[i + 1].split(","))

    print(f"=== FGO 知识库全量同步 === {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"模式: {'含卡池' if with_gacha else '不含卡池(Mooncell)'}" +
          (f" | 仅: {','.join(sorted(only))}" if only else ""))

    results = []
    steps = STEPS + ([GACHA_STEP] if with_gacha else [])
    for name, script, deps, desc in steps:
        if only and name not in only:
            continue
        ok = run_step(name, script, deps, desc)
        results.append((name, desc, ok))

    # 汇总
    print("\n" + "=" * 50)
    print("同步结果汇总:")
    for name, desc, ok in results:
        status = "✅" if ok else ("⏭" if ok is None else "❌")
        print(f"  {status} [{name}] {desc}")

    failed = [r for r in results if r[2] is False]
    if failed:
        print(f"\n⚠ {len(failed)} 项失败: {', '.join(r[0] for r in failed)}")
        print("请检查上方对应脚本输出，修复后重跑（脚本幂等，可重复执行）")
        sys.exit(1)
    print("\n✅ 全部完成")


if __name__ == "__main__":
    main()
