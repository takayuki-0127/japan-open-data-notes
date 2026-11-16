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
SRC = "出典：環境省「温泉利用状況経年変化表」をもとに作成者が加工して作成（宿泊利用人員は参考数値）"
META = {"Software": None}
main = json.load(open(R / "main.json", encoding="utf-8")); req = json.load(open(R / "requestion.json", encoding="utf-8"))
d = pd.read_csv(R / "onsen_series.csv", index_col="fy")
k = pd.read_csv(R / "requestion_kokumin.csv", index_col="fy")


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


# 図1：延べ宿泊
fig, ax = plt.subplots(figsize=(8.8, 4.8))
ax.plot(d.index, d.stays / 1e6, color=C[0], lw=2.4)
POS = {main["stays_peak_fy"]: (1970, 155), 1994: (1997, 158), 2020: (2006, 62), 2024: (2010, 150)}
for y in [main["stays_peak_fy"], 1994, 2020, 2024]:
    v = d.loc[y, "stays"] / 1e6
    ax.annotate(f"{y}年度 {v:,.1f}百万人", (y, v), xytext=POS[y], fontsize=8.5, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.7))
ax.set_ylim(0, 175); ax.set_xlim(1955, 2026)
ax.set_ylabel("年度の延べ宿泊利用人員（百万人）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"温泉地の延べ宿泊は1992年度がいちばん多く、30年（1994→2024年度）で{main['stays_pct_1994_2024']:.1f}%", loc="left", fontsize=11.5)
foot(fig)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.12)
save(fig, "fig1_stays.png")

# 図2：施設数と収容定員（1975年度=100）
fig, ax = plt.subplots(figsize=(8.8, 4.8))
s = d.loc[1975:]
for col, c, nm in [("facilities", C[1], "宿泊施設の数"), ("capacity", C[2], "収容定員"), ("cap_per_fac", C[0], "1軒あたりの収容定員")]:
    y = s[col] / s.loc[1994, col] * 100
    ax.plot(y.index, y, color=c, lw=2.3, label=nm)
    ax.text(2024.6, y.loc[2024], f"{y.loc[2024]:.0f}", va="center", fontsize=9, color=c)
ax.axhline(100, color=INK2, lw=0.7); ax.axvline(1994, color=INK2, lw=0.7, ls=":")
ax.set_xlim(1975, 2028); ax.set_ylabel("1994年度 = 100")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.set_title(f"宿の数は{main['fac_peak_fy']}年度の{main['fac_peak']:,.0f}軒から減り、1軒あたりの定員は{main['cap_per_fac_1994']:.0f}→{main['cap_per_fac_2024']:.0f}人に", loc="left", fontsize=11.5)
foot(fig)
fig.subplots_adjust(left=0.09, right=0.95, top=0.91, bottom=0.12)
save(fig, "fig2_facilities_capacity.png")

# 図3：稼働の目安
fig, ax = plt.subplots(figsize=(8.8, 4.6))
u = d.loc[1970:, "util"]
ax.plot(u.index, u, color=C[0], lw=2.3)
for y in [1994, 2019, 2024]:
    ax.text(y, u.loc[y] + 1, f"{u.loc[y]:.1f}", ha="center", fontsize=9, color=C[0])
ax.set_ylim(0, 45); ax.set_ylabel("延べ宿泊 ÷ 収容定員 ÷ 365（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"収容定員あたりの泊まりの目安は{main['util_1994']:.1f}%（1994年度）→{main['util_2019']:.1f}%（2019年度）", loc="left", fontsize=11.5)
foot(fig, "注：定員いっぱいに毎日泊まると100%になる目安。客室の稼働率とは定義が違う。")
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig3_utilization.png")

# 図4：国民保養温泉地とそれ以外（1994年度=100）
fig, ax = plt.subplots(figsize=(8.8, 4.6))
for col, c, nm in [("kokumin_stays", C[1], "国民保養温泉地"), ("other_stays", C[0], "それ以外の温泉地")]:
    y = k[col] / k.loc[1994, col] * 100
    ax.plot(y.index, y, color=c, lw=2.3, label=nm)
    ax.text(2024.6, y.loc[2024], f"{y.loc[2024]:.0f}", va="center", fontsize=9, color=c)
ax.axhline(100, color=INK2, lw=0.7)
ax.set_xlim(1976, 2028); ax.set_ylabel("延べ宿泊（1994年度 = 100）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="lower left", frameon=False, fontsize=9)
ax.set_title(f"国民保養温泉地の延べ宿泊は{req['kokumin_pct_1994_2024']:.0f}%、それ以外は{req['other_pct_1994_2024']:.0f}%（1994→2024年度）", loc="left", fontsize=11.5)
foot(fig, "注：国民保養温泉地は環境大臣が指定する温泉地。指定の数は年によって変わる。")
fig.subplots_adjust(left=0.09, right=0.95, top=0.91, bottom=0.14)
save(fig, "fig4_kokumin.png")
print("ok")
