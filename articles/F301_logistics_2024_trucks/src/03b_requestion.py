"""問い直し（結果を見てから足した）：
運んだ重さ（トン）は流れどおりだったのに、トンキロと1トンあたりの距離は下がった。距離が縮んだのは、長い距離を走る大きな車（最大積載量11トン以上）か。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
tr = pd.read_csv(ROOT / "data" / "truck_monthly.csv")
tr["ym"] = tr.year * 12 + tr.month - 1
POST = 2024 * 12 + 3; S = 2021 * 12 + 3
r4 = lambda x: round(float(x), 4)
groups = {"large": ["t11_16", "t16p"], "small_mid": ["lt3", "t3_6", "t6_11"]}
for g, cs in groups.items():
    tr[f"ton_{g}"] = tr[[f"ton_{c}" for c in cs]].sum(axis=1)
    tr[f"tonkm_{g}"] = tr[[f"tonkm_{c}" for c in cs]].sum(axis=1)
    tr[f"dist_{g}"] = tr[f"tonkm_{g}"] * 1000 / tr[f"ton_{g}"]

def its(col):
    d = tr[tr.ym >= S].set_index("ym").sort_index()
    y = np.log(d[col])
    X = pd.DataFrame(index=d.index)
    mon = (d.index % 12) + 1
    for m in range(2, 13):
        X[f"m{m}"] = (mon == m).astype(float)
    X["trend"] = (d.index - S) / 12.0
    X = sm.add_constant(X)
    pre = d.index < POST
    m = sm.OLS(y[pre], X[pre]).fit()
    dev = (y - m.predict(X))[~pre]
    return dict(col=col, mean_dev_pct=r4(100 * (np.exp(dev.mean()) - 1)), year1_dev_pct=r4(100 * (np.exp(dev[dev.index < POST + 12].mean()) - 1)),
                year2_dev_pct=r4(100 * (np.exp(dev[dev.index >= POST + 12].mean()) - 1)), resid_sd_pct=r4(100 * np.std(m.resid, ddof=X.shape[1])))
res = [its(c) for c in ["ton_large", "tonkm_large", "dist_large", "ton_small_mid", "tonkm_small_mid", "dist_small_mid"]]
pd.DataFrame(res).to_csv(RES / "requestion_by_size.csv", index=False)
# 年度ごとの平均距離と、トンキロに占める大型の割合
tr["fy"] = np.where(tr.month >= 4, tr.year, tr.year - 1)
f = tr[(tr.fy >= 2021) & (tr.fy <= 2025)].groupby("fy")[["ton_large", "tonkm_large", "ton_small_mid", "tonkm_small_mid", "tonkm_commercial", "ton_commercial"]].sum()
f["dist_large"] = f.tonkm_large * 1000 / f.ton_large
f["dist_small_mid"] = f.tonkm_small_mid * 1000 / f.ton_small_mid
f["dist_all"] = f.tonkm_commercial * 1000 / f.ton_commercial
f["large_share_tonkm"] = f.tonkm_large / f.tonkm_commercial
f = f.reset_index(); f.round(4).to_csv(RES / "requestion_fy.csv", index=False)
tr[["year", "month", "dist_large", "dist_small_mid"]].round(4).to_csv(RES / "requestion_monthly_dist.csv", index=False)
out = {"its": {r["col"]: r for r in res}, "fy": f.round(4).to_dict("records")}
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(pd.DataFrame(res).to_string()); print(f.round(3).to_string())
