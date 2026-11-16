"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：気象庁「生物季節観測累年値ファイル」をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
main = json.load(open(R / "main.json", encoding="utf-8"))
yk = pd.read_csv(R / "yearly_dev_kaede.csv").set_index("year")
yi = pd.read_csv(R / "yearly_dev_ichou.csv").set_index("year")
sk = pd.read_csv(R / "station_span_slopes_kaede.csv")
si = pd.read_csv(R / "station_span_slopes_ichou.csv")
ma = lambda s: s.rolling(5, center=True, min_periods=3).mean()

# ---- 図1：かえで 紅葉日と落葉日の偏差 --------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.9))
x = yk.loc[1955:2025]
for col, lab, c in [("color_dev", "紅葉日", C[1]), ("fall_dev", "落葉日", C[0])]:
    ax.plot(x.index, x[col], color=c, lw=0.8, alpha=0.35)
    ax.plot(x.index, ma(x[col]), color=c, lw=2.4, label=f"{lab}（5年移動平均）")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xlim(1955, 2025); ax.set_ylim(-15, 15)
ax.set_ylabel("地点の平均からのずれ（日）")
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"かえで：紅葉は10年に{main['kaede']['median_slope']['color']:.1f}日、落葉は{main['kaede']['median_slope']['fall']:.1f}日遅く", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：地点ごとに、その地点の全期間の平均を引いたずれを、年ごとに地点で平均。傾きは地点ごとの Theil–Sen の中央値。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig1_kaede_dates.png")

# ---- 図2：期間のずれ ---------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.9))
for d, lab, c in [(yk, "かえで（紅葉→落葉）", C[1]), (yi, "いちょう（黄葉→落葉）", C[2])]:
    z = d.loc[1955:2025]
    ax.plot(z.index, ma(z.span_dev), color=c, lw=2.4, label=lab)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xlim(1955, 2025); ax.set_ylim(-8, 8)
ax.set_ylabel("期間の長さの、地点の平均からのずれ（日）")
ax.legend(loc="upper right", frameon=False, fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"色づいてから散るまでが短く：かえで{main['kaede']['mean_span_1961_1990']:.1f}日→{main['kaede']['mean_span_1996_2025']:.1f}日", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：5年移動平均。日数は1961〜1990年と1996〜2025年の全地点の平均。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig2_span.png")

# ---- 図3：地点ごとの傾き ------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.7))
for k, (s, lab, c) in enumerate([(sk, "かえで", C[1]), (si, "いちょう", C[2])]):
    v = s.slope_per_decade.sort_values().values
    yv = np.full(len(v), k) + (np.arange(len(v)) % 9 - 4) / 25
    ax.scatter(v, yv, s=18, color=c, alpha=0.7, edgecolors="none")
    med = np.median(v)
    ax.plot([med, med], [k - 0.3, k + 0.3], color=INK, lw=2)
    neg = (v < 0).mean() * 100
    ax.text(5.2, k, f"中央値 {med:+.2f}日/10年\n短くなった地点 {neg:.0f}%".replace("+-", "−").replace("-", "−"), va="center", fontsize=9, color=INK)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_yticks([0, 1]); ax.set_yticklabels(["かえで\n（紅葉→落葉）", "いちょう\n（黄葉→落葉）"]); ax.invert_yaxis()
ax.set_xlim(-8, 9.5); ax.set_xlabel("期間の長さの変化（日/10年、地点ごと）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("どちらも、7〜8割の地点で期間が短くなった", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：20年以上の値がある地点。点は地点、縦の線は中央値。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.15, right=0.97, top=0.91, bottom=0.16)
save(fig, "fig3_station_slopes.png")

# ---- 図4：30年の平均の差 -------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.4))
labs = ["色づいた日", "葉が落ちた日", "期間の長さ"]
xx = np.arange(3); w = 0.36
for k, (sp, lab, c) in enumerate([("kaede", "かえで", C[1]), ("ichou", "いちょう", C[2])]):
    v = [main[sp]["period_diff_color_days"], main[sp]["period_diff_fall_days"], main[sp]["period_diff_span_days"]]
    ax.bar(xx + (k - 0.5) * (w + 0.02), v, width=w, color=c, label=lab)
    for xi, vi in zip(xx, v):
        ax.text(xi + (k - 0.5) * (w + 0.02), vi + (0.3 if vi >= 0 else -0.9), f"{vi:+.1f}".replace("-", "−"), ha="center", fontsize=9, color=INK)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(xx); ax.set_xticklabels(labs)
ax.set_ylabel("1996〜2025年の平均 − 1961〜1990年の平均（日）"); ax.set_ylim(-6, 12)
ax.legend(loc="upper right", frameon=False, fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("紅葉の遅れより、落葉の遅れが小さい", loc="left", fontsize=12)
fig.text(0.01, 0.01, f"注：両方の期間に10年以上の値がある地点（かえで{main['kaede']['period_diff_n']}地点、いちょう{main['ichou']['period_diff_n']}地点）の中央値。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.15)
save(fig, "fig4_period_diff.png")
print("ok")
