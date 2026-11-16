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
SRC = "出典：総務省「通信利用動向調査」世帯全体編（自宅でインターネットを利用する世帯の接続回線、複数回答）をもとに作成者が加工して作成"
META = {"Software": None}


def finish(fig, ax, title):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.15)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


a = pd.read_csv(R / "overall_by_year.csv", index_col=0)
yrs = list(a.index)

# 図1
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.axvspan(2023.5, 2025.5, color="#fdecc8", alpha=0.6, lw=0)
ax.text(2024.5, 6, "2024年から選択肢に\n「ホームルーター」", ha="center", fontsize=8.8, color=INK2)
for col, lab, c in [("fixed", "固定系ブロードバンド回線（光・CATV・DSLなど）", C[0]), ("ftth", "うち光回線", C[2]),
                    ("mobile", "携帯電話回線（スマホの回線・ホームルーターなど）", C[1]), ("no_fixed", "固定系を使わない世帯の目安", INK2)]:
    ax.plot(yrs, a[col], color=c, lw=2.2, marker="o", ms=5, ls="--" if col == "no_fixed" else "-", label=lab)
    for y in [2019, 2025]:
        ax.annotate(f"{a[col][y]:.1f}", (y, a[col][y]), textcoords="offset points", xytext=(-8 if y == 2019 else 8, 0),
                    ha="right" if y == 2019 else "left", va="center", fontsize=9, color=INK)
ax.set_xlim(2018.3, 2025.9)
ax.set_ylim(0, 100)
ax.set_xticks(yrs)
ax.set_xlabel("調査の年")
ax.set_ylabel("インターネットを使う世帯に占める割合（%、複数回答）")
ax.legend(frameon=False, loc="upper left", fontsize=8.8)
finish(fig, ax, "光回線などの固定系は減らず、携帯の回線の割合は2024年に跳ねた")
save(fig, "fig1_lines_overall.png")

# 図2：携帯の回線の中身
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for col, lab, c in [("mobile", "携帯電話回線（計）", C[1]), ("lte", "LTE・BWA回線", C[3]), ("g5", "5G回線", C[4]), ("home_router", "ホームルーター", C[0])]:
    s = a[col].dropna()
    ax.plot(s.index, s, color=c, lw=2.2, marker="o", ms=5, label=lab)
    ax.annotate(f"{s.iloc[-1]:.1f}", (s.index[-1], s.iloc[-1]), textcoords="offset points", xytext=(8, 0), va="center", fontsize=9, color=INK)
ax.set_xlim(2018.6, 2025.9)
ax.set_ylim(0, 80)
ax.set_xticks(yrs)
ax.set_xlabel("調査の年")
ax.set_ylabel("インターネットを使う世帯に占める割合（%、複数回答）")
ax.legend(frameon=False, loc="upper left")
finish(fig, ax, "携帯の回線の中身は、LTE から 5G とホームルーターへ")
save(fig, "fig2_mobile_breakdown.png")

# 図3：世帯人員別の固定系
sub = pd.read_csv(R / "by_attribute.csv")
cats = ["単身", "2人家族", "3人家族", "4人家族"]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
x = np.arange(len(cats)); w = 0.38
for i, (y, c) in enumerate([(2019, "#86b6ef"), (2025, C[0])]):
    v = sub[(sub.group == "世帯人員") & (sub.year == y)].set_index("category").loc[cats, "fixed"].values
    ax.bar(x + (i - 0.5) * w, v, w * 0.95, color=c, label=f"{y}年")
    for xi, vi in zip(x, v):
        ax.text(xi + (i - 0.5) * w, vi + 1, f"{vi:.1f}", ha="center", fontsize=9, color=INK)
ax.set_xticks(x, cats)
ax.set_ylim(0, 100)
ax.set_ylabel("固定系ブロードバンド回線を使う割合（%）")
ax.legend(frameon=False, loc="upper left")
finish(fig, ax, "一人暮らしでも固定系を使う割合は上がった（47.6%→57.7%）")
save(fig, "fig3_fixed_by_household_size.png")

# 図4：2023→2024年の跳ね上がりを年齢別に
q = pd.read_csv(R / "requestion_by_age.csv", index_col=0)
fig, ax = plt.subplots(figsize=(8.8, 5.0))
x = np.arange(len(q)); w = 0.38
ax.bar(x - w / 2, q.jump_2019_2023_per_year, w * 0.95, color="#86b6ef", label="2019→2023年の1年あたりの変化")
ax.bar(x + w / 2, q.jump_2023_2024, w * 0.95, color=C[1], label="2023→2024年の変化")
for xi, a1, a2 in zip(x, q.jump_2019_2023_per_year, q.jump_2023_2024):
    ax.text(xi - w / 2, a1 + (0.4 if a1 >= 0 else -1.4), f"{a1:.1f}", ha="center", fontsize=8.8, color=INK)
    ax.text(xi + w / 2, a2 + 0.4, f"{a2:.1f}", ha="center", fontsize=8.8, color=INK)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x, ["世帯主\n" + s.replace("~", "〜") for s in q.index], fontsize=9)
ax.set_ylabel("携帯電話回線の割合の変化（ポイント）")
ax.set_ylim(-3, 28)
ax.legend(frameon=False, loc="upper center", ncol=2, fontsize=9.5)
finish(fig, ax, "2024年の跳ね上がりは、20代から80歳以上まで、どの年齢でも17〜22ポイント")
fig.subplots_adjust(bottom=0.18)
save(fig, "fig4_jump_by_age.png")
