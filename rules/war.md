# War（关卡/地图）MD 生成规则

## 数据源
- 原始数据：`raw/wars/{war_id}.json`
- 关联从者/敌人：通过 `spot` -> `quest` -> `enemy` 链接

## 核心字段映射

| 字段 | JSON 路径 | 备注 |
|------|-----------|------|
| War ID | `id` | |
| 名称 | `name` | |
| 类型 | `type` | main/free/event 等 |
| 章节 | `chapter` | 如"第一章 第1节" |
| 关卡列表 | `spots[]` | 每个 spot 包含多个 quest |

## 渲染结构

### 1. 基础信息
- War ID、名称、类型、所属章节/活动

### 2. 主线关卡（Quest type = "main"）
表格列：
| 小节 | 关卡名称 | 地点 | 报酬 |
|------|----------|------|------|

- 报酬从 `rewards` 解析：`item#id xN` → 解析为图标+名称+数量
- 地点从 `spot.name` 取

### 3. 自由关卡（Quest type = "event" / "free"）
每个关卡独立成块，`---` 分隔：
- 关卡 ID
- 推荐等级
- AP 消耗
- 关卡名称
- 报酬（QP、羁绊、经验）
- 掉落物（名称 + 图标）
- 每面敌人配置：
  | 波次 | 敌人 | 职阶 | 等级 | HP |

### 4. 敌人配置详情
- 敌人 ID → 查 `raw/enemies/{enemy_id}.json`
- 显示：名称、职阶图标、等级、HP、特性标签

## 关键函数签名
```python
format_war_main_quests(war_data) -> str
format_war_free_quests(war_data) -> str
format_enemy_wave(enemy_data) -> str
```

## 特殊情况
- 同一 War 同时包含主线和自由关卡（如活动地图）
- 关卡解锁条件（通关前置关卡、特定从者等）
- 气槽机制（Break 后行为改变）