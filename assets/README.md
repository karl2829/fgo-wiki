# 素材库（assets/）

出图素材统一放这里，**所有出图脚本优先读本地素材，不再依赖外链 CDN**。
（原 `cdn.jsdelivr.net/gh/karl2829/fgo-images` 已弃用，MD 内引用已改为相对路径。）

## 分层

| 层 | 目录 | 内容 | 是否入库 |
|---|---|---|---|
| L1 图标 | `classes/` | 职阶图标 `{职阶}_{gold\|silver\|bronze}.png`（44 个） | ✅ 入 git |
| | `cards/` | 指令卡图标 `quick/arts/buster.png` | ✅ |
| | `stars/` | 星级 `1star..5star.png` | ✅ |
| | `skills/` | Atlas 技能图标 `skill_XXXXX.png`（MD 引用的唯一集合） | ✅ |
| | `items/` | Atlas 道具图标 `{item_id}.png`（MD 引用的唯一集合） | ✅ |
| L2 从者 | `servants/` | 立绘 `art_{id}.png`、头像 `face_{id}_{asc}.png`、宝具卡图 `npcard_{id}.png`、羁绊礼装 `bondce_{id}.png` | ❌ 本地缓存（约 300MB） |
| 参考 | `ui/` | 原生提取素材（atlas / mooncell / chaldea / classes / stars） | ✅ |
| | `external/` | 网上收集素材，索引与授权见 `external/README.md` | ✅ |

L2 不入库的原因：458 从者 × 立绘约 500KB，体积随从者数量线性增长，且全部可从 Atlas 重新拉取。

## 获取素材

```bash
cd ~/fgo-wiki
./.venv/bin/python scripts/fetch_assets.py --report           # 只看缺口
./.venv/bin/python scripts/fetch_assets.py --icons            # 职阶/指令卡/星级
./.venv/bin/python scripts/fetch_assets.py --skills           # MD 引用的技能图标
./.venv/bin/python scripts/fetch_assets.py --items            # MD 引用的道具图标
./.venv/bin/python scripts/fetch_assets.py --servant 100100   # 单个从者（立绘/头像/宝具卡图/羁绊礼装）
./.venv/bin/python scripts/fetch_assets.py --all-servants      # 全部从者（约 300MB）
```

规则：请求间隔 ≥0.5s、UA `fgo-wiki-updater`、增量跳过已存在文件、404 记录后跳过不中断。

## 出图脚本怎么调用

- **从者卡**（`card-render/build_data.py`）：先查 `assets/servants/`，没有才下载并落库，再复制到渲染缓存 `card-render/assets/`。
- **其它出图脚本**（技能卡、宝具图、羁绊礼装卡等）：同样优先读 `assets/{skills,items,classes,servants}/`，缺失再回退 Atlas。
- MD 里的图标引用已改为相对路径（如 `../../../assets/classes/saber_gold.png`），GitHub 与本地都能直接渲染。

## 来源与授权

| 目录 | 来源 | 授权 |
|---|---|---|
| `classes/`、`cards/`、`stars/` | 游戏 UI 提取 + gears 重绘（见 `external/README.md`） | 素材版权 TYPE-MOON / FGO PROJECT；gears 图标需署名 `gears.link/servanticons` |
| `skills/`、`items/`、`servants/` | Atlas Academy（`static.atlasacademy.io`） | 同上，仅作品内使用 |
| `ui/atlas`、`ui/mooncell`、`ui/chaldea` | 各站提取 | 见各自来源站协议 |
| `external/` | Reddit / 社区 | 见 `external/README.md` 逐条说明 |

## 已知缺口

- `classes/unknown_gold.png`、`unknown_silver.png`、`beasteresh_gold.png`、`beastiv_gold.png`：非正统职阶（loreGrandCaster 等），Atlas 与 jsdelivr 均取不到，MD 中这 46 处仍指向原 CDN。
- `assets/gacha/`：卡池 banner（89 处）仍用 CDN，尚未本地化。
