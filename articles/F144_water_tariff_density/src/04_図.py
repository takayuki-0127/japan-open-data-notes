"""04 図：results/ から5枚の図を作る（事業名・市町村名は出さない）。"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSansJP" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP", "Noto Sans JP", "sans-serif"]
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
C1, C2, C3, GR = "#2b6cb0", "#dd6b20", "#2f855a", "#718096"

S = json.load(open(RES / "summary.json", encoding="utf-8"))
d = pd.read_csv(RES / "analysis_rows_noname.csv")

# 1. 料金の分布
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.hist(d["fee10"], bins=50, color=C1, alpha=0.85)
for v, lab in [(S["fee_p5"], "5%点"), (S["fee_median"], "中央値"), (S["fee_p95"], "95%点")]:
    ax.axvline(v, color=C2, ls="--", lw=1)
    ax.text(v, ax.get_ylim()[1] * 0.93, f"{lab}\n{v:,.0f}円", ha="center", fontsize=9, color=C2,
            bbox=dict(fc="white", ec="none", alpha=0.8))
ax.set_xlabel("家庭用 10m³ あたりの料金（口径13mm、円/月）")
ax.set_ylabel("事業の数")
ax.set_title(f"水道料金の分布（令和6年度・上水道の末端給水事業 {S['n']:,}）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig1_fee_distribution.png", dpi=150); plt.close(fig)

# 2. 密度と料金（ビン散布）
fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
for ax, col, lab in [(axes[0], "dens_pipe", "管路1kmあたりの給水人口（人、対数）"),
                     (axes[1], "pop_served", "給水人口（人、対数）")]:
    ax.scatter(d[col], d["fee10"], s=5, color=GR, alpha=0.3)
    bins = pd.qcut(np.log(d[col]), 20)
    g = d.groupby(bins, observed=True).agg(x=(col, "median"), y=("fee10", "median"))
    ax.plot(g["x"], g["y"], "o-", color=C1, ms=4, lw=1.5, label="20等分した中央値")
    ax.set_xscale("log"); ax.set_xlabel(lab)
    ax.set_ylim(0, 3700)
axes[0].set_ylabel("10m³ あたりの料金（円/月）")
axes[0].set_title("密度が高いほど安い", fontsize=11)
axes[1].set_title("規模でも下がるが、密度をそろえると差は小さい", fontsize=11)
axes[0].legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig(FIG / "fig2_density_scale.png", dpi=150); plt.close(fig)

# 3. 水源別（そのまま／規模・密度をそろえた差）
src = pd.read_csv(RES / "by_source.csv").set_index("src")
order = ["地下水等", "ダム以外の表流水", "ダム", "受水", "混合"]
src = src.loc[order]
fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
axes[0].barh(order[::-1], src["fee_med"][::-1], color=C1)
for i, v in enumerate(src["fee_med"][::-1]):
    axes[0].text(v + 20, i, f"{v:,.0f}円（{int(src['n'][::-1].iloc[i])}）", va="center", fontsize=9)
axes[0].set_xlim(0, 2300); axes[0].set_xlabel("料金の中央値（円/月）")
axes[0].set_title("主な水源別の料金（かっこは事業の数）", fontsize=11)
y = np.arange(len(order))[::-1]
axes[1].errorbar(src["adj_diff"] * 100, y, xerr=[(src["adj_diff"] - src["adj_lo"]) * 100, (src["adj_hi"] - src["adj_diff"]) * 100],
                 fmt="o", color=C2, capsize=3)
axes[1].axvline(0, color=GR, lw=1)
axes[1].set_yticks(y); axes[1].set_yticklabels(order)
axes[1].set_xlabel("地下水等の事業との差（%、95%区間）")
axes[1].set_title("給水人口と密度をそろえた差", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "fig3_by_source.png", dpi=150); plt.close(fig)

# 4. どれだけ説明できたか
sh = S["shapley"]; ci = S["shapley_ci"]
labs = ["密度", "水源", "規模"]
vals = [sh[k] for k in labs]
fig, ax = plt.subplots(figsize=(8.5, 4.5))
left = 0
cols = [C1, C2, C3]
for k, v, c in zip(labs, vals, cols):
    ax.barh(["規模・密度・水源"], [v * 100], left=left, color=c)
    ax.text(left + v * 50, 0, f"{k}\n{v*100:.0f}%", ha="center", va="center", color="white", fontsize=10)
    left += v * 100
ax.barh(["規模・密度・水源"], [100 - left], left=left, color="#e2e8f0")
ax.text(left + (100 - left) / 2, 0, f"説明できない\n{100-left:.0f}%", ha="center", va="center", fontsize=10)
ax.barh(["都道府県だけ"], [S["pref_only_r2"] * 100], color=GR)
ax.barh(["都道府県だけ"], [100 - S["pref_only_r2"] * 100], left=S["pref_only_r2"] * 100, color="#e2e8f0")
ax.text(S["pref_only_r2"] * 50, 1, f"{S['pref_only_r2']*100:.0f}%", ha="center", va="center", color="white")
ax.barh(["規模・密度・水源＋都道府県"], [S["main_fe_r2"] * 100], color="#4a5568")
ax.barh(["規模・密度・水源＋都道府県"], [100 - S["main_fe_r2"] * 100], left=S["main_fe_r2"] * 100, color="#e2e8f0")
ax.text(S["main_fe_r2"] * 50, 2, f"{S['main_fe_r2']*100:.0f}%", ha="center", va="center", color="white")
ax.set_xlim(0, 100); ax.set_xlabel("料金（対数）のばらつきのうち説明できた割合（%）")
ax.invert_yaxis()
ax.set_title("料金の差の4割弱を説明。いちばん大きいのは密度", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig4_explained.png", dpi=150); plt.close(fig)

# 5. 密度5分位の費用の内訳
q = pd.read_csv(RES / "density_quintiles.csv").set_index("dq")
parts = [("c_depr", "減価償却費"), ("c_labor", "職員給与費"), ("c_bulk", "受水費"), ("c_contract", "委託料"),
         ("c_repair", "修繕費"), ("c_interest", "支払利息"), ("c_power", "動力費")]
q["c_other_mean"] = q["c_total_mean"] - sum(q[c + "_mean"] for c, _ in parts)
parts.append(("c_other", "その他"))
fig, ax = plt.subplots(figsize=(9, 4.8))
bottom = np.zeros(len(q))
pal = ["#2b6cb0", "#63b3ed", "#dd6b20", "#f6ad55", "#2f855a", "#9ae6b4", "#a0aec0", "#e2e8f0"]
for (c, lab), col in zip(parts, pal):
    ax.bar(q.index, q[c + "_mean"], bottom=bottom, color=col, label=lab, width=0.6)
    bottom += q[c + "_mean"].values
ax.plot(q.index, q["price_mean"], "o", color="black", mfc="white", mew=1.5, ms=8, label="供給単価（平均）")
ax.set_xticks(range(5))
ax.set_xticklabels([f"{i}\n{v:.0f}人/km" for i, v in zip(["低い", "やや低い", "中", "やや高い", "高い"], q["dens_med"])])
ax.set_ylabel("有収水量1m³あたり（円）")
ax.set_xlabel("管路1kmあたりの給水人口（5等分、中央値）")
ax.set_title("密度が低い事業ほど1m³あたりの費用が高い（事業の平均）", fontsize=12)
ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper right")
fig.tight_layout(); fig.savefig(FIG / "fig5_cost_by_density.png", dpi=150); plt.close(fig)
print("ok")
