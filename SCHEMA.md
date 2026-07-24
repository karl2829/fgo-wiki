# FGO 从者知识库 Schema

## 领域
Fate/Grand Order (FGO) 从者数据知识库。覆盖所有从者的基础信息、数值、技能、宝具、资料、材料需求。

## 数据来源
- Atlas Academy API: `https://api.atlasacademy.io/nice/CN/servant/{id}?lore=true`
- 从者列表: `https://api.atlasacademy.io/export/CN/basic_servant.json`
- 区域优先: CN（国服）→ JP（日服）回退

## 目录结构
```
~/fgo-wiki/
├── SCHEMA.md           # 本文件
├── index.md            # 从者总目录
├── log.md              # 操作日志
├── generate.py         # 生成脚本
├── raw/servants/       # 原始 API JSON（{id}.json）
└── entities/servants/  # 生成的 Markdown 从者页面（{name}.md）
```

## 从者页面结构
每个从者页面的固定章节（按顺序）：
1. 标题 + ID/编号/职阶/星级摘要
2. 基础信息表格
3. 数值表格（ATK/HP/六维参数）
4. Hit 信息表格
5. 技能（持有技能 + 职阶技能）
6. 宝具
7. 视觉资源（头像/卡面）
8. 资料（画师/声优 + 资料1~N）
9. 材料需求（灵基再临表格）
10. 页脚（数据来源 + 更新日期）

## 字段映射规则
| 页面字段 | JSON 路径 |
|----------|----------|
| id | .id |
| collectionNo | .collectionNo |
| name | .name |
| originalName | .originalName |
| className | .className |
| rarity | .rarity |
| cost | .cost |
| attribute | .attribute → 天/地/人/星/兽 映射 |
| alignment | .limits[0].policy + .limits[0].personality → 秩序·善 等 |
| gender | .gender → 女性/男性 映射 |
| atkBase / atkMax | .atkBase / .atkMax |
| hpBase / hpMax | .hpBase / .hpMax |
| 筋力/耐久/敏捷/魔力/幸运/宝具 | .limits[0].{strength,endurance,agility,magic,luck,np} |
| hits | .hitsDistribution → 统计每张卡牌的 hit 数量 |
| skills | .skills → 提取 name, coolDown, 效果描述 |
| classPassive | .classPassive → 提取 name, 效果描述 |
| np | .noblePhantasms[0] → name, rank, card, type, 效果描述 |
| faces | .extraAssets.faces.ascension[1] |
| ascension | .extraAssets.charaGraph.ascension[1] |
| illustrator | .profile.illustrator |
| cv | .profile.cv |
| profile | .profile.comments → 每个 comment 的 id 作为标题，comment 作为内容 |
| ascensionMaterials | .ascensionMaterials → items 中每项的 item.name + amount |

## 技能效果描述规则
- funcType 映射为中文名（查 FUNCTYPE_NAMES 表）
- 效果值取 Lv1 和 Lv10 的范围（如 "30% → 50%"）
- 不变时只显示一个值
- Value > 100 时除以 10 加 %（游戏中千分比表示）
- Turn/Count 附加回合/次数信息

## Tag 分类
- 职阶: saber, archer, lancer, rider, caster, assassin, berserker, ruler, avenger, alterego, mooncancer, foreigner, pretender, shielder
- 星级: 1star ~ 5star
- 属性: sky, earth, human, star, beast
- 阵营: lawful, chaotic, neutral, good, evil, balanced

## 更新策略
- 每次 ingest 时检查 SHA256，跳过未变化的源数据
- 如果 API 返回的 JSON 与已有 raw/ 不同，更新 raw/ 并重新生成页面
- 新增从者时同步更新 index.md
- 所有操作记录到 log.md

## 页面命名
- raw/servants/{id}.json — 以内部 ID 命名
- entities/servants/{name}.md — 以从者名命名，/ 替换为 ·
