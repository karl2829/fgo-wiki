"""羁绊加成礼装反查：读 fgo-wiki 的索引表，得到某从者可吃到的礼装与条件短词。

数据源（唯一）：
  ~/fgo-wiki/entities/bond-ce/从者适配反查.md   —— 从者 → 礼装列表
  ~/fgo-wiki/entities/bond-ce/index.md          —— 礼装编号 → 名称
"""
from __future__ import annotations
import re
from pathlib import Path

WIKI = Path.home() / "fgo-wiki"
REVERSE = WIKI / "entities/bond-ce/从者适配反查.md"
INDEX = WIKI / "entities/bond-ce/index.md"

# 条件原文 → (卡片金色词, 需要的特性)。金色词优先用 wiki 特性原词。
COND_RULES = {
    "〔秩序〕且〔善〕": ("秩序善", ["秩序", "善"]),
    "〔拥有灵衣之人〕": ("持有灵衣之人", ["持有灵衣之人"]),
    "〔秩序〕且〔女性〕": ("秩序女", ["秩序", "女性"]),
    "〔兽科从者〕": ("兽科从者", ["兽科从者"]),
    "〔活在当下的人类〕": ("活在当下的人类", ["活在当下的人类"]),
    "〔中立〕": ("中立", ["中立"]),
}
# 或关系条件单独处理：任一命中即可
COND_ANY = {"〔恶〕或〔星属性〕": ["恶", "星"]}


def _ce_names() -> dict[str, str]:
    names: dict[str, str] = {}
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(No\.\d+)\s*\|\s*\[([^\]]+)\]", line)
        if m:
            names[m.group(1)] = m.group(2)
    return names


def lookup(collection_no: int) -> list[dict]:
    """按图鉴编号取该从者可吃到的限定羁绊礼装。

    返回 [{no, name, cond, short, bonus}]，cond 为原始条件文字。
    """
    names = _ce_names()
    for line in REVERSE.read_text(encoding="utf-8").splitlines():
        if f"(#{collection_no})" not in line:
            continue
        cell = line.rsplit("|", 2)[1]
        out = []
        for seg in cell.split("；"):
            seg = seg.strip()
            if not seg:
                continue
            m = re.search(r"(No\.\d+)", seg)                  # 礼装编号
            b = re.search(r"(\+\d+%)", seg)                   # 加成
            cond = re.sub(r"\s*\+\d+%（No\.\d+）", "", seg).strip("（） ")
            cond = cond.strip("（）")
            if not m:
                continue
            out.append({
                "no": m.group(1),
                "name": names.get(m.group(1), ""),
                "cond": cond,
                "short": COND_RULES.get(cond, (cond, []))[0],
                "bonus": b.group(1) if b else "",
            })
        return out
    return []


def fit(collection_no: int, traits: list[str]) -> tuple[list[str], set[str]]:
    """按该从者实际特性，算出能吃到加成的金色词 + 已被金色词消费的特性。

    只有从者真的具备条件特性时才输出金色词（反查表已按适配过滤，这里再兜一层）。
    """
    have = set(traits)
    gold, consumed = [], set()
    for ce in lookup(collection_no):
        cond = ce["cond"]
        words: list[str] = []
        need: list[str] = []
        if cond in COND_RULES:
            word, need = COND_RULES[cond]
            if all(t in have for t in need):
                words = [word]
        elif cond in COND_ANY:
            hit = [t for t in COND_ANY[cond] if t in have]
            if hit:
                words, need = hit, hit
        for w in words:
            if w not in gold:
                gold.append(w)
        consumed.update(need)
    return gold, consumed


def gold_terms(collection_no: int) -> list[str]:
    """金色礼装适性词（按礼装顺序去重）。"""
    seen, out = set(), []
    for ce in lookup(collection_no):
        t = ce["short"]
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


if __name__ == "__main__":
    import json, sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    print(json.dumps(lookup(n), ensure_ascii=False, indent=2))
    print("gold:", gold_terms(n))
