#!/usr/bin/env python3
"""FGO 从者知识库完整生成器 v3"""

import json, os, sys, re
from collections import defaultdict
from datetime import datetime

from fgo_api_types.nice import (
    NiceServant, NiceFunction, NiceBuff, Vals,
    NiceFuncType, NiceBuffType,
)

WIKI = os.path.expanduser("~/fgo-wiki")

# ── Footer toggle ──
DISABLE_FOOTER = False  # False = 显示版权页脚

# ── Item DB ──
ITEMS_DB_PATH = os.path.join(WIKI, "entities/items/active_items.json")
ITEMS_MAP = {}
if os.path.exists(ITEMS_DB_PATH):
    with open(ITEMS_DB_PATH) as f:
        for it in json.load(f):
            ITEMS_MAP[it["id"]] = it

# Load JP items for JP-only item detection
JP_ITEM_IDS = set()
JP_ITEM_PATH = os.path.join(WIKI, "raw/items/jp_all.json")
if os.path.exists(JP_ITEM_PATH):
    with open(JP_ITEM_PATH) as f:
        for it in json.load(f):
            JP_ITEM_IDS.add(it["id"])

# Load buff calculation rules
BUFF_CALC = {}
BUFF_CALC_PATH = os.path.join(WIKI, "data/buff_calc.json")
if os.path.exists(BUFF_CALC_PATH):
    try:
        with open(BUFF_CALC_PATH, encoding="utf-8") as f:
            BUFF_CALC = json.load(f)
    except:
        pass

CARD_MAP = {"1": "Arts", "2": "Buster", "3": "Quick", "4": "Extra", "10": "Beast"}

# ── 特殊从者登记表 ──
# 技能多模组/宝具多模组/技能内双再临形态等特殊结构，生成时按登记特征走特殊分支。
SPECIAL_SERVANTS = {}
SPECIAL_PATH = os.path.join(WIKI, "data/special_servants.json")
if os.path.exists(SPECIAL_PATH):
    try:
        with open(SPECIAL_PATH, encoding="utf-8") as f:
            _sp = json.load(f)
        for _s in _sp.get("servants", []):
            SPECIAL_SERVANTS[str(_s["internalId"])] = _s
    except Exception as _e:
        print(f"[warn] special_servants.json 加载失败: {_e}", file=sys.stderr)


def is_special_servant(data):
    """返回该从者的特殊登记项，无则 None。"""
    return SPECIAL_SERVANTS.get(str(data.get("id")))


CARD_ICONS = {
    "Arts": "https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main/fgo/icons/cards/Arts.png",
    "Buster": "https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main/fgo/icons/cards/Buster.png",
    "Quick": "https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main/fgo/icons/cards/Quick.png",
    "Beast": "",
}
CDN_BASE = "https://cdn.jsdelivr.net/gh/karl2829/fgo-images@main"
CLASS_NAMES = {
    1: "Saber", 2: "Archer", 3: "Lancer", 4: "Rider",
    5: "Caster", 6: "Assassin", 7: "Berserker",
    8: "Shielder", 9: "Ruler", 10: "Alterego",
    11: "Avenger", 23: "MoonCancer", 25: "Foreigner",
    28: "Pretender", 29: "BeastIV", 33: "Beast",
    38: "BeastEresh", 40: "Beast",
}
def get_class_icon(class_id, rarity):
    name = CLASS_NAMES.get(class_id, "Unknown")
    suffix = "gold" if rarity >= 4 else "silver"
    return f"{CDN_BASE}/fgo/classes/{name.lower()}_{suffix}.png"
ATTR_MAP = {"earth": "地", "human": "人", "sky": "天", "star": "星", "beast": "兽"}
GENDER_MAP = {"female": "女性", "male": "男性", "unknown": "不明", "none": "无"}
ALIGN_POLICY = {"lawful": "秩序", "chaotic": "混沌", "neutral": "中立", "insane": "狂"}
ALIGN_PERSONALITY = {"good": "善", "evil": "恶", "balanced": "中庸", "mad": "狂", "madness": "狂", "bride": "新娘", "summer": "夏"}
TYPE_LABELS = {
    "normal": "常驻", "limited": "限定", "storyLimited": "剧情限定",
    "eventReward": "活动赠送", "heroine": "剧情",
}
FUNCTYPE_NAMES = {
    NiceFuncType.addStateShort: "付与状态",
    NiceFuncType.addState: "付与状态",
    NiceFuncType.damageNp: "伤害",
    NiceFuncType.damageNpIndividual: "对敌方全体伤害",
    NiceFuncType.gainNp: "NP增加",
    NiceFuncType.gainStar: "获得暴击星",
    NiceFuncType.hastenNpturn: "NP回收提升",
    NiceFuncType.lossHp: "HP减少",
    NiceFuncType.subState: "解除强化",
    NiceFuncType.forceInstantDeath: "自身即死",
}
func_type_label = lambda ft: FUNCTYPE_NAMES.get(ft, ft.value if isinstance(ft, NiceFuncType) else str(ft))
SKIP_FUNCTYPES = {NiceFuncType.hastenNpturn}
SKIP_BUFFS = {"暴击率提升"}  # Skip these buff names
VOICE_TYPE_NAMES = {"home": "个人空间", "groeth": "强化", "firstGet": "召唤",
                     "battle": "战斗", "treasureDevice": "宝具"}
TRAIT_BLACKLIST = {
    "genderFemale", "genderMale",
    "classSaber", "classArcher", "classLancer", "classRider", "classCaster",
    "classAssassin", "classBerserker", "classRuler", "classAvenger",
    "classAlterego", "classMooncancer", "classForeigner", "classPretender", "classShielder",
    "attributeEarth", "attributeHuman", "attributeSky", "attributeStar", "attributeBeast",
    "alignmentLawful", "alignmentChaotic", "alignmentNeutral",
    "alignmentGood", "alignmentEvil", "alignmentBalanced",
    "fiveStarServant", "fourStarServant", "threeStarServant", "twoStarServant", "oneStarServant",
    "servant", "canBeInBattle", "standardClassServant", "unknown",
    "skyOrEarthServant", "skyOrEarthExceptPseudoAndDemiServant",
}
TRAIT_NAME_CN = {
    "FSNServant": "FSN从者",
    "alignmentMadness": "狂化",
    "alignmentSummer": "夏日",
    "arthur": "亚瑟",
    "associatedToTheArgo": "阿尔戈号相关",
    "brynhildsBeloved": "布伦希尔德所爱之人",
    "bunnyServant": "兔耳从者",
    "canFlyInSpace": "太空飞行",
    "childServant": "孩童从者",
    "classAlterEgo": "Alterego",
    "classBeastDraco": "Beast(所多玛之兽／德拉科)",
    "classBeastEresh": "Beast(埃列什基伽勒)",
    "classBeastI": "BeastⅠ",
    "classBeastII": "Beast II",
    "classBeastIIIL": "BeastⅢ／L",
    "classBeastIIIR": "BeastⅢ／R",
    "classBeastIV": "BeastⅣ",
    "classLoreGrandCaster": "冠位Caster",
    "classMoonCancer": "MoonCancer",
    "classUOlgaMarieFlare": "火玛丽",
    "classUOlgaMarieGrand": "宏玛丽",
    "defender": "守护者",
    "demon": "恶魔",
    "demonBeast": "魔兽",
    "demonic": "魔性",
    "demonicBeastServant": "魔兽型从者",
    "divine": "神性",
    "divineOrDemonOrUndead": "神魔死灵",
    "divineSpirit": "神灵",
    "dragon": "龙",
    "dragonSlayer": "屠龙者",
    "existenceOutsideTheDomain": "领域外生命",
    "fae": "妖精",
    "fairyTaleServant": "童话从者",
    "feminineLookingServant": "女性外形从者",
    "genderCaenisServant": "性别不明（凯妮斯型）",
    "genderUnknown": "性别不明",
    "genji": "源氏",
    "giant": "巨人",
    "greekMythologyMales": "希腊神话男性",
    "groupServant": "群体从者",
    "hasCostume": "持有灵衣之人",
    "hasGoddessMetamorphosis": "拥有女神变容",
    "hasSupereffectiveNPAgainstAlignmentEvil": "对恶特攻",
    "hasSupereffectiveNPAgainstAlignmentGood": "对善特攻",
    "havingAnimalsCharacteristics": "兽科从者",
    "hominidaeServant": "人科从者",
    "humanoid": "人型",
    "illya": "伊莉雅",
    "immuneToPigify": "猪化无效",
    "king": "王",
    "knightsOfTheRound": "圆桌骑士",
    "lamia": "拉弥亚",
    "levitating": "浮游",
    "livingHuman": "活在当下的人类",
    "mechanical": "机械",
    "moon": "月",
    "nobunaga": "信长",
    "notBasedOnServant": "非从者",
    "obstacleMaker": "妨碍者",
    "oni": "鬼",
    "riding": "骑乘",
    "roman": "罗马",
    "ryozanpaku": "梁山泊",
    "saberClassServant": "Saber职阶从者",
    "saberface": "阿尔托莉雅脸",
    "sakuraSeries": "樱系列",
    "servantsWithSkyAttribute": "天属性从者",
    "shinsengumiServant": "新选组从者",
    "shuten": "酒吞",
    "summerModeServant": "夏日模式",
    "superGiant": "超巨大",
    "threatToHumanity": "人类威胁",
    "undeadOrDemon": "死灵或恶魔",
    "valkyrie": "女武神",
    "weakToEnumaElish": "被EA特攻",
    "wildbeast": "猛兽",
    "yuMeiren": "虞美人",
    "zeroStarServant": "0星从者",
}
SHARED_APPEND = {
    "追击技巧提升": "references/skills/append/追击技巧提升.md",
    "魔力装填": "references/skills/append/魔力装填.md",
    "对骑兵攻击适性": "references/skills/append/对骑兵攻击适性.md",
    "对魔术师攻击适性": "references/skills/append/对魔术师攻击适性.md",
    "特击技巧提升": "references/skills/append/特击技巧提升.md",
    "技能再装填": "references/skills/append/技能再装填.md",
}
# Auto-resolve missing CN append skills by pattern-based path
def resolve_append_ref(name):
    if not name:
        return None
    base = f"references/skills/append/{name}.md"
    if os.path.exists(os.path.join(WIKI, base)):
        return base
    return None

# JP append skill refs
SHARED_APPEND_JP = {
    "追撃技巧向上": "references/skills_jp/append/追撃技巧向上.md",
    "魔力装填": "references/skills_jp/append/魔力装填.md",
    "特撃技巧向上": "references/skills_jp/append/特撃技巧向上.md",
    "スキル再装填": "references/skills_jp/append/スキル再装填.md",
}
def resolve_append_ref_jp(name):
    if not name:
        return None
    base = f"references/skills_jp/append/{name}.md"
    if os.path.exists(os.path.join(WIKI, base)):
        return base
    return None

SHARED_CLASS = {
    "对魔力": "references/skills/class/对魔力.md",
    "骑乘": "references/skills/class/骑乘.md",
    "阵地建造": "references/skills/class/阵地建造.md",
    "单独行动": "references/skills/class/单独行动.md",
    "气息遮断": "references/skills/class/气息遮断.md",
    "狂化": "references/skills/class/狂化.md",
    "神性": "references/skills/class/神性.md",
    "道具作成": "references/skills/class/道具作成.md",
    "女神的神核": "references/skills/class/女神的神核.md",
    "忘却补正": "references/skills/class/忘却补正.md",
    "复仇者": "references/skills/class/复仇者.md",
    "领域外生命": "references/skills/class/领域外生命.md",
    "自我回复（魔力）": "references/skills/class/自我回复（魔力）.md",
    "单独显现": "references/skills/class/单独显现.md",
    "高等从者": "references/skills/class/高等从者.md",
    "兽之权能": "references/skills/class/兽之权能.md",
    "龙种": "references/skills/class/龙种.md",
    "无限的魔力供给": "references/skills/class/无限的魔力供给.md",
    "妖精眼": "references/skills/class/妖精眼.md",
    "人理的守护者": "references/skills/class/人理的守护者.md",
    "重力操控": "references/skills/class/重力操控.md",
}
SHARED_CLASS_JP = {
    "対魔力": "references/skills_jp/class/対魔力.md",
    "単独行動": "references/skills_jp/class/単独行動.md",
    "騎乗": "references/skills_jp/class/騎乗.md",
    "陣地作成": "references/skills_jp/class/陣地作成.md",
    "道具作成": "references/skills_jp/class/道具作成.md",
    "神性": "references/skills_jp/class/神性.md",
    "狂化": "references/skills_jp/class/狂化.md",
    "気配遮断": "references/skills_jp/class/気配遮断.md",
    "復讐者": "references/skills_jp/class/復讐者.md",
    "忘却補正": "references/skills_jp/class/忘却補正.md",
    "自己回復（魔力）": "references/skills_jp/class/自己回復（魔力）.md",
    "女神の神核": "references/skills_jp/class/女神の神核.md",
    "単独顕現": "references/skills_jp/class/単独顕現.md",
    "人理の防人": "references/skills_jp/class/人理の防人.md",
    "千里眼": "references/skills_jp/class/千里眼.md",
}


def get_buff_rule(fn):
    """Get (field, divisor, unit) for a function from buff_calc.json or funcType fallback."""
    buffs = fn.get("buffs", [])
    if buffs:
        bid = str(buffs[0].get("id", ""))
        if bid in BUFF_CALC:
            return (BUFF_CALC[bid]["field"], BUFF_CALC[bid]["divisor"], BUFF_CALC[bid].get("unit", "%"))
    ft = fn.get("funcType", "")
    if ft in (NiceFuncType.gainNp, NiceFuncType.lossNp):
        return ("Value", 100, "%")
    if ft in (NiceFuncType.delayNpturn, NiceFuncType.hastenNpturn):
        return ("Value", 0, "回合")
    if ft in (NiceFuncType.gainStar,):
        return ("Value", 0, "颗")
    return ("Value", 10, "%")


def format_func_val(fn, v):
    """Format a single value from a function using buff_calc rules."""
    field, divisor, unit = get_buff_rule(fn)
    if divisor == 0:
        return str(v)
    result = v / divisor
    if result == int(result):
        return f"{int(result)}%"
    return f"{result:.1f}%"


def get_func_values(fn, next_fn=None):
    """Get display-relevant values from a function. 
    If fn has Value2, the actual value is in next_fn's Value.
    Returns (values_list, is_fixed, formatter)."""
    field, divisor, unit = get_buff_rule(fn)
    svals = fn.get("svals", [])
    _raw_all = [int(sv.get("Value", 0) or 0) for sv in svals]
    # 按约定「值 >= 100000 是内部 id（特性/状态引用），不是展示数值」。
    # 注意：这里只按绝对值判定，不能按换算后大小判（场地/状态 id 常见 2038 量级，
    # 会被误判成 203.8%；真正该拦的是文本侧 —「…特性的状态」这类段落不出数值）。
    if any(v >= 100000 for v in _raw_all):
        return [], True, lambda v: ""
    _raw_all = None
    
    # Check for fixed_display override in buff_calc
    buffs = fn.get("buffs", [])
    if buffs:
        bid = str(buffs[0].get("id", ""))
        if bid in BUFF_CALC and BUFF_CALC[bid].get("fixed_display"):
            return [BUFF_CALC[bid]["fixed_display"]], True, lambda v: str(v)
    
    # Check if this function is linked to next function (buff_calc has_link flag)
    has_link = False
    formula = None
    buffs = fn.get("buffs", [])
    if buffs:
        bid = str(buffs[0].get("id", ""))
        if bid in BUFF_CALC and BUFF_CALC[bid].get("has_link"):
            has_link = True
            formula = BUFF_CALC[bid].get("formula")
    
    if has_link and next_fn is not None:
        # Read value from next function
        next_svals = next_fn.get("svals", [])
        vs = [int(sv.get("Value", 0)) for sv in next_svals]
        while len(vs) < 10: vs.append(vs[-1] if vs else 0)
        vs = vs[:10]
        # Get Value2 from current function for formula
        cur_v2s = [int(sv.get("Value2", 0)) for sv in fn.get("svals", [])]
        while len(cur_v2s) < 10: cur_v2s.append(cur_v2s[-1] if cur_v2s else 0)
        cur_v2s = cur_v2s[:10]
        
        if formula and "step" in formula:
            # Variable formula: base + (v2-1) * step
            result = [formula["base"] + (v2 - 1) * formula["step"] for v2 in cur_v2s]
        elif formula and "mult" in formula:
            # Fixed multiplier: v2 * mult
            result = [v * formula["mult"] for v in cur_v2s]
        else:
            # Default: v2 * 10 = %
            result = [v * 10 for v in vs]
        
        is_fixed = len(set(round(r, 2) for r in result)) <= 1
        fmt = lambda v: f"{v:.0f}%" if v == int(v) else f"{v:.1f}%"
        return result, is_fixed, fmt
    
    # Get formula for non-has_link buffs too
    if formula is None and buffs:
        bid = str(buffs[0].get("id", ""))
        if bid in BUFF_CALC:
            formula = BUFF_CALC[bid].get("formula")
    
    if field == "UseRate":
        vs = [int(sv.get("UseRate", 0)) for sv in svals if sv.get("UseRate") is not None]
    elif field == "Value2":
        vs = [int(sv.get("Value2", 0)) for sv in svals]
    else:
        vs = [int(sv.get("Value", 0)) for sv in svals]
    while len(vs) < 10:
        vs.append(vs[-1] if vs else 0)
    vs = vs[:10]
    
    # Apply formula if present (for non-has_link buffs like 1640, 1641)
    if formula:
        if "step" in formula:
            # FGO standard: step for Lv.1-9, extra bump at Lv.10
            vs = [formula["base"] + (v - 1) * formula["step"] for v in vs]
            if "last_extra" in formula and len(vs) >= 10:
                vs[9] += formula["last_extra"]
            elif "last_val" in formula and len(vs) >= 10:
                vs[9] = formula["last_val"]
        elif "mult" in formula:
            vs = [v * formula["mult"] for v in vs]
        is_fixed = len(set(round(v, 2) for v in vs)) <= 1
        fmt = lambda v: f"{v:.0f}%" if v == int(v) else f"{v:.1f}%"
        return vs, is_fixed, fmt
    
    # 按约定「值 >= 100000 是内部 id（特性/状态引用），不是数值」；
    # 单个值荒谬（>1000% 换算）同样视为非展示数值 —— 970566（状态 id）、
    # 203.8%（内部概率常数）都属这一类。旧逻辑因「不是全部超阈值」而漏渲染。
    if any(v >= 100000 or (divisor and v / divisor > 1000) for v in vs):
        return [], True, lambda v: ""
    pass  # 继续按字段规则换算
    # 「全为 0」= 纯状态标记（回避、即死无效、无敌等），不展示数值；
    # 但 1 可能是真实的「1 次/1 回合」计数，不能一刀切。HP 变动是点数，不受此限。
    if all(v == 0 for v in vs) and fn.get("funcType", "") not in (
            NiceFuncType.delayNpturn, NiceFuncType.hastenNpturn, "lossHp", "lossHpSafe"):
        return [], True, lambda v: ""

    # 自伤/消耗 HP：走 Value 桶是「每级固定点数」，不是百分比，必须原值返回。
    # （千年的报恩/一夜羽织：Value=1000/2000 表示扣 1000/2000 HP）
    if fn.get("funcType", "") in ("lossHp", "lossHpSafe"):
        raw = [int(sv.get("Value", 0) or 0) for sv in svals]
        if raw and any(raw):
            while len(raw) < 10:
                raw.append(raw[-1])
            raw = raw[:10]
            return raw, len(set(raw)) <= 1, lambda v: str(int(v))

    if divisor == 0:
        return vs, len(set(vs)) <= 1, lambda v: str(v)
    # 数值合理性：内部 id 被当成百分比时会出现 1000.9% 这类荒谬值。
    # 真实效果极少超过 1000%，超过即视为「非展示数值」，只保留文本。
    if any(v >= 100000 for v in vs):
        return [], True, lambda v: ""
    return [v/divisor for v in vs], len(set(vs)) <= 1, lambda v: f"{v:.0f}%" if v == int(v) else f"{v:.1f}%"


def format_rate(v):
    """Format Rate values (always in thousandths, 1000 = 100%)."""
    if v is None:
        return None
    result = v / 10
    if result == int(result):
        return f"{int(result)}%"
    return f"{result:.1f}%"


def get_oc_values(fn, ft):
    """Extract OC values from function — handles Value, Correction, and Rate."""
    # Check Correction mode (damage functions: damageNp/damageNpIndividual)
    oc_corrs = []
    for k in ["svals", "svals2", "svals3", "svals4", "svals5"]:
        s = fn.get(k, [])
        if s:
            c = s[0].get("Correction")
            if c is not None:
                oc_corrs.append(c)
    if len(oc_corrs) >= 5 and len(set(oc_corrs)) > 1:
        return [format_val(c, ft) for c in oc_corrs if format_val(c, ft) is not None], "correction"

    # Check Value mode (gainNp etc.)
    oc_vals = []
    for k in ["svals", "svals2", "svals3", "svals4", "svals5"]:
        s = fn.get(k, [])
        if s:
            v = s[0].get("Value")
            if v is not None:
                oc_vals.append(v)
    if len(oc_vals) >= 5 and len(set(oc_vals)) > 1:
        return [format_val(v, ft) for v in oc_vals if format_val(v, ft) is not None], "value"

    # Check Value2 mode (damageNpIndividualSum 特攻 OC values live in Value2 of svals1-5)
    oc_v2 = []
    for k in ["svals", "svals2", "svals3", "svals4", "svals5"]:
        s = fn.get(k, [])
        if s:
            v2 = s[0].get("Value2")
            if v2 is not None:
                oc_v2.append(v2)
    if len(oc_v2) >= 5 and len(set(oc_v2)) > 1:
        return [format_val(v2, ft) for v2 in oc_v2 if format_val(v2, ft) is not None], "value2"

    # Check Rate mode (addState probability effects — 技能封印 etc.)
    oc_rates = []
    for k in ["svals", "svals2", "svals3", "svals4", "svals5"]:
        s = fn.get(k, [])
        if s:
            r = s[0].get("Rate")
            if r is not None:
                oc_rates.append(r)
    if len(oc_rates) >= 5 and len(set(oc_rates)) > 1:
        return [format_rate(r) for r in oc_rates], "rate"

    # No varying OC — return first value as fixed
    if oc_corrs and len(oc_corrs) >= 1:
        return [format_val(oc_corrs[0], ft)] if format_val(oc_corrs[0], ft) else [], "fixed"
    if oc_vals and len(oc_vals) >= 1:
        return [format_val(oc_vals[0], ft)] if format_val(oc_vals[0], ft) else [], "fixed"
    if oc_rates and len(oc_rates) >= 1:
        return [format_rate(oc_rates[0])], "fixed"
    return [], "none"


def get_current_skills(skills):
    """Return current active skills (max priority per num) + old versions."""
    best = {}
    all_by_num = defaultdict(list)
    for sk in skills:
        num = sk.get("num", 0)
        all_by_num[num].append(sk)
        pri = sk.get("priority", 0)
        if num not in best or pri > best[num].get("priority", 0):
            best[num] = sk
    result = [best[n] for n in sorted(best)]
    for sk in result:
        num = sk.get("num", 0)
        # 只有「存在更高 priority 且带 condQuestId 的强化后版本」时，低版本才算强化前。
        # condQuestId 记在强化后那份上；condQuestId 全为 0 的副本是形态切换
        # （托勒密/梅柳齐娜），不能当强化前输出。
        me = sk.get("priority", 0)
        # best 取的是最高 priority，不存在「更高版本」，所以判据是「本版本或更高版本带 condQuestId」
        same_or_later = [s for s in all_by_num[num] if s.get("priority", 0) >= me]
        sk["_old_versions"] = [s for s in all_by_num[num]
                               if s.get("priority", 0) < me] if any(
            s.get("condQuestId") for s in same_or_later) else []
    return result


def get_skill_modules(skills):
    """Detect multi-module servants (双模组: 多套技能组).

    判断逻辑: 同 num 存在多个不同 priority 版本，且所有 num 都有相同数量的
    版本（例如 num1/2/3 各有 priority=1 和 priority=2 两套）→ 多模组。
    返回 (is_multi, modules)：
      - is_multi=True: modules 为 [{priority, skills:[num1..numN]}, ...] 按 priority 升序
      - is_multi=False: modules 为空，调用方走原 get_current_skills 逻辑。
    注意: 强化前后(某单一 num 有旧版本)不属于多模组——只有全部 num 版本数一致才算。
    另外第 2 套及以后的副本若带 condQuestId（强化关卡解锁）→ 一定是强化，
    不是形态切换，直接判为单模组，由 get_current_skills 取最新版本。
    """
    by_num = defaultdict(list)
    for sk in skills:
        by_num[sk.get("num", 0)].append(sk)
    nums = sorted(by_num.keys())
    if not nums:
        return False, []
    counts = {len(by_num[n]) for n in nums}
    # 所有 num 都有 ≥2 个版本且数量完全一致 → 多模组
    if len(counts) == 1 and next(iter(counts)) >= 2:
        # 强化闸门：任何一套「非首版」副本带 condQuestId，说明是强化解锁而非形态切换
        for n in nums:
            vers = sorted(by_num[n], key=lambda s: s.get("priority", 0))
            for sk in vers[1:]:
                if sk.get("condQuestId"):
                    return False, []
        nver = next(iter(counts))
        modules = []
        for v in range(nver):
            mod_skills = []
            for n in nums:
                # 该 num 中第 v 优先级版本
                vers = sorted(by_num[n], key=lambda s: s.get("priority", 0))
                mod_skills.append(vers[v])
            modules.append({"priority": v + 1, "skills": mod_skills})
        return True, modules
    return False, []


def get_np_modules(nps):
    """Detect multi-module NP servants (双宝具模组: 多套宝具, num 不同).

    普通强化宝具: 所有宝具 num 相同（均为 1），仅 priority 不同（如 101/102
    表示强化前/强化后）→ 单模组，走原逻辑。
    双宝具模组: 存在多个不同 num（如玉兔 num=1 + num=98）→ 多模组，
    每个 num 独立渲染为「宝具模组 N」。
    返回 (is_multi, modules)：
      - is_multi=True: modules 为 [{num, np}, ...] 按 num 升序
      - is_multi=False: modules 为空，调用方走原 priority 排序逻辑。
    """
    if not nps:
        return False, []
    # 过滤 ??? 占位宝具版本（与正式版本成对、效果重复）；全占位时兜底保留
    nps = [n for n in nps if n.get("name") != "？？？"]
    if not nps:
        return False, []
    nums = {np.get("num", 1) for np in nps}
    if len(nums) > 1:
        modules = sorted(nps, key=lambda x: (x.get("num", 0), x.get("priority", 0)))
        return True, modules
    return False, []


def format_cool_down(cd):
    """Format cooldown as 7→6→5 transitions."""
    if not cd:
        return ""
    transitions = []
    prev = None
    for c in cd:
        if c != prev:
            transitions.append(str(c))
            prev = c
    return "→".join(transitions)


def format_val(v, func_type=""):
    """Backward-compat: format a value by funcType (no buff_calc)."""
    if v is None:
        return None
    if isinstance(v, str):
        try:
            v = int(v)
        except ValueError:
            return str(v)
    div = 100 if func_type in (NiceFuncType.gainNp, NiceFuncType.lossNp) else (0 if func_type == NiceFuncType.gainStar else 10)
    if div == 0:
        return str(v)
    result = v / div
    if result == int(result):
        return f"{int(result)}%"
    return f"{result:.1f}%"


def get_scale_div(func_type):
    """Backward-compat."""
    return 100 if func_type in (NiceFuncType.gainNp, NiceFuncType.lossNp) else (0 if func_type == NiceFuncType.gainStar else 10)


def _func_usable(fn):
    """该函数是否可能承载「detail 里写明的那条效果」。

    排除两类：数值是内部状态 id 的壳函数、只有 buff 引用没有可读数值的态函数。
    但「付与〔特性〕」这类函数虽然有 buff，数值确实是内部特性 id，
    文本明确写了「付与〔…〕特性」时应由它承载，不能整体排除。
    """
    vals = [v.get("Value") for v in fn.get("svals", [])]
    if vals and all(isinstance(v, (int, float)) and v >= 100000 for v in vals):
        popup = fn.get("funcPopupText") or ""
        names = " ".join(b.get("name") or "" for b in fn.get("buffs", []))
        if "特性" in popup or "特性" in names:
            return True
        return False
    return True


def _norm_txt(s):
    return (s or "").replace(" ", "").replace(":", "").replace("：", "")


def _fn_named_in(fn, part):
    """该函数是否被这段文本「点名」（弹窗文本 / buff 名 / buff 说明出现在段里）。"""
    p = _norm_txt(part)
    if not p:
        return False
    cands = [fn.get("funcPopupText") or ""]
    for b in fn.get("buffs", []) or []:
        cands.append(b.get("name") or "")
        cands.append(b.get("detail") or "")
    for c in cands:
        c = _norm_txt(c)
        if len(c) >= 2 and c in p:
            return True
        if len(c) >= 5:
            # 长片段命中（≥4 字）也算点名：内部名常被缩写
            for k in range(len(c) - 3):
                if c[k:k + 4] in p:
                    return True
    return False


_STRAY_QUOTE_RE = re.compile(r"[」』][^，。]{0,3}(?=[(（<【]|\)|$)")
# 「付与「<效果>」的状态」这类段：引号里是触发时机/内部机制，数据侧只有一条壳函数，
# 渲染时只保留文本（例：卫宫〔Assassin〕射杀封杀、奥伯龙梦之终结、Passionlip 公主的指令）。
_WRAPPER_RE = re.compile(r"付与[^「]{0,10}「.+」[^」]{0,8}?的状态|付与[^「]{0,10}「.+」$")


def _is_wrapper_effect(seg):
    s = _clean_detail_text(seg).strip()
    return bool(_WRAPPER_RE.search(s.replace("\n", "")))


def _clean_detail_text(s):
    # Atlas 的 detail 里残留了成对引号的一半（解除弱化状态」(3回合)），
    # 它是数据噪音，会让文本匹配失败并丢掉整段数值。
    return _STRAY_QUOTE_RE.sub("", s)


def match_func_to_segment(segment, funcs, used_indices):
    """Match a detail segment to the best corresponding function by text similarity.
    Uses substring match as priority, then bigram overlap as fallback.
    「效果由另一种状态触发」的段（`付与「X(1次)」的状态`）在数据里只是一条壳函数，
    它的全部代价就是那行文本，不该再配数值——否则会把后面函数的数值张冠李戴。"""
    if _is_wrapper_effect(segment):
        return None
    segment = _clean_detail_text(segment)
    best_idx = None
    best_score = 0
    for fi, fn in enumerate(funcs):
        if fi in used_indices:
            continue
        ft = fn.get("funcType", "")
        if not _func_usable(fn) and not fn.get("funcPopupText"):
            continue
        # 必须让它参与匹配，否则该段会被判定为未匹配而丢掉数值。
        # 仅排除真正的内部子状态函数（funcTargetType=ptOne 的内部态）
        if ft in (NiceFuncType.subState,) and not fn.get("funcPopupText"):
            continue
        # Collect all searchable text from this function
        texts = set()
        for b in fn.get("buffs", []):
            if b.get("detail"): texts.add(b["detail"])
            if b.get("name"): texts.add(b["name"])
        texts.add(fn.get("funcPopupText", ""))
        texts.discard("")
        # 无 buff 的特殊函数类型：用中英文名做匹配关键字
        if not texts and ft in FUNCTYPE_KEYWORDS:
            texts.add(FUNCTYPE_KEYWORDS[ft])
        # 没有 buf 但仍有可读数值的函数（充能增减等），补上关键字
        if not texts and ft in ("hastenNpturn", "delayNpturn"):
            texts.add(FUNCTYPE_KEYWORDS[ft])
        # subState（解除类）自带文本，但 funcPopupText 有时为空，补上
        if ft == "subState" and fn.get("funcPopupText"):
            texts.add(fn["funcPopupText"])

        for txt in texts:
            score = 0
            # Strong priority: substring match
            if txt in segment or segment in txt:
                score = len(txt) + len(segment)  # High score for substring match
            else:
                # Bigram (2-char) overlap - more accurate than single chars
                seg_bigrams = set(segment[i:i+2] for i in range(len(segment)-1))
                txt_bigrams = set(txt[i:i+2] for i in range(len(txt)-1))
                overlap = len(seg_bigrams & txt_bigrams)
                # Penalize short bigrams that are common noise
                noise = {"状态", "效果", "自身", "敌方", "单体", "全体", "付与", "回合"}
                overlap -= len(seg_bigrams & noise & txt_bigrams)
                score = max(0, overlap)
            # 4 字以上的精确文本片段命中，优先于零散 bigram 重叠。
            # （避免「技指令卡的暴击星集中度提升」被「暴击率提升:技」抢走）
            for k in range(len(txt) - 3):
                sub = txt[k:k+4]
                if sub in segment:
                    score = max(score, 50 + len(sub))
            # 状态效果按「名称整体出现在文本里」加权重：全称命中才算真匹配。
            # （避免「付与自身回避状态」里含子串「必中状态」而被 必中 抢走）
            if txt and txt in segment and len(txt) >= 6:
                score = max(score, 80 + len(txt))
            if txt and txt in segment and len(txt) < 6:
                score = max(score, 20 + len(txt))
            # 弹窗名 / buff 名整体出现在段里，是很强的点名证据，但不能压过
            # 「长文本整体包含」：多卡副本里的短名（暴击率提升:技）会趁机抢走
            # 本该属于（宝具值增加）的段。这里只与常规分数同量级。

            if score > best_score:
                best_score = score
                best_idx = fi

    # 名称命中判定：只看「紧邻「状态」二字的那个效果名」是否出现在文本里。
    # 例如「付与自身回避状态」里虽然有子串「必中状态」，但紧邻「状态」的是「回避」，
    # 因此「必中」不算命中——避免状态类文本互相抢匹配。
    # 只有当文本里出现「X状态」结构时才启用这个校验；其余情况沿用相似度结果。
    def _named_in(fn, seg):
        cands = [b.get("name") or "" for b in fn.get("buffs", [])]
        cands += [fn.get("funcPopupText") or ""]
        for c in cands:
            c = c.strip()
            if not c:
                continue
            if f"{c}状态" in seg:
                return True
            if c in seg and not re.search(r"[^\s]{2,}状态", seg):
                return True
        return False

    if best_idx is not None and re.search(r"[^\s]{1,}状态", segment):
        if not _named_in(funcs[best_idx], segment):
            for cand in range(len(funcs)):
                if cand in used_indices:
                    continue
                if _named_in(funcs[cand], segment):
                    best_idx = cand
                    break

    # 兜底：状态类文本（晕眩/即死/延迟等）若没匹配上，挑一个还没有文本对应的
    # 状态函数补上数值，至少不让数据完全丢失。
    if best_idx is None and re.search(r"(晕眩|眩晕|即死|延迟|发动|特性)", segment):
        for fi in range(len(funcs)):
            if fi in used_indices:
                continue
            fn = funcs[fi]
            if fn.get("funcType") in ("addState", "subState"):
                return fi
    # 兜底：整段是「随机付与…各种效果」这种笼统描述时，原文没有分项，
    # 按顺序把该技能剩下的函数各渲染一次，避免数值全部丢失。
    if best_idx is None and "随机" in segment and "各种效果" in segment:
        for fi in range(len(funcs)):
            if fi not in used_indices:
                return fi

    if best_idx is None:
        best_idx = _fallback_match(segment, funcs, used_indices)
    return best_idx


# 无 buff 的函数类型 → 匹配关键字（用于没有 funcPopupText 的回血/解异常等）
FUNCTYPE_KEYWORDS = {
    "gainHp": "生命值回复",
    "gainHpFromTargets": "吸收",
    "lossHp": "生命值减少",
    "lossHpSafe": "生命值减少",
    "gainStar": "获得暴击星",
    "gainNp": "宝具值增加",
    "lossNp": "宝具值减少",
    "hastenNpturn": "充能增加",
    "delayNpturn": "充能减少",
    "subState": "解除",
}

# 语义类函数：没有具体数值可展示，渲染时只保留文本、不输出孤立的「100%」
# 这些函数常与「额外伤害/即死/目标集中」等文本同段，数值本身不是可读效果。
TEXT_ONLY_FUNCTYPES = {"subState"}

# 同一 buff 在文本段之外多出来的函数（detail 不会逐条写出来），
# 渲染时静默吸收，不重复占一段文本，也不会把数值错配到下一条效果上。
# 144 = 暴击发生率提升（常作为副作用附加）
# hastenNpturn = 充能增加（NP 增加类技能的固定伴随项，不单独占文本段）
SECONDARY_BUFF_IDS = {"144"}
SILENT_FUNCTYPES = {"hastenNpturn"}


def _fallback_match(segment, funcs, used_indices):
    """文本段没匹配上时：按语义补配对或吸收副效果函数。

    1) 文本含「回复」→ 找未用的 gainHp
    2) 文本含「解除」「弱化」→ 找未用的 subState
    3) 否则吸收一个未用的副效果函数（暴击率提升等），避免数值错位
    """
    free = [i for i in range(len(funcs)) if i not in used_indices]
    if not free:
        return None

    def find_by_type(pred):
        for i in free:
            if pred(funcs[i]):
                return i
        return None

    if "回复" in segment:
        i = find_by_type(lambda f: f.get("funcType") == "gainHp")
        if i is not None:
            return i
    if "暴击星" in segment:
        i = find_by_type(lambda f: f.get("funcType") == "gainStar")
        if i is not None:
            return i
    if "宝具值" in segment:
        i = find_by_type(lambda f: f.get("funcType") == "gainNp")
        if i is not None:
            return i
    if "生命值" in segment:
        i = find_by_type(lambda f: f.get("funcType") in ("gainHp", "lossHp", "lossHpSafe"))
        if i is not None:
            return i
    if "解除" in segment:
        # 先在「没被别段占用的状态函数」里找名字点名的，找不到再退回通用的 subState。
        # （不屈之弓射：「毅力时发动(宝具威力提升＆弱化解除)」先占了 addState，
        #   紧接着的「解除弱化」若也去抓状态函数，整段就会丢。）
        i = find_by_type(lambda f: f.get("funcType") in ("subState", "addState", "addStateShort")
                         and any(c and c.replace(" ", "") in segment.replace(" ", "")
                                 for c in ([(f.get("funcPopupText") or "")] +
                                           [b.get("name") or "" for b in f.get("buffs", [])])))
        if i is not None:
            return i
        i = find_by_type(lambda f: f.get("funcType") == "subState")
        if i is not None:
            return i
    # 吸收类文本（「吸收…生命值」= drain）：找 damageNp/gainHp 组合里的吸血函数，
    # 通常表现为 subState(减益) + gainHp 成对；优先拿无 buff 的 gainHp
    if "吸收" in segment:
        i = find_by_type(lambda f: f.get("funcType") == "gainHp")
        if i is not None:
            return i
        i = find_by_type(lambda f: str(f.get("funcType", "")).startswith("damage"))
        if i is not None:
            return i
    # 「眩晕」「晕眩」→ addState 系列
    if "眩晕" in segment or "晕眩" in segment:
        i = find_by_type(lambda f: "addState" in str(f.get("funcType", ""))
                         and any("晕" in (b.get("name") or "") for b in f.get("buffs", [])))
        if i is not None:
            return i
    # 文本里额外写了「付与〔某特性〕」但数据是独立函数（无对应文本）→ 找未用的 addState 特性函数
    if "特性" in segment:
        # 先认「本段点名的那个特性函数」——弹窗文本/buff 名/buff 说明里含〔〕内容的
        # （近藤勇·至诚 EX：文本「付与〔新选组〕特性」，函数 buff.detail 正是「付与〔新选组〕特性」）
        _brk = re.findall(r"〔([^〕]+)〕", segment)   # 文本里〔…〕的特征名
        _seg = segment.replace(" ", "")

        def _feat_named(f):
            if "addState" not in str(f.get("funcType", "")):
                return False
            for b in f.get("buffs", []):
                nm, dt = b.get("name") or "", b.get("detail") or ""
                if "特性" not in nm and "特性" not in dt:
                    continue
                if nm and nm in _seg:
                    return True
                if any(k and k in _seg for k in _brk):
                    return True
            return False

        i = find_by_type(_feat_named)
        if i is not None:
            return i
        i = find_by_type(lambda f: "addState" in str(f.get("funcType", ""))
                         and any("特性" in (b.get("name") or "") for b in f.get("buffs", [])))
        if i is not None:
            return i
    # 「解除」类文本在累加器的逐个「解除X状态」段里也常见，但对应函数常被前段占掉，
    # 这时整段没有可渲染的函数——它本来就是重复说明，允许匹配到任意未用函数以免误报未匹配。
    if "解除" in segment:
        # 只要还有未用函数就返回第一个；渲染层会因为「未点名」而只输出文本。
        for i in free:
            return i
    # 仅在段数少、函数多（说明有未写进 detail 的副效果）时才吸收，
    # 避免把真正没写进 detail 的独立效果吞掉。
    if len(free) > len([s for s in [segment]]):
        for i in free:
            buffs = funcs[i].get("buffs", [])
            if buffs and str(buffs[0].get("id", "")) in SECONDARY_BUFF_IDS:
                return i
    return None


def _absorb_silent(funcs, used):
    """把不需要单独占文本段的函数标记为已用（充能增加等）。"""
    for i, f in enumerate(funcs):
        if i not in used and f.get("funcType") in SILENT_FUNCTYPES:
            used.add(i)


def _pick_unique(seg, fns, idxs=None):
    """同一组候选函数里，按文本挑出唯一的那一个；无法区分则返回全部。

    用于「同值伴随函数」：文本只说「暴击星集中度提升」时，
    functions 里可能同时有 技/力/迅 三张卡各自的集星函数（数值完全相同）。
    只有文本能唯一指认时才吸收，否则宁可全部留着也不猜。
    """
    fns = list(fns)
    if len(fns) <= 1:
        return fns
    hit = [f for f in fns if (f.get("funcPopupText") or "") in seg]
    return hit if len(hit) == 1 else fns


def _lock_identical(fn, funcs, used, protected=()):
    """同值兄弟函数吸收。protected 里是本条文本显式点名/资源重定向到的函数，
    绝不能被顺手占掉，否则后一段会用同一函数再渲染一次，出现重复数值。"""
    cur = fn.get("funcType")
    if cur in ("gainStar", "gainNp", "gainHp", "lossHp", "lossHpSafe"):
        return
    vals = [v.get("Value") for v in fn.get("svals", [])]
    if not vals:
        return
    cands = [i for i in range(len(funcs))
             if i not in used and i not in protected
             and funcs[i].get("funcType") == cur
             and [v.get("Value") for v in funcs[i].get("svals", [])] == vals]
    if 1 < len(cands) <= 3:
        for i in cands:
            used.add(i)


def _absorb_carried(funcs, used):
    """吸收不单独成段的「附带函数」。

    典型：沙条爱歌「雅号·异星蛸」——文本写「技指令卡集星」，数据里躺着
    技/力/迅 三份同值函数；不吸收的话「获得暴击星」会错配到「暴击率提升:技」(15%)。
    也处理「攻击时追加效果」这种只有内部 id 作为数值的壳函数。
    """
    for i, f in enumerate(funcs):
        if i in used:
            continue
        ft = f.get("funcType")
        popup = f.get("funcPopupText") or ""
        vals = [v.get("Value") for v in f.get("svals", [])]
        # 壳函数：数值是内部状态 id（六位数），不是可用数值。
        # 但 popup 名有 4 字以上的（「攻击时追加效果」「毅力时发动」）是会被某段
        # 文本点名的真效果壳，不能预先吸收（但丁·七罪的刻印）。
        if vals and all(isinstance(v, (int, float)) and v >= 100000 for v in vals) \
                and len(re.sub(r"[^\u4e00-\u9fff]", "", popup)) < 4:
            names = " ".join(b.get("name") or "" for b in f.get("buffs", []))
            if "特性" not in popup and "特性" not in names:
                used.add(i)
                continue
        if ft not in ("addState", "addStateShort"):
            continue
        if not any(k in popup for k in ("集中", "威力", "耐性", "获得量")):
            continue
        # 已经在 used 里的同值兄弟 → 吸收剩余同值副本
        sib_vals = [v.get("Value") for v in f.get("svals", [])]
        alt_vals = None
        for j, o in enumerate(funcs):
            if j == i:
                continue
            ov = [v.get("Value") for v in o.get("svals", [])]
            if len(ov) >= 2 and ov[0] != ov[1]:
                alt_vals = ov
                break
        group = [j for j in range(len(funcs))
                 if j != i
                 and funcs[j].get("funcType") == ft
                 and [v.get("Value") for v in funcs[j].get("svals", [])] == sib_vals
                 and any(k in (funcs[j].get("funcPopupText") or "") for k in ("集中", "威力", "耐性", "获得量"))]
        # 只在「同值副本」场景下吸收：同组里存在另一个数值不同、且带卡色/特性前缀的兄弟
        # （雅号·异星蛸：技/力/迅 三份集星）。单条「暴击威力提升」这类没有同组兄弟，
        # 绝不能因为文本没提卡色就被吸收。
        card = CARD_KANJI_RE.search(f.get("funcPopupText") or "") or CARD_KANJI_RE.search(popup)
        if group and card and alt_vals:
            for j in group:
                used.add(j)
        # 同组但数值不同（真正的「另一张卡」副本）也一并吸收：
        # 文本只会为一个效果给一组数值，多出来的同名前缀函数属于未写明副本。
        # 只在「本函数就是被占用的那一份」时才扩展吸收同组：否则预处理阶段
        # 就会吃掉别段要用的副本（500200 亵渎审美「力攻击耐性降低」整段丢值）。
        if alt_vals and i in used:
            for j, o in enumerate(funcs):
                if j in used or j == i:
                    continue
                if o.get("funcType") != ft:
                    continue
                op = o.get("funcPopupText") or ""
                if not any(k in op for k in ("集中", "威力", "耐性", "获得量")):
                    continue
                if [v.get("Value") for v in o.get("svals", [])] != alt_vals:
                    continue
                used.add(j)


# 这些函数类型没有可读数值，渲染时跳过数值输出（只保留效果文本）
NO_VALUE_FUNCTYPES = {"subState"}

# detail 里表示指令卡色的用字（技/力/迅 → Arts/Buster/Quick）
CARD_KANJI_RE = re.compile(r"(技|力|迅)指令卡")


def format_skill_detail(sk, sk_icon=""):
    """Format skill: split detail -> match functions -> display values per segment."""
    cd = sk.get("coolDown", [])
    cd_str = f"充能时间：{format_cool_down(cd)}"
    sk_name = sk.get("name", "???")
    icon_md = f"![]({sk_icon})" if sk_icon else ""
    lines = [f"### {icon_md} {sk_name}    {cd_str}", ""]

    detail = sk.get("detail", "")
    if not detail:
        return "\n".join(lines)

    # Multi-form skill (e.g. 【第一、第二再临形象时】/【第三再临形象时】):
    # functions 数组只对应最后一个形态（游戏数据里存的是当前形态）。
    # 旧逻辑只渲染最后一段，导致前几段效果错配到别的函数上。
    # 新逻辑：按形态标记分段，逐段渲染——只有最后一段匹配 functions，
    # 前面的段落只输出文本（无函数映射，标注"数值见游戏内"）。
    form_sections = []   # [(marker, text)]
    positions = []
    mk = re.findall(r"【[^】]*(?:再临形象|阶段形象|灵基)[^】]*】", detail)
    if mk:
        # 按标记切段
        positions = [(m.start(), m.group(0)) for m in re.finditer(r"【[^】]*(?:再临形象|阶段形象|灵基)[^】]*】", detail)]
        # 有的 detail 前面还有【仅限…】之类的杂项标记，只认形态标记
        for i, (pos, marker) in enumerate(positions):
            start = pos + len(marker)
            end = positions[i + 1][0] if i + 1 < len(positions) else len(detail)
            form_sections.append((marker, detail[start:end].strip()))
    # 形态标记之前的通用说明（如果有）单独保留
    head = detail[:positions[0][0]].strip() if positions else ""
    if not form_sections:
        head = ""

    # Step 1: Split detail by ＆/＋
    # 双形态技能：只有最后一个形态有 functions 数据，前几段按纯文本渲染。
    if form_sections:
        if head:
            lines.append(head)
            lines.append("")
        used = set()

        def _both_forms(text):
            both = [p.strip() for p in re.split(r'[＆&＋+]', text) if p.strip()]
            return len(both) >= 2 and all("第" in x and ("形象" in x or "灵基" in x) for x in both)

        if len(form_sections) == 2 and _both_forms(form_sections[0][1]) and _both_forms(form_sections[1][1]):
            # 两个形态都写了完整效果 → functions 全给「前一形态」，后一形态只给文本（缺数值）
            a_marker, a_text = form_sections[0]
            b_marker, b_text = form_sections[1]
            lines.append(f"> {a_marker}")
            lines.append("")
            lines.extend(_render_skill_parts(a_text, sk, used))
            lines.append("")
            lines.append(f"> {b_marker}")
            lines.append("")
            segs = [p.strip() for p in re.split(r'[＆&＋+]', b_text) if p.strip()]
            for seg in segs:
                lines.append(seg)
                lines.append("")
            lines.append("> ⚠ 此形态的数值未包含在游戏数据中，以上为效果文本")
            return "\n".join(lines)

        for i, (marker, text) in enumerate(form_sections):
            is_last = (i == len(form_sections) - 1)
            lines.append(f"> {marker}")
            lines.append("")
            if is_last:
                # 最后一段走完整的函数匹配
                lines.extend(_render_skill_parts(text, sk))
            else:
                # 前几段：functions 里没有独立数据，用剩余函数做文本匹配
                lines.extend(_render_skill_parts(text, sk, used))
            lines.append("")
        return "\n".join(lines)

    # 单形态技能统一交给 _render_skill_parts：那里的拆段/同值吸收/特性 id 处理
    # 都已收口，这条旧分支（自带一套简化匹配）会产生不一致的输出。
    _body = _render_skill_parts(detail, sk, set())
    if not lines or lines[-1] != "":
        lines.append("")
    return "\n".join(lines + _body)

    parts = [p.strip() for p in re.split(r'[＆&＋]', detail) if p.strip()]  # noqa: unreachable
    funcs = sk.get("functions", [])
    used = set()

    for part in parts:
        fi = match_func_to_segment(part, funcs, used)
        if fi is None:
            # Multi-form: skip unmatched (other-form) segments silently
            lines.append(part)
            lines.append("—")
            lines.append("")
            continue

        used.add(fi)
        fn = funcs[fi]
        ft = fn.get("funcType", "")

        # Check for linked function (buff_calc has_link flag)
        skip_next = False
        next_fn = None
        has_link = False
        b = fn.get("buffs", [])
        if b:
            bid = str(b[0].get("id", ""))
            if bid in BUFF_CALC and BUFF_CALC[bid].get("has_link"):
                has_link = True
        if has_link and fi + 1 < len(funcs):
            skip_next = True
            next_fn = funcs[fi + 1]

        # Get values
        vals, is_fixed, formatter = get_func_values(fn, next_fn)
        
        # Skip if no displayable values (state refs)
        if not vals:
            lines.append(part)
            lines.append("")
            if skip_next and fi + 1 < len(funcs):
                used.add(fi + 1)
            continue

        # Show segment text
        lines.append(part)

        if ft in (NiceFuncType.delayNpturn,):
            lines.append(f"{int(vals[0])}")
        elif is_fixed:
            lines.append(f"{formatter(vals[0])}")
        else:
            cells = [formatter(v) for v in vals[:10]]
            lines.append("")
            lines.append("| Lv.1 | Lv.2 | Lv.3 | Lv.4 | Lv.5 | Lv.6 | Lv.7 | Lv.8 | Lv.9 | Lv.10 |")
            lines.append("|---|---|---|---|---|---|---|---|---|---|")
            lines.append("| " + " | ".join(cells) + " |")

        lines.append("")

        if skip_next and fi + 1 < len(funcs):
            used.add(fi + 1)

    return "\n".join(lines)


# 机制关键词：内部名常被缩写（迅提升/防御力下降），文本则写全称
# （迅指令卡性能提升/防御力逐渐降低）。匹配时靠它们判断「这段讲的是不是这件事」。
_MECH_KEYS = ("指令卡性能", "性能提升", "防御力", "攻击力", "宝具值", "暴击星", "暴击率",
              "生命值", "即死", "耐性", "威力", "集星", "获得量", "充能", "特攻", "无敌")



def _name_in_part(name: str, part: str) -> bool:
    """效果名能否在段文本里找到（容忍「的」「指令卡的」「度」这类连接字与修饰语）。

    例：「暴击星集中提升」 vs 「己方单体的技指令卡的暴击星集中度提升」。
    做法：逐字保留 name 里 >=2 字的连续块，要求它们按顺序出现在 part 中，
    且 part 里不得夹着 name 没有的「其他效果名」（由调用方的候选打分兜底）。
    """
    if not name:
        return False
    if name in part:
        return True
    # 文本里常插入「度」「的」「指令卡的」「率」等字（「暴击星集中提升」vs
    # 「暴击星集中度提升」），因此按「汉字子序列」判定：name 的字按顺序都能找到即可。
    pos = 0
    for ch in name:
        i = part.find(ch, pos)
        if i < 0:
            return False
        pos = i + 1
    return True


def _strip_card(s):
    """去掉内部名里的卡色/场地后缀（「暴击星集中提升：水边」→「暴击星集中提升」）。"""
    return re.sub(r"[：:][^：:]*$", "", (s or "")).strip()


def _split_wrapper_parts(parts):
    """把跨段的「付与「…(1回合)＆…(1回合)的状态」」合并回一段。

    游戏 detail 会把壳效果的内层描述也用 ＆ 切开，于是「付与「」没闭口、
    后半段又自带「」」收尾。逐段渲染会错位（后半段拿不到自己的数值），
    这里先做括号平衡：unclosed「」> 0 时把后续段接回来，直到闭合。
    """
    out = []
    buf = None
    for p in parts:
        if buf is not None:
            buf = buf + "＆" + p
            if buf.count("「") <= buf.count("」"):
                out.append(buf)
                buf = None
            continue
        if p.count("「") > p.count("」"):
            buf = p
            continue
        out.append(p)
    if buf is not None:
        out.append(buf)
    return out

def _render_skill_parts(text, sk, used=None):
    """把一段技能效果文本按 ＆/＋ 拆开，逐条匹配 functions 并渲染数值。
    used: 可选，跨段共享的已用函数索引集合（多形态渲染时避免误配）。"""
    # 注意：`＋`(U+FF0B) 是游戏里「另一条效果」的分隔符，`+`(ASCII) 只用于技能名/等级，
    # 历史上把两者一起当分隔符会把「A＋B＋C」粘成一段，导致后续整段数值错位。
    parts = [p.strip() for p in re.split(r'[＆&＋]', text) if p.strip()]
    parts = _split_wrapper_parts(parts)
    _single = len(parts) == 1
    funcs = sk.get("functions", [])
    if used is None:
        used = set()
    _absorb_silent(funcs, used)
    _absorb_carried(funcs, used)
    out = []
    # 一个效果文本段对应多个函数（如「〔新选组〕以外小幅增加」→ gainNp + 充能）
    _extra_pending = []
    # 同一技能内，本段没点名到的资源类函数（NP/暴击星等）留给下一段使用

    # 预扫描：找出与下一段文本对应的「跟随函数」（gainNp+充能、gainStar+暴击率）。
    # 这类函数紧跟在其主函数后面，detail 里不单独成段，必须跳过，
    # 否则会吞掉后一段效果对应的函数，造成数值整体错位。
    def _is_companion(prev_fn, cur_fn):
        if prev_fn is None:
            return False
        pf, cf = prev_fn.get("funcType"), cur_fn.get("funcType")
        if pf == "gainNp" and cf == "hastenNpturn":
            return True
        if pf == "gainStar" and cf in ("addState", "addStateShort"):
            ids = {str(b.get("id")) for b in cur_fn.get("buffs", [])}
            if ids & {"144", "145"}:
                return True
        return False

    _widxt = {id(p_): k for k, p_ in enumerate(parts)}   # 段对象 -> 真实下标（允许重复文本）
    _claimed = {}   # fi -> 首次认领它的文本段（用于「函数被前段顺手占掉」时的归还判断）
    for _pi, part in enumerate(parts):
        _head = len(out)   # 本段起始位置
        fi = match_func_to_segment(part, funcs, used)
        orig_fi = fi
        # 记录各段最终选中的函数：同值吸收不能把它们顺手占掉，否则后段会拿不到函数
        _picked_here = set()
        if fi is None:
            # 前面某段抢用了本该属于本段的函数时会走到这里。
            # 放开 used 限制只在「真被本段点名」的函数里找，绝不去抓完全没提到的
            # （近藤勇·至诚 EX：「小幅增加」段曾把特性函数抢走，后一段反而丢）。
            _free_fi = None
            _free_cand = [i for i, f in enumerate(funcs)
                          if i in used and _fn_named_in(f, part)]
            if _free_cand:
                _scored = match_func_to_segment(part, [funcs[i] for i in _free_cand], set())
                if _scored is not None:
                    _free_fi = _free_cand[_scored]
            if _free_fi is None:
                _scored = match_func_to_segment(part, funcs, set())
                if _scored is not None and _fn_named_in(funcs[_scored], part):
                    _free_fi = _scored
            if _free_fi is not None:
                fi = _free_fi
                # 这个函数本来是别的段「顺手占掉」的（那段文本并没点名它），
                # 现在本段真的点名了它 → 让本来属于本段，前段改为只输出文本。
                _prev_owner = _claimed.get(fi)
                _claimed[fi] = part
                if _prev_owner is not None and not _fn_named_in(funcs[fi], _prev_owner):
                    used.discard(fi)
        if fi is None:
            out.append(part)
            out.append("")
            continue

        # 选中了「跟随函数」时，真正的效果函数在它前一个位置
        # （如 NP增加 后紧跟 充能增加，获得暴击星 后紧跟 暴击率提升）
        if (_is_companion(funcs[fi - 1] if fi > 0 else None, funcs[fi])
                and fi - 1 >= 0 and (fi - 1) not in used):
            fi = fi - 1

        # 兜底：资源类文本（宝具值/暴击星/生命值/充能）若没落到对应的资源函数上，
        # 直接改判到该资源函数。（如「〔新选组〕以外宝具值增加」被「付与〔新选组〕特性」抢走）
        _RES_WORDS = (
            # 「宝具威力提升」是威力 buff，不是 NP 增加——别被「宝具」二字骗了
            (("宝具值",), ("增加", "提升", "上升"), "gainNp"),
            (("暴击星",), ("获得", "掉落", "大量"), "gainStar"),
            (("生命值", "HP"), ("回复", "恢复"), "gainHp"),
            (("充能",), ("减少", "增加"), "hastenNpturn"),
        )
        cur_ft = (funcs[fi].get("funcType") or "") if fi is not None else ""
        for w1, w2, want in _RES_WORDS:
            if not (any(w in part for w in w1) and any(w in part for w in w2)):
                continue
            if cur_ft == want:
                break
            # 「同值优先」只在当前选中函数与目标函数「文本相似」时才用：
            # 否则「获得暴击星」会被拉到同样 20 的「暴击率提升」上（苍穹的武练）。
            alt = [gi for gi in range(len(funcs))
                   if gi not in used and gi != fi and funcs[gi].get("funcType") == want]
            # 只在本段选中的函数确实属于目标类型时才做「同值优先」；
            # 否则「获得暴击星」会被拉到同值 20 的「暴击率提升」上（苍穹的武练）。
            if len(alt) > 1 and fi is not None and cur_ft == want:
                sig = [v.get("Value") for v in funcs[fi].get("svals", [])]
                same = [gi for gi in alt
                        if [v.get("Value") for v in funcs[gi].get("svals", [])] == sig]
                alt = same or alt
            if alt:
                fi = alt[0]
            break

        # 文本本身是「付与「…」的状态」这类壳效果（内层细节写在别处）：只出文本，
        # 不配任何数值 —— 数据里对应的只是一个包装函数（Kazuradrop 皮克西之指）
        if _is_wrapper_effect(part) and not re.search(r"\d", part):
            fi = None
            out.extend([part, ""])
            out.append("")
            continue

        # 特性函数：数值是内部特性 id，不能当百分比渲染（1000.9% 那种错）

        # 状态类文本（回避/必中/无敌…）若被错配到「有数值的同名邻近函数」，
        # 回退到真正的态函数：文本没写数值就不该输出数值表。
        if fi is not None and not re.search(r"\d", part):
            ft0 = funcs[fi].get("funcType")
            pop0 = funcs[fi].get("funcPopupText") or ""
            if ft0 in ("addState", "addStateShort") and any(
                    k in pop0 for k in ("威力", "数值", "耐性", "率")):
                for gi, gf in enumerate(funcs):
                    if gi in used or gi == fi:
                        continue
                    gp = gf.get("funcPopupText") or ""
                    if gp and gp in part and gf.get("funcType") in ("addState", "addStateShort"):
                        fi = gi
                        break

        # 候选分数打平时，优先文本里写明了卡色的那个函数
        if fi is not None:
            sig_val = [v.get("Value") for v in funcs[fi].get("svals", [])]
            ties = [i for i in range(len(funcs))
                    if i not in used
                    and funcs[i].get("funcType") == funcs[fi].get("funcType")
                    and [v.get("Value") for v in funcs[i].get("svals", [])] == sig_val]
            if len(ties) > 1:
                card = CARD_KANJI_RE.search(part)
                if card:
                    k = card.group(1)
                    hit = [i for i in ties if k in (funcs[i].get("funcPopupText") or "")]
                    if len(hit) == 1:
                        fi = hit[0]

        # 数值全等 + 含义不同 → 把数值相同的「伴随函数」一并占掉，
        # 防止文本里没写明的副函数被当成独立效果吸收。
        # （如 雅号·异星蛸：技/力/迅 三张卡各自的集星函数同值）
        # 本段显式选中的函数绝不能被「同值吸收」误占，否则后一段会重复用它。
        # 注意：控制流里已经没有「＋ 二次拆分」。`＋` 在 _render_skill_parts 入口
        # 就已被当作段分隔符切开（与 ＆ 同级），这里再拆只会重复渲染同一段。
        # 同值同名副本（技耐性下降 / 力耐性下降 都写「耐性降低」且数值全等）：
        # 本段点名了「力」，而前段点名的函数名里没有「力」→ 换到本段真正点名的那一份。
        # 否则后段会落到「前段占用→本段只出文本」的分支，整段丢数值表。
        _b0 = lambda t: re.sub(r"[^\u4e00-\u9fff]", "", t or "")
        _fpop0 = _b0(funcs[fi].get("funcPopupText") or "")
        _kw0 = (re.search(r"([技力迅])攻击", part) or re.search(r"([技力迅])指令卡", part)
                or re.search(r"^([技力迅])", _b0(part)) or [None, None])[1]
        if _kw0 is None:
            _kw0 = next((k for k in ("技", "力", "迅") if _b0(part).startswith(k)), None)
        if _kw0 and _fpop0 and _kw0 not in _fpop0:
            for gi in range(len(funcs)):
                _gp = _b0(funcs[gi].get("funcPopupText") or "")
                if gi != fi and gi not in _picked_here and _gp and _kw0 in _gp                         and funcs[gi].get("funcType") == funcs[fi].get("funcType") \
                        and _claimed.get(gi) is not None and not _fn_named_in(funcs[gi], _claimed[gi] or ""):
                    fi = gi
                    break

        used.add(fi)
        _claimed.setdefault(fi, part)
        fn = funcs[fi]
        # 本段文本真的点名了这个函数吗（名称/弹窗文本出现在段里）。
        # 没被点名 = 文本只描述了别的效果，这个函数是数据里附带的，
        # 不应把它的数值输出到这一段下面（曾导致「暴击威力提升」下冒出 10%）。
        _ptxt = ((fn.get("funcPopupText") or "")
                 + " " + " ".join((b.get("name") or "") for b in (fn.get("buffs") or [])))
        _ptxt = _ptxt.replace(" ", "")
        # 只认「长片段」命中：2~3 字的名字（提升/威力/技）到处都是，不能当点名依据。
        def _norm(s):
            return (s or "").replace(" ", "").replace(":", "").replace("：", "")
        _pnorm = _norm(part)

        def _best_hit(c):
            c = _norm(c)
            for L in range(len(c), 1, -1):
                for k in range(len(c) - L + 1):
                    if c[k:k + L] in _pnorm:
                        return L
            return 0

        def _sym(c):
            # 同义切分后的片段：「攻击力提升」≈「攻击力·提升」
            c = _norm(c)
            _KNOWN = ("攻击力", "防御力", "宝具值", "暴击星", "暴击率", "集星", "提升", "下降",
                      "降低", "增加", "减少", "威力", "性能", "耐性", "概率", "获取", "获得")
            frags, i = [], 0
            while i < len(c):
                for kw in _KNOWN:
                    if c.startswith(kw, i):
                        frags.append(kw)
                        i += len(kw)
                        break
                else:
                    i += 1
            return frags
        _best = max([_best_hit(fn.get("funcPopupText") or "")] +
                    [_best_hit(b.get("name") or "") for b in (fn.get("buffs") or [])] +
                    # 机制关键词（内部名很简略时，靠它判断「这段是不是在讲这件事」）
                    [_best_hit(k) for k in _MECH_KEYS if k in _norm(fn.get("funcPopupText") or "")
                     or any(k in (b.get("name") or "") for b in (fn.get("buffs") or []))] + [0])
        _best = max(_best, 99 if _fn_named_in(fn, part) else 0)
        _named = _best >= 4
        _sy = 0
        for _s in ([fn.get("funcPopupText") or ""] +
                   [b.get("name") or "" for b in (fn.get("buffs") or [])]):
            _fr = _sym(_s)
            if len(_fr) >= 2 and sum(1 for f in _fr if f in _pnorm) >= 2:
                _sy = 2
        _picked_here.add(fi)
        raw_vals = [v.get("Value") for v in fn.get("svals", [])]
        # 内部状态 id 函数（>=100000，如「每回合获得暴击星的：水边」3823=5）不是可展示效果，
        # 仅当本段点名时才渲染（且只出文本）；没点名就让给真正提到它的段。
        if raw_vals and all((v or 0) >= 100000 for v in raw_vals) and not _fn_named_in(fn, part):
            out.append(part)
            out.append("")
            continue
        # 只保护「还没用、且和本段同 funcType」的函数：跨类型的同值伙伴（如
        # 「自身宝具值增加 20%」＋「全体宝具值增加 10%」）本来就该由本段一起吃掉。
        _protect = {i for i in range(len(funcs))
                    if i not in used and funcs[i].get("funcType") == funcs[fi].get("funcType")}
        _protect.add(fi)

        # 「A提升(3回合)」这种标准效果句：即使 buff 名叫「宝具威力提升」而文本没写
        # 「宝具」二字，也算点名（否则藤堂平助·炮术义肢会整段丢数值）。
        _short_a = re.sub(r"[(（].*?[)）]", "", part).strip()
        _names = [fn.get("funcPopupText") or ""] + [b.get("name") or "" for b in (fn.get("buffs") or [])]
        if len(_short_a) >= 3:
            for _c in _names:
                if len(_c) >= 3 and _c in _short_a:
                    _named = True
                    break

        def _bare(t):
            # 去掉所有非文字内容（[(3回合)] ▲ 等），只留效果名
            return re.sub(r"[^\u4e00-\u9fff]", "", t or "")
        # 资源型函数（NP/星/HP）本身就是这段文本描述的东西，兜底匹配已经把它们
        # 精确指给了这一段；此时不要求名字逐字对上（「获得暴击星」vs「获得大量暴击星」）。
        # 「力指令卡的暴击星集中度提升」这种文案里带了「暴击星」但不是获得数量，
        # 不能因为关键词就认自己是 gainStar 段（戈耳工 · 巨怪蹂躏）。
        if fn.get("funcType") in ("gainStar", "gainNp", "gainHp") and any(
                k in part for k in ("暴击星", "宝具值", "生命值", "HP")) \
                and "集中" not in part and "掉落率" not in part and "每回合" not in part \
                and (fn.get("funcType") != "gainStar" or "获得" in part):
            _named = True
        _bare_part = _bare(part)
        if not _named and len(_bare_part) >= 3:
            # 「防御力降低」vs「防御力下降」：核心名词（防御力/攻击力/宝具值…）一致即算点名，
            # 提升/下降/降低 本来就可以换说法。
            _core_kw = next((k for k in ("防御力", "攻击力", "宝具值", "暴击星", "暴击率",
                                         "宝具威力", "暴击威力", "耐性", "掉落率", "集星",
                                         "宝具值获得", "宝具值获取", "生命值")
                             if k in _bare_part), None)
            if _core_kw and _core_kw in _bare(fn.get("funcPopupText") or ""):
                _named = True
        if _bare_part and _bare_part in {_bare(_c) for _c in _names if _c}:
            _named = True
        if not _named and len(_bare_part) >= 4:
            # 自然语言里的「防御力提升」 vs 内部名「强化(防御力提升)」：只要本段
            # 的纯文字片段被本函数的名字整段包含，就算点名。
            for _c in _names:
                _bc = _bare(_c)
                if len(_bc) >= 4 and _bare_part in _bc:
                    _named = True
                    break
        if not _named and len(_bare_part) >= 4 and not any(k in _bare_part for k in _MECH_KEYS):
            # 最后一条：这一句没有任何机制关键词，且本类型函数没有「数值不同的
            # 兄弟」——那就按相似度认下（藤堂平助·炮术义肢「攻击力提升」曾整段丢）。
            _same_ft_n = [i for i in range(len(funcs))
                          if i != fi and funcs[i].get("funcType") == fn.get("funcType")]
            if not any([v.get("Value") for v in funcs[i].get("svals", [])] != raw_vals
                       for i in _same_ft_n):
                _named = True
        # 同一 buff 出 multiple 副本（基础版 + 「：水边/：技」变体）时，本段该绑到
        # 弹窗名与文本完全一致的那个副本（凯妮斯「付与每回合获得暴击星的状态」
        # → 「每回合获得暴击星」而不是「每回合获得暴击星：水边」）。

        # 尚未处理到的段落会用到哪些函数还不知道：先把所有还没用的函数全保住，
        # 宁可少吸收，也不要把后段真正要用的函数抢掉（曾导致「暴击威力提升」
        # 被前一段的「特攻」按同值吸收吞成 30%）。
        # 精确弹窗名只被本段用到（「暴击星集中提升：水边」整句只出现在这一段），
        # 而本段选中了另一个函数 → 说明匹配把本段指错了，改指到精确命中的那个。
        # 例：凯妮斯「仅在〔水边〕场地上时,付与每回合获得暴击星」被「暴击星」抢到
        # 「每回合获得暴击星：水边」（内部状态 id 5），渲染成 0.5%。
        # 规则：完整弹窗名（带卡色/场地后缀）出现在本段 → 优先级最高。
        # 同名的「基础版」副本与「：水边」变体同时命中时，取名字最长的那个
        # （「暴击星集中提升：水边」胜过「每回合获得暴击星：水边」）。
        # 这一段匹配到的函数是否「真的在讲这一段」：完整弹窗名出现在文本里。
        # 不是的话（兜底匹配到的近似函数，如「获得暴击星」落到「暴击率提升」），
        # 允许被下面的精确命中覆盖。
        # 「获得暴击星」这类短名会被更长的「付与每回合获得暴击星的状态」包含，
        # 所以只保留「完整弹窗名」之外还要求它是该段的核心效果名（长度过滤）。
        # 精确命中：完整弹窗名出现在本段 → 绑定「顺序恰当」的副本。
        # 同名副本（「每回合获得暴击星」5/6 档与 10/20 档）在 detail 里也出现两次，
        # 文本完全一样，只能按上一次选中的下标往后取：第 2 次出现用第 2 个副本。
        # 只看「效果名本身」的匹配：去掉「仅在有…时,」限定前缀后再比，避免长前缀
        # 把 popup 名的占比压到阈值以下（苍穹的武练 第 3 段曾因此匹配失败）。
        _core_part = _strip_card(re.sub(r"^仅在有[^,，]*?场地上时[,，]?", "", part))
        # 「暴击星集中提升：技」同时含 card 名；「暴击威力提升：技」要求「暴击星」不出现，
        # 否则会把「技指令卡的暴击星集中度提升」也当成它。用「卡色后缀 + 主干」双向校验。
        # 方向必须一致：文本说「降低/下降」就只能绑「下降」类函数，反之亦然。
        # 否则「敌方全体暴击发生率降低」会落到「暴击发生率提升」（幻术 A+ 曾输出 10%＝上升档）。
        _dir_up = any(k in part for k in ("提升", "增加", "上升", "提高"))
        _dir_dn = any(k in part for k in ("降低", "下降", "减少", "削减"))
        def _dir_ok(_ff):
            _pv = (_ff.get("funcPopupText") or "") + " " + " ".join(
                b.get("name") or "" for b in (_ff.get("buffs") or []))
            if _dir_dn and not _dir_up:
                return any(k in _pv for k in ("下降", "降低", "减少", "削减"))
            if _dir_up and not _dir_dn:
                return not any(k in _pv for k in ("下降", "降低", "减少", "削减"))
            return True
        # 比较前先把「提升/下降/降低…」这些方向词和介词去掉，只比效果主体。
        def _noda(_s):
            _s = re.sub(r"[^\u4e00-\u9fff]", "", _s or "")
            for _k in ("提升", "提高", "增加", "上升", "降低", "下降", "减少", "削减",
                       "敌方", "己方", "自身", "全体", "单体", "状态", "付与", "对", "的", "率"):
                _s = _s.replace(_k, "")
            return _s
        # 方向校正：文本说「降低」而匹配到的函数是「提升」副本（或反之）→
        # 在本段真正点名的同 funcType 函数里换一个（幻术 A+ 敌方暴击发生率降低）。
        if fi is not None and not _dir_ok(funcs[fi]):
            _dir_cand = [i for i in range(len(funcs))
                         if i not in used and _dir_ok(funcs[i])
                         and _name_in_part(_noda(_strip_card(funcs[i].get("funcPopupText") or "")),
                                           _noda(part))]
            if _dir_cand:
                fi = _dir_cand[0]
                fn = funcs[fi]
                used.add(fi)
                _claimed.setdefault(fi, part)
        # 壳状态段（「…」的状态 / 引号里描述机制）：文本点名了哪个函数就用哪个。
        # 数据里常有 7 份同名的〔罪之刻印〕副本，谁先出现谁被抢（但丁·七罪的刻印
        # 段 3「毅力发动时…」曾绑到第 3 份刻印输出 10%）。
        if re.search(r"「[^」]*攻击时[^」]*」", part):
            # 「付与「技攻击时…的状态」」是间接机制的壳：真实数值由触发时的效果决定，
            # 数据里只有内部状态 id。整段只输出文本，不配表（征氏姐妹·姊妹牵绊）。
            out.extend([part, ""])
            continue
        # 只有「引号壳」段（内含「」的机制描述）才算；「1回合后付与自身宝具威力提升的状态」
        # 这种普通句不能走这条分支（会把 20% 的表吞掉）。
        if part.startswith("「") or ("「" in part and "」" in part and (
                "的状态" in part[-12:] or part.rstrip(")）").endswith("的状态"))):
            _quoted = "".join(re.findall(r"「([^」]*)」", part))
            def _q_hit(_i):
                _nm = _strip_card(funcs[_i].get("funcPopupText") or "")
                if not _nm:
                    return False
                if _name_in_part(_nm, part):
                    return True
                if _nm in _quoted:
                    return True
                # 「毅力时发动」vs 引号里的「毅力发动时」：乱序子集也算
                return len(_nm) >= 4 and all(ch in _quoted for ch in _nm)
            _named_hit = [i for i, f in enumerate(funcs) if i not in used and _q_hit(i)]
            # 机制壳段的关键词直绑：「攻击时…」→「攻击时追加效果」，「毅力…」→「毅力时发动」
            for _kw, _pn in (("攻击时", "攻击时追加效果"), ("毅力", "毅力时发动"),
                             ("宝具使用", "过量充能阶级提升"), ("每回合", "每回合")):
                if _kw in _quoted:
                    for _i2, _f2 in enumerate(funcs):
                        _n2 = _strip_card(_f2.get("funcPopupText") or "")
                        if _i2 not in used and _n2 and _pn in _n2:
                            _named_hit.insert(0, _i2)
                            break
            # 同组里优先「名字更长」的（「攻击时追加效果」「毅力时发动」胜过
            # 到处都能子序列命中的短名「罪之刻印」），长度相同才按顺序取。
            def _kw_rank(_i):
                _n = _strip_card(funcs[_i].get("funcPopupText") or "")
                for _pn in ("攻击时追加效果", "毅力时发动", "过量充能阶级提升",
                            "每回合获得暴击星", "每回合回复生命值", "每回合获取宝具值"):
                    if _n == _pn and _pn[:2] in _quoted:
                        return 0
                return 1
            _kw_first = sorted([i for i in _named_hit if _kw_rank(i) == 0])
            _named_hit = _kw_first + [i for i in _named_hit if i not in _kw_first]
            _named_hit.sort(key=lambda i: (-len(_strip_card(funcs[i].get("funcPopupText") or "")), i))
            if _named_hit and (fi is None or fi not in _named_hit[:1]):
                fi = _named_hit[0]
                fn = funcs[fi]
                used.add(fi)
                _claimed.setdefault(fi, part)
            _wrap_stage = bool(_named_hit)
        else:
            _wrap_stage = False
        _pe = [] if _wrap_stage else [i for i, f in enumerate(funcs)
               if _dir_ok(f)
               and (f.get("funcPopupText") or "")
               # 「暴击威力提升：技」这种带卡色后缀的 popup 在文本里是拆开写的
               # （「技指令卡的暴击威力提升」），所以按「主干 + 卡色」拆开校验：
               # 主干必须整段出现在效应名里，卡色字也得在句子里。
               and _name_in_part(_strip_card(f.get("funcPopupText")), _core_part)]

        if _pe:
            _pe.sort(key=lambda i: i)
            # 同名副本按 detail 出现顺序一一对应：文本里第 n 次出现用第 n 个未占用副本。
            # 「仅在有〔水边〕…时,」是限定前缀，视为同一效果的再次出现。
            def _sig(s):
                return _strip_card(re.sub(r"^仅在有[^,，]*[的]?场地上时[,，]?", "", s or ""))
            _occ = sum(1 for p_ in parts[:_pi] if _sig(p_) == _sig(part))
            # 数据顺序 = detail 顺序：优先取「排在当前匹配之后」的副本，其次取最早的
            # 只在「名字完全对得上」的候选里选；同长/同名的副本按出现次序取。
            fi = _pe[min(_occ, len(_pe) - 1)]
            fn = funcs[fi]
            # 精确命中覆盖了兜底匹配的结果：把旧函数从 used 里放回去，否则后面的段
            # 会以为它被占了而失去候选（女神变生 段 2 曾因此拿不到 50%）。
            if orig_fi is not None and orig_fi != fi:
                used.discard(orig_fi)
                if _claimed.get(orig_fi) == part:
                    _claimed.pop(orig_fi, None)
                _picked_here.discard(orig_fi)
            used.add(fi)
            _claimed.setdefault(fi, part)

        # 资源硬规则：「获得暴击星」类句子只能绑 gainStar；
        # 「暴击星集中度提升」不是获得数量，不能绑 gainStar（由 _RES_WORDS 已正确区分）。
        if "暴击星" in part and "集中" not in part and "掉落率" not in part \
                and ("获得" in part or "大量" in part):
            _gs = [i for i in range(len(funcs))
                   if funcs[i].get("funcType") == "gainStar" and i not in used]
            if _gs:
                fi = _gs[0]
                fn = funcs[fi]
                used.add(fi)
                _claimed.setdefault(fi, part)

        # 资源硬规则 2：「宝具值增加/提升」类句子只能绑 gainNp（不是 gainNp 的
        # addStateShort 伴随 buff 会输出成百分比，灾星简「己方全体宝具值小幅增加」曾出 10%）。
        if "宝具值" in part and ("增加" in part or "提升" in part) \
                and not any(k in part for k in ("获得量", "获取", "每回合", "减少")):
            _gnp = [i for i in range(len(funcs))
                    if funcs[i].get("funcType") == "gainNp" and i not in used]
            if _gnp and (fi is None or (funcs[fi].get("funcType") or "") != "gainNp"):
                fi = _gnp[0]
                fn = funcs[fi]
                used.add(fi)
                _claimed.setdefault(fi, part)

        # 名不对就不出数：本段匹配到的函数 popup 名与本段核心名毫不相干时，
        # 改指到「名字里含本段关键词」的未占用函数（斯卡哈·斯卡蒂 原初之卢恩：
        # 「迅指令卡暴击威力提升」曾绑到「迅提升」，输出 30% 而不是 50%）。
        if fi is not None:
            _lb = _bare(part)
            _fpop = _bare(fn.get("funcPopupText") or "")
            # 只在「效果主体」句里判（壳状态段「…」的状态 里的机制描述不算）
            _wan = [] if _wrap_stage else [k for k in ("暴击威力", "暴击星集中", "宝具威力", "攻击力", "防御力",
                                "暴击率", "掉落率", "宝具值") if k in _lb]
            if _wan and not any(k in _fpop for k in _wan):

                _cand = [i for i in range(len(funcs))
                         if i not in used and any(
                             k in _bare(funcs[i].get("funcPopupText") or "") for k in _wan)]
                if _cand:
                    fi = _cand[0]
                    fn = funcs[fi]
                    used.add(fi)
                    _claimed.setdefault(fi, part)
                else:
                    _sc = match_func_to_segment(part, funcs, set())
                    if _sc is not None:
                        # 全表重匹配（允许已占用的函数）——本段名字对得上就该用它，
                        # 哪怕前面某段已经把它占走了（夏夜黑寡妇「防御力降低」曾整段丢数值）。
                        fi = _sc
                        fn = funcs[fi]
                        used.add(fi)
                        _claimed.setdefault(fi, part)

        # 兜底：本段匹配到了「文本里没提过的函号」（前缀误判），但另外还有个
        # 名字完全对得上的未占用函数 → 用它（梅柳齐娜「场地版每回合获得暴击星」）。
        if fi is not None and (fn.get("funcPopupText") or "") not in part and not _wrap_stage:
            _alt = [i for i, f in enumerate(funcs)
                    if i not in used and i != fi
                    and (f.get("funcPopupText") or "")
                    and (f.get("funcPopupText") or "") in part
                    and len(f.get("funcPopupText") or "") >= 4]
            if _alt:
                _alt.sort(key=lambda i: (-len(funcs[i].get("funcPopupText") or ""), i))
                fi = _alt[0]
                fn = funcs[fi]
        # 「后续段落的文本里点到名的函数」一律保护：
        # 段 0「技指令卡的暴击星集中度提升」曾按同值吸收掉段 1 要用的
        # 「暴击威力提升：技」（30% → 应为 50%）。
        _rest_text = "".join(parts[_pi + 1:])
        _protect |= {i for i, f in enumerate(funcs)
                     if i not in used and (f.get("funcPopupText") or "")
                     and (_strip_card(f.get("funcPopupText")) in _rest_text
                          or (f.get("funcPopupText") or "") in _rest_text)}
        # 「还在本段之后、且被后面某段点名」的函数可能已经被本段在前面抢进 used，
        # 也应该保护（500200 亵渎审美「力攻击耐性降低」曾被段 0 的误判抢走 func2）。
        _protect |= {i for i in range(len(funcs)) if i not in used}
        # 不再做「同值副本吸收」：多段技能的副本靠 _pe 顺序绑定即可，
        # 提前吸收只会让后面的段丢函数（女神变生：暴击威力提升拿到 30% 而非 50%）。
        _lock_identical(fn, funcs, used, protected=set(range(len(funcs))))
        raw_vals = [v.get("Value") for v in fn.get("svals", [])]
        ft = fn.get("funcType", "")
        # 同值「伴随函数」：文本只点名一种卡色，其余卡色的同值副本静默吸收。
        # 例：雅号·异星蛸 文本写「技指令卡集星」，数据里有 技/力/迅 三份同值函数，
        # 不吸收的话下一段「获得暴击星」会错配到「暴击率提升:技」(15%)。
        # 但只在「同组里另有数值不同的兄弟」时才吸收：真正的独立效果（近藤勇的
        # 「付与〔新选组〕特性」，全表同值）不能因为数值相同就被吞掉。
        # 特性类 addState 的数值是内部特性 id，本段只输出文本、不输出数值。
        _is_feature_fn = bool(
            (ft in ("addState", "addStateShort")
             and any("特性" in (b.get("name") or "") + (b.get("detail") or "")
                     for b in (fn.get("buffs") or [])))
            # 内部状态 id（96xxxx 之类）：只对「壳函数」成立。buff 名能在文本里
            # 点名时（如〔强食〕〔献给世界树的活祭〕），它是真效果，文本也没写数值——
            # 但表头必须照样输出，否则说明行后面空一片。
            or (raw_vals and all(isinstance(v, (int, float)) and v >= 100000 for v in raw_vals)))
        if ft in ("addState", "addStateShort") and ft not in NO_VALUE_FUNCTYPES and not _is_feature_fn:
            popup = fn.get("funcPopupText") or ""
            _same_ft = [i for i in range(len(funcs)) if i != fi and funcs[i].get("funcType") == ft]
            # 同组必须存在「数值不同的兄弟」才说明本组是多卡/多目标副本集合
            _has_sibling_diff = any(
                [v.get("Value") for v in funcs[i].get("svals", [])] != raw_vals for i in _same_ft)
            # 「暴击星集中提升:技」这类多卡副本：本段点名了卡色（技/力/迅）或点名了
            # 副本里的「暴击率」时，同值但卡色不同的副本属于同一效果的另一形态，
            # 可一并吸收（否则下一段「获得暴击星」会错配到 15%）。
            _card_hit = bool(CARD_KANJI_RE.search(part)) or "暴击率" in part
            if (_has_sibling_diff and _card_hit and len(parts) <= 1
                    and any(k in popup for k in ("集中", "威力", "耐性", "获得量", "提升"))):
                # 只在「还没被本技能任何段落点名」的候选里找副本：文本里出现了该
                # 副本的弹窗名（凯妮斯「仅在〔水边〕场地上时,付与每回合获得暴击星」）
                # 说明它自己有段落，不能被本段吞掉（否则那段会拿到 0.5% 的错表）。
                _all_text = "＆".join(parts)
                for i in range(len(funcs)):
                    if i in used or i == fi:
                        continue
                    o = funcs[i]
                    if o.get("funcType") != ft:
                        continue
                    # 资源函数（获得暴击星/NP）绝不能被当副本吸收：它有文本要渲染
                    if ft in ("gainStar", "gainNp", "gainHp"):
                        continue
                    if [v.get("Value") for v in o.get("svals", [])] != raw_vals:
                        continue
                    _op = o.get("funcPopupText") or ""
                    if _op and _strip_card(_op) and _strip_card(_op) in _all_text:
                        continue
                    # 候选的完整弹窗名（「每回合获得暴击星：水边」）出现在全文任意段
                    # → 它有自己的段落，不能被本段吸收（否则那段拿不到数值）。
                    if _op and _op in _all_text:
                        continue
                    # 只吸收「文本里完全没提到」的副本；它的名字出现在任何一段里
                    # 就说明那一段会用它，必须留给那一段（女神变生：段 0 曾吞掉
                    # 段 1 的「暴击威力提升：技」，导致输出 30% 而不是 50%）。
                    if _op and any(_op in p_ or _strip_card(_op) in p_ for p_ in parts):
                        continue
                    used.add(i)

        # 整段是一个文段（含 ＋ 连接的多条效果）时，把「未被任何文本提到」的函数
        # 一并占掉：这些是数据里有、文本里没写明的附带函数。
        # 逐个处理（不带 ＋）时不做，避免把下一段要用的函数吞掉。
        # （已移除：单段时静默吸收「未被提到的函数」。它假设技能里只剩一段文本，
        #   实际多段技能的每一段都会被单独渲染，吸收会吞掉后一段要用的函数，
        #   造成数值整段消失或张冠李戴 —— 梅柳齐娜「场地版每回合获得暴击星」。）

        skip_next = False
        next_fn = None
        b = fn.get("buffs", [])
        if b:
            bid = str(b[0].get("id", ""))
            if bid in BUFF_CALC and BUFF_CALC[bid].get("has_link"):
                skip_next = True
        if skip_next and fi + 1 < len(funcs):
            next_fn = funcs[fi + 1]

        hv = fn.get("svals", [])
        has_val = any(v.get("Value") for v in hv) if hv else False
        # 特性/内部状态 id 作为数值的函数：文本已写明效果名，数值无意义
        if _is_feature_fn:
            # 特性 id 段：文本就是全部信息，不出数值表
            vals, is_fixed, formatter = [], True, lambda v: ""
        else:
            vals, is_fixed, formatter = get_func_values(fn, next_fn)
        if ft in ("lossHpSafe", "lossHp") and has_val:
            # 自伤：数值就是绝对值（HP 点数），不能按百分比换算
            vals = [int(v.get("Value", 0)) for v in hv]
            is_fixed = False if len(set(vals)) > 1 else True
            formatter = lambda v: str(int(v))

        # 只有「充能增减」按次数显示整数；HP 变动是点数，必须保留原值
        # 数值应当紧贴其说明文字，不允许多余空行把两者拆开
        _chunk = [part, ""]
        if _is_feature_fn or (not _named and not (ft == "gainStar" and "获得" in part)):
            # 特性/内部 id 段：文本就是全部信息；未被点名的附带函数：数值不属于这段
            pass
        elif not vals or ft in NO_VALUE_FUNCTYPES:
            pass
        elif ft == "addState" and "目标集中" in _bare_part and "提升" not in part:
            # 「付与己方单体目标集中状态(1回合)」：文本只有持续回合，没有数值描述
            pass
        elif ft in ("addState", "addStateShort") and vals and (
                any(k in (fn.get("funcPopupText") or "") + " ".join(
                    b.get("name") or "" for b in (fn.get("buffs") or []))
                    for k in ("毅力", "回避", "无敌", "必中"))) \
                and all(isinstance(v, (int, float)) and v <= 10 for v in vals) and _named \
                and not any(isinstance(v, (int, float)) and v >= 100000
                            for v in [x.get("Value") for x in fn.get("svals", [])]):
            # 次数类数值（毅力 1 次 / 回避 2 次）不是百分比。文本里已经写了
            # 「(1次)」就不再重复输出；文本没写次数时才补「N次」。
            if not re.search(r"[（(][^）)]*\d\s*次", part):
                out.append(f"{int(vals[0])}次" if len(set(vals)) == 1
                           else "/".join(str(int(v)) for v in vals) + "次")
                out.append("")
        elif ft == "gainStar" and vals and "获得" in part and "集中" not in part \
                and not any(k in part for k in ("毅力", "罪之刻印")):
            # 暴击星是「颗数」，按整数点数显示，不套百分比刻度
            _chunk += [(str(int(vals[0])) if is_fixed else "| " + " | ".join(str(int(v)) for v in vals[:10]) + " |"), "", ""]
            if not is_fixed:
                _chunk = [part, "", "| Lv.1 | Lv.2 | Lv.3 | Lv.4 | Lv.5 | Lv.6 | Lv.7 | Lv.8 | Lv.9 | Lv.10 |",
                          "|---|---|---|---|---|---|---|---|---|---|",
                          "| " + " | ".join(str(int(v)) for v in vals[:10]) + " |", ""]

            # 「付与每回合获得暴击星的状态(3回合)」这类壳状态：数值是内部状态 id 或
            # 后面单独那段的产出量，不属于这一行（苍穹的武练曾在此冒出孤立「20」）。
            pass
        elif ft in ("addState", "addStateShort", "gainStar") and not re.search(r"\d", part) \
                and not any(k in part for k in ("提升", "提高", "增加", "上升", "下降", "降低", "获得", "大量", "威力")) \
                and len(_bare_part) >= 5:
            # 文本既没写数值也没写「提升/降低/获得」，这个 buff 的数值不属于这段
            # （「付与自身目标集中状态(1回合)」曾被塞进 300%）。
            # 短词（「暴击威力提升」这类无变化表述）仍需保留数值。
            pass
        elif ft in ("addState", "addStateShort") and "特性" in part:
            # 「付与令场地获得〔阳光照射〕特性的状态」「一定概率付与场地〔森林〕特性」：
            # 数值是场地/特性内部 id 或概率常数（2038 → 203.8%、2073 → 207.3%），
            # 不是玩家可见的百分比 → 只出文本。
            pass
        elif ft in ("shortenSkill", "shortenSkillPT"):
            # 「技能冷却减少1回合」：数字已在文本里（1回合），数值是内部时长，不渲染
            pass
        elif ft in ("lossHp", "lossHpSafe") and vals and not re.search(r"\d", part):
            # 生命值消耗是点数（Value=500/3000），不是百分比 → 「500 HP」。
            # 文本已经写了具体数字（「生命值减少500」）时不重复输出。
            if is_fixed:
                _chunk += [f"{int(vals[0])} HP", "", ""]
            else:
                _chunk = [part, "", "| Lv.1 | Lv.2 | Lv.3 | Lv.4 | Lv.5 | Lv.6 | Lv.7 | Lv.8 | Lv.9 | Lv.10 |",
                          "|---|---|---|---|---|---|---|---|---|---|",
                          "| " + " | ".join(f"{int(v)} HP" for v in vals[:10]) + " |", ""]
        elif any(k in _bare_part for k in ("灼伤", "中毒", "诅咒")) and vals \
                and ft in ("addState", "addStateShort") \
                and not any(k in part for k in ("特攻", "特防")) \
                and any(k in part for k in ("付与", "状态")):
            # 灼伤/中毒/诅咒 的数值是每回合固定伤害点数（Value=300 → 300），不是百分比
            # get_func_values 已按 divisor(10) 除过（500→50）；灼伤伤害点数是原值，
            # 复原 ×10（50→500）。文本里已写清数值的段不需要这张表。
            _dm = [v * 10 for v in vals]
            if is_fixed:
                _chunk += [f"{int(_dm[0])}", "", ""]
            else:
                _chunk = [part, "", "| Lv.1 | Lv.2 | Lv.3 | Lv.4 | Lv.5 | Lv.6 | Lv.7 | Lv.8 | Lv.9 | Lv.10 |",
                          "|---|---|---|---|---|---|---|---|---|---|",
                          "| " + " | ".join(str(int(v)) for v in _dm[:10]) + " |", ""]
        elif ft == "gainHp" and vals and ("生命值" in _bare_part or "HP" in part) \
                and ("回复" in _bare_part or "恢复" in _bare_part or "減少" in _bare_part):
            # 生命值回复是点数（Value=1000/2500），不是百分比。
            # get_func_values 已按 divisor(10) 除过，这里 ×10 复原成真实点数。
            _hp = [v * 10 for v in vals]
            if is_fixed:
                _chunk += [str(int(_hp[0])), "", ""]
            else:
                _chunk = [part, "", "| Lv.1 | Lv.2 | Lv.3 | Lv.4 | Lv.5 | Lv.6 | Lv.7 | Lv.8 | Lv.9 | Lv.10 |",
                          "|---|---|---|---|---|---|---|---|---|---|",
                          "| " + " | ".join(str(int(v)) for v in _hp[:10]) + " |", ""]
        elif ft in (NiceFuncType.delayNpturn, NiceFuncType.hastenNpturn) and vals:
            if re.search(r"[\d一二三四五六七八九十]", part):
                _chunk += [f"{vals[0]}", "", ""]
            # 文本没写数字（「敌方全体的充能减少」）→ 只出文本，不出孤零零的「1」
        elif is_fixed:
            _chunk += [f"{formatter(vals[0])}", "", ""]
        else:
            cells = [formatter(v) for v in vals[:10]]
            _chunk = [part, "", "| Lv.1 | Lv.2 | Lv.3 | Lv.4 | Lv.5 | Lv.6 | Lv.7 | Lv.8 | Lv.9 | Lv.10 |",
                       "|---|---|---|---|---|---|---|---|---|---|",
                       "| " + " | ".join(cells) + " |", ""]
        while _chunk and _chunk[-1] == "":
            _chunk.pop()
        out.extend(_chunk)
        out.append("")

        if skip_next and fi + 1 < len(funcs):
            used.add(fi + 1)

    return out


def format_np_new(np_data, is_current=False):
    """New NP formatting: split effects by &/+, map by funcId, handle 特攻."""
    lines = []
    np_name = np_data.get("name", "???")
    np_rank = np_data.get("rank", "")
    np_card_num = str(np_data.get("card", ""))
    np_card = CARD_MAP.get(np_card_num, np_card_num)
    np_type = np_data.get("type", "")
    np_icon = np_data.get("icon", "")

    icon_md = f"![]({np_icon}) " if np_icon else ""
    lines.append(f"### {icon_md}{np_name}")
    lines.append("")
    lines.append("| 属性 | 值 |")
    lines.append("|------|-----|")
    lines.append(f"| 等级 | {np_rank} |")
    lines.append(f"| 卡色 | {np_card} |")
    lines.append(f"| 类型 | {np_type} |")
    lines.append("")

    detail = np_data.get("detail", "")
    fns = np_data.get("functions", [])

    # Step 1: Split effects by ＆ and ＋, clean ▲
    raw_parts = re.split(r"[＆＋]", detail)
    raw_parts = [p.strip() for p in raw_parts if p.strip()]
    effects_clean = [p.replace("▲", "").strip() for p in raw_parts]

    # Step 2: Check for 特攻 in any effect
    tokou_target = ""
    tokou_effect_idx = -1
    for ej, e in enumerate(effects_clean):
        m = re.search(r"〔(.+?)〕特攻", e)
        if m:
            tokou_target = m.group(1)
            tokou_effect_idx = ej
            effects_clean[ej] = e.replace(f"〔{tokou_target}〕特攻", "").strip()

    # Step 3: Render each function → corresponding effect
    for fi, fn in enumerate(fns):
        ft = fn.get("funcType", "")
        if ft in SKIP_FUNCTYPES:
            continue
        svals = fn.get("svals", [])
        buffs = fn.get("buffs", [])
        buff_name = buffs[0].get("name", "") if buffs else ""
        buff_det = buffs[0].get("detail", "") if buffs else ""

        vals = [s.get("Value") for s in svals]
        numeric = [v for v in vals if v is not None and isinstance(v, (int, float))]
        formatted = [format_val(v, ft) for v in numeric]
        formatted = [f for f in formatted if f is not None]

        # Rate values (probability-based effects)
        rates = [s.get("Rate") for s in svals]
        rate_first = rates[0] if rates else None

        # OC detection — handles Value, Correction, and Rate
        oc_values, oc_mode = get_oc_values(fn, ft)
        has_oc = oc_mode not in ("none", "fixed") and len(oc_values) >= 5

        eff_desc = effects_clean[fi] if fi < len(effects_clean) else (buff_name or buff_det or ft)
        # Strip OC tag from base damage description (it belongs to the OC row)
        eff_desc = re.sub(r"<过量充能时特攻威力提升>", "", eff_desc).strip()
        is_damage = ft in ("damageNp", "damageNpIndividual", "damageNpPierce", "damageNpIndividualSum")
        handle_tokou = (tokou_target and is_damage and fi == tokou_effect_idx)

        if handle_tokou:
            # Split: Base attack
            lines.append(f"**{eff_desc}** <宝具升级效果提升>")
            lines.append("")
            if formatted:
                cells = formatted[:5]
                while len(cells) < 5: cells.append("—")
                lines.append("| Lv.1 | Lv.2 | Lv.3 | Lv.4 | Lv.5 |")
                lines.append("|---|---|---|---|---|")
                lines.append("| " + " | ".join(cells) + " |")
                lines.append("")
            # Split: 特攻
            if has_oc:
                lines.append(f"**对〔{tokou_target}〕特攻<Over Charge时特攻威力提升>**")
            else:
                lines.append(f"**对〔{tokou_target}〕特攻**")
            lines.append("")
            if has_oc:
                oc_cells = oc_values[:5]
                while len(oc_cells) < 5: oc_cells.append("—")
                lines.append("| OC1 | OC2 | OC3 | OC4 | OC5 |")
                lines.append("|---|---|---|---|---|")
                lines.append("| " + " | ".join(oc_cells) + " |")
            elif oc_values:
                lines.append(f"固定值: {oc_values[0]}")
            else:
                lines.append("固定值: —")
            lines.append("")

        elif is_damage:
            lines.append(f"**{eff_desc}** <宝具升级效果提升>")
            lines.append("")
            if formatted:
                cells = formatted[:5]
                while len(cells) < 5: cells.append("—")
                lines.append("| Lv.1 | Lv.2 | Lv.3 | Lv.4 | Lv.5 |")
                lines.append("|---|---|---|---|---|")
                lines.append("| " + " | ".join(cells) + " |")
                lines.append("")
            if has_oc:
                oc_cells = oc_values[:5]
                while len(oc_cells) < 5: oc_cells.append("—")
                lines.append("<过量充能时效果提升>")
                lines.append("")
                lines.append("| OC1 | OC2 | OC3 | OC4 | OC5 |")
                lines.append("|---|---|---|---|---|")
                lines.append("| " + " | ".join(oc_cells) + " |")
                lines.append("")

        else:
            # Non-damage effect (buff, state, probability)
            oc_tag_raw = ""
            if "过量充能" in eff_desc or "Over Charge" in eff_desc:
                oc_label = re.search(r"<(.+?)>", eff_desc)
                oc_tag_raw = f"<{oc_label.group(1)}>" if oc_label else ""
                clean_desc = re.sub(r"<.+?>", "", eff_desc).strip()
                lines.append(f"**{clean_desc}** {oc_tag_raw}")
            else:
                lines.append(f"**{eff_desc}**")
            lines.append("")

            if has_oc:
                oc_cells = oc_values[:5]
                while len(oc_cells) < 5: oc_cells.append("—")
                lines.append("| OC1 | OC2 | OC3 | OC4 | OC5 |")
                lines.append("|---|---|---|---|---|")
                lines.append("| " + " | ".join(oc_cells) + " |")
                lines.append("")
            elif formatted and len(set(formatted)) > 1:
                cells = formatted[:5]
                while len(cells) < 5: cells.append("—")
                lines.append("| Lv.1 | Lv.2 | Lv.3 | Lv.4 | Lv.5 |")
                lines.append("|---|---|---|---|---|")
                lines.append("| " + " | ".join(cells) + " |")
                lines.append("")
            elif formatted:
                lines.append(f"固定值: {formatted[0]}")
                lines.append("")
            elif rate_first:
                rate_pct = rate_first / 10
                rate_str = f"{int(rate_pct)}%" if rate_pct == int(rate_pct) else f"{rate_pct:.1f}%"
                lines.append(f"概率: {rate_str}")
                lines.append("")
            else:
                lines.append("固定效果")
                lines.append("")

    return "\n".join(lines)


def mat_table(title, mats_dict, format_key=None, offset=0, show_total=True):
    """Generate material tables with ID, icon, name, quantity per row + total summary."""
    lines = [f"### {title}", ""]
    total_qp = 0
    total_items = {}  # id -> {name, icon, amount}

    # Data rows
    data_lines = []
    for k in sorted(mats_dict, key=int):
        md = mats_dict[k]
        qp = md.get("qp", 0)
        total_qp += qp
        items = md.get("items", [])
        if format_key:
            label = format_key(int(k))
        else:
            label = f"Lv.{int(k) + offset} → Lv.{int(k) + offset + 1}"

        if not items:
            data_lines.append(f"| {label} | {qp:,} | — | — | — | — |")
            continue

        for idx, it in enumerate(items):
            item_id = it.get('item', {}).get('id', 0)
            amount = it.get('amount', 0)
            # Look up name from items DB; construct icon URL from ID directly
            item_info = ITEMS_MAP.get(item_id, {})
            item_name = item_info.get("name", it.get('item', {}).get('name', '?'))
            if item_id in JP_ITEM_IDS and item_id not in ITEMS_MAP:
                item_icon = f"https://static.atlasacademy.io/JP/Items/{item_id}.png"
            else:
                item_icon = f"https://static.atlasacademy.io/CN/Items/{item_id}.png"
            icon_md = f"![]({item_icon})"

            # Accumulate total
            if item_id not in total_items:
                total_items[item_id] = {
                    "name": item_name,
                    "icon": icon_md,
                    "amount": 0,
                }
            total_items[item_id]["amount"] += amount

            stage_label = label if idx == 0 else ""
            data_lines.append(f"| {stage_label} | {qp if idx == 0 else ''} | {item_id} | {icon_md} | {item_name} | {amount} |")

    # Render data table
    if data_lines:
        lines.append("| 阶段 | QP | ID | 图标 | 道具名称 | 数量 |")
        lines.append("|------|-----|----|------|----------|------|")
        for dl in data_lines:
            lines.append(dl)
        lines.append("")

    # Separate total summary table
    if show_total and total_items:
        lines.append("**总计**")
        lines.append("")
        lines.append("| ID | 图标 | 道具名称 | 总数 |")
        lines.append("|----|------|----------|------|")
        for tid in sorted(total_items.keys()):
            td = total_items[tid]
            lines.append(f"| {tid} | {td['icon']} | {td['name']} | {td['amount']:,} |")
        if total_qp:
            lines.append(f"| — | — | **QP** | **{total_qp:,}** |")
        lines.append("")

    return "\n".join(lines)


# ── Main ──

def generate(data):
    svt = NiceServant.model_validate(data)
    sid = svt.id
    # 国服未实装强化预览（data/servant_preview/{sid}.json，由 scripts/sync_preview.py 生成）
    preview = None
    pv_path = os.path.join(WIKI, "data", "servant_preview", f"{sid}.json")
    if os.path.exists(pv_path):
        try:
            preview = json.load(open(pv_path, encoding="utf-8"))
        except Exception:
            preview = None
    cno = svt.collectionNo
    name = svt.name
    jp_name = data.get("_jp_name", svt.originalName)
    aliases = data.get("_aliases", [])
    class_name = svt.className
    class_id = svt.classId
    # 特殊职阶专名(如 unBeastOlgaMarie)映射为标准职阶名；标准职阶名保持不变
    STANDARD_CLASS = {"saber", "archer", "lancer", "rider", "caster", "assassin",
                      "berserker", "shielder", "ruler", "alterego", "avenger",
                      "mooncancer", "foreigner", "pretender", "beast"}
    if class_name.lower() not in STANDARD_CLASS:
        class_name = CLASS_NAMES.get(class_id, class_name)
    rarity = svt.rarity
    cost = svt.cost
    attr = ATTR_MAP.get(svt.attribute.value if hasattr(svt.attribute, 'value') else str(svt.attribute), str(svt.attribute))

    limits = data.get("limits", [])
    l0 = limits[0] if limits else {}
    alignment = ""
    if l0:
        p = ALIGN_POLICY.get(l0.get("policy", ""), l0.get("policy", ""))
        pe = ALIGN_PERSONALITY.get(l0.get("personality", ""), l0.get("personality", ""))
        alignment = f"{p}·{pe}" if p and pe else f"{p}{pe}"

    gender = GENDER_MAP.get(data.get("gender", ""), data.get("gender", ""))
    svt_type = data.get("type", "")
    svt_flag = data.get("flag", "")
    acquisition = TYPE_LABELS.get(svt_type, svt_type)
    if svt_flag == "limited":
        acquisition = "限定"
    elif svt_flag == "storyLimited":
        acquisition = "剧情限定"
    # 卡池特殊覆盖: 个别从者 type/flag 不可靠(如 U-奥尔加玛丽 type=normal 但实际限定)
    # key = collectionNo
    POOL_OVERRIDE = {
        314: "限定",   # 光之高扬斯卡娅(Atlas type/flag 均为 normal/空，实际期间限定)
        444: "限定",   # U-奥尔加玛丽
        2: "剧情限定",  # 阿尔托莉雅(Saber)
        70: "限定",     # 斯卡哈(Lancer)
        12: "限定",     # 吉尔伽美什
        51: "限定",     # 坂田金时(Berserker)
        20: "常驻",     # 库丘林(Proto)
    }
    acquisition = POOL_OVERRIDE.get(cno, acquisition)

    # Traits
    trait_names = []
    for t in data.get("traits", []):
        tn = t.get("name", "")
        if tn in TRAIT_BLACKLIST:
            continue
        trait_names.append(TRAIT_NAME_CN.get(tn, tn))
    # Add alignment and attribute to traits for searchability
    if alignment and "·" in alignment:
        for part in alignment.split("·"):
            if part:
                trait_names.insert(0, part)
    elif alignment:
        trait_names.insert(0, alignment)
    if attr:
        trait_names.insert(0, attr)

    # Cards
    cards_raw = data.get("cards", [])
    cards_display = [CARD_MAP.get(str(c), str(c)) for c in cards_raw]
    card_icons_str = " ".join(f"![{c}]({CARD_ICONS[c]})" for c in cards_display if CARD_ICONS.get(c))

    # Stats
    atk_base = data.get("atkBase", "")
    atk_max = data.get("atkMax", "")
    hp_base = data.get("hpBase", "")
    hp_max = data.get("hpMax", "")
    lv_max = data.get("lvMax", "")
    atk_g = data.get("atkGrowth", [])
    hp_g = data.get("hpGrowth", [])
    atk_100 = atk_g[99] if len(atk_g) > 99 else ""
    atk_120 = atk_g[119] if len(atk_g) > 119 else ""
    hp_100 = hp_g[99] if len(hp_g) > 99 else ""
    hp_120 = hp_g[119] if len(hp_g) > 119 else ""
    star_gen = data.get("starGen", "")
    death_rate = data.get("instantDeathChance", "")
    star_absorb = data.get("starAbsorb", "")

    # Params
    params = {k: l0.get(k, "") for k in
              ["strength", "endurance", "agility", "magic", "luck"]}
    params["npParam"] = l0.get("np", "")

    # Hits
    hits_dist = data.get("hitsDistribution", {})
    hits = {}
    card_type_map = {"1": "Arts", "2": "Buster", "3": "Quick"}
    for card_detail_id in ["1", "2", "3"]:
        arr = hits_dist.get(card_detail_id, [])
        hits[card_type_map[card_detail_id]] = len(arr)
    # Extra = card detail 4
    extra_hits = len(hits_dist.get("4", []))
    hits["Extra"] = extra_hits

    # NP hits
    nps = data.get("noblePhantasms", [])
    np_hits = len(nps[0].get("npDistribution", [])) if nps else ""

    # NP gain rates
    np_gain_data = nps[0].get("npGain", {}) if nps else {}
    np_gain_atk = np_gain_data.get("arts", [0])[0] if np_gain_data else 0
    np_gain_def = np_gain_data.get("defence", [0])[0] if np_gain_data else 0

    # Skills
    is_multi, skill_modules = get_skill_modules(data.get("skills", []))
    if is_multi:
        skills = []  # 多模组时 skills 由模组循环渲染
    else:
        skills = get_current_skills(data.get("skills", []))
    class_passive = data.get("classPassive", [])
    append_skills = data.get("appendPassive", [])

    # Visuals
    ea = data.get("extraAssets", {})
    faces_asc = ea.get("faces", {}).get("ascension", {})
    cg_asc = ea.get("charaGraph", {}).get("ascension", {})
    status_asc = ea.get("status", {}).get("ascension", {})
    models_asc = ea.get("charaFigure", {}).get("ascension", {})

    # Profile
    profile = data.get("profile", {})
    illustrator = profile.get("illustrator", "")
    cv = profile.get("cv", "")
    comments = profile.get("comments", [])
    voices = profile.get("voices", [])

    # Materials
    asc_mats = data.get("ascensionMaterials", {})
    skill_mats = data.get("skillMaterials", {})
    append_mats = data.get("appendSkillMaterials", {})
    costume_mats = data.get("costumeMaterials", {})

    # Related
    relate_quests = data.get("relateQuestIds", [])
    bond_equip = data.get("bondEquip", 0)
    valentine = data.get("valentineEquip", [])

    stars = "★" * rarity
    class_icon = get_class_icon(class_id, rarity)

    L = []
    def h(s=""): L.append(s)

    # ── Header ──
    h(f"# {name}")
    h()
    h(f"> **ID**: {sid} | **图鉴编号**: {cno} | "
      f"**职阶**: ![{class_name}]({class_icon}) {class_name} | **星级**: {stars} | **No.**: {cno}")
    h()

    # ══ 基础信息 ══
    h("## 基础信息")
    h()
    h("| 属性 | 值 |")
    h("|------|-----|")
    for label, val in [
        ("内部 ID", sid), ("图鉴编号", cno),
        ("名称", name), ("原始名称（日文）", jp_name),
        ("别名", "、".join(aliases) if aliases else "-"),
        ("职阶", f"![]({class_icon}) {class_name}"),
        ("星级", stars), ("编队消耗", cost),
        ("属性", alignment), ("阵营", attr),
        ("性别", gender), ("卡池", acquisition),
        ("指令卡", card_icons_str),
        ("特性", "、".join(trait_names) if trait_names else "-"),
    ]:
        h(f"| {label} | {val} |")
    h()

    # ══ 数值 ══
    h("## 数值")
    h()
    h("| 属性 | 值 |")
    h("|------|-----|")
    for label, val in [
        ("基础攻击力", atk_base),
        (f"满级攻击力(Lv.{lv_max})", atk_max),
        ("基础 HP", hp_base),
        (f"满级 HP(Lv.{lv_max})", hp_max),
        ("100级攻击力", atk_100), ("100级 HP", hp_100),
        ("120级攻击力", atk_120), ("120级 HP", hp_120),
        ("筋力", params["strength"]), ("耐久", params["endurance"]),
        ("敏捷", params["agility"]), ("魔力", params["magic"]),
        ("幸运", params["luck"]), ("宝具", params["npParam"]),
        ("出星率", f"{star_gen}%"),
        ("被即死率", f"{death_rate / 10:.1f}%" if death_rate else ""),
        ("暴击星权重", star_absorb),
        ("NP获得率(攻击)", f"{np_gain_atk / 100:.2f}%" if np_gain_atk else ""),
        ("NP获得率(受击)", f"{np_gain_def / 100:.2f}%" if np_gain_def else ""),
    ]:
        h(f"| {label} | {val} |")
    h()
    h("### Hit 信息")
    h()
    h("| 卡牌 | Hit 数 |")
    h("|------|--------|")
    for card in ["Quick", "Arts", "Buster", "Extra"]:
        hv = hits.get(card, 0)
        h(f"| {card} | {hv} |")
    h(f"| 宝具 | {np_hits} |")
    h()

    # ══ 持有技能 ══
    h("## 持有技能")
    h()
    def render_one_skill(sk):
        sk_name = sk.get("name", "???")
        sk_icon = sk.get("icon", "")
        h()
        h(format_skill_detail(sk, sk_icon))
        old = sk.get("_old_versions", [])
        if old:
            old_sk = old[0]
            h(f"◈ 强化前：{old_sk.get('name', '?')}")
            h()
            h(format_skill_detail(old_sk, old_sk.get('icon', '')))
            h(f"此技能由「{old_sk.get('name', '?')}」强化而来")
            h()
            qid = sk.get("condQuestId") or old_sk.get("condQuestId", 0)
            if qid:
                h(f"开放条件: 从者强化任务 (Quest ID: {qid})")
                h()
        # 国服未实装强化预览（日服已实装，CN 未实装）
        if preview:
            pv_sk = preview.get("skills", {}).get(str(sk.get("num", 0)))
            if pv_sk:
                pv_date = pv_sk.get("jp_opened_at")
                pv_event = pv_sk.get("event_name")
                pv_qid = pv_sk.get("condQuestId")
                if pv_event and pv_date:
                    pv_when = f"（{pv_event}，{pv_date} 实装）"
                elif pv_date:
                    pv_when = f"（{pv_date} 实装）"
                elif pv_event:
                    pv_when = f"（{pv_event} 实装）"
                else:
                    pv_when = ""
                h(f"⚠ 国服未实装：日服已强化为「{pv_sk.get('name', '?')}」{pv_when}")
                h()
                h(format_skill_detail(pv_sk, pv_sk.get("icon", "")))
                if pv_qid:
                    h(f"开放条件: 从者强化任务 (Quest ID: {pv_qid})")
                h()
        h()

    if is_multi:
        # 多模组: 每套技能模组独立成组渲染，标注模组序号
        for mod in skill_modules:
            pri = mod["priority"]
            h(f"### 技能模组 {pri}")
            h()
            for sk in mod["skills"]:
                render_one_skill(sk)
    else:
        for sk in skills:
            render_one_skill(sk)

    # ══ 职阶技能 ══
    h("## 职阶技能")
    h()
    for cp in class_passive:
        cp_name = cp.get("name", "???")
        # Strip rank suffix to get base name
        cp_base = cp_name.rstrip(" ABCDEFGHIJKLMNOPQRSTUVWXYZ+＋-")
        cp_rank = cp_name[len(cp_base):].strip()
        cp_detail = cp.get("detail", "")
        cp_icon = cp.get("icon", "")
        cp_fns = cp.get("functions", [])
        cp_val_str = ""
        if cp_fns:
            fn = cp_fns[0]
            svals = fn.get("svals", [])
            if svals:
                ft = fn.get("funcType", "")
                fv = format_val(svals[0].get('Value', ''), ft)
                cp_val_str = f" {fv}" if fv is not None else ""
        ref_path = SHARED_CLASS.get(cp_base) or SHARED_CLASS_JP.get(cp_base)
        if ref_path:
            h(f"- **[[{cp_name}]]** ({ref_path}): {cp_detail}{cp_val_str}")
        else:
            h(f"- **{cp_name}**: {cp_detail}{cp_val_str}  ![]({cp_icon})")
        h()

    # ══ 追加技能 ══
    h("## 追加技能")
    h()
    for ap in append_skills:
        ask = ap.get("skill", {})
        ask_name = ask.get("name", "???")
        ask_detail = ask.get("detail", "")
        ref_path = SHARED_APPEND.get(ask_name) or resolve_append_ref(ask_name) or SHARED_APPEND_JP.get(ask_name) or resolve_append_ref_jp(ask_name)
        if ref_path:
            h(f"- **[[{ask_name}]]** ({ref_path}): {ask_detail}")
        else:
            # Inline compact display
            fns = ask.get("functions", [])
            vals_list = []
            for fn in fns:
                ft = fn.get("funcType", "")
                if ft in SKIP_FUNCTYPES:
                    continue
                svals = fn.get("svals", [])
                numeric = [s.get("Value") for s in svals if s.get("Value") is not None and isinstance(s.get("Value"), (int, float))]
                if not numeric:
                    continue
                fmt = [format_val(v, ft) for v in numeric]
                fmt = [f for f in fmt if f is not None]
                if fmt:
                    vals_list.append("    ".join(fmt) if len(set(fmt)) > 1 else fmt[0])
            summary = " → ".join(vals_list) if vals_list else "-"
            h(f"- **{ask_name}**: {ask_detail}  [{summary}]")
        h()

    # ══ 宝具 ══
    h("## 宝具")
    h()
    is_multi_np, np_modules = get_np_modules(nps)
    if is_multi_np:
        # 双宝具模组（如玉兔 num=1 + num=98）：每个 num 独立标注模组序号
        for mi, np in enumerate(np_modules, start=1):
            h(f"**宝具模组 {mi}**")
            h()
            h(format_np_new(np, True))
            if mi < len(np_modules):
                h("---")
            h()
    else:
        # 过滤 ??? 占位宝具版本（与正式版本成对、效果重复）；全占位时兜底保留
        filtered_nps = [n for n in nps if n.get("name") != "？？？"]
        if not filtered_nps:
            filtered_nps = nps
        sorted_nps = sorted(filtered_nps, key=lambda x: x.get("priority", 0))
        for ni, np in enumerate(sorted_nps):
            is_current = (ni == len(sorted_nps) - 1)
            if len(sorted_nps) == 1:
                status_tag = "**未强化**"
            elif is_current:
                status_tag = "**强化后**"
            else:
                status_tag = "**强化前**"
            h(status_tag)
            h()
            h(format_np_new(np, is_current))
            if not is_current:
                h("---")
            h()
        # 国服未实装强化预览（日服已实装，CN 未实装）— 宝具
        if preview:
            for pv_num, pv_np in preview.get("nps", {}).items():
                pv_date = pv_np.get("jp_opened_at")
                pv_event = pv_np.get("event_name")
                pv_qid = pv_np.get("condQuestId")
                if pv_event and pv_date:
                    pv_when = f"（{pv_event}，{pv_date} 实装）"
                elif pv_date:
                    pv_when = f"（{pv_date} 实装）"
                elif pv_event:
                    pv_when = f"（{pv_event} 实装）"
                else:
                    pv_when = ""
                h(f"⚠ 国服未实装：日服已强化为「{pv_np.get('name', '?')}」{pv_when}")
                h()
                h(format_np_new(pv_np, False))
                if pv_qid:
                    h(f"开放条件: 从者强化任务 (Quest ID: {pv_qid})")
                h()

    # ══ 视觉资源 ══
    h("## 视觉资源")
    h()
    h("### 头像")
    for k in sorted(faces_asc, key=int):
        h(f"- 再临 {k}: ![]({faces_asc[k]})")
    h()
    h("### 卡面")
    for k in sorted(cg_asc, key=int):
        h(f"- 再临 {k}: ![]({cg_asc[k]})")
    h()
    h("### 灵基再临图标")
    for k in sorted(status_asc, key=int):
        h(f"- 再临 {k}: ![]({status_asc[k]})")
    h()
    # Costume icons
    costume_icons = ea.get("equipFace", {})
    if not costume_icons:
        # Try other sources
        costume_icons = ea.get("faces", {}).get("costume", {})
    if costume_icons:
        h("### 灵衣图标")
        for k in costume_icons:
            h(f"- 灵衣 {k}: ![]({costume_icons[k]})")
        h()
    if models_asc:
        h("### 模型")
        for k in sorted(models_asc, key=int):
            h(f"- 再临 {k}: ![]({models_asc[k]})")
        h()

    # ══ 资料 ══
    h("## 资料")
    h()
    h(f"- **画师**: {illustrator}")
    h(f"- **声优**: {cv}")
    h(f"- **完整资料**: [[资料/{name}]]")
    h()
    # Write lore to separate file
    lore_lines = [f"# {name} - 资料", "",
                  f"- **画师**: {illustrator}", f"- **声优**: {cv}", ""]
    for c in comments:
        lore_lines.append(f"### 资料 {c.get('id', '?')}")
        lore_lines.append(c.get("comment", ""))
        lore_lines.append("")
    lore_path = os.path.join(WIKI, "references", "lore", f"{name}.md")
    with open(lore_path, "w", encoding="utf-8") as lf:
        lf.write("\n".join(lore_lines))

    # ══ 材料需求 ══
    h("## 材料需求")
    h()
    if asc_mats:
        h(mat_table("灵基再临", asc_mats,
                    format_key=lambda k: f"阶段{k} → {k+1}"))
    if skill_mats:
        h(mat_table("技能强化", skill_mats))
    if append_mats:
        h(mat_table("追加技能", append_mats))
    if costume_mats:
        # Try to get costume name
        costume_info = data.get("profile", {}).get("costume", {})
        costume_names = {}
        # costume_info only has IDs, try to get names from basic list
        try:
            with open("/tmp/fgo_servant_list.json") as f:
                blist = json.load(f)
            for s in blist:
                if s["id"] == sid:
                    for ck, cv in s.get("costume", {}).items():
                        costume_names[ck] = cv.get("shortName", f"灵衣{ck}")
                    break
        except:
            pass
        h(mat_table("灵衣开放", costume_mats,
                format_key=lambda k: costume_names.get(str(k), f"灵衣{str(k)}"),
                show_total=False))

    # ══ 语音 ══
    h("## 语音")
    h()
    h(f"- **完整语音**: [[语音/{name}]]")
    h()
    # Write voices to separate file
    voice_lines = [f"# {name} - 语音", ""]
    from collections import defaultdict
    by_type = defaultdict(list)
    for vg in voices:
        vtype = vg.get("type", "")
        by_type[vtype].append(vg)
    for vtype, groups in by_type.items():
        vlabel = VOICE_TYPE_NAMES.get(vtype, vtype)
        voice_lines.append(f"## {vlabel}")
        voice_lines.append("")
        if len(groups) == 1 and groups[0].get("voicePrefix", 0) == 0:
            for vl in groups[0].get("voiceLines", []):
                vname = vl.get("name", "")
                vtext = vl.get("text", "")
                if isinstance(vtext, list): vtext = " ".join(vtext)
                vtext = vtext.replace("[r]", "").replace("\\n", " ").strip()
                if not vtext: continue
                voice_lines.append(f"- **{vname}**: {vtext[:200]}")
        else:
            for vg in groups:
                vp = vg.get("voicePrefix", 0)
                prefix_label = f"形态{vp}" if vp > 0 else "基础"
                voice_lines.append(f"### {prefix_label}")
                voice_lines.append("")
                for vl in vg.get("voiceLines", []):
                    vname = vl.get("name", "")
                    vtext = vl.get("text", "")
                    if isinstance(vtext, list): vtext = " ".join(vtext)
                    vtext = vtext.replace("[r]", "").replace("\\n", " ").strip()
                    if not vtext: continue
                    voice_lines.append(f"- **{vname}**: {vtext[:200]}")
                voice_lines.append("")
        voice_lines.append("")
    voice_path = os.path.join(WIKI, "references", "voices", f"{name}.md")
    with open(voice_path, "w", encoding="utf-8") as vf:
        vf.write("\n".join(voice_lines))

    # ══ 关联内容 ══
    h("## 关联内容")
    h()
    if relate_quests:
        h("### 幕间物语 / 强化关卡")
        for q in relate_quests:
            h(f"- [[关卡/{q}]]")
        h()
    ce = f"[[礼装/{bond_equip}]]" if bond_equip else "待补充"
    val = ", ".join(f"[[礼装/{v}]]" for v in valentine) if valentine else "待补充"
    h(f"- **羁绊礼装**: {ce}")
    h(f"- **情人节礼物**: {val}")
    h(f"- **卡池**: [[卡池/{name}]]")
    h()

    if not DISABLE_FOOTER:
        h("---")
        h()
        h("*数据来源: [Atlas Academy API](https://api.atlasacademy.io) | 游戏素材版权归 TYPE-MOON / FGO PROJECT 所有*")
    
    return "\n".join(L)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate.py <servant_id>")
        sys.exit(1)
    sid = sys.argv[1]
    json_path = os.path.join(WIKI, f"raw/servants/CN/{sid}.json")
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found")
        sys.exit(1)
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    md = generate(data)
    name = data.get("name", str(sid)).replace("/", "·").replace("\\", "")
    entity_id = data.get("id", sid)
    entity_path = os.path.join(WIKI, "entities/servants/CN", f"{entity_id}.md")
    with open(entity_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Generated: {entity_path} ({len(md)} chars)")


if __name__ == "__main__":
    main()
