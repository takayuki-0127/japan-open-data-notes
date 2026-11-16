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
SRC = "出典：総務省「家計調査（家計収支編）」長期時系列表（e-Stat）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
link = pd.read_csv(R / "shares_linked.csv", index_col=0)

# ---- 図1：割合の長期推移 -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.stackplot(link.index, link["away_pct"], link["prepared_pct"], colors=[C[0], C[1]], edgecolor="#fcfcfb", lw=0.8)
ax.text(1975, 4.5, "外食", color="white", fontsize=11)
ax.text(1995, 19.5, "調理食品（中食）", color="white", fontsize=11)
for y in [1963, 1990, 2019, 2025]:
    v = link.loc[y, "both_pct"]
    ax.text(y, v + 0.8, f"{v:.0f}%", ha="left" if y == 1963 else "center", fontsize=9.5, color=INK)
ax.axvline(1999.5, color=INK2, lw=0.8, ls=":")
ax.text(2000, 36.5, "2000年から系列を切り替え\n（農林漁家を含む二人以上の世帯）", fontsize=8.5, color=INK2)
ax.set_xlim(1963, 2025); ax.set_ylim(0, 40)
ax.set_ylabel("食料（外食を含む）に占める割合（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"食費に占める外食＋調理食品は、1963年の{main['both_pct']['1963']:.0f}%から2025年の{main['both_pct']['2025']:.0f}%に", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：二人以上の世帯。1999年までは農林漁家世帯を除く。外食は学校給食を含む。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig1_share_long_term.png")

# ---- 図2：名目・実質・物価 ---------------------------------------------------------------
ix = pd.read_csv(R / "nominal_real_price_index.csv")
fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.7), sharey=True)
for ax, item in zip(axes, ["調理食品", "外食"]):
    q = ix[ix.item == item]
    for col, lab, c, ls in [("nominal_idx", "支出（名目）", INK, "-"), ("price_idx", "物価の分", C[1], "--"), ("real_idx", "量の分（実質）", C[0], "-")]:
        ax.plot(q.year, q[col], color=c, lw=2, ls=ls)
        ax.text(2025.5, q[col].iloc[-1], f"{lab}\n{q[col].iloc[-1]:.0f}", fontsize=8.8, color=INK, va="center")
    ax.axhline(100, color=INK2, lw=0.8, ls=":")
    ax.set_xlim(2000, 2033); ax.set_title(item, loc="left", fontsize=11)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
axes[0].set_ylabel("2000年＝100")
dd = main["decomposition_2000_2025"]["調理食品"]
fig.suptitle(f"調理食品の支出の伸び（+{dd['nominal_change_pct']:.0f}%）の{dd['price_share_of_log_growth_pct']:.0f}%は値上がり。外食は量が2000年より{abs(main['decomposition_2000_2025']['外食']['real_change_pct']):.0f}%少ない",
             x=0.01, ha="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：二人以上の世帯。量の分は家計調査の実質増減率（消費者物価指数で実質化）を積み上げたもの。物価の分＝名目÷実質。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.9, top=0.86, bottom=0.15, wspace=0.35)
save(fig, "fig2_nominal_real_price.png")

# ---- 図3：世帯の形 ------------------------------------------------------------------------
sa = pd.read_csv(R / "shares_all.csv")
fig, ax = plt.subplots(figsize=(8.6, 4.9))
for s, lab, c in [("単身(2000-)", "単身世帯", C[1]), ("総世帯(2000-)", "総世帯", C[2]), ("二人以上(2000-)", "二人以上の世帯", C[0])]:
    q = sa[sa.series == s]
    ax.plot(q.year, q.both_pct, color=c, lw=2, marker="o", ms=3.5)
    ax.text(2025.4, q.both_pct.iloc[-1], f"{lab}\n{q.both_pct.iloc[-1]:.0f}%", fontsize=9, color=INK, va="center")
ax.set_xlim(2000, 2030); ax.set_ylim(20, 60)
ax.set_ylabel("食料に占める外食＋調理食品の割合（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"単身世帯の割合は{main['household_type_2000_both_pct']['単身']:.0f}%から{main['household_type_2025_both_pct']['単身']:.0f}%に下がり、二人以上の世帯は上がった", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：2000〜2025年。外食は学校給食を含む。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig3_household_types.png")

# ---- 図4：問い直し（折れ目） -----------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.6, 4.9))
for col, lab, c in [("away_pct", "外食", C[0]), ("prepared_pct", "調理食品", C[1])]:
    q = link.loc[1963:2019, col]
    ax.plot(q.index, q.values, color=c, lw=0, marker="o", ms=3.5)
    b = req["q1"][f"{col}_1963-2019"]
    x = q.index.values.astype(float); bb = b["break_year"]
    X = np.column_stack([np.ones_like(x), x - bb, np.clip(x - bb, 0, None)])
    coef, *_ = np.linalg.lstsq(X, q.values, rcond=None)
    ax.plot(x, X @ coef, color=c, lw=2)
    ax.text(2020.5, (X @ coef)[-1], f"{lab}\n折れ目 {bb}年\n前 +{b['slope_before_pt_per_10y']:.1f}／後 +{b['slope_after_pt_per_10y']:.1f}\n（ポイント／10年）", fontsize=8.6, color=INK, va="center")
ax.set_xlim(1963, 2034); ax.set_ylim(0, 22)
ax.set_ylabel("食料に占める割合（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"外食の割合の伸びは{req['q1']['away_pct_1963-2019']['break_year']}年ごろにほぼ止まり、調理食品は伸び続けた", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：二人以上の世帯、1963〜2019年（2020年からの落ち込みの前）。点は実績、線は1か所で傾きが変わる直線を当てはめたもの。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig4_break_years.png")
print("figures done")
