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
SRC = "出典：国立環境研究所 温室効果ガスインベントリオフィス「日本の温室効果ガス排出量データ」（2026年版・2025年版）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
W = pd.read_csv(R / "series_2026.csv").set_index("fy")
rev = pd.read_csv(R / "vintage_revision.csv").set_index("fy")
pp = pd.read_csv(R / "requestion_post_peak.csv")
C6 = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]

# ---- 図1：CO2 と HFC（2013年度＝100） -----------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
i_co2 = W.CO2_total / W.CO2_total.loc[2013] * 100
i_hfc = W.HFC_total / W.HFC_total.loc[2013] * 100
ax.plot(W.index, i_co2, color=C[0], lw=2.2)
ax.plot(W.index, i_hfc, color=C[1], lw=2.2)
ax.text(2024.4, i_co2.loc[2024], f"CO2\n{i_co2.loc[2024]:.0f}", va="center", fontsize=9.5, color=INK)
ax.text(2024.4, i_hfc.loc[2024], f"HFC\n{i_hfc.loc[2024]:.0f}", va="center", fontsize=9.5, color=INK)
ax.axhline(100, color=INK2, lw=0.8, ls=":")
ax.axvline(2013, color=INK2, lw=0.8, ls=":")
ax.annotate(f"HFCのピーク {main['hfc_peak_year']}年度", (main["hfc_peak_year"], i_hfc.loc[main["hfc_peak_year"]]), xytext=(2009, 150),
            fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.annotate(f"HFCの最小 {main['hfc_min_year']}年度", (main["hfc_min_year"], i_hfc.loc[main["hfc_min_year"]]), xytext=(1996, 35),
            fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.set_xlim(1990, 2027.5); ax.set_ylim(0, 160)
ax.set_ylabel("2013年度＝100")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"2013→2024年度で CO2 は−{abs(main['co2_change_2013_2024_pct']):.0f}%、HFC は+{main['hfc_change_2013_2024_pct']:.0f}%", loc="left", fontsize=12)
fig.text(0.01, 0.01, f"注：HFC は CO2 換算。2024年度は CO2 {main['co2_2024']:.0f}百万トン、HFC {main['hfc_2024']:.1f}百万トン。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig1_co2_vs_hfc_index.png")

# ---- 図2：HFC の用途別（積み上げ） ----------------------------------------------------------------
parts = [("HFC_byproduct_hfc23", "HCFC22製造時の副生HFC23"), ("HFC_refrig_commercial", "業務用冷凍空調機器"),
         ("HFC_refrig_household_ac", "家庭用エアコン"), ("HFC_refrig_car_ac", "カーエアコン"), ("HFC_foam", "発泡剤")]
other = W.HFC_total - sum(W[c] for c, _ in parts)
ys = [W[c].values for c, _ in parts] + [other.values]
labs = [n for _, n in parts] + ["その他（エアゾールなど）"]
fig, ax = plt.subplots(figsize=(8.8, 5.2))
ax.stackplot(W.index, ys, colors=C6, labels=labs, edgecolor="#fcfcfb", linewidth=0.6)
ax.legend(loc="upper left", frameon=False, fontsize=8.8, ncol=2)
ax.set_xlim(1990, 2024); ax.set_ylim(0, 38)
ax.set_ylabel("HFC の排出（百万トンCO2換算）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"工場の副生ガスが減り、冷媒が増えた。2024年度は冷媒が{main['refrig_share_2024_pct']:.0f}%", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：冷媒＝業務用冷凍空調機器・家庭用エアコン・カーエアコン・冷凍空調のその他（その他は図では「その他」に含む）。2026年版。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig2_hfc_by_use.png")

# ---- 図3：ピーク後の減少の内訳（版ごと） --------------------------------------------------------
uses = [("refrig_commercial", "業務用冷凍空調機器"), ("refrig_household_ac", "家庭用エアコン"), ("refrig_car_ac", "カーエアコン"), ("aerosol", "エアゾール・MDI")]
groups = [(2, "2025年版 2021→2023年度"), (1, "2026年版 2021→2023年度"), (0, "2026年版 2021→2024年度")]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
yb = np.arange(len(uses))
hgt = 0.26
for k, (row, lab) in enumerate(groups):
    vals = [pp.loc[row, u] for u, _ in uses]
    pos = yb + (k - 1) * (hgt + 0.02)
    ax.barh(pos, vals, height=hgt, color=C[k], label=f"{lab}（計 {pp.loc[row, 'total_change']:+.2f}）")
    for p_, v in zip(pos, vals):
        ax.text(v + (0.03 if v >= 0 else -0.03), p_, f"{v:+.2f}", va="center", ha="left" if v >= 0 else "right", fontsize=8.4, color=INK)
ax.set_yticks(yb); ax.set_yticklabels([n for _, n in uses]); ax.invert_yaxis()
ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlim(-2.0, 0.5)
ax.set_xlabel("HFC の増減（百万トンCO2換算）")
ax.legend(loc="lower left", frameon=False, fontsize=8.6)
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("ピーク後の減少は業務用が中心。家庭用エアコンの減少は版で変わる", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：ピークの2021年度からの増減。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.2, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig3_post_peak_by_use.png")

# ---- 図4：版による書き換え ----------------------------------------------------------------------
r = rev.loc[2005:]
fig, ax = plt.subplots(figsize=(8.8, 4.8))
ax.plot(r.index, r.hfc_2025ver, color=C[0], lw=2.2, label="2025年版（2025年公表）")
ax.plot(r.index, r.hfc_2026ver, color=C[1], lw=2.2, label="2026年版（2026年公表）")
ax.annotate(f"2023年度 {main['vintage_2023_hfc_2025ver']:.1f}", (2023, main["vintage_2023_hfc_2025ver"]), xytext=(2014.5, 33.5), fontsize=9, color=INK,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.annotate(f"2023年度 {main['vintage_2023_hfc_2026ver']:.1f}", (2023, main["vintage_2023_hfc_2026ver"]), xytext=(2017, 24), fontsize=9, color=INK,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.set_xlim(2005, 2024.5); ax.set_ylim(8, 36)
ax.set_xticks(range(2005, 2025, 3)); ax.set_xticklabels([f"{x}" for x in range(2005, 2025, 3)])
ax.set_ylabel("HFC の排出（百万トンCO2換算）")
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"版の改訂で{main['vintage_max_rev_year']}年度は{abs(main['vintage_max_rev_mt']):.1f}百万トン下に。主に家庭用エアコン", loc="left", fontsize=12)
fig.text(0.01, 0.01, f"注：2022年度の書き換えのうち家庭用エアコン {req['vintage_2022_diff_mt']['家庭用エアコン']:+.2f}、業務用 {req['vintage_2022_diff_mt']['業務用冷凍空調機器']:+.2f}（百万トン）。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig4_vintage_revision.png")
print("ok")
