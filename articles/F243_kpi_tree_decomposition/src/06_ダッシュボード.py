"""F243 06 ダッシュボード：架空の書店チェーン「ひかり書店（架空）」の月次報告を想定した、売上の変化の説明ページ（静的 HTML）。
数字は 03_分析 の A（架空のシミュレーション）。実在の会社・データではない。"""
import json, os
B = os.path.join(os.path.dirname(__file__), "..")
j = json.load(open(f"{B}/results/main.json"))["A"]
S0, S1 = j["売上0"], j["売上1"]; sh = j["シャープレイ"]; nv = j["素朴なツリーのシャープレイ"]
man = lambda x: f"{x/1e4:,.0f}万円"
steps = [("前の期間", S0, "base"), ("訪問数", sh["訪問数"], "d"), ("チャネル構成", sh["構成"], "d"), ("チャネル別の購入率", sh["購入率"], "d"),
         ("点数", sh["点数"], "d"), ("単価", sh["単価"], "d"), ("今の期間", S1, "base")]
W, H, x0, bw, top = 760, 300, 60, 80, 20
mx = S1 * 1.1; sc = lambda v: (H - 40) * v / mx
bars = []; cum = 0
for i, (lab, v, t) in enumerate(steps):
    x = x0 + i * (bw + 20)
    if t == "base":
        y = H - 20 - sc(v); h = sc(v); col = "#6b7a8f"; cum = v; txt = man(v)
    else:
        a, b = cum, cum + v; y = H - 20 - sc(max(a, b)); h = max(sc(abs(v)), 1.5); col = "#2e8b57" if v >= 0 else "#c0392b"; cum = b; txt = ("+" if v >= 0 else "") + man(v)
    bars.append(f'<rect x="{x}" y="{y:.1f}" width="{bw}" height="{h:.1f}" fill="{col}"/><text x="{x+bw/2}" y="{y-6:.1f}" text-anchor="middle" font-size="13">{txt}</text><text x="{x+bw/2}" y="{H-2}" text-anchor="middle" font-size="12">{lab}</text>')
svg = f'<svg width="{W}" height="{H+10}" xmlns="http://www.w3.org/2000/svg">{"".join(bars)}</svg>'
cv = j["チャネル別の購入率の変化"]
html = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>売上の変化の説明（架空）</title>
<style>body{{font-family:'Noto Sans CJK JP',sans-serif;margin:24px;color:#222;width:1120px}}h1{{font-size:22px;margin:0 0 4px}}.note{{color:#666;font-size:13px}}
.row{{display:flex;gap:16px;margin-top:14px}}.card{{border:1px solid #ddd;border-radius:8px;padding:12px 16px;flex:1}}.big{{font-size:26px;font-weight:bold}}
.tree{{font-size:14px;line-height:1.9}}.warn{{background:#fff4e5;border-left:4px solid #e67e22;padding:10px 14px;font-size:14px;margin-top:14px}}
table{{border-collapse:collapse;font-size:13px}}td,th{{border-bottom:1px solid #eee;padding:4px 10px;text-align:right}}th:first-child,td:first-child{{text-align:left}}</style></head><body>
<h1>今月の売上はなぜ伸びたか ― KPI ツリーで分ける</h1><div class="note">架空の書店チェーン「ひかり書店（架空）」の社内向けを想定した例。数字はシミュレーションで、実在の会社のデータではありません。</div>
<div class="row"><div class="card"><div>売上</div><div class="big">{man(S0)} → {man(S1)}</div><div>{j['伸び率']*100:+.1f}%</div></div>
<div class="card"><div>全体の購入率</div><div class="big">{j['全体の購入率0']*100:.1f}% → {j['全体の購入率1']*100:.1f}%</div><div>ただしチャネル別ではアプリ {cv[0]*100:+.0f}%・Web {cv[1]*100:+.0f}%</div></div>
<div class="card"><div>総訪問数</div><div class="big">20.0万 → 20.0万</div><div>アプリの割合 10% → 30%</div></div></div>
<div class="row"><div class="card"><b>売上の変化の内訳（シャープレイ値。並べる順番の平均）</b><br>{svg}</div>
<div class="card tree"><b>KPI ツリー</b><br>売上 ＝ 訪問数 × Σ（チャネルの割合 × 購入率 × 点数 × 単価）<br>・アプリ：訪問 2万→6万、購入率 20%→18%<br>・Web：訪問 18万→14万、購入率 2.0%→1.8%<br>・点数・単価：変わらず<br><br>
<table><tr><th>要因</th><th>寄与</th></tr><tr><td>チャネル構成</td><td>{man(sh['構成'])}</td></tr><tr><td>チャネル別の購入率</td><td>{man(sh['購入率'])}</td></tr><tr><td>訪問数・点数・単価</td><td>0円</td></tr></table></div></div>
<div class="warn"><b>読み方の注意：</b>チャネルを分けずに「全体の購入率」で見ると、購入率が {man(nv['全体の購入率'])} 分の伸びを生んだように見えます。実際は、どちらのチャネルでも購入率は下がっていて、伸びたのは購入率の高いアプリの割合が増えたためです（シンプソンのパラドックス）。施策の評価は、チャネル別の購入率で行います。</div>
</body></html>"""
open(f"{B}/dashboard/kpi_tree_dashboard.html", "w").write(html)
print("ok", len(html))
