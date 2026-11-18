"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R, F = ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "svg.hashsalt": "f478"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#999999"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：関西電力送配電・九州電力送配電「エリア需給実績」（7〜9月の平日、1時間値。2024年以降は30分値を1時間に平均）をもとに作成者が加工して作成"
META = {"Software": None}
AREAS = ["関西", "九州"]


def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7.4, color=INK2)
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def style(ax, grid="y"):
    ax.grid(axis=grid, color=GRID, lw=0.8); ax.set_axisbelow(True)


sm = pd.read_csv(R / "summer_summary.csv")
q = json.loads((R / "requestion.json").read_text(encoding="utf-8"))
prof = pd.read_csv(R / "requestion_hourly_profile_by_year.csv")

# 図1：山の時刻（平均）の推移
fig, axs = plt.subplots(1, 2, figsize=(10, 5), sharey=True)
fig.subplots_adjust(left=0.07, right=0.98, top=0.78, bottom=0.17, wspace=0.08)
for ax, area in zip(axs, AREAS):
    s = sm[sm.area == area]
    ax.plot(s.year, s.demand_peak_hour_mean_wd, color=C[0], marker="o", ms=4, lw=2, label="需要の山（平均）")
    ax.plot(s.year, s.resid_peak_hour_mean_wd, color=C[1], marker="o", ms=4, lw=2, label="残余需要の山（平均）")
    ax.plot(s.year, s.demand_peak_hour_median_wd, color=C[0], ls=":", lw=1.2, label="需要の山（中央値）")
    ax.plot(s.year, s.resid_peak_hour_median_wd, color=C[1], ls=":", lw=1.2, label="残余需要の山（中央値）")
    ax.set_title(area, loc="left", fontsize=11); style(ax)
    ax.set_xticks(range(2016, 2027, 2)); ax.set_ylim(12, 19.5)
axs[0].set_ylabel("山の時刻（時台、平日）")
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, frameon=False, fontsize=8.8, loc="upper left", bbox_to_anchor=(0.06, 0.92), ncol=4)
fig.suptitle("山の時刻は2016年からほぼ動かない。九州の残余需要の山は初めから18時台", x=0.01, ha="left", fontsize=12.5, color=INK)
save(fig, "fig1_peak_hours_by_year.png")

# 図2：平日の時刻ごとの平均（期間）
fig, axs = plt.subplots(1, 2, figsize=(10, 5.2))
fig.subplots_adjust(left=0.08, right=0.98, top=0.80, bottom=0.17, wspace=0.22)
for ax, area in zip(axs, AREAS):
    for (y0, y1), ls, lab in [((2016, 2018), "--", "2016〜18年"), ((2024, 2026), "-", "2024〜26年")]:
        p = prof[(prof.area == area) & (prof.year >= y0) & (prof.year <= y1)].groupby("hour")[["demand", "resid"]].mean()
        ax.plot(p.index, p.demand / 1000, color=C[0], ls=ls, lw=1.8, label=f"需要 {lab}")
        ax.plot(p.index, p.resid / 1000, color=C[1], ls=ls, lw=1.8, label=f"残余需要 {lab}")
    ax.set_title(area, loc="left", fontsize=11); style(ax)
    ax.set_xticks(range(0, 24, 3)); ax.set_xlabel("時台")
    ax.axvspan(13.5, 14.5, color=GRID, alpha=0.6); ax.axvspan(17.5, 18.5, color=GRID, alpha=0.6)
axs[0].set_ylabel("平日の平均（GW）"); axs[0].legend(frameon=False, fontsize=8.4, loc="lower right")
fig.suptitle("昼の残余需要が沈み、夕方との差が開いた（灰色は14時台と18時台）", x=0.01, ha="left", fontsize=12.5, color=INK)
save(fig, "fig2_hourly_profiles.png")

# 図3：夏の最大の比（残余需要の最大÷需要の最大）
fig, ax = plt.subplots(figsize=(9, 5))
fig.subplots_adjust(left=0.09, right=0.97, top=0.86, bottom=0.15)
for i, area in enumerate(AREAS):
    s = sm[sm.area == area]
    ax.plot(s.year, s.resid_to_demand_max_ratio * 100, color=C[i], marker="o", lw=2, label=area)
    ax.annotate(f"{s.resid_to_demand_max_ratio.iloc[0] * 100:.1f}%", (2016, s.resid_to_demand_max_ratio.iloc[0] * 100), xytext=(8, -4), textcoords="offset points", fontsize=9, color=C[i])
    ax.annotate(f"{s.resid_to_demand_max_ratio.iloc[-1] * 100:.1f}%", (2026, s.resid_to_demand_max_ratio.iloc[-1] * 100), xytext=(-8, 8), textcoords="offset points", fontsize=9, color=C[i])
ax.set_ylabel("夏の残余需要の最大 ÷ 夏の需要の最大（%）"); ax.set_xticks(range(2016, 2027)); ax.legend(frameon=False)
ax.set_title("火力などで賄う山の高さは、需要の山の9割前後に下がった", loc="left", fontsize=12.5, color=INK, pad=12); style(ax)
save(fig, "fig3_resid_to_demand_max.png")

# 図4：問い直し（18時台−14時台の残余需要）
fig, ax = plt.subplots(figsize=(9, 5))
fig.subplots_adjust(left=0.1, right=0.97, top=0.86, bottom=0.15)
w = 0.38
for i, area in enumerate(AREAS):
    s = q[area]["by_year_gap_mw"]
    ys = np.array(sorted(int(k) for k in s)); vs = np.array([s[str(y)] if str(y) in s else s[y] for y in ys])
    ax.bar(ys + (i - 0.5) * w, vs, w, color=C[i], label=area)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylabel("18時台の残余需要 − 14時台の残余需要（MW、平日の平均）"); ax.set_xticks(range(2016, 2027)); ax.legend(frameon=False)
ax.set_title("夕方の残余需要が昼を上回る幅は、九州で約1.8倍（3年平均）、関西でも0から約700MWへ", loc="left", fontsize=12.5, color=INK, pad=12); style(ax)
save(fig, "fig4_evening_minus_midday.png")
