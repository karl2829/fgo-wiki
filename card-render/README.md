# FGO 卡面渲染（pytakumi 生产管线）

> **生成规则定版见 [RULES.md](RULES.md)**——数据源、效果四态展示、日文名、资产、数值口径全在那里，改版先改它。

规范第 **2 级**：HTML/CSS → Skia，不起浏览器进程。简单拼装图仍走 PIL。

## 用

```bash
cd ~/fgo-wiki/card-render
.venv/bin/python build_data.py <内部ID>                       # MD → data/<内部ID>.json（含立绘/图标同步）
.venv/bin/python make_card.py <内部ID> -o out/card_x.png      # 渲染（--hero-only 只出从者区）
bash /home/mila/ops/publish_image.sh "$PWD/out/card_x.png"    # 发布 gen.karlhub.cn/<时间戳>_card_x.png
```

`--no-art` 已废弃：立绘固定取 `assets/art_<id>.png`，参数仅为兼容旧命令保留。

视口宽度自动取 `width + 2*bleed`（默认 1080+80=1160），渲染后裁掉多余黑边只留 `margin`。
**别再直接把 width 当视口用**——模板 body 有 40px padding，视口只给 1080 会把右边 80px 连金框一起切掉。

```python
from cardkit.render import render_template, render_html
render_template("servant_card_data.html", "out/card.png")             # 用 templates/ 下的文件
render_html(html_str, "out/x.png", base="templates")                  # 直接喂字符串
```

返回 `{"path", "size", "ms", "bytes"}`。

## 目录

```
build_data.py   数据管线：CN MD 主数据 + JP 日文名 + 宝具解析 + 资产下载
make_card.py    模板填充 + 调用渲染内核
RULES.md        生成规则（定版，改版先改它）
cardkit/
  render.py     渲染入口：注入字体、收集本地图片、dpr 换算、计时
  palette.py    暗色主题色值（与模板 :root 一一对应，PIL 侧也用它）
templates/
  servant_card_data.html      生产模板（唯一在用）
assets/
  art_<id>.png                从者立绘（按从者隔离，禁止共享单文件）
  bond_ce_<id>.png            羁绊礼装图
  badge_<rarity>.png / stars_*  星级徽标与小金星（PIL 自绘）
  {职阶}_{gold|silver|bronze}.png  职阶图标（取自 ~/fgo-wiki/assets/classes）
  其余：指令卡、技能图标
data/           中间 JSON（gitignore，可重新生成）
out/            渲染输出
.venv/          pytakumi 0.1.5 + pillow
```

## 实测开销（本机，阿尔托莉雅从者卡）

| 输出 | 耗时 | 峰值 RSS |
|---|---|---|
| 1080×1430 (dpr 1) | 243 ms | 83 MB |
| 2160×2860 (dpr 2) | 741 ms | 83 MB |
| Chromium 对照 (dpr 2) | 1540 ms | 292 MB |

连跑 100 张内存稳定在 83 MB（对照：html2pic 每张 +25 MB，100 张到 2.65 GB）。

## 改模板时必须知道的坑

1. **中文字体必须显式注入**：pytakumi 不扫系统字体，不传 `fonts=[...]` 全部渲染成豆腐块。
   `cardkit.render.fonts()` 已固定读 `/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc`。
2. **不支持 `::before` / `::after` 装饰块**：要画装饰就写真实 div（模板里的 `.top-gloss` 就是这么来的）。
3. **不支持 `filter: blur()` / `backdrop-filter`**：毛玻璃改成不透明度更高的纯色块（`.art-tag`）。
4. **`filter: drop-shadow()` 有崩渲染的风险**：文字发光一律用 `text-shadow`。
5. **不支持 `clip-path`**；圆角 + `overflow:hidden` 是支持的，裁图用这个。
6. **`dpr` 用法**：传 `width=1080*dpr` 且 `device_pixel_ratio=dpr`。只传 dpr 会得到 1080×2860 这种半残结果。
7. 图片必须通过 `images={src: bytes}` 传入，渲染器不会自己读盘（`render.py` 已自动收集相对路径）。
8. **空 `<div>` 不生成布局盒**：`flex-grow` / `min-height` / `margin-top:auto` 对它都不生效。要压底就 `position:absolute; bottom:0`，要留白就用带内容的元素加 `padding`。
9. **量位置先用临时亮边框实测**（`border:2px solid #f00` + numpy 找纯色行），别按 CSS 数值推像素。

## 支持度速查

✅ flex(+gap/flex:1) · grid(1fr) · 圆角+overflow 裁图 · 线性/径向渐变 · transform:rotate
✅ :nth-child · background-clip:text 烫金 · box-shadow(多重/inset) · text-shadow · 绝对定位
✅ filter:brightness/saturate/contrast · rgba 叠层 · 中文（注字体后）

❌ ::before/::after 盒子 · filter:blur · backdrop-filter · clip-path · 远程图片自动抓取
