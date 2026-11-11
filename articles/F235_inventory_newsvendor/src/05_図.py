# 05 図（4枚）とダッシュボード（HTML）
import json, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib import font_manager
for p in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in p: font_manager.fontManager.addfont(p)
plt.rcParams["font.family"] = "Noto Sans CJK JP"; plt.rcParams["axes.spines.top"] = False; plt.rcParams["axes.spines.right"] = False
f = pd.read_csv("data/forecasts_h1to3.csv"); g = f[(f.h == 1) & ~f.コロナ期]
A = pd.read_csv("results/A_summary_h1.csv"); B = pd.read_csv("results/B_calibration_h1.csv"); B2 = pd.read_csv("results/B2_calibration_pooled_h1.csv")
COL = {"季節ナイーブ": "#9e9e9e", "ETS": "#1f77b4", "SARIMA": "#d62728"}

# 図1 外れの分布
fig, ax = plt.subplots(figsize=(9, 4.8)); bins = np.linspace(-12, 12, 49)
for m in ["季節ナイーブ", "SARIMA"]:
    e = (g[g.モデル == m].比 - 1) * 100
    ax.hist(e, bins=bins, alpha=.5, color=COL[m], label=f"{m}（平均 {e.mean():+.1f}%、90%点 {np.quantile(e,.9):+.1f}%）")
    ax.axvline(np.quantile(e, .9), color=COL[m], ls="--", lw=1.2)
ax.axvline(0, color="#333", lw=1); ax.set_xlabel("実績が予測より何%多かったか（1か月先、＋は足りない側）"); ax.set_ylabel("月の数（6業態×起点）")
ax.set_title("図1　予測の外れの分布：「去年と同じ」は足りない側に偏る（点線は90%点）", loc="left", fontsize=12)
ax.legend(fontsize=9, frameon=False); fig.tight_layout(); fig.savefig("figures/fig1_error_dist.png", dpi=150); plt.close()

# 図2 決め方ごとの損（SARIMA）
ORDER = ["点予測そのまま", "一律＋5%", "正規近似の安全在庫", "過去の外れの分位点", "SARIMA の80%区間の上端"]
CM = {"点予測そのまま": "#9e9e9e", "一律＋5%": "#ff9800", "正規近似の安全在庫": "#1f77b4", "過去の外れの分位点": "#d62728", "SARIMA の80%区間の上端": "#8e24aa"}
x = A[A.モデル == "SARIMA"]; fig, ax = plt.subplots(figsize=(9, 4.8))
for k in ORDER:
    y = x[x.決め方 == k].sort_values("ratio"); ax.plot(y.ratio.astype(int).astype(str), y.損, marker="o", lw=2 if k == "過去の外れの分位点" else 1.3, color=CM[k], label=k)
ax.set_xlabel("足りない1単位の損 ÷ 余る1単位の損（例として置いた比）"); ax.set_ylabel("損（需要100あたり、余る1単位の損＝1）")
ax.set_title("図2　発注量の決め方ごとの損（SARIMA の1か月先予測、2018〜2024年の月）", loc="left", fontsize=12)
ax.legend(fontsize=9, frameon=False); fig.tight_layout(); fig.savefig("figures/fig2_cost_by_method.png", dpi=150); plt.close()

# 図3 目標と実際のサービス率
fig, ax = plt.subplots(figsize=(7.5, 5.2)); s = B[B.モデル == "SARIMA"]
for k, c in [("正規近似の安全在庫", "#1f77b4"), ("過去の外れの分位点", "#d62728")]:
    y = s[s.決め方 == k]; ax.plot(y.tau * 100, y.サービス率 * 100, marker="o", color=c, label=f"{k}（業態ごと）")
y = B2[B2.モデル == "SARIMA"]; ax.plot(y.tau * 100, y.サービス率 * 100, marker="s", color="#2e7d32", label="過去の外れの分位点（6業態まとめて）")
ax.plot([50, 95], [50, 95], color="#333", ls=":", lw=1, label="目標どおり")
ax.set_xlabel("目標のサービス率（欠品しない月の割合、%）"); ax.set_ylabel("実際に欠品しなかった月の割合（%）")
ax.set_title("図3　目標どおりに欠品を防げたか（SARIMA）", loc="left", fontsize=12); ax.legend(fontsize=9, frameon=False)
fig.tight_layout(); fig.savefig("figures/fig3_calibration.png", dpi=150); plt.close()

# 図4 サービス率と余りのトレードオフ（予測の良さで曲線が動く）
fig, ax = plt.subplots(figsize=(9, 4.8)); q = B[B.決め方 == "過去の外れの分位点"]
for m in ["季節ナイーブ", "ETS", "SARIMA"]:
    y = q[q.モデル == m].sort_values("tau"); ax.plot(y.余り, y.サービス率 * 100, marker="o", color=COL[m], label=m)
    for _, r in y[y.tau.isin([0.5, 0.9])].iterrows(): ax.annotate(f"目標{int(r.tau*100)}%", (r.余り, r.サービス率 * 100), fontsize=8, xytext=(4, -10), textcoords="offset points", color=COL[m])
ax.set_xlabel("余った在庫（需要100あたり、平均）"); ax.set_ylabel("欠品しなかった月の割合（%）")
ax.set_title("図4　欠品を減らすほど余りが増える：予測が良いほど同じ余りで欠品が少ない", loc="left", fontsize=12)
ax.legend(fontsize=9, frameon=False); fig.tight_layout(); fig.savefig("figures/fig4_tradeoff.png", dpi=150); plt.close()

# ダッシュボード（HTML 1枚、JS で倍率を計算）
past = {ty: sorted(np.round(x.sort_values("対象月").比.values, 5).tolist()) for ty, x in g[g.モデル == "SARIMA"].groupby("業態")}
last = g[g.モデル == "SARIMA"].sort_values("起点").groupby("業態").tail(1)[["業態", "対象月", "予測"]]
bt = A[A.モデル == "SARIMA"][["決め方", "ratio", "損", "サービス率"]].round(3).to_dict("records")
D = {"past": past, "last": last.round(0).to_dict("records"), "bt": bt}
html = """<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>発注の倍率ダッシュボード（例）</title>
<style>body{font-family:'Noto Sans CJK JP',sans-serif;margin:24px;color:#222;background:#fff}h1{font-size:20px;margin:0 0 4px}
.note{color:#666;font-size:12px}.row{display:flex;gap:16px;margin-top:14px}.card{border:1px solid #ddd;border-radius:8px;padding:12px 16px;flex:1}
.big{font-size:30px;font-weight:bold;color:#d62728}table{border-collapse:collapse;font-size:13px;width:100%}td,th{border-bottom:1px solid #eee;padding:4px 6px;text-align:right}th:first-child,td:first-child{text-align:left}
label{font-size:14px;margin-right:12px}</style></head><body>
<h1>発注の倍率ダッシュボード（架空の小売チェーンの例）</h1>
<div class="note">商業動態統計の業態別販売額を「架空のチェーンの需要」とみなした練習です。損の比は例として置く値で、実在の会社の費用ではありません。</div>
<div class="row"><div><label>業態 <select id="ty"></select></label>
<label>足りない損 ÷ 余る損 <input id="r" type="range" min="1" max="19" step="1" value="9"> <b id="rv">9</b></label></div></div>
<div class="row"><div class="card"><div>目標のサービス率</div><div class="big" id="tau"></div><div class="note">= 足りない損 ÷（足りない損＋余る損）</div></div>
<div class="card"><div>発注の倍率（予測 ×）</div><div class="big" id="mul"></div><div class="note">過去の外れ（実績÷予測）の、目標のサービス率の点</div></div>
<div class="card"><div>次の月の発注量の目安</div><div class="big" id="q"></div><div class="note" id="qn"></div></div></div>
<div class="row"><div class="card"><div><b>過去の外れの分布</b>（SARIMA・1か月先、赤線が倍率）</div><canvas id="cv" width="520" height="200"></canvas></div>
<div class="card"><div><b>過去の検証：決め方ごとの損とサービス率</b>（SARIMA、6業態）</div><table id="bt"></table></div></div>
<script>const D=__DATA__;
const ty=document.getElementById('ty'),r=document.getElementById('r');Object.keys(D.past).forEach(k=>{const o=document.createElement('option');o.textContent=k;ty.appendChild(o)});
function qt(a,p){const s=[...a].sort((x,y)=>x-y),h=(s.length-1)*p,l=Math.floor(h);return s[l]+(s[Math.min(l+1,s.length-1)]-s[l])*(h-l)}
function draw(){const k=ty.value,R=+r.value,t=R/(R+1),a=D.past[k],m=qt(a,t),L=D.last.find(x=>x['業態']==k);
document.getElementById('rv').textContent=R;document.getElementById('tau').textContent=(t*100).toFixed(0)+'%';
document.getElementById('mul').textContent='×'+m.toFixed(3);document.getElementById('q').textContent=Math.round(L['予測']*m/100).toLocaleString()+'億円';
document.getElementById('qn').textContent=L['対象月']+' の予測 '+Math.round(L['予測']/100).toLocaleString()+'億円 × 倍率（業態全体の規模。例）';
const c=document.getElementById('cv').getContext('2d');c.clearRect(0,0,520,200);const lo=0.9,hi=1.1,nb=40,cnt=Array(nb).fill(0);a.forEach(v=>{const i=Math.min(nb-1,Math.max(0,Math.floor((v-lo)/(hi-lo)*nb)));cnt[i]++});
const mx=Math.max(...cnt);cnt.forEach((n,i)=>{c.fillStyle='#bbb';c.fillRect(20+i*12,170-n/mx*150,10,n/mx*150)});
const X=v=>20+(v-lo)/(hi-lo)*480;c.strokeStyle='#d62728';c.lineWidth=2;c.beginPath();c.moveTo(X(m),10);c.lineTo(X(m),170);c.stroke();
c.strokeStyle='#333';c.lineWidth=1;c.beginPath();c.moveTo(X(1),10);c.lineTo(X(1),170);c.stroke();c.fillStyle='#333';c.font='11px sans-serif';
[0.9,0.95,1,1.05,1.1].forEach(v=>c.fillText(v.toFixed(2),X(v)-12,188));
const rr=[1,2,4,9,19].includes(R)?R:[1,2,4,9,19].reduce((p,q)=>Math.abs(q-R)<Math.abs(p-R)?q:p);
let h='<tr><th>決め方（比 '+rr+'）</th><th>損</th><th>欠品しない月</th></tr>';D.bt.filter(x=>x.ratio==rr).sort((x,y)=>x['損']-y['損']).forEach(x=>{h+='<tr><td>'+x['決め方']+'</td><td>'+x['損'].toFixed(1)+'</td><td>'+(x['サービス率']*100).toFixed(0)+'%</td></tr>'});
document.getElementById('bt').innerHTML=h}
ty.onchange=draw;r.oninput=draw;ty.value='スーパー';draw();</script></body></html>"""
open("dashboard/index.html", "w").write(html.replace("__DATA__", json.dumps(D, ensure_ascii=False)))
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1100, "height": 530}, device_scale_factor=1.5)
    pg.goto("file://" + __import__("os").path.abspath("dashboard/index.html")); pg.wait_for_timeout(500)
    pg.screenshot(path="figures/fig5_dashboard.png", full_page=False); b.close()
print("ok")
