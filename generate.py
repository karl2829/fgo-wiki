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
    38: "BeastEresh",
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
    "genderCaenisServant": "性别不明",
    "genderUnknown": "性别不明",
    "genji": "源氏",
    "giant": "巨人",
    "greekMythologyMales": "希腊神话男性",
    "groupServant": "群体从者",
    "hasCostume": "持有灵衣之人",
    "hasGoddessMetamorphosis": "拥有女神变容",
    "hasSupereffectiveNPAgainstAlignmentEvil": "对恶特攻",
    "hasSupereffectiveNPAgainstAlignmentGood": "对善特攻",
    "havingAnimalsCharacteristics": "动物特性",
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
    
    # Skip very large values (>50000, state references) 
    if all(v > 50000 for v in vs):
        return [], True, lambda v: ""
    # Values of 0 or 1 for evasion/dodge/guts are flags, not percentages (only for Value field, not Value2)
    if all(v < 5 for v in vs) and fn.get("funcType","") not in (NiceFuncType.delayNpturn,):
        # Check if this is a Value2-based buff (like attack-trigger NP gain)
        buffs = fn.get("buffs", [])
        is_value2 = False
        if buffs:
            bid = str(buffs[0].get("id", ""))
            if bid in BUFF_CALC and BUFF_CALC[bid].get("field") == "Value2":
                is_value2 = True
        if not is_value2:
            return [], True, lambda v: ""
    if divisor == 0:
        return vs, len(set(vs)) <= 1, lambda v: str(v)
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
        sk["_old_versions"] = [s for s in all_by_num[num]
                               if s.get("priority", 0) < sk.get("priority", 0)]
    return result


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


def match_func_to_segment(segment, funcs, used_indices):
    """Match a detail segment to the best corresponding function by text similarity.
    Uses substring match as priority, then bigram overlap as fallback."""
    best_idx = None
    best_score = 0
    for fi, fn in enumerate(funcs):
        if fi in used_indices:
            continue
        ft = fn.get("funcType", "")
        if ft in (NiceFuncType.subState,):
            continue
        # Collect all searchable text from this function
        texts = set()
        for b in fn.get("buffs", []):
            if b.get("detail"): texts.add(b["detail"])
            if b.get("name"): texts.add(b["name"])
        texts.add(fn.get("funcPopupText", ""))
        texts.discard("")
        
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
            
            if score > best_score:
                best_score = score
                best_idx = fi
    return best_idx


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

    # Step 1: Split detail by ＆/＋
    parts = [p.strip() for p in re.split(r'[＆&＋+]', detail) if p.strip()]
    funcs = sk.get("functions", [])
    used = set()

    for part in parts:
        fi = match_func_to_segment(part, funcs, used)
        if fi is None:
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
        is_damage = ft in ("damageNp", "damageNpIndividual", "damageNpPierce")
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
    cno = svt.collectionNo
    name = svt.name
    jp_name = data.get("_jp_name", svt.originalName)
    aliases = data.get("_aliases", [])
    class_name = svt.className
    class_id = svt.classId
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
      f"**职阶**: ![{class_name}]({class_icon}) {class_name} | **星级**: {stars}")
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
    for sk in skills:
        sk_name = sk.get("name", "???")
        sk_icon = sk.get("icon", "")
        sk_ss = sk.get("strengthStatus", 0)
        sk_cq = sk.get("condQuestId", 0)
        has_strengthen = sk_ss > 0
        h()
        h(format_skill_detail(sk, sk_icon))
        old = sk.get("_old_versions", [])
        if old and has_strengthen:
            old_sk = old[0]
            h(f"◈ 强化前：{old_sk.get('name', '?')}")
            h()
            h(format_skill_detail(old_sk, old_sk.get('icon', '')))
            h(f"此技能由「{old_sk.get('name', '?')}」强化而来")
            h()
            qid = sk_cq or old_sk.get("condQuestId", 0)
            if qid:
                h(f"开放条件: 从者强化任务 (Quest ID: {qid})")
                h()
        h()

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
    sorted_nps = sorted(nps, key=lambda x: x.get("priority", 0))
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
