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
SRC = "出典：内閣府「県民経済計算」（2011〜2023年度）をもとに作成者が加工して作成"
META = {"Software": None}


def finish(fig, ax, title, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.19)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
P = pd.read_csv(R / "pref_2019_2023.csv", dtype={"code": str}).sort_values("code").reset_index(drop=True)
Q = pd.read_csv(R / "requestion_factor_income.csv", dtype={"code": str}).sort_values("code").reset_index(drop=True)
short = lambda s: s if s == "北海道" else s[:-1]

# 図1：県ごとの移出入（純）の県内総生産比（北から南の順）
fig, ax = plt.subplots(figsize=(10, 5.6))
x = np.arange(len(P))
ax.bar(x, P.nx, 0.72, color=[C[0] if v > 0 else C[1] for v in P.nx])
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x, [short(s) for s in P.pref], rotation=90, fontsize=8.5)
ax.set_xlim(-0.8, len(P) - 0.2)
ax.set_ylabel("移出入（純）÷県内総生産（%）")
ax.text(0.99, 0.97, "青：黒字（県外・海外へ売る方が多い）\n橙：赤字（県外・海外から買う方が多い）", transform=ax.transAxes, ha="right", va="top", fontsize=9, color=INK2)
finish(fig, ax, f"県の外との取引（2019〜2023年度の平均）：黒字は47のうち{m['n_positive']}、東京都は県内総生産の{m['tokyo_nx']:.0f}%")
fig.subplots_adjust(bottom=0.2)
save(fig, "fig1_netexports_by_pref.png")


def scatter(col, xlab, name, title):
    fig, ax = plt.subplots(figsize=(9, 5.6))
    t = P.pref == "東京都"
    ax.scatter(P[~t][col], P[~t].nx, s=28, color=C[0], alpha=0.8, lw=0)
    ax.scatter(P[t][col], P[t].nx, s=40, color=C[1], lw=0)
    ax.annotate("東京都", (P[t][col].iloc[0], P[t].nx.iloc[0]), xytext=(8, -4), textcoords="offset points", fontsize=9.5, color=C[1])
    e = P[~t]
    b, a = np.polyfit(e[col], e.nx, 1)
    xs = np.linspace(e[col].min(), e[col].max(), 50)
    ax.plot(xs, a + b * xs, color=INK2, lw=1.2, ls="--")
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xlabel(xlab); ax.set_ylabel("移出入（純）÷県内総生産（%）")
    finish(fig, ax, title, grid="both")
    fig.subplots_adjust(bottom=0.19)
    save(fig, name)


rb = pd.read_csv(R / "robustness.csv").set_index("check").value
scatter("manuf_sh", "製造業の割合（県内総生産に対する%、2019〜2023年度の平均）", "fig2_manufacturing.png",
        f"製造業の割合が大きい県ほど黒字：相関 {m['r_manuf']:.2f}（東京都を除くと {m['r_manuf_ex_tokyo']:.2f}）")
scatter("pubedu_sh", "公務と教育の割合（県内総生産に対する%、2019〜2023年度の平均）", "fig3_public_educ.png",
        f"公務と教育の割合が大きい県ほど赤字：相関 {m['r_public_educ']:.2f}（破線は東京都を除いた当てはめ）")

# 図4：要素所得を足すと（北から南の順）
fig, ax = plt.subplots(figsize=(10, 5.6))
ax.vlines(x, Q.nx, Q.both, color=GRID, lw=2.2)
ax.scatter(x, Q.nx, s=26, color=C[1], label="移出入（純）", zorder=3)
ax.scatter(x, Q.both, s=26, color=C[2], label="移出入（純）＋域外からの要素所得（純）", zorder=3)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x, [short(s) for s in Q.pref], rotation=90, fontsize=8.5)
ax.set_xlim(-0.8, len(Q) - 0.2)
ax.set_ylabel("県内総生産に対する%（2019〜2023年度の平均）")
ax.legend(loc="lower right", frameon=False, fontsize=9)
q = m["requestion"]
finish(fig, ax, f"県外で働く人の所得などを足すと、黒字の県は {q['n_both_positive']} に（移出入だけでは {m['n_positive']}）", grid="y")
fig.subplots_adjust(bottom=0.2)
save(fig, "fig4_with_factor_income.png")
