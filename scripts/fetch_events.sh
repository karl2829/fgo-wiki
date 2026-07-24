#!/bin/bash
# FGO 活动数据拉取脚本 v1
# 用法: bash fetch_events.sh <event_id>
# 示例: bash fetch_events.sh 80549

set -e
WIKI=~/fgo-wiki
EVENT_ID=${1:?Usage: bash fetch_events.sh <event_id>}

echo "=== 拉取活动 #${EVENT_ID} ==="

# 1. 拉取活动详情
mkdir -p $WIKI/raw/events $WIKI/entities/events $WIKI/raw/wars $WIKI/entities/wars
curl -s "https://api.atlasacademy.io/nice/CN/event/${EVENT_ID}?lore=true" -o $WIKI/raw/events/${EVENT_ID}.json
echo "✓ 活动 JSON 已保存"

# 2. 生成活动 Markdown
python3 $WIKI/generate_events.py ${EVENT_ID}
echo "✓ 活动 Markdown 已生成"

# 3. 提取 warIds 并拉取 War 数据
WAR_IDS=$(python3 -c "
import json
with open('$WIKI/raw/events/${EVENT_ID}.json') as f:
    d = json.load(f)
print(' '.join(str(w) for w in d.get('warIds', [])))
")

if [ -n "$WAR_IDS" ]; then
    for wid in $WAR_IDS; do
        echo ""
        echo "=== 拉取 War #${wid} ==="
        curl -s "https://api.atlasacademy.io/nice/CN/war/${wid}?lore=true" -o $WIKI/raw/wars/${wid}.json
        echo "✓ War JSON 已保存"

        # Generate War Markdown with main/free quest separation
        python3 -c "
import json, os, urllib.request
from datetime import datetime

with open('$WIKI/raw/wars/${wid}.json') as f:
    war = json.load(f)

# Fetch quest details
quest_details = {}
for sp in war.get('spots', []):
    for q in sp.get('quests', []):
        qid = q['id']
        try:
            url = f'https://api.atlasacademy.io/nice/CN/quest/{qid}?lang=en'
            req = urllib.request.Request(url, headers={'User-Agent':'fgo-wiki/1.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                quest_details[qid] = json.loads(resp.read())
        except:
            quest_details[qid] = {}

# Separate
main_q, free_q = [], []
for sp in war.get('spots', []):
    sn = sp.get('name','?')
    for q in sp.get('quests', []):
        e = {'id':q['id'],'name':q.get('name','?'),'type':q.get('type','main'),'spot':sn,'d':quest_details.get(q['id'],{})}
        (main_q if e['type']=='main' else free_q).append(e)

lines = [f'# {war.get(\"name\",str(${wid}))}', '',
         f'> **ID**: {war[\"id\"]} | **类型**: event',
         '', '## 地图信息', '',
         '| 属性 | 值 |', '|------|-----|',
         f'| War ID | {war[\"id\"]} |',
         f'| 名称 | {war.get(\"name\",\"?\")} |',
         '', '## 主线关卡', '',
         '| 小节 | 关卡名称 | 地点 | 报酬 |',
         '|------|----------|------|------|']
for mq in main_q:
    d = mq['d']; sub = d.get('chapterSubId', d.get('chapterSubStr', '?'))
    gifts = d.get('gifts', [])
    rw = ', '.join(f'{g.get(\"type\",\"?\")}#{g.get(\"objectId\",\"?\")} x{g.get(\"num\",1)}' for g in gifts) if gifts else '—'
    lines.append(f'| {sub} | {mq[\"name\"]} | {mq[\"spot\"]} | {rw} |')

lines += ['', '## 自由关卡', '',
          '| 关卡 ID | 推荐等级 | 关卡名称 | 报酬 | 掉落物 | 敌配置 |',
          '|---------|----------|----------|------|--------|--------|']
for fq in free_q:
    d = fq['d']; rlv = d.get('recommendLv', '?')
    gifts = d.get('gifts', [])
    rw = ', '.join(f'{g.get(\"type\",\"?\")}#{g.get(\"objectId\",\"?\")} x{g.get(\"num\",1)}' for g in gifts) if gifts else '—'
    lines.append(f'| {fq[\"id\"]} | {rlv} | {fq[\"name\"]} | {rw} | 待补充 | 待补充 |')

lines += ['',
          f'**总计**：{len(main_q)} 个主线关卡 + {len(free_q)} 个自由关卡 = {len(main_q)+len(free_q)} 关',
          '', f'*数据来源: Atlas Academy API* | *最后更新: {datetime.now().strftime(\"%Y-%m-%d\")}*']

os.makedirs('$WIKI/entities/wars', exist_ok=True)
with open(f'$WIKI/entities/wars/{wid}.md', 'w') as f:
    f.write('\n'.join(lines))
print(f'✓ War Markdown 已生成: entities/wars/{wid}.md')
"
    done
fi

echo ""
echo "=== 完成 ==="
ls -la $WIKI/entities/events/ $WIKI/entities/wars/ 2>/dev/null | tail -5
