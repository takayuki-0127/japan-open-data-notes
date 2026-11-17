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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：国土交通省「建設総合統計」、内閣府「県民経済計算」をもとに作成者が加工して作成"
META = {"Software": None}


def finish(fig, ax, title, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.19)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)


m = json.load(open(R / "main.json", encoding="utf-8"))
w = pd.read_csv(R / "pref_wide.csv", dtype={"code": str}).sort_values("code").reset_index(drop=True)
nat = pd.read_csv(R / "national.csv").set_index("year")
rel = pd.read_csv(R / "requestion_relative.csv").set_index("year")
d = pd.read_csv(R / "pref_year_ratio.csv", dtype={"code": str})
Y = [1996, 2005, 2015, 2023]
short = lambda s: s if s == "北海道" else s[:-1]
METRO = ["埼玉県", "千葉県", "東京都", "神奈川県", "岐阜県", "愛知県", "三重県", "京都府", "大阪府", "兵庫県", "奈良県"]

# 図1：県ごとの割合 1996 と 2023（北から南の順）
fig, ax = plt.subplots(figsize=(10, 5.6))
x = np.arange(len(w))
ax.vlines(x, w.r2023, w.r1996, color=GRID, lw=2.2)
ax.scatter(x, w.r1996, s=26, color="#b9b8b3", label="1996年度", zorder=3)
ax.scatter(x, w.r2023, s=28, color=C[0], label="2023年度", zorder=3)
ax.set_xticks(x, [short(s) for s in w.pref], rotation=90, fontsize=8.5)
for lab in ax.get_xticklabels():
    if lab.get_text() in [short(p) for p in METRO]:
        lab.set_color(C[1])
ax.set_xlim(-0.8, len(w) - 0.2); ax.set_ylim(0, 18)
ax.set_ylabel("公共工事の出来高÷県内総生産（%）")
ax.legend(loc="upper right", frameon=False, fontsize=9.5)
ax.text(0.99, 0.84, "橙の県名：三大都市圏", transform=ax.transAxes, ha="right", fontsize=9, color=C[1])
finish(fig, ax, f"公共工事の重さ：全国 {m['national_ratio']['1996']:.1f}% → {m['national_ratio']['2023']:.1f}%、47県のうち{47 - m['n_up_1996_2023']}で下がった")
fig.subplots_adjust(bottom=0.2)
save(fig, "fig1_ratio_by_pref.png")

# 図2：地方圏と三大都市圏の中央値の推移
fig, ax = plt.subplots(figsize=(9, 5.4))
xx = np.arange(len(Y))
for a, c in [("local_median", C[0]), ("metro_median", C[1])]:
    ax.plot(xx, rel[a].values, color=c, lw=2.4, marker="o", label="地方圏（36道県）の中央値" if a == "local_median" else "三大都市圏（1都2府8県）の中央値")
    for i, v in enumerate(rel[a].values):
        ax.text(i, v + 0.25, f"{v:.1f}%", ha="center", va="bottom", fontsize=9.5, color=c)
ax.plot(xx, [m["national_ratio"][str(y)] for y in Y], color=INK2, lw=1.4, ls="--", label="全国（合計どうしの比）")
for i, y in enumerate(Y):
    ax.text(i, 0.4, f"差 {rel.loc[y, 'gap_pt']:.1f}pt／{rel.loc[y, 'times']:.2f}倍", ha="center", fontsize=9, color=INK2)
ax.set_xticks(xx, [f"{y}年度" for y in Y]); ax.set_ylim(0, 10.5); ax.set_xlim(-0.4, 3.4)
ax.set_ylabel("公共工事の出来高÷県内総生産（%）")
ax.legend(loc="upper right", frameon=False, fontsize=9)
finish(fig, ax, f"地方圏と三大都市圏の差は {rel.loc[1996, 'gap_pt']:.1f}pt → {rel.loc[2023, 'gap_pt']:.1f}pt。倍率では {rel.loc[1996, 'times']:.2f} → {rel.loc[2023, 'times']:.2f}倍")
save(fig, "fig2_local_vs_metro.png")

# 図3：1996年度の水準と、2023年度までの変化
fig, ax = plt.subplots(figsize=(9, 5.6))
mt = w.pref.isin(METRO)
ax.scatter(w[~mt].r1996, w[~mt].chg, s=30, color=C[0], label="地方圏", lw=0)
ax.scatter(w[mt].r1996, w[mt].chg, s=30, color=C[1], label="三大都市圏", lw=0)
b, a = np.polyfit(w.r1996, w.chg, 1)
xs = np.linspace(w.r1996.min(), w.r1996.max(), 50)
ax.plot(xs, a + b * xs, color=INK2, lw=1.2, ls="--")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xlabel("1996年度の公共工事÷県内総生産（%）"); ax.set_ylabel("2023年度までの変化（ポイント）")
ax.legend(loc="lower left", frameon=False, fontsize=9.5)
finish(fig, ax, f"高かった県ほど大きく下がった：相関 {m['hypotheses']['H3']['r_level_change']:.2f}（1ポイント高いと {abs(m['slope_level_change']):.2f}ポイント多く低下）", grid="both")
fig.subplots_adjust(bottom=0.19)
save(fig, "fig3_level_vs_change.png")

# 図4：建設の出来高に占める公共の割合（中央値）
fig, ax = plt.subplots(figsize=(9, 5.4))
for a, c, lab in [("local_share_total", C[0], "地方圏の中央値"), ("metro_share_total", C[1], "三大都市圏の中央値")]:
    ax.plot(xx, rel[a].values, color=c, lw=2.4, marker="o", label=lab)
    for i, v in enumerate(rel[a].values):
        ax.text(i, v + 1, f"{v:.1f}%", ha="center", va="bottom", fontsize=9.5, color=c)
ax.plot(xx, nat.loc[Y, "share_total"].values, color=INK2, lw=1.4, ls="--", label="全国")
ax.set_xticks(xx, [f"{y}年度" for y in Y]); ax.set_ylim(0, 65); ax.set_xlim(-0.4, 3.4)
ax.set_ylabel("建設の出来高のうち公共工事の割合（%）")
ax.legend(loc="lower right", frameon=False, fontsize=9)
finish(fig, ax, f"建設の中での公共の割合は下がっていない：地方圏 {rel.loc[1996, 'local_share_total']:.1f}% → {rel.loc[2023, 'local_share_total']:.1f}%")
save(fig, "fig4_public_share_of_construction.png")
