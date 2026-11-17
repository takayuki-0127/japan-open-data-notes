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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：厚生労働省「就労条件総合調査」（労働者1人平均年間休日総数、各年1月1日現在）をもとに作成者が加工して作成"
META = {"Software": None}
SHORT = {"F": "電気・ガス・熱供給・水道業", "G": "情報通信業", "L": "学術研究・専門技術サービス業",
         "H": "運輸業・郵便業", "M": "宿泊業・飲食サービス業", "N": "生活関連サービス業・娯楽業"}


def finish(fig, ax, title):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.8, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
w = pd.read_csv(R / "industry_mean_days.csv", index_col=0)
low3, high3 = m["hypotheses"]["H3"]["low3"], m["hypotheses"]["H3"]["high3"]
Y1 = m["years"][1]

# 図1：分類の順（F, G, H, L, M, N）に並べる
fig, ax = plt.subplots(figsize=(8.8, 5.0))
order = sorted(high3 + low3)
ends = {c: w[c][Y1] for c in order}
pos, prev = {}, None
for c in sorted(ends, key=lambda k: -ends[k]):
    y = ends[c] if prev is None else min(ends[c], prev - 1.1)
    pos[c] = y; prev = y
for c, col in zip(order, C):
    ls = "-" if c in high3 else "--"
    ax.plot(w.index, w[c], color=col, lw=2.0, ls=ls, marker="o", ms=3.5, label=SHORT[c] + ("（2009年に多い）" if c in high3 else "（2009年に少ない）"))
    ax.annotate(f"{w[c][Y1]:.1f}", (Y1, w[c][Y1]), xytext=(Y1 + 0.3, pos[c]), textcoords="data", va="center", fontsize=8.8, color=INK)
tot = pd.Series({int(k): v for k, v in m["total"].items()}).loc[2009:]
ax.plot(tot.index, tot, color=INK2, lw=2.4, label="調査計（全産業）")
ax.set_xlim(2008.5, 2026.3)
ax.set_ylim(90, 128)
ax.set_xlabel("調査の年（各年1月1日現在）")
ax.set_ylabel("労働者1人平均の年間休日（日）")
ax.legend(frameon=False, loc="lower right", fontsize=8.6, ncol=2)
finish(fig, ax, "休日の少なかった産業が増え、多い産業はほぼ横ばい")
fig.subplots_adjust(left=0.09, right=0.96, top=0.89, bottom=0.15)
save(fig, "fig1_high_low_industries.png")

# 図2：産業間の差
sp = pd.read_csv(R / "spread_by_year.csv", index_col=0)
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(sp.index, sp["range"], color=C[0], lw=2.2, marker="o", ms=5, label="最も多い産業と少ない産業の差（範囲）")
ax.plot(sp.index, sp["sd"], color=C[1], lw=2.2, marker="o", ms=5, label="産業間の標準偏差（ばらつき）")
for col in ["range", "sd"]:
    for y in [2009, Y1]:
        ax.annotate(f"{sp[col][y]:.1f}", (y, sp[col][y]), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9, color=INK)
ax.set_ylim(0, 30)
ax.set_xlabel("調査の年")
ax.set_ylabel("日数（日）")
ax.legend(frameon=False, loc="upper right")
finish(fig, ax, "15産業の年間休日の差は、25.2日から15.6日に縮んだ")
fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.15)
save(fig, "fig2_spread.png")

# 図3：企業規模
sz = pd.read_csv(R / "size_mean_days.csv", index_col=0)
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for c, lab, col in [("1000+", "1,000人以上", C[0]), ("300-999", "300〜999人", C[2]), ("100-299", "100〜299人", C[3]), ("30-99", "30〜99人", C[1])]:
    ax.plot(sz.index, sz[c], color=col, lw=2.2, marker="o", ms=4, label=lab)
    ax.annotate(f"{sz[c][Y1]:.1f}", (Y1, sz[c][Y1]), textcoords="offset points", xytext=(6, 0), va="center", fontsize=9, color=INK)
ax.set_xlim(2001, 2026.8)
ax.set_xlabel("調査の年")
ax.set_ylabel("労働者1人平均の年間休日（日）")
ax.legend(frameon=False, loc="lower right")
g = m["size_gap"]
finish(fig, ax, f"1,000人以上と30〜99人の差は、2009年{g['2009']:.1f}日→{Y1}年{g[str(Y1)]:.1f}日")
fig.subplots_adjust(left=0.09, right=0.96, top=0.89, bottom=0.15)
save(fig, "fig3_by_size.png")

# 図4：少ない3産業の階級
q = pd.read_csv(R / "requestion_classes.csv", index_col=0)
fig, ax = plt.subplots(figsize=(8.8, 5.0))
codes = sorted(low3)
x = np.arange(len(codes)); w4 = 0.2
for i, (col, lab, c) in enumerate([("share_under100_2009", "100日未満 2009年", "#f4b393"), ("share_under100_" + str(Y1), f"100日未満 {Y1}年", C[1]),
                                    ("share_120plus_2009", "120日以上 2009年", "#86b6ef"), ("share_120plus_" + str(Y1), f"120日以上 {Y1}年", C[0])]):
    v = q.loc[codes, col].values
    ax.bar(x + (i - 1.5) * w4, v, w4 * 0.95, color=c, label=lab)
    for xi, vi in zip(x, v):
        ax.text(xi + (i - 1.5) * w4, vi + 0.8, f"{vi:.0f}", ha="center", fontsize=8.5, color=INK)
ax.set_xticks(x, [SHORT[c] for c in codes])
ax.set_ylabel("その産業の労働者に占める割合（%）")
ax.legend(frameon=False, loc="upper right", ncol=2, fontsize=9)
ax.set_ylim(0, 75)
finish(fig, ax, "休日の少なかった産業では「年100日未満」の働き手が大きく減った")
fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.15)
save(fig, "fig4_classes_low3.png")
