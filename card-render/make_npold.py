# -*- coding: utf-8 -*-
"""生成「主题卡 + 旧版宝具区块排版」对照版模板。

只改两处：①卡片高度改为自适应 ②宝具区效果条目换成旧版「描述行 + 独立数值框」结构。
其余（立绘、头部、技能行、页脚、配色）与定版模板逐字一致。
"""
import pathlib
import re

ROOT = pathlib.Path("/home/mila/card-render")
src = (ROOT / "templates/dark_servant_card.html").read_text(encoding="utf-8")
h = src

# ① 卡片高度自适应（宝具块变高后不能写死 1350）
h = h.replace(".card{width:1080px;height:1350px;", ".card{width:1080px;min-height:1350px;")

# ② 追加旧版数值框样式
extra_css = """
/* ---------- 旧版宝具区块：每个效果自带一排独立数值框 ---------- */
.eb{margin-top:15px}
.eb-d{display:flex;align-items:baseline;gap:10px}
.eb-d .n{font-size:24px;color:var(--text-1)}
.eb-d .h{font-size:15px;color:var(--gold-mid)}
.eb-v{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin-top:9px}
.vb{height:52px;display:flex;align-items:center;justify-content:center;border-radius:7px;
  background:rgba(11,18,32,.50);border:1px solid rgba(255,255,255,.10);
  color:var(--num);font-size:24px;font-variant-numeric:tabular-nums;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.05)}
.vb.on{background:rgba(201,162,39,.16);border-color:rgba(201,162,39,.60);color:var(--gold-hi);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.10), 0 0 14px rgba(201,162,39,.12)}
"""
h = h.replace("</style></head><body>", extra_css + "</style></head><body>")

NP = """<section class="np">
  <div class="np-head">
    <div class="goldbar"></div>
    <div class="t">宝　具</div>
    <div class="dot"></div>
    <div class="stamp">N O B L E&nbsp;&nbsp;P H A N T A S M</div>
    <div class="spacer"></div>
    <div class="np-rule"></div>
    <div class="np-mark">N P</div>
  </div>
  <div class="name-row">
    <div>
      <div class="np-name">誓约胜利之剑</div>
      <div class="np-sub">Excalibur　／　約束された勝利の剣</div>
    </div>
    <div class="rank"><span class="rk-lb">R A N K</span><span class="rk-v">A++</span></div>
  </div>
  <div class="chips">
    <div class="chip c-buster">Buster</div>
    <div class="chip c-blue">对城宝具</div>
    <div class="chip c-ghost">全体攻击</div>
  </div>
  <div class="div-weak"></div>

  <div class="eb">
    <div class="eb-d"><span class="n">对敌方全体发动强大的攻击</span><span class="h">〈宝具升级效果提升〉</span></div>
    <div class="eb-v">
      <div class="vb">400%</div><div class="vb">500%</div><div class="vb on">550%</div>
      <div class="vb">575%</div><div class="vb">600%</div>
    </div>
  </div>

  <div class="eb">
    <div class="eb-d"><span class="n">自身的宝具值增加</span><span class="h">〈过量充能时效果提升〉</span></div>
    <div class="eb-v">
      <div class="vb on">20%</div><div class="vb">27.5%</div><div class="vb">35%</div>
      <div class="vb">42.5%</div><div class="vb">50%</div>
    </div>
  </div>

  <div class="npbar">
    <span class="lb">NP</span>
    <div class="track"><div class="fill"></div></div>
    <span class="pct">100%</span>
  </div>
</section>"""

new, n = re.subn(r'<section class="np">.*?</section>', NP, h, count=1, flags=re.S)
assert n == 1, "没找到宝具区"
out = ROOT / "templates/dark_servant_card_npold.html"
out.write_text(new, encoding="utf-8")
print("written", out, len(new))
