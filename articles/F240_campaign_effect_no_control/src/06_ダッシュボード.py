"""施策効果の報告ダッシュボード（1枚の静的 HTML）と、その画面（図6）を作る。
架空の会社「なにわステイ（架空の宿泊チェーン）」の社内向けという設定。数字は公的統計（大阪府全体）から。"""
import json
from pathlib import Path
import pandas as pd

B = Path(__file__).resolve().parents[1]; R = B / "results"; D = B / "dashboard"; D.mkdir(exist_ok=True)
o = json.load(open(R / "main.json"))
S = pd.read_csv(R / "C_sc_path.csv", parse_dates=[0], index_col=0)
M = pd.read_csv(R / "M_monthly.csv", parse_dates=[0], index_col=0)
P = pd.read_csv(R / "D_placebo_space.csv")
data = {
    "dates": [d.strftime("%Y-%m") for d in S.index],
    "actual": [round(v / 1e4, 1) for v in S.actual], "synth": [round(v / 1e4, 1) for v in S.synth],
    "months": [d.strftime("%Y-%m") for d in M.index],
    "eff": [round(v * 100, 1) for v in M.eff_pct], "persons": [round(v / 1e4, 1) for v in M.persons],
}
sc = o["C_sc"][0]
eff = sc["expo_eff"] * 100; persons = sc["persons"] / 1e4
variants = [(c["label"], c["expo_eff"] * 100) for c in o["C_sc"][:4]]
lo_v = min(v for _, v in variants); hi_v = max(v for _, v in variants)
pl = o["D_placebo_space"]; pt = o["E_placebo_time"]
html = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>施策効果レポート（架空）</title>
<style>
body{{font-family:"Noto Sans CJK JP","Hiragino Sans",sans-serif;margin:0;background:#f5f6f8;color:#222}}
header{{background:#1f3b57;color:#fff;padding:14px 22px}} header h1{{font-size:20px;margin:0}} header p{{margin:4px 0 0;font-size:12px;opacity:.85}}
.wrap{{padding:16px 22px;display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}
.card{{background:#fff;border-radius:8px;padding:12px 14px;box-shadow:0 1px 3px rgba(0,0,0,.1)}}
.k{{font-size:12px;color:#666}} .v{{font-size:26px;font-weight:700;margin-top:4px}} .s{{font-size:11px;color:#888;margin-top:2px}}
.wide{{grid-column:span 3}} .side{{grid-column:span 1}} .full{{grid-column:span 4}}
table{{border-collapse:collapse;width:100%;font-size:12px}} td,th{{border-bottom:1px solid #eee;padding:4px 6px;text-align:right}} th:first-child,td:first-child{{text-align:left}}
.ok{{color:#1e7d32}} .ng{{color:#c0392b}} .note{{font-size:12px;line-height:1.6}}
</style></head><body>
<header><h1>万博期間の宿泊需要：施策効果レポート（2025年4〜10月）</h1>
<p>架空の宿泊チェーン「なにわステイ」の社内向けの例。数字は観光庁「宿泊旅行統計調査」の大阪府全体の日本人延べ宿泊者数から計算（自社データではない）</p></header>
<div class="wrap">
<div class="card"><div class="k">期間中の増加（合成対照）</div><div class="v">+{eff:.1f}%</div><div class="s">条件を変えると +{lo_v:.1f}〜+{hi_v:.1f}%</div></div>
<div class="card"><div class="k">増えた宿泊（7か月の合計）</div><div class="v">約{persons:.0f}万人泊</div><div class="s">実際 − 合成の大阪</div></div>
<div class="card"><div class="k">場所のプラセボ（外れの比）</div><div class="v">{pl['osaka_rank_ratio']}位 / {pl['n']}</div><div class="s">偶然でこの順位になる確率 約{pl['p_ratio']*100:.0f}%</div></div>
<div class="card"><div class="k">時期のプラセボ（2024年4〜10月）</div><div class="v">{pt['sc_eff']*100:+.1f}%</div><div class="s">万博のない年はほぼ0 → 方法は過大に出ていない</div></div>
<div class="card wide"><div class="k">実際と合成の大阪（万人泊／月）</div><canvas id="c1" width="900" height="270"></canvas></div>
<div class="card side"><div class="k">月ごとの増加</div><table><tr><th>月</th><th>増加</th><th>万人泊</th></tr>
{''.join(f"<tr><td>{m}</td><td class={'ok' if e>=0 else 'ng'}>{e:+.1f}%</td><td>{p:+.1f}</td></tr>" for m,e,p in zip(data['months'],data['eff'],data['persons']))}
</table></div>
<div class="card full note"><b>読み方</b>：「前年同月比 +12.9%」は景気や旅行全体の動きも含む数字。合成対照は、ほかの都道県の組み合わせで「万博がなかった大阪」を作り、その差を施策の効果とみる。
<b>判断</b>：期間中の増加ははっきりしている（9月が最大）。閉幕後の11〜12月はマイナスで、需要の前倒しの可能性がある（推測）。外国人の宿泊は別の要因が大きく、この方法では判断しない。</div>
</div>
<script>
const D={json.dumps(data, ensure_ascii=False)};
const c=document.getElementById('c1'),x=c.getContext('2d');const W=c.width,H=c.height,L=50,Rr=10,T=10,Bt=30;
const vals=D.actual.concat(D.synth);const mn=Math.min(...vals)*0.97,mx=Math.max(...vals)*1.02;
const X=i=>L+(W-L-Rr)*i/(D.dates.length-1),Y=v=>T+(H-T-Bt)*(1-(v-mn)/(mx-mn));
const i0=D.dates.indexOf('2025-04'),i1=D.dates.indexOf('2025-10');
x.fillStyle='#f6d5d1';x.fillRect(X(i0)-8,T,X(i1)-X(i0)+16,H-T-Bt);
x.strokeStyle='#ccc';x.fillStyle='#666';x.font='11px sans-serif';
for(let k=0;k<5;k++){{const v=mn+(mx-mn)*k/4;x.beginPath();x.moveTo(L,Y(v));x.lineTo(W-Rr,Y(v));x.stroke();x.fillText(v.toFixed(0),8,Y(v)+4);}}
D.dates.forEach((d,i)=>{{if(d.endsWith('-01')||d.endsWith('-07'))x.fillText(d,X(i)-20,H-10);}});
function line(a,col,dash){{x.strokeStyle=col;x.lineWidth=2.2;x.setLineDash(dash);x.beginPath();a.forEach((v,i)=>i?x.lineTo(X(i),Y(v)):x.moveTo(X(i),Y(v)));x.stroke();x.setLineDash([]);}}
line(D.synth,'#2c6fbb',[6,4]);line(D.actual,'#c0392b',[]);
x.fillStyle='#c0392b';x.fillText('実際の大阪府',L+10,T+14);x.fillStyle='#2c6fbb';x.fillText('合成の大阪（ほかの都道県の組み合わせ）',L+100,T+14);
</script></body></html>"""
(D / "index.html").write_text(html, encoding="utf-8")

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 760}, device_scale_factor=1.5)
    pg.goto((D / "index.html").as_uri()); pg.wait_for_timeout(500)
    pg.screenshot(path=str(B / "figures/fig6_dashboard.png"), full_page=True); b.close()
print("ok")
