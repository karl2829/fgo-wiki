#!/usr/bin/env python3
"""生成 FGO 特攻一览 MD（从者/礼装/纹章 三大项）

用法: python3 gen_tokou_overview.py
输出: ~/fgo-wiki/entities/tokou/特攻一览.md

数据源:
- 从者: raw/servants/{CN,JP}/*.json (宝具伤害特攻 svals.Target) + entities/servants/CN|JP/*.md (技能特攻状态)
- 礼装: raw/craft-essences/CN/*.json (skills detail 含〔X〕特攻)
- 纹章: entities/command-codes/*.md (效果文本含〔X〕特攻)
"""
import json, os, glob, re, collections

FGO_WIKI = os.path.expanduser('~/fgo-wiki')
OUT_DIR = os.path.join(FGO_WIKI, 'entities', 'tokou')

# ---------- trait id -> 中文 ----------
with open('/tmp/cn_trait_dict.json') as f:
    trait_dict = json.load(f)  # id(str) -> en
with open(os.path.join(FGO_WIKI, 'data/trait_translations.json')) as f:
    tt = json.load(f)

EXTRA_CN = {
    'genderMale': '男性', 'genderFemale': '女性',
    'attributeHuman': '人', 'attributeEarth': '地', 'attributeSky': '天',
    'attributeStar': '星', 'attributeBeast': '兽',
    'alignmentLawful': '秩序', 'alignmentChaotic': '混沌', 'alignmentNeutral': '中立',
    'alignmentGood': '善', 'alignmentEvil': '恶', 'alignmentBalanced': '中庸',
    'classSaber': '剑士', 'classArcher': '弓兵', 'classLancer': '枪兵',
    'classRider': '骑兵', 'classCaster': '魔术师', 'classAssassin': '暗杀者',
    'classBerserker': '狂战士', 'classRuler': '裁定者', 'classAvenger': '复仇者',
    'classAlterEgo': '他人格', 'classMoonCancer': '月之癌', 'classForeigner': '降临者',
    'classPretender': 'Pretender', 'classShielder': '盾兵',
    'standardClassServant': '七骑士的从者', 'saberClassServant': '剑士职阶从者',
    'superGiant': '超巨大', 'giant': '巨人', 'threatToHumanity': '人类的威胁',
    'buffCharm': '魅惑', 'buffBurn': '灼伤', 'buffCurse': '诅咒', 'buffPoison': '毒',
    'buffBound': '束缚', 'buffDefUp': '防御力提升', 'buffDeathResistDown': '即死耐性下降',
    'skillSeal': '技能封印', 'riding': '骑乘技能', 'undead': '死灵', 'oni': '鬼',
    'weakToEnumaElish': '被EA特攻', 'brynhildsBeloved': '所爱之人',
    'arthur': '亚瑟', 'skyOrEarthServant': '天或地之力从者',
    'weakPointsRevealed': '弱点暴露', 'notProtectedByBBDubai': '非保护对象',
    'humanoid': '人型', 'divine': '神性', 'demonic': '魔性', 'dragon': '龙',
    'king': '王', 'saberface': '阿尔托莉雅脸', 'roman': '罗马',
    'mechanical': '机械', 'fae': '妖精', 'divineSpirit': '神灵',
    'demonicBeastServant': '魔兽型从者', 'wildbeast': '猛兽',
    'havingAnimalsCharacteristics': '兽科从者', 'livingHuman': '活在当下的人类',
    'hasCostume': '持有灵衣之人', 'existenceOutsideTheDomain': '领域外生命',
    'childServant': '孩童从者', 'fairyTaleServant': '童话从者',
    'groupServant': '群体从者', 'servant': '从者', 'human': '人类',
    'skyOrEarthExceptPseudoAndDemiServant': '天或地之力从者(除拟似与亚从者)',
}

def tid_to_cn(tid):
    en = trait_dict.get(str(tid), '')
    if en in tt:
        return tt[en]
    if en in EXTRA_CN:
        return EXTRA_CN[en]
    return en or f'#{tid}'

DAMAGE_TOKOU = {'damageNpIndividual', 'damageNpIndividualSum',
                'damageNpStateIndividualFix', 'damageNpAndOrCheckIndividuality'}

# ---------- 1. 从者特攻 ----------
def scan_servant_md(path):
    """从从者 MD 提取特攻（宝具伤害特攻 + 技能特攻状态），与知识库渲染一致"""
    out = []
    with open(path) as f:
        content = f.read()
    if '特攻' not in content:
        return out
    # 宝具特攻: **对〔X〕特攻**（含 <Over Charge时特攻威力提升> 后缀）
    for m in re.finditer(r'\*\*对〔([^〕]+)〕特攻', content):
        out.append(('宝具', m.group(1).strip()))
    # 技能特攻状态: 〔X〕...特攻状态
    for m in re.finditer(r'〔([^〕]+)〕', content):
        tail = content[m.end():m.end() + 30]
        if '特攻状态' in tail:
            out.append(('技能', m.group(1).strip()))
    return out

svt_data = {}  # cno -> {name, region, className, items:[(src, owner, target)]}
for region in ['CN', 'JP']:
    for fn in glob.glob(os.path.join(FGO_WIKI, 'raw/servants', region, '*.json')):
        with open(fn) as f:
            d = json.load(f)
        cno = d.get('collectionNo')
        if cno is None:
            continue
        if cno in svt_data and region == 'JP':
            continue
        items = []
        mdpath = os.path.join(FGO_WIKI, 'entities/servants', region, os.path.basename(fn).replace('.json', '.md'))
        if os.path.exists(mdpath):
            items = scan_servant_md(mdpath)
        if items:
            svt_data[cno] = {'name': d.get('name', ''), 'region': region,
                             'className': d.get('className', ''), 'items': items}

# 去重 + 按从者聚合
svt_rows = []  # (cno, name, region, [(src, owner, target)])
for cno in sorted(svt_data.keys()):
    v = svt_data[cno]
    uniq = []
    seen = set()
    for src, target in v['items']:
        key = (src, target)
        if key in seen:
            continue
        seen.add(key)
        uniq.append((src, target))
    svt_rows.append((cno, v['name'], v['region'], uniq))

# ---------- 2. 礼装特攻 ----------
ce_rows = []
ce_pat = re.compile(r'〔([^〕]+)〕')
for fn in glob.glob(os.path.join(FGO_WIKI, 'raw/craft-essences', 'CN', '*.json')):
    with open(fn) as f:
        d = json.load(f)
    targets = set()
    for sk in d.get('skills', []):
        detail = sk.get('detail', '') or ''
        if '特攻' not in detail:
            continue
        for m in ce_pat.finditer(detail):
            # 取〔X〕之后 20 字符内是否出现"特攻"
            tail = detail[m.end():m.end() + 20]
            if '特攻' in tail:
                targets.add(m.group(1).strip())
    if targets:
        ce_rows.append((d.get('collectionNo'), d.get('name', ''), sorted(targets)))

# ---------- 3. 纹章特攻 ----------
cc_rows = []
cc_pat = re.compile(r'〔([^〕]+)〕')
for fn in glob.glob(os.path.join(FGO_WIKI, 'entities/command-codes', '*.md')):
    with open(fn) as f:
        content = f.read()
    if '特攻' not in content:
        continue
    m_id = re.search(r'\*\*ID\*\*: (\d+)', content)
    m_name = re.search(r'^# (.+)$', content, re.M)
    targets = set()
    for m in cc_pat.finditer(content):
        tail = content[m.end():m.end() + 20]
        if '特攻' in tail:
            targets.add(m.group(1).strip())
    if targets:
        cc_rows.append((m_id.group(1) if m_id else '?', m_name.group(1).strip() if m_name else '?', sorted(targets)))

# ---------- 渲染 ----------
def render():
    os.makedirs(OUT_DIR, exist_ok=True)
    L = []
    L.append('# FGO 特攻一览')
    L.append('')
    L.append('> 统计范围：从者（宝具/技能）、概念礼装、指令纹章')
    L.append('> 数据来源：本地知识库 raw/servants + entities MD')
    L.append('')
    L.append('## 统计概览')
    L.append('')
    L.append('| 类别 | 数量 |')
    L.append('|------|------|')
    cn_svt = sum(1 for _, _, r, _ in svt_rows if r == 'CN')
    jp_svt = sum(1 for _, _, r, _ in svt_rows if r == 'JP')
    L.append(f'| 特攻从者 | {len(svt_rows)}（CN {cn_svt} + JP-only {jp_svt}） |')
    L.append(f'| 特攻礼装 | {len(ce_rows)} |')
    L.append(f'| 特攻纹章 | {len(cc_rows)} |')
    L.append('')
    L.append('## 一、从者特攻')
    L.append('')
    L.append(f'共 {len(svt_rows)} 名从者拥有特攻（宝具伤害特攻 / 技能特攻状态）。')
    L.append('')
    for cno, name, region, items in svt_rows:
        jp = ' *' if region == 'JP' else ''
        L.append(f'### #{cno} {name}{jp}')
        L.append('')
        # 按来源分组展示
        for src in ['宝具', '技能']:
            sub = [it for it in items if it[0] == src]
            if not sub:
                continue
            targets = sorted(set(t for _, t in sub))
            L.append(f'- **{src}特攻**：' + '、'.join(f'〔{t}〕' for t in targets))
        L.append('')
    L.append('## 二、礼装特攻')
    L.append('')
    L.append(f'共 {len(ce_rows)} 张礼装拥有特攻效果。')
    L.append('')
    L.append('| 图鉴编号 | 名称 | 特攻目标 |')
    L.append('|----------|------|----------|')
    for cno, name, targets in ce_rows:
        L.append(f'| {cno} | {name} | {"、".join("〔"+t+"〕" for t in targets)} |')
    L.append('')
    L.append('## 三、纹章特攻')
    L.append('')
    L.append(f'共 {len(cc_rows)} 枚纹章拥有特攻效果。')
    L.append('')
    L.append('| ID | 名称 | 特攻目标 |')
    L.append('|----|------|----------|')
    for cid, name, targets in cc_rows:
        L.append(f'| {cid} | {name} | {"、".join("〔"+t+"〕" for t in targets)} |')
    L.append('')
    L.append('---')
    L.append('')
    L.append('*数据来源: [Atlas Academy API](https://api.atlasacademy.io) | 游戏素材版权归 TYPE-MOON / FGO PROJECT 所有*')
    L.append('')
    path = os.path.join(OUT_DIR, '特攻一览.md')
    with open(path, 'w') as f:
        f.write('\n'.join(L))
    print(f'已生成: {path}')
    print(f'从者 {len(svt_rows)} / 礼装 {len(ce_rows)} / 纹章 {len(cc_rows)}')

if __name__ == '__main__':
    render()
