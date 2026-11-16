"""04 図（オフライン）：results の CSV から図を4枚作る。"""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
from matplotlib import font_manager
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f:
        font_manager.fontManager.addfont(f)
ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, FIG, DATA = ROOT / "results", ROOT / "figures", ROOT / "data"
FIG.mkdir(exist_ok=True)
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
C1, C2, C3, C4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2})
SRC = "出典：総務省「家計調査」（二人以上の世帯）、「消費者物価指数」をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))

def save(fig, name, src=SRC):
    fig.text(0.01, 0.01, src, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)

# 図1 名目と実質
ts = pd.read_csv(RES / "total_by_year.csv")
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(ts.year, ts.nominal_vs_2019 * 100, color=C2, lw=2, marker="o", ms=4, label="支払った金額（名目）")
ax.plot(ts.year, ts.real_vs_2019 * 100, color=C1, lw=2, marker="o", ms=4, label="物価の上がった分を除いた量（実質）")
ax.axhline(100, color=INK2, lw=1, ls="--")
for col, c in [("nominal_vs_2019", C2), ("real_vs_2019", C1)]:
    v = ts[col].iloc[-1] * 100
    ax.text(2025.15, v, f"{v:.0f}", va="center", fontsize=9, color=INK)
ax.set_xticks(ts.year); ax.set_xlim(2014.6, 2025.6); ax.set_ylim(20, 120)
ax.set_ylabel("1世帯あたりの年間支出（2019年＝100）"); ax.grid(axis="y", color=GRID, lw=0.8)
ax.legend(frameon=False, loc="lower left")
ax.set_title(f"レジャー・娯楽サービス10品目：金額は2019年を超えたが、物価を除くと{M['R_real_2025']*100:.0f}", loc="left", fontsize=11)
fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.14)
save(fig, "fig1_nominal_real.png")

# 図2 品目ごと
it = pd.read_csv(RES / "items.csv").sort_values("R_real")
fig, ax = plt.subplots(figsize=(8, 5))
y = np.arange(len(it))
ax.barh(y, it.R_real * 100, color=C1, height=0.6, label="実質（物価を除いた量）")
ax.scatter(it.R_nominal * 100, y, color=C2, s=40, zorder=3, label="名目（支払った金額）", edgecolor="white", linewidth=0.8)
for yi, (v, n19) in enumerate(zip(it.R_real * 100, it.nominal_2019)):
    ax.text(3, yi, f"{v:.0f}", va="center", ha="left", fontsize=8.5, color="white")
ax.set_yticks(y); ax.set_yticklabels([f"{a}（2019年 {b:,}円）" for a, b in zip(it["item"], it.nominal_2019)], fontsize=9)
ax.axvline(100, color=INK2, lw=1, ls="--")
ax.set_xlim(0, 165); ax.set_xlabel("2025年の支出（2019年＝100）。品目の右の円は2019年の1世帯あたり年間支出")
ax.legend(frameon=False, loc="lower right", fontsize=9); ax.grid(axis="x", color=GRID, lw=0.8)
ax.set_title("戻っていないのはパック旅行。映画・演劇や入場料は2019年を超えた", loc="left", fontsize=11)
fig.subplots_adjust(left=0.33, right=0.97, top=0.92, bottom=0.14)
save(fig, "fig2_items.png", SRC + "。国内パック旅行費は宿泊料の物価で割り引いた（代用）")

# 図3 旅行3品目と娯楽7品目（実質）
d = pd.read_csv(DATA / "leisure_items.csv"); cpi = pd.read_csv(DATA / "cpi_leisure.csv").set_index("year")
cpi["映画・演劇"] = (cpi["映画観覧料"] + cpi["演劇観覧料"]) / 2
DEF = {"宿泊料": "宿泊料", "国内パック旅行費": "宿泊料", "外国パック旅行費": "外国パック旅行費", "映画・演劇等入場料": "映画・演劇",
       "スポーツ観覧料": "プロ野球観覧料", "スポーツクラブ使用料": "フィットネスクラブ使用料", "他のスポーツ施設使用料": "入場・観覧・ゲーム代",
       "文化施設入場料": "文化施設入場料", "遊園地入場・乗物代": "テーマパーク入場料", "他の入場・ゲーム代": "入場・観覧・ゲーム代"}
x = d[(d.table == "age") & (d.group == "平均") & d.item.isin(DEF)].copy()
x["real"] = [v / cpi.loc[yy, DEF[i]] * 100 for v, yy, i in zip(x.amount, x.year, x.item)]
grp = {"宿泊料": "旅行（宿泊料・国内パック・外国パック）", "国内パック旅行費": "旅行（宿泊料・国内パック・外国パック）", "外国パック旅行費": "旅行（宿泊料・国内パック・外国パック）"}
x["g"] = x.item.map(grp).fillna("入場・観覧・スポーツなど7品目")
s = x.groupby(["g", "year"]).real.sum().unstack(0)
s = s / s.loc[2019] * 100
fig, ax = plt.subplots(figsize=(8, 4.6))
for col, c in zip(["入場・観覧・スポーツなど7品目", "旅行（宿泊料・国内パック・外国パック）"], [C3, C1]):
    ax.plot(s.index, s[col], color=c, lw=2, marker="o", ms=4, label=col)
    ax.text(2025.15, s[col].iloc[-1], f"{s[col].iloc[-1]:.0f}", va="center", fontsize=9)
ax.axhline(100, color=INK2, lw=1, ls="--")
ax.axvspan(2020.5, 2023.5, color=GRID, alpha=0.5, lw=0)
ax.text(2022, 125, "外国パック旅行費の物価指数は\n2021〜23年に調査が止まっていた", ha="center", fontsize=8, color=INK2)
ax.set_xticks(s.index); ax.set_xlim(2014.6, 2025.6); ax.set_ylim(0, 140)
ax.set_ylabel("物価を除いた支出（2019年＝100）"); ax.grid(axis="y", color=GRID, lw=0.8)
ax.legend(frameon=False, loc="lower left")
ax.set_title(f"娯楽は{M['R_real_entertainment7']*100:.0f}まで戻り、旅行は{M['R_real_travel3']*100:.0f}にとどまる（物価を除いた量）", loc="left", fontsize=11)
fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.14)
save(fig, "fig3_travel_vs_entertainment.png")

# 図4 年齢・収入（ふだんの1年の揺れと並べる）
g = pd.read_csv(RES / "groups.csv")
fig, axs = plt.subplots(1, 2, figsize=(8.6, 4.6), sharey=True, gridspec_kw={"width_ratios": [6, 5]})
for ax, table, lab in [(axs[0], "age", "世帯主の年齢"), (axs[1], "income", "年間収入の五分位（Ⅰが低い2割）")]:
    t = g[g.table == table]
    xx = np.arange(len(t))
    ax.bar(xx, t.R_real * 100, color=C1, width=0.6)
    ax.scatter(xx, t.R_real_2019_2018 * 100, color=C4, marker="D", s=36, zorder=3, edgecolor="white", linewidth=0.8)
    for xi, v in zip(xx, t.R_real * 100):
        ax.text(xi + 0.32, v + 2, f"{v:.0f}", ha="left", fontsize=8.5)
    ax.axhline(100, color=INK2, lw=1, ls="--")
    ax.set_xticks(xx); ax.set_xticklabels([s.replace("～", "〜") for s in t.group], fontsize=8.5)
    ax.set_xlabel(lab); ax.grid(axis="y", color=GRID, lw=0.8); ax.set_ylim(0, 140)
axs[0].set_ylabel("物価を除いた支出（比べる前の年＝100）")
axs[1].legend(handles=[Patch(color=C1, label="2025年÷2019年"), Line2D([], [], color=C4, marker="D", ls="", label="コロナ前の1年（2019年÷2018年）")],
              frameon=False, fontsize=8.5, loc="upper right")
fig.suptitle("年齢では70歳以上の戻りが鈍い。収入による違いは、コロナ前の1年の揺れより小さい", x=0.01, ha="left", fontsize=11)
fig.subplots_adjust(left=0.09, right=0.98, top=0.9, bottom=0.16, wspace=0.08)
save(fig, "fig4_age_income.png")
print("figures done")
