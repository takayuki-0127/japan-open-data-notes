"""04_figures.py : results の CSV・JSON から図を4枚作る（オフライン）。"""
import json
import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

for f in sorted(font_manager.findSystemFonts()):
    if "NotoSansCJK" in f:
        font_manager.fontManager.addfont(f)
ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
C1, C2, C3, C4 = "#2a78d6", "#eb6834", "#1baf7a", "#9a9893"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
                     "svg.hashsalt": "20261116"})
SRC = "出典：総務省「家計調査」長期時系列表（二人以上の世帯のうち勤労者世帯、月）をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))
Q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))


def save(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


# 図1 月ごとの可処分所得と消費支出（2016〜2025年の平均）
p = pd.read_csv(RES / "monthly_profile.csv")
p = p[p.period == "2016-2025"]
fig, ax = plt.subplots(figsize=(8, 4.6))
x = p.month.values
ax.bar(x - 0.2, p["可処分所得"] / 1e4, width=0.4, color=C1, label="可処分所得（手取り）")
ax.bar(x + 0.2, p["消費支出"] / 1e4, width=0.4, color=C2, label="消費支出")
for m in (6, 7, 12):
    r = p[p.month == m].iloc[0]
    ax.text(m - 0.2, r["可処分所得"] / 1e4 + 1, f"{r['可処分所得'] / 1e4:.0f}", ha="center", fontsize=8, color=C1)
    ax.text(m + 0.2, r["消費支出"] / 1e4 + 1, f"{r['消費支出'] / 1e4:.0f}", ha="center", fontsize=8, color=C2)
ax.set_xticks(range(1, 13)); ax.set_xticklabels([f"{m}月" for m in range(1, 13)])
ax.set_ylabel("1世帯あたり1か月（万円）"); ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper left")
ax.set_title("手取りは6・7・12月に大きく増えるが、消費支出はほとんど動かない（2016〜2025年の平均）", loc="left", fontsize=10.5)
fig.subplots_adjust(left=0.09, right=0.98, top=0.9, bottom=0.15)
save(fig, "fig1_monthly_profile.png")

# 図2 ボーナスの月の手取りの上乗せの行き先（2000〜2025年の合計に対する割合）
d = M["decomp_share_of_excess_Yd"]
parts = [("消費支出", d["消費支出"], C2), ("預貯金の純増", d["預貯金純増"], C1),
         ("住宅ローンの返済（土地家屋借金純減）", d["土地家屋借金純減"], C3),
         ("保険・有価証券", d["保険純増"] + d["有価証券純購入"], "#7d5bc4"),
         ("手元の現金（繰越純増）", d["繰越純増"], C4),
         ("そのほか（他の借金・クレジット・財産）", d["他の借金純減"] + d["クレジット購入借入金純減"] + d["財産純増"] + d["その他の純増"], "#c9c7c1")]
fig, ax = plt.subplots(figsize=(8, 4.2))
labels = [a for a, _, _ in parts][::-1]; vals = [v * 100 for _, v, _ in parts][::-1]; cols = [c for _, _, c in parts][::-1]
ax.barh(labels, vals, color=cols)
for i, v in enumerate(vals):
    ax.text(max(v, 0) + 1, i, f"{v:.1f}%", va="center", fontsize=9)
ax.set_xlim(0, 100); ax.set_xlabel("ボーナスの月（6・7・12月）に増えた手取りに対する割合（%）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
fig.suptitle(f"ボーナスの月に増えた手取り（1年あたり平均 {M['mean_excess_yen_per_year']['可処分所得'] / 1e4:.0f}万円）のうち、"
             f"同じ月の消費に出たのは{d['消費支出'] * 100:.1f}%", x=0.01, ha="left", fontsize=10.5)
fig.subplots_adjust(left=0.42, right=0.96, top=0.88, bottom=0.2)
save(fig, "fig2_where_it_goes.png")

# 図3 年ごとの見かけの使う割合
e = pd.read_csv(RES / "excess_by_year.csv")
fig, ax = plt.subplots(figsize=(8, 4.4))
ax.plot(e.year, e.A_y * 100, color=C2, lw=2, marker="o", ms=4)
ax.axhline(0, color=INK2, lw=0.8)
ax.axvline(2017.5, color=INK2, lw=0.8, ls="--")
ax.text(2017.6, 9.3, "2018年1月\n家計簿の様式の変更", fontsize=8, color=INK2, va="top")
ax.text(2000, e.A_y.iloc[0] * 100 + 0.6, f"{e.A_y.iloc[0] * 100:.1f}%", fontsize=8.5)
ax.text(2025, e.A_y.iloc[-1] * 100 - 1.0, f"{e.A_y.iloc[-1] * 100:.1f}%", fontsize=8.5, ha="center")
ax.set_xticks(range(2000, 2026, 5)); ax.set_ylim(-2, 11)
ax.set_ylabel("消費の上乗せ ÷ 手取りの上乗せ（%）"); ax.grid(axis="y", color=GRID, lw=0.8)
ax.set_title(f"ボーナスの月に増えた手取りのうち、同じ月に使った割合：2000〜09年の平均{M['A_y_mean_2000_2009'] * 100:.1f}%"
             f" → 2016〜25年{M['A_y_mean_2016_2025'] * 100:.1f}%", loc="left", fontsize=10)
fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.15)
save(fig, "fig3_share_by_year.png")

# 図4 夏と冬の消費の上乗せ（10大費目。保健医療は図から除く）
it = pd.read_csv(RES / "items_excess.csv")
c = it[(it.level == "10大費目") & (it.item != "保健医療")].copy()
c = c.sort_values("winter_yen")
fig, ax = plt.subplots(figsize=(8, 4.8))
y = np.arange(len(c))
ax.barh(y + 0.2, c.winter_yen / 1e3, height=0.4, color=C1, label=f"冬（12月）：計 {M['winter_excess_C_yen'] / 1e4:+.1f}万円")
ax.barh(y - 0.2, c.summer_yen / 1e3, height=0.4, color=C2, label=f"夏（6・7月）：計 {M['summer_excess_C_yen'] / 1e4:+.1f}万円")
ax.set_yticks(y); ax.set_yticklabels(c.item); ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlabel("ふだんの月（9か月の平均）より多く使った額（千円、2000〜2025年の1年あたり平均）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True); ax.legend(frameon=False, loc="lower right")
ax.set_title("冬は食料と交際費などで多く、夏はむしろふだんより少ない", loc="left", fontsize=10.5)
fig.subplots_adjust(left=0.2, right=0.97, top=0.9, bottom=0.17)
fig.text(0.2, 0.045, "保健医療は図から除いた。「その他の消費支出」は交際費・こづかい・諸雑費など", fontsize=7.5, color=INK2)
save(fig, "fig4_items_summer_winter.png")
print("ok")
