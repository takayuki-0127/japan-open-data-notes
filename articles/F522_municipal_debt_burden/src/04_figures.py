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
SRC = "出典：総務省「市町村別決算状況調」（2009・2014・2019・2024年度）をもとに作成者が加工して作成"
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
d = pd.read_csv(R / "muni_year_ratio.csv", dtype={"code": str})
yr = pd.read_csv(R / "by_year.csv").set_index("year")
sz = pd.read_csv(R / "by_year_size.csv")
sp = pd.read_csv(R / "requestion_split.csv")
YEARS = [2009, 2014, 2019, 2024]
LABELS = ["5千人未満", "5千〜1万人", "1万〜3万人", "3万〜10万人", "10万〜30万人", "30万人以上"]
x = np.arange(len(YEARS))

# 図1：将来負担比率の分布
fig, ax = plt.subplots(figsize=(9, 5.4))
data = [d[d.year == y].fbr.clip(upper=300).values for y in YEARS]
ax.boxplot(data, positions=x, widths=0.36, showfliers=False, medianprops={"color": C[1], "lw": 2.2},
           boxprops={"color": INK2}, whiskerprops={"color": INK2}, capprops={"color": INK2})
for i, y in enumerate(YEARS):
    ax.text(i + 0.21, yr.loc[y, "fbr_median"] + 3, f"中央値 {yr.loc[y, 'fbr_median']:.1f}%", fontsize=9.5, color=C[1], va="bottom")
ax.set_xticks(x, [f"{y}年度\n「－」（負担なし）{yr.loc[y, 'fbr_none_pct']:.1f}%" for y in YEARS], fontsize=9.5)
ax.set_ylabel("将来負担比率（%、「－」は0として表示）")
ax.set_ylim(-5, 260); ax.set_xlim(-0.5, 3.95)
finish(fig, ax, f"将来負担比率の中央値は {yr.loc[2009, 'fbr_median']:.1f}% → {yr.loc[2024, 'fbr_median']:.1f}%、半分以上の市町村で負担なしに")
save(fig, "fig1_future_burden_ratio.png")

# 図2：実質公債費比率
fig, ax = plt.subplots(figsize=(9, 5.4))
q = d.groupby("year").rdsr.quantile([.1, .25, .5, .75, .9]).unstack()
ax.fill_between(x, q[0.1], q[0.9], color=C[0], alpha=0.12, lw=0, label="真ん中の80%")
ax.fill_between(x, q[0.25], q[0.75], color=C[0], alpha=0.28, lw=0, label="真ん中の50%")
ax.plot(x, q[0.5], color=C[0], lw=2.4, marker="o", label="中央値")
for i, y in enumerate(YEARS):
    ax.text(i, q.loc[y, 0.5] + 0.5, f"{q.loc[y, 0.5]:.1f}%", ha="center", va="bottom", fontsize=10, color=INK)
    ax.text(i, 1.0, f"18%以上：{int(yr.loc[y, 'rdsr_over18'])}団体", ha="center", fontsize=9, color=INK2)
ax.axhline(18, color=C[1], lw=1, ls="--")
ax.text(3.35, 18.3, "18%（地方債の発行に許可が要る線）", ha="right", va="bottom", fontsize=9, color=C[1])
ax.set_xticks(x, [f"{y}年度" for y in YEARS]); ax.set_xlim(-0.35, 3.35); ax.set_ylim(0, 28)
ax.set_ylabel("実質公債費比率（%）")
ax.legend(loc="upper right", frameon=False, fontsize=9, ncol=3)
finish(fig, ax, f"実質公債費比率の中央値は {yr.loc[2009, 'rdsr_median']:.1f}% → {yr.loc[2024, 'rdsr_median']:.1f}%、2019年度からは下げ止まり")
save(fig, "fig2_debt_service_ratio.png")

# 図3：人口規模別、「－」（負担なし）の割合
fig, ax = plt.subplots(figsize=(9, 5.4))
xs = np.arange(len(LABELS)); w = 0.38
for k, (y, c) in enumerate([(2009, GRID), (2024, C[0])]):
    v = sz[sz.year == y].set_index("size").reindex(LABELS).fbr_none_pct.values
    ax.bar(xs + (k - 0.5) * w, v, w, color=c if y == 2024 else "#b9b8b3", label=f"{y}年度")
    for i, vv in enumerate(v):
        ax.text(xs[i] + (k - 0.5) * w, vv + 1, f"{vv:.0f}", ha="center", va="bottom", fontsize=9, color=INK)
ax.set_xticks(xs, LABELS); ax.set_ylim(0, 90)
ax.set_ylabel("将来負担比率が「－」（負担なし）の団体の割合（%）")
ax.legend(loc="upper right", frameon=False, fontsize=9.5)
s24 = sz[sz.year == 2024].set_index("size")
finish(fig, ax, f"小さな町村ほど負担なしが多い（2024年度：5千人未満 {s24.loc['5千人未満', 'fbr_none_pct']:.0f}%、30万人以上 {s24.loc['30万人以上', 'fbr_none_pct']:.0f}%）")
save(fig, "fig3_no_burden_by_size.png")

# 図4：（地方債−積立金）÷標準財政規模 の変化の分解
fig, ax = plt.subplots(figsize=(9.6, 5.4))
g = ["全体"] + LABELS
t = sp.set_index("group").reindex(g)
xs = np.arange(len(g)); w = 0.2
for k, (col, lab, c) in enumerate([("debt_effect_pt", "地方債の額の変化", C[1]), ("fund_effect_pt", "積立金の額の変化", C[2]),
                                   ("denominator_effect_pt", "標準財政規模の変化", C[3]), ("change_pt", "合計（比の変化）", INK2)]):
    ax.bar(xs + (k - 1.5) * w, t[col].values, w, color=c, label=lab)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(xs, g); ax.set_ylabel("2009→2024年度の変化（ポイント）")
ax.legend(loc="lower right", frameon=False, fontsize=9, ncol=2)
ax.set_ylim(t[["debt_effect_pt", "fund_effect_pt", "denominator_effect_pt", "change_pt"]].values.min() - 22, 12)
a = m["requestion"]["all"]
finish(fig, ax, f"（地方債−積立金）÷標準財政規模の低下 {-a['change_pt']:.1f}pt のうち、積立金の増加の分が {-a['fund_effect_pt']:.1f}pt")
save(fig, "fig4_split_debt_fund.png")
