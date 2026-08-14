#!/usr/bin/env python3
"""
FGO 宝具图渲染器 - 精确高度版 + 技能卡样式
布局：左右分栏，数据顺序：宝具名 → 固定效果 → 升级描述+数值 → OC描述+数值
样式：全部来自技能卡定稿
"""

import os
import requests
from PIL import Image, ImageDraw, ImageFont
import io
import time

# ============================================================
# 配置（技能卡样式）
# ============================================================

CARD_W = 700
PD = 20
GOLD = "#C9A84C"
GOLD_DARK = "#A8893C"
GOLD_LIGHT = "#E8D5A3"
BUSTER_RED = "#CC2233"
NAME_C = "#1A1A2E"
DESC_C = "#1A1A2E"
VAL_C = "#1A1A2E"
NO_C = "#999999"
BG_CARD = "#FAFAF8"
BG_PANEL = "#F5F3F0"
BLK_BG = "#F5F3F0"          # 宝具区块背景
VAL_BG = "#F5F3F0"

VALUE_BOX_W = 80
VALUE_BOX_H = 30

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
            img = img.resize(size, Image.LANCZOS)
        return img
    except:
        return None

def get_text_height(text, font):
    bbox = font.getbbox(text)
    return bbox[3] - bbox[1]

def draw_value_box(draw, x, y, value):
    """技能卡风格数值框：浅灰背景，金色边框，圆角4"""
    draw.rounded_rectangle([x, y, x + VALUE_BOX_W, y + VALUE_BOX_H], radius=4,
                           fill=VAL_BG, outline=GOLD, width=1)
    font = load_font(16, bold=True)
    tw = font.getbbox(value)[2]
    draw.text((x + (VALUE_BOX_W - tw)//2, y + 6), value, font=font, fill=VAL_C)

def draw_gold_line(draw, x1, y, x2, width=2):
    """技能卡风格金色线（带光晕）"""
    draw.line([(x1, y), (x2, y)], fill=GOLD, width=width)
    draw.line([(x1+2, y-1), (x2-2, y-1)], fill=GOLD_LIGHT, width=1)
    draw.line([(x1+2, y+1), (x2-2, y+1)], fill=GOLD_DARK, width=1)

# ============================================================
# 主渲染函数（布局完全来自精确高度版）
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
            {"desc": "付与自身无敌贯通状态(1回合)", "value": None},
            {"desc": "付与无视防御状态(1回合)", "value": None},
            {"desc": "仅在〔水边〕场地上时，Buster指令卡性能提升(1回合)", "value": "20%"},
        ],
        "upgrade_desc": "对敌方全体发动强大的攻击<宝具升级效果提升>",
        "upgrade_values": ["300%", "400%", "450%", "475%", "500%"],
        "oc_desc": "对〔秩序〕特攻<Over Charge时特攻威力提升>",
        "oc_values": ["150%", "162.5%", "175%", "187.5%", "200%"],
    }

    # 字体（技能卡规格）
    f_title = load_font(22, bold=True)   # 宝具名
    f_name = load_font(18, bold=True)    # 保留但不用
    f_desc = load_font(16, bold=True)    # 描述
    f_value = load_font(16, bold=True)   # 数值
    f_no = load_font(14)
    f_footer = load_font(13)
    f_empty = load_font(16)
    f_star = load_font(14)

    # ---------- 精确高度计算 ----------
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

    # ---------- 创建画布（技能卡渐变） ----------
    img = Image.new("RGBA", (CARD_W, total_height), BG_CARD)
    draw = ImageDraw.Draw(img)

    # 微渐变
    for yy in range(total_height):
        ratio = yy / total_height
        r = int(250 - 8 * ratio)
        g = int(250 - 10 * ratio)
        b = int(248 - 11 * ratio)
        draw.line([(0, yy), (CARD_W, yy)], fill=(r, g, b, 255))

    # ---------- 卡片边框（技能卡样式） ----------
    draw.rounded_rectangle([2, 2, CARD_W-2, total_height-2], radius=12,
                           outline=GOLD, width=2)
    draw.rounded_rectangle([6, 6, CARD_W-6, total_height-6], radius=10,
                           outline=(0, 0, 0, 12), width=2)

    y = 20

    # ---------- 星级 ----------
    star_img = download_image(
        "https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main/fgo/icons/stars/star5.png", (103, 24))
    if star_img:
        img.paste(star_img, ((CARD_W - 103)//2, y), star_img)
    else:
        draw.text(((CARD_W - 100)//2, y), "★★★★★", font=load_font(20), fill=GOLD)
    y += 44

    # ---------- 从者信息 ----------
    av_sz = 112
    av = download_image(data["face_url"], (av_sz, av_sz))
    if av:
        draw.rectangle([PD-2, y-2, PD+av_sz+2, y+av_sz+2], outline=GOLD, width=3)
        img.paste(av, (PD, y), av)
    else:
        draw.rectangle([PD, y, PD+av_sz, y+av_sz], outline=GOLD, width=2)

    info_x = PD + av_sz + 20
    name_y = y + 16

    name_text = data["servant_name"]
    no_text = f"No.{data['servant_id']}"
    no_width = f_no.getbbox(no_text)[2]
    max_name_width = CARD_W - PD - no_width - info_x - 20

    name_font = load_font(30, bold=True)
    name_width = name_font.getbbox(name_text)[2]
    if name_width > max_name_width:
        for size in [28, 26, 24]:
            name_font = load_font(size, bold=True)
            if name_font.getbbox(name_text)[2] <= max_name_width:
                break

    draw.text((info_x, name_y), name_text, font=name_font, fill=NAME_C)
    name_bbox = name_font.getbbox(name_text)
    draw_gold_line(draw, info_x, name_y + name_bbox[3] + 2,
                   info_x + name_bbox[2], width=2)

    draw.text((CARD_W - PD - no_width, name_y + 8), no_text, font=f_no, fill=NO_C)

    row2_y = name_y + name_bbox[3] + 16
    ci_sz = 44
    ci = download_image("https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main/fgo/classes/archer_gold.png", (ci_sz, ci_sz))
    if ci:
        img.paste(ci, (info_x, row2_y), ci)
    else:
        draw.rectangle([info_x, row2_y, info_x+ci_sz, row2_y+ci_sz], outline=GOLD, width=2)

    y = row2_y + ci_sz + 20

    # ---------- 主分隔线 ----------
    sep_w = int(CARD_W * 0.7)
    sep_x = (CARD_W - sep_w) // 2
    draw_gold_line(draw, sep_x, y, sep_x + sep_w, width=2)
    y += 16

    # ---------- 宝具区块（技能卡样式块） ----------
    block_x = PD
    block_y = y
    block_w = CARD_W - PD * 2
    block_h = block_h

    # 块阴影
    draw.rounded_rectangle([block_x + 2, block_y + 2,
                            block_x + block_w + 2, block_y + block_h + 2],
                           radius=10, fill=(0, 0, 0, 12))
    # 块主体
    draw.rounded_rectangle([block_x, block_y, block_x + block_w, block_y + block_h],
                           radius=10, fill=BLK_BG, outline=GOLD, width=1)

    # ---------- 右上角水印（极淡） ----------
    icon_img = download_image(data["np_icon_url"])
    if icon_img is not None:
        bg_icon = icon_img.resize((180, 180), Image.LANCZOS)
        bg_icon = bg_icon.convert("RGBA")
        datas = bg_icon.getdata()
        new_data = [(r, g, b, int(a * 0.15)) for r, g, b, a in datas]
        bg_icon.putdata(new_data)
        wm_w, wm_h = bg_icon.size
        wm_x = block_x + block_w - wm_w
        wm_y = block_y
        img.paste(bg_icon, (wm_x, wm_y), bg_icon)

    # ---------- 左侧面板 ----------
    left_w = 100
    left_h = block_h - 12
    left_x = block_x + 12
    left_y = block_y + 6
    draw.rounded_rectangle([left_x, left_y, left_x + left_w, left_y + left_h],
                           radius=6, fill="#FAF8F5", outline=GOLD, width=1)

    # 左侧内容垂直居中
    content_h = 80 + 10 + 28 + 10 + 28
    left_start_y = left_y + (left_h - content_h) // 2

    # Buster 图标
    card_icon = download_image(
        "https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main/fgo/icons/cards/Buster.png", (75, 75))
    if card_icon:
        img.paste(card_icon, (left_x + 12, left_start_y), card_icon)
    left_start_y += 80 + 10

    draw.text((left_x + 12, left_start_y), f"等级 {data['rank']}",
              font=load_font(14), fill=NAME_C)
    left_start_y += 28 + 10

    draw.text((left_x + 12, left_start_y), data["np_type"],
              font=load_font(14), fill=NAME_C)

    # ---------- 右侧内容 ----------
    right_x = left_x + left_w + 16
    right_y = block_y + 6

    # 宝具名（使用技能卡风格：18px 加粗，但为了突出用22px）
    draw.text((right_x, right_y), data["np_name"], font=f_title, fill=NAME_C)
    right_y += get_text_height(data["np_name"], f_title) + 8

    # 固定效果
    for eff in data["fixed_effects"]:
        desc = eff["desc"]
        value = eff["value"] if eff["value"] is not None else "∅"
        draw.text((right_x, right_y), desc, font=f_desc, fill=DESC_C)
        right_y += get_text_height(desc, f_desc) + 4
        draw_value_box(draw, right_x, right_y, value)
        right_y += VALUE_BOX_H + 6

    right_y += 12

    # 升级描述
    draw.text((right_x, right_y), data["upgrade_desc"], font=f_desc, fill=DESC_C)
    right_y += get_text_height(data["upgrade_desc"], f_desc) + 8

    # 升级数值（5个框，但技能卡风格是10列，这里我们保持5列但用技能卡样式）
    bw = 64
    gap = 4
    sx = right_x
    for i, v in enumerate(data["upgrade_values"]):
        x = sx + i * (bw + gap)
        draw.rounded_rectangle([x, right_y, x + bw, right_y + 28], radius=4,
                               fill=VAL_BG, outline=GOLD, width=1)
        val_text = str(v)
        tw2 = f_value.getbbox(val_text)[2]
        draw.text((x + (bw - tw2)//2, right_y + 7), val_text, font=f_value, fill=VAL_C)
        # 星标在 Lv.1, Lv.6, Lv.10 位置，这里只有5个，我们只在第一个和最后一个加星
        if i == 0 or i == 4:
            draw.text((x + bw - 8, right_y - 8), "★", font=f_star, fill=GOLD)
    right_y += 34

    # OC描述
    draw.text((right_x, right_y), data["oc_desc"], font=f_desc, fill=DESC_C)
    right_y += get_text_height(data["oc_desc"], f_desc) + 8

    # OC数值
    for i, v in enumerate(data["oc_values"]):
        x = sx + i * (bw + gap)
        draw.rounded_rectangle([x, right_y, x + bw, right_y + 28], radius=4,
                               fill=VAL_BG, outline=GOLD, width=1)
        val_text = str(v)
        tw2 = f_value.getbbox(val_text)[2]
        draw.text((x + (bw - tw2)//2, right_y + 7), val_text, font=f_value, fill=VAL_C)
        if i == 0 or i == 4:
            draw.text((x + bw - 8, right_y - 8), "★", font=f_star, fill=GOLD)

    # ---------- 底部来源 ----------
    footer_line_y = total_height - 40
    footer_line_w = int(CARD_W * 0.7)
    footer_line_x = (CARD_W - footer_line_w) // 2
    draw.line([(footer_line_x, footer_line_y), (footer_line_x + footer_line_w, footer_line_y)],
              fill=(200, 200, 200, 60), width=1)

    footer_text = "Atlas Academy API · fgo-wiki 本地知识库"
    tw = f_footer.getbbox(footer_text)[2]
    draw.text(((CARD_W - tw)//2, footer_line_y + 8), footer_text, font=f_footer, fill=NO_C)

    img.save(output_path, "PNG")
    print(f"✅ 已生成: {output_path}")

if __name__ == "__main__":
    render_noble_phantasm("/tmp/noble_phantasm.png")
