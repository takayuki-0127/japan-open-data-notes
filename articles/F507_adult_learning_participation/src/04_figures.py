"""図4枚（PNG）。日付などのメタデータは入れない。数字は results から読む。"""
import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from common import ROOT

R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#8a63d2"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：総務省統計局「社会生活基本調査」（時系列統計表 第1表、2016・2021年 第1-4表）をもとに作成者が加工して作成"
META = {"Software": None}
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
YEARS = [1986, 1991, 1996, 2001, 2006, 2011, 2016, 2021]


def finish(fig, ax, title, sub=None):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=22 if sub else 12)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9, color=INK2)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    fig.text(0.01, 0.012, SRC, fontsize=7.6, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


# ---- 図1：年齢をそろえた行動者率の推移 ----
fig, ax = plt.subplots(figsize=(8.6, 5.0)); fig.subplots_adjust(left=0.08, right=0.84, top=0.85, bottom=0.14)
ax.axvspan(1993.5, 1998.5, color="#efeeea", zorder=0)
ax.text(1996, 45.5, "1996年は\n多くの年齢で低い", ha="center", fontsize=8.5, color=INK2)
for key, lab, c in [("std_25_64", "25〜64歳", C[0]), ("std_65plus", "65歳以上", C[1])]:
    ys = [m[key][str(y)] for y in YEARS]
    ax.plot(YEARS, ys, color=c, lw=2, marker="o", ms=6, mec="#fcfcfb", mew=1.5, label=lab)
    ax.text(2021.8, ys[-1], f"{lab} {ys[-1]:.1f}%", va="center", fontsize=10, color=INK)
    ax.text(YEARS[0] - 0.6, ys[0], f"{ys[0]:.1f}", va="center", ha="right", fontsize=9, color=INK2)
ax.text(2001, m["std_25_64"]["2001"] + 1.4, f"{m['std_25_64']['2001']:.1f}", ha="center", fontsize=9, color=INK2)
ax.text(2001, m["std_65plus"]["2001"] - 2.6, f"{m['std_65plus']['2001']:.1f}", ha="center", fontsize=9, color=INK2)
ax.set_xticks(YEARS); ax.set_ylim(0, 50); ax.set_xlim(1983, 2023)
ax.set_ylabel("行動者率（%）"); ax.legend(loc="lower right", frameon=False)
finish(fig, ax, "働く世代はほぼ横ばいが続き、2021年に上がった。65歳以上は2000年代に上がった",
       "学習・自己啓発・訓練（学業・職場の研修を除く）を過去1年にした人の割合。年齢の構成を2021年にそろえた値")
save(fig, "fig1_std_trend.png")

# ---- 図2：年齢別、2001・2016・2021年 ----
ages = list(m["age_rates_total"].keys())
fig, ax = plt.subplots(figsize=(8.6, 5.0)); fig.subplots_adjust(left=0.08, right=0.98, top=0.85, bottom=0.17)
wbar = 0.26
for i, (y, c) in enumerate([(2001, "#b9b8b3"), (2016, C[0] + "88"), (2021, C[0])]):
    xs = [j + (i - 1) * (wbar + 0.02) for j in range(len(ages))]
    vals = [m["age_rates_total"][a][str(y)] for a in ages]
    ax.bar(xs, vals, width=wbar, color=c, label=f"{y}年")
    if y == 2021:
        for x, v in zip(xs, vals):
            ax.text(x, v + 0.6, f"{v:.1f}", ha="center", fontsize=8.5, color=INK)
ax.set_xticks(range(len(ages))); ax.set_xticklabels([f"{a}\n（{m['ages_up_2016_2021'][a]:+.1f}）" for a in ages])
ax.set_ylim(0, 58); ax.set_ylabel("行動者率（%）"); ax.legend(frameon=False, ncol=3, loc="upper right")
finish(fig, ax, "2016→2021年はどの年齢も上がり、30代の上がり方が最も大きい", "年齢別の行動者率（%）。年齢の下のかっこは2016→2021年の差（ポイント）")
save(fig, "fig2_by_age.png")

# ---- 図3：種類別（25〜64歳、2001年から）----
Y2 = [2001, 2006, 2011, 2016, 2021]
fig, ax = plt.subplots(figsize=(8.6, 5.0)); fig.subplots_adjust(left=0.08, right=0.74, top=0.85, bottom=0.14)
items = [("computing", "パソコンなどの情報処理", C[0]), ("business", "ビジネス（パソコン除く）", C[5]),
         ("foreign", "外国語", C[1]), ("home", "家政・家事", C[2]), ("humanities", "人文・社会・自然科学", C[3]), ("arts", "芸術・文化", C[4])]
last = []
for k, lab, c in items:
    ys = [m["kind_25_64"][k][str(y)] for y in Y2]
    ax.plot(Y2, ys, color=c, lw=2, marker="o", ms=6, mec="#fcfcfb", mew=1.5, label=lab)
    last.append([ys[-1], lab])
last.sort()
pos = []
for v, lab in last:  # 右端のラベルが重ならないよう少しずらす
    p = v if not pos or v - pos[-1] >= 1.0 else pos[-1] + 1.0
    pos.append(p)
    ax.text(2021.6, p, f"{lab} {v:.1f}%", va="center", fontsize=9, color=INK)
ax.set_xticks(Y2); ax.set_ylim(0, 26); ax.set_xlim(2000, 2022)
ax.set_ylabel("行動者率（%）")
ax.text(2001, m["kind_25_64"]["computing"]["2001"] + 0.9, f"{m['kind_25_64']['computing']['2001']:.1f}", ha="center", fontsize=9, color=INK2)
finish(fig, ax, "パソコンの学習は2001年の山から下がり、2021年に戻りかけた",
       "25〜64歳、種類別の行動者率（年齢の構成を2021年にそろえた値）。種類の区分がそろう2001年から")
save(fig, "fig3_by_kind.png")

# ---- 図4：目的別（問い直し）----
P = [("自分の教養を高めるため", "自分の教養を\n高めるため"), ("現在の仕事に役立てるため", "現在の仕事に\n役立てるため"),
     ("仕事につくため", "仕事に\nつくため"), ("その他", "その他")]
fig, ax = plt.subplots(figsize=(8.6, 5.0)); fig.subplots_adjust(left=0.08, right=0.98, top=0.85, bottom=0.16)
for i, (y, c) in enumerate([("2016", C[0] + "88"), ("2021", C[0])]):
    xs = [j + (i - 0.5) * 0.36 for j in range(len(P))]
    vals = [q["total_by_purpose"][p][y] for p, _ in P]
    ax.bar(xs, vals, width=0.34, color=c, label=f"{y}年")
    for x, v in zip(xs, vals):
        ax.text(x, v + 0.4, f"{v:.1f}", ha="center", fontsize=9, color=INK)
for j, (p, _) in enumerate(P):
    ax.text(j, max(q["total_by_purpose"][p]["2021"], q["total_by_purpose"][p]["2016"]) + 2.4,
            f"+{q['total_by_purpose'][p]['diff']:.1f}ポイント", ha="center", fontsize=9, color=INK2)
ax.set_xticks(range(len(P))); ax.set_xticklabels([l for _, l in P])
ax.set_ylim(0, 28); ax.set_ylabel("行動者率（%）"); ax.legend(frameon=False, loc="upper right")
finish(fig, ax, "上がった分は、教養のための学習と仕事のための学習の両方",
       "25〜64歳、目的別の行動者率（年齢の構成を2021年にそろえた値）。目的は複数選べる")
save(fig, "fig4_purpose.png")
