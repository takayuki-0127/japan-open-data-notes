"""図4枚（PNG）。日付などのメタデータは入れない。地方は北から南の順。"""
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
SRC = "出典：国土交通省「建築着工統計調査」（使途別「倉庫」、年度）をもとに作成者が加工して作成"
META = {"Software": None}
REGIONS = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]


def finish(fig, ax, title, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.015, SRC, fontsize=7.6, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
nat = pd.read_csv(R / "national.csv").set_index("fy")

# 図1：全国の倉庫の着工床面積と、関東の割合
fig, (ax, ax2) = plt.subplots(2, 1, figsize=(8.6, 6.2), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]})
ax.plot(nat.index, nat["floor_m2"] / 1e4, color=C[0], lw=2.2)
ax.set_ylabel("万㎡（年度）")
ax.set_ylim(0, 2000)
for fy, lab, dy in [(1990, "1990年度 %.0f万㎡" % m["national_floor_10k_m2"]["peak"], 40),
                    (2009, "2009年度 %.0f万㎡" % m["national_floor_10k_m2"]["min"], -170),
                    (2021, "2021年度 %.0f万㎡" % m["national_floor_10k_m2"]["2021"], 60)]:
    y = nat.loc[fy, "floor_m2"] / 1e4
    ax.scatter([fy], [y], color=C[0], zorder=3, s=22)
    ax.annotate(lab, (fy, y), xytext=(fy + (0.6 if fy != 2021 else -9), y + dy), fontsize=9.5, color=INK)
ax.set_title("倉庫の着工床面積は、2009年度の底から2021年度に3倍余りに（バブル期の水準には届かない）",
             loc="left", fontsize=12, color=INK, pad=10)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax2.plot(nat.index, nat["kanto_share"], color=C[1], lw=2)
ax2.set_ylabel("関東の割合（%）")
ax2.set_ylim(20, 50)
ax2.grid(axis="y", color=GRID, lw=0.8); ax2.set_axisbelow(True)
ax2.set_xlabel("年度")
ax2.text(1988.3, 45.5, "全国に占める関東（1都6県）の割合", fontsize=9.5, color=C[1])
fig.text(0.01, 0.015, SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.92, bottom=0.12, hspace=0.12)
save(fig, "fig1_national_trend.png")

# 図2：地方別の増減（5年度平均の差、万㎡）2つの期間
a = pd.read_csv(R / "contrib_2005_09_to_2015_19.csv", index_col=0).loc[REGIONS]
b = pd.read_csv(R / "contrib_2015_19_to_2021_25.csv", index_col=0).loc[REGIONS]
fig, ax = plt.subplots(figsize=(8.6, 4.9))
x = np.arange(len(REGIONS)); wd = 0.38
ax.bar(x - wd / 2, a["change_10k_m2"], wd, color=C[0], label="2005〜09年度 → 2015〜19年度")
ax.bar(x + wd / 2, b["change_10k_m2"], wd, color=C[3], label="2015〜19年度 → 2021〜25年度")
for i in range(len(REGIONS)):
    for v, off in [(a["change_10k_m2"].iloc[i], -wd / 2), (b["change_10k_m2"].iloc[i], wd / 2)]:
        ax.text(i + off, v + (2 if v >= 0 else -9), f"{v:+.0f}", ha="center", fontsize=8.2, color=INK2)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x, REGIONS)
ax.set_ylabel("年度平均の増減（万㎡）")
ax.set_ylim(-22, 115)
ax.legend(frameon=False, fontsize=9.5, loc="upper right")
finish(fig, ax, "2010年代の増加の多くは関東（この区切りで8割）。2020年代は九州・沖縄や中部でも増えた")
fig.subplots_adjust(left=0.1, right=0.97, top=0.89, bottom=0.14)
save(fig, "fig2_region_change.png")

# 図3：1むねあたりの床面積とむね数（全国）
fig, (ax, ax2) = plt.subplots(1, 2, figsize=(9.0, 4.4))
yr = nat.index
ax.plot(yr, nat["floor_per_bldg"], color=C[0], lw=2)
ax.axvspan(2023.5, 2025.5, color=GRID, alpha=0.6, lw=0)
ax.text(2016.2, 150, "2024・25年度は\nむね数に小数あり", fontsize=8.2, color=INK2)
ax.set_ylabel("1むねあたりの床面積（㎡）")
ax.set_xlabel("年度")
ax.set_ylim(0, 1200)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("1むねあたりは大きくなった", loc="left", fontsize=11.5, color=INK)
ax2.plot(yr, nat["n_bldg"] / 1e3, color=C[1], lw=2)
ax2.set_ylabel("むね数（千むね）")
ax2.set_xlabel("年度")
ax2.set_ylim(0, 60)
ax2.grid(axis="y", color=GRID, lw=0.8); ax2.set_axisbelow(True)
ax2.set_title("建てる数は減った", loc="left", fontsize=11.5, color=INK)
fig.suptitle("倉庫は「数より大きさ」：1むねあたり %.0f㎡（2005〜09年度）→ %.0f㎡（2021〜23年度）"
             % (m["H4_floor_per_bldg_m2"]["2005_09"], m["H4_floor_per_bldg_m2"]["2021_23"]),
             x=0.01, ha="left", fontsize=12, color=INK)
fig.text(0.01, 0.015, SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.08, right=0.98, top=0.83, bottom=0.17, wspace=0.3)
save(fig, "fig3_size_and_count.png")

# 図4：問い直し　地方別に、床面積の伸びを「むね数」と「大きさ」に分ける（log の差）
d = pd.read_csv(R / "requestion_count_size.csv").set_index("region").loc[REGIONS + ["全国"]]
fig, ax = plt.subplots(figsize=(8.6, 4.9))
labels = REGIONS + ["全国"]
x = np.arange(len(labels))
ax.bar(x, d["logdiff_size"], 0.6, color=C[0], label="1むねあたりの大きさの寄与")
ax.bar(x, d["logdiff_n"], 0.6, color=C[1], label="むね数の寄与")
ax.scatter(x, d["logdiff_floor"], color=INK, zorder=3, s=26, label="床面積の変化（合計）")
for i, v in enumerate(d["floor_ratio"]):
    ax.text(i, max(d["logdiff_size"].iloc[i], d["logdiff_floor"].iloc[i]) + 0.04, f"×{v:.2f}", ha="center", fontsize=8.2, color=INK2)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x, labels)
ax.set_ylabel("log の差（2005〜09年度 → 2021〜23年度）")
ax.legend(frameon=False, fontsize=9, loc="lower left", ncol=3)
ax.set_ylim(-0.75, 1.0)
finish(fig, ax, "どの地方でも、むね数は減り、1むねの大きさが増えた（数字は床面積の倍率）")
fig.subplots_adjust(left=0.1, right=0.97, top=0.89, bottom=0.14)
save(fig, "fig4_count_size_decomposition.png")
print("ok")
