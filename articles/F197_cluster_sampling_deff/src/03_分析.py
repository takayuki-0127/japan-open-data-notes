"""03 分析：地区（クラスター）抽出の設計効果（DEFF）と級内相関（ICC）。

- 母集団：1,725市区町村（SSDSE-A 2026年版。避難指示区域が設定された福島県の12市町村と、前回の人口が0の町を除く）。
- 平均の推定は比推定（選んだ地区の合計÷選んだ市区町村の数）。拡大推定（地区の数で割り戻す）は比較用。
- 地区の作り方 4通り × 地区の大きさ m = 2, 3, 5, 10, 20（都道府県そのものは1通り）。
- 分散は式で厳密に計算し、シミュレーションは95%区間の当たり方の確認に使う。
"""
import json

import numpy as np
import pandas as pd

from common import (IND, IND_ORDER, MEAN_IND, RES, SEED, clusters, icc_anova, load,
                    var_cluster_mean, var_cluster_ratio, var_srs_mean)

KINDS = ["adjacent", "pref_random", "national_random"]
MS = [2, 3, 5, 10, 20]
NS = [60, 120, 240]
R_RANDOM = 40  # ランダムな地区分けは40通りの平均


def design_rows(df, kind, m, rng, year):
    reps = R_RANDOM if kind in ("pref_random", "national_random") else 1
    rows = []
    for r in range(reps):
        lab = clusters(df, kind, m, rng)
        M = lab.max() + 1
        mbar = len(df) / M
        for ind in IND_ORDER:
            y = df[ind].to_numpy()
            rho = icc_anova(y, lab)
            for n in NS:
                k = max(2, int(round(n / mbar)))
                n_exp = k * mbar
                vc = var_cluster_ratio(y, lab, k)
                ve = var_cluster_mean(y, lab, k)
                vs = var_srs_mean(y, n_exp)
                rows.append(dict(year=year, kind=kind, m=m if kind != "prefecture" else round(mbar, 1),
                                 rep=r, M=M, mbar=mbar, ind=ind, n=n, k=k, n_exp=n_exp, icc=rho,
                                 deff=vc / vs, deff_exp=ve / vs, kish=1 + (mbar - 1) * rho, se_srs=np.sqrt(vs), se_cluster=np.sqrt(vc),
                                 cv_cluster=np.sqrt(vc) / y.mean(), cv_srs=np.sqrt(vs) / y.mean()))
    return rows


def run_year(year, rng):
    df = load(year)
    rows = []
    for kind in KINDS:
        for m in MS:
            rows += design_rows(df, kind, m, rng, year)
    rows += design_rows(df, "prefecture", None, rng, year)
    return pd.DataFrame(rows)


rng = np.random.default_rng(SEED)
raw = pd.concat([run_year("y", rng), run_year("x", rng)], ignore_index=True)
raw.to_csv(RES / "design_raw.csv.gz", index=False)
grid = (raw.groupby(["year", "kind", "m", "ind", "n"], as_index=False)
        .agg(M=("M", "mean"), mbar=("mbar", "mean"), k=("k", "mean"), n_exp=("n_exp", "mean"),
             icc=("icc", "mean"), deff=("deff", "mean"), deff_exp=("deff_exp", "mean"), kish=("kish", "mean"),
             se_srs=("se_srs", "mean"), se_cluster=("se_cluster", "mean"),
             cv_cluster=("cv_cluster", "mean"), cv_srs=("cv_srs", "mean")))
grid["n_eff"] = grid["n_exp"] / grid["deff"]
grid.to_csv(RES / "design_grid.csv", index=False)

# 主な表：今の値・n=120
main = grid[(grid.year == "y") & (grid.n == 120)]
tab_icc = main[main.m.isin([5])].pivot_table(index="ind", columns="kind", values="icc").reindex(IND_ORDER)
pref_icc = main[main.kind == "prefecture"].set_index("ind")["icc"].reindex(IND_ORDER)
tab_icc["prefecture"] = pref_icc
tab_icc.round(4).to_csv(RES / "icc_m5.csv")
adj = main[main.kind == "adjacent"].pivot_table(index="ind", columns="m", values="deff").reindex(IND_ORDER)
adj["prefecture"] = main[main.kind == "prefecture"].set_index("ind")["deff"].reindex(IND_ORDER)
adj.round(3).to_csv(RES / "deff_adjacent_n120.csv")
neff = main[main.kind == "adjacent"].pivot_table(index="ind", columns="m", values="n_eff").reindex(IND_ORDER)
neff["prefecture"] = main[main.kind == "prefecture"].set_index("ind")["n_eff"].reindex(IND_ORDER)
neff.round(1).to_csv(RES / "neff_adjacent_n120.csv")

# 年の頑健性：前回の値（2021年版）との ICC の比較（隣どうし m=5）
yr = grid[(grid.kind == "adjacent") & (grid.m == 5) & (grid.n == 120)].pivot_table(
    index="ind", columns="year", values="icc").reindex(IND_ORDER)
yr.round(4).to_csv(RES / "icc_by_year_adjacent_m5.csv")

# 標本の大きさの頑健性：隣どうし m=5 の DEFF を n で比べる
nn = grid[(grid.year == "y") & (grid.kind == "adjacent") & (grid.m == 5)].pivot_table(
    index="ind", columns="n", values="deff").reindex(IND_ORDER)
nn.round(3).to_csv(RES / "deff_by_n_adjacent_m5.csv")

# ---------------------------------------------------------------- シミュレーション（95%区間）
df = load("y")
N = len(df)
SIM = 4000
sim_rows = []
for kind, m in [("adjacent", 5), ("adjacent", 10), ("prefecture", None), ("national_random", 5)]:
    lab = clusters(df, kind, m or 1, np.random.default_rng(SEED + 1))
    M = lab.max() + 1
    mbar = N / M
    k = max(2, int(round(120 / mbar)))
    idx_by = pd.Series(np.arange(N)).groupby(lab).apply(np.array).to_list()
    srng = np.random.default_rng(SEED + 2)
    for ind in IND_ORDER:
        y = df[ind].to_numpy(float)
        T = np.array([y[i].sum() for i in idx_by])
        cnt = np.array([len(i) for i in idx_by])
        truth = y.mean()
        est, se_n, se_c, est_exp = [], [], [], []
        for _ in range(SIM):
            pick = srng.choice(M, k, replace=False)
            ys = np.concatenate([y[idx_by[c]] for c in pick])
            n = len(ys)
            r = T[pick].sum() / cnt[pick].sum()
            est.append(r)
            est_exp.append(M / k * T[pick].sum() / N)
            se_n.append(np.sqrt(max(1 - n / N, 0) * ys.var(ddof=1) / n))
            d = T[pick] - r * cnt[pick]
            se_c.append(np.sqrt((1 - k / M) * d.var(ddof=1) / k / mbar ** 2))
        est, se_n, se_c, est_exp = map(np.array, (est, se_n, se_c, est_exp))
        sim_rows.append(dict(kind=kind, m=m if m else round(mbar, 1), k=k, ind=ind, truth=truth,
                             sd_sim=est.std(), sd_formula=np.sqrt(var_cluster_ratio(y, lab, k)),
                             sd_srs=np.sqrt(var_srs_mean(y, k * mbar)), sd_exp=est_exp.std(),
                             naive_se_mean=se_n.mean(), cluster_se_mean=se_c.mean(),
                             cover_naive=np.mean(np.abs(est - truth) <= 1.96 * se_n),
                             cover_cluster=np.mean(np.abs(est - truth) <= 1.96 * se_c)))
sim = pd.DataFrame(sim_rows)
sim.round(4).to_csv(RES / "simulation_n120.csv", index=False)

summ = {
    "N": int(N), "deff_exp_prefecture_n120": main[main.kind == "prefecture"].set_index("ind")["deff_exp"].round(2).to_dict(), "M_adjacent_m5": int(grid[(grid.kind == "adjacent") & (grid.m == 5)].M.iloc[0]),
    "icc_m5": tab_icc.round(4).to_dict(),
    "deff_adjacent_n120": adj.round(3).to_dict(),
    "neff_adjacent_n120": neff.round(1).to_dict(),
    "icc_by_year": yr.round(4).to_dict(),
    "deff_by_n": nn.round(3).to_dict(),
    "simulation": sim.round(4).to_dict(orient="records"),
}
(RES / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1, default=float))
pd.set_option("display.width", 200)
print(tab_icc.round(3)); print(adj.round(2)); print(neff.round(0)); print(yr.round(3)); print(nn.round(2))
print(sim.round(3).to_string())
