# FGO 卡面渲染（pytakumi 生产管线）

> **生成规则定版见 [RULES.md](RULES.md)**——数据源、效果四态展示、日文名、资产、数值口径全在那里，改版先改它。

规范第 **2 级**：HTML/CSS → Skia，不起浏览器进程。简单拼装图仍走 PIL。

## 用

```bash
cd ~/card-render
.venv/bin/python -m cardkit templates/dark_servant_card.html out/card.png            # 2x，2200×2740
.venv/bin/python -m cardkit templates/dark_servant_card.html out/card.png --dpr 1    # 1x，1100×1370
.venv/bin/python -m cardkit templates/dark_servant_card.html out/card.png --margin 0 # 2x，2160×2700，零边距
```

视口宽度自动取 `width + 2*bleed`（默认 1080+80=1160），渲染后裁掉多余黑边只留 `margin`。
**别再直接把 width 当视口用**——模板 body 有 40px padding，视口只给 1080 会把右边 80px 连金框一起切掉。

```python
from cardkit.render import render_template, render_html
render_template("dark_servant_card.html", "out/card.png")            # 用 templates/ 下的文件
render_html(html_str, "out/x.png", base="templates")                  # 直接喂字符串
```

返回 `{"path", "size", "ms", "bytes"}`。

## 目录

```
cardkit/
  render.py     渲染入口：注入字体、收集本地图片、dpr 换算、计时
  palette.py    暗色主题色值（与模板 :root 一一对应，PIL 侧也用它）
templates/
  servant_frame.html          从者卡通用框架（定版 2026-11-22）：头部 + 特性 + 页脚
                              技能区/宝具区是虚线占位，数据填充下一步再做
  dark_servant_card.html      数据卡 · 深色 · 立绘出血 + 印刷表宝具区
  dark_servant_card_npold.html  同上，宝具区改独立数值框（make_npold.py 生成）
  rarity_frames.html          稀有度三档金属环对照图
assets/
  art/                        立绘池 5 张（asc1..asc4 + costume，512×724）
  art_current.png             当前选中的立绘，模板只引这张
  其余：职阶、指令卡、技能图标、5star.png、bond_ce.png
pick_art.py     立绘随机选择（--art asc2 / --list / --seed N）
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

## 通用框架（servant_frame.html）

出图：`pick_art.py` 选立绘 → `python -m cardkit templates/servant_frame.html out/x.png`，默认 2200×3789。

右栏字段顺序（宁少不多）：职阶图标 + `SERVANT ／ SABER` + 五连星 → 名字 → 日文名 → 属性行 → 分隔线 → ATK/HP → 指令卡 → 特性文字行 → 画师/声优 → 羁绊礼装块。
立绘 432×540 贴左贴顶出血，右下角胶囊 `No.002`；底部 96px 渐隐 + 1px 淡金收口，给角标一个落点。
星级图 `assets/5star.png`（328×86）显示 114×30。稀有度只换金属环：`.card.r3` 银 / `.card.r2` 铜。

## 支持度速查

✅ flex(+gap/flex:1) · grid(1fr) · 圆角+overflow 裁图 · 线性/径向渐变 · transform:rotate
✅ :nth-child · background-clip:text 烫金 · box-shadow(多重/inset) · text-shadow · 绝对定位
✅ filter:brightness/saturate/contrast · rgba 叠层 · 中文（注字体后）

❌ ::before/::after 盒子 · filter:blur · backdrop-filter · clip-path · 远程图片自动抓取
