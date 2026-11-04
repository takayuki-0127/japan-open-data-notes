"""03 分析：層の作り方・配分・標本の大きさで、合計の推定の精度がどれだけ変わるか。

分散は層別単純無作為抽出の式で厳密に計算する（乱数に頼らない）。
乱数のシミュレーション（5,000回）は、式の確認と、95%区間が本当に95%当たるかの確認に使う。
推定量はどれも「層ごとの平均×層の数」の単純な拡大推定（比推定などは使わない）。
"""
import json

import numpy as np
import pandas as pd

from common import (RES, SEED, Y, Y_ORDER, allocate, load, strat_sd, strata_cumsqrtf,
                    strata_quantile, strata_region, var_srs, var_total)

df = load()
N = len(df)
xpop = df["x_pop"].to_numpy(float)
pref = df["pref"].to_numpy(int)
yv = {k: df[f"y_{k}"].to_numpy(float) for k in Y_ORDER}
xv = {k: df[f"x_{k}"].to_numpy(float) for k in Y_ORDER}


def make_strata(kind, H):
    if kind == "cumsqrtf":
        return strata_cumsqrtf(xpop, H)
    if kind == "quantile":
        return strata_quantile(xpop, H)
    if kind == "region":
        return strata_region(pref)
    if kind == "region_size":  # 8地方×前回の人口の大小2（中央値で分ける）
        big = (xpop > np.median(xpop)).astype(int)
        return strata_region(pref) * 2 + big
    raise ValueError(kind)


def designs(h, n, k):
    """1つの指標 k について、配分の違う設計を返す（名前 → 各層の標本数）。"""
    out = {
        "prop": allocate(h, n, "prop"),
        "neyman_oracle": allocate(h, n, "neyman", strat_sd(yv[k], h)),
        "neyman_prior": allocate(h, n, "neyman", strat_sd(xv[k], h)),
        "neyman_pop": allocate(h, n, "neyman", strat_sd(xpop, h)),
        "equal": allocate(h, n, "equal"),
    }
    return out


def cv(v, k):
    tot = yv[k].sum()
    return float(np.sqrt(v) / tot * 100)


rows = []
# ---------------------------------------------------------------- A. 主な比較（累積√f・5層・n=100）＋ B. 層の数 ＋ C. 標本の大きさ ＋ D. 層の作り方
grid = []
for skind in ["cumsqrtf", "quantile"]:
    for H in [2, 3, 4, 5, 6, 8, 10]:
        for n in [50, 100, 200, 400]:
            grid.append((skind, H, n))
for n in [25, 50, 100, 200, 400, 800]:
    grid.append(("cumsqrtf", 5, n))
for skind in ["region", "region_size"]:
    for n in [50, 100, 200, 400]:
        grid.append((skind, None, n))
grid = list(dict.fromkeys(grid))
for skind, H, n in grid:
    h = make_strata(skind, H if H else 0)
    Hn = h.max() + 1
    for k in Y_ORDER:
        vs = var_srs(yv[k], n)
        rows.append(dict(strata=skind, H=Hn, n=n, y=k, alloc="srs", var=vs, cv=cv(vs, k), eff=1.0))
        for name, nh in designs(h, n, k).items():
            v = var_total(yv[k], h, nh)
            rows.append(dict(strata=skind, H=Hn, n=n, y=k, alloc=name, var=v, cv=cv(v, k), eff=vs / v,
                             takeall=int(np.sum(nh == np.bincount(h))), nh="/".join(map(str, nh))))
tab = pd.DataFrame(rows)
tab.to_csv(RES / "precision_grid.csv", index=False)

main = tab[(tab.strata == "cumsqrtf") & (tab.H == 5) & (tab.n == 100)]
pv = main.pivot(index="y", columns="alloc", values="eff").loc[Y_ORDER]
pc = main.pivot(index="y", columns="alloc", values="cv").loc[Y_ORDER]
pv.round(2).to_csv(RES / "main_efficiency_H5_n100.csv")
pc.round(2).to_csv(RES / "main_cv_H5_n100.csv")
print("効率（SRS の分散 ÷ 設計の分散）H=5, n=100, 累積√f")
print(pv.round(2))
print("CV%")
print(pc.round(2))

# 層の境目と各層の件数
h5 = make_strata("cumsqrtf", 5)
bnd = pd.DataFrame({"層": range(5), "件数": np.bincount(h5),
                    "前回人口の最小": [int(xpop[h5 == k].min()) for k in range(5)],
                    "前回人口の最大": [int(xpop[h5 == k].max()) for k in range(5)],
                    "世帯数の合計に占める割合%": [round(yv["households"][h5 == k].sum() / yv["households"].sum() * 100, 1) for k in range(5)],
                    "農家数の合計に占める割合%": [round(yv["farms"][h5 == k].sum() / yv["farms"].sum() * 100, 1) for k in range(5)]})
for name, nh in designs(h5, 100, "households").items():
    bnd[f"n_{name}(世帯)"] = nh
bnd["n_neyman_prior(農家)"] = designs(h5, 100, "farms")["neyman_prior"]
bnd.to_csv(RES / "strata_H5.csv", index=False)
print(bnd.to_string())

# ---------------------------------------------------------------- E. 多目的の調査：ある指標に合わせた配分を、ほかの指標に使うと
cross = []
for a in Y_ORDER:
    nh = allocate(h5, 100, "neyman", strat_sd(xv[a], h5))
    for k in Y_ORDER:
        cross.append(dict(alloc_for=a, y=k, eff=var_srs(yv[k], 100) / var_total(yv[k], h5, nh)))
cross = pd.DataFrame(cross).pivot(index="alloc_for", columns="y", values="eff").loc[Y_ORDER, Y_ORDER]
cross.round(2).to_csv(RES / "cross_allocation_H5_n100.csv")
print("行の指標に合わせた配分 → 列の指標の効率")
print(cross.round(2))

# ---------------------------------------------------------------- F. シミュレーション（n=100、5,000回）
rng = np.random.default_rng(SEED)
R = 5000
sim = []


def draw_strat(h, nh, R):
    """各層から nh 件を非復元で選んだ添字（R×n）。"""
    idx_all = []
    for k in range(h.max() + 1):
        members = np.flatnonzero(h == k)
        keys = rng.random((R, len(members)))
        pick = np.argpartition(keys, nh[k] - 1, axis=1)[:, : nh[k]] if nh[k] < len(members) else np.tile(np.arange(len(members)), (R, 1))
        idx_all.append(members[pick])
    return idx_all


for k in ["households", "employees", "births", "farms", "aging_mean"]:
    y = yv[k]
    T = y.sum()
    plans = {"srs": (np.zeros(N, int), np.array([100]))}
    for name, nh in designs(h5, 100, k).items():
        if name in ("prop", "neyman_prior", "neyman_pop"):
            plans[name] = (h5, nh)
    for name, (h, nh) in plans.items():
        groups = draw_strat(h, nh, R)
        est = np.zeros(R)
        vhat = np.zeros(R)
        for kk, g in enumerate(groups):
            Nk = (h == kk).sum()
            ys = y[g]
            est += Nk * ys.mean(axis=1)
            if nh[kk] < Nk:
                vhat += Nk**2 * (1 - nh[kk] / Nk) * ys.var(axis=1, ddof=1) / nh[kk]
        se = np.sqrt(vhat)
        cover = np.mean(np.abs(est - T) <= 1.96 * se)
        under = np.mean(est < T)
        v_formula = var_srs(y, 100) if name == "srs" else var_total(y, h, nh)
        sim.append(dict(y=k, alloc=name, cv_sim=float(est.std() / T * 100), cv_formula=float(np.sqrt(v_formula) / T * 100),
                        bias_pct=float((est.mean() - T) / T * 100), coverage95=float(cover), share_below=float(under),
                        median_ratio=float(np.median(est) / T)))
        if k == "households":
            np.save(RES / f"sim_households_{name}.npy", est / T)
sim = pd.DataFrame(sim)
sim.round(4).to_csv(RES / "simulation_n100.csv", index=False)
print(sim.round(3).to_string())

# ---------------------------------------------------------------- まとめ
summ = {
    "N": N,
    "H5_bounds": bnd[["前回人口の最小", "前回人口の最大", "件数"]].to_dict("records"),
    "main_eff": pv.round(3).to_dict(),
    "main_cv": pc.round(3).to_dict(),
}
json.dump(summ, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
