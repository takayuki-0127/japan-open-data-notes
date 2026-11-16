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
    if any(cand == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#8a63d2"]
INK2, GRID = "#52514e", "#e4e3df"
SRC = "出典：国土交通省「自動車燃料消費量調査」（第1表、各年度）をもとに作成者が加工して作成"
META = {"Software": None}
main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
t = pd.read_csv(R / "private_car_gasoline_by_fy.csv", index_col="fy")
KN = {"regular": "普通車", "small": "小型車", "hybrid": "ハイブリッド", "kei": "軽自動車"}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


# 図1：1台あたり年間走行キロ
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for i, k in enumerate(["hybrid", "regular", "small", "kei"]):
    ax.plot(t.index, t[f"kmcar_{k}"], color=C[i + 1], lw=1.3, alpha=0.9, label=KN[k])
ax.plot(t.index, t.km_per_car, color=C[0], lw=3, label="4車種の合計")
for y in [2019, 2020, 2025]:
    ax.text(y + (0.35 if y == 2019 else 0), t.km_per_car.loc[y] + 180, f"{t.km_per_car.loc[y]:,.0f}", ha="center", fontsize=8.8, color=C[0])
ax.axvspan(2019.5, 2021.5, color="#a9a8a3", alpha=0.15, lw=0)
ax.text(2020.5, 6150, "2020〜21年度", ha="center", fontsize=8.5, color=INK2)
ax.set_ylim(6000, 13000); ax.set_xlim(2009.5, 2025.5)
ax.set_ylabel("1台あたりの年間走行キロ（km）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="upper left", frameon=False, fontsize=8.8, ncol=5)
ax.set_title(f"1台あたりの走行キロは2019年度まで横ばい、2020年度に下がり、2023〜25年度はコロナ前より{-req['all']['post_vs_pre_pct']:.0f}%少ない", loc="left", fontsize=10.8)
foot(fig, "注：ガソリンの自家用乗用車。1台あたり = 1日1車当たり走行キロ × 365（使われていない日も含めた平均）。")
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig1_km_per_car.png")

# 図2：指数（2011〜13年度平均=100）
base = t.loc[2011:2013].mean()
fig, ax = plt.subplots(figsize=(8.8, 4.8))
for col, c, nm in [("km_per_car", C[0], "1台あたり走行キロ"), ("l_per_km", C[2], "1kmあたり燃料（燃費の逆数）"), ("l_per_car", C[1], "1台あたり燃料")]:
    s = t[col] / base[col] * 100
    ax.plot(s.index, s, color=c, lw=2.3, label=nm)
    ax.text(2025.2, s.loc[2025], f"{s.loc[2025]:.1f}", va="center", fontsize=9, color=c)
ax.axhline(100, color=INK2, lw=0.8)
ax.set_ylim(70, 106); ax.set_xlim(2009.5, 2026.2)
ax.set_ylabel("2011〜13年度平均 = 100")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="lower left", frameon=False, fontsize=9)
ax.set_title(f"1台あたり燃料は{main['l_per_car_chg']:.1f}%、走行キロは{main['km_per_car_chg']:.1f}%（2011〜13年度→2023〜25年度）", loc="left", fontsize=11.5)
foot(fig, "注：ガソリンの自家用乗用車（普通車・小型車・ハイブリッド・軽自動車）の合計。")
fig.subplots_adjust(left=0.09, right=0.96, top=0.91, bottom=0.14)
save(fig, "fig2_index_fuel_km.png")

# 図3：燃料の合計の変化の分解
dc = main["decomp"]
labels = ["台数", "1台あたり走行キロ", "1kmあたり燃料", "燃料の合計"]
vals = [dc["cars"], dc["km_per_car"], dc["l_per_km"], dc["total_pct"]]
fig, ax = plt.subplots(figsize=(8.8, 4.6))
cols = [C[3], C[0], C[2], INK2]
ax.bar(range(4), vals, color=cols, width=0.6)
for i, v in enumerate(vals):
    ax.text(i, v + (0.5 if v >= 0 else -0.5), f"{v:+.1f}%", ha="center", va="bottom" if v >= 0 else "top", fontsize=10)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(range(4)); ax.set_xticklabels(labels)
ax.set_ylim(-25, 6); ax.set_ylabel("2011〜13年度平均→2023〜25年度平均（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"燃料が{-dc['total_pct']:.0f}%減ったうち、燃費の改善の分が{-dc['l_per_km']:.0f}%、走らなくなった分が{-dc['km_per_car']:.0f}%", loc="left", fontsize=11.5)
foot(fig, f"注：燃料 = 台数 × 1台あたり走行キロ × 1kmあたり燃料。対数の差で分けて、合計の変化に比例させた。燃料の合計は{main['fuel_A_bn_l'] * 100:,.0f}万kℓ→{main['fuel_B_bn_l'] * 100:,.0f}万kℓ。")
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig3_decomposition.png")

# 図4：走行キロの車種別の割合
fig, ax = plt.subplots(figsize=(8.8, 4.8))
order = ["regular", "small", "kei", "hybrid"]
cols = [C[2], C[3], C[4], C[1]]
ax.stackplot(t.index, [t[f"kmshare_{k}"] for k in order], colors=cols, labels=[KN[k] for k in order], alpha=0.9)
y0 = 0
for k, c in zip(order, cols):
    v = t[f"kmshare_{k}"].loc[2025]
    ax.text(2025.15, y0 + v / 2, f"{KN[k]} {v:.0f}%", va="center", fontsize=8.8, color=INK2)
    y0 += v
ax.set_xlim(2010, 2025); ax.set_ylim(0, 100)
ax.set_ylabel("走行キロの割合（%）")
ax.set_title(f"軽自動車とハイブリッドの割合は{main['kmshare_kei_hv_A']:.0f}%から{main['kmshare_kei_hv_B']:.0f}%へ（3年平均）", loc="left", fontsize=11.5)
foot(fig, "注：ガソリンの自家用乗用車4車種の走行キロの合計に占める割合。")
fig.subplots_adjust(left=0.09, right=0.84, top=0.91, bottom=0.14)
save(fig, "fig4_km_share_by_type.png")
print("ok")
