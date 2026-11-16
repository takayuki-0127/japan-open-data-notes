"""04 図：fig1〜fig4（PNG、日付などのメタデータなし）。"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
RES = ROOT / "results"
p = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if pathlib.Path(p).exists():
    fm.fontManager.addfont(p)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e5e0",
                     "grid.linewidth": 0.6, "axes.axisbelow": True, "axes.unicode_minus": True})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK2 = "#52514e"
SRC = "出典：気象庁「過去の気象データ検索（年ごとの値）」「日本の月平均気温偏差」をもとに作成者が加工して作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))
MM = M["main"]


def save(fig, name, note=""):
    fig.text(0.01, 0.01, SRC + ("\n" + note if note else ""), fontsize=7, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


# fig1 最深積雪の指数（地点の中央値）
Y = pd.read_csv(RES / "yearly.csv")
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(Y.year, Y.idx_median, color=C[0], lw=1.4, marker="o", ms=3)
ax.plot(Y.year, Y.idx_median.rolling(11, center=True, min_periods=6).mean(), color="#0b0b0b", lw=2.2, label="11年移動平均")
a, b = M["idx_median_1962_1991"], M["idx_median_1996_2025"]
ax.hlines(a, 1962, 1991, color=C[1], lw=2, ls="--"); ax.text(1963, a - 9, f"1962〜1991年の平均 {a:.0f}", color=INK2, fontsize=8.5)
ax.hlines(b, 1996, 2025, color=C[1], lw=2, ls="--"); ax.text(1997, b - 9, f"1996〜2025年の平均 {b:.0f}", color=INK2, fontsize=8.5)
ax.set_ylim(0, None)
ax.set_xlabel("寒候年（前年8月〜その年7月）"); ax.set_ylabel("最深積雪（1962〜1991年平均＝100）")
ax.set_title(f"最深積雪は年ごとの上下が大きく、減り方はゆるやか（{MM['n_st']}地点の中央値）", loc="left")
ax.legend(frameon=False, fontsize=8.5, loc="lower left")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig1_index.png", "1962〜2025寒候年に50冬以上の値があり、1962〜1991年の平均最深積雪が5cm以上の気象台など。各年の値は地点の指数の中央値")

# fig2 地点ごとの変化（雪の多さ別）
S = pd.read_csv(RES / "station_trends.csv", dtype={"st": str})
S["t"] = pd.qcut(S.base, 3, labels=["少ない3分の1", "中くらい", "多い3分の1"])
fig, ax = plt.subplots(figsize=(8, 4.8))
rng = np.random.default_rng(20261116)
for i, (lab, g) in enumerate(S.groupby("t", observed=False)):
    x = i + rng.uniform(-0.18, 0.18, len(g))
    ax.scatter(x, g.chg_pct, s=34, color=C[i], edgecolor="white", linewidth=1, zorder=3)
    m = g.chg_pct.median()
    ax.hlines(m, i - 0.3, i + 0.3, color="#0b0b0b", lw=2.2, zorder=4)
    ax.text(i + 0.33, m, f"中央値 {m:+.0f}%", va="center", fontsize=8.5, color="#0b0b0b")
    rng_txt = f"{g.base.min():.0f}〜{g.base.max():.0f}cm"
    ax.text(i, -57, rng_txt, ha="center", fontsize=8, color=INK2)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(range(3), ["雪が少ない3分の1", "中くらい", "雪が多い3分の1"]); ax.grid(axis="x", visible=False)
ax.set_ylim(-60, 30); ax.set_xlim(-0.5, 2.9)
ax.set_ylabel("最深積雪の変化（%）\n1962〜1991年平均 → 1996〜2025年平均")
ax.set_title("もともと雪が少ない地点ほど、割合では大きく減った", loc="left")
fig.subplots_adjust(bottom=0.15, left=0.13, right=0.98, top=0.92)
save(fig, "fig2_by_snowiness.png", "1点が1地点。下の数字は、各グループの1962〜1991年の平均最深積雪の範囲")

# fig3 大雪の冬とほとんど積もらない冬の割合（10年ごと）
E = pd.read_csv(RES / "extremes_by_decade.csv"); L = pd.read_csv(RES / "low_by_decade.csv")
lab = ["1962〜65", "66〜75", "76〜85", "86〜95", "96〜2005", "06〜15", "16〜25"]
fig, ax = plt.subplots(figsize=(8, 4.6))
x = np.arange(len(E))
ax.plot(x, 100 * E.ext_share, color=C[0], lw=2, marker="o", ms=7, markeredgecolor="white", label="大雪の冬（1962〜1991年の上位10%を超えた）")
ax.plot(x, 100 * L.low_share, color=C[1], lw=2, marker="o", ms=7, markeredgecolor="white", label="ほとんど積もらない冬（1962〜1991年平均の10%未満）")
for xi, v in zip(x, 100 * E.ext_share): ax.text(xi, v + 0.4, f"{v:.1f}", ha="center", fontsize=8, color=INK2)
for xi, v in zip(x, 100 * L.low_share): ax.text(xi, v - 0.9, f"{v:.1f}", ha="center", fontsize=8, color=INK2)
ax.set_xticks(x, lab); ax.set_ylim(0, 15)
ax.set_xlabel("寒候年"); ax.set_ylabel("地点×冬に占める割合（%）")
ax.set_title("大雪の冬は減り、ほとんど積もらない冬が増えた", loc="left")
ax.legend(frameon=False, fontsize=8.5, loc="upper left")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.92)
save(fig, "fig3_extremes.png", "地点ごとの基準で数え、全地点を合わせた割合")

# fig4 冬の気温と最深積雪
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.scatter(Y.djf, Y.idx_median, s=36, color=C[2], edgecolor="white", linewidth=1, zorder=3)
k = np.polyfit(Y.djf, np.log(Y.idx_median), 1)
xx = np.linspace(Y.djf.min(), Y.djf.max(), 50)
ax.plot(xx, np.exp(np.polyval(k, xx)), color=INK2, lw=1, ls="--")
for _, r in Y[Y.year.isin([1963, 1984, 2006, 2007, 2020, 2016])].iterrows():
    ax.annotate(f"{int(r.year)}", (r.djf, r.idx_median), xytext=(4, 3), textcoords="offset points", fontsize=8, color=INK2)
ax.set_ylim(0, None)
ax.set_xlabel("全国の冬（12〜2月）の気温偏差（℃、1991〜2020年平均との差）")
ax.set_ylabel("最深積雪（1962〜1991年平均＝100、地点の中央値）")
ax.set_title(f"冬が1℃暖かいと、最深積雪は約{-MM['pct_per_deg']:.0f}%少ない", loc="left")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.92)
save(fig, "fig4_winter_temp.png", f"点は寒候年。破線は対数での当てはめ。本文の値（1℃あたり{MM['pct_per_deg']:.0f}%）は地点固定効果つき回帰（年でクラスター頑健標準誤差）")
