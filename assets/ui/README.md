# FGO 素材库（出图用）

## 目录

- `AssetStorage_JP.txt` — 官方资产清单（41,341 个 assetbundle：name,size,crc,path），来自 `git.atlasacademy.io/atlasacademy/fgo-game-data`（需走 API blob 接口，raw 被 CF 拦）。
- `bundles_ui.txt` — 从清单筛出的 803 个 UI 家族 bundle（Terminal / EventUI / UI / CommonUI / Battle / Shop / Gacha / MyRoom / Formation / Party / Menu / Title / Login / Support / Friend / Present / Summon / Material / Status / Enhance / CommandCode / Craft / Tutorial）。
- `chaldea/` — Chaldea 项目自带 FGO UI 切图 21 张 + `manifest.json`（listframes 底板、指令卡底纹、卡色图标、艺术字）。
- `atlas/` — Atlas 静态站实测可取的图 + `index.json` 索引（路径/URL/字节数）。
- 探测器：`~/fgo-wiki/scripts/probe_atlas_assets.py`

## Atlas 静态站取图规则（2026-11 实测）

```
https://static.atlasacademy.io/{CN|JP}/<bundle路径>/<精灵名>.png
```

例：
- `Terminal/Info/CommonUIAtlas/icon_nplv.png` ✅
- `Items/12.png`、`BuffIcons/bufficon_1014.png`、`SkillIcons/skill_999999.png` ✅
- 从者 `Faces/f_{servantId}.png`、礼装 `EquipFaces/f_{equipId}.png`、立绘 `Servants/{id}/status_servant_1.png` ✅

注意：Atlas 只镜像**它自己前端引用过的**精灵，不是完整 UI 库。盲猜精灵名命中率很低（CommonUIAtlas 目录 139 个候选只中 5 个）。UI 九宫格边框、按钮、活动横幅要拿到全套，必须解 bundle。

## 已知 404 的路径形态（别浪费时间）

`Items/{itemId}.png` 之外的 `ClassIcons/archer.png`、`Commands/1.png`、`UI/...`、`Equip/{id}.png`、`ClassIcons/img_classchart.png` 之外的职阶图 —— 按单个精灵名猜基本不通。

## 待办

- Step 2（未做）：按 `bundles_ui.txt` 拉单个 bundle（每个几百 KB）→ UnityPy 解 sprite → 补进本库；国服 bundle 加密，需要 APK 里的 key。

## Mooncell 魔术礼装图标（官方，2026-11 补）

- 目录：`assets/ui/mooncell/`，索引 `index.json`（礼装名 → 文件名/尺寸/来源 URL）。
- 抓取：`python3 scripts/fetch_mc_icons.py "魔术礼装·极地用迦勒底制服" ...`（无参看用法）。
- 命名不统一：有的带 `魔术礼装·` 前缀，有的把「真说」写作「真实」（如 第五真说/第五真实）。脚本先试精确标题，再用 `list=search&srnamespace=6` 兜底。
- 尺寸统一 150×150 RGBA，透明背景做展示时要先按 alpha bbox 裁边。
- 立绘另有 `魔术礼装·XXX1.png`（约 472×1024）可作大图。
- 出图时按等比 contain 放进方框，**不要**拉伸成 2:1，否则视觉上被压扁。

## 星级 / 职阶素材

- `assets/ui/stars/{1..5}star.png`：Mooncell 官方星级整排图（1星 64×60、5星 328×86 等），直接右键对齐即可，别自己画星星。
- `assets/ui/classes/<class>_<gold|silver|bronze>.png`：由 CDN 菱形职阶图标挖掉内部深色底得到的**透明底**版本（`scripts/class_icon_transparent.py`，内部泛洪挖色，纹章与金框保持完整）。原图内底实心会挡住头像。
- 星级配色规则：5★/4★ 金、3★ 银、1~2★ 铜；职阶图标底色跟随同一规则。
