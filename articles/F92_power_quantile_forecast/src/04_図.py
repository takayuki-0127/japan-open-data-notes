"""04 図"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG, COLORS

FIG.mkdir(exist_ok=True)
p = pd.read_csv(RES / "pred_tokyo.csv", parse_dates=["date"])
ev = pd.read_csv(RES / "coverage_tokyo.csv")
se = pd.read_csv(RES / "coverage_by_season.csv")
fx = pd.read_csv(RES / "fixed_margin.csv")
M = {"conf": "点予測＋残差の分位点", "qr": "線形の分位点回帰", "lgbq": "LightGBM の分位点"}

# 図1 2025年夏の扇形（点予測＋残差の分位点）
g = p[(p.date >= "2025-07-01") & (p.date <= "2025-09-30")]
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.fill_between(g.date, g["conf_0.5"] / 1e3, g["conf_0.99"] / 1e3, color="#1a73e8", alpha=.15, label="99%の上限まで")
ax.fill_between(g.date, g["conf_0.5"] / 1e3, g["conf_0.95"] / 1e3, color="#1a73e8", alpha=.25, label="95%の上限まで")
ax.fill_between(g.date, g["conf_0.5"] / 1e3, g["conf_0.9"] / 1e3, color="#1a73e8", alpha=.35, label="90%の上限まで")
ax.plot(g.date, g["conf_0.5"] / 1e3, color="#1a73e8", lw=1.2, label="予測（中央）")
ax.plot(g.date, g.actual / 1e3, color="black", lw=1.2, label="実績")
out = g[g.actual > g["conf_0.95"]]
ax.scatter(out.date, out.actual / 1e3, color="#d93025", zorder=5, s=22, label=f"95%の上限を超えた日（{len(out)}日）")
ax.set_ylabel("翌日のピーク需要（GW）")
ax.set_title("2025年夏（7〜9月）の東京エリア：翌日のピーク需要の予測と上側の幅")
ax.legend(ncol=3, fontsize=8.5, loc="lower center")
ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "fig1_fan_2025summer.png"); plt.close()

# 図2 名目の水準と実際のカバー率
fig, ax = plt.subplots(figsize=(6.4, 5.4))
ax.plot([0.5, 1], [50, 100], color="gray", ls="--", lw=1, label="ちょうど名目どおり")
for lab, gg in ev.groupby("方法", sort=False):
    ax.plot(gg.tau, gg["カバー率(%)"], marker="o", color=COLORS[lab], label=lab)
ax.set_xlabel("狙った水準（分位点）"); ax.set_ylabel("実績が上限以下に収まった割合（%）")
ax.set_xlim(.48, 1.0); ax.set_ylim(48, 100)
ax.set_title("狙った水準どおりに収まったか（東京・2020年度〜2026年度上期、2,374日）", fontsize=10)
ax.legend(fontsize=9); ax.grid(alpha=.3)
ax2 = ax.inset_axes([.52, .1, .44, .38])
for lab, gg in ev.groupby("方法", sort=False):
    gg = gg[gg.tau >= .9]
    ax2.plot(gg.tau, gg["カバー率(%)"], marker="o", color=COLORS[lab])
ax2.plot([.9, .99], [90, 99], color="gray", ls="--", lw=1)
ax2.set_title("90%以上を拡大", fontsize=8); ax2.tick_params(labelsize=7); ax2.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "fig2_coverage.png"); plt.close()

# 図3 季節別のカバー率（95%と99%）
seasons = ["夏（7〜9月）", "冬（12〜2月）", "その他"]
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), sharey=True)
for ax, t in zip(axes, (0.95, 0.99)):
    w = .26
    for i, lab in enumerate(M.values()):
        v = [se[(se.季節 == s) & (se.方法 == lab) & (np.isclose(se.tau, t))]["カバー率(%)"].iloc[0] for s in seasons]
        b = ax.bar(np.arange(3) + (i - 1) * w, v, w, color=COLORS[lab], label=lab)
        ax.bar_label(b, fmt="%.0f", fontsize=8)
    ax.axhline(t * 100, color="black", ls="--", lw=1)
    ax.set_xticks(range(3), seasons); ax.set_ylim(80, 101)
    ax.set_title(f"{int(t*100)}%の上限（点線が狙い）")
    ax.grid(axis="y", alpha=.3)
axes[0].set_ylabel("収まった割合（%）"); axes[0].legend(fontsize=8.5, loc="lower left")
fig.suptitle("季節で分けると、夏と冬は狙いより外れやすい", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig3_season.png"); plt.close()

# 図4 点予測からの上乗せ（%）とカバー率：固定の上乗せとの比較（横軸はすべて同じ点予測を基準にする）
TT = [0.8, 0.9, 0.95, 0.975, 0.99]
rows = []
for k, lab in M.items():
    for t in TT:
        rows.append({"方法": lab, "tau": t, "点予測からの上乗せ(%)": 100 * ((p[f"{k}_{t}"] - p.point) / p.point).mean(),
                     "カバー率(%)": 100 * (p.actual <= p[f"{k}_{t}"]).mean()})
for m in (3, 5, 8):
    rows.append({"方法": "固定の上乗せ", "tau": None, "点予測からの上乗せ(%)": m, "カバー率(%)": 100 * (p.actual <= p[f"fixed{m}"]).mean()})
mg = pd.DataFrame(rows)
mg.to_csv(RES / "margin_vs_point.csv", index=False)
fig, ax = plt.subplots(figsize=(7, 5))
for lab, gg in mg.groupby("方法", sort=False):
    if lab == "固定の上乗せ":
        ax.plot(gg["点予測からの上乗せ(%)"], gg["カバー率(%)"], marker="s", color=COLORS[lab], label="点予測に一律3・5・8%を足す")
        continue
    ax.plot(gg["点予測からの上乗せ(%)"], gg["カバー率(%)"], marker="o", color=COLORS[lab], label=lab)
    for _, r in gg.iterrows():
        ax.annotate(f"{r.tau:g}", (r["点予測からの上乗せ(%)"], r["カバー率(%)"]), fontsize=7, xytext=(3, -9), textcoords="offset points")
ax.set_xlabel("点予測（LightGBM）からの上乗せ（%、平均）"); ax.set_ylabel("実績が上限以下に収まった割合（%）")
ax.set_title("同じだけ上乗せしたとき、どれだけ収まるか", fontsize=11)
ax.legend(fontsize=8.5); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "fig4_margin_vs_coverage.png"); plt.close()

# 図5 頑健性
rb = pd.read_csv(RES / "robustness.csv")
sets = list(dict.fromkeys(rb.設定))
fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
for ax, t in zip(axes, (95, 99)):
    for i, lab in enumerate(M.values()):
        gg = rb[rb.方法 == lab].set_index("設定").reindex(sets)
        ax.scatter(gg[f"{t}%カバー率"], np.arange(len(sets)) + (i - 1) * .2, color=COLORS[lab], label=lab, s=30)
    ax.axvline(t, color="black", ls="--", lw=1)
    ax.set_title(f"{t}%の上限：収まった割合（%）"); ax.grid(alpha=.3)
axes[0].set_yticks(range(len(sets)), sets); axes[0].invert_yaxis()
axes[0].legend(fontsize=8, loc="lower left")
fig.suptitle("設定を変えたときのカバー率（点線が狙い）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig5_robustness.png"); plt.close()
print("ok")
