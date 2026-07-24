# {{war_name}}

> **ID**: {{war_id}} | **类型**: event | **关联活动**: [[../events/{{event_shortname}}]]

## 地图信息

| 属性 | 值 |
|---|---|
| War ID | {{war_id}} |
| 名称 | {{war_name}} |

## 主线关卡

| 小节 | 关卡名称 | 地点 | 报酬 |
|---|---|---|---|
| {{sub}} | {{name}} | {{spot}} | {{rewards}} |

## 自由关卡

| 关卡 ID | 推荐等级 | 关卡名称 | 报酬 | 掉落物 | 敌配置 |
|---|---|---|---|---|---|
| {{id}} | {{recommendLv}} | {{name}} | {{rewards}} | {{drops}} | {{enemies}} |

**总计**：{{main_count}} 个主线关卡 + {{free_count}} 个自由关卡 = {{total}} 关

---

*数据来源: Atlas Academy API* | *最后更新: {{date}}*

## 生成规则

1. 从 War JSON 中提取 spots → quests
2. 对每个 quest 调用 `/nice/CN/quest/{quest_id}?lang=en` 获取报酬、推荐等级
3. 按 quest.type 分为 "main"（主线）和 "event"（自由）
4. 主线：小节号(from chapterSubId/phase)、名称、地点、报酬
5. 自由：ID、推荐等级、名称、报酬、掉落物、敌配置
6. 掉落物和敌配置 API 不返回时标"待补充"
