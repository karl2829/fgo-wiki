# FGO 知识库

一个 Fate/Grand Order 的中文数据知识库，数据来自 Atlas Academy API，部分补充参考 Mooncell。全部内容以 Markdown 形式组织，供本地检索、群聊问答和生成图片使用。

## 这是什么

把游戏里散落的数据整理成结构化的 Markdown 文件，方便查询和二次加工。最初是给 QQ 群机器人做问答知识库用的，后来慢慢补齐了从者、礼装、活动、卡池这些数据，现在基本能覆盖日常会问到的东西。

数据是定期同步的：国服新实装、日服先行、活动上线都会补进来，由同步脚本按状态记录只拉新增的部分。

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
│   ├── bond-ce/           # 羁绊加成礼装 → 从者归属（8 张限定礼装 + 从者反查）
│   └── tokou/             # 特攻一览（从者/礼装/纹章）
├── raw/                   # 原始 API JSON（不入库，可重新拉取）
├── assets/                # 出图素材库（classes/ cards/ stars/ skills/ items/ 入库，servants/ 本地缓存；见 assets/README.md）
├── scripts/               # 同步、生成、渲染脚本
├── card-render/           # 从者卡出图管线（pytakumi，附属子项目，规则见 card-render/RULES.md）
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
| 从者（国服） | 458 |
| 从者（日服，全量） | 487 |
| 概念礼装（国服） | 2284 |
| 概念礼装（日服） | 333 |
| 活动（国服） | 334 |
| 活动（日服） | 67 |
| 指令纹章 | 199 |
| 御主礼装 | 27 |

## 数据来源

- 主数据：Atlas Academy API（https://api.atlasacademy.io），拉取 `lore=true` 完整版
- 补充数据：Mooncell（https://fgo.wiki），主要用于活动开放条件、卡池信息、灵衣名单等 API 缺失或滞后的部分

## 主要脚本

| 脚本 | 作用 |
|------|------|
| `scripts/sync_all.py` | 一键同步入口（默认跳过卡池，`--with-gacha` 开启） |
| `scripts/fetch_servants.py` | 国服从者增量拉取 |
| `scripts/fetch_jp_servants.py` | 日服从者**全量**补全（日文名/宝具名/技能名数据源，2026-11 起） |
| `scripts/generate_ce.py` | 礼装 MD 生成 + 索引重建 |
| `scripts/gen_bond_ce.py` | 羁绊加成礼装归属索引（纯本地，生成 `entities/bond-ce/`） |
| `scripts/fetch_events.py` | 活动增量同步 |
| `scripts/fetch_mooncell_gacha.py` | 卡池（从 Mooncell 爬取） |
| `scripts/sync_command_codes.py` | 指令纹章 |
| `scripts/sync_mystic_codes.py` | 御主礼装 |
| `scripts/sync_items.py` | 道具 |
| `scripts/sync_campaigns.py` | 特殊奖励时段（CN 已公告 + JP 未来一年预估） |
| `scripts/render_skill_card.py` | 技能卡图片渲染（Pillow） |
| `scripts/render_noble_phantasm.py` | 宝具图渲染 |
| `scripts/rebuild_servants_id.py` | 从者 MD 重建（默认增量，`--full` 全量） |
| `scripts/fetch_assets.py` | 素材库拉取（图标/技能/道具/从者素材，本地优先） |
| `scripts/audit_servants.py` | 从者 MD 审计（字段完整性抽查） |
| `scripts/regen_all_servants.py` | CN 从者 MD 全量重生成（备份 + 变更统计） |
| `card-render/build_data.py` | 从者卡数据管线（MD → JSON + 资产） |
| `card-render/make_card.py` | 从者卡渲染（pytakumi，2200px 宽） |

## 从者卡出图

`card-render/` 是从者卡渲染管线，数据全部取自本仓库的 MD（CN 主数据 + JP 日文名），
pytakumi 直接把 HTML/CSS 渲染成 PNG，不启浏览器。生成口径（效果四态、`∅`、日文名、
资产、数值口径）见 [`card-render/RULES.md`](card-render/RULES.md)。

```bash
cd card-render
.venv/bin/python build_data.py <内部ID>
.venv/bin/python make_card.py <内部ID> -o out/card.png
```

## 开源协议

本知识库采用 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hans) 协议开源。可以自由使用、修改、分享，但需署名、非商业用途、以相同协议共享。

游戏素材（图片、立绘、图标等）版权归 TYPE-MOON / FGO PROJECT 所有，不随本仓库协议授权。

## 致谢

- 感谢 [Atlas Academy](https://atlasacademy.io) 维护的游戏数据 API，本知识库的主体数据来自这里
- 感谢 [Mooncell](https://fgo.wiki) 社区的整理工作，活动开放条件、卡池信息等补充数据参考于此（遵循 CC BY-NC-SA 4.0 协议）
- 感谢 TYPE-MOON / FGO PROJECT 创造了这款游戏
