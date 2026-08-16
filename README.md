# FGO 知识库

一个 Fate/Grand Order 的中文数据知识库，数据来自 Atlas Academy API，部分补充参考 Mooncell。全部内容以 Markdown 形式组织，供本地检索、群聊问答和生成图片使用。

## 这是什么

把游戏里散落的数据整理成结构化的 Markdown 文件，方便查询和二次加工。最初是给 QQ 群机器人做问答知识库用的，后来慢慢补齐了从者、礼装、活动、卡池这些数据，又加了特性统计和特攻一览，现在基本能覆盖日常会问到的东西。

数据是增量维护的：国服新实装、日服先行、活动上线都会定期同步，有独立的同步脚本和状态记录，不会每次全量重拉。

## 目录结构

```
fgo-wiki/
├── entities/              # 知识库主体（Markdown）
│   ├── servants/          # 从者（CN/JP 分目录，按内部 ID 命名）
│   ├── craft-essences/    # 概念礼装
│   ├── events/            # 活动（新活动完整版，老活动简略版）
│   ├── gacha/             # 卡池（当前/未来单文件 + expired_gacha.md 汇总）
│   ├── command-codes/     # 指令纹章
│   ├── mystic-codes/      # 御主礼装
│   ├── items/             # 道具
│   ├── wars/              # 关卡
│   ├── mechanics/         # 机制文档（伤害公式、NP 获取、buff 系统等）
│   ├── traits/            # 特性统计（按职阶分类的从者合集）
│   └── tokou/             # 特攻一览（从者/礼装/纹章）
├── raw/                   # 原始 API JSON（不入库，可重新拉取）
├── scripts/               # 同步、生成、渲染脚本
├── references/            # 从者语音、资料、技能引用
├── rules/                 # 各实体类型的生成规则
├── data/                  # 映射表、翻译表、同步状态
├── generate.py            # 从者 MD 生成器
├── RULES.md               # 生成规则总索引
└── SCHEMA.md              # 数据结构说明
```

## 数据规模

| 类型 | 数量 |
|------|------|
| 从者（国服） | 451 |
| 从者（日服先行） | 30 |
| 概念礼装（国服） | 2284 |
| 概念礼装（日服） | 333 |
| 活动（国服） | 334 |
| 活动（日服） | 67 |
| 指令纹章 | 199 |
| 御主礼装 | 27 |
| 特性统计 | 87 |
| 特攻一览 | 从者 184 / 礼装 83 / 纹章 38 |

## 数据来源

- 主数据：Atlas Academy API（https://api.atlasacademy.io），拉取 `lore=true` 完整版
- 补充数据：Mooncell（https://fgo.wiki），主要用于活动开放条件、卡池信息、灵衣名单等 API 缺失或滞后的部分
- 增量更新：各类数据都有独立的同步状态文件（`data/*_sync_state.json`），按 `synced_ids` 只拉新增，不重复请求

## 主要脚本

| 脚本 | 作用 |
|------|------|
| `scripts/sync_all.py` | 一键同步入口（默认跳过卡池，`--with-gacha` 开启） |
| `scripts/fetch_servants.py` | 国服从者增量拉取 |
| `scripts/fetch_jp_only.py` | 日服先行从者 |
| `scripts/generate_ce.py` | 礼装 MD 生成 + 索引重建 |
| `scripts/fetch_events.py` | 活动增量同步 |
| `scripts/fetch_mooncell_gacha.py` | 卡池（从 Mooncell 爬取） |
| `scripts/sync_command_codes.py` | 指令纹章 |
| `scripts/sync_mystic_codes.py` | 御主礼装 |
| `scripts/sync_items.py` | 道具 |
| `scripts/sync_campaigns.py` | 特殊奖励时段（CN 已公告 + JP 未来一年预估） |
| `scripts/gen_trait_stats.py` | 特性统计 MD 生成 |
| `scripts/gen_tokou_overview.py` | 特攻一览 MD 生成 |
| `scripts/render_skill_card.py` | 技能卡图片渲染（Pillow） |
| `scripts/render_noble_phantasm.py` | 宝具图渲染 |
| `scripts/rebuild_servants_id.py` | 从者 MD 重建（默认增量，`--full` 全量） |

## 增量更新

同步脚本遵循同一套约定：`data/` 下每个类型一个 sync_state 文件，记录已同步的 ID 和最后同步时间，每次只补差集。新数据进来后，实体 MD 也是增量生成——已存在的文件不动，只补缺失的。

卡池比较特殊，从 Mooncell 爬取，按 `gacha_raw.json` 里的 `last_sync_at` 判断增量。过期卡池汇总到一个 `expired_gacha.md`，不占单文件。

## 特性统计与特攻一览

这两个是后加的整理型数据，适合快速查"谁有神性""谁对魔性特攻"这类问题。

- **特性统计**（`entities/traits/`）：每个特性一个文件，按职阶分组列出从者。判定合并了基础特性、灵基阶段追加和灵衣追加，所以像斯卡哈要穿兔女郎灵衣才算兽科这类情况也有标注。
- **特攻一览**（`entities/tokou/`）：从者、礼装、纹章三类合并成一个文件。从者侧区分宝具特攻和技能特攻状态，JP-only 从者带 `*` 标记。

新增从者或活动后，重跑对应的生成脚本即可保持这两块同步。

## 已知限制

- Quest 敌人配置和掉落物无法通过 API 获取（Atlas DB 是前端渲染），这部分数据缺失
- 活动开放条件等字段偶尔要手动从 Mooncell 补
- 个别从者的语音/资料（`references/`）是空壳，待后续补齐
- 日服未来一年的 Campaign 时间是基于去年同期的预估，日期仅供参考

## 版权声明

- 游戏数据来源于 Atlas Academy API
- 部分补充数据参考 Mooncell，遵循 CC BY-NC-SA 4.0 协议
- 游戏素材（图片、立绘、图标等）版权归 TYPE-MOON / FGO PROJECT 所有
- 本知识库仅供个人学习研究，非商业用途
