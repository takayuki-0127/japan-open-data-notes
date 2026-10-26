"""図を作る（5枚）。"""
import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

from common import DATA, RES, FIG

FIG.mkdir(exist_ok=True)
m = pd.read_csv(DATA / "muni.csv").set_index("code")
P = pd.read_csv(DATA / "pairs.csv")
C = pd.read_csv(DATA / "centroids.csv").set_index("code")
E = json.load(open(RES / "estimates.json", encoding="utf-8"))
T = P[P.kind == "touch"].copy()
T["gap"] = (m.loc[T.code_a, "mw20"].values - m.loc[T.code_b, "mw20"].values)
T["gap"] = T.gap.abs()
T["dx"] = (m.loc[T.code_a, "dlog_mw"].values - m.loc[T.code_b, "dlog_mw"].values) * 100

# 1 地図
fig, ax = plt.subplots(figsize=(7.2, 7.6))
cc = C[C.lon > 127.5]
ax.scatter(cc.lon, cc.lat, s=2, color="#cccccc", zorder=1)
segs = [[C.loc[a, ["lon", "lat"]].values, C.loc[b, ["lon", "lat"]].values] for a, b in zip(T.code_a, T.code_b)]
lc = LineCollection(segs, cmap="viridis_r", linewidths=2.2, zorder=2)
lc.set_array(T.gap.values)
lc.set_clim(0, 120)
ax.add_collection(lc)
cb = fig.colorbar(lc, ax=ax, shrink=0.6)
cb.set_label("ペアの最低賃金の差（2020年度、円）")
ax.set_xlim(128.5, 146); ax.set_ylim(30.5, 45.7)
ax.set_aspect(1.2)
ax.set_title("県境をはさんで接する市区町村ペア（724組）")
ax.set_xticks([]); ax.set_yticks([])
fig.tight_layout(); fig.savefig(FIG / "f15_map.png"); plt.close()

# 2 分布
fig, axs = plt.subplots(1, 2, figsize=(9, 3.6))
axs[0].hist(T.gap, bins=np.arange(0, 180, 10), color="#4C72B0")
axs[0].set_xlabel("最低賃金の差（円、2020年度）"); axs[0].set_ylabel("ペア数")
axs[0].set_title(f"水準の差：中央値 {T.gap.median():.0f}円")
axs[1].hist(T.dx.abs(), bins=np.arange(0, 2.0, 0.1), color="#DD8452")
axs[1].set_xlabel("2015→20年度の上がり方の差（%ポイント）")
axs[1].set_title(f"上がり方の差：最大 {T.dx.abs().max():.1f}ポイント")
fig.suptitle("ペアの中の最低賃金の違い：水準は違うが、上がり方はほぼ同じ", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f15_gap_dist.png"); plt.close()

# 3 散布
a, b = m.loc[T.code_a], m.loc[T.code_b]
fr = lambda d, y: (d[f"emp_food_{y}"] + d[f"emp_retail_{y}"]).values
dy = (np.log(fr(a, 21) / fr(a, 16)) - np.log(fr(b, 21) / fr(b, 16))) * 100
ok = np.isfinite(dy)
x, y = T.dx.values[ok], dy[ok]
lo, hi = np.percentile(y, [1, 99]); y = np.clip(y, lo, hi)
fig, ax = plt.subplots(figsize=(6.4, 4.6))
ax.scatter(x, y, s=8, alpha=0.35, color="#4C72B0")
bins = pd.qcut(x, 10, duplicates="drop")
g = pd.DataFrame({"x": x, "y": y, "b": bins}).groupby("b", observed=True).mean()
ax.plot(g.x, g.y, "o-", color="#C44E52", label="10等分した平均")
bt = E["main"]["main_foodretail"]["beta"]
xx = np.linspace(x.min(), x.max(), 10)
ax.plot(xx, bt * xx, color="k", lw=1, label=f"ペアの中の傾き {bt:.2f}（区間 {E['main']['main_foodretail']['lo']:.1f}〜{E['main']['main_foodretail']['hi']:.1f}）")
ax.axhline(0, color="#999", lw=0.6); ax.axvline(0, color="#999", lw=0.6)
ax.set_xlabel("最低賃金の上がり方の差（%ポイント、A−B）")
ax.set_ylabel("飲食・小売の従業者の伸びの差（%、A−B）")
ax.set_title("ペアの中の差：2016→21年")
ax.legend(fontsize=8, loc="lower right")
fig.tight_layout(); fig.savefig(FIG / "f15_scatter.png"); plt.close()

# 4 産業別
lab = {"main_food": "宿泊・飲食", "main_retail": "卸売・小売", "main_foodretail": "飲食＋小売",
       "main_life": "生活関連・娯楽", "main_medical": "医療・福祉", "main_manuf": "製造業（対照）",
       "main_total": "全産業", "main_fr_minus_manuf": "飲食＋小売 − 製造業"}
r = pd.DataFrame(E["main"]).T.loc[list(lab)]
fig, ax = plt.subplots(figsize=(6.6, 4.2))
yy = np.arange(len(r))[::-1]
ax.errorbar(r.beta, yy, xerr=[r.beta - r.lo, r.hi - r.beta], fmt="o", color="#4C72B0", capsize=3)
ax.axvline(0, color="k", lw=0.8)
ax.set_yticks(yy); ax.set_yticklabels([lab[i] for i in r.index])
ax.set_xlabel("弾力性（最低賃金が1%多く上がると、従業者は何%変わるか）")
ax.set_title("産業別の推定（95%区間、県の組でクラスタ）")
fig.tight_layout(); fig.savefig(FIG / "f15_by_industry.png"); plt.close()

# 5 頑健性
R = pd.DataFrame(E["robust"]).T
fig, ax = plt.subplots(figsize=(6.8, 4.2))
yy = np.arange(len(R))[::-1]
ax.errorbar(R.beta, yy, xerr=[R.beta - R.lo, R.hi - R.beta], fmt="o", color="#DD8452", capsize=3)
ax.axvline(0, color="k", lw=0.8)
ax.axvspan(-0.3, 0, color="#55A868", alpha=0.25, label="0〜−0.3")
ax.set_yticks(yy); ax.set_yticklabels(R.index, fontsize=8.5)
ax.set_xlabel("弾力性（緑の帯：海外の研究でよく報告される大きさ）")
ax.set_title("頑健性（飲食＋小売の弾力性）")
ax.legend(fontsize=8, loc="lower right")
fig.tight_layout(); fig.savefig(FIG / "f15_robustness.png"); plt.close()
print("ok")
