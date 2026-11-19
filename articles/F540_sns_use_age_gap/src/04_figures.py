"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE = pathlib.Path(__file__).resolve().parent.parent
R = BASE / "results"; F = BASE / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "svg.hashsalt": "f540"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#8a5cc7"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：総務省「通信利用動向調査」世帯構成員編（2015〜2025年）をもとに作成者が加工して作成"
META = {"Software": None}
AGE_JP = {"13-19": "13〜19歳", "20-29": "20代", "30-39": "30代", "40-49": "40代", "50-59": "50代", "60-69": "60代", "70-79": "70代", "80+": "80歳以上"}


def finish(fig, ax, title):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.012, SRC, fontsize=7.8, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def bands(ax):
    for x0 in (2019.5, 2020.5):
        ax.axvspan(x0, x0 + 1, color="#f1efe9", zorder=0)
    ax.text(2020.5, ax.get_ylim()[1] * 0.985, "選択肢の\n言い方が変わった年", ha="center", va="top", fontsize=8.3, color=INK2)


m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
P = pd.read_csv(R / "wide_p_all.csv", index_col="year").loc[2015:2025]
S = pd.read_csv(R / "wide_s.csv", index_col="year").loc[2015:2025]
G = pd.read_csv(R / "gaps_by_year.csv", index_col="year").loc[2015:2025]
J = pd.read_csv(R / "change_year_jumps.csv", index_col="age")

# 図1 年齢別の SNS を使う人の割合（人口ベース）
fig, ax = plt.subplots(figsize=(8.4, 5.0))
for i, a in enumerate(["20-29", "40-49", "60-69", "70-79", "80+"]):
    ax.plot(P.index, P[a], color=C[i], lw=2.2, marker="o", ms=3.5)
    nudge = {"20-29": 2.2, "40-49": -2.2}.get(a, 0)
    ax.text(2025.25, P.loc[2025, a] + nudge, f"{AGE_JP[a]} {P.loc[2025, a]:.1f}%", va="center", fontsize=9.3, color=C[i])
ax.set_ylim(0, 100); ax.set_xlim(2014.6, 2027.4)
ax.set_xticks(range(2015, 2026, 2))
ax.set_ylabel("その年齢の人のうち SNS を使った人（%）")
bands(ax)
finish(fig, ax, "70代は2015年の6%から2025年の44%に。80歳以上は16%で、20代との差は縮んでいない")
fig.text(0.01, 0.045, "注：SNS の割合（ネットを使う人のうち）×ネットを使った人の割合（全員のうち。無回答は使わない側）。", fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.98, top=0.88, bottom=0.14)
save(fig, "fig1_sns_by_age.png")

# 図2 20代と70代の差：人口ベースと利用者ベース
fig, ax = plt.subplots(figsize=(8.4, 4.8))
ax.plot(G.index, G["p_all__gap_20_70"], color=C[0], lw=2.4, marker="o", ms=3.5, label="人口ベース（全員のうち）")
ax.plot(G.index, G["s__gap_20_70"], color=C[1], lw=2.4, marker="o", ms=3.5, label="利用者ベース（ネットを使う人のうち）")
for col, c, dy in [("p_all__gap_20_70", C[0], 3), ("s__gap_20_70", C[1], -5)]:
    for y in (2015, 2025):
        ax.annotate(f"{G.loc[y, col]:.1f}", (y, G.loc[y, col]), xytext=(0, dy + (2 if dy > 0 else -6)), textcoords="offset points", ha="center", fontsize=9, color=c)
ax.set_ylim(0, 80); ax.set_xticks(range(2015, 2026, 2))
ax.set_ylabel("20代 − 70代（ポイント）")
ax.legend(frameon=False, loc="lower left")
bands(ax)
finish(fig, ax, "ネットを使う人の中の差は半分以下に。全員で見た差の縮みは3割")
fig.subplots_adjust(left=0.09, right=0.98, top=0.88, bottom=0.11)
save(fig, "fig2_gap_two_bases.png")

# 図3 2015→2025 の伸びを分ける（年齢別）
ages = ["50-59", "60-69", "70-79", "80+"]
dec = {a: (m["H2"] if a == "70-79" else m["H2_other"][a]) for a in ages}
fig, ax = plt.subplots(figsize=(8.4, 4.6))
x = np.arange(len(ages))
ps = [dec[a]["part_s_pt"] for a in ages]; pu = [dec[a]["part_u_pt"] for a in ages]
ax.bar(x, ps, color=C[1], width=0.55, label="ネットを使う人のうち SNS を使う割合が増えた分")
ax.bar(x, pu, bottom=ps, color=C[0], width=0.55, label="ネットを使う人が増えた分")
for i, a in enumerate(ages):
    ax.text(i, ps[i] + pu[i] + 1, f"計 +{dec[a]['dp_pt']:.1f}", ha="center", fontsize=9.5, color=INK)
    ax.text(i, ps[i] / 2, f"{ps[i]:.1f}", ha="center", va="center", fontsize=9, color="white")
    ax.text(i, ps[i] + pu[i] / 2, f"{pu[i]:.1f}", ha="center", va="center", fontsize=9, color="white")
ax.set_xticks(x, [AGE_JP[a] for a in ages]); ax.set_ylim(0, 60)
ax.set_ylabel("2015→2025年の伸び（ポイント）")
ax.legend(frameon=False, loc="upper right", fontsize=9)
finish(fig, ax, "70代の伸び（+37.5）の7割は、ネットを使う人の中で SNS が広がった分")
fig.subplots_adjust(left=0.09, right=0.98, top=0.88, bottom=0.11)
save(fig, "fig3_decomposition.png")

# 図4 選択肢が変わった年の伸び
ages = ["13-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"]
fig, ax = plt.subplots(figsize=(8.4, 4.8))
x = np.arange(len(ages)); w = 0.27
ax.bar(x - w, [J.loc[a, "mean_d_around"] for a in ages], w, color="#b9b7b0", label="ほかの年の平均（2016〜19・2022〜25年）")
ax.bar(x, [J.loc[a, "d_2019_2020"] for a in ages], w, color=C[1], label="2019→2020年（無料通話の選択肢がなくなった）")
ax.bar(x + w, [J.loc[a, "d_2020_2021"] for a in ages], w, color=C[0], label="2020→2021年（「無料通話機能を含む」に）")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x, [AGE_JP[a] for a in ages], fontsize=9.5)
ax.set_ylabel("ネットを使う人のうち SNS の割合の1年の伸び（ポイント）")
ax.legend(frameon=False, loc="upper left", fontsize=8.8)
ax.set_ylim(-5, 27)
finish(fig, ax, "60代以上の伸びは、選択肢が変わった2つの年に集中している")
fig.subplots_adjust(left=0.09, right=0.98, top=0.88, bottom=0.11)
save(fig, "fig4_change_years.png")
print("ok")
