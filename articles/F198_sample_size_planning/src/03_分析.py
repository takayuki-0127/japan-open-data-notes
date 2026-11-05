"""03 分析：必要な標本の大きさの計算と、公表されている標本の大きさ・標準誤差との比較。"""
import json

import numpy as np
import pandas as pd

from common import (DATA, RES, SEED, LFS_POP15, LFS_LABOR, LFS_UNEMP, LFS_N_MONTH, Z95, Z80,
                    n_margin, n_cv, n_change, srs_se_total)

out = {}

# ---- A. 教科書の式：割合を ±e で推定するのに何人要るか
P = [0.5, 0.3, 0.1, 0.05, 0.025, 0.01]
E = [0.01, 0.02, 0.03, 0.05]
rows = []
for p in P:
    r = {"p": p}
    for e in E:
        r[f"abs_pm{int(e*100)}pt"] = n_margin(p, e)
    for cv in (0.05, 0.10, 0.20):
        r[f"rel_cv{int(cv*100)}"] = n_cv(p, cv)
    rows.append(r)
A = pd.DataFrame(rows)
A.round(0).to_csv(RES / "A_required_n_proportion.csv", index=False)
out["n_p50_pm1"] = n_margin(0.5, 0.01)
out["n_p50_pm3"] = n_margin(0.5, 0.03)
out["n_p50_pm5"] = n_margin(0.5, 0.05)
out["n_p01_pm1"] = n_margin(0.01, 0.01)
out["n_p025_cv5"] = n_cv(0.025, 0.05)

# ---- B. 労働力調査：公表の標準誤差と、同じ人数の単純無作為の標準誤差を比べる（設計効果）
se = pd.read_csv(DATA / "lfs_se_by_size.csv")
N = LFS_POP15 * 1e4
n_m = LFS_N_MONTH
se["srs_monthly_10k"] = srs_se_total(N, se.size_10k * 1e4, n_m) / 1e4
se["deff_monthly"] = (se.monthly_se_10k / se.srs_monthly_10k) ** 2
# 年平均：公表の標準誤差から「単純無作為なら何人分に当たるか」（有効標本数）を逆算
p = se.size_10k * 1e4 / N
se["neff_annual"] = p * (1 - p) * N**2 / (se.annual_se_10k * 1e4) ** 2
se["neff_monthly"] = p * (1 - p) * N**2 / (se.monthly_se_10k * 1e4) ** 2
se["annual_to_monthly_var_ratio"] = (se.monthly_se_10k / se.annual_se_10k) ** 2
se.round(3).to_csv(RES / "B_lfs_deff_by_size.csv", index=False)
out["lfs_deff_monthly_range"] = [float(se.deff_monthly.min()), float(se.deff_monthly.max())]
out["lfs_deff_monthly_median"] = float(se.deff_monthly.median())
out["lfs_neff_monthly_median"] = float(se.neff_monthly.median())
out["lfs_neff_annual_median"] = float(se.neff_annual.median())
out["lfs_var_ratio_median"] = float(se.annual_to_monthly_var_ratio.median())

# 主要項目（年平均）でも同じ逆算
mi = pd.read_csv(DATA / "lfs_main_items_2025.csv")
p = mi.annual_2025_10k * 1e4 / N
mi["neff_annual"] = p * (1 - p) * N**2 / (mi.annual_se_10k * 1e4) ** 2
# 標準誤差は1万人単位で丸められているので、±0.5万人の幅も出しておく
mi["neff_if_se_plus05"] = p * (1 - p) * N**2 / ((mi.annual_se_10k + 0.5) * 1e4) ** 2
mi["neff_if_se_minus05"] = p * (1 - p) * N**2 / ((mi.annual_se_10k - 0.5) * 1e4) ** 2
out["main_neff_max_item"] = mi.loc[mi.neff_annual.idxmax(), "item"]
out["main_neff_min_item"] = mi.loc[mi.neff_annual.idxmin(), "item"]
out["main_neff_ratio_point"] = float(mi.neff_annual.max() / mi.neff_annual.min())
out["main_neff_ratio_conservative"] = float(mi.loc[mi.neff_annual.idxmax(), "neff_if_se_plus05"] / mi.loc[mi.neff_annual.idxmin(), "neff_if_se_minus05"])
mi.round(0).to_csv(RES / "B_lfs_main_items_neff.csv", index=False)

# ---- C. 失業率の「先月から何ポイント変わったか」を見分けるには
u = LFS_UNEMP / LFS_LABOR
nL = LFS_N_MONTH * LFS_LABOR / LFS_POP15            # 毎月の標本のうち労働力人口（約6.4万人）
# 公表：完全失業者 176万人の月次標準誤差を、大きさ別の表から対数で内挿
lx, ly = np.log(se.size_10k[::-1]), np.log(se.monthly_se_10k[::-1])
se_unemp_m = float(np.exp(np.interp(np.log(LFS_UNEMP), lx, ly)))   # 万人
se_rate_pub = se_unemp_m / LFS_LABOR                                 # 失業率の標準誤差（労働力人口の誤差は無視）
se_rate_srs = np.sqrt(u * (1 - u) / nL)
deff_u = (se_rate_pub / se_rate_srs) ** 2
out.update(u=u, nL=nL, se_unemp_month_10k=se_unemp_m, se_rate_pub_pt=se_rate_pub * 100,
           se_rate_srs_pt=se_rate_srs * 100, deff_unemp=deff_u)
rows = []
for rho in (0.0, 0.25, 0.5):
    mdc = (Z95 + Z80) * se_rate_pub * np.sqrt(2 * (1 - rho))
    rows.append({"rho": rho, "mdc_pt": mdc * 100,
                 "margin95_diff_pt": Z95 * se_rate_pub * np.sqrt(2 * (1 - rho)) * 100,
                 "n_needed_d01": n_change(u, 0.001, rho, deff_u),
                 "n_needed_d02": n_change(u, 0.002, rho, deff_u),
                 "n_needed_d03": n_change(u, 0.003, rho, deff_u)})
C = pd.DataFrame(rows)
C.round(3).to_csv(RES / "C_unemployment_change.csv", index=False)
out["C"] = C.round(4).to_dict("records")
# 標本の大きさと見分けられる変化（曲線用）
ns = np.logspace(3.5, 6.5, 61)
curve = pd.DataFrame({"n_labor": ns})
for rho in (0.0, 0.5):
    curve[f"mdc_pt_rho{rho}"] = (Z95 + Z80) * np.sqrt(deff_u * 2 * (1 - rho) * u * (1 - u) / ns) * 100
curve.to_csv(RES / "C_mdc_curve.csv", index=False)

# ---- D. 区分の数（全国／11地域／47都道府県）と必要な総数
rows = []
for D in (1, 11, 47):
    for e in (0.01, 0.02, 0.03, 0.05):
        for deff in (1.0, 1.5, 2.0):
            rows.append({"domains": D, "margin_pt": e * 100, "deff": deff,
                         "n_total_p50": D * n_margin(0.5, e, deff),
                         "n_total_p10": D * n_margin(0.1, e, deff)})
Dt = pd.DataFrame(rows)
Dt.round(0).to_csv(RES / "D_domains_total_n.csv", index=False)

# 実際の標本の大きさ：仮に47に等分したときの1区分あたりの人数と、p=0.5・p=0.1 の95%の誤差の幅
sv = pd.read_csv(DATA / "survey_designs.csv")
sv["n_use"] = sv.persons_or_units.fillna(sv.households)
rows = []
for _, r in sv.iterrows():
    for D in (1, 11, 47):
        for deff in (1.0, 1.5, 2.0):
            nd = r.n_use / D
            rows.append({"statistic": r.statistic, "n": r.n_use, "domains": D, "deff": deff, "n_per_domain": nd,
                         "margin_p50_pt": Z95 * np.sqrt(deff * 0.25 / nd) * 100,
                         "margin_p10_pt": Z95 * np.sqrt(deff * 0.09 / nd) * 100})
S = pd.DataFrame(rows)
S.round(3).to_csv(RES / "D_survey_margins.csv", index=False)

# 地域別：同じ大きさの推定値でも、地域の人口が小さいほど標準誤差率は小さい（その地域の中での割合が大きいため）
reg = pd.read_csv(DATA / "lfs_regional_se_annual.csv").set_index("size_10k")
out["regional_se_100_range"] = [float(reg.loc[100].min()), float(reg.loc[100].max())]
out["regional_se_10_range"] = [float(reg.loc[10].min()), float(reg.loc[10].max())]

# ---- E. 式どおりの人数で、狙った精度が出るか（シミュレーション）
rng = np.random.default_rng(SEED)
R = 20000
rows = []
for p, target in ((0.5, ("abs", 0.03)), (0.1, ("abs", 0.02)), (0.025, ("cv", 0.10)), (0.01, ("abs", 0.01)), (0.01, ("cv", 0.20))):
    kind, val = target
    n = int(np.ceil(n_margin(p, val) if kind == "abs" else n_cv(p, val)))
    for nn, lab in ((n, "式の人数"), (max(50, n // 4), "式の1/4")):
        x = rng.binomial(nn, p, R) / nn
        half = Z95 * np.sqrt(x * (1 - x) / nn)
        cover = np.mean((x - half <= p) & (p <= x + half))
        within = np.mean(np.abs(x - p) <= (val if kind == "abs" else val * Z95 * p))
        rows.append({"p": p, "target": f"{kind}{val}", "n": nn, "label": lab,
                     "achieved_cv": float(np.std(x) / p), "share_within_target": float(within),
                     "wald_coverage": float(cover), "share_zero": float(np.mean(x == 0))})
E5 = pd.DataFrame(rows)
E5.round(4).to_csv(RES / "E_simulation.csv", index=False)
out["E"] = E5.round(4).to_dict("records")

# 人口の大きさの仮定を ±5% 動かしたときの設計効果
sens = []
for f in (0.95, 1.0, 1.05):
    Nn = N * f
    d = (se.monthly_se_10k / (srs_se_total(Nn, se.size_10k * 1e4, n_m) / 1e4)) ** 2
    sens.append({"pop_factor": f, "deff_min": float(d.min()), "deff_max": float(d.max())})
for nm in (90_000, 100_000, 110_000):
    d = (se.monthly_se_10k / (srs_se_total(N, se.size_10k * 1e4, nm) / 1e4)) ** 2
    sens.append({"n_month": nm, "deff_min": float(d.min()), "deff_max": float(d.max())})
out["deff_sensitivity"] = sens

json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: v for k, v in out.items() if k not in ("E",)}, ensure_ascii=False, indent=1, default=float))
print(se[["size_10k", "monthly_se_10k", "srs_monthly_10k", "deff_monthly", "neff_monthly", "neff_annual", "annual_to_monthly_var_ratio"]].round(2))
print(mi[["item", "annual_2025_10k", "neff_annual"]])
print(E5.round(3))
