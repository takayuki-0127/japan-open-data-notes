"""図を作る。"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG

FIG.mkdir(parents=True, exist_ok=True)
C1, C2, C3, GR = "#2a6f97", "#e07a5f", "#81b29a", "#8d99ae"
df = pd.read_csv(DATA / "panel.csv")
yr = pd.read_csv(RES / "distance_by_year.csv")
per = pd.read_csv(RES / "distance_by_period.csv")
rob = pd.read_csv(RES / "robustness.csv")
rob2 = pd.read_csv(RES / "robustness_period.csv")
rs = pd.read_csv(RES / "robustness_shinkansen.csv")
ev = pd.read_csv(RES / "shinkansen_event.csv")
res25 = pd.read_csv(RES / "residuals_2025.csv")

# 1) 2025年：距離と「出発・到着の大きさから見込まれる移動」に対する比
g = df[df.year == 2025].copy()
T = g.flow.sum()
out_o = g.groupby("o").flow.sum(); in_d = g.groupby("d").flow.sum()
g["exp"] = g.o.map(out_o) * g.d.map(in_d) / T
g["ratio"] = g.flow / g["exp"]
fig, ax = plt.subplots(figsize=(7.2, 5))
for a, col, lab in [(0, GR, "隣接していない"), (1, C2, "隣接している")]:
    s = g[(g.adj == a) & (g.flow > 0)]
    ax.scatter(s.dist, s.ratio, s=7 if a == 0 else 16, alpha=.45 if a == 0 else .85, color=col, label=lab, lw=0)
ax.set_xscale("log"); ax.set_yscale("log")
x = np.linspace(np.log(20), np.log(2300), 50)
for b, col, lab in [(yr.loc[yr.year == 2025, "ppml"].item(), C1, "PPML の傾き"), (yr.loc[yr.year == 2025, "ols"].item(), C3, "対数の最小二乗法の傾き")]:
    s = g[g.flow > 0]
    a0 = np.average(np.log(s.ratio) - b * np.log(s.dist), weights=s.flow if "PPML" in lab else None)
    ax.plot(np.exp(x), np.exp(a0 + b * x), color=col, lw=2.2, label=f"{lab}（{b:.2f}）")
ax.set_xlabel("県庁所在地どうしの距離（km、対数目盛）")
ax.set_ylabel("実際の移動 ÷ 出発・到着の大きさから見込まれる移動（対数目盛）")
ax.set_title("2025年：遠い県どうしほど、移動は見込みより少ない（47×46組）")
ax.legend(fontsize=9, loc="lower left"); ax.grid(alpha=.3, which="both")
fig.tight_layout(); fig.savefig(FIG / "f33_scatter_2025.png"); plt.close(fig)

# 2) 年ごとの距離の弾力性：対数 OLS と PPML
fig, ax = plt.subplots(figsize=(7.2, 4.4))
for c, se, col, lab in [("ols", "ols_se", C3, "対数の最小二乗法（出発・到着の固定効果）"),
                        ("ppml", "ppml_se", C1, "PPML（出発・到着の固定効果）"),
                        ("ppml_ctrl", "ppml_ctrl_se", C2, "PPML＋隣接・同じ地方")]:
    ax.plot(yr.year, yr[c], color=col, lw=2, label=lab)
    ax.fill_between(yr.year, yr[c] - 1.96 * yr[se], yr[c] + 1.96 * yr[se], color=col, alpha=.15)
ax.set_ylabel("距離の弾力性（距離1%あたりの移動の変化%）")
ax.set_title("距離の効き方：手法で大きく違い、37年でわずかに弱まった")
ax.legend(fontsize=9, loc="lower right"); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "f33_elasticity_by_year.png"); plt.close(fig)

# 3) 期間ごとの弾力性（基本と、東京圏を除く場合）
fig, ax = plt.subplots(figsize=(7.2, 4.2))
xs = np.arange(len(per))
ax.errorbar(xs, per.b, yerr=1.96 * per.se, fmt="o-", color=C1, capsize=4, label="基本（すべての組）")
pf_ = pd.read_csv(RES / "robustness_period_full.csv")
tk = pf_[pf_.setting == "東京圏を除く"]
ax.errorbar(xs + .08, tk.b, yerr=1.96 * tk.se, fmt="s--", color=C2, capsize=4, label="東京圏（1都3県）を発着とする移動を除く")
import json
sm = json.load(open(RES / "summary.json", encoding="utf-8"))["period_diff_2020s_minus_1990s"]
ax.set_xlabel(f"基本：2020〜25年 − 1989〜95年 = {sm['diff']:+.3f}（標準誤差 {sm['se']:.3f}）。期間どうしの差は、縦線（水準のぶれ）より精度よく測れる", fontsize=8.5)
ax.set_xticks(xs); ax.set_xticklabels([p.replace("_", "〜") for p in per.period])
ax.set_ylabel("距離の弾力性（PPML）")
ax.set_title("弱まったのは東京圏が絡む移動。除くと変化はほぼない")
ax.legend(fontsize=9, loc="upper left"); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "f33_elasticity_by_period.png"); plt.close(fig)

# 4) 2025年の残差：見込みより多い・少ない組（移動者500人以上）
b = res25[res25.flow >= 500].copy()
short = lambda x: x if x == "北海道" else x[:-1]
b["label"] = b.o_name.map(short) + "→" + b.d_name.map(short)
top = b.sort_values("ratio", ascending=False).head(10)
bot = b.sort_values("ratio").head(10)
fig, axs = plt.subplots(1, 2, figsize=(8.6, 4.6))
axs[0].barh(top.label[::-1], top.ratio[::-1], color=C2); axs[0].set_title("見込みより多い（実際÷予測）")
axs[1].barh(bot.label[::-1], bot.ratio[::-1], color=C1); axs[1].set_title("見込みより少ない（実際÷予測）")
for a in axs:
    a.axvline(1, color="k", lw=.8); a.grid(alpha=.3, axis="x"); a.tick_params(axis="y", labelsize=9)
fig.suptitle("2025年：重力モデル（距離・隣接・同じ地方）の予測と比べた移動（移動者500人以上の組）", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "f33_residuals_2025.png"); plt.close(fig)

# 5) 新幹線でつながった前後（イベントスタディ）
fig, ax = plt.subplots(figsize=(7.2, 4.2))
ax.errorbar(ev.k, ev.b, yerr=1.96 * ev.se, fmt="o-", color=C1, capsize=3)
ax.axhline(0, color="k", lw=.8); ax.axvline(-0.5, color=GR, ls="--")
ax.set_xlabel("新幹線網でつながった年からの年数（−6 と 9 は、それより前後をまとめたもの）")
ax.set_ylabel("移動の変化（対数、つながる前年＝0）")
ax.set_title("新幹線でつながった組：つながる前から相対的に減り続けていた")
ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "f33_shinkansen_event.png"); plt.close(fig)

# 6) 頑健性：距離の弾力性（左）と新幹線の係数（右）
fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.8), gridspec_kw=dict(width_ratios=[1, 1]))
r = rob.iloc[::-1]
cols = [C3 if "最小二乗" in s else C1 for s in r.setting]
for i, (bb, ss, cc) in enumerate(zip(r.b, r.se, cols)):
    axs[0].errorbar(bb, i, xerr=1.96 * ss, fmt="none", ecolor=cc, capsize=3)
axs[0].scatter(r.b, np.arange(len(r)), color=cols, zorder=3)
axs[0].set_yticks(np.arange(len(r))); axs[0].set_yticklabels(r.setting, fontsize=8.5)
axs[0].set_title("距離の弾力性（1989〜2025年をまとめた推定）", fontsize=10); axs[0].grid(alpha=.3)
q = rs.iloc[::-1].copy(); q["setting"] = q.setting.str.replace("（時期の違いだけで比べる）", "")
axs[1].errorbar(q.b, np.arange(len(q)), xerr=1.96 * q.se, fmt="o", color=C2, capsize=3)
axs[1].axvline(0, color="k", lw=.8)
axs[1].set_yticks(np.arange(len(q))); axs[1].set_yticklabels(q.setting, fontsize=8.5)
axs[1].set_title("新幹線網でつながった効果（PPML、ペアの固定効果つき）", fontsize=10); axs[1].grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "f33_robustness.png"); plt.close(fig)
print("ok")
