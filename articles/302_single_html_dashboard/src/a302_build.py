"""302：同じダッシュボードを4つの作り方で HTML にする。
V1＝グラフの部品を CDN から読む／V2＝部品も HTML の中に入れる／V3＝部品を使わず SVG を自分で描く／
V4＝部品は中に入れ、データだけ別ファイル（data.json）から読む。
あわせて、中に入れるデータの行数を増やした HTML（大きさの試し）も作る。
"""
import json
import numpy as np, pandas as pd
from common import DATA, ROOT

OUT = ROOT / "html"; OUT.mkdir(exist_ok=True)
df = pd.read_csv(DATA / "lodging_guest_nights.csv")
df = df[df.month > 0].sort_values(["year", "month"])
SER = {"total": "全体", "s0_9": "従業者0〜9人", "s10_29": "10〜29人", "s30_99": "30〜99人", "s100": "100人以上", "foreign": "外国人"}
data = {"labels": [f"{y}-{m:02d}" for y, m in zip(df.year, df.month)], "series": {k: [int(v) for v in df[k]] for k in SER}, "names": SER}
DJ = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
LIB = (ROOT / "vendor" / "chart.umd.min.js").read_text()
CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"

CSS = """body{font-family:system-ui,'Noto Sans CJK JP','Yu Gothic',Meiryo,sans-serif;margin:16px;color:#0b0b0b;background:#fff}
h1{font-size:18px;margin:0 0 8px}.cards{display:flex;gap:12px;margin:8px 0 12px;flex-wrap:wrap}
.card{border:1px solid #d9d8d2;border-radius:8px;padding:8px 14px;min-width:150px}.card b{font-size:22px;display:block}
.card span{font-size:12px;color:#666}select{font-size:14px;padding:4px}.box{max-width:900px}
#err{color:#b00020;font-size:13px}small{color:#777}"""
HEAD = """<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>延べ宿泊者数ダッシュボード</title><style>%s</style></head><body>
<h1>延べ宿泊者数（全国・月別、2015〜2025年）</h1>
<label>区分 <select id="sel"></select></label>
<div class="cards"><div class="card"><span>2025年の合計</span><b id="k1">-</b></div><div class="card"><span>2019年比</span><b id="k2">-</b></div>
<div class="card"><span>いちばん多い月（2025年）</span><b id="k3">-</b></div></div>
<div class="box" id="box"></div><div id="err"></div>
<small>出典：観光庁「宿泊旅行統計調査」をもとに作成者が加工して作成</small>
""" % CSS
# 3つの数字（カード）と区分の選択は、どの作り方でも同じコード
COMMON = """
function fmt(n){return (n/1e8).toFixed(2)+'億人泊'}
function kpi(D,k){const L=D.labels,s=D.series[k];let a25=0,a19=0,mx=-1,mi='';
 L.forEach((l,i)=>{if(l.startsWith('2025')){a25+=s[i];if(s[i]>mx){mx=s[i];mi=l.slice(5)+'月'}}if(l.startsWith('2019'))a19+=s[i]});
 k1.textContent=fmt(a25);k2.textContent=(a25/a19*100).toFixed(1)+'%';k3.textContent=mi}
function setup(D,draw){const sel=document.getElementById('sel');
 for(const k in D.names){const o=document.createElement('option');o.value=k;o.textContent=D.names[k];sel.appendChild(o)}
 const go=()=>{kpi(D,sel.value);draw(D,sel.value);window.__ok=true;window.__t=performance.now()};
 sel.onchange=go;go()}
window.__ok=false;window.addEventListener('error',e=>{document.getElementById('err').textContent='読み込めませんでした：'+(e.message||'外部のファイル')},true);
"""
CHART = """
let ch;function draw(D,k){const cv=document.getElementById('cv');if(ch)ch.destroy();
 ch=new Chart(cv,{type:'line',data:{labels:D.labels,datasets:[{label:D.names[k],data:D.series[k],borderColor:'#2a78d6',pointRadius:0,borderWidth:2}]},
 options:{animation:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}})}
document.getElementById('box').innerHTML='<canvas id="cv" width="900" height="360"></canvas>';
"""
SVG = """
function draw(D,k){const s=D.series[k],W=900,H=360,p=[50,26,30,20],mx=Math.max(...s);
 const x=i=>p[0]+i*(W-p[0]-p[3])/(s.length-1),y=v=>H-p[2]-v/mx*(H-p[2]-p[1]);
 let d='';s.forEach((v,i)=>{d+=(i?'L':'M')+x(i).toFixed(1)+' '+y(v).toFixed(1)});
 let g='';for(let t=0;t<=4;t++){const v=mx*t/4;g+=`<line x1="${p[0]}" x2="${W-p[3]}" y1="${y(v)}" y2="${y(v)}" stroke="#e5e4de"/><text x="${p[0]-6}" y="${y(v)+4}" font-size="11" text-anchor="end">${(v/1e6).toFixed(0)}</text>`}
 D.labels.forEach((l,i)=>{if(l.endsWith('-01'))g+=`<text x="${x(i)}" y="${H-10}" font-size="11" text-anchor="middle">${l.slice(0,4)}</text>`});
 document.getElementById('box').innerHTML=`<svg id="sv" viewBox="0 0 ${W} ${H}" width="100%">${g}<path d="${d}" fill="none" stroke="#2a78d6" stroke-width="2"/><text x="6" y="14" font-size="11">百万人泊</text></svg>`}
"""

def page(lib_tag, data_js, draw_js, start):
    return HEAD + lib_tag + "<script>" + COMMON + data_js + draw_js + start + "</script></body></html>"

INLINE_DATA = "const D=" + DJ + ";"
pages = {
    "v1_cdn.html": page(f'<script src="{CDN}"></script>', INLINE_DATA, CHART, "setup(D,draw);"),
    "v2_inline.html": page("<script>" + LIB + "</script>", INLINE_DATA, CHART, "setup(D,draw);"),
    "v3_svg.html": page("", INLINE_DATA, SVG, "setup(D,draw);"),
    "v4_fetch.html": page("<script>" + LIB + "</script>", "", CHART,
                          "fetch('data.json').then(r=>r.json()).then(D=>setup(D,draw)).catch(e=>{document.getElementById('err').textContent='データを読み込めませんでした：'+e.message});"),
}
for n, h in pages.items():
    (OUT / n).write_text(h, encoding="utf-8")
(OUT / "data.json").write_text(DJ, encoding="utf-8")

# ---- 大きさの試し：中に入れる行数を増やす（架空の明細。月×区分の合計を画面で集計してから描く）
rng = np.random.default_rng(302)
BIG = """
function agg(R){const m=new Map();for(const r of R){m.set(r[0],(m.get(r[0])||0)+r[2])}const L=[...m.keys()].sort();return {labels:L,series:{total:L.map(l=>m.get(l))},names:{total:'合計'}}}
const D=agg(R);
"""
for n in (1_000, 10_000, 100_000, 300_000, 1_000_000):
    ym = rng.integers(0, 132, n); cat = rng.integers(0, 50, n); val = rng.integers(1, 5000, n)
    lab = data["labels"]
    rows = "[" + ",".join(f'["{lab[a]}",{b},{c}]' for a, b, c in zip(ym, cat, val)) + "]"
    for tag, lib_tag, draw in (("inline", "<script>" + LIB + "</script>", CHART), ("svg", "", SVG)):
        h = page(lib_tag, "const R=" + rows + ";" + BIG, draw, "setup(D,draw);")
        (OUT / f"big_{tag}_{n}.html").write_text(h, encoding="utf-8")
print({p.name: p.stat().st_size for p in sorted(OUT.iterdir())})
