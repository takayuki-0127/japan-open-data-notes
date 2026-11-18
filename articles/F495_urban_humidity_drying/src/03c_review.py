"""独立レビューで足した確かめ（2026-11-18）。乱数は使わない。結果は results/review_checks.json。
1. 大都市と15地点の地点ごとの傾きの違いの検定（Mann–Whitney、両側）
2. 区分の平均の系列の傾きの90%区間（最小二乗法、Newey–West の標準誤差、ラグ3）
3. 大都市−15地点の差に「直線＋ある年の段差」を当て、直線と BIC で比べる（段差の年は1975〜2015年から残差最小）"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, norm

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
T = pd.read_csv(R / "station_slopes.csv")
Y = pd.read_csv(R / "yearly_group_mean.csv")
Y["gap"] = Y.rh_city - Y.rh_rural
x = Y.year.values.astype(float)
n = len(x)


def nw_slope(y, lags=3):
    X = np.column_stack([np.ones(n), x - 1961])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    u = y - X @ b
    XtXi = np.linalg.inv(X.T @ X)
    S = (X * u[:, None]).T @ (X * u[:, None])
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        G = (X[L:] * u[L:, None]).T @ (X[:-L] * u[:-L, None])
        S += w * (G + G.T)
    se = float(np.sqrt((XtXi @ S @ XtXi)[1, 1]))
    z = norm.ppf(0.95)
    return round(b[1] * 10, 4), round((b[1] - z * se) * 10, 4), round((b[1] + z * se) * 10, 4)


out = {}
mw = mannwhitneyu(T[T.group == "city"].rh_slope, T[T.group == "rural"].rh_slope, alternative="two-sided")
out["mw_rh_slope_city_vs_rural_p"] = round(float(mw.pvalue), 4)
for c in ["rh_city", "rh_rural", "gap"]:
    s, lo, hi = nw_slope(Y[c].values)
    out[f"{c}_slope_per10y"] = s; out[f"{c}_ci90"] = [lo, hi]

g = Y.gap.values
bic = lambda sse, k: n * np.log(sse / n) + k * np.log(n)
X1 = np.column_stack([np.ones(n), x - 1961]); b1, *_ = np.linalg.lstsq(X1, g, rcond=None)
bic_line = bic(float(((g - X1 @ b1) ** 2).sum()), 2)
best = None
for k in range(1975, 2016):
    X = np.column_stack([np.ones(n), x - 1961, (x >= k).astype(float)])
    b, *_ = np.linalg.lstsq(X, g, rcond=None)
    sse = float(((g - X @ b) ** 2).sum())
    if best is None or sse < best[1]:
        best = (k, sse, b)
k, sse, b = best
out["gap_step"] = {"step_year": int(k), "step_size": round(float(b[2]), 4), "slope_other_per10y": round(float(b[1]) * 10, 4),
                   "bic_step_line": round(float(bic(sse, 4)), 3), "bic_line": round(float(bic_line), 3),
                   "step_better": bool(bic(sse, 4) < bic_line)}
m = lambda a, c, col="gap": round(float(Y.loc[Y.year.between(a, c), col].mean()), 2)
out["gap_1961_1997"] = m(1961, 1997); out["gap_2003_2025"] = m(2003, 2025)
json.dump(out, open(R / "review_checks.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
