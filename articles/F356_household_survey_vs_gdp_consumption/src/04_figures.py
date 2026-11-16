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
SRC = "出典：総務省「家計調査」「国勢調査」、内閣府「四半期別GDP速報」をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
d = pd.read_csv(R / "annual_indicators.csv").set_index("year")
t = pd.read_csv(R / "requestion_same_units.csv").set_index("year")
dc = pd.read_csv(R / "decomposition.csv").iloc[0]

# ---- 図1：名目の指数 --------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for col, lab, c, ls in [("gdp_hh_exrent_nom_idx", "GDP 家計最終消費支出（除く持ち家の帰属家賃）", C[1], "-"), ("survey_agg_idx", "家計調査 総世帯×世帯数", C[2], "--"),
                        ("tp_cons_month_idx", "家計調査 二人以上の世帯 1世帯あたり", C[0], "-"), ("th_cons_year_idx", "家計調査 総世帯 1世帯あたり", C[3], "-")]:
    ax.plot(d.index, d[col], color=c, lw=2.2, ls=ls, label=f"{lab}（2025年 {d[col].iloc[-1]:.0f}）")
ax.axhline(100, color=INK2, lw=0.8, ls=":")
ax.legend(loc="upper left", frameon=False, fontsize=8.8)
ax.set_xlim(2000, 2025.5); ax.set_ylim(80, 130)
ax.set_ylabel("名目、2000年＝100")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("2000→2025年、家計調査の1世帯あたりは−1%、GDPの家計消費は+18%（名目）", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：世帯数は国勢調査の一般世帯数（5年ごと）を一定の率でつないだ値。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig1_nominal_index.png")

# ---- 図2：差の分解（2000→2025年、対数×100） ------------------------------------------------------
steps = [("家計調査\n二人以上\n1世帯あたり", dc.two_plus), ("総世帯に\n広げる", dc.part_coverage), ("世帯数を\n掛ける", dc.part_households), ("残り", dc.part_residual)]
fig, ax = plt.subplots(figsize=(8.8, 4.8))
cum = 0.0
for i, (lab, v) in enumerate(steps):
    v100 = v * 100
    bottom = cum if i > 0 else 0
    ax.bar(i, v100, bottom=bottom, width=0.6, color=C[0] if i == 0 else (C[2] if v100 >= 0 else C[1]))
    ax.text(i, bottom + v100 + (0.8 if v100 >= 0 else -0.8), f"{v100:+.1f}", ha="center", va="bottom" if v100 >= 0 else "top", fontsize=9.5, color=INK)
    cum = bottom + v100
ax.bar(len(steps), dc.gdp * 100, width=0.6, color=C[3])
ax.text(len(steps), dc.gdp * 100 + 0.8, f"{dc.gdp*100:+.1f}", ha="center", va="bottom", fontsize=9.5, color=INK)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(range(len(steps) + 1)); ax.set_xticklabels([s for s, _ in steps] + ["GDP\n家計消費\n（除く帰属家賃）"], fontsize=9)
ax.set_ylim(-12, 26); ax.set_ylabel("2000→2025年の伸び（対数×100、名目）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"総世帯に広げて世帯数を掛けると、GDPとの差の{dc.share_closed_by_households*100:.0f}%が埋まる", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：左から順に足すと右端のGDPになる。「残り」は消費の範囲の違いや標本のぶれなどを合わせたもの。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.2)
save(fig, "fig2_gap_decomposition.png")

# ---- 図3：同じ単位で実質を比べる ---------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.8), sharey=True)
for ax, pairs, ttl in [(axes[0], [("gdp_real_per_household", "GDP", C[1]), ("survey_total_real_per_household", "家計調査 総世帯", C[3]), ("survey_two_plus_real_per_household", "家計調査 二人以上", C[0])], "1世帯あたり（実質）"),
                       (axes[1], [("gdp_real_per_person", "GDP", C[1]), ("survey_total_real_per_person", "家計調査 総世帯", C[3])], "1人あたり（実質）")]:
    for col, lab, c in pairs:
        ax.plot(t.index, t[col], color=c, lw=2.2, label=f"{lab}（2025年 {t[col].iloc[-1]:.0f}）")
    ax.axhline(100, color=INK2, lw=0.8, ls=":")
    ax.set_title(ttl, loc="left", fontsize=11)
    ax.legend(loc="lower left", frameon=False, fontsize=8.8)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    ax.set_xlim(2000, 2025.5)
axes[0].set_ylim(70, 120); axes[0].set_ylabel("2000年＝100")
fig.suptitle("単位をそろえると差は小さい：1世帯あたりはどちらも実質で1〜2割減", x=0.01, ha="left", fontsize=12)
fig.text(0.01, 0.01, "注：家計調査の総世帯は名目のため、GDPの家計消費（除く帰属家賃）のデフレーターで実質化した。二人以上は家計調査の実質増減率をつないだ。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.98, top=0.86, bottom=0.15, wspace=0.08)
save(fig, "fig3_same_units_real.png")

# ---- 図4：前年比 ----------------------------------------------------------------------------------
g_s = d.tp_real_idx.pct_change() * 100; g_g = d.gdp_hh_exrent_real.pct_change() * 100
fig, ax = plt.subplots(figsize=(8.8, 4.8))
ax.plot(d.index, g_g, color=C[1], lw=2, marker="o", ms=4, label="GDP 家計消費（実質、除く帰属家賃）")
ax.plot(d.index, g_s, color=C[0], lw=2, marker="o", ms=4, label="家計調査 二人以上の世帯（実質）")
ax.axhline(0, color=INK2, lw=0.8)
ax.legend(loc="lower left", frameon=False, fontsize=9)
ax.set_xlim(2000.5, 2025.5); ax.set_ylim(-8, 6)
ax.set_ylabel("前年比（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
H4 = main["hypotheses"]["H4"]
ax.set_title(f"前年比の相関は{H4['corr']:.2f}（2020・2021年を除くと{H4['corr_excl_2020_21']:.2f}）", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：家計調査の二人以上の世帯は1世帯あたり、GDPは国全体の総額。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig4_yoy.png")
print("figures ok")
