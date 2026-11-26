"""把从者数据填进通用框架模板，出完整卡。

用法：
  .venv/bin/python make_card.py 100100                 # 数据在 data/100100.json
  .venv/bin/python make_card.py 100100 -o out/card.png
  .venv/bin/python make_card.py 100100 -o out/card_002.png   # 立绘固定取 assets/art_<id>.png

数据只认 data/<id>.json，字段见 data/100100.json；数值必须来自 ~/fgo-wiki 实体文件，
本脚本不做任何补算。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TPL = ROOT / "templates" / "servant_card_data.html"

BREAK_LEVELS = {1, 6, 10}   # 技能本断点：Lv.1 / Lv.6 / Lv.10
HIGHLIGHT_LEVEL = 6         # 高亮常驻断点


def _skill_effect(eff: dict) -> str:
    desc, values, fixed = eff.get("desc", ""), eff.get("values"), eff.get("fixed")
    head = f'<div class="sk-d"><span>{desc}</span>'
    if values:
        head += '<span class="tag">Lv.1–10</span>'
    head += "</div>"

    if not values:                      # 恒定效果 / 无数值效果：都是通栏单格
        body = fixed if fixed else '<span class="empty">∅</span>'
        cls = "vb1" if fixed else "vb1 vb-empty"
        return f'<div class="sk-e">{head}<div class="v1"><div class="{cls}">{body}</div></div></div>'

    cells = []
    for i, v in enumerate(values, start=1):
        cls = "vb"
        mark = '<i class="brk"></i>' if i in BREAK_LEVELS else ""   # Lv.1/6/10 底部金线，不做高亮框
        cells.append(f'<div class="{cls}">{v}{mark}</div>')
    return f'<div class="sk-e">{head}<div class="v10">{"".join(cells)}</div></div>'


def _skill(sk: dict) -> str:
    effects = "".join(_skill_effect(e) for e in sk["effects"])
    jp = f'<span class="nm-jp">{sk["name_jp"]}</span>' if sk.get("name_jp") else ""
    return f'''  <div class="sk">
    <div class="sk-h">
      <img src="../assets/{sk["icon"]}">
      <span class="nm">{sk["name"]}</span>{jp}<span class="rk">{sk["rank"]}</span>
      <span class="sep"></span>
      <span class="sp"></span>
      <span class="cd">充能 <b>{sk["cd"]}</b></span>
    </div>
    {effects}
  </div>'''


def build_skills(skills: list[dict]) -> str:
    body = "\n".join(_skill(s) for s in skills)
    return f'''<div class="sec-h"><span class="bar"></span><span class="t">持有技能</span>
  <span class="line"></span><span class="n">S K I L L S</span></div>

<section class="skills">
{body}
</section>
'''


def _np_effect(eff: dict) -> str:
    values, fixed = eff.get("values"), eff.get("fixed")
    if values:
        body = f'<div class="eb-v">{"".join(f"<div class=\"vb5\">{v}</div>" for v in values)}</div>'
    elif fixed:
        body = f'<div class="eb-v"><div class="vb5 vb5-fix">{fixed}</div></div>'
    else:                               # 无数值效果：通栏单格填 ∅
        body = '<div class="eb-v"><div class="vb5 vb5-fix vb-empty"><span class="empty">∅</span></div></div>' 
    return f'''  <div class="eb">
    <div class="eb-d"><span class="n">{eff["desc"]}</span><span class="h">{eff.get("hint","")}</span></div>
    {body}
  </div>'''


def build_np(np: dict) -> str:
    chips = "".join(f'<div class="chip {c}">{t}</div>' for t, c in np["chips"])
    effects = "\n".join(_np_effect(e) for e in np["effects"])
    note = f'<span class="rk-note">{np["note"]}</span>' if np.get("note") else ""
    return f'''<section class="np">
  <div class="np-head">
    <div class="goldbar"></div>
    <div class="t">宝　具</div>
    <div class="dot"></div>
    <div class="stamp">N O B L E&nbsp;&nbsp;P H A N T A S M</div>
    <div class="spacer"></div>
    <div class="np-rule"></div>
    <div class="np-mark">N P</div>
  </div>
  <div class="name-row">
    <div>
      <div class="np-name">{np["name"]}</div>
      <div class="np-sub">{np["sub"]}</div>
    </div>
    <div class="rank"><span class="rk-lb">R A N K</span><span class="rk-v">{np["rank"]}</span>{note}</div>
  </div>
  <div class="chips">{chips}</div>
  <div class="div-weak"></div>
{effects}
</section>
'''



def _cw(t: str) -> float:
    """字宽估算：中日文字符 1，其余 0.55。"""
    return sum(1.0 if ord(c) > 0x2E80 else 0.55 for c in t)


def build_traits(data: dict, budget: float = 72.0) -> str:
    """特性行：能吃到羁绊加成礼装的条件词置顶金色（用 wiki 特性原词），其余灰白跟随，排不下以 … 收尾。"""
    from cardkit import bondce
    traits = list(data.get("traits", []))
    if not traits:
        return ""
    no = int(data.get("collection_no", 0))
    pool = traits + [data["gender"]] if data.get("gender") else traits   # 性别也是礼装条件
    gold, consumed = bondce.fit(no, pool) if no else ([], set())

    parts, used, truncated = [], 0.0, False
    for w in gold:
        parts.append(("g", w)); used += _cw(w) + 1.8
    for t in traits:
        if t in consumed:
            continue
        if used + _cw(t) + 1.8 > budget:
            truncated = True
            break
        parts.append(("", t)); used += _cw(t) + 1.8

    html = "<i>・</i>".join(
        f'<span class="g">{w}</span>' if c == "g" else f"<span>{w}</span>" for c, w in parts)
    if truncated:
        html += '<i>・</i><span style="color:#5A677D">…</span>'
    return html


def assets_used(html: str) -> list[str]:
    """这张卡实际引用了 assets/ 下哪些文件（拷贝进插件时照单搬）。"""
    return sorted(set(re.findall(r'src="\.\./assets/([^"]+)"', html)))


def build_html(data: dict, hero_only: bool = False) -> str:
    """把从者数据模型填进模板，返回完整 HTML（不落盘、不渲染）。"""
    html = TPL.read_text(encoding="utf-8")
    if hero_only:                       # 只出从者区模版：技能/宝具留空
        html = html.replace("<!--SKILLS-->", "").replace("<!--NP-->", "")
    else:
        html = html.replace("<!--SKILLS-->", build_skills(data["skills"]))
        html = html.replace("<!--NP-->", build_np(data["np"]))

    if not data.get("name_jp") or data.get("name_jp") == data.get("name"):   # 伪日文名不显示
        html = html.replace('    <div class="name-jp">{{NAME_JP}}</div>', "")

    # ---- 头部字段全部来自 data（build_data.py 从 fgo-wiki MD 解析）----
    sid = str(data.get("servant_id") or data.get("id") or "")
    card_icon = {"Quick": "card_Q.png", "Arts": "card_A.png", "Buster": "card_B.png"}
    cards_html = "".join(
        '<img src="../assets/%s">' % card_icon.get(c, "card_A.png") for c in data.get("cards", []))
    hex_data = list(data.get("hex", []))
    if data.get("npgain"):
        hex_data.append(["NP获得", data["npgain"]])
    hex_html = "".join(f'<div class="hx"><i>{k}</i><b>{v}</b></div>' for k, v in hex_data)
    bond = data.get("bond") or {}
    bond_meta = "　·　".join(x for x in [bond.get("type", ""), bond.get("rarity", ""),
                                         f'COST {bond["cost"]}' if bond.get("cost") else ""] if x)
    klass = data.get("class", "")

    # 头部可配字段：星级图标按稀有度取金/银/铜，立绘裁切位置，限定标识
    rarity = int(data.get("rarity", 5))
    tier = "gold" if rarity >= 4 else ("silver" if rarity == 3 else "bronze")
    for k, v in {
        "STARS": f"stars_{rarity}_{tier}_glow.png",
        "ART_POS": data.get("art_pos", "50% 5%"),
        "LIMITED": data.get("limited", ""),
        "TRAITS": build_traits(data),
        "NPG": data.get("npgain", "—"),
        "RNUM": str(rarity),
        "NO": str(data.get("no", "")),
        "NAME": data.get("name", ""),
        "NAME_JP": "" if data.get("name_jp", "") == data.get("name", "") else data.get("name_jp", ""),
        "CLASS_EN": klass.upper(),
        "CLASS_ICON": "%s_%s.png" % (klass, "gold" if rarity >= 4 else ("silver" if rarity == 3 else "bronze")) if klass else "saber_gold.png",
        "ATK": f'{int(data["atk"]):,}' if isinstance(data.get("atk"), int) else data.get("atk", ""),
        "HP": f'{int(data["hp"]):,}' if isinstance(data.get("hp"), int) else data.get("hp", ""),
        "LEVEL": str(data.get("level", "90")),
        "CARDS": cards_html,
        "HEX": hex_html,
        "ARTIST": data.get("artist", ""),
        "CV": data.get("cv", ""),
        "ART": f"art_{sid}.png",
        "BOND_IMG": f"bond_ce_{sid}.png",
        "BOND_NAME": bond.get("name", ""),
        "BOND_META": bond_meta,
    }.items():
        html = html.replace("{{" + k + "}}", str(v))
    return html


def render_data(
    data: dict,
    out: Path,
    *,
    hero_only: bool = False,
    extra_images: dict[str, bytes] | None = None,
    dpr: int = 2,
) -> dict:
    """渲染一个从者数据模型 → PNG（进程内，不再起子进程）。

    extra_images：模板里 src="../assets/art_<id>.png" 这样的资源不在 assets/ 下时，
    用同一个 src 字符串做 key 直接喂 bytes（插件侧艺术缓存就是这样接进来的）。
    """
    from cardkit.render import render_html

    html = build_html(data, hero_only=hero_only)
    sid = str(data.get("servant_id") or data.get("id") or "x")
    built = ROOT / "out" / f"_built_{sid}.html"
    built.parent.mkdir(parents=True, exist_ok=True)
    built.write_text(html, encoding="utf-8")

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    r = render_html(html, out, base=TPL.parent, dpr=dpr, extra_images=extra_images)
    log = f'{r["path"]}  {r["size"][0]}x{r["size"][1]}  {r["ms"]:.0f} ms  {r["bytes"] / 1024:.0f} KB'
    return {"out": str(out), "log": log, "html": html, "render": r, "assets": assets_used(html)}


def render(servant_id: str, out: Path, hero_only: bool = False) -> dict:
    """兼容旧入口：从 data/<内部ID>.json 读数据再渲染。"""
    data = json.loads((ROOT / "data" / f"{servant_id}.json").read_text(encoding="utf-8"))
    return render_data(data, out, hero_only=hero_only)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("servant_id", nargs="?")
    ap.add_argument("--json", default=None, help="直接从数据模型 JSON 渲染（插件侧走这条路）")
    ap.add_argument("--assets-report", action="store_true", help="打印本卡引用的 assets 清单")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--no-art", action="store_true", help="已废弃：立绘固定为 assets/art_<id>.png，此参数仅为兼容旧命令")
    ap.add_argument("--hero-only", action="store_true", help="只渲染从者区（定模版用）")
    args = ap.parse_args()
    sid = args.servant_id
    if args.json:
        data = json.loads(Path(args.json).read_text(encoding="utf-8"))
        sid = sid or str(data.get("servant_id") or "x")
        out = Path(args.out) if args.out else ROOT / "out" / f"card_{sid}.png"
        r = render_data(data, out, hero_only=args.hero_only)
    else:
        if not sid:
            ap.error("要么给内部ID，要么给 --json")
        out = Path(args.out) if args.out else ROOT / "out" / f"card_{sid}.png"
        r = render(sid, out, hero_only=args.hero_only)
    print(r["log"])
    if args.assets_report:
        print("assets:", json.dumps(r["assets"], ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
