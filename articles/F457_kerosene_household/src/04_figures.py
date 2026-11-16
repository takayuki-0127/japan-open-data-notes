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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK2, GRID = "#52514e", "#e4e3df"
SRC = "出典：総務省「家計調査」（二人以上の世帯）をもとに作成者が加工して作成"
META = {"Software": None}
main = json.load(open(R / "main.json", encoding="utf-8"))
L = pd.read_csv(R / "kerosene_long_linked.csv", index_col="year")
N = pd.read_csv(R / "kerosene_national_2007_2025.csv", index_col="year")
ct = pd.read_csv(R / "cities_2018_2025.csv", index_col="region")


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


# 図1：長期
s = L.qty_linked.dropna()
fig, ax = plt.subplots(figsize=(8.8, 4.8))
ax.plot(s.index, s, color=C[0], lw=2.4)
ax.annotate(f"{main['peak_year']}年 {main['peak_qty']:.0f}ℓ", (main["peak_year"], main["peak_qty"]), xytext=(1980, 360), fontsize=9, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.text(2025.3, s.loc[2025], f"{s.loc[2025]:.0f}ℓ", va="center", fontsize=9, color=C[0])
ax.axvline(2007, color=INK2, lw=0.7, ls=":"); ax.text(2007.3, 60, "2007年までは長期時系列表\n（農林漁家世帯を除く）を\n2007年の比でつないだ", fontsize=8, color=INK2)
ax.set_ylim(0, 400); ax.set_xlim(1972, 2029)
ax.set_ylabel("1世帯あたり年間の購入数量（ℓ）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"灯油を買う量は{main['peak_year']}年がいちばん多く、2025年はその{100 + main['qty_pct_peak_2025']:.0f}%", loc="left", fontsize=11.5)
foot(fig, "注：二人以上の世帯。購入数量は1974年から。")
fig.subplots_adjust(left=0.09, right=0.95, top=0.91, bottom=0.12)
save(fig, "fig1_long_quantity.png")

# 図2：量・支出・値段（2008=100）
fig, ax = plt.subplots(figsize=(8.8, 4.8))
for col, c, nm in [("qty", C[0], "購入数量"), ("spend", C[1], "支出金額"), ("price", C[3], "平均価格（支出÷数量）")]:
    y = N.loc[2008:, col] / N.loc[2008, col] * 100
    ax.plot(y.index, y, color=c, lw=2.3, marker="o", ms=3, label=nm)
    ax.text(2025.3, y.loc[2025], f"{y.loc[2025]:.0f}", va="center", fontsize=9, color=c)
ax.axhline(100, color=INK2, lw=0.7)
ax.set_xlim(2007.5, 2026.5); ax.set_xticks(range(2008, 2026, 2)); ax.set_ylabel("2008年 = 100")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="lower left", frameon=False, fontsize=9)
ax.set_title(f"2008→2025年に量は{main['qty_pct_2008_2025']:.0f}%、支出は{main['spend_pct_2008_2025']:.0f}%（値段が{main['price_2008']:.0f}→{main['price_2025']:.0f}円/ℓ）", loc="left", fontsize=11.5)
foot(fig)
fig.subplots_adjust(left=0.08, right=0.95, top=0.91, bottom=0.12)
save(fig, "fig2_qty_spend_price.png")

# 図3：買う世帯の割合と、買う世帯あたりの量
fig, axs = plt.subplots(1, 2, figsize=(8.8, 4.6))
axs[0].plot(N.index, N.share_buyers, color=C[2], lw=2.3, marker="o", ms=3)
axs[0].set_title("購入世帯数（1万世帯あたりを%に。月の平均とみられる）", fontsize=9.5); axs[0].set_ylim(0, 25); axs[0].set_ylabel("%")
axs[1].plot(N.index, N.qty_per_buyer, color=C[0], lw=2.3, marker="o", ms=3)
axs[1].set_title("購入数量 ÷ 購入世帯の割合（ℓ、目安）", fontsize=9.5); axs[1].set_ylim(0, 1300)
for a in axs: a.grid(axis="y", color=GRID, lw=0.8); a.set_axisbelow(True)
axs[0].text(2008, N.share_buyers.loc[2008] + 0.8, f"{N.share_buyers.loc[2008]:.1f}", fontsize=9); axs[0].text(2024, N.share_buyers.loc[2025] + 0.8, f"{N.share_buyers.loc[2025]:.1f}", fontsize=9)
axs[1].text(2008, N.qty_per_buyer.loc[2008] + 40, f"{N.qty_per_buyer.loc[2008]:.0f}", fontsize=9); axs[1].text(2023.5, N.qty_per_buyer.loc[2025] + 40, f"{N.qty_per_buyer.loc[2025]:.0f}", fontsize=9)
fig.suptitle(f"減った量の{main['decomp_share_buyers_pct']:.0f}%は「買う世帯の割合（月平均）が下がった」分（2008→2025年）", x=0.01, ha="left", fontsize=11.5)
foot(fig, "注：購入数量 = 購入世帯数 ÷ 1万 × 購入世帯あたりの量。対数の差で分けた。購入世帯数は数値の大きさから月の平均とみられる（推測）。")
fig.subplots_adjust(left=0.08, right=0.97, top=0.84, bottom=0.14, wspace=0.25)
save(fig, "fig3_buyers_decomposition.png")

# 図4：都市別 2018年と2025年
fig, ax = plt.subplots(figsize=(8.8, 5.0))
north = main["north_cities"]
col = [C[1] if c in north else C[0] for c in ct.index]
ax.scatter(ct.qty_2018, ct.qty_2025, s=30, color=col, edgecolor="white", lw=0.5)
lim = [5, 1500]; ax.plot(lim, lim, color=INK2, lw=0.8, ls="--")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(*lim); ax.set_ylim(*lim)
for c in north:
    ax.text(ct.loc[c, "qty_2018"] * 1.05, ct.loc[c, "qty_2025"] * 0.9, c, fontsize=7.8, color=INK2)
ax.set_xlabel("2018年の購入数量（ℓ、対数目盛）"); ax.set_ylabel("2025年の購入数量（ℓ、対数目盛）")
ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"52市のうち{main['n_down_2018_2025']}市で減った（点線より下が減少）", loc="left", fontsize=11.5)
foot(fig, "注：1つの点が1つの都道府県庁所在市・政令市。オレンジは北海道・東北の7市。")
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig4_cities.png")
print("ok")
