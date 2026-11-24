# -*- coding: utf-8 -*-
"""卡面渲染器：pytakumi (HTML → Skia)，不启浏览器进程。

规范定位：第 2 级。能用 PIL 拼的简单图仍应走 PIL；信息密度高的卡走这里。

用法：
    from cardkit.render import render_template
    render_template("dark_servant_card.html", "out.png")

命令行：
    python -m cardkit.render templates/dark_servant_card.html out.png [--width 1080] [--dpr 2]
"""
from __future__ import annotations

import argparse
import io
import os
import pathlib
import re
import time

import pytakumi

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"

# 中文字体必须显式注入：pytakumi 不扫描系统字体，缺字会渲染成豆腐块。
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/source-han-sans/SourceHanSansSC-Regular.otf",
)

_fonts: list[bytes] | None = None


def fonts() -> list[bytes]:
    global _fonts
    if _fonts is None:
        got = [open(p, "rb").read() for p in FONT_CANDIDATES if os.path.exists(p)]
        if not got:
            raise RuntimeError("找不到中文字体，先装 fonts-wqy-zenhei")
        _fonts = got
    return _fonts


def collect_images(html: str, base: pathlib.Path) -> dict[str, bytes]:
    """把 HTML 里引用的本地图片读成 bytes 传给渲染器（pytakumi 不会自己读盘）。"""
    out: dict[str, bytes] = {}
    for src in set(re.findall(r'src="([^"]+)"', html)):
        if src.startswith(("http://", "https://", "data:")):
            continue
        p = (base / src)
        if p.is_file():
            out[src] = p.read_bytes()
    return out


def render_html(
    html: str,
    out_path: str | pathlib.Path,
    *,
    width: int = 1080,
    dpr: int = 2,
    bleed: int = 40,
    margin: int = 10,
    base: str | pathlib.Path | None = None,
) -> dict:
    """渲染一段 HTML 到 PNG。

    width 是卡面 CSS 宽度（1080），bleed 是模板 body 的 padding（用于容纳外发光），
    margin 是裁切后保留的边距（CSS px，留一点发光但要紧贴卡片）。
    视口 = (width + 2*bleed) * dpr，渲染完按 margin 裁掉多余的黑边。
    """
    base_dir = pathlib.Path(base) if base else TEMPLATES
    t0 = time.perf_counter()
    png = pytakumi.html_to_pic(
        html,
        width=int((width + 2 * bleed) * dpr),
        device_pixel_ratio=dpr,
        format="png",
        images=collect_images(html, base_dir) or None,
        fonts=fonts(),
    )
    ms = (time.perf_counter() - t0) * 1000

    from PIL import Image
    im = Image.open(io.BytesIO(png))
    if margin is not None:
        cut = max(0, (bleed - margin)) * dpr
        im = im.crop((cut, cut, im.width - cut, im.height - cut))

    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, format="PNG")
    return {"path": str(out_path), "size": im.size, "ms": round(ms, 0),
            "bytes": out_path.stat().st_size}


def render_template(name: str, out_path: str | pathlib.Path, **kw) -> dict:
    tpl = TEMPLATES / name
    return render_html(tpl.read_text(encoding="utf-8"), out_path, base=tpl.parent, **kw)


def main() -> None:
    ap = argparse.ArgumentParser(description="渲染 FGO 卡面")
    ap.add_argument("template")
    ap.add_argument("out")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--dpr", type=int, default=2)
    ap.add_argument("--bleed", type=int, default=40, help="模板 body padding（容纳外发光）")
    ap.add_argument("--margin", type=int, default=10, help="裁切后保留的边距，0=紧贴卡片")
    a = ap.parse_args()

    kw = dict(width=a.width, dpr=a.dpr, bleed=a.bleed, margin=a.margin)
    p = pathlib.Path(a.template)
    if p.is_file():
        r = render_html(p.read_text(encoding="utf-8"), a.out, base=p.parent, **kw)
    else:
        r = render_template(a.template, a.out, **kw)
    print(f"{r['path']}  {r['size'][0]}x{r['size'][1]}  {r['ms']:.0f} ms  {r['bytes']/1024:.0f} KB")


if __name__ == "__main__":
    main()
