#!/usr/bin/env python3
"""
FGO 技能卡 Pillow 渲染器 - 定稿版（改造：数据从 MD 解析）

用法：
    python3 render_skill_final.py 204600
    python3 render_skill_final.py 350        # 也支持按图鉴编号 collectionNo
    python3 render_skill_final.py            # 默认用 204600（源为朝）

输出：/tmp/skill_card_{id}.png
数据来源：~/fgo-wiki/entities/servants/CN/{内部ID}.md
"""

import os
import re
import sys
import math
import json
import requests
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import io

# ============================================================
# 配置
# ============================================================

CARD_W = 700
PD = 28
BLK_GAP = 18                     # 技能块间距从 22 → 18（去掉分隔线后收窄）
SEP_PCT = 0.70

# 颜色
RED = "#E04040"
NAME_C = "#1A1A2E"
DESC_C = "#1A1A2E"
VAL_C = "#1A1A2E"
EMPTY_C = "#BBBBBB"
NO_C = "#999999"
CARD_BG_TOP = "#FAFAF8"
CARD_BG_BOTTOM = "#F2F0EB"
BLK_BG = "#F5F3F0"
VAL_BG = "#F5F3F0"
SHADOW_COLOR = "#000000"

# 知识库路径
KB_DIR = os.path.expanduser("~/fgo-wiki")
DATA_DIR = os.path.join(KB_DIR, "data")
ENT_DIR = os.path.join(KB_DIR, "entities")
SVT_DIR = os.path.join(ENT_DIR, "servants", "CN")
ID_MAP_PATH = os.path.join(DATA_DIR, "servant_id_map.json")

# ============================================================
# 星级颜色映射
# ============================================================

def get_rarity_color(rarity):
    if rarity >= 4:
        return "#C9A84C"
    elif rarity == 3:
        return "#C0C0C0"
    else:
        return "#CD7F32"

# ============================================================
# 工具函数
# ============================================================

def load_font(size, weight="regular"):
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
        if url.startswith("http"):
            resp = requests.get(url, timeout=5)
            if resp.status_code != 200:
                return None
            img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        else:
            img = Image.open(url).convert("RGBA")
        if size:
            img = img.resize(size, Image.LANCZOS)
        return img
    except Exception as e:
        print(f"⚠️ 下载图片失败: {url} - {e}")
        return None

# ============================================================
# MD 数据解析
# ============================================================

_MD_ICON = re.compile(r"!\[(?:.*?)\]\(([^)]+)\)")


def _parse_rarity(line):
    """从「星级 ★★★★★」提取数字，返回 rarity 或 None"""
    m = re.search(r"★+", line)
    if m:
        return len(m.group(0))
    return None


def _parse_class_gold(line):
    """从职阶图标 URL 提取 (className, 是否金卡)。
    URLs 形如 .../fgo/classes/archer_gold.png 或 archer_silver.png。
    返回 ('archer', True/False, 图标完整URL) 或 (None,...)。"""
    m = re.search(r"fgo/classes/(\w+)_(gold|silver)\.png", line)
    if not m:
        # 指数形式: ![](url) className
        um = re.search(r"\]\(([^)]*classes/(\w+)_(\w+)\.png)\)", line)
        if not um:
            return None, None, None
        return um.group(2), (um.group(3).lower() == "gold"), um.group(1)
    return m.group(1), (m.group(2).lower() == "gold"), m.group(0)


def parse_servant_md(md_path):
    """从从者 MD 文件解析出 (servant, skills) 结构。

    servant: dict(name, rarity, class_name, collection_no, face_url)
    skills: list[{name, rank, cooldown, icon_url, effects:[{desc, values}]}]

    values 为长度 10 的数字列表；无数值效果 values=None。
    """
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    lines = text.splitlines()

    # ---- 头部区块：名称 / 星级 / 图鉴编号 / 职阶 / 头像 ----
    servant = {}
    cn_collect = None
    # 标题行 # 名称
    for ln in lines:
        m = re.match(r"^#\s+(.+)", ln)
        if m:
            servant["name"] = m.group(1).strip()
            break

    rarity = None
    class_name = None
    class_gold = None
    for ln in lines:
        r = _parse_rarity(ln)
        if r:
            rarity = r
        cg, gold, _ = _parse_class_gold(ln)
        if cg:
            class_name = cg
            class_gold = gold

    # 图鉴编号
    m = re.search(r"\*\*图鉴编号\*\*:\s*(\d+)", text) or \
        re.search(r"图鉴编号\s*\|\s*(\d+)", text)
    if m:
        cn_collect = int(m.group(1))

    # 头像（视觉资源 → 再临 1）
    face_url = None
    m = re.search(r"### 头像\s*\n- 再临 1:\s*!\[[^\]]*\]\(([^)]+)\)", text)
    if m:
        face_url = m.group(1).strip()

    servant["rarity"] = rarity if rarity is not None else 5
    servant["class_name"] = class_name or ""
    servant["class_gold"] = class_gold if class_gold is not None else (servant["rarity"] >= 4)
    servant["collection_no"] = cn_collect
    servant["face_url"] = face_url

    # ---- 持有技能区 ----
    skills = []
    # 截取 [## 持有技能, ## 职阶技能) 区间
    sec_start = sec_end = None
    for i, ln in enumerate(lines):
        if re.match(r"^##\s+持有技能", ln):
            sec_start = i
        elif sec_start is not None and re.match(r"^##\s+", ln) and i > sec_start:
            sec_end = i
            break
    if sec_end is None:
        sec_end = len(lines)
    if sec_start is None:
        return servant, []
    sec = lines[sec_start+1:sec_end]

    # 逐行解析技能块
    cur = None

    def parse_vals_row(line):
        """尝试把表格数据行解析为数字列表。解析失败返回 None。"""
        line = line.strip()
        if not line.startswith("|"):
            return None
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            return None
        vals = []
        for c in cells:
            c2 = c.strip().rstrip("%％").strip()
            try:
                v = float(c2)
                if v.is_integer():
                    v = int(v)
                vals.append(v)
            except ValueError:
                # 表头行如 Lv.1 / --- 会在这里失败
                return None
        return vals if vals else None

    i = 0
    next_is_old = False   # 下一个技能块是「◈ 强化前」的旧版技能
    cur_is_old = False    # 当前技能块是否为旧版（结束时丢弃）
    while i < len(sec):
        ln = sec[i].strip()
        # 技能头：### ![icon](url) 名称 等级    充能时间：a→b→c
        mh = re.match(r"^###\s+", ln)
        if mh:
            # 收尾上一技能（cur_is_old 时上一技能是强化前旧版，不加入）
            if cur is not None and not cur_is_old:
                skills.append(cur)
            # 当前新块的旧版标记继承自 next_is_old，并重置 next
            cur_is_old = next_is_old
            next_is_old = False
            cur = {"name": None, "rank": None, "cooldown": [], "icon_url": None, "effects": []}
            rest = re.sub(r"^###\s+", "", ln)
            # 图标 URL
            im = _MD_ICON.search(rest)
            if im:
                cur["icon_url"] = im.group(1)
                rest = rest[:im.start()] + rest[im.end():].lstrip()
            # 充能时间
            cm = re.search(r"充能时间[:：]\s*([\d→\-]+)", rest)
            if cm:
                cur["cooldown"] = [int(x) for x in
                                   re.findall(r"\d+", cm.group(1).replace("→", "-"))]
                rest = rest[:cm.start()].rstrip()
            # 名称 + 等级（等级在名称后，如 "镇西八郎 A"）
            rest = rest.strip()
            # 等级：末尾 A/EX/B++ 等
            rm = re.search(r"\s+([A-Ea-e][Xx\+\＋\-]*)\s*$", rest)
            if rm:
                cur["rank"] = rm.group(1).strip()
                rest = rest[:rm.start()].rstrip()
            else:
                cur["rank"] = None
            cur["name"] = rest.strip() or None
            i += 1
            continue

        # 空行
        if not ln:
            i += 1
            continue

        # 数值表格数据行（以 | 开头且可解析为数字）
        vals = parse_vals_row(ln)
        if vals is not None and cur is not None:
            if cur["effects"]:
                cur["effects"][-1]["values"] = vals
            i += 1
            continue

        # 表头行/分隔行（Lv.1 |---|---）：parse 失败即跳过
        if ln.startswith("|"):
            i += 1
            continue

        # 单行数值（固定值效果，如 "20%" / "1000"）：并入上一 effect 的 fixed_value
        single_num = re.match(r"^([\d.]+)(%|％)?$", ln)
        if single_num and cur is not None and cur["effects"]:
            try:
                fv = float(single_num.group(1))
                if fv.is_integer():
                    fv = int(fv)
            except ValueError:
                fv = ln.strip()
            cur["effects"][-1]["fixed_value"] = fv
            i += 1
            continue

        # 强化本/元信息标注行：跳过（不是效果）
        if ln.startswith("◈"):
            # 「◈ 强化前：XXX」后的下一个技能块是强化前的旧技能，跳过
            next_is_old = True
            i += 1
            continue
        if ln.startswith("此技能由") or ln.startswith("开放条件"):
            i += 1
            continue

        # 普通描述行
        desc = ln.strip()
        if desc in "—" or desc == "":
            i += 1
            continue
        cur["effects"].append({"desc": desc, "values": None})
        i += 1

    if cur is not None and not cur_is_old:
        skills.append(cur)

    # 清理空技能块
    skills = [s for s in skills if s.get("name")]

    return servant, skills


def resolve_md_path(uid):
    """根据内部 ID 或图鉴编号定位 MD 文件路径。返回绝对路径或 None。"""
    raw = str(uid).strip()
    id_map = {}
    if os.path.exists(ID_MAP_PATH):
        with open(ID_MAP_PATH, encoding="utf-8") as f:
            id_map = json.load(f)

    cand = None
    # 1. 直接内部 ID 作为文件名
    if os.path.exists(os.path.join(SVT_DIR, f"{raw}.md")):
        cand = f"{raw}.md"
    else:
        # 2. 图鉴编号 → 内部 ID
        if id_map:
            for sid, info in id_map.items():
                if str(info.get("collectionNo")) == raw and os.path.exists(
                        os.path.join(SVT_DIR, f"{sid}.md")):
                    cand = f"{sid}.md"
                    break
        # 3. 名字
        if not cand:
            for sid, info in id_map.items():
                if info.get("name") == uid and os.path.exists(
                        os.path.join(SVT_DIR, f"{sid}.md")):
                    cand = f"{sid}.md"
                    break

    if not cand:
        return None
    return os.path.join(SVT_DIR, cand)


# ============================================================
# 主渲染函数
# ============================================================

def render_skill_card(servant, skills, output_path):
    rarity = servant.get("rarity", 5)
    ac = get_rarity_color(rarity)

    # 加载字体
    f_title = load_font(30, "bold")
    f_name = load_font(18, "bold")
    f_rank = load_font(18, "bold")
    f_desc = load_font(16, "bold")
    f_value = load_font(16, "bold")
    f_cd = load_font(15, "bold")
    f_no = load_font(14)
    f_footer = load_font(13)
    f_empty = load_font(16)
    f_star = load_font(14)

    # ===== 计算卡片高度 =====
    av_sz = 112
    info_height = 44 + 30 + av_sz + 44

    h = info_height
    for skill in skills:
        h += 52 + 2
        for eff in skill.get("effects", []):
            h += 26 + 28 + 6
        h += BLK_GAP
    h += 48

    # ===== 创建画布（微渐变底） =====
    gradient = Image.new("RGBA", (CARD_W, h), (0, 0, 0, 0))
    grad_draw = ImageDraw.Draw(gradient)
    for y in range(h):
        ratio = y / h
        r = int(250 - 8 * ratio)
        g = int(250 - 10 * ratio)
        b = int(248 - 11 * ratio)
        grad_draw.line([(0, y), (CARD_W, y)], fill=(r, g, b, 255))

    img = Image.new("RGBA", (CARD_W, h), CARD_BG_TOP)
    img = Image.alpha_composite(img, gradient)

    draw = ImageDraw.Draw(img)

    # ===== 卡片边框 =====
    draw.rounded_rectangle([2, 2, CARD_W-2, h-2], radius=12, outline=ac, width=2)

    # ===== 内阴影（透明度从 15 → 12） =====
    shadow_alpha = 12
    shadow_color = (0, 0, 0, shadow_alpha)
    draw.rounded_rectangle([6, 6, CARD_W-6, h-6], radius=10, outline=shadow_color, width=2)

    y = 20

    # ============================================================
    # 星星（从 CDN 加载原始尺寸）
    # ============================================================
    star_urls = {
        1: "https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main/fgo/icons/stars/star1.png",
        2: "https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main/fgo/icons/stars/star2.png",
        3: "https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main/fgo/icons/stars/star3.png",
        4: "https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main/fgo/icons/stars/star4.png",
        5: "https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main/fgo/icons/stars/star5.png",
    }
    star_img = download_image(star_urls.get(rarity, star_urls[5]))
    if star_img:
        sw, sh = star_img.size
        star_x = (CARD_W - sw) // 2
        img.paste(star_img, (star_x, y), star_img)
    else:
        star_text = "★" * rarity
        star_font = load_font(20)
        star_width = star_font.getbbox(star_text)[2]
        draw.text(((CARD_W - star_width) // 2, y), star_text, font=star_font, fill=ac)

    y += 44

    # ============================================================
    # 从者信息区
    # ============================================================

    av = download_image(servant.get("face_url"), (av_sz, av_sz))
    if av:
        draw.rectangle([PD-2, y-2, PD+av_sz+2, y+av_sz+2], outline=ac, width=3)
        img.paste(av, (PD, y), av)
    else:
        draw.rectangle([PD, y, PD+av_sz, y+av_sz], outline=ac, width=2)
        draw.text((PD+av_sz//2-12, y+av_sz//2-10), "?", font=f_title, fill="#999")

    info_x = PD + av_sz + 20

    name_y = y + 16

    name_text = servant.get("name", "")
    no_text = f"No.{servant.get('collection_no', '')}"
    no_width = f_no.getbbox(no_text)[2]
    max_name_width = CARD_W - PD - no_width - info_x - 20

    # 自适应字号
    name_font = load_font(30, "bold")
    name_width = name_font.getbbox(name_text)[2]
    if name_width > max_name_width:
        for size in [28, 26, 24]:
            name_font = load_font(size, "bold")
            if name_font.getbbox(name_text)[2] <= max_name_width:
                break

    draw.text((info_x, name_y), name_text, font=name_font, fill=NAME_C)

    # 从者名下划线
    name_bbox = name_font.getbbox(name_text)
    underline_y = name_y + name_bbox[3] + 2
    draw.line([(info_x, underline_y), (info_x + name_bbox[2], underline_y)], fill=ac, width=1)

    # No.350
    draw.text((CARD_W - PD - no_width, name_y + 8), no_text, font=f_no, fill=NO_C)

    row2_y = name_y + name_font.getbbox(name_text)[3] + 16

    # 职阶图标
    ci_sz = 44
    cls = servant.get("class_name", "").lower()
    # 稀有度 → 职阶图标 tier：4-5★ gold，3★ silver，1-2★ bronze
    if rarity >= 4:
        tier = "gold"
    elif rarity == 3:
        tier = "silver"
    else:
        tier = "bronze"
    # 保底键名：若 class 名不含正确 CDN 键，回退 archer（默认）
    class_key = cls if cls in ("saber","archer","lancer","rider","caster","assassin","berserker",
                                "shielder","ruler","avenger","alterego","mooncancer",
                                "foreigner","pretender") else "archer"
    class_icon_url = f"https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main/fgo/classes/{class_key}_{tier}.png"
    ci = download_image(class_icon_url, (ci_sz, ci_sz))
    if ci:
        img.paste(ci, (info_x, row2_y), ci)
    else:
        draw.rectangle([info_x, row2_y, info_x+ci_sz, row2_y+ci_sz], outline=ac, width=2)
        draw.text((info_x+ci_sz//2-10, row2_y+ci_sz//2-12),
                  {"archer":"弓"}.get(cls, "?"), font=f_name, fill=ac)

    y = row2_y + ci_sz + 20

    # ===== 主分隔线（从者信息区与技能块之间） =====
    sep_w = int(CARD_W * SEP_PCT)
    sep_x = (CARD_W - sep_w) // 2
    draw.line([(sep_x, y), (sep_x + sep_w, y)], fill=ac, width=2)
    y += 16

    # ============================================================
    # 技能块（无分隔线）
    # ============================================================

    for idx, skill in enumerate(skills):
        block_y = y
        block_h = 48 + 2
        for eff in skill.get("effects", []):
            block_h += 26 + 28 + 6
        block_h += 8

        # 技能块阴影
        shadow_offset = 2
        draw.rounded_rectangle([PD+shadow_offset, block_y+shadow_offset, CARD_W-PD+shadow_offset, block_y+block_h+shadow_offset],
                               radius=10, fill=(0,0,0,12))

        # 技能块主体
        draw.rounded_rectangle([PD, block_y, CARD_W-PD, block_y+block_h], radius=10, fill=BLK_BG, outline=ac, width=1)

        inner_y = block_y + 10

        # 技能图标
        ic_sz = 40
        ic = download_image(skill.get("icon_url"), (ic_sz, ic_sz))
        if ic:
            draw.rounded_rectangle([PD+10, inner_y-4, PD+10+ic_sz+4, inner_y-4+ic_sz+4], radius=6, fill="#FFFFFF", outline=ac, width=1)
            img.paste(ic, (PD + 12, inner_y - 2), ic)
        else:
            draw.rectangle([PD+12, inner_y-2, PD+12+ic_sz, inner_y-2+ic_sz], outline=ac, width=1)
            draw.text((PD+12+ic_sz//2-8, inner_y+ic_sz//2-10), "?", font=f_name, fill=NO_C)

        # 技能名
        skill_text = f"{skill.get('name', '')}"
        draw.text((PD + 12 + ic_sz + 16, inner_y + 4), skill_text, font=f_name, fill=NAME_C)

        # 等级标识（红色）
        rank_text = skill.get('rank', '') or ""
        draw.text((PD + 12 + ic_sz + 16 + f_name.getbbox(skill_text)[2] + 6, inner_y + 4), rank_text, font=f_rank, fill=RED)

        # 充能时间
        cd_text = "→".join(map(str, skill.get("cooldown", [])))
        draw.text((CARD_W - PD - 16 - 60, inner_y + 5), cd_text, font=f_cd, fill=RED)

        inner_y += 48

        for eff in skill.get("effects", []):
            draw.text((PD + 16, inner_y), eff["desc"], font=f_desc, fill=DESC_C)
            inner_y += 28

            values = eff.get("values")
            fixed = eff.get("fixed_value")
            bw = 50
            gap = 4
            tw = bw * 10 + gap * 9
            sx = (CARD_W - tw) // 2

            if fixed is not None:
                # 固定值效果：合并单框居中显示（无星标）
                draw.rounded_rectangle([sx, inner_y, sx+tw, inner_y+28], radius=4, fill=VAL_BG, outline=ac, width=1)
                fixed_text = f"{fixed}%" if isinstance(fixed, (int,float)) and fixed < 1000 else str(fixed)
                tw2 = f_value.getbbox(fixed_text)[2]
                draw.text((sx + (tw - tw2)//2, inner_y + 7), fixed_text, font=f_value, fill=VAL_C)
            elif values is None or len(values) == 0:
                # ∅ 占位框
                draw.rounded_rectangle([sx, inner_y, sx+tw, inner_y+28], radius=4, fill=VAL_BG, outline=ac, width=1)
                tw2 = f_empty.getbbox("∅")[2]
                draw.text((sx + (tw - tw2)//2, inner_y + 5), "∅", font=f_empty, fill=EMPTY_C)
            else:
                for i, v in enumerate(values[:10]):
                    x = sx + i * (bw + gap)
                    draw.rounded_rectangle([x, inner_y, x+bw, inner_y+28], radius=4, fill=VAL_BG, outline=ac, width=1)
                    val_text = f"{v}%" if isinstance(v, (int,float)) and v < 1000 else str(v)
                    tw2 = f_value.getbbox(val_text)[2]
                    draw.text((x + (bw - tw2)//2, inner_y + 7), val_text, font=f_value, fill=VAL_C)
                    # 星标
                    if i in [0, 5, 9]:
                        draw.text((x + bw - 8, inner_y - 8), "★", font=f_star, fill=ac)

            inner_y += 32

        y = block_y + block_h + BLK_GAP

        # 已去掉技能块之间的分隔线

    # ===== 底部来源 =====
    footer_line_y = h - 40
    footer_line_w = int(CARD_W * 0.7)
    footer_line_x = (CARD_W - footer_line_w) // 2
    draw.line([(footer_line_x, footer_line_y), (footer_line_x + footer_line_w, footer_line_y)], fill=(200,200,200,60), width=1)

    footer_text = "Atlas Academy API · fgo-wiki 本地知识库"
    tw = f_footer.getbbox(footer_text)[2]
    draw.text(((CARD_W - tw)//2, footer_line_y + 8), footer_text, font=f_footer, fill=NO_C)

    # ===== 保存 =====
    img.save(output_path, "PNG", dpi=(200, 200))
    print(f"✅ 已生成: {output_path}, 尺寸: {CARD_W}x{h}")
    return output_path


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    uid = sys.argv[1] if len(sys.argv) > 1 else "204600"
    md_path = resolve_md_path(uid)
    if not md_path:
        print(f"❌ 无法定位从者 ID/fig鉴编号 {uid} 的 MD 文件")
        sys.exit(1)

    servant, skills = parse_servant_md(md_path)
    sid = os.path.basename(md_path).replace(".md", "")
    out = f"/tmp/skill_card_{sid}.png"
    render_skill_card(servant, skills, out)
