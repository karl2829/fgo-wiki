#!/usr/bin/env python3
"""生成 FGO 特性统计 MD 文件（参考 Mooncell 特性页格式）

用法: python3 gen_trait_stats.py [特性名...]
    不带参数 = 生成全部 79 个常规特性 + 特殊组合特性
    带参数   = 只生成指定特性（支持中/英文名）

数据源: ~/fgo-wiki/raw/servants/{CN,JP}/*.json
- 常规 trait: base + traitAdd + ascensionAdd.individuality.{ascension,costume} 全部合并
- 组合特性: 按 alignment/gender/class 条件判断，支持"任一阶段满足"逻辑
- 部分灵基才有: 生成时标注满足条件的阶段
"""
import json, os, glob, re, collections, sys
from datetime import datetime

FGO_WIKI = os.path.expanduser('~/fgo-wiki')
RAW = os.path.join(FGO_WIKI, 'raw', 'servants')
OUT = os.path.join(FGO_WIKI, 'entities', 'traits')

# ---------- 1. 加载 trait 翻译表 ----------
TRAIT_NAME_CN = {}
TRAIT_BLACKLIST = set()
with open(os.path.join(FGO_WIKI, 'generate.py')) as f:
    src = f.read()
m = re.search(r'TRAIT_NAME_CN\s*=\s*\{(.*?)\n\}', src, re.S)
if m:
    for k, v in re.findall(r'"([^"]+)"\s*:\s*"([^"]*)"', m.group(1)):
        TRAIT_NAME_CN[k] = v
m = re.search(r'TRAIT_BLACKLIST\s*=\s*\{(.*?)\n\}', src, re.S)
if m:
    TRAIT_BLACKLIST = set(re.findall(r'"([^"]+)"', m.group(1)))

# Mooncell 标准名修正 + 别名标注（trait_translations.json / generate.py 里为旧名"动物特性"）
# NAME_OVERRIDES: trait_key -> (标准显示名, 别名标注)
NAME_OVERRIDES = {
    'havingAnimalsCharacteristics': ('兽科从者', '动物特性'),
    'genderCaenisServant': ('性别不明（凯妮斯型）', '性别不明·凯妮斯'),
}

# Atlas API 数据缺失、但 Mooncell 明确判定的补充名单（含对应灵衣，2026-08 核验）
# key = trait_key, value = list of collectionNo（这些从者拥有对应特性但 Atlas traits 未标注）
MOONCELL_SUPPLEMENT = {
    'hasCostume': [161, 346, 408, 437, 444],  # 土方岁三 No.133 / 莫里亚蒂(Ruler) No.135 / 耀星哈桑 No.140 / 但丁 No.142 / U-奥尔加玛丽 No.136
    # 组合特性补充：key = 中文名 + '_extra'，value 为 collectionNo 列表
    '混沌且七骑士_extra': [81],  # 亨利·杰基尔＆海德：宝具变身后(海德)变为混沌属性，Mooncell 计入混沌且七骑士
}

# ---------- 2. 加载全部从者（含 per-stage traits） ----------
class Servant:
    __slots__ = ['cno', 'name', 'className', 'classId', 'region',
                 'base_traits', 'stages']  # stages: list of (label, frozenset traits)

def load_servants():
    servants = {}
    for region in ['CN', 'JP']:
        for fn in glob.glob(os.path.join(RAW, region, '*.json')):
            try:
                with open(fn) as f:
                    d = json.load(f)
                cno = d.get('collectionNo')
                if cno is None:
                    continue
                if cno in servants and region == 'JP':
                    continue
                sv = Servant()
                sv.cno = cno
                sv.name = d.get('name', '')
                sv.className = d.get('className', '')
                sv.classId = d.get('classId')
                sv.region = region
                # base traits + traitAdd（Atlas 视为常驻拥有，Mooncell 统计含此类）
                base = set(t['name'] for t in d.get('traits', []))
                for ta in d.get('traitAdd', []):
                    for t in ta.get('trait', []):
                        base.add(t['name'])
                sv.base_traits = frozenset(base)
                stages = []
                ind = (d.get('ascensionAdd') or {}).get('individuality') or {}
                asc = ind.get('ascension') or {}
                for k in sorted(asc.keys(), key=lambda x: int(x) if str(x).isdigit() else x):
                    stage_name = f"第{int(k)+1}阶段" if str(k).isdigit() else str(k)
                    stages.append((stage_name, frozenset(t['name'] for t in asc[k])))
                cost = ind.get('costume') or {}
                for cid, lst in cost.items():
                    stages.append((f"灵衣{cid}", frozenset(t['name'] for t in lst)))
                sv.stages = stages
                servants[cno] = sv
            except Exception:
                continue
    return servants

SERVANTS = load_servants()

# ---------- 3. 职阶 ----------
CLASS_ORDER = ['saber', 'archer', 'lancer', 'rider', 'caster', 'assassin',
               'berserker', 'ruler', 'avenger', 'alterEgo', 'moonCancer',
               'foreigner', 'pretender', 'shielder', 'beast', 'beastI', 'beastII',
               'beastIIIL', 'beastIIIR', 'beastIV', 'beastEresh', 'beastVII',
               'unBeastOlgaMarie', 'uOlgaMarieFlareCollection',
               'uOlgaMarieGrandCollection', 'uOlgaMarieAquaCollection',
               'uOlgaMarieStellarCollection', 'loreGrandCaster', 'unknown']
CLASS_CN = {
    'saber': '剑士', 'archer': '弓兵', 'lancer': '枪兵', 'rider': '骑兵',
    'caster': '魔术师', 'assassin': '暗杀者', 'berserker': '狂战士',
    'ruler': '裁定者', 'avenger': '复仇者', 'alterEgo': 'Alterego',
    'moonCancer': 'MoonCancer', 'foreigner': '降临者', 'pretender': 'Pretender',
    'shielder': '盾兵', 'beast': 'Beast', 'beastI': 'BeastⅠ',
    'beastII': 'BeastⅡ', 'beastIIIL': 'BeastⅢ／L', 'beastIIIR': 'BeastⅢ／R',
    'beastIV': 'BeastⅣ', 'beastEresh': 'Beast(埃列什基伽勒)',
    'beastVII': 'BeastⅦ', 'unBeastOlgaMarie': 'U-奥尔加玛丽(UnBeast)',
    'uOlgaMarieFlareCollection': 'U-奥尔加玛丽(Flare)',
    'uOlgaMarieGrandCollection': 'U-奥尔加玛丽(Grand)',
    'uOlgaMarieAquaCollection': 'U-奥尔加玛丽(Aqua)',
    'uOlgaMarieStellarCollection': 'U-奥尔加玛丽(Stellar)',
    'loreGrandCaster': '冠位Caster', 'unknown': '未知',
}

def get_class_cn(cls):
    return CLASS_CN.get(cls, cls)

# ---------- 4. 特性成员判定 ----------
def trait_members(trait_key):
    """常规 trait：任一阶段/基础拥有即算；Atlas 缺失的用 Mooncell 补充"""
    members = {}
    for cno, sv in SERVANTS.items():
        if trait_key in sv.base_traits:
            members[cno] = None  # None = 无条件
        else:
            for label, tset in sv.stages:
                if trait_key in tset:
                    members[cno] = label
                    break
    for cno in MOONCELL_SUPPLEMENT.get(trait_key, []):
        if cno not in members and cno in SERVANTS:
            members[cno] = 'Mooncell补充'
    return members

def combo_members(cond, desc):
    """组合特性：条件函数 sv -> True/False，返回 (members, stage_note)"""
    members = {}
    stage_info = {}
    for cno, sv in SERVANTS.items():
        satisfied = []
        if cond(sv.base_traits):
            satisfied.append('基础')
        for label, tset in sv.stages:
            if cond(tset):
                satisfied.append(label)
        if satisfied:
            members[cno] = None
            stage_info[cno] = satisfied
    return members, stage_info

# 组合条件
def has(tset, *names):
    return all(n in tset for n in names)

def any_of(tset, *names):
    return any(n in tset for n in names)

SPECIAL = {
    # key: (中文名, 类型, 数据)
    '兽科从者': ('special', 'havingAnimalsCharacteristics'),
    '秩序且善': ('combo', lambda ts: has(ts, 'alignmentLawful', 'alignmentGood')),
    '秩序的女性': ('combo', lambda ts: has(ts, 'alignmentLawful', 'genderFemale')),
    '中立': ('combo', lambda ts: has(ts, 'alignmentNeutral')),
    '混沌且七骑士': ('combo', lambda ts: has(ts, 'alignmentChaotic', 'standardClassServant')),
    '星之力或恶': ('combo', lambda ts: any_of(ts, 'attributeStar', 'alignmentEvil')),
    '秩序': ('combo', lambda ts: has(ts, 'alignmentLawful')),
    '善': ('combo', lambda ts: has(ts, 'alignmentGood')),
    '恶': ('combo', lambda ts: has(ts, 'alignmentEvil')),
}

# ---------- 5. 渲染 ----------
def build_class_groups(cnos):
    groups = collections.defaultdict(list)
    for cno in sorted(cnos):
        sv = SERVANTS.get(cno)
        if not sv:
            groups['unknown'].append(cno)
            continue
        groups[sv.className].append(cno)
    return groups

def fmt_servant_list(cnos, stage_info=None):
    parts = []
    for cno in sorted(cnos):
        sv = SERVANTS.get(cno)
        if not sv:
            parts.append(f"#{cno}(本地缺失)")
            continue
        jp = ' *' if sv.region == 'JP' else ''
        if stage_info and stage_info.get(cno):
            cond = '；'.join(stage_info[cno][:3])
            if len(stage_info[cno]) > 3:
                cond += f' 等{len(stage_info[cno])}项'
            parts.append(f"{sv.name}(#{cno}){jp} [仅部分形态:{cond}]")
        else:
            parts.append(f"{sv.name}(#{cno}){jp}")
    return parts

def render_md(cn_name, en_name, members, stage_info=None, note_lines=None, alias=None):
    groups = build_class_groups(members)
    total = len(members)
    lines = []
    lines.append(f"# 特性：{cn_name}")
    lines.append("")
    if en_name:
        lines.append(f"> **特性名**: {cn_name} (`{en_name}`)")
    if alias:
        lines.append(f"> **别名**: {alias}")
    lines.append(f"> **持有该特性的可召唤从者数**: {total}")
    # JP 标记统计
    jp_count = sum(1 for cno in members if cno in SERVANTS and SERVANTS[cno].region == 'JP')
    if jp_count:
        lines.append(f"> 其中 {jp_count} 名为仅日服实装的从者（带 * 标记）")
    lines.append("")
    # 职阶分布
    lines.append("## 特性分布")
    lines.append("")
    lines.append("| 职阶 | 数量 |")
    lines.append("|------|------|")
    for cls in CLASS_ORDER:
        lst = groups.get(cls, [])
        if not lst:
            continue
        pct = f"{len(lst)/total*100:.1f}%" if total else "0%"
        lines.append(f"| {get_class_cn(cls)} | {len(lst)} ({pct}) |")
    for cls, lst in groups.items():
        if cls not in CLASS_ORDER:
            lines.append(f"| {cls} | {len(lst)} |")
    lines.append("")
    lines.append("## 持有该特性的从者")
    lines.append("")
    for cls in CLASS_ORDER:
        lst = groups.get(cls, [])
        if not lst:
            continue
        lines.append(f"### {get_class_cn(cls)}（{len(lst)}）")
        lines.append("")
        for s in fmt_servant_list(lst, stage_info):
            lines.append(f"- {s}")
        lines.append("")
    for cls, lst in groups.items():
        if cls not in CLASS_ORDER:
            lines.append(f"### {cls}（{len(lst)}）")
            lines.append("")
            for s in fmt_servant_list(lst, stage_info):
                lines.append(f"- {s}")
            lines.append("")
    if note_lines:
        lines.append("## 备注")
        lines.append("")
        for n in note_lines:
            lines.append(f"- {n}")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*数据来源: [Atlas Academy API](https://api.atlasacademy.io) | 游戏素材版权归 TYPE-MOON / FGO PROJECT 所有*")
    lines.append("")
    return "\n".join(lines)

def cn_name_for(trait_key):
    """返回 (显示名, 别名) ；无别名时别名=None"""
    if trait_key in NAME_OVERRIDES:
        ov = NAME_OVERRIDES[trait_key]
        if isinstance(ov, tuple):
            return ov
        return ov, None
    return TRAIT_NAME_CN.get(trait_key, trait_key), None

def safe_filename(cn):
    # 文件名保留别名标注，方便检索；替换文件名非法字符
    return cn.replace('/', '_').replace('（', '(').replace('）', ')')

def main():
    os.makedirs(OUT, exist_ok=True)
    args = sys.argv[1:]
    generated = []

    # A. 常规 trait
    trait_member_map = {}
    for t in TRAIT_NAME_CN:
        if t in TRAIT_BLACKLIST:
            continue
        trait_member_map[t] = trait_members(t)

    # 是否过滤只生成指定特性
    wanted = set()
    if args:
        wanted = set(args)

    for t, members in sorted(trait_member_map.items(), key=lambda x: -len(x[1])):
        if t == 'havingAnimalsCharacteristics':
            continue  # 由 SPECIAL 生成（中文名修正为"兽科从者"）
        cn, alias = cn_name_for(t)
        if args and not (cn in wanted or t in wanted or TRAIT_NAME_CN.get(t) in wanted or (alias and alias in wanted)):
            continue
        fname = safe_filename(f"特性：{cn}.md")
        note = []
        if t == 'havingAnimalsCharacteristics':
            note = ['本特性即游戏内礼装「来自NFF的爱」等羁绊加成对象〔兽科从者〕。',
                    '判定合并了基础特性、灵基阶段追加与灵衣追加（部分从者仅特定形态拥有）。']
        if t == 'hasCostume':
            note = ['本特性即游戏内礼装「至诚的一针」等羁绊加成对象〔持有灵衣之人〕。',
                    '判定合并了基础特性、灵基阶段追加与灵衣追加（部分从者仅特定形态拥有）。',
                    '以下从者拥有灵衣但 Atlas API 未标注该特性，按 Mooncell 灵衣一览补充：'
                    + '、'.join(f'#{cno} {SERVANTS[cno].name}' for cno in MOONCELL_SUPPLEMENT['hasCostume'] if cno in SERVANTS) + '。']
        content = render_md(cn, t, members, note_lines=note, alias=alias)
        with open(os.path.join(OUT, fname), 'w') as f:
            f.write(content)
        generated.append((fname, len(members)))

    # B. 特殊组合特性
    for cn, spec in SPECIAL.items():
        if args and cn not in wanted and '兽科' not in wanted and '动物特性' not in wanted:
            continue
        kind, data = spec
        if kind == 'special':
            t = data
            members = trait_member_map.get(t, trait_members(t))
            stage_info = None
            en = t
            # 应用 NAME_OVERRIDES 标注（如 兽科从者 别名 动物特性）
            disp, alias = cn_name_for(t)
            if disp != t:
                cn = disp
        else:
            members, stage_info = combo_members(data, cn)
            en = cn
            alias = None
            # 组合特性补充（Mooncell 判定但 Atlas 无数据，如宝具变身形态）
            for cno in MOONCELL_SUPPLEMENT.get(cn + '_extra', []):
                if cno in SERVANTS and cno not in members:
                    members[cno] = None
                    stage_info[cno] = ['Mooncell补充']
        note = []
        if cn == '秩序且善':
            note = ['游戏内礼装「检查报告」的羁绊加成对象：〔秩序且善〕特性从者。',
                    '判定条件：同时拥有「秩序」与「善」属性（任一形态）。']
        elif cn == '秩序的女性':
            note = ['游戏内礼装「献给幸福的新娘」的羁绊加成对象：〔秩序的女性〕特性从者。',
                    '判定条件：同时拥有「秩序」属性和女性性别（任一形态）。']
        elif cn == '中立':
            note = ['游戏内礼装「記憶の大図書館」(JP)的羁绊加成对象：〔中立〕特性从者。',
                    '判定条件：拥有「中立」属性（任一形态）。']
        elif cn == '混沌且七骑士':
            note = ['游戏内礼装「カルデアの者」(JP)的羁绊加成对象：〔混沌且七骑士〕特性从者。',
                    '判定条件：同时拥有「混沌」属性和七骑士标准职阶（任一形态）。',
                    '补充：亨利·杰基尔＆海德(#81) 宝具变身后(海德)变为混沌属性，按 Mooncell 计入。']
        elif cn == '星之力或恶':
            note = ['游戏内礼装「異星の神」(JP)的羁绊加成对象：〔星之力从者〕或〔恶〕特性从者。',
                    '判定条件：拥有「星」属性 或 「恶」属性（任一形态）。']
        content = render_md(cn, en, members, stage_info=stage_info, note_lines=note, alias=alias)
        fname = safe_filename(f"特性：{cn}.md")
        with open(os.path.join(OUT, fname), 'w') as f:
            f.write(content)
        generated.append((fname, len(members)))

    print(f"共生成 {len(generated)} 个特性 MD")
    for fname, n in sorted(generated):
        print(f"  {fname} ({n})")

if __name__ == '__main__':
    main()
