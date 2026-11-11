"""05 ダッシュボード：架空のネット書店「あおば書店（架空）」の集計チェック画面（静的な HTML）と、その画像。"""
import os, json
import pandas as pd
import lib

ROOT = lib.ROOT; RES = os.path.join(ROOT, "results")
s = json.load(open(os.path.join(RES, "summary.json")))
mag = pd.read_csv(os.path.join(RES, "B_error_magnitude.csv"))
short = json.load(open(os.path.join(RES, "short_labels.json")))
cm = pd.read_csv(os.path.join(RES, "A_catch_matrix_sqlite.csv"), index_col=0)
sim = lib.simulate(seed=1)
retail, dim, hol = lib.load_retail()
dbs = lib.make_dbs(dict(retail=retail, item_dim=dim, holidays=hol, **sim))
sp = {x["id"]: x for x in lib.SPECS}
gross = lib.run(dbs, sp["B1"]["good"], "sqlite").set_index("k").v
net = lib.run(dbs, sp["B3"]["good"], "sqlite").set_index("k").v
cust = lib.run(dbs, sp["B6"]["good"], "sqlite").set_index("k").v
conv = lib.run(dbs, sp["B13"]["good"], "sqlite").set_index("k").v
m = "2025-12"
rows = ""
for t in lib.TESTS:
    n = int(cm[t].map(lambda x: str(x) == "True").sum())
    rows += f"<tr><td>{t}</td><td class='ok'>合格</td><td>{n} / 21</td></tr>"
top = mag.reindex(mag.total_err_pct.abs().sort_values(ascending=False).index).head(8)
bars = ""
for _, r in top.iterrows():
    w = min(abs(r.total_err_pct), 320) / 320 * 100
    bars += f"<div class='bar'><span class='lab'>{r.id} {short[r.id]}</span><span class='b {'neg' if r.total_err_pct < 0 else 'pos'}' style='width:{w:.0f}%'></span><span class='v'>{r.total_err_pct:+.0f}%</span></div>"
html = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>集計チェック（あおば書店・架空）</title>
<style>
body{{font-family:'Noto Sans CJK JP',sans-serif;margin:0;background:#f5f6f8;color:#1a202c}}
header{{background:#234e52;color:#fff;padding:14px 24px}} header h1{{margin:0;font-size:20px}} header p{{margin:4px 0 0;font-size:12px;opacity:.85}}
.wrap{{padding:18px 24px;display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.cards{{grid-column:1/3;display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}
.card{{background:#fff;border-radius:8px;padding:12px 14px;box-shadow:0 1px 2px #0002}} .card .t{{font-size:12px;color:#4a5568}} .card .n{{font-size:24px;font-weight:700;margin-top:4px}}
.panel{{background:#fff;border-radius:8px;padding:12px 16px;box-shadow:0 1px 2px #0002}} .panel h2{{font-size:14px;margin:0 0 8px}}
table{{width:100%;border-collapse:collapse;font-size:12.5px}} td{{padding:5px 4px;border-bottom:1px solid #edf2f7}} .ok{{color:#2f855a;font-weight:700}}
.bar{{display:flex;align-items:center;font-size:12px;margin:5px 0}} .lab{{width:46%}} .b{{display:inline-block;height:12px;border-radius:2px}} .pos{{background:#dd6b20}} .neg{{background:#c53030}} .v{{margin-left:6px}}
.note{{grid-column:1/3;font-size:11px;color:#4a5568}}
</style></head><body>
<header><h1>売上集計のチェック画面（あおば書店・架空）</h1><p>毎朝の集計の後に7種類のテストを流し、ひとつでも失敗したら数字を配る前に止める。会社・数字はすべて架空（シミュレーション）。</p></header>
<div class="wrap">
<div class="cards">
<div class="card"><div class="t">{m} の売上（値引き前）</div><div class="n">{gross[m]/1e6:.1f} 百万円</div></div>
<div class="card"><div class="t">{m} の売上（値引き後）</div><div class="n">{net[m]/1e6:.1f} 百万円</div></div>
<div class="card"><div class="t">{m} に購入した顧客</div><div class="n">{int(cust[m]):,} 人</div></div>
<div class="card"><div class="t">{m} の購入率（注文 ÷ 訪問）</div><div class="n">{conv[m]*100:.2f}%</div></div>
</div>
<div class="panel"><h2>今朝のテスト結果（正しい SQL）</h2><table><tr><td><b>テスト</b></td><td><b>今朝</b></td><td><b>誤りを入れたとき見つけた数</b></td></tr>{rows}</table>
<p style="font-size:12px">21個の誤りのうち、どれかのテストで見つかったのは {s['main']['caught_any']} 個。小さなデータでの答え合わせ（T5）を外すと {s['main']['without_T5']} 個。</p></div>
<div class="panel"><h2>誤りを入れたときの合計のずれ（大きい順に8つ）</h2>{bars}</div>
<div class="note">データ：注文はシミュレーション（あおば書店は架空の会社）。公開データの部分は経済産業省「商業動態統計」。SQL は DuckDB と SQLite で実行（SQL Server 版は自動変換で未実行）。</div>
</div></body></html>"""
os.makedirs(os.path.join(ROOT, "dashboard"), exist_ok=True)
p = os.path.join(ROOT, "dashboard", "check_dashboard.html")
open(p, "w", encoding="utf-8").write(html)
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport=dict(width=1200, height=720), device_scale_factor=1.5)
    pg.goto("file://" + p); pg.wait_for_timeout(500)
    pg.screenshot(path=os.path.join(ROOT, "figures", "fig6_check_dashboard.png"), full_page=True); b.close()
print("dashboard ok")
