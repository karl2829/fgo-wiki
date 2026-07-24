# 礼装 MD 生成规则

## 数据源
- 原始数据：`raw/craftEssences/{id}.json`
- 图片资源：Atlas Academy CDN

## 核心字段映射

| 字段 | JSON 路径 | 备注 |
|------|-----------|------|
| ID | `id` | |
| 名称 | `name` | |
| 原名 | `originalName` | |
| 稀有度 | `rarity` | ★×N |
| COST | `cost` | |
| 类型 | `type` | 常驻/限定/活动/纪念/礼装经验... |
| 描述 | `detail` | 含技能效果文本 |
| 最大等级 | `maxLevel` | 通常 50/80/100 |
| 图标 | `icon` | Atlas CDN |
| 立绘 | `illustrationId` / `charaGraph` | |
| 画师 | `illustrator` | |
| 系列 | `series` | 如"概念礼装" |
| 获取方式 | `detail` / 单独字段 | 卡池/活动/任务/礼装经验... |
| 动画 | `animationId` | 如有 Live2D |

## 效果渲染

### 礼装技能效果
- 从 `detail` 字段提取
- 分割符：`＆` / `＋` / `▲` / `，`
- 每个效果独立一行，格式：
  - **效果名称**：数值
  - 固定值直接显示，随等级变化的显示 Lv.1-10/Lv.1-5 表格

### 效果表格（随等级变化）
- 礼装通常 50/80/100 级，表格列数按最大等级
- 表头：`Lv.1 | Lv.2 | ... | Lv.N`
- 数值从 API 的 `vals` / `svals` 提取

## 突破/强化材料
- 同从者材料表格式
- 列：阶段 | QP | ID | 图标 | 道具名称 | 数量
- 总计表单独成表

## 立绘/视觉资源
- 普通立绘
- 最大突破立绘
- 如有动画：Live2D 标记

## 关键函数签名
```python
format_ce_effects(ce_data) -> str
format_ce_materials(mats_dict) -> str
```

## 特殊情况
- 礼装经验卡：只显示提供经验值，无技能效果
- 联动/限定礼装：标注获取途径
- 同名不同稀度：按 ID 区分