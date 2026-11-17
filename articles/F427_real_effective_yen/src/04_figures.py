"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R, F = ROOT / "data", ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：日本銀行「実効為替レート」「外国為替相場」（日本銀行 時系列統計データ検索サイト）をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
e = pd.read_csv(D / "monthly.csv").set_index("ym")
x = (e.index // 100) + ((e.index % 100) - 0.5) / 12

# 図1 実質実効
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(x, e.reer, color=C[1], lw=1.8)
ax.axhline(m["reer_latest"], color=INK2, lw=0.8, ls="--")
ax.text(1972, m["reer_latest"] - 15, f"2026年9月 {m['reer_latest']:.1f}\n（1970年1月は{m['reer_1970_01']:.1f}）", fontsize=9, color=INK2)
pk = m["reer_peak_month"]
ax.annotate(f"{pk//100}年{pk%100}月 {m['reer_peak']:.1f}", (pk // 100 + (pk % 100 - 0.5) / 12, m["reer_peak"]), xytext=(2002, 185), fontsize=9, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.set_xlim(1969.5, 2027); ax.set_ylim(40, 205)
ax.set_ylabel("実質実効為替レート（2020年＝100、上が円高）")
style(ax)
ax.set_title("円の実質実効為替レートは、1970年の統計開始以来の最も低い水準", loc="left", fontsize=12)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.17)
save(fig, F / "fig1_reer.png", SRC, f"注：月次。最も低いのは{m['reer_min_month']//100}年{m['reer_min_month']%100}月の{m['reer_min']:.1f}。2020年より前に、2026年9月の値以下の月はない。")

# 図2 名目・実質・相対物価（対数、1970年1月＝100）
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for col, lab, c in [("neer", "名目実効為替レート", C[0]), ("reer", "実質実効為替レート", C[1]), ("relprice", "相対物価（実質÷名目）", C[2])]:
    s = e[col] / e.loc[197001, col] * 100
    ax.plot(x, s, color=c, lw=1.8, label=lab)
ax.set_yscale("log")
from matplotlib.ticker import NullFormatter
ax.set_yticks([25, 50, 100, 200, 400, 800]); ax.set_yticklabels(["25", "50", "100", "200", "400", "800"]); ax.yaxis.set_minor_formatter(NullFormatter())
ax.axhline(100, color=INK2, lw=0.6)
ax.set_xlim(1969.5, 2027)
ax.set_ylabel("1970年1月＝100（対数目盛り）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
mult = e.loc[m["latest_month"], "neer"] / e.loc[197001, "neer"]
ax.set_title(f"名目では1970年1月の{mult:.1f}倍の円高。物価の差がそれを打ち消した", loc="left", fontsize=12)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.17)
save(fig, F / "fig2_nominal_real_price.png", SRC, "注：相対物価は、日本の物価を相手国の物価で割ったものにあたる（実質÷名目）。下がるのは日本の物価が相手国ほど上がらなかったこと。")

# 図3 分解
dd = pd.read_csv(R / "decomp.csv").iloc[:3]
labs = [f"ピーク（{m['reer_peak_month']//100}年{m['reer_peak_month']%100}月）→\n2026年9月", "1995年1月→\n2026年9月", "2012年1月→\n2026年9月"]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
xx = np.arange(3)
ln_ = np.log(1 + dd.nominal_pct / 100) * 100; lp = np.log(1 + dd.relprice_pct / 100) * 100
ax.bar(xx, ln_, color=C[0], width=0.55, label="名目（為替そのもの）")
ax.bar(xx, lp, bottom=ln_, color=C[2], width=0.55, label="相対物価（物価の差）")
for i in range(3):
    tot = ln_.iloc[i] + lp.iloc[i]
    ax.text(i, tot - 6, f"実質 {dd.real_pct.iloc[i]:.0f}%\n名目の分 {dd.nominal_share.iloc[i]:.0f}%・物価の差 {dd.relprice_share.iloc[i]:.0f}%", ha="center", va="top", fontsize=9)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(xx, labs); ax.set_ylim(-135, 10)
ax.set_ylabel("実質実効の変化（対数×100）")
ax.legend(frameon=False, loc="lower right", fontsize=9)
style(ax)
ax.set_title("1995年からの下落の6〜7割は物価の差、2012年からの下落の8割は名目の円安", loc="left", fontsize=12)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.17)
save(fig, F / "fig3_decomposition.png", SRC)

# 図4 相対物価の前年比
t = pd.read_csv(R / "relprice_yoy.csv").set_index("year").loc[1990:2025]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.bar(t.index, t.relprice_yoy_pct, color=[C[2] if v >= 0 else C[0] for v in t.relprice_yoy_pct], width=0.75)
for (a, b, k) in [(1996, 2012, "relprice_yoy_mean_1996_2012"), (2013, 2021, "relprice_yoy_mean_2013_2021"), (2022, 2025, "relprice_yoy_mean_2022_2025")]:
    ax.hlines(q[k], a - 0.4, b + 0.4, color=INK, lw=1.4, ls="--")
    ax.text((a + b) / 2, q[k] - 0.55, f"平均 {q[k]:+.1f}%", ha="center", fontsize=9)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylabel("相対物価の前年比（%、年平均）")
style(ax)
ax.set_title("物価の差による押し下げは、1996〜2012年の年2.9%から2022年以降はほぼ0に", loc="left", fontsize=12)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig4_relprice_yoy.png", SRC)
