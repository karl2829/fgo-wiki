# FGO 战斗机制文档索引

> 最后更新：2026-08-16 | 共 21 个文档

本目录包含 FGO 游戏底层机制的结构化文档，涵盖从战斗计算到从者养成的完整知识体系。

## 📖 快速导航

| 文档 | 内容说明 |
|---|---|
| [游戏术语手册](./game_terms.md) | FGO 常用术语、黑话、昵称大全，新手必读 |
| [伤害计算公式](./damage_formula.md) | 完整伤害公式 + 各项乘区说明 + 计算示例 |
| [NP 获得公式](./np_gain_formula.md) | NP 获得量计算（攻击/被攻击） + 各项补正 |
| [暴击星获取公式](./star_gain_formula.md) | 暴击星获得量计算 + 分配机制 |
| [Buff 系统与计算](./buff_system.md) | A/B/C/D 类 Buff 分类 + 稀释机制 + 上限汇总 |
| [指令卡系统](./command_card.md) | 首位加成 + 位置补正 + Chain 系统 + Extra Attack |
| [战斗机制（MISS/GUARD/暴击）](./battle_mechanics.md) | MISS/GUARD 判定 + 暴击概率 + 暴击星分配 |
| [宝具系统](./noble_phantasm_system.md) | 宝具等级 + Over Charge + 宝具封印 + 强化 |
| [从者养成系统](./servant_ascension_skill.md) | 灵基再临 + 技能强化 + 宝具强化 + 附加技能 + 羁绊 |
| [敌方 AI 与行动模式](./enemy_ai.md) | 行动次数 + 气槽系统 + 攻击偏好 + Break 机制 |
| [职阶与阵营克制](./class_affinity.md) | 职阶克制 + 阵营克制 + 兽阶从者克制 |
| [游戏常数汇总](./constants.md) | 所有关键常数的速查表 |

## 📂 基础数据（Mooncell 游戏数据基础）

| 文档 | 内容说明 |
|---|---|
| [职阶基础数据](./class_basic_data.md) | 职阶伤害系数/集星权重/掉星率/充能格/行动次数 + 副属性克制 |
| [御主经验表](./master_level_exp.md) | 御主 1~200 级经验表 + COST + 等级上限历史 |
| [从者经验表](./servant_exp.md) | 从者 1~120 级经验表 + 强化 QP |
| [概念礼装经验表](./ce_exp.md) | 概念礼装 1~100 级经验表 + 强化 QP |
| [QP 消耗汇总](./qp_cost.md) | 灵基再临/技能/宝具/圣杯转临/指令卡强化 QP |
| [从者币系统](./servant_coin.md) | 从者币获得（召唤/羁绊/任务） + 消耗（追加技能/120级） |
| [从者面板数据](./servant_panel_data.md) | 参数补正/星级基础值/职阶补正/等级补正 + 面板计算公式 |
| [指令卡连携倍率表](./command_card_multipliers.md) | 27 种卡组伤害倍率 + 指令卡位置倍率 + 首卡染色/连携 |
| [从者集星权重排名](./star_weight_ranking.md) |
| [特殊奖励时段表](./campaign_timeline.md) | 强化大成功/经验2倍/AP减半/牵绊等 Campaign（CN当前+JP未来一年预估） |
| [战斗公式精确数值表](./combat_formula_tables.md) | 指令卡NP补正/NP敌补正/掉星率/敌补正/即死/状态成功率 |

## 📂 按主题分类

### 战斗计算
- [伤害计算公式](./damage_formula.md)
- [NP 获得公式](./np_gain_formula.md)
- [暴击星获取公式](./star_gain_formula.md)
- [游戏常数汇总](./constants.md)
- [战斗公式精确数值表](./combat_formula_tables.md)

### 战斗机制
- [指令卡系统](./command_card.md)
- [指令卡连携倍率表](./command_card_multipliers.md)
- [Buff 系统与计算](./buff_system.md)
- [战斗机制（MISS/GUARD/暴击）](./battle_mechanics.md)
- [宝具系统](./noble_phantasm_system.md)

### 从者与养成
- [从者养成系统](./servant_ascension_skill.md)
- [职阶与阵营克制](./class_affinity.md)
- [从者面板数据](./servant_panel_data.md)
- [从者经验表](./servant_exp.md)
- [概念礼装经验表](./ce_exp.md)
- [QP 消耗汇总](./qp_cost.md)
- [从者币系统](./servant_coin.md)

### 敌方与数据
- [敌方 AI 与行动模式](./enemy_ai.md)
- [游戏术语手册](./game_terms.md)
- [职阶基础数据](./class_basic_data.md)
- [御主经验表](./master_level_exp.md)
- [从者集星权重排名](./star_weight_ranking.md)

## 📌 使用建议

1. **新手入门**：建议先从 [游戏术语手册](./game_terms.md) 开始，了解 FGO 常用术语
2. **伤害计算**：核心文档是 [伤害计算公式](./damage_formula.md) + [Buff 系统与计算](./buff_system.md) + [战斗公式精确数值表](./combat_formula_tables.md)
3. **战斗策略**：推荐 [指令卡系统](./command_card.md) + [敌方 AI 与行动模式](./enemy_ai.md)
4. **养成规划**：参考 [从者养成系统](./servant_ascension_skill.md) + [从者面板数据](./servant_panel_data.md) + [QP 消耗汇总](./qp_cost.md)
5. **数值查表**：经验/QP/从者币/连携倍率等精确数据见「基础数据」分类

---

*数据来源：atlasacademy/fgo-docs + Mooncell + FGO Wiki*
