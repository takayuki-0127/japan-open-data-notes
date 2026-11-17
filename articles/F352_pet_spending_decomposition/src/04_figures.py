"""04 図（オフライン）：results の CSV から図を4枚作る。"""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
from matplotlib import font_manager

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f:
        font_manager.fontManager.addfont(f)
ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2})
SRC = "出典：総務省「家計調査」（二人以上の世帯）、「消費者物価指数」をもとに作成者が加工して作成。動物病院代は含まない"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))
Q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))

def save(fig, name, src=SRC):
    fig.text(0.01, 0.01, src, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)

t = pd.read_csv(RES / "total_by_year.csv")
# 図1 名目と実質（円）
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(t.year, t.nominal_total, color=C2, lw=2, marker="o", ms=4, label="支払った金額（名目）")
ax.plot(t.year, t.real_total_long, color=C1, lw=2, marker="o", ms=4, label="2025年の値段で数えた量（実質）")
ax.axvline(2019, color=INK2, lw=1, ls="--")
for col in ["nominal_total", "real_total_long"]:
    ax.text(2025.2, t[col].iloc[-1], f"{t[col].iloc[-1]:,.0f}円", va="center", fontsize=8.5)
ax.text(2019.1, 6500, "2019年", fontsize=8.5, color=INK2)
ax.set_xlim(2004.5, 2027); ax.set_ylim(6000, 24000); ax.set_xticks(range(2005, 2026, 2))
ax.set_ylabel("1世帯あたり年間（円）"); ax.grid(axis="y", color=GRID, lw=0.8); ax.legend(frameon=False, loc="upper left")
ax.set_title("ペットフード・用品・サービスへの支出：2019年までは量が増え、その後は値上がりの分", loc="left", fontsize=11)
fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.21)
save(fig, "fig1_nominal_real.png", SRC + "。\n2014年までの用品・サービスは他の教養娯楽用品の物価で割り引いた")

# 図2 名目の伸びを物価と量に分ける
fig, ax = plt.subplots(figsize=(8, 4.4))
per = ["2005→2019年（14年）", "2019→2025年（6年）"]
nomg = [M["nominal_growth_2005_2019"], M["nominal_growth_2019_2025"]]
realg = [M["real_growth_2005_2019_long"], M["real_growth_2019_2025_long"]]
lp = [np.log(1 + n) - np.log(1 + q) for n, q in zip(nomg, realg)]
lq = [np.log(1 + q) for q in realg]
y = np.arange(2)
ax.barh(y, lq, color=C1, height=0.5, label="量の伸び（実質）")
ax.barh(y, lp, left=[max(v, 0) for v in lq], color=C2, height=0.5, label="値上がりの分")
for yi, (n, a, b) in enumerate(zip(nomg, lq, lp)):
    ax.text(max(a, 0) + b + 0.01, yi, f"名目 +{n*100:.0f}%（うち量 " + ("±0" if abs(realg[yi]) < 0.005 else f"{realg[yi]*100:+.0f}") + "%）", va="center", fontsize=9)
ax.axvline(0, color=INK2, lw=1)
ax.set_yticks(y); ax.set_yticklabels(per); ax.invert_yaxis(); ax.set_xlim(-0.05, 0.75)
ax.set_xlabel("伸び（対数の差。0.1 はおよそ10%）"); ax.grid(axis="x", color=GRID, lw=0.8); ax.legend(frameon=False, loc="lower right", fontsize=9)
ax.set_title("2019年からの伸びは、ほとんどが値上がりの分", loc="left", fontsize=11)
fig.subplots_adjust(left=0.2, right=0.97, top=0.9, bottom=0.22)
save(fig, "fig2_price_vs_volume.png", SRC + "。\nフード以外は他の教養娯楽用品の物価で割り引いた")

# 図3 ペットフード：買う回数と1回あたりの実質の額
f = pd.read_csv(RES / "food_freq.csv")
b = f[f.year == 2019].iloc[0]
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(f.year, f.food_freq_per100 / b.food_freq_per100 * 100, color=C3, lw=2, marker="o", ms=4, label="買う回数（100世帯あたりの購入回数）")
ax.plot(f.year, f.food_per_purchase_real / b.food_per_purchase_real * 100, color=C1, lw=2, marker="o", ms=4, label="1回あたりの額（物価を除く）")
ax.plot(f.year, t.cpi_food / t[t.year == 2019].cpi_food.iloc[0] * 100, color=C2, lw=1.6, ls="--", label="ペットフードの物価")
ax.axhline(100, color=INK2, lw=0.8)
for col, s in [("回数", f.food_freq_per100 / b.food_freq_per100 * 100), ("1回", f.food_per_purchase_real / b.food_per_purchase_real * 100)]:
    ax.text(2025.2, s.iloc[-1], f"{s.iloc[-1]:.0f}", va="center", fontsize=9)
ax.text(2025.2, t.cpi_food.iloc[-1] / t[t.year == 2019].cpi_food.iloc[0] * 100, f"{t.cpi_food.iloc[-1] / t[t.year == 2019].cpi_food.iloc[0] * 100:.0f}", va="center", fontsize=9)
ax.set_xlim(2004.5, 2026.3); ax.set_xticks(range(2005, 2026, 2)); ax.set_ylim(50, 170)
ax.set_ylabel("2019年＝100"); ax.grid(axis="y", color=GRID, lw=0.8); ax.legend(frameon=False, loc="upper left", fontsize=9)
ax.set_title("ペットフード：買う回数は増え続け、1回あたりの額（物価を除く）は2019年から約2割減った", loc="left", fontsize=11)
fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.14)
save(fig, "fig3_food_frequency.png")

# 図4 品目ごと（2019→2025）
it = pd.read_csv(RES / "items.csv")
fig, ax = plt.subplots(figsize=(8, 4.2))
y = np.arange(len(it)); h = 0.36
ax.barh(y - h / 2, it.nominal_growth * 100, height=h, color=C2, label="名目（支払った金額）")
ax.barh(y + h / 2, it.real_growth * 100, height=h, color=C1, label="実質（物価を除いた量）")
for yi, (n, q) in enumerate(zip(it.nominal_growth * 100, it.real_growth * 100)):
    ax.text(n + 1, yi - h / 2, f"{n:+.0f}%", va="center", fontsize=8.5)
    ax.text(max(q, 0) + 1, yi + h / 2, f"{q:+.0f}%", va="center", fontsize=8.5)
ax.axvline(0, color=INK2, lw=1)
ax.set_yticks(y); ax.set_yticklabels([f"{a}\n（2019年 {b:,}円）" for a, b in zip(it["item"], it.nominal_2019)]); ax.invert_yaxis()
ax.set_xlim(-15, 60); ax.set_xlabel("2019年から2025年の伸び（%）"); ax.grid(axis="x", color=GRID, lw=0.8)
ax.legend(frameon=False, loc="lower right", fontsize=9)
ax.set_title("量が増えたのはペット関連サービス。フードの量は減った", loc="left", fontsize=11)
fig.subplots_adjust(left=0.22, right=0.97, top=0.9, bottom=0.21)
save(fig, "fig4_items.png", SRC + "。\nフードは犬・猫用の物価、用品はペットトイレ用品、サービスはペット美容院代の物価で割り引いた")
print("figures done")
