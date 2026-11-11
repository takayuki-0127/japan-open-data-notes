"""値上げ判断のダッシュボード（静的 HTML）を作り、画面写真を図6にする。架空のスーパー「さくらマート」は架空の店。"""
import json
import pandas as pd
from common import *
G = pd.read_csv(RES / "D_group_elasticity_and_risk.csv").sort_values("b")
rows = G[["group", "b", "lo", "hi", "items"]].round(2).to_dict("records")
html = """<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>値上げ判断ボード（架空の店）</title>
<style>body{font-family:'Noto Sans CJK JP',sans-serif;margin:24px;background:#f7f7f5;color:#222;width:1100px}
h1{font-size:20px;margin:0 0 4px}.note{color:#666;font-size:12px}.wrap{display:flex;gap:20px;margin-top:14px}
.card{background:#fff;border:1px solid #ddd;border-radius:8px;padding:14px 16px;flex:1}
label{display:block;font-size:13px;margin:8px 0 2px}input{width:100%}.big{font-size:28px;font-weight:bold}
table{border-collapse:collapse;width:100%;font-size:13px}td,th{border-bottom:1px solid #eee;padding:4px 6px;text-align:right}
th:first-child,td:first-child{text-align:left}.ok{color:#2a7a3b}.ng{color:#b02a2a}</style></head><body>
<h1>値上げ判断ボード：さくらマート（架空の店）</h1>
<div class="note">弾力性は家計調査（2002〜2024年、品目の前年差・全品目の年の効果を除く）の群ごとの推定。家計全体の値で、1つの店の弾力性ではない。</div>
<div class="wrap"><div class="card"><b>条件を入れる</b>
<label>粗利率 <span id="mv"></span>%</label><input id="m" type="range" min="5" max="60" value="30">
<label>値上げ幅 <span id="xv"></span>%</label><input id="x" type="range" min="1" max="20" value="5">
<label>その商品の弾力性 <span id="ev"></span></label><input id="e" type="range" min="-80" max="0" value="-15">
</div><div class="card"><b>結果</b><div>利益の変化</div><div class="big" id="pr"></div>
<div>売上の変化：<span id="rv"></span></div><div>利益が減り始める弾力性（分かれ目）：<b id="be"></b></div>
<div class="note">弾力性が分かれ目より小さい（マイナスに大きい）ときだけ、値上げで利益が減る。</div></div>
<div class="card"><b>群ごとの弾力性（家計全体）</b><table><tr><th>群</th><th>弾力性</th><th>95%区間</th><th>品目</th></tr>__ROWS__</table></div></div>
<script>const $=i=>document.getElementById(i);function f(){const m=$('m').value/100,x=$('x').value/100,e=$('e').value/10;
$('mv').textContent=(m*100).toFixed(0);$('xv').textContent=(x*100).toFixed(0);$('ev').textContent=e.toFixed(1);
const p=((1+x)-(1-m))/m*Math.pow(1+x,e)-1,r=Math.pow(1+x,1+e)-1,be=Math.log(m/(m+x))/Math.log(1+x);
$('pr').textContent=(p>=0?'+':'')+(p*100).toFixed(1)+'%';$('pr').className='big '+(p>=0?'ok':'ng');
$('rv').textContent=(r>=0?'+':'')+(r*100).toFixed(1)+'%';$('be').textContent=be.toFixed(2);}
['m','x','e'].forEach(i=>$(i).addEventListener('input',f));f();</script></body></html>"""
tr = "".join(f"<tr><td>{r['group']}</td><td>{r['b']:.2f}</td><td>{r['lo']:.2f}〜{r['hi']:.2f}</td><td>{r['items']}</td></tr>" for r in rows)
out = ROOT / "dashboard" / "price_decision_board.html"
out.write_text(html.replace("__ROWS__", tr), encoding="utf-8")
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1150, "height": 520}, device_scale_factor=1.5)
    pg.goto(out.as_uri()); pg.wait_for_timeout(300)
    pg.screenshot(path=str(FIG / "f234_06_dashboard.png"), full_page=True); b.close()
print("ok")
