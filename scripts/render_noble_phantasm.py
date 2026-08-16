#!/usr/bin/env python3
"""
FGO宝具图渲染器 蓝金可读完整版
修复：透明面板文字看不清，改为深蓝半透面板+蓝金数值框，花纹降透明度
"""

import os
import requests
from PIL import Image, ImageDraw, ImageFont
import io

# ============================================================
# 配置
# ============================================================
CARD_W = 700
PD = 20

GOLD = "#D4AF37"
GOLD_DARK = "#A8893C"
GOLD_LIGHT = "#FFE8A3"
DARK_GOLD = "#8B6914"
BUSTER_RED = "#CC2233"

# -------- 文字配色(适配深蓝半透面板) --------
NAME_C = "#FFE8A3"
DESC_C = "#F0E6C8"
VAL_C = "#1A1A2E"
NO_C = "#B8B8CC"
FOOTER_C = "#B8B8CC"

# 宝具面板：深蓝半透背景
NP_PANEL_BG = (20, 35, 70, 210)
# 数值框：蓝金底色
VAL_BG = "#D8B86A"

VALUE_BOX_W = 80
VALUE_BOX_H = 30

SKY_BACKGROUND = True
SKY_BG_FILE = "bg_sky.png"
BG_BOTTOM_COLOR = (10, 25, 60)

# ============================================================
# 工具函数
# ============================================================
def load_font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except:
                continue
    return ImageFont.load_default()

def download_image(url, size=None):
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            return None
        img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        if size:
            img = img.resize(size, Image.Resampling.LANCZOS)
        return img
    except Exception:
        return None

def get_text_height(text, font):
    bbox = font.getbbox(text)
    return bbox[3] - bbox[1]

def draw_rounded_rect(draw, x1, y1, x2, y2, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill, outline=outline, width=width)

def draw_value_box(draw, x, y, value):
    """蓝金风格数值框"""
    draw_rounded_rect(draw, x, y, x + VALUE_BOX_W, y + VALUE_BOX_H, radius=6,
                      fill=VAL_BG, outline=GOLD, width=1)
    font = load_font(16, bold=True)
    tw = font.getbbox(value)[2]
    draw.text((x + (VALUE_BOX_W - tw) // 2, y + 6), value, font=font, fill=VAL_C)

def draw_gold_line(draw, x1, y, x2, width=2):
    draw.line([(x1, y), (x2, y)], fill=GOLD, width=width)
    draw.line([(x1 + 2, y - 1), (x2 - 2, y - 1)], fill=GOLD_LIGHT, width=1)
    draw.line([(x1 + 2, y + 1), (x2 - 2, y + 1)], fill=DARK_GOLD, width=1)

def build_sky_background(card_w, card_h, split_y):
    if not os.path.exists(SKY_BG_FILE):
        canvas = Image.new("RGBA", (card_w, card_h))
        d = ImageDraw.Draw(canvas)
        for yy in range(card_h):
            ratio = yy / card_h
            r = int(90 - 50 * ratio)
            g = int(130 - 70 * ratio)
            b = int(200 - 90 * ratio)
            d.line([(0, yy), (card_w, yy)], fill=(r, g, b, 255))
        return canvas

    raw = Image.open(SKY_BG_FILE).convert("RGBA")
    top_chunk = raw.resize((card_w, split_y), Image.Resampling.LANCZOS)

    sample_color = top_chunk.getpixel((card_w // 2, split_y - 1))
    bot_h = card_h - split_y

    bot_grad = Image.new("RGBA", (card_w, bot_h))
    dg = ImageDraw.Draw(bot_grad)
    r0, g0, b0, _ = sample_color
    r1, g1, b1 = BG_BOTTOM_COLOR

    for yy in range(bot_h):
        t = yy / bot_h
        rr = int(r0 * (1 - t) + r1 * t)
        gg = int(g0 * (1 - t) + g1 * t)
        bb = int(b0 * (1 - t) + b1 * t)
        dg.line([(0, yy), (card_w, yy)], fill=(rr, gg, bb, 255))

    full_bg = Image.new("RGBA", (card_w, card_h))
    full_bg.paste(top_chunk, (0, 0))
    full_bg.paste(bot_grad, (0, split_y))
    return full_bg

def draw_panel_pattern(draw, x1, y1, x2, y2):
    """花纹降低透明度，不抢文字"""
    #四角卷草
    draw.arc([x1 + 10, y1 + 10, x1 + 50, y1 + 50], start=180, end=270, fill=(212, 175, 55, 25), width=2)
    draw.arc([x2 - 50, y1 + 10, x2 - 10, y1 + 50], start=270, end=360, fill=(212, 175, 55, 25), width=2)
    draw.arc([x1 + 10, y2 - 50, x1 + 50, y2 - 10], start=90, end=180, fill=(212, 175, 55, 25), width=2)
    draw.arc([x2 - 50, y2 - 50, x2 - 10, y2 - 10], start=0, end=90, fill=(212, 175, 55, 25), width=2)
    #内部装饰线
    for i in range(6):
        offset = i * 90
        draw.line([(x1 + offset, y1 + 60), (x1 + offset + 40, y1 + 120)], fill=(212, 175, 55, 15), width=1)
        draw.line([(x2 - offset, y2 - 60), (x2 - offset - 40, y2 - 120)], fill=(212, 175, 55, 15), width=1)
    #淡金圆点
    for i in range(8):
        px = x1 + 30 + i * 75
        py = y1 + 30 + (i % 4) * 35
        draw.ellipse([px, py, px + 3, py + 3], fill=(212, 175, 55, 20))

# ============================================================
# 主渲染
# ============================================================
def render_noble_phantasm(output_path):
    data = {
        "servant_name": "源为朝",
        "servant_id": "104200",
        "rarity": 5,
        "face_url": "https://static.atlasacademy.io/CN/Faces/f_1042000.png",
        "np_name": "轰沉·弓张月",
        "np_icon_url": "https://static.atlasacademy.io/CN/Servants/Commands/104200/card_servant_np.png",
        "rank": "B+",
        "card_type": "Buster",
        "np_type": "对舰宝具",
        "fixed_effects": [
            {"desc": "付与自身无敌贯通状态(1回合)", "value": "∅"},
            {"desc": "付与无视防御状态(1回合)", "value": "∅"},
            {"desc": "仅在〔水边〕场地上时，Buster指令卡性能提升(1回合)", "value": "20%"},
        ],
        "upgrade_desc": "对敌方全体发动强大的攻击<宝具升级效果提升>",
        "upgrade_values": ["300%", "400%", "450%", "475%", "500%"],
        "oc_desc": "对〔秩序〕特攻<Over Charge时特攻威力提升>",
        "oc_values": ["150%", "162.5%", "175%", "187.5%", "200%"],
    }

    f_title = load_font(22, bold=True)
    f_name = load_font(18, bold=True)
    f_desc = load_font(16, bold=True)
    f_value = load_font(16, bold=True)
    f_no = load_font(14)
    f_footer = load_font(13)

    #高度计算
    title_h = get_text_height(data["np_name"], f_title)
    right_content_h = title_h + 8

    for eff in data["fixed_effects"]:
        desc_h = get_text_height(eff["desc"], f_desc)
        right_content_h += desc_h + 4
        right_content_h += VALUE_BOX_H + 6

    right_content_h += 12
    upgrade_h = get_text_height(data["upgrade_desc"], f_desc)
    right_content_h += upgrade_h + 8
    right_content_h += VALUE_BOX_H + 12
    oc_h = get_text_height(data["oc_desc"], f_desc)
    right_content_h += oc_h + 8
    right_content_h += VALUE_BOX_H + 8
    block_h = right_content_h

    total_height = 20 + 44 + 20 + 112 + 20 + 16 + 2 + 20 + block_h + 20 + 30

    #背景
    if SKY_BACKGROUND:
        y_temp = 20
        y_temp += 44
        y_temp += 20 + 112 + 20 + 16 + 2 + 20
        SPLIT_Y = y_temp
        img = build_sky_background(CARD_W, total_height, SPLIT_Y)
    else:
        img = Image.new("RGBA", (CARD_W, total_height), (250, 250, 248, 255))
    draw = ImageDraw.Draw(img)

    #外层双层金边
    draw_rounded_rect(draw, 2, 2, CARD_W - 2, total_height - 2, radius=12, outline=GOLD, width=2)
    draw_rounded_rect(draw, 6, 6, CARD_W - 6, total_height - 6, radius=10, outline=DARK_GOLD, width=1)

    y = 20
    #顶部五星
    star_img = download_image("https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main/fgo/icons/stars/star5.png", (103, 24))
    if star_img:
        img.paste(star_img, ((CARD_W - 103) // 2, 6), star_img)
    else:
        draw.text(((CARD_W - 100) // 2, 6), "★★★★★", font=load_font(20), fill=GOLD)

    #头像
    av_sz = 112
    av = download_image(data["face_url"], (av_sz, av_sz))
    if av:
        draw_rounded_rect(draw, PD - 2, y - 2, PD + av_sz + 2, y + av_sz + 2, radius=14, outline=GOLD, width=3)
        img.paste(av, (PD, y), av)

    info_x = PD + av_sz + 20
    name_y = y + 16
    no_text = f"No.{data['servant_id']}"
    no_width = f_no.getbbox(no_text)[2]

    name_font = load_font(30, bold=True)
    name_text = data["servant_name"]
    name_width = name_font.getbbox(name_text)[2]
    max_name_width = CARD_W - PD - no_width - info_x - 20
    if name_width > max_name_width:
        for sz in [28,26,24]:
            name_font = load_font(sz, bold=True)
            if name_font.getbbox(name_text)[2] <= max_name_width:
                break
    draw.text((info_x, name_y), name_text, font=name_font, fill=NAME_C)
    name_bbox = name_font.getbbox(name_text)
    draw_gold_line(draw, info_x, name_y + name_bbox[3] + 2, info_x + name_bbox[2], width=2)

    #右上角编号
    draw.text((CARD_W - PD - no_width, 8), no_text, font=f_no, fill=NO_C)

    #职阶图标
    row2_y = name_y + name_bbox[3] + 16
    ci_sz = 44
    ci = download_image("https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main/fgo/classes/archer_gold.png", (ci_sz, ci_sz))
    if ci:
        img.paste(ci, (info_x, row2_y), ci)

    y = row2_y + ci_sz + 20
    draw_gold_line(draw, PD, y, CARD_W - PD, width=2)
    y += 16

    block_x = PD
    block_y = y
    block_w = CARD_W - PD * 2

    # ==========宝具面板：深蓝半透底板 + 金边==========
    draw_rounded_rect(draw, block_x, block_y, block_x + block_w, block_y + block_h,
                      radius=14, fill=NP_PANEL_BG, outline=GOLD, width=2)
    #绘制淡金花纹
    draw_panel_pattern(draw, block_x, block_y, block_x + block_w, block_y + block_h)

    #右上角淡水印
    draw.text((block_x + block_w - 260, block_y + 10), "Dioscures Tyndaridae",
              font=load_font(22), fill=(180, 180, 180, 180))
    draw.text((block_x + block_w - 240, block_y + 34), "双神赞歌",
              font=load_font(22), fill=(180, 180, 180, 180))

    #左侧区域
    left_x = block_x + 12
    left_y = block_y + 6
    left_w = 100
    content_h = 80 + 10 + 28 + 10 + 28
    left_start_y = left_y + ((block_h -12) - content_h)//2

    card_icon = download_image("https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main/fgo/icons/cards/Buster.png", (75,75))
    if card_icon:
        img.paste(card_icon, (left_x+12, left_start_y), card_icon)
    left_start_y += 80 + 10
    draw.text((left_x +12, left_start_y), f"等级 {data['rank']}", font=load_font(14), fill=DESC_C)
    left_start_y += 28 + 10
    draw.text((left_x +12, left_start_y), data["np_type"], font=load_font(14), fill=DESC_C)

    #右侧文字内容
    right_x = left_x + left_w +16
    right_y = block_y + 6
    draw.text((right_x, right_y), data["np_name"], font=f_title, fill=NAME_C)
    right_y += get_text_height(data["np_name"], f_title) + 8

    for eff in data["fixed_effects"]:
        draw.text((right_x, right_y), eff["desc"], font=f_desc, fill=DESC_C)
        right_y += get_text_height(eff["desc"], f_desc)+4
        draw_value_box(draw, right_x, right_y, eff["value"])
        right_y += VALUE_BOX_H + 6

    right_y +=12
    draw.text((right_x, right_y), data["upgrade_desc"], font=f_desc, fill=DESC_C)
    right_y += get_text_height(data["upgrade_desc"], f_desc)+8

    bw = 64
    gap = 4
    sx = right_x
    for i, v in enumerate(data["upgrade_values"]):
        bx = sx + i*(bw+gap)
        draw_rounded_rect(draw, bx, right_y, bx+bw, right_y+28, radius=6, fill=VAL_BG, outline=GOLD, width=1)
        tw2 = f_value.getbbox(v)[2]
        draw.text((bx + (bw-tw2)//2, right_y+7), v, font=f_value, fill=VAL_C)
    right_y += 34

    draw.text((right_x, right_y), data["oc_desc"], font=f_desc, fill=DESC_C)
    right_y += get_text_height(data["oc_desc"], f_desc)+8
    for i, v in enumerate(data["oc_values"]):
        bx = sx + i*(bw+gap)
        draw_rounded_rect(draw, bx, right_y, bx+bw, right_y+28, radius=6, fill=VAL_BG, outline=GOLD, width=1)
        tw2 = f_value.getbbox(v)[2]
        draw.text((bx + (bw-tw2)//2, right_y+7), v, font=f_value, fill=VAL_C)

    #底部页脚
    footer_line_y = total_height -40
    footer_line_w = int(CARD_W*0.7)
    footer_line_x = (CARD_W-footer_line_w)//2
    draw.line([(footer_line_x, footer_line_y), (footer_line_x+footer_line_w, footer_line_y)],
              fill=(200,200,200,60), width=1)
    footer_text = "Atlas Academy API · fgo-wiki 本地知识库"
    tw = f_footer.getbbox(footer_text)[2]
    draw.text(((CARD_W-tw)//2, footer_line_y+8), footer_text, font=f_footer, fill=FOOTER_C)

    img.save(output_path, "PNG")
    print(f"✅输出完成：{output_path}")

if __name__ == "__main__":
    render_noble_phantasm("/tmp/noble_phantasm.png")

