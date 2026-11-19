"""問い直し（結果を見てから足した）：合併で市町村が減っても、もとの町村の公民館は残ったのか。
県ごとに log(公民館2024/2002) を log(市町村数2024/2002) に回帰し、傾き（弾力性）を見る。
傾き0＝市町村が減っても公民館はそのまま、傾き1＝市町村と同じ割合で減った。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

BASE = pathlib.Path(__file__).resolve().parent.parent
RES = BASE / "results"
SEED = 20261116
t = pd.read_csv(RES / "pref_changes.csv", index_col="pref")
x = np.log(t.muni_2024 / t.muni_2002); y = np.log(t.total_2024 / t.total_2002)
r = sm.OLS(y, sm.add_constant(x)).fit(cov_type="HC1")
rng = np.random.default_rng(SEED)
bs = []
xa, ya = x.to_numpy(), y.to_numpy()
for _ in range(2000):
    i = rng.integers(0, len(xa), len(xa))
    X = np.column_stack([np.ones(len(i)), xa[i]])
    bs.append(np.linalg.lstsq(X, ya[i], rcond=None)[0][1])
# 市町村数が変わらなかった県（東京）の参考と、1市町村あたりの公民館
t2 = t.copy()
t2["per_muni_2002"] = t2.total_2002 / t2.muni_2002
t2["per_muni_2024"] = t2.total_2024 / t2.muni_2024
t2[["region", "muni_2002", "muni_2024", "total_2002", "total_2024", "per_muni_2002", "per_muni_2024"]].round(3).to_csv(RES / "requestion_per_muni.csv")
out = {"slope": round(float(r.params.iloc[1]), 3), "slope_ci_hc1": [round(float(v), 3) for v in r.conf_int().iloc[1]],
       "slope_boot_ci": [round(float(np.quantile(bs, 0.025)), 3), round(float(np.quantile(bs, 0.975)), 3)],
       "intercept": round(float(r.params.iloc[0]), 3), "intercept_pct": round((np.exp(float(r.params.iloc[0])) - 1) * 100, 1),
       "r2": round(float(r.rsquared), 3), "n": int(r.nobs),
       "n_per_muni_up": int((t2.per_muni_2024 > t2.per_muni_2002).sum()),
       "median_per_muni_2002": round(float(t2.per_muni_2002.median()), 2), "median_per_muni_2024": round(float(t2.per_muni_2024.median()), 2)}
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=1))
