#!/bin/bash
# ~/fgo-wiki/scripts/fetch_mooncell_quest.sh
# 用法：./fetch_mooncell_quest.sh "因陀罗的大试炼 ～巡回破裂天空～"

ACTIVITY_NAME="$1"
if [ -z "$ACTIVITY_NAME" ]; then
    echo "用法: ./fetch_mooncell_quest.sh '活动名称'"
    exit 1
fi

echo "📡 正在爬取: $ACTIVITY_NAME"

python3 << PYEOF
import sys
import re
import json
from pathlib import Path
from datetime import datetime
import requests
from bs4 import BeautifulSoup

ACTIVITY = sys.argv[1] if len(sys.argv) > 1 else "因陀罗的大试炼 ～巡回破裂天空～"

MOONCELL_API = "https://fgo.wiki/api.php"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 1. 搜索确认页面标题
def find_page(activity):
    params = {"action": "query", "list": "search", "srsearch": f"{activity} 关卡配置", "format": "json"}
    resp = requests.get(MOONCELL_API, params=params, headers=HEADERS, timeout=10)
    data = resp.json()
    for result in data.get("query", {}).get("search", []):
        title = result.get("title", "")
        if "关卡配置" in title:
            return title
    return None

# 2. 获取页面 HTML
def get_page_html(title):
    params = {"action": "parse", "page": title, "format": "json", "prop": "text"}
    resp = requests.get(MOONCELL_API, params=params, headers=HEADERS, timeout=10)
    data = resp.json()
    if "parse" in data:
        return data["parse"]["text"]["*"]
    print(f"❌ 获取失败: {data}")
    return None

# 3. 解析敌人
def parse_enemy(text):
    # 匹配: [穢れた騎士] Lv.47([剑])HP 30,048
    pattern = r'\[(.*?)\]\s*Lv\.(\d+)\(\[(.*?)\]\)HP\s*([\d,]+)'
    match = re.search(pattern, text)
    if match:
        return {"name": match.group(1).strip(), "level": int(match.group(2)), "class": match.group(3).strip(), "hp": int(match.group(4).replace(",", ""))}
    return None

# 4. 解析关卡表格
def parse_table(table):
    rows = table.find_all("tr")
    if not rows:
        return None
    # 提取关卡名
    first_text = rows[0].get_text(strip=True) if rows else ""
    name = ""
    if "进行度" in first_text:
        name = first_text.split("进行度")[0].strip()
    elif "推荐Lv." in first_text:
        name = first_text.split("推荐Lv.")[0].strip()
    else:
        name = first_text[:30]
    # 提取敌人
    enemies = []
    for row in rows:
        cells = row.find_all("td")
        for cell in cells:
            text = cell.get_text(strip=True)
            if "[" in text and "Lv." in text and "HP" in text:
                enemy = parse_enemy(text)
                if enemy:
                    enemies.append(enemy)
    return {"name": name, "enemies": enemies}

# 5. 主流程
title = find_page(ACTIVITY)
if not title:
    print(f"❌ 未找到: {ACTIVITY}")
    sys.exit(1)

print(f"✅ 找到页面: {title}")
html = get_page_html(title)
if not html:
    sys.exit(1)

soup = BeautifulSoup(html, "html.parser")
tables = soup.find_all("table", class_="wikitable")

quests = []
for table in tables:
    data = parse_table(table)
    if data and data["enemies"]:
        quests.append(data)

print(f"📊 解析到 {len(quests)} 个关卡")

# 6. 更新 MD 文件
md_path = Path.home() / "fgo-wiki" / "entities" / "events" / f"{ACTIVITY}.md"
if not md_path.exists():
    print(f"⚠️ 活动文件不存在: {md_path}")
    sys.exit(1)

content = md_path.read_text(encoding="utf-8")
if "## 关卡配置" in content:
    content = content.split("## 关卡配置")[0].strip()

new_section = f"\n\n## 关卡配置\n\n> 来源: Mooncell | {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
for q in quests:
    new_section += f"### {q['name']}\n\n"
    if q["enemies"]:
        new_section += "| 敌人 | 职阶 | 等级 | HP |\n|---|---|---|---|\n"
        for e in q["enemies"]:
            new_section += f"| {e['name']} | {e['class']} | {e['level']} | {e['hp']} |\n"
    new_section += "\n"

md_path.write_text(content + new_section, encoding="utf-8")
print(f"✅ 已更新: {md_path}")
PYEOF
