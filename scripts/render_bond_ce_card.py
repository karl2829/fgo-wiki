#!/usr/bin/env python3
"""从 entities/bond-ce/ 的礼装 MD 出「某职阶 × 某星级」从者卡图（纯 Pillow）。

用法:
  python3 render_bond_ce_card.py 2052 archer 4 [-o out.png]
  职阶用英文 className（archer/lancer/saber/rider/caster/assassin/berserker/...）

数据源：entities/bond-ce/羁绊礼装：No.{cno} *.md 的「达标从者」节（与知识库同源）
头像：static.atlasacademy.io/CN/Faces/f_{svtId}0.png（128px，本地缓存后放大）
"""
import argparse, glob, json, math, os, re, sys, urllib.request

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

WIKI = os.path.expanduser('~/fgo-wiki')
CACHE = os.path.expanduser('~/.hermes/cache/scratch/bond_ce')
CLASS_ICON_DIR = os.path.join(WIKI, 'assets', 'external', 'reddit-gears-icons', 'class-icons')
FONT = '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
CLASS_CN = {'saber': '剑士', 'archer': '弓兵', 'lancer': '枪兵', 'rider': '骑兵',
            'caster': '魔术师', 'assassin': '暗杀者', 'berserker': '狂战士',
            'ruler': '裁定者', 'avenger': '复仇者', 'alterEgo': 'Alterego',
            'moonCancer': 'MoonCancer', 'foreigner': '降临者', 'pretender': 'Pretender',
            'shielder': '盾兵'}
ATTR_CN = {'human': '人', 'sky': '天', 'earth': '地', 'star': '星', 'beast': '兽'}

BG_TOP = (13, 24, 39)
BG_BOT = (26, 46, 74)
GOLD = (212, 175, 55)
GOLD_L = (240, 217, 140)
WHITE = (238, 243, 250)
GREY = (150, 168, 190)


def load_servants():
    out = {}
    for f in glob.glob(os.path.join(WIKI, 'raw', 'servants', 'CN', '*.json')):
        d = json.load(open(f))
        out[d.get('collectionNo')] = {'svt': d.get('id'), 'name': d.get('name'),
                                      'attr': d.get('attribute'), 'cls': d.get('className')}
    return out


def parse_md(cno):
    hits = glob.glob(os.path.join(WIKI, 'entities', 'bond-ce', f'羁绊礼装：No.{cno} *.md'))
    if not hits:
        sys.exit(f'找不到 No.{cno} 的礼装 MD')
    path = hits[0]
    txt = open(path).read()
    name = re.search(r'^# 羁绊礼装：No\.\d+ (.+)$', txt, re.M).group(1)
    cond = re.search(r'- \*\*加成对象条件\*\*: (.+)', txt)
    full = None
    for m in re.finditer(r'- \*\*原文\*\*: (.+)', txt):
        full = m.group(1)
    # 按职阶节切分
    sections, cur = {}, None
    for line in txt.splitlines():
        h = re.match(r'^### (.+?)（(\d+)）$', line)
        if h:
            cur = h.group(1)
            sections[cur] = []
            continue
        if line.startswith('## '):
            cur = None
            continue
        m = re.match(r'^- (★*) (.+?)\(#(\d+)\)(\s+\*)?(.*)$', line)
        if cur and m:
            sections[cur].append({'stars': len(m.group(1)), 'name': m.group(2),
                                  'cno': int(m.group(3)), 'jp': bool(m.group(4)),
                                  'note': m.group(5).strip()})
    return {'name': name, 'cond': cond.group(1) if cond else '', 'full': full,
            'sections': sections, 'path': path}


def fetch_face(svt):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, f'{svt}.png')
    if not os.path.exists(p):
        url = f'https://static.atlasacademy.io/CN/Faces/f_{svt}0.png'
        urllib.request.urlretrieve(url, p)
    return p


def star_sprite(size, edges=5):
    """高质量金星：4x 超采样 + 垂直金属渐变 + 描边 + 顶部高光。"""
    S = 4
    n = size * S
    cx = cy = n / 2
    r_out, r_in = n * 0.5, n * 0.5 * 0.42
    pts = []
    for i in range(edges * 2):
        ang = -math.pi / 2 + i * math.pi / edges
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    mask = Image.new('L', (n, n), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)

    grad = Image.new('RGBA', (n, n))
    gd = ImageDraw.Draw(grad)
    stops = [(0.0, (255, 250, 225)), (0.28, (252, 225, 150)),
             (0.55, (232, 186, 74)), (0.78, (188, 138, 32)), (1.0, (140, 96, 18))]
    for y in range(n):
        t = y / (n - 1)
        for k in range(len(stops) - 1):
            t0, c0 = stops[k]
            t1, c1 = stops[k + 1]
            if t0 <= t <= t1:
                f = (t - t0) / max(t1 - t0, 1e-6)
                gd.line([(0, y), (n, y)],
                        fill=tuple(int(c0[i] + (c1[i] - c0[i]) * f) for i in range(3)))
                break
    star = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    star.paste(grad, (0, 0), mask)

    # 左上亮边（斜角高光）
    rim = ImageChops.subtract(mask, ImageChops.offset(mask, max(2, n // 90), max(2, n // 90)))
    rim = rim.filter(ImageFilter.GaussianBlur(max(1, n // 200)))
    star = Image.alpha_composite(star, Image.merge(
        'RGBA', (Image.new('L', (n, n), 255), Image.new('L', (n, n), 249),
                 Image.new('L', (n, n), 222), rim.point(lambda v: int(v * 0.72)))))
    sd = ImageDraw.Draw(star)
    sd.line(pts + [pts[0]], fill=(88, 58, 10, 240), width=max(2, n // 26), joint='curve')
    # 顶部高光
    hi = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    hp = [(cx + (x - cx) * 0.52, cy + (y - cy) * 0.52 - n * 0.06) for x, y in pts]
    hm = Image.new('L', (n, n), 0)
    ImageDraw.Draw(hm).polygon(hp, fill=110)
    hi.paste(Image.new('RGBA', (n, n), (255, 255, 250, 255)), (0, 0), hm)
    star = Image.alpha_composite(star, hi)
    # 左上高光点
    dot = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    ImageDraw.Draw(dot).ellipse([n * 0.30, n * 0.22, n * 0.46, n * 0.38], fill=(255, 255, 250, 150))
    dot = dot.filter(ImageFilter.GaussianBlur(max(1, n * 0.012)))
    star = Image.alpha_composite(star, dot)
    # 斜向金属亮带
    band = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    ImageDraw.Draw(band).polygon(
        [(0, n * 0.52), (n * 0.62, 0), (n * 0.95, 0), (0, n * 0.92)],
        fill=(255, 255, 245, 46))
    bm = Image.new('L', (n, n), 0)
    bm.paste(band.split()[3], (0, 0))
    bm = Image.composite(bm, Image.new('L', (n, n), 0), mask)
    star = Image.alpha_composite(star, Image.merge('RGBA', (*band.split()[:3], bm)))
    # 金色柔光
    glow = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    gm = mask.filter(ImageFilter.GaussianBlur(max(2, n * 0.035)))
    glow.paste(Image.new('RGBA', (n, n), (255, 198, 90, 120)), (0, 0), gm)
    star = Image.alpha_composite(glow, star)
    return star.resize((size, size), Image.LANCZOS)


OFFICIAL_STAR = os.path.join(WIKI, 'assets', 'ui', 'stars', 'star_official_single.png')


def star_row(count, size=22, gap=1):
    """优先用官方单颗星素材（51x54，从 5star.png 切出），没有则程序绘制。"""
    if os.path.exists(OFFICIAL_STAR):
        sp = Image.open(OFFICIAL_STAR).convert('RGBA')
        h = size
        w = max(1, round(sp.width * h / sp.height))
        sp = sp.resize((w, h), Image.LANCZOS)
    else:
        sp = star_sprite(size)
        w = size
    row = Image.new('RGBA', (count * w + (count - 1) * gap, h), (0, 0, 0, 0))
    for i in range(count):
        row.paste(sp, (i * (w + gap), 0), sp)
    return row


def add_outline(layer, px=1, color=(16, 12, 6, 235)):
    """给透明图形加一圈深色描边（不是实心底板），保证浅色头像上也能看清。"""
    a = layer.split()[3]
    big = a.filter(ImageFilter.MaxFilter(px * 2 + 1))
    ring = ImageChops.subtract(big, a)
    out = Image.new('RGBA', layer.size, (0, 0, 0, 0))
    out.paste(Image.new('RGBA', layer.size, color), (0, 0), ring)
    return Image.alpha_composite(out, layer)


def with_shadow(layer, blur=2.5, alpha=165, dy=2):
    """给透明素材加柔和投影，返回 (画布, padding)，避免用实心底块挡头像。"""
    pad = 7
    w, h = layer.size
    canvas = Image.new('RGBA', (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    a = layer.split()[3].filter(ImageFilter.GaussianBlur(blur)).point(
        lambda v: int(v * alpha / 255))
    sh = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    sh.paste(Image.new('RGBA', (w, h), (0, 0, 0, 255)), (pad, pad + dy), a)
    canvas = Image.alpha_composite(canvas, sh)
    canvas.paste(layer, (pad, pad), layer)
    return canvas, pad


def class_badge(cls, size=30):
    p = os.path.join(CLASS_ICON_DIR, f'{cls}.png')
    if not os.path.exists(p):
        return None
    im = Image.open(p).convert('RGBA')
    im.thumbnail((size, size), Image.LANCZOS)
    return im


def vgrad(size, top, bot):
    w, h = size
    img = Image.new('RGB', size)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        d.line([(0, y), (w, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    return img


def font(size):
    return ImageFont.truetype(FONT, size)


def rounded_thumb(path, box, radius, ring=3):
    s = int(box * 4)
    im = Image.open(path).convert('RGB').resize((s, s), Image.LANCZOS)
    mask = Image.new('L', (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=int(radius * 4), fill=255)
    return im, mask


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cno', type=int)
    ap.add_argument('cls')
    ap.add_argument('stars', type=int)
    ap.add_argument('-o', '--out', default=None)
    ap.add_argument('--star-size', type=int, default=0, help='星级图标边长，0=按头像 0.10 自动')
    ap.add_argument('--badge-size', type=int, default=0, help='职阶徽章边长，0=按头像 0.32 自动')
    a = ap.parse_args()

    md = parse_md(a.cno)
    svts = load_servants()
    cls_cn = CLASS_CN.get(a.cls, a.cls)
    rows = [r for r in md['sections'].get(cls_cn, []) if r['stars'] == a.stars]
    if not rows:
        sys.exit(f'No.{a.cno} 的{cls_cn} ★{a.stars} 没有达标从者')
    rows.sort(key=lambda r: r['cno'])

    n = len(rows)
    CARD_W, GAP = 184, 22
    W = 96 + n * CARD_W + (n - 1) * GAP
    W = max(W, 900)
    H = 508
    img = vgrad((W, H), BG_TOP, BG_BOT)
    d = ImageDraw.Draw(img)

    # 外框 + 顶/底金线
    d.rectangle([0, 0, W - 1, H - 1], outline=(46, 72, 108), width=2)
    d.line([(0, 128), (W, 128)], fill=(70, 100, 140), width=2)

    d.text((48, 34), f'No.{a.cno}  {md["name"]}', font=font(42), fill=GOLD_L)
    sub = f'{md["cond"]} · {cls_cn} ★{a.stars} · 共 {n} 骑'
    d.text((50, 92), sub, font=font(22), fill=GREY)

    # 右上角加成角标
    badge = '羁绊点数 +20%（最大解放）'
    fb = font(20)
    tw = d.textlength(badge, font=fb)
    d.rounded_rectangle([W - tw - 76, 40, W - 40, 82], radius=10, outline=GOLD, width=2)
    d.text((W - tw - 58, 50), badge, font=fb, fill=GOLD_L)

    total_w = n * CARD_W + (n - 1) * GAP
    x0 = (W - total_w) // 2
    top = 176
    for i, r in enumerate(rows):
        x = x0 + i * (CARD_W + GAP)
        info = svts.get(r['cno'], {})
        # 卡片底
        d.rounded_rectangle([x, top, x + CARD_W, top + 256], radius=14,
                            fill=(20, 36, 58), outline=(52, 82, 122), width=2)
        # 头像
        box, rad, ring = 132, 16, 3
        px = x + (CARD_W - box) // 2
        py = top + 24
        try:
            face = Image.open(fetch_face(info.get('svt') or r['cno'])).convert('RGB')
        except Exception:
            face = Image.new('RGB', (128, 128), (40, 60, 90))
        s = box * 4
        face = face.resize((s, s), Image.LANCZOS)
        mask = Image.new('L', (s, s), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=rad * 4, fill=255)
        face = face.resize((box, box), Image.LANCZOS)
        mask = mask.resize((box, box), Image.LANCZOS)
        img.paste(face, (px, py), mask)
        d.rounded_rectangle([px - ring, py - ring, px + box + ring - 1, py + box + ring - 1],
                            radius=rad + 3, outline=GOLD, width=ring)
        # 名字（超长自动缩字号）
        fs = 21
        while d.textlength(r['name'], font=font(fs)) > CARD_W - 16 and fs > 14:
            fs -= 1
        nm = font(fs)
        tw = d.textlength(r['name'], font=nm)
        d.text((x + (CARD_W - tw) / 2, py + box + 24), r['name'], font=nm, fill=WHITE)
        # 星级图标：贴头像右下角，右对齐、贴边
        ss = a.star_size or max(10, round(box * 0.105))
        gap_s = max(1, round(ss * 0.12))
        row = star_row(min(r['stars'], 5), size=ss, gap=gap_s)
        sx = px + box - 6 - row.width
        sy = py + box - 6 - row.height
        star_layer, sp = with_shadow(add_outline(row, 1), blur=2.5, alpha=190, dy=1)
        img.paste(star_layer, (sx - sp, sy - sp), star_layer)
        # 职阶徽章：头像右上角，方形带金边
        bs = a.badge_size or max(24, round(box * 0.21))
        badge = class_badge(a.cls, bs)
        if badge is not None:
            bx = px + 6
            by = py + 6
            b_layer, bp = with_shadow(add_outline(badge, 1), blur=2.0, alpha=175, dy=1)
            img.paste(b_layer, (bx - bp, by - bp), b_layer)
        # 属性 + 编号
        attr = ATTR_CN.get(info.get('attr'), '')
        tag = f'{attr}属性  #{r["cno"]}'
        ft = font(17)
        tw = d.textlength(tag, font=ft)
        d.text((x + (CARD_W - tw) / 2, py + box + 62), tag, font=ft, fill=GREY)
        # 形态备注
        if r['note'] and '仅部分形态' in r['note']:
            fn = font(15)
            t2 = '仅部分形态'
            tw = d.textlength(t2, font=fn)
            d.text((x + (CARD_W - tw) / 2, py + box + 90), t2, font=fn, fill=(214, 160, 90))

    d.text((48, H - 46), 'FGO 知识库 · 羁绊加成礼装索引', font=font(17), fill=(110, 130, 156))
    src = '数据来源: Atlas Academy API'
    fs2 = font(17)
    d.text((W - d.textlength(src, font=fs2) - 48, H - 46), src, font=fs2, fill=(110, 130, 156))

    out = a.out or os.path.join(CACHE, f'bond_ce_{a.cno}_{a.cls}_{a.stars}.png')
    img.save(out)
    print(out)
    for r in rows:
        print(' ', r['name'], f"#{r['cno']}")


if __name__ == '__main__':
    main()
