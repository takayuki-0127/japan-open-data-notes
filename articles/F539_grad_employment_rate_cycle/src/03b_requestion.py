"""問い直し（結果を見てから足した）：1964〜1999年の卒業の関係（就職率＝a＋b×前年度の有効求人倍率）を
2000年以降に延ばすと、実際の就職率はどれだけ下回り、その差は縮んだのか。"""
import json, pathlib
import pandas as pd
import statsmodels.api as sm

BASE = pathlib.Path(__file__).resolve().parent.parent
RES = BASE / "results"
df = pd.read_csv(BASE / "data" / "panel.csv", index_col="grad_year").loc[1964:2025]
pre = df.loc[1964:1999]
X = sm.add_constant(pre[["yuko_fy_lag1"]])
r = sm.OLS(pre["univ_t"], X).fit()
pred = r.params["const"] + r.params["yuko_fy_lag1"] * df["yuko_fy_lag1"]
gap = (df["univ_t"] - pred).rename("actual_minus_pred")
out = pd.DataFrame({"univ_t": df["univ_t"], "yuko_fy_lag1": df["yuko_fy_lag1"], "pred_from_1964_1999": pred.round(3), "gap": gap.round(3)})
out.to_csv(RES / "requestion_gap.csv")
per = {}
for a, b in [(1964, 1999), (2000, 2009), (2010, 2019), (2020, 2025)]:
    per[f"{a}-{b}"] = round(float(gap.loc[a:b].mean()), 2)
res = {"pre_fit": {"const": round(float(r.params["const"]), 2), "b_per_0.1": round(float(r.params["yuko_fy_lag1"]) / 10, 3),
                   "r2": round(float(r.rsquared), 3), "n": int(r.nobs)},
       "mean_gap_by_period": per,
       "gap_2003": round(float(gap.loc[2003]), 1), "gap_2019": round(float(gap.loc[2019]), 1), "gap_2025": round(float(gap.loc[2025]), 1)}
# 2010年以降だけで直線を当てはめたときの、倍率がゼロのときの値ではなく、倍率1.2のときの就職率（両期間の比べ）
for a, b in [(1964, 1999), (2010, 2025)]:
    d = df.loc[a:b]
    rr = sm.OLS(d["univ_t"], sm.add_constant(d[["yuko_fy_lag1"]])).fit()
    res[f"at_1.2_{a}_{b}"] = round(float(rr.params["const"] + 1.2 * rr.params["yuko_fy_lag1"]), 1)
(RES / "requestion.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))
