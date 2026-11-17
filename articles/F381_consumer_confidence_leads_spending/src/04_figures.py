"""図を作る（PNG。日付などのメタデータは入れない）。ネットにはつながない。"""
import json, sys, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import RES, FIG, DATA

for f in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    if pathlib.Path(f).exists():
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.6, "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
                     "svg.hashsalt": "f381"})
B, O, G = "#2a78d6", "#eb6834", "#8a8984"
SRC = "出典：内閣府「消費動向調査」「四半期別GDP速報」（2026年7-9月期1次速報）、総務省「家計調査」「消費者物価指数」をもとに作成者が加工して作成"
FIG.mkdir(exist_ok=True)
main = json.load(open(RES / "main.json", encoding="utf-8"))


def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7, color="#52514e")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


d = pd.read_csv(DATA / "quarterly_panel.csv")
x = d.year + (d.q - 1) / 4

# 図1：態度指数の変化と消費の前期比
fig, ax = plt.subplots(2, 1, figsize=(9, 6.2), sharex=True)
fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.1, hspace=0.25)
ax[0].bar(x, d.d_cci, width=0.2, color=B)
ax[0].set_ylabel("前期差（ポイント）")
ax[0].set_title("消費者態度指数の前期からの変化（四半期平均、季節調整値）", fontsize=10, loc="left")
ax[1].bar(x, d.g_hc_xrent, width=0.2, color=np.where(d.shock > 0, G, O))
ax[1].set_ylabel("前期比（%）")
ax[1].set_title("実質の家計消費（持ち家の帰属家賃を除く）の前期比　灰色は消費税の引き上げ前後・2020年の感染症の四半期", fontsize=10, loc="left")
for a in ax:
    a.axhline(0, color="#52514e", lw=0.8)
fig.suptitle(f"態度指数が大きく動いた次の期に、消費が同じ向きに動くとは限らない（前の期の変化との相関 r={main['crosscorr']['r_lead1']:.2f}）",
             x=0.01, ha="left", fontsize=12)
save(fig, "fig1_cci_vs_consumption.png")

# 図2：時差の相関
cc = pd.read_csv(RES / "crosscorr_quarterly.csv")
fig, ax = plt.subplots(figsize=(8, 4.6))
fig.subplots_adjust(left=0.1, right=0.97, top=0.86, bottom=0.2)
ax.errorbar(cc.k, cc.r, yerr=[cc.r - cc.lo95, cc.hi95 - cc.r], fmt="o", color=B, ms=8, capsize=4, lw=2)
ax.axhline(0, color="#52514e", lw=0.8)
ax.set_xticks(cc.k)
ax.set_xticklabels([f"{k}" for k in cc.k])
ax.set_xlabel("ずれ（四半期）　プラス＝態度指数の変化のあとの消費、マイナス＝前の消費")
ax.set_ylabel("相関係数（点と95%区間）")
for k, r in zip(cc.k, cc.r):
    ax.annotate(f"{r:.2f}", (k, r), xytext=(8, 0), textcoords="offset points", fontsize=8, color="#0b0b0b", va="center")
pos = cc[cc.k >= 1]
assert ((pos.lo95 < 0) & (pos.hi95 > 0)).all()
fig.suptitle(f"態度指数が動いたあと1〜4期の消費との相関は {pos.r.min():.2f}〜{pos.r.max():.2f} で、95%区間はどれも0をまたぐ", x=0.01, ha="left", fontsize=12)
ax.set_title("態度指数の前期差 × 実質家計消費の前期比（1994〜2026年、消費税・感染症の四半期を除く）", fontsize=9, loc="left")
save(fig, "fig2_crosscorr.png")

# 図3：予測の誤差の比（頑健性と構成指標）
rob = pd.read_csv(RES / "robustness.csv")
comp = pd.read_csv(RES / "components.csv")
lab = list(rob.case) + [f"{r.y_label}：{r.x_label}" for r in comp[comp.y != "g_hc_xrent"].itertuples()] + \
      [f"家計消費：{r.x_label}" for r in comp[(comp.y == "g_hc_xrent") & (comp.x != "cci")].itertuples()]
val = list(rob.rmse_ratio) + list(comp[comp.y != "g_hc_xrent"].rmse_ratio) + list(comp[(comp.y == "g_hc_xrent") & (comp.x != "cci")].rmse_ratio)
grp = ["rob"] * len(rob) + ["comp"] * (len(val) - len(rob))
fig, ax = plt.subplots(figsize=(9, 8.6))
fig.subplots_adjust(left=0.47, right=0.95, top=0.9, bottom=0.08)
yy = np.arange(len(val))[::-1]
ax.barh(yy, np.array(val) - 1, left=1, color=[B if g == "rob" else O for g in grp], height=0.6)
ax.axvline(1, color="#0b0b0b", lw=1)
ax.axvline(0.95, color="#52514e", lw=0.8, ls="--")
ax.text(0.951, yy[0] + 0.8, "5%改善の線（H1 の基準）", fontsize=8, color="#52514e")
ax.set_yticks(yy)
ax.set_yticklabels(lab, fontsize=8)
ax.set_xlim(0.93, 1.07)
ax.set_xlabel("予測の誤差の比（態度指数あり ÷ 消費の過去だけ。1未満なら改善）")
for y0, v in zip(yy, val):
    ax.text(max(v, 1) + 0.002, y0, f"{v:.3f}", va="center", fontsize=7, color="#0b0b0b")
ax.grid(axis="y", visible=False)
fig.suptitle(f"{len(val)}通りのどれでも、態度指数を足して1期先の予測が5%以上よくなるものはない（最小 {min(val):.3f}）", x=0.01, ha="left", fontsize=12)
ax.set_title("青＝主な結果と頑健性（家計消費）、橙＝目的変数・指標の入れ替え。2005〜2026年の逐次の1期先予測", fontsize=9, loc="left", x=-0.6)
save(fig, "fig3_forecast_ratio.png")

# 図4：問い直し 態度指数と物価の上がり方
m = pd.read_csv(RES / "requestion_monthly.csv").dropna(subset=["cci", "infl"])
rq = json.load(open(RES / "requestion.json", encoding="utf-8"))
fig, ax = plt.subplots(figsize=(8, 5.4))
fig.subplots_adjust(left=0.1, right=0.97, top=0.86, bottom=0.16)
e = m[m.year <= 2020]
l = m[m.year >= 2021]
ax.scatter(e.infl, e.cci, s=18, color=B, alpha=0.7, label="2004年4月〜2020年12月", edgecolors="#fcfcfb", linewidths=0.5)
ax.scatter(l.infl, l.cci, s=18, color=O, alpha=0.85, label="2021年1月〜2026年9月", edgecolors="#fcfcfb", linewidths=0.5)
ax.set_xlabel("消費者物価指数（持ち家の帰属家賃を除く総合）の前年同月比（%）")
ax.set_ylabel("消費者態度指数（季節調整値）")
ax.legend(frameon=False, loc="lower left")
fig.suptitle(f"態度指数は、消費より物価の上がり方と逆に動く（相関 物価 {rq['all']['r_cci_infl']:.2f}、消費 {rq['all']['r_cci_cons']:.2f}）",
             x=0.01, ha="left", fontsize=12)
ax.set_title("月次。消費は家計調査の消費支出の実質増減率（前年同月比）との相関", fontsize=9, loc="left")
save(fig, "fig4_cci_vs_inflation.png")
print("figures ok")
