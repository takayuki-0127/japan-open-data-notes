"""どこからどこへ：都道府県間の移動行列（1954〜2025年、1989年を除く）の重力モデルと、東京圏への集中"""
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib.pyplot as plt
from common import *

od = load_od()
YEARS = sorted(od)
P = list(range(1, 47))  # 沖縄県は1972年まで含まれないので、比べやすさのため除く
lat = np.radians([CAP[p][0] for p in P]); lon = np.radians([CAP[p][1] for p in P])
dlat = lat[:, None] - lat[None, :]; dlon = lon[:, None] - lon[None, :]
a = np.sin(dlat / 2) ** 2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2) ** 2
DIST = 2 * 6371 * np.arcsin(np.sqrt(a))
ii, jj = np.where(~np.eye(46, dtype=bool))
O = pd.get_dummies(pd.Series(ii), prefix="o", dtype=float).iloc[:, 1:]
D = pd.get_dummies(pd.Series(jj), prefix="d", dtype=float).iloc[:, 1:]
X = pd.concat([pd.Series(np.log(DIST[ii, jj]), name="ldist"), O, D], axis=1)
X = sm.add_constant(X)

rows, tk, hh = [], [], []
nonTA = [p - 1 for p in P if p not in TOKYO_AREA]
TA = [p - 1 for p in TOKYO_AREA]
for y in YEARS:
    M = od[y][:46, :46]
    yv = M[ii, jj]
    m = sm.GLM(yv, X, family=sm.families.Poisson()).fit(cov_type="HC1")
    b, se = m.params["ldist"], m.bse["ldist"]
    w = yv / yv.sum()
    rows.append({"year": y, "dist_elast": b, "se": se, "lo": b - 1.96 * se, "hi": b + 1.96 * se,
                 "mean_km": float((w * DIST[ii, jj]).sum()), "share_lt300": float(w[DIST[ii, jj] < 300].sum() * 100),
                 "total": yv.sum()})
    out = M.sum(axis=1)
    sh = M[nonTA][:, TA].sum(axis=1) / out[nonTA] * 100
    tk.append(pd.Series(sh, index=[PREF[p] for p in nonTA], name=y))
    S = M / out[:, None]; hh.append(pd.Series((S ** 2).sum(axis=1), index=[PREF[p - 1] for p in P], name=y))
G = pd.DataFrame(rows); G.to_csv(RES / "g2_gravity.csv", index=False, encoding="utf-8-sig")
TK = pd.DataFrame(tk); TK.index.name = "year"; TK.to_csv(RES / "g2_tokyo_share_by_origin.csv", encoding="utf-8-sig")
HH = pd.DataFrame(hh); HH.index.name = "year"; HH.to_csv(RES / "g2_hhi_by_origin.csv", encoding="utf-8-sig")
print(G[G.year.isin([1954, 1960, 1970, 1980, 1990, 2000, 2010, 2011, 2012, 2019, 2020, 2025])].round(3).to_string())
summ = pd.DataFrame({"tokyo_share_median": TK.median(axis=1), "hhi_median": HH.median(axis=1)})
summ.to_csv(RES / "g2_summary.csv", encoding="utf-8-sig")
print(summ.loc[[1954, 1960, 1970, 1980, 1990, 2000, 2011, 2019, 2021, 2025]].round(3))
pick = ["北海道", "青森県", "秋田県", "新潟県", "長野県", "静岡県", "愛知県", "大阪府", "広島県", "福岡県", "鹿児島県"]
print(TK.loc[[1954, 1970, 1990, 2011, 2025], pick].round(1).to_string())
chg = (TK.loc[2025] - TK.loc[1990]).sort_values()
print("1990→2025で上昇が大きい", chg.tail(5).round(1).to_dict(), "下降", chg.head(5).round(1).to_dict())
chg.to_csv(RES / "g2_tokyo_share_change_1990_2025.csv", encoding="utf-8-sig")

# 図1：距離の弾力性
fig, axes = plt.subplots(1, 2, figsize=(10, 3.9))
ax = axes[0]
ax.fill_between(G.year, G.lo, G.hi, color=LIGHT, alpha=.7, lw=0)
ax.plot(G.year, G.dist_elast, color=BLUE, lw=2)
ax.set_ylabel("距離の弾力性"); ax.set_title("距離が2倍になると移動はどれだけ減るか", loc="left", fontsize=11)
ax = axes[1]
ax.plot(G.year, G.share_lt300, color=ORANGE, lw=2, label="300km未満の移動の割合（%）")
ax.set_ylabel("%"); ax2 = ax.twinx(); ax2.plot(G.year, G.mean_km, color=GRAY, lw=1.6, label="平均移動距離（km、右軸）")
ax2.set_ylabel("km"); ax2.spines["top"].set_visible(False)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=8.5, loc="lower left")
ax.set_title("近くへの移動の割合と平均距離", loc="left", fontsize=11)
note(axes[0], SOURCE + "\n重力モデル（ポアソン回帰、出発地・到着地の固定効果）。帯は95%信頼区間。距離は都道府県庁所在地の間の直線距離。沖縄県と1989年を除く", -0.14)
fig.savefig(FIG / "g2_distance.png"); plt.close(fig)

# 図2：東京圏へ向かう割合（出発地別）
fig, ax = plt.subplots(figsize=(8.6, 4.4))
for c in TK.columns: ax.plot(TK.index, TK[c], color=LIGHT, lw=.7, alpha=.8)
ax.plot(TK.index, TK.median(axis=1), color=BLUE, lw=2.4, label="42道府県の中央値")
for c, col in [("北海道", PURPLE), ("大阪府", ORANGE), ("福岡県", GREEN), ("青森県", INK)]:
    ax.plot(TK.index, TK[c], color=col, lw=1.5, label=c)
ax.set_ylabel("転出者のうち東京圏へ向かった割合（%）"); ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper left")
ax.set_ylim(0, None); ax.set_title("ほかの道府県から出ていく人のうち、東京圏へ向かう割合", loc="left", fontsize=12)
note(ax, SOURCE + "\n東京圏＝埼玉・千葉・東京・神奈川。細い線は各道府県（沖縄県を除く42道府県）。1989年はデータなし", -0.13)
fig.savefig(FIG / "g2_tokyo_share.png"); plt.close(fig)

# 図3：1990→2025の変化（道府県別）
fig, ax = plt.subplots(figsize=(8.6, 6.4))
c2 = chg.sort_values()
cols = [ORANGE if v > 0 else BLUE for v in c2.values]
ax.barh(range(len(c2)), c2.values, color=cols)
ax.set_yticks(range(len(c2))); ax.set_yticklabels(c2.index, fontsize=7.5); ax.axvline(0, color=INK, lw=.7)
ax.set_xlabel("東京圏へ向かう割合の変化（%ポイント、1990年→2025年）")
ax.set_title("東京圏へ向かう割合は、どの道府県で増えたか", loc="left", fontsize=12)
note(ax, SOURCE, -0.12)
fig.savefig(FIG / "g2_tokyo_change.png"); plt.close(fig)
