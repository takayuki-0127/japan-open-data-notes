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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：総務省「家計調査（家計収支編）」長期時系列表（e-Stat）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
s = pd.read_csv(R / "season_by_year.csv")
lg = pd.read_csv(R / "long_annual.csv")
e = pd.read_csv(R / "requestion_month_excess.csv")
rb = pd.read_csv(R / "robustness.csv")
s = s[s.year <= 2025]

# ---- 図1：贈答品の年額の長い流れ ----------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(lg.year, lg.gift_goods_year / 1e4, color=C[0], lw=2)
ax.plot(s.year, s.annual / 1e4, color=C[1], lw=2)
pk = lg.loc[lg.gift_goods_year.idxmax()]
ax.plot([pk.year], [pk.gift_goods_year / 1e4], "o", ms=8, color=C[0], mec="#fcfcfb", mew=2)
ax.text(pk.year, pk.gift_goods_year / 1e4 + 0.6, f"{int(pk.year)}年 {pk.gift_goods_year/1e4:.1f}万円", ha="center", fontsize=9.5, color=INK)
v25 = float(s.loc[s.year == 2025, "annual"].iloc[0])
ax.text(2023.5, v25 / 1e4 - 2.6, f"2025年\n{v25/1e4:.1f}万円", ha="center", fontsize=9.5, color=INK)
ax.text(1977, 2.6, "二人以上の世帯（農林漁家を除く）\n1963〜2007年", fontsize=9, color=INK2)
ax.text(2008.5, 12.6, "二人以上の世帯\n2000年〜", fontsize=9, color=INK2)
ax.set_xlim(1962, 2027); ax.set_ylim(0, 17)
ax.set_ylabel("人に贈る物の支出（1世帯あたり年額、万円）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"人に贈る物への支出は{int(pk.year)}年が山で、2025年はその{main['annual_2025_vs_peak']*100:.0f}%（名目）", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：用途分類の交際費のうち物（食料・家具家事用品・被服及び履物・教養娯楽・他の物品サービス）の合計。贈与金（現金）は含まない。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig1_gift_goods_long.png")

# ---- 図2：夏・冬の上乗せと、ふだんの月（1世帯あたり、円） --------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for col, lab, c in [("winter_excess", "冬の上乗せ（11〜12月）", C[1]), ("summer_excess", "夏の上乗せ（6〜8月）", C[0]), ("base_month", "ふだんの月の1か月分", C[2])]:
    v0, v1 = float(s[col].iloc[0]), float(s[col].iloc[-1])
    ax.plot(s.year, s[col], color=c, lw=2, label=f"{lab}：2000年 {v0:,.0f}円 → 2025年 {v1:,.0f}円（{v1/v0*100:.0f}%）")
ax.legend(loc="lower left", frameon=False, fontsize=9)
ax.set_xlim(2000, 2025.5); ax.set_ylim(0, 15000)
ax.set_xticks(range(2000, 2026, 5))
ax.set_ylabel("1世帯あたり（円）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"夏と冬の贈答品の上乗せは、2000年から2025年で{main['ratios_2025_vs_2000']['season_excess']*100:.0f}%に", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：二人以上の世帯。上乗せ＝その月々の贈答品の支出 −（2〜5・9・10月の平均 × 月数）。名目。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig2_season_excess.png")

# ---- 図3：月ごとの上乗せ（7月・8月・11月・12月） -----------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.9), sharey=True)
ee = e[e.year <= 2025]
for ax, pairs, ttl in [(axes[0], [("m7", "7月", C[0]), ("m8", "8月", C[2])], "夏"), (axes[1], [("m12", "12月", C[1]), ("m11", "11月", C[3])], "冬")]:
    for col, lab, c in pairs:
        ax.plot(ee.year, ee[col], color=c, lw=2)
        v0, v1 = float(ee[col].iloc[0]), float(ee[col].iloc[-1])
        ax.text(2025.5, v1, f"{lab}\n{v0:,.0f}→{v1:,.0f}", fontsize=8.6, color=INK, va="center")
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xlim(2000, 2031.5); ax.set_xticks(range(2000, 2026, 5))
    ax.set_title(ttl, loc="left", fontsize=11)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
axes[0].set_ylabel("ふだんの月より多い分（1世帯あたり、円）")
axes[0].text(2001, 9300, "8月はお盆の時期", fontsize=8.6, color=INK2)
fig.suptitle(f"7月の上乗せは{req['m7_2025']/req['m7_2000']*100:.0f}%に、12月は{req['m12_2025']/req['m12_2000']*100:.0f}%に。8月と11月は残る", x=0.01, ha="left", fontsize=12)
fig.text(0.01, 0.01, "注：二人以上の世帯、名目。ふだんの月＝2〜5・9・10月の平均。6月はほぼ0なので省いた。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.98, top=0.86, bottom=0.16, wspace=0.12)
save(fig, "fig3_month_excess.png")

# ---- 図4：頑健性（2025年÷2000年） ----------------------------------------------------------
lab_map = {0: "本線", 1: "ふだん＝中央値", 2: "ふだんに1月を入れる", 3: "ふだん＝9・10月だけ", 4: "7月と12月だけ", 5: "物価で割り引く"}
fig, ax = plt.subplots(figsize=(8.8, 4.8))
yy = np.arange(len(rb))[::-1]
ax.barh(yy, rb.season_ratio * 100, height=0.55, color=C[0])
for y_, v in zip(yy, rb.season_ratio * 100):
    ax.text(v + 1, y_, f"{v:.0f}%", va="center", fontsize=9.5, color=INK)
ax.set_yticks(yy); ax.set_yticklabels([lab_map[i] for i in range(len(rb))])
ax.axvline(50, color=INK2, lw=0.8, ls=":")
ax.text(50.8, len(rb) - 0.45, "半分", fontsize=8.6, color=INK2)
ax.set_xlim(0, 80); ax.set_xlabel("夏と冬の上乗せの合計、2025年 ÷ 2000年（%）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"決め方を変えても、上乗せは2000年の{rb.season_ratio.min()*100:.0f}〜{rb.season_ratio.max()*100:.0f}%に", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：二人以上の世帯。物価は消費支出全体の名目と実質の増減率の差で割り引いた目安。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.2, right=0.97, top=0.9, bottom=0.17)
save(fig, "fig4_robustness.png")
print("figures ok")
