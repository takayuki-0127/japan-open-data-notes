"""04 図"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG, VNAMES

FIG.mkdir(exist_ok=True)
comb = pd.read_csv(RES / "nowcast_combined.csv")
acc = pd.read_csv(RES / "accuracy.csv")
rob = pd.read_csv(RES / "robustness.csv")
per = pd.read_csv(RES / "per_series.csv")
summ = json.load(open(RES / "summary.json"))
C = {"AR(1)": "#9aa0a6", "ブリッジ方程式": "#e8a33d", "MIDAS（20系列の平均）": "#3b7dd8", "DFM（F18）": "#c0392b"}

# 1 鉱工業生産の MIDAS の重み
fig, ax = plt.subplots(figsize=(7.5, 4.2))
cols = ["#cfe0f7", "#8fb6ea", "#4f8bd9", "#1f4e99"]
for v, c in zip(VNAMES, cols):
    w = summ["weights_iip"][v]
    ax.plot(range(len(w)), w, marker="o", color=c, lw=2, label=f"{v}末")
ax.set_xticks(range(6))
ax.set_xticklabels(["手に入る\n最新の月", "1か月前", "2か月前", "3か月前", "4か月前", "5か月前"])
ax.set_ylabel("重み（合計1）")
ax.set_title("MIDAS が鉱工業生産の各月に付けた重み（74四半期の平均）")
ax.legend(frameon=False)
ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "f90_weights.png"); plt.close()

# 2 時点ごとの RMSE
a = acc[acc.設定 == "基本"]
fig, ax = plt.subplots(figsize=(7.5, 4.2))
xx = np.arange(4); wdt = .2
for i, (lab, col) in enumerate([("AR(1)", "RMSE_AR"), ("ブリッジ方程式", "RMSE_ブリッジ"), ("MIDAS（20系列の平均）", "RMSE_MIDAS"), ("DFM（F18）", "RMSE_DFM")]):
    vals = a[col].values
    ax.bar(xx + (i - 1.5) * wdt, vals, wdt, label=lab, color=C[lab])
    for xi, vv in zip(xx, vals):
        ax.text(xi + (i - 1.5) * wdt, vv + .02, f"{vv:.2f}", ha="center", fontsize=7.5)
ax.set_xticks(xx); ax.set_xticklabels([v + "末" for v in VNAMES])
ax.set_ylabel("RMSE（前期比、%ポイント）")
ax.set_title("GDP 前期比のナウキャストの誤差（2008Q1〜2026Q2、74四半期）")
ax.set_ylim(0, 2.0)
ax.legend(frameon=False, ncol=4, fontsize=8, loc="upper center")
fig.tight_layout(); fig.savefig(FIG / "f90_rmse.png"); plt.close()

# 3 予測と実績（翌月末）
b = comb[comb.vint == "翌月"].copy()
b["qq"] = pd.PeriodIndex(b.q, freq="Q").to_timestamp(how="end")
fig, ax = plt.subplots(figsize=(8.5, 4.2))
ax.axhline(0, color="k", lw=.6)
ax.plot(b.qq, b.actual, color="k", lw=1.6, label="実績")
ax.plot(b.qq, b.almon6, color=C["MIDAS（20系列の平均）"], lw=1.3, label="MIDAS（20系列の平均）")
ax.plot(b.qq, b.dfm, color=C["DFM（F18）"], lw=1.1, ls="--", label="DFM（F18）")
ax.set_ylim(-9, 6)
ax.set_ylabel("実質 GDP 前期比（%）")
ax.set_title("翌月末（1次速報の直前）のナウキャストと実績")
ax.legend(frameon=False, fontsize=8.5, loc="lower left")
ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "f90_nowcast_vs_actual.png"); plt.close()

# 4 系列ごと（MIDAS ÷ AR）
pp = per.set_index("series")[VNAMES]
fig, ax = plt.subplots(figsize=(7.5, 7))
im = ax.imshow(pp.values, cmap="RdBu_r", vmin=0.5, vmax=1.5, aspect="auto")
ax.set_xticks(range(4)); ax.set_xticklabels([v + "末" for v in VNAMES])
ax.set_yticks(range(len(pp))); ax.set_yticklabels(pp.index, fontsize=8.5)
for i in range(pp.shape[0]):
    for j in range(4):
        ax.text(j, i, f"{pp.values[i, j]:.2f}", ha="center", va="center", fontsize=7.5)
ax.set_title("1系列だけの MIDAS の誤差 ÷ AR(1) の誤差（1未満が AR より良い）", fontsize=10)
fig.colorbar(im, ax=ax, shrink=.6)
fig.tight_layout(); fig.savefig(FIG / "f90_per_series.png"); plt.close()

# 5 頑健性
r = rob[rob.評価 == "全期間"].set_index("設定")
r2 = rob[rob.評価 == "コロナ期を除く"].set_index("設定")
labs = list(r.index)
fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), sharey=True)
for ax, d, t in [(axes[0], r, "全期間（74四半期）"), (axes[1], r2, "コロナ期を除く（68四半期）")]:
    y = np.arange(len(labs))
    ax.barh(y - .2, d.loc[labs, "2か月目"], .4, color="#8fb6ea", label="2か月目末")
    ax.barh(y + .2, d.loc[labs, "翌月"], .4, color="#1f4e99", label="翌月末")
    ax.axvline(1, color="k", lw=.8)
    ax.set_yticks(y); ax.set_yticklabels(labs, fontsize=8.5)
    ax.set_title(t, fontsize=10)
    ax.set_xlabel("RMSE ÷ AR(1) の RMSE")
    ax.set_xlim(0, 1.25)
axes[0].invert_yaxis()
axes[0].legend(frameon=False, fontsize=8.5, loc="lower right")
fig.suptitle("設定を変えたときの誤差（AR より小さいほど良い）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f90_robust.png"); plt.close()
print("ok")
