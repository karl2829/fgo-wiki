# 外部素材库索引

从网上收集的 FGO 出图素材，统一放在 `assets/external/`。本地原生素材在 `assets/ui/`、`assets/classes/`（Atlas / Mooncell 提取）。

## 目录速查

| 目录 | 内容 | 关键文件 | 尺寸 |
|---|---|---|---|
| `fgo-card-generator/` | 从者卡 / 礼装卡框模板、80px 职阶图标、装饰线 | `S0~S5.png`（稀有度卡框）、`CE1~CE5.png`（礼装卡框）、`{class}{0-3}.png`、`line.png`、`all*.png` | 卡框 512×875，图标 80×80 |
| `reddit-gears-icons/sheets/` | gears 重绘的高清职阶徽章**整版**（7 张，含官方 + 原创 + Beast/Grand） | `sheet1~7.png` | 6665×8541 RGBA |
| `reddit-gears-icons/class-icons/` | 从 sheet3（icons only 透明版）切好的**单枚**职阶徽章 | `saber.png` `archer.png` `lancer.png` `rider.png` `caster.png` `assassin.png` `berserker.png` `ruler.png` `avenger.png` `shielder.png` `mooncancer.png` `foreigner.png` `alterego.png` `pretender.png`（`beast.png` 来自 Mooncell，见下） | 约 600~1200px |
| `reddit-axwy11/` | Fate 卡牌打印图（300dpi 整版） | `fate-cards-300dpi.jpg` | 2550×3300 |

## 来源与授权

### 1. gears 的高清职阶图标（推荐）
- 出处：Reddit r/grandorder `1rfoa6w` — *High-Res Servant Class Icons — Official, Original, Beasts, Grands, and More!*
- 作者说明：1200×1200 版本，官方图标矢量化重绘 + 原创补齐（Saver / Voyager / Gatekeeper / Faker / Watcher / Funny Vamp / Gunner / Launcher），有 SVGs 与更多玩家职阶，见作者维护的 Beast's Lair 帖。
- 图内自带的授权文字：**FREE TO USE WITH CREDIT => GEARS.LINK/SERVANTICONS**，即免费使用但必须署名，署名指向 `gears.link/servanticons`。
- 7 张 sheet 的差异：`sheet1` 蓝色底版、`sheet2` 金色底版、`sheet3` 仅图标（透明，已切成单枚）、`sheet4` 蓝金混合、`sheet5` 深红/兽系、`sheet6/7` 白金系。要带底色的徽章用 1/2 号 sheet 切，纯图标用 3 号。

### 2. FGO-Card-Generator（卡框模板）
- 出处：GitHub `Ice-Pendragon/FGO-Card-Generator`，路径 `img/fgo/`
- 内容：`S0~S5` 六个稀有度的从者卡框模板、`CE1~CE5` 礼装卡框，中间留空放立绘；`line.png`、`all*.png`、`none*.png` 是装饰线与占位符。
- 仓库未标注 License，**仅限内部排版使用**，对外发布前需自行确认。

### 3. 300dpi 卡牌打印图
- 出处：Reddit r/grandorder `axwy11` — *Fate Cards Print Out 300dpi*（原帖评论里有 1000dpi 版本，未取到）。
- 用途：卡面版式参考 / 打印。

## 网络备注（下次复现用）

Reddit 与 `i.redd.it` 在本机被 DNS 污染（解析到 `2001::1`）且 IP 层封锁，直连和走 mihomo 代理都失败。可用通道：

```bash
# 1. 取帖子元数据与 gallery 图片 URL（Pushshift 替代站，直连可用）
curl -s 'https://api.pullpush.io/reddit/search/submission/?ids=1rfoa6w' -o /tmp/pp.json
# 图片 URL 在 data[0].media_metadata[<id>].s.u，顺序看 data[0].gallery_data.items

# 2. 绕过图片封锁：weserv 图片代理（直连可用，能拉原图）
curl -s -o out.png "https://images.weserv.nl/?url=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1],safe=''))" '<图片URL>')"
```

`gears.link/servanticons` 会 302 到 Beast's Lair 论坛帖（Cloudflare 403，未取到）；作者 GitHub 是 `involutegirl/gearslink.github.io`，但仓库里只有作品集图，没有职阶图标源文件。

## 用在哪

- `scripts/render_bond_ce_card.py`：礼装羁绊卡图，读 `reddit-gears-icons/class-icons/{class}.png` 当归属徽章，`assets/ui/stars/star_official_single.png` 当星级图标。
- 卡框模板（`S0~S5`）尚未接入任何脚本，可用作从者卡背景。

## 易错点

- **切图命名必须以 `ref-official-8class.png`（官方 UI 那一行：盾 尺 复仇 月癌 丑 外星人 伪装 兽）为准，不能凭感觉命名。** 这张图是唯一可靠的对照基准。
- 高级职阶形状（易混，务必照表）：**Shielder 十字盾 / Ruler 天平 / Avenger 恶魔火焰头 / MoonCancer 花冠+花萼（不是月亮）/ AlterEgo 左右分裂双面+底部五珠（像半张脸）/ Foreigner 八芒星 / Pretender 燃烧的王冠假面（三股火舌+梯形基座）/ Beast 红黑多目兽面**。形状描述只作参考，**文件名映射才是定版依据**。
- 基础七骑：Saber 剑 / Lancer 枪 / Archer 弓 / Rider 马+轮 / Caster 星杖 / Assassin 骷髅 / Berserker 兽角。
- **问号不是 Pretender**，是 Unknown 占位图（sheet 里 `r5c2`，彩虹菱形版是 `r5c1`）。
- 曾经连错三次：问号当伪阶、AlterEgo 的双面像当面具、月癌的花冠当 AlterEgo；最后复仇/伪装两枚也装反过。教训：切完必须与 `ref-official-8class.png` 逐格比对，或用已知从者出图验证。
- **切图对应关系（2026-11-20 定版，用户确认）**：`saber:r1c2 archer:r1c4 lancer:r1c3 rider:r2c1 caster:r2c2 assassin:r2c3 berserker:r2c4 ruler:r3c3 avenger:r3c4 mooncancer:r3c5 alterego:r4c2 shielder:r4c1 foreigner:r4c3 pretender:r4c4`；`r3c1/r3c2` 是空方块碎片、`r5c1/r5c2` 是 Unknown 问号，全部丢弃。
- **gears 整版 18 枚里没有兽职阶图标**（行1 左上是八叶轮、行2 第4 的双角面具是狂战士，都别拿来顶替）。Mooncell 官方 `Class-Beast-I/II/III.png`（红黑多目兽面）配色与浅金剪影不搭、用户嫌不好看，现存 `assets/external/mooncell/class/` 备用。**`beast.png` 当前用 gears 的问号（`r5c2`）占位**，是用户指定的临时方案，找到浅金风格兽图标再换。

## 还没做的

- `sheet1/2`（蓝底 / 金底）单枚切割——需要带底色徽章时再切。
- Beast I~VII、Grand、自制职阶（Saver / Voyager / Gunner 等）未命名，只保留整版 sheet。
- Reddit 原帖的高清星级素材、1000dpi 卡图未取到。
