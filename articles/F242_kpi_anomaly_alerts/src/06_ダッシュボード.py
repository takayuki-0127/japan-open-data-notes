"""06 ダッシュボード：架空の会社「あおばマート」（架空）の毎日の注文数を見張る画面の例を、1枚の HTML で作る。
数字はシミュレーション（種0）で、実在の会社のデータではない。"""
import numpy as np, pandas as pd, json, html
s = pd.read_csv("results/A_sim_seed0_series.csv", parse_dates=["date"])
d = s[s.date >= "2025-09-01"].reset_index(drop=True)
ly = np.log(s.orders.values)
W, H, P = 860, 240, 40
x = lambda i: P + i * (W - 2 * P) / (len(d) - 1)
lo, hi = d.orders.min() * 0.95, d.orders.max() * 1.05
y = lambda v: H - P - (v - lo) / (hi - lo) * (H - 2 * P)
pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(d.orders))
dots = "".join(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="5" fill="#d62728"/>' for i, (v, a) in enumerate(zip(d.orders, d["D6 D5＋2日確認"])) if a)
dots += "".join(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="3" fill="none" stroke="#ff7f0e" stroke-width="1.5"/>' for i, (v, a, b) in enumerate(zip(d.orders, d["D5 D3＋暦"], d["D6 D5＋2日確認"])) if a and not b)
camp = "".join(f'<rect x="{x(i)-3:.1f}" y="{P}" width="6" height="{H-2*P}" fill="#1f77b4" opacity="0.10"/>' for i, sp in enumerate(d.sp) if sp == 3)
ax = "".join(f'<text x="{x(i):.1f}" y="{H-12}" font-size="11" text-anchor="middle" fill="#555">{dt:%m/%d}</text>' for i, dt in enumerate(d.date) if dt.day == 1)
al = s[(s["D5 D3＋暦"]) & (s.date >= "2025-01-01")].tail(8)
rows = ""
for _, r in al.iloc[::-1].iterrows():
    conf = r["D6 D5＋2日確認"]; dirn = "下振れ" if r.z5 < 0 else "上振れ"
    act = "担当者に連絡（すぐ確認）" if abs(r.z5) > 5 else ("2日続いたので確認" if conf else "様子見（明日も外れたら確認）")
    rows += f"<tr><td>{r.date:%Y-%m-%d}（{'月火水木金土日'[r.date.weekday()]}）</td><td>{int(r.orders):,}</td><td>{dirn}</td><td>{r.z5:+.1f}</td><td>{act}</td></tr>"
yr = s[s.date.dt.year == 2025]
n5 = int(yr["D5 D3＋暦"].sum()); n6 = int(yr["D6 D5＋2日確認"].sum())
page = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>KPI 見張り（架空：あおばマート）</title>
<style>body{{font-family:'Noto Sans CJK JP',sans-serif;margin:20px;color:#222;background:#fff;width:900px}}h1{{font-size:20px;margin:0 0 4px}}.sub{{color:#666;font-size:12px;margin-bottom:12px}}
.cards{{display:flex;gap:12px;margin:10px 0}}.card{{border:1px solid #ddd;border-radius:8px;padding:8px 14px;min-width:150px}}.card b{{font-size:22px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border-bottom:1px solid #eee;padding:5px 8px;text-align:left}}th{{background:#f6f6f6}}.note{{font-size:12px;color:#555}}</style></head><body>
<h1>毎日の注文数の見張り（架空の会社：あおばマート）</h1><div class="sub">※架空の会社・シミュレーションの数字です。ルール：前の「ふつうの日」の同じ曜日4回の中央値と比べる（祝日は日曜と、販促の日は前の販促の日と比べる）。|z|が3.5を超えたら印、5を超えるか2日続いたら連絡。</div>
<div class="cards"><div class="card">2025年の印<br><b>{n5}日</b></div><div class="card">2025年の連絡<br><b>{n6}日</b></div><div class="card">空振りの目安<br><b>年4回まで</b></div><div class="card">次の見直し<br><b>四半期ごと</b></div></div>
<svg width="{W}" height="{H}" style="border:1px solid #eee">{camp}<polyline points="{pts}" fill="none" stroke="#333" stroke-width="1.3"/>{dots}{ax}
<text x="{P}" y="18" font-size="12" fill="#555">注文数（2025年9月〜12月）　●連絡　○印だけ　青の帯＝販促の日</text></svg>
<h3 style="font-size:15px;margin:14px 0 4px">直近の印</h3><table><tr><th>日付</th><th>注文数</th><th>向き</th><th>z</th><th>どうするか</th></tr>{rows}</table>
<p class="note">読み方：z は「いつもの外れの何倍外れたか」。年末年始・お盆は比べる相手がいないので前年と比べ、z が6を超えたときだけ印をつけます。</p></body></html>"""
open("dashboard/index.html", "w").write(page); print("ok", n5, n6)
