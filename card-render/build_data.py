"""从 ~/fgo-wiki 的 MD 实体生成 data/<servant_id>.json（卡片数据源）。

原则：文本数据全部从 MD 文件解析，不读 Atlas API、不做数值补算。
例外（MD 未收录的字段）：宝具日文原名从 raw/*.json 兜底，缺则留空。

用法：
  .venv/bin/python build_data.py 100100          # 内部 ID
  .venv/bin/python build_data.py 100100 --no-assets
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WIKI = Path.home() / "fgo-wiki"
ASSETS = ROOT / "assets"

RANK_RE = re.compile(r"^(EX|[A-E]\+{0,2})$")

# fgo-wiki MD 里有些宝具效果标题直接是 Atlas 的 funcType（damageNp / gainStar …），
# 那是数据缺口不是效果名。这里按游戏内标准叫法兜底，方向/目标不明确的一律中性表述。
FUNC_LABELS = {
    "damageNp": "对敌方发动强大的攻击",
    "damageNpIndividual": "对敌方单体发动强大的攻击",
    "damageNpIndividualSum": "对敌方单体发动强大的攻击",
    "damageNpPierce": "对敌方发动无视防御的攻击",
    "gainStar": "获得暴击星",
    "gainNp": "宝具值增加",
    "lossNp": "宝具值减少",
    "lossHp": "HP 减少",
    "delayNpturn": "延迟宝具充能",
    "subState": "解除状态",
    "instantDeath": "即死效果",
    "forceInstantDeath": "必定即死",
    "moveToLastSubmember": "移动到替补席最后",
    "addState": "付与状态",
}
FUNC_KEY_RE = re.compile(r"^[a-z][A-Za-z0-9_]*$")


def resolve_func_key(desc: str, np_kind: str = "") -> str:
    """把 funcType 标题翻成中文；none 返回空串（该效果整条丢弃）。"""
    if desc == "none":
        return ""
    label = FUNC_LABELS.get(desc)
    if label is None:
        return desc                      # 不是内部键，原样返回
    # 攻击类：按宝具类型补「单体/全体」，这是游戏内固定说法，不算编造
    if desc.startswith("damageNp") and "单体" not in label:
        if "对人" in np_kind:
            return "对敌方单体发动强大的攻击"
        if np_kind.endswith("宝具"):
            return "对敌方全体发动强大的攻击"
    return label
VALUE_RE = re.compile(r"^[+\-]?\d+(?:\.\d+)?\s*(?:%|個|个|星|枚|次|回合)?$")     # 无等级差异的固定值行
TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")


def has_kana(t: str) -> bool:
    """是否含日文假名（用来判定字段是真日文还是中文占位）。"""
    return any("\u3040" <= c <= "\u30ff" for c in t or "")


def _wiki(p: str) -> Path:
    return WIKI / p


def _table_rows(block: str) -> list[list[str]]:
    rows = []
    for line in block.splitlines():
        m = TABLE_ROW.match(line.strip())
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        if all(set(c) <= set("-: ") for c in cells):      # 分隔行
            continue
        rows.append(cells)
    return rows


def _kv(rows: list[list[str]]) -> dict[str, str]:
    out = {}
    for r in rows:
        if len(r) >= 2 and r[0]:
            out[r[0]] = r[1]
    return out


def _section(text: str, title: str) -> str:
    """取 `## title` 到下一个同级标题之间的内容。"""
    m = re.search(rf"^##\s+{re.escape(title)}\s*$(.*?)(?=^##\s+\S|\Z)", text, re.S | re.M)
    return m.group(1) if m else ""


def parse_skills(text: str, keep_all: bool = False) -> list[dict]:
    """解析持有技能：去掉「国服未实装」与「强化前」旧版本，只留当前国服版本。"""
    body = _section(text, "持有技能")
    superseded = set(re.findall(r"◈\s*强化前：(\S+)", text))      # 被强化顶掉的旧技能名
    # 「⚠ 国服未实装：日服已强化为「X」」里的 X 是日服版本，国服不出
    unimplemented = set(re.findall(r"国服未实装：日服已强化为「(.+?)」", text))

    blocks, cur = [], None
    for line in body.splitlines():
        m = re.match(r"^###\s+!\[\]\((\S+?)\)\s+(.+?)\s{2,}充能时间：([\d→\-]+)\s*$", line.strip())
        if m:
            cur = {"icon_url": m.group(1), "head": m.group(2).strip(),
                   "cd": m.group(3), "lines": []}
            blocks.append(cur)
            continue
        if cur is not None:
            cur["lines"].append(line)

    skills = []
    for b in blocks:
        parts = b["head"].split()
        rank = parts[-1] if parts and RANK_RE.match(parts[-1]) else ""
        name = " ".join(parts[:-1]) if rank else b["head"]
        full = f"{name} {rank}".strip()
        if not keep_all and (name in superseded or full in superseded
                             or name in unimplemented or full in unimplemented):
            continue

        effects, pending = [], None
        for line in b["lines"]:
            s = line.strip()
            if not s:
                continue
            if s.startswith("|"):
                rows = _table_rows(s)
                if rows and rows[0] and rows[0][0].startswith("Lv.1"):
                    continue
                if rows and rows[0] and rows[0][0].startswith("Lv.") is False:
                    vals = rows[0]
                    if pending is None:
                        pending = {"desc": "", "values": None}
                        effects.append(pending)
                    pending["values"] = vals
                    pending = None
                continue
            if s.startswith(("⚠", "◈", "开放条件", "此技能由", "###", "##")):
                continue
            if VALUE_RE.match(s):                      # 固定值（如「宝具值增加」下的 30%）
                if effects and effects[-1]["values"] is None and not effects[-1].get("fixed"):
                    effects[-1]["fixed"] = s
                else:
                    effects.append({"desc": "", "values": None, "fixed": s})
                pending = None
                continue
            effects.append({"desc": s.rstrip("▲").strip(), "values": None})
            pending = effects[-1]

        skills.append({
            "name": name,
            "rank": rank,
            "cd": b["cd"],
            "icon": b["icon_url"].rsplit("/", 1)[-1],
            "effects": [e for e in effects if e["desc"] or e["values"] or e.get("fixed")],
        })
    return skills


def parse_np(text: str, sid: str, region: str = "CN") -> dict:
    """解析宝具：优先取「强化后」段，无则取「未强化/强化前」段。"""
    body = _section(text, "宝具")
    parts = re.split(r"^\*\*(未强化|强化前|强化后)\*\*\s*$", body, flags=re.M)
    # parts = [前言, 标签1, 内容1, 标签2, 内容2, ...]
    segs = [(parts[i].strip(), parts[i + 1]) for i in range(1, len(parts) - 1, 2)]
    if not segs:
        segs = [("", body)]
    pick = next((seg for seg in segs if seg[0] == "强化后"), segs[-1])
    label, block = pick
    note = {"未强化": "", "强化前": "", "强化后": "强化后"}.get(label, "")

    m = re.search(r"^###\s+!\[\]\((\S+?)\)\s+(.+)$", block, re.M)
    name = m.group(2).strip() if m else ""
    info = _kv(_table_rows(block))
    rank = info.get("等级", "")
    card = info.get("卡色", "")
    kind = info.get("类型", "")

    effects = []
    for line in block.splitlines():
        s2 = line.strip()
        if not s2 or s2.startswith(("###", "|---")):
            continue
        if s2.startswith("|"):                      # 数值行 / 属性表
            rows = _table_rows(s2)
            if not rows or rows[0][0] in ("属性", "等级", "卡色", "类型"):
                continue
            if re.match(r"^(Lv\.1|OC1)", rows[0][0]):
                continue
            if effects and effects[-1]["values"] is None:
                effects[-1]["values"] = rows[0]
            continue
        mf = re.match(r"^固定值[:：]\s*(.+)$", s2)
        if mf and effects:
            effects[-1]["fixed"] = mf.group(1).strip()
            continue
        me = re.match(r"^\*\*(.+?)\*\*\s*(?:<(.+?)>)?\s*$", s2)
        if me:
            inner, outer_hint = me.group(1), me.group(2)
            mh = re.search(r"<(.+?)>", inner)       # hint 写在加粗内部的写法
            hint = outer_hint or (mh.group(1) if mh else "")
            desc = re.sub(r"<[^>]*>", "", inner).strip()
            resolved = resolve_func_key(desc, kind)
            effects.append({"desc": resolved,
                            "hint": f"〈{hint.strip()}〉" if hint else "",
                            "values": None,
                            "_drop": not resolved})
            continue

    sub = ""
    raw = _wiki(f"raw/servants/{region}/{sid}.json")
    if raw.exists():
        try:
            rd = json.loads(raw.read_text(encoding="utf-8"))
            nps = rd.get("noblePhantasms") or []
            if nps:
                np0 = nps[0]
                cn, orig, ruby = (np0.get("name") or "", np0.get("originalName") or "",
                                  np0.get("ruby") or "")
                sub = "　／　".join([x for x in (orig if orig and orig != cn else "", ruby) if x])
        except Exception:
            sub = ""

    scope = ""
    for e in effects:                       # 攻击范围看含「全体/单体」的那条效果
        d = e["desc"]
        if "全体" in d:
            scope = "全体攻击"
            break
        if "单体" in d:
            scope = "单体攻击"
            break

    chips = []
    if card:
        chips.append([card, f"c-{card.lower()}"])
    if kind:
        chips.append([kind, "c-blue"])
    if scope:
        chips.append([scope, "c-ghost"])

    kept = []
    for e in effects:
        if e.pop("_drop", False):
            continue
        if e["desc"] or e["values"] or e.get("fixed"):
            kept.append(e)
    return {"name": name, "sub": sub, "rank": rank, "note": note, "chips": chips,
            "effects": kept}


def load_jp(sid: str) -> dict:
    """读日服 MD，取真日文名（从者 / 技能 / 宝具）。"""
    md = _wiki(f"entities/servants/JP/{sid}.md")
    if not md.exists():
        return {}
    t = md.read_text(encoding="utf-8")
    base = _kv(_table_rows(_section(t, "基础信息")))
    name_jp = ""
    for cand in (base.get("名称", ""), base.get("原始名称（日文）", "")):
        if has_kana(cand):                       # 名称被人工改成中文时退回原始名称
            name_jp = cand
            break
    jp_np = parse_np(t, sid, region="JP")
    return {"name_jp": name_jp, "skills": parse_skills(t, keep_all=True), "np": jp_np}


def _skill_sig(sk: dict) -> tuple:
    """技能签名：(等级, 充能, 全部效果数值链) —— 中日两版据此配对，避免同名同数值撞车。"""
    chain = tuple(tuple(e["values"]) if e.get("values") else () for e in sk.get("effects", []))
    return (sk.get("rank", ""), sk.get("cd", ""), chain)


def parse_bond(text: str, sid: str) -> dict:
    m = re.search(r"\*\*羁绊礼装\*\*:\s*\[\[礼装/(\d+)\]\]", text)
    if not m:
        return {}
    ce_id = m.group(1)
    ce_md = _wiki(f"entities/craft-essences/CN/{ce_id}.md")
    if not ce_md.exists():
        return {}
    ct = ce_md.read_text(encoding="utf-8")
    head = ct.splitlines()[0].lstrip("# ").strip()
    meta = _kv(_table_rows(_section(ct, "基础信息")))
    img = ""
    raw = _wiki(f"raw/craft-essences/CN/{ce_id}.json")
    if raw.exists():
        try:
            rd = json.loads(raw.read_text(encoding="utf-8"))
            img = (rd.get("extraAssets", {}).get("charaGraph", {}).get("equip") or {}).get(ce_id, "")
        except Exception:
            img = ""
    return {"name": head, "type": meta.get("类型", ""), "rarity": meta.get("星级", ""),
            "cost": meta.get("COST", ""), "img_url": img}


def parse_servant(sid: str) -> dict:
    md_path = _wiki(f"entities/servants/CN/{sid}.md")
    text = md_path.read_text(encoding="utf-8")

    name = text.splitlines()[0].lstrip("# ").strip()
    h3 = text.splitlines()[2]
    coll = int(re.search(r"\*\*图鉴编号\*\*:\s*(\d+)", h3).group(1))
    icon_m = re.search(r"!\[\]\((\S*?classes/[a-z_]+?\.png)\)", h3)
    class_icon_url = icon_m.group(1) if icon_m else ""
    cls_m = re.search(r"classes/([a-z]+)_([a-z]+)\.png", h3)
    klass = cls_m.group(1) if cls_m else ""
    rarity = h3.count("★")

    base = _kv(_table_rows(_section(text, "基础信息")))
    stats = _kv(_table_rows(_section(text, "数值")))

    cards = [m.group(1) for m in re.finditer(r"cards/(\w+)\.png", base.get("指令卡", ""))]
    traits = [t.strip() for t in base.get("特性", "").split("、") if t.strip()]

    hexes = [[k, stats.get(k, "")] for k in ("筋力", "耐久", "敏捷", "魔力", "幸运")]

    # 满级等级跟着从者上限走（1★60 / 2★65 / 3★70 / 4★80 / 5★90），取 MD 里最高的「满级」键
    lv = "90"
    _best = 0
    for k in stats:
        m = re.match(r"满级攻击力\(Lv\.(\d+)\)", k)
        if m and int(m.group(1)) > _best:
            _best = int(m.group(1))
    if _best:
        lv = str(_best)
    atk = stats.get(f"满级攻击力(Lv.{lv})", "")
    hp = stats.get(f"满级 HP(Lv.{lv})", "")

    shiryo = _section(text, "资料")
    artist = re.search(r"\*\*画师\*\*:\s*(\S+)", shiryo)
    cv = re.search(r"\*\*声优\*\*:\s*(\S+)", shiryo)

    vis = _section(text, "视觉资源")
    art_urls = re.findall(r"CharaGraph/\d+/(\S+?\.png)", vis)
    art_url = f"https://static.atlasacademy.io/CN/CharaGraph/{sid}/{art_urls[-1]}" if art_urls else ""

    jp = load_jp(sid)
    jp_map = {_skill_sig(k): k["name"] for k in jp.get("skills", [])}

    # 技能 id 跨服一致，优先用它配日文名；id 缺失（如日服已强化换代）再退签名匹配
    cn_ids, jp_by_id = {}, {}
    for region, bucket in (("CN", "cn"), ("JP", "jp")):
        fp = _wiki(f"raw/servants/{region}/{sid}.json")
        if not fp.exists():
            continue
        try:
            rj = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if bucket == "cn":
            # CN raw 里同时含「强化前」旧技能，不能按索引对齐，用中文名建表
            cn_ids = {x.get("name", ""): x.get("id") for x in (rj.get("skills") or [])}
        else:
            jp_by_id = {x.get("id"): x.get("name", "") for x in (rj.get("skills") or [])}

    cn_skills = parse_skills(text)
    for sk in cn_skills:
        key = cn_ids.get(sk["name"]) if isinstance(cn_ids, dict) else None
        if not key:                             # 名称不完全一致（如带等级后缀差异）再按前缀找
            for nm, sid_v in (cn_ids.items() if isinstance(cn_ids, dict) else []):
                if nm.split()[0] == sk["name"].split()[0] and nm.split()[-1] == sk.get("rank", ""):
                    key = sid_v
                    break
        sk["name_jp"] = (jp_by_id.get(key) or jp_map.get(_skill_sig(sk)) or "")

    np_cn = parse_np(text, sid, region="CN")
    np_jp = jp.get("np") or {}
    np_cn["name_jp"] = np_jp.get("name", "")
    ruby = np_jp.get("sub", "")                 # JP raw 的 ruby（读音/英文名）
    np_cn["sub"] = "　／　".join(x for x in (np_cn["name_jp"], ruby) if x) or np_cn.get("sub", "")

    return {
        "servant_id": int(sid),
        "collection_no": coll,
        "no": f"{coll:03d}",
        "name": name,
        "name_jp": jp.get("name_jp") or base.get("原始名称（日文）", ""),
        "class": klass,
        "rarity": rarity,
        "gender": base.get("性别", ""),
        "alignment": base.get("属性", ""),
        "camp": base.get("阵营", ""),
        "limited": base.get("卡池", ""),
        "traits": traits,
        "cards": cards,
        "atk": int(atk.replace(",", "")) if atk.replace(",", "").isdigit() else atk,
        "hp": int(hp.replace(",", "")) if hp.replace(",", "").isdigit() else hp,
        "level": lv,
        "hex": hexes,
        "npgain": stats.get("NP获得率(攻击)", ""),
        "skills": cn_skills,
        "np": np_cn,
        "artist": artist.group(1) if artist else "",
        "cv": cv.group(1) if cv else "",
        "bond": parse_bond(text, sid),
        "art_url": art_url,
        "class_icon_url": class_icon_url,
        "art_pos": "50% 5%",
    }


def _download(url: str, dest: Path) -> bool:
    if not url:
        return False
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            dest.write_bytes(r.read())
        return True
    except Exception as e:
        print(f"  ! 下载失败 {url}: {e}", file=sys.stderr)
        return False


def fetch_assets(d: dict) -> None:
    ASSETS.mkdir(exist_ok=True)
    # 职阶图标：优先用 fgo-wiki 本地素材（按稀有度取金/银/铜），其次 CDN
    klass = (d.get("class", "") or "").lower()
    rarity = int(d.get("rarity", 5))
    tier = "gold" if rarity >= 4 else ("silver" if rarity == 3 else "bronze")
    if klass:
        dest = ASSETS / f"{klass}_{tier}.png"
        local = WIKI / "assets/classes" / dest.name
        if not dest.exists():
            if local.exists():
                shutil.copy(local, dest)
                print(f"  职阶图标 → assets/{dest.name}（wiki 本地）")
            elif d.get("class_icon_url") and _download(d["class_icon_url"], dest):
                print(f"  职阶图标 → assets/{dest.name}（CDN）")
    sid = d.get("servant_id")
    wiki_srv = Path(os.path.expanduser("~/fgo-wiki/assets/servants"))
    wiki_srv.mkdir(parents=True, exist_ok=True)

    def _from_library(name: str, url: str, dest: Path) -> bool:
        """素材库优先：assets/servants 里已有就直接复制，没有就下载到库里再复制。"""
        lib = wiki_srv / name
        if not lib.exists():
            if not url or not _download(url, lib):
                return False
        shutil.copy(lib, dest)
        return True

    if d.get("art_url") and _from_library(f"art_{sid}.png", d["art_url"], ASSETS / f"art_{sid}.png"):
        print(f"  立绘 → assets/art_{sid}.png（{d['art_url'].rsplit('/',1)[-1]}）")
    for sk in d["skills"]:
        icon = sk["icon"]
        dest = ASSETS / icon
        if dest.exists():
            continue
        url = next((u for u in
                    (f"https://static.atlasacademy.io/CN/SkillIcons/{icon}",
                     f"https://static.atlasacademy.io/JP/SkillIcons/{icon}")), "")
        if _download(url, dest):
            print(f"  技能图标 → assets/{icon}")
    img = d.get("bond", {}).get("img_url")
    if img and _from_library(f"bondce_{sid}.png", img, ASSETS / f"bond_ce_{sid}.png"):
        print(f"  羁绊礼装 → assets/bond_ce_{sid}.png")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("servant_id")
    ap.add_argument("--no-assets", action="store_true")
    a = ap.parse_args()

    d = parse_servant(a.servant_id)
    if not a.no_assets:
        fetch_assets(d)

    out = ROOT / "data" / f"{a.servant_id}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{out}  No.{d['no']} {d['name']} {d['class']} ★{d['rarity']}")
    print(f"  技能 {len(d['skills'])}： " + " / ".join(f"{s['name']} {s['rank']} cd{s['cd']}" for s in d["skills"]))
    print(f"  宝具 {d['np']['rank']} {d['np']['name']}（{len(d['np']['effects'])} 条效果）")
    print(f"  羁绊礼装 {d['bond'].get('name','—')} {d['bond'].get('rarity','')} COST {d['bond'].get('cost','')}")


if __name__ == "__main__":
    sys.exit(main())
