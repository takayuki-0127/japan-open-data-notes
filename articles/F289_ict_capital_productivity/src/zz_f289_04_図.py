"""04 図：figures/ に6枚。"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
ROOT = pathlib.Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 110, "savefig.dpi": 150})
res = json.load(open(ROOT / "results" / "main.json"))
t = pd.read_csv(ROOT / "results" / "B_sectors.csv", index_col=0)
C1, C2, CG = "#2b6cb0", "#dd6b20", "#a0aec0"

# 図1：ICT投資の比率（市場経済の部門の合計）
m = res["macro"]
ys = sorted(int(y) for y in m["ict_inv_share"])
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.plot(ys, [m["ict_inv_share"][str(y)] * 100 for y in ys], color=C1, lw=2, label="ICT（情報機器・通信機器・ソフトウェア）")
ax.plot(ys, [m["sw_inv_share"][str(y)] * 100 for y in ys], color=C2, lw=2, label="うちソフトウェア")
ax.set_ylabel("名目投資に占める割合（%）"); ax.set_ylim(0, None)
ax.set_title("図1 投資の中のICTの割合（市場経済の92部門の合計）")
ax.legend(frameon=False); fig.tight_layout(); fig.savefig(FIG / "fig1_ict_investment_share.png"); plt.close(fig)

# 図2：水準（2015年）
fig, ax = plt.subplots(figsize=(7.5, 5.2))
p = t["ict_producer"]
ax.scatter(t.loc[~p, "depth2015"], t.loc[~p, "LP2015"], s=26, color=C1, alpha=.75, label="ICTを使う側")
ax.scatter(t.loc[p, "depth2015"], t.loc[p, "LP2015"], s=36, color=C2, marker="D", label="ICTを作る側（6部門）")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("1時間あたりのICT資本（円、2015年価格、対数目盛）")
ax.set_ylabel("1時間あたりの実質付加価値（円、対数目盛）")
h1 = res["base"]["H1_level"]
ax.set_title(f"図2 ICT資本の多い産業ほど、労働生産性は高い（2015年、順位相関 {h1['rho']:.2f}）")
ax.legend(frameon=False, loc="lower right"); fig.tight_layout(); fig.savefig(FIG / "fig2_level_2015.png"); plt.close(fig)

# 図3：伸び（2×2）
fig, axes = plt.subplots(2, 2, figsize=(10, 7.6), sharex="col")
for j, pn in enumerate(["前半", "後半"]):
    lab = {"前半": "1995→2007年", "後半": "2007→2019年"}[pn]
    for i, (yv, yl, key) in enumerate([(f"g_LP_{pn}", "労働生産性の伸び（年率）", f"H2_{pn}"), (f"TFP_{pn}", "TFPの伸び（年平均）", f"H3_{pn}")]):
        ax = axes[i, j]
        x = t[f"g_depth_{pn}"] * 100; y = t[yv] * 100
        ax.scatter(x[~p], y[~p], s=20, color=C1, alpha=.7); ax.scatter(x[p], y[p], s=28, color=C2, marker="D")
        ax.axhline(0, color=CG, lw=.8); ax.axvline(0, color=CG, lw=.8)
        r = res["base"][key]
        ax.set_title(f"{lab}　順位相関 {r['rho']:+.2f}（95%区間 {r['lo']:+.2f}〜{r['hi']:+.2f}）", fontsize=10)
        if j == 0: ax.set_ylabel(yl + "（%）")
        if i == 1: ax.set_xlabel("1時間あたりICT資本の伸び（年率、%）")
fig.suptitle("図3 ICT資本を増やした産業ほど伸びたか（上：労働生産性、下：TFP）", y=.995)
fig.tight_layout(); fig.savefig(FIG / "fig3_growth.png"); plt.close(fig)

# 図4：相関のまとめ（基本と頑健性）
rows = [("H1 水準（2015年）", "H1_level"), ("H2 伸び 前半", "H2_前半"), ("H2 伸び 後半", "H2_後半"),
        ("H3 TFP 前半", "H3_前半"), ("H3 TFP 後半", "H3_後半"), ("H4 前半のICT投資比率→後半の伸び", "H4")]
conds = [("基本", "base", C1), ("ソフトウェアだけ", "R1_software", C2), ("作る側を除く", "R2_noprod", "#38a169"), ("後半を2020年まで", "R4_to2020", "#805ad5")]
fig, ax = plt.subplots(figsize=(9, 5.4))
for k, (lab, key) in enumerate(rows):
    for q, (cl, ck, col) in enumerate(conds):
        r = res[ck][key]; yy = k + (q - 1.5) * 0.18
        ax.plot([r["lo"], r["hi"]], [yy, yy], color=col, lw=1.4) if q == 0 else None
        ax.scatter(r["rho"], yy, color=col, s=28 if q == 0 else 18, zorder=3, label=cl if k == 0 else None)
ax.axvline(0, color="k", lw=.8)
for v in (-0.2, 0.2, 0.3): ax.axvline(v, color=CG, lw=.6, ls=":")
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows]); ax.invert_yaxis()
ax.set_xlabel("順位相関（線は基本の95%区間）"); ax.set_xlim(-0.6, 0.9)
ax.set_title("図5 4つの問いの答え（点は条件ごとの順位相関）")
ax.legend(frameon=False, loc="lower right", fontsize=9); fig.tight_layout(); fig.savefig(FIG / "fig5_summary.png"); plt.close(fig)

# 図5：問い直し（水準の相関は資本全体の多さで説明できるか）
re = res["reask"]; yrs = [1995, 2007, 2015, 2019]
fig, ax = plt.subplots(figsize=(8, 4.4))
ax.plot(yrs, [re[str(y)]["nonict_depth_vs_LP"] for y in yrs], "o-", color=CG, label="ICT以外の資本の多さ と 労働生産性")
ax.plot(yrs, [re[str(y)]["ict_depth_vs_LP"] for y in yrs], "o-", color=C1, label="ICT資本の多さ と 労働生産性")
ax.plot(yrs, [re[str(y)]["ict_vs_LP_partial_nonict"] for y in yrs], "o--", color=C2, label="ICT資本の多さ と 労働生産性（ICT以外の資本の多さをそろえた偏相関）")
ax.axhline(0, color="k", lw=.8); ax.set_ylim(-0.2, 1); ax.set_ylabel("順位相関")
ax.set_title("図6 問い直し：ICTの分だけで見た結びつきは、年を追って強くなった")
ax.legend(frameon=False, fontsize=9, loc="upper left"); fig.tight_layout(); fig.savefig(FIG / "fig6_reask.png"); plt.close(fig)

# 図6：H4 前半のICT投資比率 と 後半の労働生産性の伸び
fig, ax = plt.subplots(figsize=(7.5, 5))
x = t["ict_inv_ratio_前半"] * 100; y = t["g_LP_後半"] * 100
ax.scatter(x[~p], y[~p], s=24, color=C1, alpha=.75, label="ICTを使う側"); ax.scatter(x[p], y[p], s=34, color=C2, marker="D", label="ICTを作る側")
ax.axhline(0, color=CG, lw=.8); ax.set_xscale("log")
r = res["base"]["H4"]
ax.set_xlabel("1995〜2007年のICT投資比率（名目投資に占める%、対数目盛）"); ax.set_ylabel("2007→2019年の労働生産性の伸び（年率、%）")
ax.set_title(f"図4 白書の指標（ICT投資比率）と、その後の伸び（順位相関 {r['rho']:+.2f}）")
ax.legend(frameon=False); fig.tight_layout(); fig.savefig(FIG / "fig4_h4.png"); plt.close(fig)
print(sorted(x.name for x in FIG.glob("*.png")))
