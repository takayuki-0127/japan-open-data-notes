"""図を作る（PNG。日付などのメタデータは入れない）。ネットにはつながない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
f = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if pathlib.Path(f).exists():
    font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e", "axes.grid": True,
                     "grid.color": "#e6e5e0", "grid.linewidth": 0.6, "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C1, C2, C3, C4, INK = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#0b0b0b"
SRC = "出典：経済産業省「特定サービス産業動態統計調査」（結婚式場業）、厚生労働省「人口動態統計」、総務省「消費者物価指数」をもとに作成者が加工して作成"
main = json.load(open(RES / "main.json", encoding="utf-8"))
ix = pd.read_csv(RES / "index_annual.csv")


def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7, color="#52514e")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


# 図1：件数・婚姻・売上の指数（2つの様式を分けて）
fig, ax = plt.subplots(1, 2, figsize=(10, 4.8), sharey=True, gridspec_kw={"width_ratios": [15, 10]})
fig.subplots_adjust(left=0.07, right=0.98, top=0.83, bottom=0.17, wspace=0.08)
for a, era, base in [(ax[0], "old", 2000), (ax[1], "new", 2015)]:
    e = ix[ix.era == era]
    a.plot(e.year, e.marr_idx, color=C1, lw=2, marker="o", ms=4, label="婚姻件数")
    a.plot(e.year, e.count_idx, color=C2, lw=2, marker="o", ms=4, label="式場の取扱件数")
    a.plot(e.year, e.sales_idx, color=C3, lw=2, marker="o", ms=4, label="式場の売上高")
    a.axhline(100, color="#52514e", lw=0.8)
    a.set_title(f"{'旧様式 2000〜2014年（2000年＝100）' if era == 'old' else '新様式 2015〜2024年（2015年＝100）'}", fontsize=10, loc="left")
    last = e.iloc[-1]
    for col, cc in [("marr_idx", C1), ("count_idx", C2), ("sales_idx", C3)]:
        a.annotate(f"{last[col]:.0f}", (last.year, last[col]), xytext=(4, 0), textcoords="offset points", fontsize=8, color=INK, va="center")
ax[0].set_ylabel("指数")
ax[0].legend(frameon=False, loc="lower left")
fig.suptitle(f"式場の件数は結婚より速く減った（2000→2014年：件数 {main['periods']['old']['count_cum_pct']:.0f}%、婚姻 {main['periods']['old']['marr_cum_pct']:.0f}%）",
             x=0.01, ha="left", fontsize=12)
fig.text(0.01, 0.045, "式場の指数は、調査対象の入れ替えを調整した前年比をつないだもの。2014→2015年は調査の様式が変わり、つながらない", fontsize=8, color="#52514e")
save(fig, "fig1_index_count_marriages.png")

# 図2：売上の変化の分解
dec = pd.read_csv(RES / "decomposition.csv")
fig, ax = plt.subplots(figsize=(9.5, 6))
fig.subplots_adjust(left=0.3, right=0.97, top=0.88, bottom=0.14)
yy = np.arange(len(dec))[::-1] * 1.25
h = 0.24
for j, (col, lab, cc) in enumerate([("sales", "売上高の変化（下の3つの合計）", "#52514e"), ("marriages", "婚姻件数の変化", C1),
                                    ("share", "結婚1組あたりの式場の件数の変化", C2), ("unit_price", "1件あたりの売上の変化", C3)]):
    pos = yy + (1.5 - j) * h
    ax.barh(pos, dec[col], height=h * 0.88, color=cc, label=lab)
    for y0, v in zip(pos, dec[col]):
        ax.text(v + (1 if v >= 0 else -1), y0, f"{v:+.0f}", va="center", ha="left" if v >= 0 else "right", fontsize=8, color=INK)
ax.axvline(0, color="#52514e", lw=0.8)
ax.set_yticks(yy)
ax.set_yticklabels(dec.period, fontsize=9)
ax.set_xlabel("対数の変化（×100、おおよそ%）")
ax.set_xlim(-85, 35)
ax.legend(frameon=False, fontsize=8, loc="lower left")
ax.grid(axis="y", visible=False)
fig.suptitle("売上の減りの多くは「結婚1組あたりの式場の件数」の減りから。1件あたりの売上の上がりが一部を埋めた", x=0.01, ha="left", fontsize=12)
save(fig, "fig2_decomposition.png")

# 図3：1件あたりの売上（名目・実質）
fig, ax = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True, gridspec_kw={"width_ratios": [15, 10]})
fig.subplots_adjust(left=0.07, right=0.97, top=0.83, bottom=0.14, wspace=0.08)
for a, era in [(ax[0], "old"), (ax[1], "new")]:
    e = ix[ix.era == era]
    a.plot(e.year, e.unit_idx, color=C1, lw=2, marker="o", ms=4, label="1件あたりの売上（名目）")
    a.plot(e.year, e.unit_real_idx, color=C2, lw=2, marker="o", ms=4, label="同・物価（総合）で割った実質")
    a.axhline(100, color="#52514e", lw=0.8)
    a.set_title("旧様式（2000年＝100）" if era == "old" else "新様式（2015年＝100）", fontsize=10, loc="left")
    close = abs(e.unit_idx.iloc[-1] - e.unit_real_idx.iloc[-1]) < 2
    for col, dy in [("unit_idx", 6 if close else 0), ("unit_real_idx", -6 if close else 0)]:
        a.annotate(f"{e[col].iloc[-1]:.0f}", (e.year.iloc[-1], e[col].iloc[-1]), xytext=(4, dy), textcoords="offset points", fontsize=8, color=INK, va="center")
ax[0].set_ylabel("指数")
ax[0].legend(frameon=False, loc="upper left")
lv = main["levels"]
fig.suptitle(f"1件あたりの売上は2000年代とコロナのあとに上がり、2024年は約{lv['unit_2024_man']:.0f}万円（2019年は約{lv['unit_2019_man']:.0f}万円、実数の比）", x=0.01, ha="left", fontsize=12)
save(fig, "fig3_unit_sales.png")

# 図4：問い直し 月ごとの割合
ms = pd.read_csv(RES / "requestion_month_share.csv")
rq = json.load(open(RES / "requestion.json", encoding="utf-8"))
fig, ax = plt.subplots(figsize=(9, 4.8))
fig.subplots_adjust(left=0.09, right=0.97, top=0.83, bottom=0.16)
for g, cc, lab in [("2000_2004", C1, "2000〜2004年"), ("2009_2013", C3, "2009〜2013年"), ("2015_2019", C4, "2015〜2019年"), ("2022_2024", C2, "2022〜2024年")]:
    z = ms[ms.group == g]
    ax.plot(z.month, z.share, color=cc, lw=2, marker="o", ms=5, label=lab)
ax.set_xticks(range(1, 13))
ax.set_xticklabels([f"{m}月" for m in range(1, 13)])
ax.set_ylabel("その年の取扱件数に占める割合（%）")
ax.legend(frameon=False, ncol=4, loc="upper center", fontsize=9)
ax.set_ylim(0, 17)
fig.suptitle(f"式が減っても、春・秋（4・5・10・11月）への集中はほぼ同じ（{rq['2000_2004']['peak_share']:.1f}% → {rq['2022_2024']['peak_share']:.1f}%）",
             x=0.01, ha="left", fontsize=12)
ax.set_title("年の途中で調査対象が変わった2014・2020年と、2021年は除く", fontsize=9, loc="left")
save(fig, "fig4_season_share.png")
print("figures ok")
