"""問い直し（結果を見てから足した）。
Q1：2003年に夏の不作付地の割合が高かった都道府県ほど、その後（2003→2025年）に田本地が大きく減ったのか。
Q2：2025年に主食用米の作付けが増えた分は、田んぼのどこから来たのか（2024→2025年）。
結果は results/requestion.json と results/requestion_*.csv。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
reg = pd.read_csv(R / "region_shares.csv")
s = pd.read_csv(ROOT / "data" / "summer_paddy_use_national.csv").set_index("year")
rice = pd.read_csv(ROOT / "data" / "rice_area.csv").set_index("year")
rng = np.random.default_rng(20261116)


def r(x, k=3):
    return round(float(x), k)


out = {}
pf = reg[reg.level == "都道府県"].pivot(index="name", columns="year", values=["paddy", "unplanted_pct", "nonrice_pct"])
pf = pf.sort_index()


def relation(y0, y1, drop=()):
    q = pf.drop(index=list(drop))
    chg = 100 * (q[("paddy", y1)] / q[("paddy", y0)] - 1)
    x = q[("unplanted_pct", y0)]
    sp = stats.spearmanr(x, chg)
    X = sm.add_constant(pd.DataFrame({"unplanted": x.values, "nonrice": q[("nonrice_pct", y0)].values}))
    fit = sm.OLS(chg.values, X).fit(cov_type="HC1")
    # ブートストラップ（都道府県を復元抽出、2,000回）で傾きの区間
    n = len(q); b = []
    xv, yv, zv = x.values, chg.values, q[("nonrice_pct", y0)].values
    for _ in range(2000):
        i = rng.integers(0, n, n)
        Xb = np.column_stack([np.ones(n), xv[i], zv[i]])
        coef, *_ = np.linalg.lstsq(Xb, yv[i], rcond=None)
        b.append(coef[1])
    lo, hi = np.percentile(b, [2.5, 97.5])
    return {"y0": y0, "y1": y1, "n": int(n), "spearman_rho": r(sp.statistic), "spearman_p": r(sp.pvalue, 5),
            "ols_slope_unplanted": r(fit.params.iloc[1]), "ols_slope_se_hc1": r(fit.bse.iloc[1]), "ols_slope_p": r(fit.pvalues.iloc[1], 5),
            "ols_slope_nonrice": r(fit.params.iloc[2]), "boot_ci_slope": [r(lo), r(hi)],
            "paddy_change_median_pct": r(chg.median(), 1)}


cases = {"main_2003_2025": relation(2003, 2025),
         "alt_2004_2025": relation(2004, 2025),
         "alt_2003_2024": relation(2003, 2024),
         "drop_hokkaido_okinawa": relation(2003, 2025, drop=("北海道", "沖縄")),
         "drop_tokyo_osaka_kanagawa": relation(2003, 2025, drop=("東京", "大阪", "神奈川"))}
out["q1"] = cases
pd.DataFrame(cases).T.to_csv(R / "requestion_q1.csv")

# Q2：2024→2025年
a, b = 2024, 2025
d = {
    "staple_change": float(rice.loc[b, "rice_staple_area"] - rice.loc[a, "rice_staple_area"]),
    "rice_field_change": float(s.loc[b, "rice_field"] - s.loc[a, "rice_field"]),
    "feed_rice_change": float(rice.loc[b, "feed_rice"] - rice.loc[a, "feed_rice"]),
    "wcs_change": float(rice.loc[b, "wcs"] - rice.loc[a, "wcs"]),
    "nonrice_change": float(s.loc[b, "nonrice_only"] - s.loc[a, "nonrice_only"]),
    "unplanted_change": float(s.loc[b, "unplanted"] - s.loc[a, "unplanted"]),
    "paddy_change": float(s.loc[b, "paddy"] - s.loc[a, "paddy"]),
}
d["other_nonstaple_change"] = d["rice_field_change"] - d["staple_change"] - d["feed_rice_change"] - d["wcs_change"]
d["within_rice_shift"] = d["staple_change"] - d["rice_field_change"]
d["within_rice_shift_share_pct"] = round(100 * d["within_rice_shift"] / d["staple_change"], 1)
d["feed_rice_share_of_staple_increase_pct"] = round(100 * -d["feed_rice_change"] / d["staple_change"], 1)
out["q2"] = d
pd.DataFrame([d]).to_csv(R / "requestion_q2.csv", index=False)

with open(R / "requestion.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
