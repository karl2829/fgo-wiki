# 从者 MD 生成规则

## 数据源
- 原始数据：`raw/servants/{id}.json`
- 图片资源：Atlas Academy CDN

## 核心字段映射

| 字段 | JSON 路径 | 备注 |
|------|-----------|------|
| ID | `id` | |
| 图鉴编号 | `collectionNo` | |
| 名称 | `name` | |
| 原名 | `originalName` / `_jp_name` | |
| 职阶 | `className` | |
| 星级 | `rarity` | ★×N |
| COST | `cost` | |
| 属性 | `attribute` | earth/human/sky/star/beast → 地/人/天/星/兽 |
| 性别 | `gender` | female/male/unknown/none → 女性/男性/不明/无 |
| 阵营 | `alignment.policy` + `alignment.personality` | 秩序·善 等 |
| 获取方式 | `type` + `flag` | 常驻/限定/剧情限定/活动赠送... |
| 画师 | `illustrator` / `profile.illustrator` | |
| 声优 | `cv` / `profile.cv` | |
| 特性标签 | `traits[]` | 过滤黑名单，映射中文 |

## 宝具渲染

### 数据选择
- 使用 `noblePhantasms` 全部宝具，按 priority 排序
- 标签规则：
  - 仅 1 个宝具 → `**未强化**`
  - 2 个宝具，低 priority → `**强化前**`，高 priority → `**强化后**`
- `functions` 数组按 funcId 映射到效果段

### 特攻 OC 标签
- 特攻的 `<Over Charge时特攻威力提升>` 标签仅在 OC 值有变化时显示
- OC 值全相等（固定值）→ 不显示该标签，避免描述与数值矛盾

### 效果解析规则
1. `detail` 字段按 `＋` / `＆` 分割为独立效果描述
2. 每个效果按顺序对应一个 function（funcId 过滤）
3. 效果描述中的 `▲` 仅作视觉标记，分割后从末尾清除

### 特攻特殊处理
当效果描述包含 `〔target〕特攻` 时，拆分为两个独立条目：
- 基础攻击：去掉 `〔target〕特攻` 后的描述 + NP 升级表
- 特攻：`对〔target〕特攻<Over Charge时特攻威力提升>` + OC 表/固定值

### 数值来源映射

| funcType | NP等级值 (Lv.1-5) | OC值 (OC1-5) |
|----------|------------------|--------------|
| damageNp / damageNpIndividual | `svals[0-4].Value` | `svals[0-5].Correction`（优先）|
| gainNp | `svals[0-4].Value` / 100 | `svals[0-5].Value` / 100 |
| addState 概率型 | `svals[0-4].Rate` / 10 | `svals[0-5].Rate` / 10 |
| 其他 | `svals[0-4].Value` / 10 | `svals[0-5].Value` / 10 |

### OC 检测顺序（`get_oc_values()`）
1. **Correction 模式**：`svals[0-5][0].Correction` 5个值不全相等
2. **Value 模式**：`svals[0-5][0].Value` 5个值不全相等
3. **Rate 模式**：`svals[0-5][0].Rate` 5个值不全相等（概率型效果如技能封印）
4. 均不命中 → 取第一个值为固定值，不生成 OC 表

### 强化前内容展示

有强化本的技能（`strengthStatus > 0`），在强化后底部添加：

```
◈ 强化前：{原技能名}

{原技能效果 + 10列表格}

此技能由「{原技能名}」强化而来

开放条件: 从者强化任务 (Quest ID: {quest_id})
```

无强化本的技能不显示上述内容。`strengthStatus == 0` 的技能不输出任何底部标注。

### 文件命名
- 文件名使用 `{内部ID}.md`（如 `100100.md`），避免同名从者覆盖
- 映射文件：`data/servant_id_map.json`（id → {name, collectionNo, className}）
- 名称文件仅用于展示，ID 文件用于数据关联
- 百分号：数值带 `%`
- 纯数字：不带 `%`
- gainNp 保留 1 位小数（27.5%）
- 整数值不显示小数（30%）

## 技能渲染

### 主动技能（10列表格）
- 表头：`Lv.1` ~ `Lv.10`
- 冷却：`充能时间：7→6→5`（只显示变化值）
- 多效果拆分：每效果独立表格
- 固定值（10级无变化）：文字描述，不生成表格

### 职阶技能
- 无等级变化，文字描述
- 格式：`- **[[技能名 等级]]** (ref_path): 效果描述`

### 追加技能
- 同主动技能，10列表格
- 无冷却显示
- 共享引用文件在 `references/skills/append/`

## 材料需求表

### 列结构
| 阶段 | QP | ID | 图标 | 道具名称 | 数量 |

### 图标 URL
**直接按 ID 构造**：`https://static.atlasacademy.io/CN/Items/{item_id}.png`
（忽略 items DB 的 icon 字段，该字段 627/899 条错误）

### 总计表
单独成表，每类材料分别统计：
| ID | 图标 | 道具名称 | 总数 |
最后一行：`| — | — | **QP** | **{total_qp:,}** |`

## 视觉资源
- 头像、卡面、灵基再临图标、模型、灵衣图标
- 使用 Atlas Academy CDN 链接

## 关键函数签名
```python
format_val(v, func_type) -> str
format_np_effects(np_data) -> str
format_skill_detail(sk, icon) -> str
mat_table(title, mats_dict, format_key, offset, show_total) -> str
get_current_skills(skills) -> list
get_scale_div(func_type) -> int  # 0/10/100
```

## 特殊情况
- 多段伤害 NP：每段独立 function，按顺序渲染
- 强化前后 NP 共存：只渲染最后一个（强化版）
- OC 值全等：不生成 OC 表
- 技能强化前后：`get_current_skills` 自动取最高 priority
- 缺失字段：用默认值或跳过，不报错
- 宝具 detail 为空：用兜底描述"对敌方全体发动强大的攻击<宝具升级效果提升>"