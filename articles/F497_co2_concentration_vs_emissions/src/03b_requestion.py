"""問い直し（結果を見てから足した）：綾里の年増加量の年ごとの上下は、エルニーニョ監視指数（NINO.3）でどれだけ説明できるか。
日本の排出量の動きと比べる。NINO.3 は同じ暦年の12か月平均と、前年7月〜当年6月の12か月平均の2通り。乱数は使わない。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
A = pd.read_csv(R / "annual.csv"); ry = A[A.station == "綾里"].set_index("year").growth.dropna()
N = pd.read_csv(ROOT / "data" / "nino3.csv")
E = pd.read_csv(ROOT / "data" / "emissions.csv").set_index("fy").co2_total_Mt
N["t"] = N.year * 12 + N.month - 1
cal = N.groupby("year").nino3.agg(["mean", "count"]); cal = cal[cal["count"] == 12]["mean"]
jj = {y: N[(N.t >= (y - 1) * 12 + 6) & (N.t <= y * 12 + 5)].nino3 for y in range(1950, 2026)}
jj = pd.Series({y: v.mean() for y, v in jj.items() if len(v) == 12})
D = pd.DataFrame({"growth": ry, "nino_cal": cal, "nino_jul_jun": jj, "em": E}).loc[1991:2024].dropna()
x = (D.index.values - 1991).astype(float)
out = {"n": int(len(D)), "years": [int(D.index.min()), int(D.index.max())]}
def fit(cols):
    X = sm.add_constant(np.column_stack([x] + [D[c].values for c in cols]))
    return sm.OLS(D.growth.values, X).fit()
base = fit([]); out["r2_trend"] = round(float(base.rsquared), 3)
res = []
for name, cols in [("trend", []), ("trend+nino_cal", ["nino_cal"]), ("trend+nino_jul_jun", ["nino_jul_jun"]), ("trend+em", ["em"])]:
    f = fit(cols)
    rec = {"model": name, "r2": round(float(f.rsquared), 3), "adj_r2": round(float(f.rsquared_adj), 3)}
    if cols:
        rec.update({"coef": round(float(f.params[2]), 4), "se": round(float(f.bse[2]), 4), "p": round(float(f.pvalues[2]), 4)})
    res.append(rec)
T = pd.DataFrame(res); T.to_csv(R / "requestion_models.csv", index=False)
out["models"] = res
f = fit(["nino_jul_jun"]); D["fit_nino"] = f.fittedvalues; D["fit_trend"] = base.fittedvalues
D.round(4).to_csv(R / "requestion_series.csv", index_label="year")
# 増加量の大きい年と小さい年
out["top_growth_years"] = [int(y) for y in D.growth.sort_values(ascending=False).index[:4]]
out["nino_jul_jun_of_top"] = [round(float(D.loc[y, "nino_jul_jun"]), 2) for y in out["top_growth_years"]]
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
