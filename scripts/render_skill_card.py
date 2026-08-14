#!/usr/bin/env python3
"""FGO skill card v4 - left header, official-style stars, red rank, bigger desc, visible footer."""
import os, math, requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CARD_W = 700
PD = 24
BLK_GAP = 20
FONT_PATH = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
CLASS_DIR = os.path.expanduser("~/fgo-wiki/assets/classes")
CACHE_DIR = os.path.expanduser("~/fgo-wiki/cache/skill-icons")
os.makedirs(CACHE_DIR, exist_ok=True)

# Colors
GOLD = (201, 168, 76)
SILVER = (192, 192, 196)
BRONZE = (205, 127, 50)
DARK = "#1A1A2E"
DARK2 = "#2A2A3A"
LIGHT_GRAY = "#999999"
GRAY = "#666666"
CD_RED = "#E04040"
RANK_RED = "#CC2233"
BLOCK_BG = "#FAFAF8"
BLOCK_BD = "#E8E4E0"
VAL_BG = "#FFFFFF"
VAL_BD = "#D8D0C8"
CARD_BG = "#FFFFFF"
CARD_BD = "#E0DDD8"

def font(sz):
    if os.path.exists(FONT_PATH):
        try: return ImageFont.truetype(FONT_PATH, sz, encoding="unic")
        except: pass
    return ImageFont.load_default()

def bbox(d, t, f):
    b = d.textbbox((0, 0), t, font=f)
    return b[2] - b[0]

def wrap(t, f, mw, d):
    lines, cur = [], ""
    for ch in t:
        if bbox(d, cur + ch, f) > mw and cur:
            lines.append(cur); cur = ch
        else: cur += ch
    if cur: lines.append(cur)
    return lines

def download_img(url, name):
    path = os.path.join(CACHE_DIR, name)
    if os.path.exists(path):
        try: return Image.open(path).convert("RGBA")
        except: pass
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent":"fgo-wiki/1.0"})
        if r.status_code == 200:
            with open(path, "wb") as f: f.write(r.content)
            return Image.open(path).convert("RGBA")
    except: pass
    return None

def square(im, size, radius=0):
    im = im.resize(size, Image.LANCZOS)
    if radius > 0:
        mask = Image.new("L", size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0,0,size[0],size[1]], radius, fill=255)
        out = Image.new("RGBA", size, (0,0,0,0))
        out.paste(im, (0,0), mask)
        return out
    return im

# ── Test data: 源为朝 (No.350) ──
SD = {
    "id": 204600,
    "name": "源为朝",
    "class_id": 13,
    "rarity": 5,
    "face_url": "https://static.atlasacademy.io/CN/Faces/f_2046000.png",
    "collection_no": 350,
}

SKILLS = [
    {
        "name": "镇西八郎",
        "rank": "A",
        "cd": [7, 6, 5],
        "icon": "https://static.atlasacademy.io/CN/SkillIcons/skill_00306.png",
        "effects": [
            {"desc": "自身的力指令卡性能提升(3次·3回合)", "vals": [30, 32, 34, 36, 38, 40, 42, 44, 46, 50]},
            {"desc": "暴击威力提升(3回合)", "vals": [20, 21, 22, 23, 24, 25, 26, 27, 28, 30]},
        ],
    },
    {
        "name": "不屈之弓射",
        "rank": "B",
        "cd": [8, 7, 6],
        "icon": "https://static.atlasacademy.io/CN/SkillIcons/skill_00404.png",
        "effects": [
            {"desc": "付与自身毅力状态(1次·3回合)", "vals": [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 2000]},
            {"desc": "付与「毅力发动时，自身的宝具威力提升(1次·3回合)」", "vals": [10, 11, 12, 13, 14, 15, 16, 17, 18, 20]},
            {"desc": "解除弱化状态(3回合)", "vals": None},
            {"desc": "宝具值增加", "vals": [20, 21, 22, 23, 24, 25, 26, 27, 28, 30]},
        ],
    },
    {
        "name": "机械性弓术",
        "rank": "EX",
        "cd": [9, 8, 7],
        "icon": "https://static.atlasacademy.io/CN/SkillIcons/skill_00310.png",
        "effects": [
            {"desc": "付与自身必中状态(5回合)", "vals": None},
            {"desc": "付与「每回合自身的宝具威力提升(1次·5回合)的状态」(5回合)", "vals": [10, 11, 12, 13, 14, 15, 16, 17, 18, 20]},
            {"desc": "付与每回合获得宝具值的状态(5回合)", "vals": [5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 10]},
        ],
    },
]

def get_star_strip(rarity, accent):
    """Create a horizontal strip of N outlined stars like FGO Wiki style."""
    if rarity <= 0: return None
    sz = 24
    gap = 2
    w = rarity * sz + (rarity - 1) * gap
    h = sz
    strip = Image.new("RGBA", (w, h), (0,0,0,0))
    sdr = ImageDraw.Draw(strip)
    for i in range(rarity):
        x = i * (sz + gap)
        # Draw outlined star
        star = _draw_star((sz, h), accent)
        strip.paste(star, (x, 0), star)
    return strip

def _draw_star(size, color):
    """Draw a single outlined five-point star."""
    w, h = size
    img = Image.new("RGBA", (w, h), (0,0,0,0))
    dr = ImageDraw.Draw(img)
    cx, cy = w/2, h/2
    outer = min(w, h) * 0.45
    inner = outer * 0.4
    pts = []
    for i in range(10):
        ang = math.radians(-90 + i * 36)
        r = outer if i % 2 == 0 else inner
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    dr.polygon(pts, fill=color + (255,))
    # outline
    dr.polygon(pts, outline=(255,255,255,200), width=1)
    return img

def render(sid, out_path):
    rar = SD["rarity"]
    if rar >= 4:
        accent = GOLD; class_suffix = "gold"
    elif rar == 3:
        accent = SILVER; class_suffix = "silver"
    else:
        accent = BRONZE; class_suffix = "bronze"

    f10 = font(10); f11 = font(11); f12 = font(12)
    f14 = font(14); f15 = font(15); f16 = font(16)
    f17 = font(17); f18 = font(18); f20 = font(20)
    f22 = font(22); f28 = font(28)

    # ── Measure blocks ──
    dtmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    block_heights = []
    for sk in SKILLS:
        bh = 60
        for eff in sk["effects"]:
            n = max(len(wrap(eff["desc"], f17, CARD_W - PD*2 - 100, dtmp)), 1)
            bh += n*24 + 10 + 30
        block_heights.append(bh)

    header_h = 130
    h = header_h + sum(block_heights) + BLK_GAP*len(SKILLS) + 52

    # ── Card canvas (crop tightly, no extra shadow bleed) ──
    img = Image.new("RGBA", (CARD_W, h), CARD_BG)
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle([0, 0, CARD_W-1, h-1], 16, outline=CARD_BD, width=1)
    # subtle shadow via border only, no external bleed
    y = PD

    # ═══════════════════════════════════════
    # HEADER: avatar + name left, No./stars/class right
    # ═══════════════════════════════════════
    AV_SZ = 92
    avatar = download_img(SD["face_url"], f"f{sid}.png")
    if avatar:
        avatar = square(avatar, (AV_SZ, AV_SZ), 8)
        # border ring
        ring = Image.new("RGBA", (AV_SZ+8, AV_SZ+8), (0,0,0,0))
        ImageDraw.Draw(ring).rounded_rectangle([2,2,AV_SZ+5,AV_SZ+5], 10, outline=accent, width=3)
        img.paste(ring, (PD-4, y-4), ring)
        img.paste(avatar, (PD, y), avatar)

    name_x = PD + AV_SZ + 18
    # Name
    dr.text((name_x, y + 8), SD["name"], fill=DARK, font=f28)
    # No.
    dr.text((name_x, y + 50), f"No.{SD.get('collection_no','')}", fill=LIGHT_GRAY, font=f16)

    # Right column: arc stars above class icon
    right_x = CARD_W - PD - 90
    right_cx = right_x + 45
    CI_SZ = 50
    ci_y = y + 56
    # Arc stars ABOVE class icon
    if rar > 1:
        arc_r = int(CI_SZ * 1.3)
        cx = right_cx
        cy = ci_y + CI_SZ // 2 - 2
        start_deg = 135
        end_deg = 45
        for i in range(rar):
            frac = i / (rar - 1) if rar > 1 else 0.5
            deg = start_deg + frac * (end_deg - start_deg)
            rad = math.radians(deg)
            sx = cx + arc_r * math.cos(rad)
            sy = cy - arc_r * math.sin(rad)
            star = _draw_star((20, 20), accent)
            img.paste(star, (int(sx - 10), int(sy - 10)), star)

    # Class icon
    class_path = os.path.join(CLASS_DIR, f"{SD['class_id']}_{class_suffix}.png")
    if os.path.exists(class_path):
        ci = square(Image.open(class_path).convert("RGBA"), (CI_SZ, CI_SZ), 8)
        img.paste(ci, (right_x + (90 - CI_SZ)//2, ci_y), ci)

    y += header_h

    # ═══════════════════════════════════════
    # SKILL BLOCKS
    # ═══════════════════════════════════════
    for si, sk in enumerate(SKILLS):
        block_top = y
        block_h = block_heights[si]
        bx = PD + 4
        bw = CARD_W - PD*2

        # Block background + border
        block = Image.new("RGBA", (bw, block_h), BLOCK_BG)
        ImageDraw.Draw(block).rounded_rectangle([0,0,bw-1,block_h-1], 10, outline=BLOCK_BD, width=1)
        img.paste(block, (bx, block_top), block)

        by = block_top + 14

        # Skill icon
        icon_img = download_img(sk["icon"], f"sk{sid}_{si}.png")
        if icon_img:
            icon_img = square(icon_img, (48, 48), 6)
            img.paste(icon_img, (bx + 14, by), icon_img)

        # Skill name
        name_w = bbox(dr, sk["name"], f20)
        dr.text((bx + 72, by + 4), sk["name"], fill=DARK, font=f20)
        # Rank in red
        dr.text((bx + 72 + name_w + 6, by + 6), sk["rank"], fill=RANK_RED, font=f18)

        # Cooldown
        cd_text = " → ".join(str(c) for c in sorted(set(sk["cd"]), reverse=True))
        cd_w = bbox(dr, cd_text, f15)
        dr.text((bx + bw - 14 - cd_w, by + 10), cd_text, fill=CD_RED, font=f15)

        by += 56

        # Effects
        for eff in sk["effects"]:
            desc_lines = wrap(eff["desc"], f17, bw - 36, dr)
            for li, line in enumerate(desc_lines):
                dr.text((bx + 16, by + li*24), line, fill=DARK2, font=f17)
            by += len(desc_lines)*24 + 10

            # Value grid
            vals = eff.get("vals")
            gy = by
            BW = 50
            BGAP = 4
            TW = BW*10 + BGAP*9
            SX = (CARD_W - TW)//2

            if not vals:
                dr.rounded_rectangle([SX, gy, SX+TW, gy+26], 6, fill=VAL_BG, outline=VAL_BD, width=1)
                dr.text((SX + (TW - bbox(dr, "∅", f15))//2, gy+3), "∅", fill=LIGHT_GRAY, font=f16)
                by += 34
            elif len(vals) <= 1:
                dr.rounded_rectangle([SX, gy, SX+TW, gy+26], 6, fill=VAL_BG, outline=VAL_BD, width=1)
                v = vals[0]
                vt = f"{int(v)}%" if isinstance(v, (int,float)) and v < 1000 else str(int(v)) if isinstance(v, (int,float)) else str(v)
                dr.text((SX + (TW - bbox(dr, vt, f16))//2, gy+3), vt, fill=DARK, font=f16)
                by += 34
            else:
                for ci in range(10):
                    cx = SX + ci*(BW+BGAP)
                    v = vals[ci]
                    vt = f"{int(v)}%" if isinstance(v, (int,float)) and v < 1000 else str(int(v)) if isinstance(v, (int,float)) else str(v)
                    dr.rounded_rectangle([cx, gy, cx+BW, gy+26], 5, fill=VAL_BG, outline=VAL_BD, width=1)
                    dr.text((cx + (BW - bbox(dr, vt, f15))//2, gy+4), vt, fill=DARK, font=f15)
                    if ci in (0,5,9):
                        dr.text((cx + BW - 12, gy - 3), "★", fill=GOLD, font=f10)
                by += 34

        y += block_h + BLK_GAP

    # Footer
    foot1 = "Atlas Academy API · fgo-wiki 本地知识库"
    foot2 = "游戏素材版权归 TYPE-MOON / FGO PROJECT 所有"
    fw1 = bbox(dr, foot1, f12)
    fw2 = bbox(dr, foot2, f12)
    dr.text(((CARD_W - fw1)//2, y + 4), foot1, fill=GRAY, font=f12)
    dr.text(((CARD_W - fw2)//2, y + 20), foot2, fill=GRAY, font=f12)

    img.save(out_path, "PNG", dpi=(200,200))
    print(f"✅ {out_path} {CARD_W}x{h} {os.path.getsize(out_path)//1024}KB")

if __name__ == "__main__":
    import time
    t = time.time()
    render(204600, "/tmp/fgo_skill_card_v4.png")
    print(f"{time.time()-t:.2f}s")