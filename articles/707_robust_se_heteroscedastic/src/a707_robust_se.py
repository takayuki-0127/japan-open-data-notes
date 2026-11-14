"""707 散らばりが x とともに広がるデータで、ふつうの標準誤差の95%区間は何%当たるのか

y = 1 + 0.5x + e、x は右に裾の長い分布（自由度3のχ²を3で割ったもの、平均1）。e の標準偏差は x^h（h=0 で一定）。
h を 0・0.5・1・1.5、件数 n を 20・50・200・1000 に変え、各4,000回、傾きの95%区間を
  ふつうの標準誤差／HC0（ホワイト）／HC3
で作り、本当の傾き0.5を含む割合を数える。単回帰なので式で計算し、1回だけ statsmodels と一致を確かめる。seed 707。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from scipy import stats
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 707）"
rng = np.random.default_rng(707)
B1, REPS = 0.5, 4000
HS, NS = [0.0, 0.5, 1.0, 1.5], [20, 50, 200, 1000]


def gen(n, h, reps):
    x = rng.chisquare(3, (reps, n)) / 3
    e = rng.normal(0, 1, (reps, n)) * x ** h
    return x, 1 + B1 * x + e


def ses(x, y):
    xm = x.mean(1, keepdims=True); dx = x - xm
    sxx = (dx ** 2).sum(1)
    b = (dx * (y - y.mean(1, keepdims=True))).sum(1) / sxx
    a = y.mean(1) - b * xm[:, 0]
    e = y - a[:, None] - b[:, None] * x
    n = x.shape[1]
    s2 = (e ** 2).sum(1) / (n - 2)
    se_ols = np.sqrt(s2 / sxx)
    se_hc0 = np.sqrt((dx ** 2 * e ** 2).sum(1)) / sxx
    hii = 1 / n + dx ** 2 / sxx[:, None]
    se_hc3 = np.sqrt((dx ** 2 * e ** 2 / (1 - hii) ** 2).sum(1)) / sxx
    return b, se_ols, se_hc0, se_hc3


x1, y1 = gen(50, 1.0, 1)
b, so, s0, s3 = ses(x1, y1)
m = sm.OLS(y1[0], sm.add_constant(x1[0]))
assert np.isclose(m.fit().params[1], b[0]) and np.isclose(m.fit().bse[1], so[0])
assert np.isclose(m.fit(cov_type="HC0").bse[1], s0[0]) and np.isclose(m.fit(cov_type="HC3").bse[1], s3[0])

M = ["ふつうの標準誤差", "HC0", "HC3"]
rows = []
for h in HS:
    for n in NS:
        x, y = gen(n, h, REPS)
        b, *se = ses(x, y)
        t = stats.t.ppf(0.975, n - 2)
        rec = {"h": h, "n": n}
        for k, s in zip(M, se):
            rec[f"cover_{k}"] = round(float((np.abs(b - B1) <= t * s).mean() * 100), 2)
            rec[f"se_ratio_{k}"] = round(float(s.mean() / b.std()), 3)
        rows.append(rec)
T = pd.DataFrame(rows); T.to_csv(RES / "summary.csv", index=False)
out = {"true_slope": B1, "reps": REPS, "x_dist": "χ²(3)/3（平均1）", "sd_of_e": "x^h",
       "cells": {f"h={r['h']},n={r['n']}": {k: v for k, v in r.items() if k not in ("h", "n")} for r in rows}}
json.dump(out, open(RES / "a707_main.json", "w"), ensure_ascii=False, indent=1)

cols = [ORANGE, BLUE, GREEN]
# 図1：n=200 で h ごとの当たる割合
fig, ax = plt.subplots(figsize=(8, 3.8))
t2 = T[T.n == 200]
for k, c in zip(M, cols):
    ax.plot(t2.h, t2[f"cover_{k}"], "o-", color=c, label=k)
ax.axhline(95, color=GRAY, lw=0.8, ls="--"); ax.set_ylim(45, 100)
ax.set_xlabel("散らばりの広がり方 h（誤差の標準偏差＝x^h）"); ax.set_ylabel("95%区間が本当の傾きを含む割合（%）")
ax.legend(frameon=False, fontsize=9); ax.set_title("200件：散らばりが x とともに広がるほど、ふつうの区間は当たらなくなる")
save(fig, "a707_by_h.png", SRC)
# 図2：h=1 で n ごと
fig, ax = plt.subplots(figsize=(8, 3.8))
t3 = T[T.h == 1.0]
for k, c in zip(M, cols):
    ax.plot(t3.n, t3[f"cover_{k}"], "o-", color=c, label=k)
ax.axhline(95, color=GRAY, lw=0.8, ls="--"); ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels(NS); ax.set_ylim(45, 100)
ax.set_xlabel("件数"); ax.set_ylabel("95%区間が本当の傾きを含む割合（%）")
ax.legend(frameon=False, fontsize=9); ax.set_title("h=1：件数を増やしても、ふつうの区間は当たるようにならない。HC0 は件数が少ないと甘い")
save(fig, "a707_by_n.png", SRC)
# 図3：例のデータ
x, y = gen(200, 1.0, 1)
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.scatter(x[0], y[0], s=10, color=BLUE, alpha=0.6)
xs = np.linspace(0, x.max(), 50); ax.plot(xs, 1 + B1 * xs, color=ORANGE, label="本当の直線 y=1+0.5x")
ax.set_xlabel("x"); ax.set_ylabel("y"); ax.legend(frameon=False, fontsize=9)
ax.set_title("h=1 の例（200件）：x の大きい少数の点が大きく散らばる")
save(fig, "a707_example.png", SRC)
print(T.to_string())
