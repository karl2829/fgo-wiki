#!/usr/bin/env python3
"""
FGO 宝具图渲染器 - 纯银灰版（独立脚本）
所有颜色均使用银灰色系，无金色残留
输出到 /tmp/noble_phantasm_silver_final2.png
"""

print("🔥 纯银灰版（独立脚本）已加载")

import os
import requests
from PIL import Image, ImageDraw, ImageFont
import io
import time

# ============================================================
# 配置 - 仅银灰色系
# ============================================================

CARD_W = 700
PD = 20

# 银灰色系（明显与金色不同）
SILVER_MAIN = "#B8B0A0"      # 主边框（灰银色）
SILVER_DARK = "#A09888"      # 暗银灰
SILVER_LIGHT = "#D0C8B8"     # 亮银灰
SILVER_TEXT = "#555555"      # 银灰色文字

# 背景色
BG_CARD = "#F5F2EC"          # 灰白底（偏冷）
BG_PANEL = "#EBE5DC"         # 左侧面板
BLK_BG = "#F0ECE5"           # 宝具区块
VAL_BG = "#EBE5DC"           # 数值框

# 文字颜色
NAME_C = "#1A1A2E"
DESC_C = "#333333"
VAL_C = "#1A1A2E"
NO_C = "#888888"
BUSTER_RED = "#CC2233"
SHADOW_ALPHA = 8

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
    draw.rounded_rectangle([x, y, x + VALUE_BOX_W, y + VALUE_BOX_H], radius=4,
                           fill=VAL_BG, outline=SILVER_MAIN, width=2)
    font = load_font(16, bold=True)
    tw = font.getbbox(value)[2]
    draw.text((x + (VALUE_BOX_W - tw)//2, y + 6), value, font=font, fill=VAL_C)

def draw_silver_line(draw, x1, y, x2, width=3):
    draw.line([(x1, y), (x2, y)], fill=SILVER_MAIN, width=width)
    draw.line([(x1+1, y-1), (x2-1, y-1)], fill=SILVER_LIGHT, width=1)
    draw.line([(x1+1, y+1), (x2-1, y+1)], fill=SILVER_DARK, width=1)

# ============================================================
# 主渲染函数
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

    f_title = load_font(22, bold=True)
    f_desc = load_font(16, bold=True)
    f_value = load_font(16, bold=True)
    f_no = load_font(14)
    f_footer = load_font(13)
    f_empty = load_font(16)
    f_star = load_font(14)

    # ---------- 高度计算 ----------
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

    # ---------- 创建画布 ----------
    img = Image.new("RGBA", (CARD_W, total_height), BG_CARD)
    draw = ImageDraw.Draw(img)

    # 极淡渐变
    for yy in range(total_height):
        ratio = yy / total_height
        r = int(245 - 4 * ratio)
        g = int(242 - 6 * ratio)
        b = int(236 - 8 * ratio)
        draw.line([(0, yy), (CARD_W, yy)], fill=(r, g, b, 255))

    # ---------- 卡片边框 ----------
    draw.rounded_rectangle([2, 2, CARD_W-2, total_height-2], radius=12,
                           outline=SILVER_DARK, width=4)
    draw.rounded_rectangle([6, 6, CARD_W-6, total_height-6], radius=10,
                           outline=(0, 0, 0, SHADOW_ALPHA), width=2)

    # ---------- 稀有度顶线 ----------
    draw.rounded_rectangle([20, 6, CARD_W-20, 9], radius=2, fill=SILVER_MAIN)
    draw.rounded_rectangle([20, 11, CARD_W-20, 12], radius=1, fill=SILVER_LIGHT)

    y = 20

    # ---------- 星级 ----------
    star_img = download_image(
        "https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main/fgo/icons/stars/star5.png", (103, 24))
    if star_img:
        img.paste(star_img, ((CARD_W - 103)//2, y), star_img)
    else:
        draw.text(((CARD_W - 100)//2, y), "★★★★★", font=load_font(20), fill=SILVER_MAIN)
    y += 44

    # ---------- 从者信息 ----------
    av_sz = 112
    av = download_image(data["face_url"], (av_sz, av_sz))
    if av:
        draw.rectangle([PD-2, y-2, PD+av_sz+2, y+av_sz+2], outline=SILVER_MAIN, width=3)
        img.paste(av, (PD, y), av)
    else:
        draw.rectangle([PD, y, PD+av_sz, y+av_sz], outline=SILVER_MAIN, width=2)

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
    draw_silver_line(draw, info_x, name_y + name_bbox[3] + 2,
                     info_x + name_bbox[2], width=3)

    draw.text((CARD_W - PD - no_width, name_y + 8), no_text, font=f_no, fill=NO_C)

    row2_y = name_y + name_bbox[3] + 16
    ci_sz = 44
    ci = download_image("https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main/fgo/classes/archer_gold.png", (ci_sz, ci_sz))
    if ci:
        img.paste(ci, (info_x, row2_y), ci)
    else:
        draw.rectangle([info_x, row2_y, info_x+ci_sz, row2_y+ci_sz], outline=SILVER_MAIN, width=2)

    y = row2_y + ci_sz + 20

    # ---------- 主分隔线 ----------
    sep_w = int(CARD_W * 0.7)
    sep_x = (CARD_W - sep_w) // 2
    draw_silver_line(draw, sep_x, y, sep_x + sep_w, width=3)
    y += 16

    # ---------- 宝具区块 ----------
    block_x = PD
    block_y = y
    block_w = CARD_W - PD * 2
    block_h = block_h

    draw.rounded_rectangle([block_x + 2, block_y + 2,
                            block_x + block_w + 2, block_y + block_h + 2],
                           radius=10, fill=(0, 0, 0, SHADOW_ALPHA))
    draw.rounded_rectangle([block_x, block_y, block_x + block_w, block_y + block_h],
                           radius=10, fill=BLK_BG, outline=SILVER_MAIN, width=2)

    # ---------- 右上角水印 ----------
    icon_img = download_image(data["np_icon_url"])
    if icon_img is not None:
        bg_icon = icon_img.resize((180, 180), Image.LANCZOS)
        bg_icon = bg_icon.convert("RGBA")
        datas = bg_icon.getdata()
        new_data = [(r, g, b, int(a * 0.12)) for r, g, b, a in datas]
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
                           radius=6, fill=BG_PANEL, outline=SILVER_MAIN, width=2)

    content_h = 80 + 10 + 28 + 10 + 28
    left_start_y = left_y + (left_h - content_h) // 2

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

    draw.text((right_x, right_y), data["np_name"], font=f_title, fill=NAME_C)
    right_y += get_text_height(data["np_name"], f_title) + 8

    for eff in data["fixed_effects"]:
        desc = eff["desc"]
        value = eff["value"] if eff["value"] is not None else "∅"
        draw.text((right_x, right_y), desc, font=f_desc, fill=DESC_C)
        right_y += get_text_height(desc, f_desc) + 4
        draw_value_box(draw, right_x, right_y, value)
        right_y += VALUE_BOX_H + 6

    right_y += 12

    draw.text((right_x, right_y), data["upgrade_desc"], font=f_desc, fill=DESC_C)
    right_y += get_text_height(data["upgrade_desc"], f_desc) + 8

    bw = 64
    gap = 4
    sx = right_x
    for i, v in enumerate(data["upgrade_values"]):
        x = sx + i * (bw + gap)
        draw.rounded_rectangle([x, right_y, x + bw, right_y + 28], radius=4,
                               fill=VAL_BG, outline=SILVER_MAIN, width=2)
        val_text = str(v)
        tw2 = f_value.getbbox(val_text)[2]
        draw.text((x + (bw - tw2)//2, right_y + 7), val_text, font=f_value, fill=VAL_C)
        if i == 0 or i == 4:
            draw.text((x + bw - 8, right_y - 8), "★", font=f_star, fill=SILVER_MAIN)
    right_y += 34

    draw.text((right_x, right_y), data["oc_desc"], font=f_desc, fill=DESC_C)
    right_y += get_text_height(data["oc_desc"], f_desc) + 8

    for i, v in enumerate(data["oc_values"]):
        x = sx + i * (bw + gap)
        draw.rounded_rectangle([x, right_y, x + bw, right_y + 28], radius=4,
                               fill=VAL_BG, outline=SILVER_MAIN, width=2)
        val_text = str(v)
        tw2 = f_value.getbbox(val_text)[2]
        draw.text((x + (bw - tw2)//2, right_y + 7), val_text, font=f_value, fill=VAL_C)
        if i == 0 or i == 4:
            draw.text((x + bw - 8, right_y - 8), "★", font=f_star, fill=SILVER_MAIN)

    # ---------- 底部来源 ----------
    footer_line_y = total_height - 40
    footer_line_w = int(CARD_W * 0.7)
    footer_line_x = (CARD_W - footer_line_w) // 2
    draw.line([(footer_line_x, footer_line_y), (footer_line_x + footer_line_w, footer_line_y)],
              fill=(200, 195, 188, 60), width=1)

    footer_text = "Atlas Academy API · fgo-wiki 本地知识库"
    tw = f_footer.getbbox(footer_text)[2]
    draw.text(((CARD_W - tw)//2, footer_line_y + 8), footer_text, font=f_footer, fill=NO_C)

    # ---------- 水印标记 ----------
    draw.text((CARD_W - 120, total_height - 14), "SILVER", font=load_font(12),
              fill=(180, 170, 160, 60))

    img.save(output_path, "PNG")
    print(f"✅ 已生成纯银灰版: {output_path}")
    print(f"  主色: SILVER_MAIN = #B8B0A0")

if __name__ == "__main__":
    render_noble_phantasm("/tmp/noble_phantasm_silver_final2.png")
