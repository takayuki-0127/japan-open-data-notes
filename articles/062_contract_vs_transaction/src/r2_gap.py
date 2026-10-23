"""成約価格（レインズ）と取引価格（登記＋アンケート）の差：同じ市区町村・同じ四半期・同じ条件で比べる"""
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib.pyplot as plt
from common import *
from r1_index import prep, controls

res, byyear, bytier, share = [], [], [], []
for kind in ["マンション", "戸建て"]:
    g = prep(kind)
    g = g[g.special == 0].copy()
    g["cell"] = g.muni + "_" + g.t.astype(str)
    # 市区町村の価格水準（期間全体の㎡単価中央値）で5分位
    unit = np.log(g.price / g.area)
    lvl = unit.groupby(g.muni).median()
    g["tier"] = g.muni.map(pd.qcut(lvl, 5, labels=["最も安い20%", "2", "3", "4", "最も高い20%"]))
    X = controls(g, kind).drop(columns=["special"])
    g["seiyaku"] = (g.src == "成約").astype(float)
    # 圏域別の差
    D = pd.get_dummies(g.region, dtype=float).mul(g.seiyaku, axis=0).add_prefix("gap_")
    Z = pd.concat([g[["y", "cell"]], X, D], axis=1)
    cols = ["y"] + list(X.columns) + list(D.columns)
    W = demean(Z, cols, "cell"); keep = [c for c in cols[1:] if W[c].abs().sum() > 0]
    m = sm.OLS(W.y, W[keep]).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(g.muni)[0]})
    for r in REGIONS:
        c = "gap_" + r; res.append({"kind": kind, "region": r, "gap": m.params[c], "se": m.bse[c]})
    # 全国の年別
    D2 = pd.get_dummies(g.year, dtype=float).mul(g.seiyaku, axis=0).add_prefix("gy_")
    D3 = pd.get_dummies(g.tier, dtype=float).mul(g.seiyaku, axis=0).add_prefix("gt_")
    for D_, lab, store in [(D2, "year", byyear), (D3, "tier", bytier)]:
        Z = pd.concat([g[["y", "cell"]], X, D_], axis=1); cols = ["y"] + list(X.columns) + list(D_.columns)
        W = demean(Z, cols, "cell"); keep = [c for c in cols[1:] if W[c].abs().sum() > 0]
        m2 = sm.OLS(W.y, W[keep]).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(g.muni)[0]})
        for c in D_.columns:
            store.append({"kind": kind, lab: c.split("_", 1)[1], "gap": m2.params[c], "se": m2.bse[c]})
    # 件数シェア
    s = g.groupby(["year", "src"]).size().unstack(); s["share_seiyaku"] = s["成約"] / s.sum(axis=1); s["kind"] = kind
    share.append(s.reset_index())
    # 比較に使えるセル（両方の情報があるセル）の割合
    both = g.groupby("cell").src.nunique().eq(2)
    print(kind, len(g), "両方あるセルの件数割合", round(g.cell.map(both).mean(), 3))

R = pd.DataFrame(res); Y = pd.DataFrame(byyear); T = pd.DataFrame(bytier); S_ = pd.concat(share)
for df_ in (R, Y, T):
    df_["pct"] = (np.exp(df_.gap) - 1) * 100; df_["lo"] = (np.exp(df_.gap - 1.96 * df_.se) - 1) * 100; df_["hi"] = (np.exp(df_.gap + 1.96 * df_.se) - 1) * 100
R.to_csv(RES / "r2_gap_region.csv", index=False, encoding="utf-8-sig"); Y.to_csv(RES / "r2_gap_year.csv", index=False, encoding="utf-8-sig")
T.to_csv(RES / "r2_gap_tier.csv", index=False, encoding="utf-8-sig"); S_.to_csv(RES / "r2_share.csv", index=False, encoding="utf-8-sig")
print(R.round(2)); print(Y.round(2)); print(T.round(2)); print(S_)

# 先行・遅行：四半期の前期比の相関（r1の指数から）
idx = pd.read_csv(RES / "r1_index.csv")
ll = []
for kind in ["マンション", "戸建て"]:
    for r in REGIONS:
        a = idx[(idx.kind == kind) & (idx.src == "取引") & (idx.region == r)].set_index("t")["b"].diff()
        b = idx[(idx.kind == kind) & (idx.src == "成約") & (idx.region == r)].set_index("t")["b"].diff()
        for k in (-1, 0, 1):
            ll.append({"kind": kind, "region": r, "lag": k, "corr": a.corr(b.shift(k))})
LL = pd.DataFrame(ll); LL.to_csv(RES / "r2_leadlag.csv", index=False, encoding="utf-8-sig")
print(LL.pivot_table(index=["kind", "region"], columns="lag", values="corr").round(2))

# 図1：圏域別の差
fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.8), sharey=True)
for ax, kind in zip(axes, ["マンション", "戸建て"]):
    s = R[R.kind == kind]
    for i, r in enumerate(REGIONS):
        v = s[s.region == r].iloc[0]
        ax.bar(i, v.pct, .6, color=RCOL[r]); ax.errorbar(i, v.pct, yerr=[[v.pct - v.lo], [v.hi - v.pct]], color=INK, lw=1, capsize=3)
        ax.text(i, v.hi + .4 if v.pct >= 0 else v.lo - 1.4, f"{v.pct:+.1f}%", ha="center", fontsize=9)
    ax.axhline(0, color=INK, lw=.6); ax.set_xticks(range(5)); ax.set_xticklabels(REGIONS, fontsize=9.5); ax.set_title(f"中古{kind}", loc="left")
axes[0].set_ylabel("成約価格 − 取引価格（%）")
fig.suptitle("同じ市区町村・同じ四半期・同じ条件なら、成約価格は取引価格より何%高いか", x=.02, y=1.05, ha="left", fontsize=12)
note(axes[0], SOURCE + "\n市区町村×四半期の固定効果、築年・面積・駅距離・構造などを調整。ひげは95%信頼区間", -0.13)
fig.savefig(FIG / "r2_gap_region.png"); plt.close(fig)

# 図2：価格水準の5分位別
fig, ax = plt.subplots(figsize=(8, 3.9))
tiers = ["最も安い20%", "2", "3", "4", "最も高い20%"]
for j, (kind, col) in enumerate([("マンション", BLUE), ("戸建て", ORANGE)]):
    s = T[T.kind == kind].set_index("tier").loc[tiers]
    x = np.arange(5) + (j - .5) * .36
    ax.bar(x, s.pct, .34, color=col, label=f"中古{kind}")
    ax.errorbar(x, s.pct, yerr=[s.pct - s.lo, s.hi - s.pct], fmt="none", color=INK, lw=1, capsize=2)
ax.axhline(0, color=INK, lw=.6); ax.set_xticks(range(5)); ax.set_xticklabels(["最も安い\n20%", "2", "3", "4", "最も高い\n20%"])
ax.set_xlabel("市区町村の価格水準（㎡単価の中央値で5等分）"); ax.set_ylabel("成約価格 − 取引価格（%）"); ax.legend(frameon=False)
ax.set_title("安い地域の戸建てほど、成約価格のほうが高く出る", loc="left")
note(ax, SOURCE, -0.26)
fig.savefig(FIG / "r2_gap_tier.png"); plt.close(fig)

# 図3：件数の内訳
fig, ax = plt.subplots(figsize=(7.6, 3.6))
for kind, col in [("マンション", BLUE), ("戸建て", ORANGE)]:
    s = S_[S_.kind == kind]; ax.plot(s.year, s.share_seiyaku * 100, "o-", color=col, lw=2, label=f"中古{kind}")
    for _, r_ in s.iterrows(): ax.text(r_.year, r_.share_seiyaku * 100 + 1.2, f"{r_.share_seiyaku * 100:.0f}", ha="center", fontsize=8.5, color=col)
ax.set_ylabel("成約価格情報の割合（%）"); ax.set_xticks(range(2021, 2026)); ax.legend(frameon=False)
ax.set_title("データに占める成約価格情報の割合（分析に使った件数）", loc="left")
note(ax, SOURCE, -0.16)
fig.savefig(FIG / "r2_share.png"); plt.close(fig)
