# F259 06 判断用の HTML の表（架空の会社「あおばストア（架空）」の社内向けの例）
import json, pandas as pd
A = pd.read_csv("results/A_cost_main.csv")
agg = A.groupby(["p", "L", "決め方"])[["費用", "在庫費", "欠品費", "売り逃し率", "カバー率"]].mean().round(4).reset_index()
mod = A.groupby(["p", "L", "モデル", "決め方"]).費用.mean().round(3).reset_index()
data = json.dumps({"agg": agg.to_dict(orient="records"), "mod": mod.to_dict(orient="records")}, ensure_ascii=False)
html = """<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>安全在庫の決め方（架空）</title><style>
body{font-family:"Noto Sans JP",sans-serif;margin:16px;color:#222;background:#fff;max-width:960px}
h1{font-size:20px}p.note{color:#666;font-size:13px}table{border-collapse:collapse;margin:12px 0;font-size:14px;width:100%}
th,td{border-bottom:1px solid #ddd;padding:6px 8px;text-align:right}th:first-child,td:first-child{text-align:left}
tr.best td{background:#fdecea;font-weight:bold}select{font-size:15px;margin-right:12px}.wrap{overflow-x:auto}
</style></head><body>
<h1>安全在庫の決め方と費用（あおばストア（架空）・社内向けの例）</h1>
<p class="note">需要は商業動態統計の6業態の月次販売額を、架空の会社の需要に見立てたもの（2017〜2019年の月平均＝100）。予測は F231 の5モデル。2か月ごとに発注。費用は例として置いた比（在庫1単位1か月=1、売り逃し1単位=p）で、実在の費用ではない。</p>
<label>リードタイム L <select id="L"><option>0</option><option>1</option><option selected>2</option><option>3</option></select></label>
<label>売り逃しの損 p <select id="p"><option>4</option><option selected>9</option><option>19</option></select></label>
<div class="wrap"><table id="t1"></table></div><h2 style="font-size:16px">モデル別の月あたり費用</h2><div class="wrap"><table id="t2"></table></div>
<p class="note">カバー率：L+R か月の需要を「予測の合計＋安全在庫」で覆えた割合（目標は p/(p+1)）。「後から見た最良の倍率」は結果を見てから選んだ目安で、実際には使えない。</p>
<script>const D=__DATA__;const R=["なし","偏りだけ直す","ルートの式","合計の外れの分位点","分位点（2か月持つ前提）","後から見た最良の倍率"];
const M=["季節ナイーブ","季節ナイーブ＋伸び","ETS","SARIMA","LightGBM"];
function f(x,d=1){return x==null||isNaN(x)?"—":x.toFixed(d)}
function draw(){const L=+document.getElementById("L").value,p=+document.getElementById("p").value;
const a=D.agg.filter(r=>r.L===L&&r.p===p);const real=a.filter(r=>r.決め方!=="後から見た最良の倍率");const mn=Math.min(...real.map(r=>r.費用));
let h="<tr><th>安全在庫の決め方</th><th>月あたり費用</th><th>在庫費</th><th>欠品費</th><th>売り逃し率</th><th>カバー率</th></tr>";
for(const n of R){const r=a.find(x=>x.決め方===n);if(!r)continue;h+=`<tr class="${r.費用===mn?"best":""}"><td>${n}</td><td>${f(r.費用)}</td><td>${f(r.在庫費)}</td><td>${f(r.欠品費)}</td><td>${f(r.売り逃し率*100,2)}%</td><td>${(r.カバー率==null||isNaN(r.カバー率))?"—":f(r.カバー率*100,0)+"%"}</td></tr>`}
document.getElementById("t1").innerHTML=h;
let g="<tr><th>モデル</th>"+R.map(n=>`<th>${n}</th>`).join("")+"</tr>";
for(const m of M){g+=`<tr><td>${m}</td>`+R.map(n=>{const r=D.mod.find(x=>x.L===L&&x.p===p&&x.モデル===m&&x.決め方===n);return `<td>${r?f(r.費用):"—"}</td>`}).join("")+"</tr>"}
document.getElementById("t2").innerHTML=g}
document.getElementById("L").onchange=draw;document.getElementById("p").onchange=draw;draw();</script></body></html>"""
open("dashboard/index.html", "w").write(html.replace("__DATA__", data)); print(len(html))
