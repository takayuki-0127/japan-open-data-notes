"""実データの「誤差の構造」を調べる：二方向固定効果を除いた残差の大きさ・時系列の相関・県どうしの相関"""
import json
import numpy as np, pandas as pd
from common import RAW, DATA, RES, wide, demean2

p = pd.read_csv(RAW / "f01_panel.csv")[["code", "pref", "year", "emp_rate", "unemp_rate"]]
p.to_csv(DATA / "panel.csv", index=False)

out = {}
for col in ["emp_rate", "unemp_rate"]:
    for label, years in [("2008-2019", list(range(2008, 2020))), ("2008-2025", list(range(2008, 2026)))]:
        Y, prefs = wide(p, col, years)
        r = demean2(Y)
        sd = r.std(ddof=1)
        rho = (r[:, 1:] * r[:, :-1]).sum() / (r[:, :-1] ** 2).sum()
        C = np.corrcoef(r)
        cross = C[np.triu_indices_from(C, 1)].mean()
        # 県ごとの AR(1)
        rhos = [(ri[1:] * ri[:-1]).sum() / (ri[:-1] ** 2).sum() for ri in r]
        out[f"{col}|{label}"] = dict(resid_sd=round(float(sd), 4), ar1=round(float(rho), 3),
                                     ar1_pref_median=round(float(np.median(rhos)), 3),
                                     cross_corr_mean=round(float(cross), 3), n_pref=len(prefs), n_year=len(years))
        print(col, label, out[f"{col}|{label}"])

# F14（市町村の人口集中地区の密度の変化、2時点の差）
a = pd.read_csv(RAW / "f14_analysis.csv", dtype={"code5": str})
a = a[a["group"].isin(["作成", "未作成"])].copy()
for c in ["d_dens_2015", "d_dens_2020"]:
    lo, hi = a[c].quantile([0.01, 0.99])
    a[c + "_w"] = a[c].clip(lo, hi)
a[["code5", "group", "d_dens_2015_w", "d_dens_2020_w", "x_lpop"]].to_csv(DATA / "f14_cross.csv", index=False)
out["f14"] = dict(n=int(len(a)), n_treat=int((a.group == "作成").sum()),
                  sd_2020=round(float(a["d_dens_2020_w"].std()), 3), sd_2015=round(float(a["d_dens_2015_w"].std()), 3),
                  corr_2015_2020=round(float(a[["d_dens_2015_w", "d_dens_2020_w"]].corr().iloc[0, 1]), 3))
print(out["f14"])
json.dump(out, open(RES / "error_structure.json", "w"), ensure_ascii=False, indent=1)
