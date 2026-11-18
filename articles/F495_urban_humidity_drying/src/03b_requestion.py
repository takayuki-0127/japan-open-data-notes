"""問い直し（結果を見てから足した）：乾き方は一直線か。区分の平均の相対湿度と、大都市−15地点の差に、
折れ線（ある年で傾きが変わる直線）を当て、折れる年を1975〜2015年から残差の二乗和が最小になる年に決める。乱数は使わない。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
Y = pd.read_csv(R / "yearly_group_mean.csv")
Y["gap"] = Y.rh_city - Y.rh_rural
x = Y.year.values.astype(float)


def hinge(y, k):
    X = np.column_stack([np.ones_like(x), x - 1961, np.maximum(x - k, 0)])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    sse = float(((y - X @ b) ** 2).sum())
    return b, sse


def line_sse(y):
    X = np.column_stack([np.ones_like(x), x - 1961])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return float(((y - X @ b) ** 2).sum()), b


out = {}; fits = []
for col in ["rh_city", "rh_rural", "gap"]:
    y = Y[col].values
    best = min(((k, *hinge(y, k)) for k in range(1975, 2016)), key=lambda t: (t[2], t[0]))
    k, b, sse = best
    sse1, b1 = line_sse(y)
    n = len(y)
    bic_h = n * np.log(sse / n) + 4 * np.log(n)  # 折れる年も1つの母数として数える
    bic_l = n * np.log(sse1 / n) + 2 * np.log(n)
    out[col] = {"break_year": int(k), "slope_before_per10y": round(b[1] * 10, 4), "slope_after_per10y": round((b[1] + b[2]) * 10, 4),
                "line_slope_per10y": round(b1[1] * 10, 4), "bic_hinge": round(float(bic_h), 3), "bic_line": round(float(bic_l), 3),
                "hinge_better": bool(bic_h < bic_l)}
    X = np.column_stack([np.ones_like(x), x - 1961, np.maximum(x - k, 0)])
    fits.append(pd.DataFrame({"year": Y.year, "series": col, "value": y, "fit": X @ b}))
# 折れる年の前後の平均の差（区分の平均の5年平均）
pd.concat(fits).round(4).to_csv(R / "requestion_fit.csv", index=False)
m = lambda a, b, c: round(float(Y.loc[Y.year.between(a, b), c].mean()), 2)
out["gap_1961_1970"] = m(1961, 1970, "gap"); out["gap_2016_2025"] = m(2016, 2025, "gap")
out["city_rh_2001_2010"] = m(2001, 2010, "rh_city"); out["city_rh_2016_2025"] = m(2016, 2025, "rh_city")
out["rural_rh_2001_2010"] = m(2001, 2010, "rh_rural"); out["rural_rh_2016_2025"] = m(2016, 2025, "rh_rural")
out["city_rh_1961_1970"] = m(1961, 1970, "rh_city"); out["rural_rh_1961_1970"] = m(1961, 1970, "rh_rural")
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
