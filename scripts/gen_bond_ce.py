#!/usr/bin/env python3
"""生成「羁绊加成礼装」专属索引 MD —— 解决「哪些从者能吃到这张羁绊礼装加成」的检索问题。

数据源（纯本地，不联网）：
- raw/craft-essences/{CN,JP}/*.json  → 礼装效果（funcType=servantFriendshipUp）
- raw/servants/{CN,JP}/*.json        → 从者 traits / 职阶 / 星级 / 形态

输出：entities/bond-ce/
- index.md                      总览 + 条件反查 + 全体（无条件）羁绊礼装表
- 羁绊礼装：No.{cno} {name}.md   单张礼装：条件 + 按职阶×星级的达标从者名单
- 从者适配反查.md                从者 → 可吃到的羁绊礼装

条件语义（来自 Atlas functions）：
- functvals 多个           = OR（任一特性即可）
- script.overwriteTvals    = 外层 OR，内层 AND
- 纯数字 id 组（如 2801200） = 特指某个 svtId 的从者（不是 traits）
用法: ~/fgo-wiki/.venv/bin/python scripts/gen_bond_ce.py
"""
import json, os, glob, collections

FGO_WIKI = os.path.expanduser('~/fgo-wiki')
RAW_CE = os.path.join(FGO_WIKI, 'raw', 'craft-essences')
RAW_SVT = os.path.join(FGO_WIKI, 'raw', 'servants')
OUT = os.path.join(FGO_WIKI, 'entities', 'bond-ce')

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
TRAIT_CN = {
    'havingAnimalsCharacteristics': '兽科从者',
    'FSNServant': 'Fate/stay night从者',
    'livingHuman': '活在当下的人类',
    'hasCostume': '拥有灵衣之人',
    'alignmentLawful': '秩序', 'alignmentGood': '善', 'alignmentNeutral': '中立',
    'alignmentChaotic': '混沌', 'alignmentEvil': '恶',
    'genderFemale': '女性', 'attributeStar': '星属性',
    'standardClassServant': '七骑士职阶',
    'classSaber': '剑士职阶', 'classArcher': '弓兵职阶', 'classLancer': '枪兵职阶',
    'classRider': '骑兵职阶', 'classCaster': '魔术师职阶',
    'classAssassin': '暗杀者职阶', 'classBerserker': '狂战士职阶',
}
ALIGN_CN = {'alignmentLawful': '秩序', 'alignmentNeutral': '中立', 'alignmentChaotic': '混沌',
            'alignmentGood': '善', 'alignmentEvil': '恶', 'alignmentBalanced': '中庸'}


def trait_cn(name):
    return TRAIT_CN.get(name, name)


# ---------------- 从者 ----------------
class Servant:
    __slots__ = ['cno', 'svt_ids', 'name', 'className', 'rarity', 'region',
                 'base_traits', 'stages']


def load_servants():
    out = {}
    for region in ['CN', 'JP']:
        for fn in glob.glob(os.path.join(RAW_SVT, region, '*.json')):
            try:
                d = json.load(open(fn))
            except Exception:
                continue
            cno = d.get('collectionNo')
            if cno is None:
                continue
            if cno in out and region == 'JP':
                continue
            s = Servant()
            s.cno = cno
            s.svt_ids = {d.get('id')}
            s.name = d.get('name', '')
            s.className = d.get('className', 'unknown')
            s.rarity = d.get('rarity', 0)
            s.region = region
            base = set(t['name'] for t in d.get('traits') or [])
            for ta in d.get('traitAdd') or []:
                for t in ta.get('trait') or []:
                    base.add(t['name'])
            s.base_traits = frozenset(base)
            stages = []
            ind = (d.get('ascensionAdd') or {}).get('individuality') or {}
            for k, lst in (ind.get('ascension') or {}).items():
                label = f"第{int(k)+1}阶段" if str(k).isdigit() else str(k)
                stages.append((label, frozenset(t['name'] for t in lst)))
            for cid, lst in (ind.get('costume') or {}).items():
                stages.append((f"灵衣{cid}", frozenset(t['name'] for t in lst)))
            s.stages = stages
            if cno in out:  # CN 优先，补齐 svt id
                out[cno].svt_ids |= s.svt_ids
            else:
                out[cno] = s
    return out


SERVANTS = load_servants()
SVT_TO_CNO = {}
for cno, s in SERVANTS.items():
    for sid in s.svt_ids:
        SVT_TO_CNO[sid] = cno

# Atlas 数据缺失、Mooncell 明确判定的补充名单（与 scripts/gen_trait_stats.py 的
# MOONCELL_SUPPLEMENT 保持一致，2026-08 按灵衣一览核验）
_EXTRA_TRAITS = {
    'hasCostume': [161, 346, 408, 437, 444],   # 土方岁三 / 莫里亚蒂(Ruler) / 耀星哈桑 / 但丁 / U-奥尔加玛丽
    'alignmentChaotic': [81],                  # 亨利·杰基尔＆海德：宝具变身后为混沌属性
}
for _t, _cnos in _EXTRA_TRAITS.items():
    for _c in _cnos:
        if _c in SERVANTS:
            SERVANTS[_c].base_traits = SERVANTS[_c].base_traits | {_t}


def align_cn(traits):
    p = [ALIGN_CN[n] for n in ('alignmentLawful', 'alignmentNeutral', 'alignmentChaotic') if n in traits]
    q = [ALIGN_CN[n] for n in ('alignmentGood', 'alignmentBalanced', 'alignmentEvil') if n in traits]
    if not p and not q:
        return ''
    return '·'.join(p + q)


# ---------------- 礼装条件解析 ----------------
def groups_of(fn):
    """返回 groups: [[(id, name), ...], ...]  外层 OR / 内层 AND"""
    groups = []
    for t in fn.get('functvals') or []:
        groups.append([(t.get('id'), t.get('name'))])
    for grp in (fn.get('script') or {}).get('overwriteTvals') or []:
        groups.append([(t.get('id'), t.get('name')) for t in grp])
    return groups


def clean_groups(groups):
    """trait 用 name；name 为 unknown / 纯数字时按 svtId 特指从者（记为 svt:<id>）"""
    out = []
    for g in groups:
        g2 = []
        for tid, name in g:
            if name and name != 'unknown' and not str(name).isdigit():
                g2.append(name)
            elif isinstance(tid, int) and tid > 10000:
                g2.append('svt:%d' % tid)   # svtId 量级，特指该从者
        if g2:
            out.append(g2)
    return out


def cond_text(groups):
    parts = []
    for g in groups:
        names = []
        for n in g:
            if n.startswith('svt:'):
                cno = SVT_TO_CNO.get(int(n[4:]))
                nm = SERVANTS[cno].name if cno else f'svtId {n[4:]}'
                names.append(f'特指从者「{nm}」')
            else:
                names.append(f'〔{trait_cn(n)}〕')
        t = '且'.join(names)
        if len(groups) > 1 and len(names) > 1:
            t = f'（{t}）'
        parts.append(t)
    return '或'.join(parts)


def match_servant(sv, groups):
    """返回满足的形态标签列表（空 = 不满足）"""
    hits = []
    for g in groups:
        svts = [int(n[4:]) for n in g if n.startswith('svt:')]
        traits = [n for n in g if not n.startswith('svt:')]
        if svts and not (sv.svt_ids & set(svts)):
            continue
        if not traits:
            if svts:
                hits.append('特指')
            continue
        if all(t in sv.base_traits for t in traits):
            hits.append('基础')
            continue
        for label, tset in sv.stages:
            if all(t in tset for t in traits):
                hits.append(label)
                break
    return hits


def collect_ces():
    """返回 {cno: {name, rarity, region, conds:[{detail, groups, unf, full, status}]}}"""
    ces = {}
    for region in ['CN', 'JP']:
        for fn in glob.glob(os.path.join(RAW_CE, region, '*.json')):
            try:
                d = json.load(open(fn))
            except Exception:
                continue
            cno = d.get('collectionNo')
            if cno is None:
                continue
            for s in d.get('skills') or []:
                for f in s.get('functions') or []:
                    if f.get('funcType') != 'servantFriendshipUp':
                        continue
                    groups = clean_groups(groups_of(f))
                    rate = (f.get('svals') or [{}])[0].get('RateCount')
                    pct = (rate / 10) if isinstance(rate, (int, float)) else None
                    if cno not in ces:
                        ces[cno] = {'name': d.get('name', ''), 'rarity': d.get('rarity', 0),
                                    'region': region, 'conds': []}
                    # 同条件去重（有些礼装重复列同 func）
                    key = (s.get('detail'), tuple(map(tuple, groups)))
                    if any((c['detail'], tuple(map(tuple, c['groups']))) == key for c in ces[cno]['conds']):
                        continue
                    ces[cno]['conds'].append({
                        'detail': s.get('detail', ''), 'groups': groups,
                        'pct': pct, 'status': s.get('strengthStatus'),
                    })
                    break
    return ces


CES = collect_ces()

# 收录范围（2026-11 用户定）：只做「按从者属性/经历归属」的羁绊礼装。
# 排除：按职阶限定的（2124 魔术师 / 2142 骑兵 / 2607 剑士）——职阶本身就能直接查，没有交叉筛选价值；
#       英灵逢魔 1973~1979（FSN从者 +10%，7 张同效果，实用度低）。
BOND_CE_IDS = [1949, 2020, 2052, 2209, 2233, 2437, 2509, 2583]
EXCLUDED_CE = {
    '按职阶限定（查职阶名单即可）': [2124, 2142, 2607],
    '英灵逢魔系列（FSN从者 +10%，7 张同效果）': [1973, 1974, 1975, 1976, 1977, 1978, 1979],
}
LIMITED = {k: v for k, v in CES.items() if k in BOND_CE_IDS and any(c['groups'] for c in v['conds'])}


def is_event(detail):
    return ('活动限定' in detail) or ('期間限定' in detail) or ('イベント' in detail) \
        or ('イベント期間限定' in detail)


GENERAL = {k: v for k, v in CES.items() if not any(c['groups'] for c in v['conds'])}
GENERAL_CN = {k: v for k, v in GENERAL.items() if v['region'] == 'CN' and not is_event(v['conds'][0]['detail'])}
GENERAL_CN_EVENT = {k: v for k, v in GENERAL.items() if v['region'] == 'CN' and is_event(v['conds'][0]['detail'])}
GENERAL_JP_ONLY = {k: v for k, v in GENERAL.items() if v['region'] == 'JP'}

# 拥有灵衣但 Atlas 未标 hasCostume 的从者（Mooncell 灵衣一览）
COSTUME_EXTRA = [161, 346, 408, 437, 444]

CE_NOTES = {
    1949: ['〔兽科从者〕= Atlas 特性 `havingAnimalsCharacteristics`，判定合并基础特性 + 灵基阶段/灵衣追加特性。'],
    2020: ['〔活在当下的人类〕= Atlas 特性 `livingHuman`，包含部分拟似从者、亚从者。'],
    2052: ['〔秩序且善〕= 同时拥有 `alignmentLawful`（秩序）与 `alignmentGood`（善）。'],
    2209: ['〔拥有灵衣之人〕= Atlas 特性 `hasCostume`。',
           'Atlas 未标注但确实拥有灵衣的 {n} 名已按 Mooncell 灵衣一览补充：{extra}。'],
    2233: ['〔秩序的女性〕= 同时拥有 `alignmentLawful`（秩序）与 `genderFemale`（女性）。'],
    2437: ['〔恶〕或〔星属性〕，满足任一即可；本礼装为国服未实装的日服礼装。'],
    2509: ['〔混沌〕且〔七骑士职阶〕= 同时拥有 `alignmentChaotic` 与 `standardClassServant`。',
           '另有特指条款：所罗门(#459) 无条件计入，因此达标数比「混沌且七骑士」特性人数多 1。',
           '补充：亨利·杰基尔＆海德(#81) 宝具变身后为混沌属性，按 Mooncell 计入。',
           '本礼装为国服未实装的日服礼装。'],
    2583: ['〔中立〕= Atlas 特性 `alignmentNeutral`；本礼装为国服未实装的日服礼装。'],
}

FOOTER = ('---\n\n*数据来源: [Atlas Academy API](https://api.atlasacademy.io) | '
          '游戏素材版权归 TYPE-MOON / FGO PROJECT 所有*\n')


def fmt_stars(r):
    return '★' * r if r else '—'


def members_of(cond):
    """返回 [(cno, stages)]，按 collectionNo"""
    res = []
    for cno, sv in SERVANTS.items():
        hits = match_servant(sv, cond['groups'])
        if hits:
            res.append((cno, hits))
    res.sort()
    return res


def render_ce(cno, info):
    lines = [f"# 羁绊礼装：No.{cno} {info['name']}", '']
    lines.append(f"> **图鉴编号**: {cno} | **星级**: {fmt_stars(info['rarity'])} | "
                 f"**服务器**: {'国服' if info['region']=='CN' else '日服（国服未实装）'}")
    lines.append('> **作用**: 关卡通关时的牵绊点数加成（仅对符合条件的从者生效）')
    lines.append('')
    per_cond = []
    for i, c in enumerate(info['conds']):
        head = '未满破效果' if (c['status'] or 0) < 99 else '最大解放效果'
        if len(info['conds']) == 1:
            head = '效果'
        lines.append(f'## {head}')
        lines.append('')
        lines.append(f"- **原文**: {c['detail']}")
        if c['groups']:
            lines.append(f"- **加成对象条件**: {cond_text(c['groups'])}")
        if c['pct'] is not None:
            lines.append(f"- **加成倍率**: {c['pct']:g}%")
        else:
            lines.append("- **加成倍率**: 见原文")
        lines.append('')
        per_cond.append(c)
    # 名单（按第一条件组）
    cond = per_cond[0]
    mem = members_of(cond)
    total = len(mem)
    jp = sum(1 for cno_, _ in mem if SERVANTS[cno_].region == 'JP')
    groups = collections.defaultdict(lambda: collections.defaultdict(list))
    for cno_, hits in mem:
        sv = SERVANTS[cno_]
        groups[sv.className][sv.rarity].append((cno_, hits, sv))
    cls_list = [c for c in CLASS_ORDER if c in groups] + [c for c in groups if c not in CLASS_ORDER]
    stars = sorted({r for cls in groups for r in groups[cls]}, reverse=True)
    lines.append('## 职阶 × 星级速查')
    lines.append('')
    lines.append('| 职阶 | ' + ' | '.join(fmt_stars(r) for r in stars) + ' | 合计 |')
    lines.append('|------|' + '|'.join(['------'] * (len(stars) + 1)) + '|')
    for cls in cls_list:
        cells = [str(len(groups[cls].get(r, []))) if groups[cls].get(r) else '·' for r in stars]
        lines.append(f"| {CLASS_CN.get(cls, cls)} | " + ' | '.join(cells) +
                     f" | {sum(len(v) for v in groups[cls].values())} |")
    lines.append(f"| **合计** | " + ' | '.join(
        str(sum(len(groups[c].get(r, [])) for c in groups)) for r in stars) + f" | {total} |")
    lines.append('')
    lines.append(f"## 达标从者（{total} 名{'，含 ' + str(jp) + ' 名日服限定*' if jp else ''}）")
    lines.append('')
    for cls in cls_list:
        n = sum(len(v) for v in groups[cls].values())
        lines.append(f"### {CLASS_CN.get(cls, cls)}（{n}）")
        lines.append('')
        for rar in sorted(groups[cls], reverse=True):
            for cno_, hits, sv in groups[cls][rar]:
                mark = ' *' if sv.region == 'JP' else ''
                note = ''
                if hits == ['特指']:
                    note = ' [特指条款]'
                elif hits and hits != ['基础']:
                    note = f" [仅部分形态：{'；'.join(hits[:3])}{' 等' + str(len(hits)) + '项' if len(hits) > 3 else ''}]"
                lines.append(f"- {fmt_stars(rar)} {sv.name}(#{cno_}){mark}{note}")
        lines.append('')
    # 备注
    lines.append('## 备注')
    lines.append('')
    lines.append('- 判定按从者的基础特性 + 灵基阶段/灵衣追加特性，任一形态满足即计入，并在条目后标注所需形态。')
    lines.append('- 带 `*` 为仅日服实装、国服尚未上线的从者。')
    for n in CE_NOTES.get(cno, []):
        if '{extra}' in n:
            extra = '、'.join(f"{SERVANTS[c].name}(#{c})" for c in COSTUME_EXTRA if c in SERVANTS)
            n = n.replace('{n}', str(len(COSTUME_EXTRA))).replace('{extra}', extra)
        lines.append(f'- {n}')
    lines.append('- 效果对象是符合上述条件的从者本人（依据效果文本），与礼装装备在谁身上无关。')
    lines.append('')
    lines.append(FOOTER)
    return '\n'.join(lines)


def render_index():
    lines = ['# 羁绊加成礼装索引', '']
    lines.append('> 用于快速反查「某张羁绊礼装能加成哪些从者」以及「某从者能吃到哪些羁绊礼装」。')
    lines.append('> 数据来自本地 Atlas 数据（CN 优先，JP 补充）。国服未实装的礼装标 `日服`。')
    lines.append('')
    lines.append('## 收录范围')
    lines.append('')
    lines.append(f"- **收录 {len(LIMITED)} 张**：按从者属性 / 经历限定的羁绊礼装（含 3 张日服未实装）。")
    lines.append('- **不收**按职阶限定的礼装（No.2124 魔术师 / No.2142 骑兵 / No.2607 剑士）：'
                 '职阶本身就是检索维度，直接查该职阶从者名单更有用。')
    lines.append('- **不收**英灵逢魔系列（No.1973~1979，〔Fate/stay night从者〕+10%，7 张同效果）：实用度低。')
    lines.append('')
    lines.append('## 一、限定条件型羁绊礼装')
    lines.append('')
    lines.append('| 编号 | 礼装 | 加成对象 | 未满破 | 满破 | 达标从者 | 服务器 |')
    lines.append('|------|------|----------|--------|------|----------|--------|')
    rows = []
    for cno, info in LIMITED.items():
        conds = sorted(info['conds'], key=lambda c: (c['status'] or 0))
        gtext = cond_text(conds[0]['groups'])
        unf = next((c['pct'] for c in conds if (c['status'] or 0) < 99), None)
        full = next((c['pct'] for c in conds if (c['status'] or 0) >= 99), None)
        n = len(members_of(conds[0]))
        rows.append((info['region'] != 'CN', cno, info, gtext, unf, full, n))
    rows.sort(key=lambda x: (x[0], x[1]))
    for _, cno, info, gtext, unf, full, n in rows:
        f_unf = f'{unf:g}%' if unf is not None else '—'
        f_full = f'{full:g}%' if full is not None else ('无满破变化' if unf is not None else '—')
        link = f"[{info['name']}](羁绊礼装：No.{cno} {info['name']}.md)"
        lines.append(f"| No.{cno} | {link} | {gtext} | {f_unf} | {f_full} | {n} | "
                     f"{'国服' if info['region']=='CN' else '日服'} |")
    lines.append('')
    lines.append('## 二、条件 → 礼装 反查')
    lines.append('')
    rev = collections.defaultdict(list)
    for cno, info in LIMITED.items():
        for c in info['conds']:
            t = cond_text(c['groups'])
            if f"No.{cno} {info['name']}" not in rev[t]:
                rev[t].append(f"No.{cno} {info['name']}")
    lines.append('| 加成对象 | 礼装 |')
    lines.append('|----------|------|')
    for t in sorted(rev):
        items = sorted(rev[t], key=lambda s: int(s.split()[0].split('.')[1]))
        lines.append(f"| {t} | {'；'.join(items)} |")
    lines.append('')
    lines.append(f'## 三、通用羁绊礼装总表（无特性限制，{len(GENERAL)} 张）')
    lines.append('')
    lines.append('> 这类礼装对队伍里任何从者都生效，用来填满剩余礼装位。')
    lines.append('')
    lines.append('| 编号 | 礼装 | 类型 | 未满破效果（原文） | 最大解放效果（原文） |')
    lines.append('|------|------|------|--------------------|----------------------|')

    def gen_type(cno, info):
        if info['region'] == 'JP':
            return '日服未实装'
        return '活动关卡限定' if is_event(info['conds'][0]['detail']) else '常驻通用'

    all_gen = sorted(GENERAL.items(),
                     key=lambda kv: (0 if kv[1]['region'] == 'CN' else 1,
                                     0 if not is_event(kv[1]['conds'][0]['detail']) else 1,
                                     kv[0]))
    for cno, info in all_gen:
        conds = sorted(info['conds'], key=lambda c: (c['status'] or 0))
        unf = next((c['detail'] for c in conds if (c['status'] or 0) < 99), conds[0]['detail'])
        full = next((c['detail'] for c in conds if (c['status'] or 0) >= 99), '—')
        lines.append(f"| No.{cno} | {info['name']} | {gen_type(cno, info)} | {unf} | {full} |")
    lines.append('')
    lines.append(f'> 构成：国服常驻通用 {len(GENERAL_CN)} 张 + 国服活动关卡限定 {len(GENERAL_CN_EVENT)} 张 '
                 f"+ 日服未实装 {len(GENERAL_JP_ONLY)} 张。日服那批在 `raw/craft-essences/CN/` 补齐后重跑脚本即会自动归位。")
    lines.append('')
    lines.append('> 注：No.99~108「英灵肖像」系列为固定值加成（每条 +50 牵绊点），非百分比。')
    lines.append('')
    lines.append('## 四、组队提示')
    lines.append('')
    lines.append('- 队伍 6 位 = 5 名自家从者 + 1 名助战，对应 6 个礼装位（助战自带的算 1 张）。')
    lines.append('- 效果文本的对象是「获得〔某特性〕的牵绊点数」，即判定跟随从者本身，与礼装装在谁身上无关。')
    lines.append('- 多张礼装能否叠加、有无上限，本地数据无法支撑，未做断言，以游戏内实测为准。')
    lines.append('- 刷某从者羁绊时：先用 `从者适配反查.md` 查他能吃到哪些条件礼装，剩下的礼装位放通用礼装（第三节）。')
    lines.append('')
    lines.append('## 检索用法')
    lines.append('')
    lines.append('- 「弓阶四星秩序善从者」→ 打开「羁绊礼装：No.2052 检查报告」，看「职阶 × 星级速查」表 ↗ 弓兵 × ★4。')
    lines.append('- 「某个从者能吃什么礼装」→ 打开 `从者适配反查.md` 搜从者名。')
    lines.append('- 命令行：`grep "摩根" entities/bond-ce/从者适配反查.md`。')
    lines.append('')
    lines.append(FOOTER)
    return '\n'.join(lines)


def render_reverse():
    lines = ['# 从者 → 羁绊礼装 反查', '']
    lines.append('> 按图鉴编号排序。列出每名从者能吃到哪些限定条件型羁绊礼装（取最大解放数值）。')
    lines.append('> 全体通用礼装（No.330 迦勒底午餐时光 等）对任何从者都生效，见 `index.md` 第三节。')
    lines.append('')
    # 条件组去重合并（如英灵逢魔 7 张同条件）
    cond_map = collections.OrderedDict()
    for cce, info in sorted(LIMITED.items()):
        pct = max((c['pct'] for c in info['conds'] if c['pct'] is not None), default=None)
        for c in info['conds']:
            key = tuple(tuple(g) for g in c['groups'])
            if key not in cond_map:
                cond_map[key] = {'text': cond_text(c['groups']), 'ces': [], 'pct': pct}
            if cce not in cond_map[key]['ces']:
                cond_map[key]['ces'].append(cce)
    lines.append('## 条件组一览')
    lines.append('')
    lines.append('| 加成对象 | 礼装编号 | 最大解放加成 |')
    lines.append('|----------|----------|--------------|')
    for key, v in cond_map.items():
        ces = v['ces']
        ids = f"No.{ces[0]}~{ces[-1]}（{len(ces)}张）" if len(ces) > 1 else f"No.{ces[0]}"
        pct = f"+{v['pct']:g}%" if v['pct'] is not None else '见原文'
        lines.append(f"| {v['text']} | {ids} | {pct} |")
    lines.append('')
    lines.append('## 逐从者反查')
    lines.append('')
    lines.append('| 从者 | 职阶 | 星级 | 可吃到的限定礼装 |')
    lines.append('|------|------|------|------------------|')
    rows = []
    for cno, sv in SERVANTS.items():
        hits = []
        for key, v in cond_map.items():
            groups = [list(g) for g in key]
            h = match_servant(sv, groups)
            if h:
                ces = v['ces']
                ids = f"No.{ces[0]}~{ces[-1]}" if len(ces) > 1 else f"No.{ces[0]}"
                pct = f"+{v['pct']:g}%" if v['pct'] is not None else ''
                suffix = ''
                if h != ['基础'] and h != ['特指']:
                    suffix = f"〔仅{'、'.join(h[:2])}{'等' if len(h) > 2 else ''}〕"
                hits.append(f"{v['text']} {pct}（{ids}）{suffix}")
        rows.append((cno, sv, hits))
    for cno, sv, hits in sorted(rows):
        mark = ' *' if sv.region == 'JP' else ''
        lines.append(f"| {sv.name}(#{cno}){mark} | {CLASS_CN.get(sv.className, sv.className)} | "
                     f"{fmt_stars(sv.rarity)} | {'；'.join(hits) if hits else '—'} |")
    lines.append('')
    lines.append('> 带 `*` 为仅日服实装、国服尚未上线的从者。')
    lines.append('')
    lines.append(FOOTER)
    return '\n'.join(lines)


def main():
    os.makedirs(OUT, exist_ok=True)
    # 清理旧生成文件，避免改名残留
    for f in glob.glob(os.path.join(OUT, '羁绊礼装：No.*.md')):
        os.remove(f)
    made = []
    for cno, info in LIMITED.items():
        content = render_ce(cno, info)
        fn = f"羁绊礼装：No.{cno} {info['name']}.md"
        open(os.path.join(OUT, fn), 'w').write(content)
        made.append(fn)
    open(os.path.join(OUT, 'index.md'), 'w').write(render_index())
    open(os.path.join(OUT, '从者适配反查.md'), 'w').write(render_reverse())
    print(f"限定礼装 {len(LIMITED)} 张，通用(国服) {len(GENERAL_CN)} 张，国服活动限定 {len(GENERAL_CN_EVENT)} 张，日服通用 {len(GENERAL_JP_ONLY)} 张，从者 {len(SERVANTS)} 名")
    for f in made:
        print(' ', f)


if __name__ == '__main__':
    main()
