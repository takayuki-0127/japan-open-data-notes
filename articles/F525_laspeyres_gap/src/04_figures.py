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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：総務省「地方公務員給与実態調査」「住民基本台帳に基づく人口、人口動態及び世帯数調査」をもとに作成者が加工して作成"
META = {"Software": None}


def finish(fig, ax, title, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.19)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)


m = json.load(open(R / "main.json", encoding="utf-8"))
d = pd.read_csv(ROOT / "data" / "laspeyres.csv", dtype={"code": str})
Y = [2008, 2013, 2018, 2025]
LABELS = ["5千人未満", "5千〜1万人", "1万〜3万人", "3万〜10万人", "10万〜30万人", "30万人以上"]
KIND = ["都道府県", "指定都市", "市", "特別区", "町", "村"]
mu = d[d.kubun >= 3]
x = np.arange(len(Y))

# 図1：市区町村の分布
fig, ax = plt.subplots(figsize=(9, 5.4))
ax.boxplot([mu[mu.year == y].las.values for y in Y], positions=x, widths=0.4, whis=(10, 90), showfliers=False,
           medianprops={"color": C[1], "lw": 2.2}, boxprops={"color": INK2}, whiskerprops={"color": INK2}, capprops={"color": INK2})
for i, y in enumerate(Y):
    s = m["muni"][str(y)]
    ax.text(i + 0.24, s["median"], f"中央値 {s['median']:.1f}\n標準偏差 {s['sd']:.2f}", fontsize=9, color=INK, va="center")
ax.axhline(100, color=INK2, lw=1, ls="--")
ax.text(-0.45, 100.2, "国＝100", fontsize=9, color=INK2, va="bottom")
ax.set_xticks(x, [f"{y}年" + ("\n（参考値）" if y == 2013 else "") for y in Y]); ax.set_xlim(-0.5, 3.8); ax.set_ylim(86, 103)
ax.set_ylabel("ラスパイレス指数（ひげは10%点と90%点）")
finish(fig, ax, f"市区町村の給与水準のばらつきは、標準偏差 {m['muni']['2008']['sd']:.2f} → {m['muni']['2025']['sd']:.2f} に縮んだ")
save(fig, "fig1_spread_by_year.png")

# 図2：団体の種類別の中央値
fig, ax = plt.subplots(figsize=(9, 5.4))
cols = [C[0], C[2], C[3], C[4], C[1], INK2]
last = sorted([(m["kind_median"][f"2025_{kk}"], kk, c) for kk, c in zip(KIND, cols)], reverse=True)
ly, prev = {}, None
for v, kk, c in last:  # 右端の名前が重ならないように、上から順に0.45以上あける
    y_ = v if prev is None else min(v, prev - 0.45)
    ly[kk] = y_; prev = y_
for kk, c in zip(KIND, cols):
    v = [m["kind_median"][f"{y}_{kk}"] for y in Y]
    ax.plot(x, v, color=c, lw=2.2, marker="o", label=kk)
    ax.text(3.08, ly[kk], f"{kk} {v[-1]:.1f}", color=c, fontsize=9, va="center")
ax.axhline(100, color=INK2, lw=1, ls="--")
ax.set_xticks(x, [f"{y}年" for y in Y]); ax.set_xlim(-0.3, 3.75); ax.set_ylim(91, 103.5)
ax.set_ylabel("ラスパイレス指数の中央値")
finish(fig, ax, f"村の中央値は {m['kind_median']['2008_村']:.1f} → {m['kind_median']['2025_村']:.1f}、特別区は {m['kind_median']['2008_特別区']:.1f} → {m['kind_median']['2025_特別区']:.1f}")
save(fig, "fig2_by_kind.png")

# 図3：2025年の人口規模別
m25 = d[(d.year == 2025) & (d.kubun >= 2)].copy()
m25["size"] = pd.cut(m25.pop2025, [0, 5000, 10000, 30000, 100000, 300000, 1e9], right=False, labels=LABELS).astype(str)
fig, ax = plt.subplots(figsize=(9, 5.4))
xs = np.arange(len(LABELS))
rng = np.random.default_rng(0)
for i, s in enumerate(LABELS):
    v = m25[m25["size"] == s].las.values
    ax.scatter(i + rng.uniform(-0.2, 0.2, len(v)), v, s=5, color=C[0], alpha=0.3, lw=0)
ax.boxplot([m25[m25["size"] == s].las.values for s in LABELS], positions=xs, widths=0.5, showfliers=False,
           medianprops={"color": C[1], "lw": 2.2}, boxprops={"color": INK2}, whiskerprops={"color": INK2}, capprops={"color": INK2})
ax.axhline(100, color=INK2, lw=1, ls="--")
ax.set_xticks(xs, LABELS); ax.set_ylim(85, 104)
ax.set_ylabel("ラスパイレス指数（2025年）")
finish(fig, ax, f"人口の多い団体ほど高い（2025年）：中央値 5千人未満 {m['size_median_2025']['5千人未満']:.1f}、30万人以上 {m['size_median_2025']['30万人以上']:.1f}")
save(fig, "fig3_by_size_2025.png")

# 図4：2008年の水準の5分位ごとの変化
q = pd.read_csv(R / "requestion_quintiles.csv")
fig, ax = plt.subplots(figsize=(9, 5.4))
xs = np.arange(len(q))
ax.bar(xs, q.chg_median, 0.6, color=[C[0] if v > 0 else C[1] for v in q.chg_median])
for i, (v, u) in enumerate(zip(q.chg_median, q.up_pct)):
    ax.text(i, v + (0.25 if v > 0 else -0.25), f"{v:+.1f}\n（上がった {u:.0f}%）", ha="center", va="bottom" if v > 0 else "top", fontsize=9, color=INK)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(xs, [f"{a}\n（2008年 {b:.1f}）" for a, b in zip(["低い方の5分の1", "2番目", "3番目", "4番目", "高い方の5分の1"], q.las_08)], fontsize=9)
ax.set_ylim(-3.2, 7.5); ax.set_ylabel("2008→2025年の変化（中央値、ポイント）")
rq = m["requestion"]
finish(fig, ax, f"低かった団体が上がり、高かった団体が下がった（{rq['n_matched']}団体、相関 {rq['r_level_change']:.2f}）")
save(fig, "fig4_change_by_quintile.png")
