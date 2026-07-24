#!/usr/bin/env python3
"""FGO 概念礼装知识库生成器 v1"""

import json, os, sys, re
from datetime import datetime
import urllib.request
import urllib.error

WIKI = os.path.expanduser("~/fgo-wiki")

RARITY_STARS = {1: "★", 2: "★★", 3: "★★★", 4: "★★★★", 5: "★★★★★"}
TYPE_LABELS = {
    "servantEquip": "牵绊礼装",
    "normal": "普通礼装",
    "heroine": "剧情礼装",
    "eventReward": "活动奖励",
    "limited": "限定礼装",
    "storyLimited": "剧情限定",
    "valentine": "情人节礼物",
}


def fetch_ce(cn: int) -> dict:
    """Fetch CE data from Atlas API, trying CN first then JP fallback."""
    # Try CN
    urls = [
        f"https://api.atlasacademy.io/nice/CN/equip/{cn}?lore=true",
        f"https://api.atlasacademy.io/nice/JP/equip/{cn}?lore=true",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "fgo-wiki/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if "JP" in url and e.code == 404:
                return None
            continue
        except Exception:
            continue
    return None


def format_effect(text: str) -> str:
    """Extract effect description from HTML-encoded skill text."""
    if not text:
        return "—"
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities
    import html
    text = html.unescape(text)
    # Replace HTML-encoded line breaks
    text = text.replace("\\n", "\n").replace("\r\n", "\n")
    # Clean up multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def generate(data: dict) -> str:
    """Generate markdown from CE JSON data."""
    name = data.get("name", "?")
    cn = data.get("collectionNo", data.get("id", "?"))
    rarity = data.get("rarity", 1)
    stars = RARITY_STARS.get(rarity, "★")
    ctype = data.get("type", "normal")
    type_label = TYPE_LABELS.get(ctype, ctype)
    flag = data.get("flag", "")
    cost = data.get("cost", "?")
    lv_max = data.get("lvMax", "?")
    atk_base = data.get("atkBase", 0)
    atk_max = data.get("atkMax", 0)
    hp_base = data.get("hpBase", 0)
    hp_max = data.get("hpMax", 0)

    lines = [f"# {name}", ""]
    lines.append(f"> **ID**: {data.get('id','?')} | **图鉴编号**: {cn} | **星级**: {stars} | **COST**: {cost}")
    if flag:
        lines.append(f"> **类型**: {type_label}")
    lines.append("")

    # 基础信息
    lines.append("## 基础信息")
    lines.append("")
    lines.append("| 属性 | 值 |")
    lines.append("|------|-----|")
    lines.append(f"| 名称 | {name} |")
    if data.get("originalName") and data["originalName"] != name:
        lines.append(f"| 日文名称 | {data['originalName']} |")
    if type_label:
        lines.append(f"| 类型 | {type_label} |")
    lines.append(f"| 星级 | {stars} |")
    lines.append(f"| COST | {cost} |")
    lines.append(f"| 等级上限 | {lv_max} |")
    lines.append("")

    # 数值
    lines.append("## 数值")
    lines.append("")
    lines.append("| 属性 | Lv.1 | Lv.MAX |")
    lines.append("|------|------|--------|")
    lines.append(f"| ATK | {atk_base} | {atk_max} |")
    lines.append(f"| HP | {hp_base} | {hp_max} |")
    lines.append("")

    # 技能效果
    skills = data.get("skills", [])
    if skills:
        lines.append("## 技能效果")
        lines.append("")
        for skill in skills:
            skill_name = skill.get("name", "?")
            priority = skill.get("priority", 0)
            detail = format_effect(skill.get("detail", ""))

            if not detail:
                continue

            if priority == 2:
                lines.append(f"### 满破效果")
            else:
                lines.append(f"### 未破效果")

            lines.append("")
            if skill.get("icon"):
                icon_url = skill["icon"]
                lines.append(f"![]({icon_url})")
                lines.append("")
            lines.append(f"- **效果**：{detail}")
            lines.append("")

    # 画师与声优
    illustrator = data.get("illustrator", "")
    cv = data.get("cv", "")
    if illustrator or cv:
        lines.append("## 画师与声优")
        lines.append("")
        if illustrator:
            lines.append(f"- **画师**：{illustrator}")
        if cv:
            lines.append(f"- **声优**：{cv}")
        lines.append("")

    # 背景描述
    comments = data.get("comments", [])
    if comments:
        comment_text = comments[0].get("comment", "")
        if comment_text:
            lines.append("## 背景描述")
            lines.append("")
            lines.append(comment_text)
            lines.append("")

    # 视觉资源
    lines.append("## 视觉资源")
    lines.append("")

    extra = data.get("extraAssets", {})

    # Card graphics
    chara = extra.get("charaGraph", {})
    if chara:
        lines.append("### 卡面")
        for asc in sorted(chara.keys()):
            val = chara[asc]
            if isinstance(val, dict):
                for sid, url in val.items():
                    lines.append(f"![]({url})")
            else:
                lines.append(f"![]({val})")
        lines.append("")

    # Faces
    faces = extra.get("faces", {})
    if faces:
        lines.append("### 头像")
        for asc in sorted(faces.keys()):
            val = faces[asc]
            if isinstance(val, dict):
                for sid, url in val.items():
                    lines.append(f"![]({url})")
            else:
                lines.append(f"![]({val})")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"*数据来源: Atlas Academy API* | *最后更新: {datetime.now().strftime('%Y-%m-%d')}*")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_ce.py <collectionNo>")
        sys.exit(1)

    cn = int(sys.argv[1])
    print(f"Fetching CE #{cn}...")

    data = fetch_ce(cn)
    if data is None:
        print(f"Error: CE #{cn} not found (tried CN and JP)")
        sys.exit(1)

    # Skip 1-2 star, only import 3★~5★
    rarity = data.get("rarity", 1)
    if rarity < 3:
        name = data.get("name", f"#{cn}")
        print(f"Skipped: {name} ({RARITY_STARS.get(rarity,'?')})")
        sys.exit(0)

    # Save raw JSON
    raw_dir = os.path.join(WIKI, "raw/craft-essences")
    os.makedirs(raw_dir, exist_ok=True)
    raw_path = os.path.join(raw_dir, f"{cn}.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Raw saved: {raw_path}")

    # Generate markdown
    md = generate(data)
    name = data.get("shortName") or data.get("name", str(cn))
    name = re.sub(r'\s+', ' ', name).replace("/", "·").replace("\\", "").strip()
    entity_dir = os.path.join(WIKI, "entities/craft-essences")
    os.makedirs(entity_dir, exist_ok=True)
    entity_path = os.path.join(entity_dir, f"{name}.md")
    with open(entity_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Generated: {entity_path} ({len(md)} chars)")


if __name__ == "__main__":
    main()
