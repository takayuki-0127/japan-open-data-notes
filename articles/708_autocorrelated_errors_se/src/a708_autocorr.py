"""708 誤差に自己相関のある時系列で回帰すると、ふつうの標準誤差は何倍小さく出るのか

月次の y と x（x と y は無関係、傾き0）。x も誤差 u も自己相関 ρ の AR(1)。
ρ を 0・0.3・0.6・0.9、長さ n を 60・120・480 か月に変え、各3,000回、傾きの検定（両側5%）を
  ふつうの標準誤差／Newey–West（ずらし幅 L＝floor(4(n/100)^(2/9))）／Newey–West（L＝12）
で行い、偽の有意の割合と標準誤差の比を数える。式で計算し、1回だけ statsmodels の HAC と一致を確かめる。seed 708。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from scipy import stats
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 708）"
rng = np.random.default_rng(708)
REPS = 3000
RHOS, NS = [0.0, 0.3, 0.6, 0.9], [60, 120, 480]


def ar1(rho, reps, n, burn=100):
    e = rng.normal(0, 1, (reps, n + burn)); z = np.zeros_like(e)
    for t in range(1, n + burn):
        z[:, t] = rho * z[:, t - 1] + e[:, t]
    return z[:, burn:]


def fit(x, y, lags):
    n = x.shape[1]
    dx = x - x.mean(1, keepdims=True)
    sxx = (dx ** 2).sum(1)
    b = (dx * (y - y.mean(1, keepdims=True))).sum(1) / sxx
    e = (y - y.mean(1, keepdims=True)) - b[:, None] * dx
    se = np.sqrt((e ** 2).sum(1) / (n - 2) / sxx)
    out = [b, se]
    g = dx * e
    for L in lags:
        s = (g ** 2).sum(1)
        for j in range(1, L + 1):
            s = s + 2 * (1 - j / (L + 1)) * (g[:, j:] * g[:, :-j]).sum(1)
        out.append(np.sqrt(s) / sxx)
    return out


x1, y1 = ar1(0.6, 1, 120), ar1(0.6, 1, 120)
r = fit(x1, y1, [4])
m = sm.OLS(y1[0], sm.add_constant(x1[0])).fit(cov_type="HAC", cov_kwds={"maxlags": 4, "use_correction": False})
assert np.isclose(m.params[1], r[0][0]) and np.isclose(m.bse[1], r[2][0])

rows = []
for rho in RHOS:
    for n in NS:
        L1 = int(np.floor(4 * (n / 100) ** (2 / 9)))
        x, u = ar1(rho, REPS, n), ar1(rho, REPS, n)
        y = 2 + 0 * x + u
        b, se_o, se_n1, se_n12 = fit(x, y, [L1, 12])
        z = stats.norm.ppf(0.975); t = stats.t.ppf(0.975, n - 2)
        rows.append({"rho": rho, "n": n, "nw_lag": L1,
                     "reject_ols": round(float((np.abs(b) / se_o > t).mean() * 100), 2),
                     "reject_nw_auto": round(float((np.abs(b) / se_n1 > z).mean() * 100), 2),
                     "reject_nw_12": round(float((np.abs(b) / se_n12 > z).mean() * 100), 2),
                     "se_ratio_ols": round(float(se_o.mean() / b.std()), 3),
                     "se_ratio_nw_auto": round(float(se_n1.mean() / b.std()), 3),
                     "se_ratio_nw_12": round(float(se_n12.mean() / b.std()), 3),
                     "theory_var_ratio": round((1 + rho * rho) / (1 - rho * rho), 2)})
T = pd.DataFrame(rows); T.to_csv(RES / "summary.csv", index=False)
out = {"true_slope": 0, "reps": REPS, "model": "x と誤差がともに AR(1)、同じ ρ",
       "cells": {f"rho={r['rho']},n={r['n']}": {k: v for k, v in r.items() if k not in ("rho", "n")} for r in rows}}
json.dump(out, open(RES / "a708_main.json", "w"), ensure_ascii=False, indent=1)

labs = [("reject_ols", ORANGE, "ふつうの標準誤差"), ("reject_nw_auto", BLUE, "Newey–West（ずらし幅は自動）"), ("reject_nw_12", GREEN, "Newey–West（ずらし幅12）")]
# 図1：n=120 で ρ ごとの偽の有意
fig, ax = plt.subplots(figsize=(8, 3.8)); t2 = T[T.n == 120]
for c, col, lab in labs:
    ax.plot(t2.rho, t2[c], "o-", color=col, label=lab)
ax.axhline(5, color=GRAY, lw=0.8, ls="--")
ax.set_xlabel("x と誤差の自己相関 ρ"); ax.set_ylabel("関係0で「有意」になった割合（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("120か月：自己相関が強いほど、ふつうの検定は関係のない x を「有意」とする")
save(fig, "a708_by_rho.png", SRC)
# 図2：ρ=0.9 で n ごと
fig, ax = plt.subplots(figsize=(8, 3.8)); t3 = T[T.rho == 0.9]
for c, col, lab in labs:
    ax.plot(t3.n, t3[c], "o-", color=col, label=lab)
ax.axhline(5, color=GRAY, lw=0.8, ls="--"); ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels(NS)
ax.set_xlabel("系列の長さ（か月）"); ax.set_ylabel("関係0で「有意」になった割合（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("ρ=0.9：Newey–West でも直りきらない。ずらし幅を長くすると近づく")
save(fig, "a708_by_n.png", SRC)
# 図3：例
x, u = ar1(0.9, 1, 120), ar1(0.9, 1, 120)
fig, ax = plt.subplots(figsize=(8.5, 3.6))
ax.plot(x[0], color=BLUE, label="x"); ax.plot(u[0] + 0, color=ORANGE, label="y（x とは無関係）")
ax.set_xlabel("月"); ax.legend(frameon=False, fontsize=9)
ax.set_title("ρ=0.9 の例：どちらもゆっくり上下するので、たまたま同じ向きに動く期間が長い")
save(fig, "a708_example.png", SRC)
print(T.to_string())
