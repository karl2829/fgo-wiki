# 活动 MD 生成规则

## 数据源
- 原始数据：`raw/events/{event_id}.json`
- 关联 War：`event.warIds[]` → `raw/wars/{war_id}.json`

## 核心字段映射

| 字段 | JSON 路径 | 备注 |
|------|-----------|------|
| Event ID | `id` | |
| 名称 | `name` | |
| 短名 | `shortName` | |
| 类型 | `type` | eventQuest / raid / lottery / box 等 |
| 开始时间 | `startedAt` | Unix timestamp |
| 结束时间 | `endedAt` | Unix timestamp |
| 完全结束 | `finishedAt` | 含兑换期 |
| 公告链接 | `noticeAt` / `banner` | |
| Banner 图 | `banner` / `noticeBanner` | Atlas CDN |
| 简介 | `detail` | HTML/纯文本混合 |
| 关联 War | `warIds[]` | 关卡地图引用 |

## 渲染结构

### 1. 活动时间
| 项目 | 时间 |
|------|------|
| 公告时间 | YYYY-MM-DD HH:MM |
| 开始时间 | YYYY-MM-DD HH:MM |
| 结束时间 | YYYY-MM-DD HH:MM |
| 完全结束 | YYYY-MM-DD HH:MM |
| 素材开放 | 常驻 / 日期 |

### 2. 开放条件
- 从 `eventDetail.condQuestId` / `condQuestPhase` 提取
- 格式：`通关「{quest_name}」后开放`
- 若 API 无数据，从 Mooncell 页面抓取

### 3. 活动简介
- `detail` 字段清洗 HTML 标签后展示

### 4. 视觉资源
- 活动主横幅
- 公告横幅
- 其他关联图片

### 5. 地图/关卡
**不存放具体关卡数据**，只放 War 引用：
```
## 地图/关卡

- [[wars/8397|War #8397]]
- [[wars/8398|War #8398]]
```

### 6. 商店兑换
表头：`| 图标 | 道具 | 限购 | 所需道具 | 数量 |`
- 图标：优先 `shop.targetIds` → 从 items DB 取，无则构造 CDN
- 道具名称：从 API `shop.name` 直接取
- 优先级：按 `releaseConditions` 排序

### 7. 抽奖池（Box Gacha）
- 表头：`| 图标 | 奖品 | 类型 | 总数 |`
- 奖品名称：从 items DB 查 `objectId` 映射真实名称
- 分"稀有奖品"和"普通奖品"两块
- 底部：`**合计奖格**：{count} 个`

### 8. 活动加成从者
- 来源：Mooncell 活动页面"活动加成从者"章节
- 提取：`Servant{NUM}.jpg` → 从者 ID
- 通过 `/nice/CN/servant/{id}` 查名字、职阶
- 按加成等级分块展示（EX/A/B）
- 每块内按职阶分组

### 9. 活动礼装
- 来源：Mooncell 活动页面"活动礼装"章节
- 提取：`礼装{NUM}.jpg` → 礼装 ID
- 表格：`| 礼装 ID | 名称 |`（简洁版，详情后续关联 craft-essences）

## 关键函数签名
```python
format_event(event_data) -> str
format_event_shop(shops) -> str
format_event_lottery(lotteries) -> str
format_event_bonus_servants(html) -> str
format_event_ces(html) -> str
```

## 特殊情况
- 无 War 关联的活动（如仅有任务/礼装的小型活动）
- 复刻活动：标注"复刻"，时间用最新一期
- 多期活动：按 warIds 分期展示
- 活动礼装/加成从者优先从 API `eventAdds` / `pointBuffs` 取，缺失则抓 Mooncell