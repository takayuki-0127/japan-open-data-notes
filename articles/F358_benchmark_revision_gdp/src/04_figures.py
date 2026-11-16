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
SRC = "出典：内閣府「四半期別GDP速報」2025年7-9月期1次速報（2015年基準）・2次速報（2020年基準）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
t = pd.read_csv(R / "gdp_revisions.csv").set_index("year")
cw = pd.read_csv(R / "nominal_revision_by_component.csv").set_index("year")

# ---- 図1：名目GDPの新旧 ---------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(t.index, t.nominal_old / 1000, color=C[0], lw=2.2, label="2015年基準（2025年11月の公表）")
ax.plot(t.index, t.nominal_new / 1000, color=C[1], lw=2.2, label="2020年基準（2025年12月の公表）")
ax.axhline(600, color=INK2, lw=0.8, ls=":")
ax.text(1995, 603, "600兆円", fontsize=8.8, color=INK2)
ax.annotate(f"2024年 {main['nominal_2024_old']/1000:.1f}兆円", (2024, main["nominal_2024_old"] / 1000), xytext=(2013.5, 590), fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.annotate(f"2024年 {main['nominal_2024_new']/1000:.1f}兆円", (2024, main["nominal_2024_new"] / 1000), xytext=(2012.5, 630), fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.set_xlim(1994, 2025); ax.set_ylim(480, 650)
ax.set_ylabel("名目GDP（兆円、暦年）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"基準改定で2024年の名目GDPは{main['rev_2024_trillion']:.1f}兆円（{main['rev_2024_pct']:.1f}%）上に", loc="left", fontsize=12)
fig.text(0.01, 0.01, f"注：600兆円を初めて超えた年は、2015年基準では{req['old_first_above_600']}年、2020年基準では{req['new_first_above_600']}年。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig1_nominal_levels.png")

# ---- 図2：名目の水準の書き換え（%） -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.8))
ax.bar(t.index, t.nominal_level_rev_pct, width=0.75, color=C[1])
for y in [1994, main["rev_min_year"], 2019, 2024]:
    v = t.loc[y, "nominal_level_rev_pct"]
    ax.text(y, v + 0.08, f"{v:.1f}", ha="center", fontsize=8.8, color=INK)
ax.set_xlim(1993, 2025); ax.set_ylim(0, 5)
ax.set_ylabel("名目GDPの書き換え（%、新÷旧−1）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"どの年も上に書き換わり、幅は{main['rev_min_pct']:.1f}〜{main['rev_max_pct']:.1f}%。2021年から大きい", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：二つの公表回の差。基準改定と同時に行われた年次推計の見直しも含む。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig2_level_revision_pct.png")

# ---- 図3：実質の前年比の新旧 --------------------------------------------------------------------
q = t.loc[1995:2024]
fig, ax = plt.subplots(figsize=(8.8, 4.8))
w = 0.4
ax.bar(q.index - w / 2, q.real_growth_old, width=w, color=C[0], label="2015年基準")
ax.bar(q.index + w / 2, q.real_growth_new, width=w, color=C[1], label="2020年基準")
ax.axhline(0, color=INK2, lw=0.8)
for y in [2014, 2021, 2023]:
    ax.text(y, max(q.loc[y, "real_growth_old"], q.loc[y, "real_growth_new"]) + 0.3, f"{q.loc[y,'real_growth_rev']:+.2f}", ha="center", fontsize=8.6, color=INK)
ax.legend(loc="lower left", frameon=False, fontsize=9)
ax.set_xlim(1994, 2025); ax.set_ylim(-7, 5.5)
ax.set_ylabel("実質GDPの前年比（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
H2 = main["hypotheses"]["H2"]
ax.set_title(f"実質の伸び率の書き換えは平均{H2['value']:.2f}ポイント。最大は2021年の+0.87", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：数字は書き換え（新−旧、ポイント）。符号が変わったのは2011年（+0.02%→−0.20%）だけ。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig3_real_growth.png")

# ---- 図4：2024年の書き換えの内訳 -------------------------------------------------------------------
names = {"business_inv": "民間企業設備", "pce": "民間最終消費支出", "housing": "民間住宅", "gov_cons": "政府最終消費支出", "private_inv_change": "民間在庫変動",
         "public_inv": "公的固定資本形成", "exports": "輸出", "public_inv_change": "公的在庫変動", "imports": "輸入（差し引く側）"}
c = pd.Series(main["components_2024"]).sort_values()
fig, ax = plt.subplots(figsize=(8.8, 4.8))
yy = np.arange(len(c))
ax.barh(yy, c.values, height=0.6, color=[C[1] if v >= 0 else C[0] for v in c.values])
for y_, v in zip(yy, c.values):
    ax.text(v + (0.2 if v >= 0 else -0.2), y_, f"{v:+.1f}", va="center", ha="left" if v >= 0 else "right", fontsize=9, color=INK)
ax.set_yticks(yy); ax.set_yticklabels([names[k] for k in c.index])
ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlim(-3, 15)
ax.set_xlabel("2024年の名目の書き換え（兆円、新−旧）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"2024年の+{main['rev_2024_trillion']:.1f}兆円のうち、企業設備が+{c['business_inv']:.1f}兆円、消費が+{c['pce']:.1f}兆円", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：輸入は GDP から差し引くので、輸入の上方修正は GDP を下げる向き（ここでは符号を GDP への影響にそろえた）。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.2, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig4_components_2024.png")
print("figures ok")
