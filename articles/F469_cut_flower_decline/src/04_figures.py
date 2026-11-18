"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C1, C2, C3, C4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK2, GRID, GRAY = "#52514e", "#e4e3df", "#b5b4ae"
META = {"Software": None}
S_K = "出典：農林水産省「作物統計（花き生産出荷統計）」をもとに作成者が加工して作成"
S_H = "出典：総務省「家計調査」「消費者物価指数」をもとに作成者が加工して作成"
S_I = "出典：財務省「貿易統計」、農林水産省「作物統計（花き生産出荷統計）」をもとに作成者が加工して作成"
M = json.load(open(R / "main.json", encoding="utf-8"))
T = pd.read_csv(R / "group_totals.csv")
I = pd.read_csv(R / "items_2005_2025.csv")
H = pd.read_csv(R / "household_spend.csv").set_index("year")
LT = pd.read_csv(R / "household_longterm.csv").set_index("year")
AG = pd.read_csv(R / "requestion_age.csv")
CMP = pd.read_csv(R / "import_vs_domestic.csv")


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


def foot(fig, src, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + src, fontsize=7.6, color=INK2)


def style(ax, yint=False):
    ax.xaxis.set_major_locator(mt.MaxNLocator(integer=True))
    ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)


# 図1：切り花類の出荷量と、類ごとの指数
g = M["groups"]["切り花類"]
fig, axes = plt.subplots(1, 2, figsize=(10, 4.7))
ax = axes[0]
s = T[(T.group == "切り花類") & (T.measure == "ship")].set_index("year").value.loc[1990:] / 1e5
ax.plot(s.index, s.values, color=C1, lw=2)
ax.scatter([g["peak_year"]], [g["peak"] / 1e5], color=C1, s=36, zorder=3, edgecolor="#fcfcfb", linewidth=1.5)
ax.text(g["peak_year"], g["peak"] / 1e5 + 2.2, f'{g["peak_year"]}年 {g["peak"]/1e5:.1f}億本', ha="center", fontsize=9, color=INK2)
ax.text(2025.5, s[2025], f"{s[2025]:.1f}", fontsize=9, color=INK2, va="center")
ax.set_ylim(0, 65); ax.set_xlim(1988, 2029); ax.set_ylabel("出荷量（億本）")
ax.set_title("切り花類の出荷量", fontsize=11, loc="left"); style(ax)
ax = axes[1]
for name, c in [("切り花類", C1), ("鉢もの類", C2), ("花壇用苗もの類", C3), ("球根類", C4)]:
    q = T[(T.group == name) & (T.measure == "ship")].set_index("year").value.loc[1990:]
    idx = q / q[2005] * 100
    ax.plot(idx.index, idx.values, color=c, lw=2, label=name)
    ax.text(2025.5, idx[2025] + {"切り花類": 0, "鉢もの類": -9, "花壇用苗もの類": 9, "球根類": 0}[name], f"{idx[2025]:.0f}", fontsize=9, color=INK2, va="center")
ax.axhline(100, color=INK2, lw=0.7, ls=":")
ax.set_ylim(0, 300); ax.set_xlim(1989, 2029); ax.set_ylabel("出荷量の指数（2005年＝100）")
ax.set_title("どの類も2005年から半分前後に", fontsize=11, loc="left"); ax.legend(frameon=False, fontsize=8.8); style(ax)
fig.suptitle(f'切り花の出荷量は{g["peak_year"]}年の山から{-g["pct_from_peak"]:.1f}%減った', x=0.01, ha="left", fontsize=12)
fig.subplots_adjust(bottom=0.16, top=0.83, left=0.07, right=0.96, wspace=0.27)
foot(fig, S_K, "2025年は令和7年産の全国の表。切り花類の計は1989→1990年に主な品目の伸びでは説明できない段差があるため、1990年からを示した。")
save(fig, "fig1_shipments.png")

# 図2：品目別の2005→2025年の変化
fig, ax = plt.subplots(figsize=(8.8, 5.4))
q = I.sort_values("pct_ship", ascending=True).reset_index(drop=True)
y = np.arange(len(q))
cols = [C2 if it == "きく" else C1 for it in q.item]
ax.barh(y, q.pct_ship, color=cols, height=0.62)
for yi, v, sh in zip(y, q.pct_ship, q.share_2025):
    ax.text(v - 1, yi, f"{v:.1f}%", ha="right", va="center", fontsize=8.6, color=INK2)
ax.set_yticks(y); ax.set_yticklabels([f"{it}（2025年 {sh:.1f}%）" for it, sh in zip(q.item, q.share_2025)], fontsize=9)
tot = M["kirihana_pct_2005_2025"]
ax.axvline(tot, color=INK2, lw=1, ls="--"); ax.text(tot + 0.8, len(q) - 0.4, f"切り花類の計 {tot:.1f}%", fontsize=8.8, color=INK2)
ax.set_xlim(-75, 0); ax.set_xlabel("出荷量の変化（2005→2025年、%）")
ax.invert_yaxis()
ax.grid(axis="x", color=GRID); ax.set_axisbelow(True)
ax.set_title("どの品目も減った。大きく減ったのはカーネーションとばら", fontsize=11.5, loc="left")
fig.subplots_adjust(bottom=0.17, top=0.92, left=0.27, right=0.97)
foot(fig, S_K, "かっこ内は2025年の切り花類の出荷量に占める割合。きくは輪ぎく（大・中輪）・小ぎく・スプレイぎくの合計で、内訳も並べた。")
save(fig, "fig2_items.png")

# 図3：家計の切り花の支出（長期）と年齢別
h = M["household"]
fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), gridspec_kw={"width_ratios": [1.25, 1]})
ax = axes[0]
ax.plot(LT.index, LT.spend_nonfarm, color=GRAY, lw=1.6, label="名目（長期時系列、農林漁家を除く）")
ax.plot(H.index, H.spend, color=C1, lw=2, label="名目（第4-6表）")
ax.plot(H.index, H.real_spend_2025yen, color=C2, lw=2, label="実質（2025年の物価で）")
rl = LT.real_2025yen.dropna(); ax.plot(rl.index, rl.values, color=C2, lw=1.4, ls="--")
ax.text(2025.6, H.spend[2025], f"{H.spend[2025]:,.0f}円", fontsize=9, color=INK2, va="center")
ax.set_ylim(0, 19000); ax.set_xlim(1962, 2033); ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, p: f"{v:,.0f}"))
ax.set_ylabel("1世帯あたり年間（円）"); ax.set_title("切り花の支出（二人以上の世帯）", fontsize=11, loc="left")
ax.legend(frameon=False, fontsize=8.3, loc="lower right"); style(ax)
ax = axes[1]
x = np.arange(len(AG)); w = 0.38
ax.bar(x - w / 2 - 0.01, AG.spend_2002, width=w, color=GRAY, label="2002年")
ax.bar(x + w / 2 + 0.01, AG.spend_2025, width=w, color=C1, label="2025年")
for xi, v, p in zip(x, AG.spend_2025, AG.pct_spend):
    ax.text(xi + w / 2, v + 250, f"{p:.0f}%", ha="center", fontsize=8.4, color=INK2)
ax.set_xticks(x); ax.set_xticklabels([a.replace("～", "〜\n") for a in AG.age], fontsize=8.6)
ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, p: f"{v:,.0f}"))
ax.set_ylabel("1世帯あたり年間（円）"); ax.set_title("世帯主の年齢別：どの年齢でも減った", fontsize=11, loc="left")
ax.legend(frameon=False, fontsize=8.6, loc="upper left"); ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
fig.suptitle(f'支出は2002→2025年に名目{-h["pct_nominal"]:.0f}%、実質{-h["pct_real"]:.0f}%減。買う回数も、1回に買う実質の額も減った', x=0.01, ha="left", fontsize=12)
fig.subplots_adjust(bottom=0.2, top=0.83, left=0.08, right=0.97, wspace=0.27)
foot(fig, S_H, "実質は切り花の消費者物価指数（2025年＝100）で割った値。点線は長期時系列を同じ指数で割った値（1970年から）。右の％は2002→2025年の変化。")
save(fig, "fig3_household.png")

# 図4：輸入（重さ）と国内の出荷量（本数）の指数
fig, axes = plt.subplots(1, 3, figsize=(10.4, 4.3), sharey=True)
for ax, n in zip(axes, ["きく", "カーネーション", "ばら"]):
    q = CMP[CMP.item == n].set_index("year")
    ax.plot(q.index, q.import_idx, color=C2, lw=2, label="輸入（重さ）")
    ax.plot(q.index, q.domestic_idx, color=C1, lw=2, label="国内の出荷量（本数）")
    for col in ["import_idx", "domestic_idx"]:
        ax.text(2025.4, q[col][2025], f"{q[col][2025]:.0f}", fontsize=8.8, color=INK2, va="center")
    ax.axhline(100, color=INK2, lw=0.7, ls=":")
    ax.set_title(n, fontsize=11, loc="left"); ax.set_xlim(2008, 2028.5); style(ax)
axes[0].set_ylabel("指数（2009年＝100）"); axes[0].set_ylim(0, 200)
axes[0].legend(frameon=False, fontsize=8.6, loc="upper left")
fig.suptitle("きく・カーネーションは輸入が増え、国内が減った。ばらは両方減った", x=0.01, ha="left", fontsize=12)
fig.subplots_adjust(bottom=0.2, top=0.83, left=0.07, right=0.97, wspace=0.18)
foot(fig, S_I, "輸入は HS 0603.11（ばら）・0603.12（カーネーション）・0603.14（きく）の重さ。単位が違うので、割合ではなく動き（指数）だけをくらべる。")
save(fig, "fig4_import_vs_domestic.png")
