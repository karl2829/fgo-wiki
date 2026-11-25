# -*- coding: utf-8 -*-
"""FGO 卡面暗色主题调色板。

数值与 templates/servant_card_data.html 的 :root 变量一一对应；
PIL 侧需要画同风格的元素时直接引用这里，避免两套色值漂移。
"""

# ---------- 底色（三段竖直渐变：顶 → 中 → 底） ----------
BG_TOP = "#17243D"
BG_BASE = "#131E33"
BG_BOTTOM = "#0C1524"
BG_DEEP = "#0B1220"      # 页面外围 / 最深处的底
SEAM = "#141F35"          # 立绘淡出落点：必须等于该高度的底色，否则出硬边

# ---------- 区块 ----------
PANEL = "#1B2A45"
PANEL_HEAD = "#22345A"
PANEL_NP_TOP = "#1E2F4D"
PANEL_NP_BOTTOM = "#182742"
NP_HEAD_TOP = "#263B62"
NP_HEAD_BOTTOM = "#1F3054"
SLOT = "#0F1729"          # 数值槽 / NP 条底

# ---------- 文字 ----------
TEXT_PRIMARY = "#F2EDE3"   # 正文，深底 14.3:1
TEXT_SECONDARY = "#A9B6CC"  # 次要说明，7.0:1
TEXT_TERTIARY = "#8B98AE"   # 标签，4.9:1
TEXT_NUM = "#F0D48A"       # 数值，凹槽上 12.3:1
TEXT_ON_GOLD = "#12192B"   # 压在金色块上的深字，7.2:1

# ---------- 金 / 金属 ----------
GOLD_HI = "#F5E3AE"
GOLD = "#E3C36B"
GOLD_MID = "#C9A227"
GOLD_DARK = "#A8862F"
GOLD_DEEP = "#8A6E1A"
# 金属环 / 烫金渐变停点
METAL_RING = [
    (0, "#6E5620"), (9, "#C9A227"), (19, "#F8EDCB"), (31, "#E8C877"),
    (47, "#A8862F"), (63, "#C9A227"), (79, "#F5E3AE"), (93, "#8A6E1A"), (100, "#C9A227"),
]
METAL_FOIL = [
    (0, "#F8EDCB"), (22, "#E8C877"), (42, "#C9A227"), (52, "#8A6E1A"),
    (64, "#C9A227"), (86, "#F5E3AE"), (100, "#F8EDCB"),
]

# ---------- 功能色 ----------
BLUE = "#5B8FD6"
BLUE_DIM = "#7FA8E0"
BUSTER = "#D8543F"

# ---------- 稀有度（只改线，不改面） ----------
RARITY = {
    5: {"edge": "#E3C36B", "glow": "rgba(227,195,107,.30)"},
    4: {"edge": "#C9A227", "glow": "rgba(201,162,39,.24)"},
    3: {"edge": "#B9C2CC", "glow": "rgba(185,194,204,.22)"},
    2: {"edge": "#B07B4A", "glow": "rgba(176,123,74,.22)"},
    1: {"edge": "#A5703F", "glow": "rgba(165,112,63,.20)"},
}


def rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgba(hex_color: str, alpha: float) -> tuple[int, int, int, int]:
    return (*rgb(hex_color), round(alpha * 255))
