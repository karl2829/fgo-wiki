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
2. **数据源优先级**：**JP 仅补充 CN 没有的数据**，不重复拉取 CN 已有的内容。
   - 优先拉取国服（CN）数据
   - JP 只拉取 CN 不存在的条目（按 ID 去重）
   - 已拉取过的数据不重复拉取（增量更新）
   - CN 和 JP 都无数据则标记为待补充
3. **只保留一份数据**：API 数据只拉取 `lore=true` 或 `_lore` 完整版，**不保留非 lore 副本**。一份数据涵盖全部字段，减少冗余和混淆。
4. **数据优先**：原始 JSON → 结构化解析 → Markdown，不硬编码
5. **表格标准化**：固定表头、固定列数、统一图标 CDN
6. **引用分离**：活动不存关卡，只引用 War；War 存完整关卡
7. **API 请求间隔**：拉取外部 API 数据时，每次请求间隔至少 **0.5 秒**，避免被限流或加入黑名单。
8. **容错优先**：字段缺失用默认值或跳过，不报错中断
9. **目录结构统一**：所有实体类型目录下按 `{类型}/CN/` 和 `{类型}/JP/` 划分。不要在 `entities/` 下直接放文件，也不用 `_jp` 后缀。
10. **增量生成**：单个实体独立生成，批量跑脚本
11. **增量更新标准**：所有数据类型的增量脚本统一用 `last_sync_at` + `synced_ids` 判断：
    - **卡池**：`fetch_mooncell_gacha.py` — 从 Mooncell 主页面拉新增池
    - **从者**：`fetch_servants.py` + `fetch_jp_only.py` — API 增量
    - **活动**：`fetch_events.py` — 分界线 + 增量差集
    - **道具**：`sync_items.py` — 全量对比 `synced_ids` ✅
    - **御主礼装**：`sync_mystic_codes.py` — max_id 步长探测 ✅
    - **指令纹章**：`sync_command_codes.py` — state 文件跳过已同步 ✅
    - **礼装**：`generate_ce.py` — 30天内本地缓存跳过 ✅
12. **版权声明**：每个生成的 MD 文件底部必须包含：
    ```
    *数据来源: [Atlas Academy API](https://api.atlasacademy.io) | 游戏素材版权归 TYPE-MOON / FGO PROJECT 所有*
    ```
    如页面使用了 Mooncell 补充数据，额外注明：
    ```
    *部分数据参考自 [Mooncell](https://fgo.wiki)，遵循 CC BY-NC-SA 4.0 协议*
    ```

---

## 通用技术规范

### 图标 CDN
```
从者头像:     https://static.atlasacademy.io/CN/Faces/f_{svt_id}{asc}.png
从者立绘:     https://static.atlasacademy.io/CN/CharaGraph/{svt_id}/{svt_id}{asc}@1.png
宝具图标:     https://static.atlasacademy.io/CN/Servants/Commands/{svt_id}/card_servant_np.png
技能图标:     https://static.atlasacademy.io/CN/SkillIcons/{icon_name}.png
道具图标:     https://static.atlasacademy.io/CN/Items/{item_id}.png
职阶图标:     https://static.atlasacademy.io/CN/ClassIcons/class_{class_id}.png
指令卡图标:   https://static.atlasacademy.io/CN/Servants/Commands/icon_card_{arts/buster/quick}.png
```

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
│   ├── servants/           # 从者 MD（按名称命名）
│   ├── craft_essences/     # 礼装 MD
│   ├── wars/               # War MD（按 War ID 命名）
│   ├── events/             # 活动 MD（按短名命名）
│   ├── mechanics/          # 机制文档（13个子文件）
│   └── items/              # 道具 DB (active_items.json)
├── raw/
│   ├── servants/           # 原始 API JSON
│   ├── wars/
│   ├── events/
│   └── ...
├── references/
│   ├── skills/
│   │   ├── class/          # 职阶技能引用
│   │   └── append/         # 追加技能引用
│   └── lore/               # 从者资料
├── rules/                  # 本目录（生成规则文档）
└── generate.py             # 主生成脚本
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

- [ ] 新增从者 → 跑 `generate.py <id>` → 检查 NP/技能表格
- [ ] 新增活动 → 跑 `generate_events.py <id>` → 检查商店/抽奖/加成从者
- [ ] 新增 War → 检查主线/自由关卡、敌人配置
- [ ] 机制文档变更 → 更新对应 `mechanics/*.md` + 头部日期
- [ ] 道具 DB 更新 → 跑同步脚本 → 修复 icon 字段

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

> 最后更新：2026-07-23 | 维护者：Mila | 对应 generate.py v3