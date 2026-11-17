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
SRC = "出典：総務省「家計調査」（二人以上の世帯）、「消費者物価指数」（2025年基準）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
y = pd.read_csv(R / "annual_2015_2025.csv").set_index("year")
old = pd.read_csv(R / "annual_1963_2007.csv").set_index("year")
S = pd.read_csv(R / "monthly_share.csv").set_index("year")
S.columns = [int(c) for c in S.columns]

# ---- 図1：長期（名目） -------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.9))
ax.plot(old.index, old.yen / 1000, color=C[1], lw=2.2, label="1963〜2007年（農林漁家世帯を除く二人以上の世帯）")
ax.plot(y.index, y.laundry_yen / 1000, color=C[0], lw=2.2, marker="o", ms=4, label="2015〜2025年（二人以上の世帯）")
ax.annotate(f"{main['old_peak_year']}年 {main['old_peak_yen']/1000:.1f}千円", (main["old_peak_year"], main["old_peak_yen"] / 1000), xytext=(1999, 20.3),
            fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.annotate(f"2025年 {main['laundry_2025']/1000:.1f}千円", (2025, main["laundry_2025"] / 1000), xytext=(2010, 2.2),
            fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.text(2011, 12, "2008〜2014年は\n品目別の表なし", ha="center", fontsize=8.5, color=INK2)
ax.set_xlim(1962, 2026); ax.set_ylim(0, 22)
ax.set_ylabel("洗濯代（千円/年・1世帯）")
ax.legend(loc="upper left", frameon=False, fontsize=8.6)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"クリーニング代は{main['old_peak_year']}年が山。2025年はその{main['ratio_2025_to_peak_nominal']*100:.0f}%（名目）", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：家計調査の品目「洗濯代」（クリーニング代など）。名目の値（物価で割っていない）。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig1_long_run.png")

# ---- 図2：2015＝100 の名目・物価・実質 ----------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.8))
for col, lab, cc in [("laundry_yen", "名目の支出", C[1]), ("cpi_clean", "物価（クリーニング代Ａ・Ｂの平均）", C[0]), ("real_yen_2025prices", "実質の支出（物価で割った値）", C[2])]:
    v = y[col] / y[col].loc[2015] * 100
    ax.plot(y.index, v, color=cc, lw=2.2, marker="o", ms=4)
    ax.text(2025.25, v.loc[2025], f"{lab} {v.loc[2025]:.0f}", va="center", fontsize=9, color=INK)
ax.axhline(100, color=INK2, lw=0.8, ls=":")
ax.set_xlim(2015, 2030.2); ax.set_ylim(40, 145); ax.set_xticks(range(2015, 2026))
ax.set_xticklabels([str(v) for v in range(2015, 2026)], fontsize=9)
ax.set_ylabel("2015年＝100")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"値段は{main['cpi_clean_change_pct']:.0f}%上がり、名目は{abs(main['nominal_change_2015_2025_pct']):.0f}%、実質は{abs(main['real_change_2015_2025_pct']):.0f}%減った", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：二人以上の世帯の1世帯あたり年間の洗濯代。2015→2025年。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig2_nominal_real.png")

# ---- 図3：月ごとの割合 -------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.6))
mm = np.arange(1, 13); w = 0.38
a = S.loc[2015:2019].mean(); b = S.loc[2021:2025].mean()
ax.bar(mm - w / 2 - 0.02, a.values, width=w, color=C[0], label="2015〜2019年の平均")
ax.bar(mm + w / 2 + 0.02, b.values, width=w, color=C[1], label="2021〜2025年の平均")
ax.axhline(100 / 12, color=INK2, lw=0.8, ls=":")
ax.text(12.6, 100 / 12, "1/12", va="center", fontsize=8.5, color=INK2)
ax.set_xticks(mm); ax.set_xticklabels([f"{m}月" for m in mm])
ax.set_ylabel("年の洗濯代に占める割合（%）"); ax.set_ylim(0, 18)
ax.legend(loc="upper right", frameon=False, fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"衣替えの4〜6月と10〜11月で年の{main['peak5_share_2021_2025']:.0f}%。季節の形は変わらない", loc="left", fontsize=12)
fig.text(0.01, 0.01, f"注：4〜6月・10〜11月の割合は{main['peak5_share_2015_2019']:.1f}%（2015〜2019年）→{main['peak5_share_2021_2025']:.1f}%（2021〜2025年）。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.08, right=0.95, top=0.91, bottom=0.15)
save(fig, "fig3_monthly_share.png")

# ---- 図4：年齢別 2015→2025 ---------------------------------------------------------------------------
AG = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
fig, ax = plt.subplots(figsize=(8.8, 4.8))
for i, a_ in enumerate(AG):
    v0, v1 = req["yen_2015"][a_] / 1000, req["yen_2025"][a_] / 1000
    ax.plot([v0, v1], [i, i], color=GRID, lw=3, zorder=1)
    ax.scatter([v0], [i], s=70, color=C[0], zorder=2, label="2015年" if i == 0 else None)
    ax.scatter([v1], [i], s=70, color=C[1], zorder=3, label="2025年" if i == 0 else None)
    ax.text(max(v0, v1) + 0.25, i, f"{req['change_pct'][a_]:+.1f}%".replace("-", "−"), va="center", fontsize=9.5, color=INK)
ax.set_yticks(range(len(AG))); ax.set_yticklabels([f"世帯主 {a_}" for a_ in AG]); ax.invert_yaxis()
ax.set_xlim(1.5, 11.5); ax.set_xlabel("洗濯代（千円/年・1世帯）")
ax.legend(loc="lower right", frameon=False, fontsize=9)
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("どの年齢でも減った。最も減ったのは50〜59歳（−40%）", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：二人以上の世帯、世帯主の年齢階級別。単年の値で、年ごとの振れがある（3年平均の比較は results/requestion.json）。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.2, right=0.97, top=0.91, bottom=0.16)
save(fig, "fig4_by_age.png")
print("ok")
