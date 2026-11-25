# FGO Wiki 生成规则总索引

## 规则文件体系

| 规则文件 | 适用范围 | 核心内容 |
|---------|---------|---------|
| `rules/servant.md` | 从者 MD (`entities/servants/`) | 技能10列表格、NP/OC各5列表格、效果解析、材料表 |
| `rules/craft_essence.md` | 礼装 MD (`entities/craft_essences/`) | 效果渲染、材料表、立绘 |
| `rules/war.md` | War MD (`entities/wars/`) | 主线/自由关卡、敌人配置、掉落 |
| `rules/event.md` | 活动 MD (`entities/events/`) | 时间、商店、抽奖、加成从者、礼装 |
| `rules/mechanics.md` | 机制文档 (`entities/mechanics/`) | 13个子文档的详细生成规范 |

---

## 核心生成原则

1. **数据来源严格限定**：所有数据必须来自本地 `~/fgo-wiki/entities/` 目录下的文件，不得引用互联网搜索结果或凭空编造。查不到就回复「知识库中暂无此数据」，并建议更精确的名称。
2. **数据源优先级**：**从者（servants）CN / JP 双份全量存储**，其它实体类型仍按「JP 仅补充 CN 没有的数据」。
   - **从者例外（2026-11 用户定）**：日文名、宝具名、技能名以日服为准，故 JP 从者必须全量拉取并生成 MD，不再只存「国服未实装」的从者；CN / JP 同 ID 各存一份，互不覆盖
   - 其它实体：优先 CN，JP 只拉 CN 不存在的条目（按 ID 去重）
   - 已拉取过的数据不重复拉取（增量更新）
   - CN 和 JP 都无数据则标记为待补充
3. **只保留一份数据**：API 数据只拉取 `lore=true` 或 `_lore` 完整版，**不保留非 lore 副本**。一份数据涵盖全部字段，减少冗余和混淆。
4. **数据优先**：原始 JSON → 结构化解析 → Markdown，不硬编码
5. **表格标准化**：固定表头、固定列数、统一图标 CDN
6. **引用分离**：活动不存关卡，只引用 War；War 存完整关卡
7. **API 请求间隔**：拉取外部 API 数据时，每次请求间隔至少 **0.5 秒**，避免被限流或加入黑名单。
8. **容错优先**：字段缺失用默认值或跳过，不报错中断
9. **目录结构统一**：**已分服**的类型（`servants/`、`craft-essences/`、`events/`、`gacha/`）一律用 `{类型}/CN/` 和 `{类型}/JP/` 子目录；**暂未分服**的类型（`items/`、`command-codes/`、`mystic-codes/`、`mechanics/`、`traits/`、`tokou/`、`bond-ce/`、`wars/`）直接放类型目录下，按各自规则命名。不要在 `entities/` 根下直接放文件，也不用 `_jp` 后缀。
10. **增量生成**：单个实体独立生成，批量跑脚本
11. **增量更新标准**：所有数据类型的增量脚本统一用 `last_sync_at` + `synced_ids` 判断：
    - **卡池**：`fetch_mooncell_gacha.py` — 从 Mooncell 主页面拉新增池
    - **从者**：`fetch_servants.py`（CN 增量）+ `fetch_jp_servants.py`（JP 全量补全，2026-11 起取代 `fetch_jp_only.py`）
    - **活动**：`fetch_events.py` — 分界线 + 增量差集
    - **道具**：`sync_items.py` — 全量对比 `synced_ids` ✅
    - **御主礼装**：`sync_mystic_codes.py` — max_id 步长探测 ✅
    - **指令纹章**：`sync_command_codes.py` — state 文件跳过已同步 ✅
    - **礼装**：`generate_ce.py` — 30天内本地缓存跳过 ✅
12. **卡池横幅 CDN**：当前/未来卡池的 banner 图上传至 `fgo/gacha/` 目录，CDN 路径为 `https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main/fgo/gacha/{gid}.png`。新卡池获取流程：
    - 从 Mooncell 拉取 → 下载 banner → 用 `zxgpcli upload` 上传
    - `gacha_raw.json` 中 `banner` 字段使用 CDN URL
    - MD 文件中 URL 需对中文文件名进行 `urllib.parse.quote` 编码
13. **版权声明**：每个生成的 MD 文件底部必须包含：
    ```
    *数据来源: [Atlas Academy API](https://api.atlasacademy.io) | 游戏素材版权归 TYPE-MOON / FGO PROJECT 所有*
    ```
    如页面使用了 Mooncell 补充数据，额外注明：
    ```
    *部分数据参考自 [Mooncell](https://fgo.wiki)，遵循 CC BY-NC-SA 4.0 协议*
    ```

---

## 国服 / 日服进度差（底层前提，2026-11 用户定）

**国服整体落后日服约 1 年。** 这是所有「未来 / 排期 / 预估」类内容（`entities/mechanics/campaign_timeline.md`、未来视卡池、前瞻活动、JP→CN 映射）的默认基准：

- 主线剧情节点对齐最准，整体按 `日服日期 + 1 年 ≈ 国服日期` 推算。
- 中间会有跑动：个别活动/复刻提前或延后几周到一两个月，属于正常偏差，不要因此推翻 1 年这个基准（也别自行改成半年、9 个月）。
- 推算结果一律标 `⚠预估`，写成「约 X 年 X 月」；不写成确定档期。
- 国服确切日期只认官网公告（`fgo-current-events`/`game.bilibili.com/fgo/news.html`）。**公告与推算冲突时以公告为准**，推算只用于公告还没覆盖的时间段。
- 不得把「日服档期」直接当「国服档期」写进 MD；跨服映射必须走 +1 年并标注预估来源。

---

## 通用技术规范

### 素材库优先（2026-11 定）

**出图一律先读本地 `assets/`，缺失才回退下载**；索引与分层见 `assets/README.md`。

| 素材 | 本地路径 | 兜底来源 |
|---|---|---|
| 职阶图标 | `assets/classes/{职阶}_{gold\|silver\|bronze}.png` | 无（fgo-images 已弃用） |
| 指令卡 | `assets/cards/{quick,arts,buster}.png` | Atlas `Servants/Commands/icon_card_*.png` |
| 星级 | `assets/stars/{1..5}star.png` | 无 |
| 技能图标 | `assets/skills/{icon_name}.png` | Atlas `SkillIcons/{icon_name}.png` |
| 道具图标 | `assets/items/{item_id}.png` | Atlas `Items/{item_id}.png` |
| 从者立绘/头像/宝具卡图/羁绊礼装 | `assets/servants/`（本地缓存，不入库） | Atlas `CharaGraph` / `Faces` / `Servants/Commands` / `Items` |

- 批量获取：`scripts/fetch_assets.py`（`--icons/--skills/--items/--servant ID/--all-servants`）
- MD 内图标引用已改相对路径（`../../../assets/...`），不再写 CDN
- `cdn.jsdelivr.net/gh/karl2829/fgo-images` **已弃用**，不要新增引用；卡池 banner 是唯一例外（待本地化）

### 格式化函数签名
```python
format_val(v, func_type) -> str          # 数值→百分比/纯数字
format_np_effects(np_data) -> str        # 宝具效果→表格
format_skill_detail(sk, icon) -> str     # 技能→10列表格
mat_table(title, mats, ...) -> str       # 材料表+总计表
format_ce_effects(ce_data) -> str        # 礼装效果
```

### 百分比格式化规则
| funcType | 除数 | 示例 |
|----------|------|------|
| damageNp / damageNpIndividual | 10 | 4000 → 400% |
| gainNp | 100 | 2750 → 27.5% |
| gainStar | 0 (原始) | 15 → 15 |
| addStateShort / addState / 其他 | 10 | 300 → 30% |

- 整数不显示小数：`30%` 不 `30.0%`
- 保留 1 位小数：`27.5%`
- 跳过标志位：`addStateShort` 中 Value < 5 视为标志位，不显示

---

## 目录结构约定

```
fgo-wiki/
├── entities/
│   ├── servants/{CN,JP}/    # 从者 MD（按内部 ID 命名）
│   ├── craft-essences/{CN,JP}/  # 礼装 MD
│   ├── events/{CN,JP}/      # 活动 MD（按短名命名）
│   ├── gacha/{CN,JP}/       # 卡池（当前/未来 + expired_gacha 汇总）
│   ├── items/               # 道具 MD（按 item ID 命名，未分服）
│   ├── command-codes/       # 指令纹章（未分服）
│   ├── mystic-codes/        # 御主礼装（未分服）
│   ├── mechanics/           # 机制文档（未分服）
│   ├── traits/              # 特性统计（按职阶分类的从者合集）
│   ├── tokou/               # 特攻一览
│   ├── bond-ce/             # 羁绊加成礼装归属索引
│   └── wars/                # War MD（按 War ID 命名）
├── raw/                     # 原始 API JSON（gitignore，可重新拉取）
│   └── {类型}/{CN,JP}/{id}.json
├── assets/                  # 出图素材（classes/ 职阶图标、external/ 网图索引）
├── scripts/                 # 同步、生成、审计脚本
├── card-render/             # 从者卡出图管线（pytakumi，规则见 card-render/RULES.md）
├── references/              # 从者语音、资料、技能引用
├── data/                    # 映射表、翻译表、同步状态
├── rules/                   # 各实体类型的生成规则
├── generate.py              # 从者 MD 主生成脚本
├── RULES.md                 # 本文件（规则总索引）
├── SCHEMA.md                # 数据结构说明
└── README.md                # 项目说明
```

---

## 关键实现细节

### 宝具效果渲染顺序
1. 先发 Buff（伤害前生效）→ 独立描述 + 表格
2. NP 升级效果表（Lv.1-5）
3. OC 效果表（OC1-5，Correction/Value 双模式）
4. 后发效果（NP 增加等）→ 描述 + 单值

### 技能效果拆分
- `detail` 字段按 `＆` `＋` `▲` 分割
- 每个子效果独立 10 列表格（Lv.1-10）
- 固定值（10级无变化）只显示文字

### 材料表格式
| 阶段 | QP | ID | 图标 | 道具名称 | 数量 |
|------|-----|----|------|----------|------|

**总计表**（每类单独）：
| ID | 图标 | 道具名称 | 总数 |
最后行：`| — | — | **QP** | **{total_qp:,}** |`

### Mooncell 数据补完
- 活动开放条件、加成从者、礼装、评价：API 缺失时抓 Mooncell
- 礼装 ID 从 `礼装{NUM}.jpg` 提取

---

## 更新维护清单

- [ ] 新增从者 → 跑 `generate.py <id>` → 检查 NP/技能表格 → **根据该从者特性追加到 `entities/traits/特性：*.md`**（若已有对应特性文件则补充该从者，否则新建；含灵基/灵衣条件追加的标注形态）
- [ ] 新增活动 → 跑 `generate_events.py <id>` → 检查商店/抽奖/加成从者 → **检查商店是否存在灵衣兑换权限，若存在则把对应从者更新到 `entities/traits/特性：持有灵衣之人.md`**（Atlas 可能未及时标注 hasCostume，以活动商店灵衣为准）
- [ ] 新增 War → 检查主线/自由关卡、敌人配置
- [ ] 机制文档变更 → 更新对应 `mechanics/*.md` + 头部日期
- [ ] 道具 DB 更新 → 跑同步脚本 → 修复 icon 字段
- [ ] 新增从者/礼装/纹章 → 重跑 `scripts/gen_tokou_overview.py` 更新特攻一览
- [ ] 新增从者 → 重跑 `scripts/gen_trait_stats.py` 更新特性统计

---

## 常见坑位提醒

| 问题 | 解决 |
|------|------|
| Items DB icon 字段错误 | 忽略 DB icon，直接用 `{id}.png` 构造 URL |
| NP 多版本（强化前后） | 只渲染最后一个（`nps[-1]`） |
| OC 值全相等 | 不生成 OC 表 |
| 技能强化前后共存 | `get_current_skills()` 自动取最高 priority |
| Mooncell 结构变化 | 选择器用语义类名，避免位置依赖 |
| 礼装 ID 冲突 | 按 ID 命名文件，同名不同稀度共存 |

---

> 最后更新：2026-11-25 | 维护者：Mila | 规则变更：JP 从者全量存储、card-render 并入