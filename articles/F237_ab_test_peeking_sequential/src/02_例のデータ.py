"""SQL とダッシュボードで使う「1回分のテスト」の日別データを作る（架空のECサイト・シミュレーション）。
差がないのに毎日見ると途中で 1.96 を越えてしまう例（H0）と、本当に +10% の差がある例（H1）。"""
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from common import *
Z = norm.ppf(1 - ALPHA / 2)
def daily_table(seed, pB):
    cA, cB, n = sim_cum(1, 14, BASE, pB, seed)
    h = np.arange(1, 15) * HOURS - 1
    rows = []
    prevA = prevB = prevN = 0
    for d, hh in enumerate(h, 1):
        rows.append(dict(day=d, arm="A", visitors=int(n[hh] - prevN), conversions=int(cA[0, hh] - prevA)))
        rows.append(dict(day=d, arm="B", visitors=int(n[hh] - prevN), conversions=int(cB[0, hh] - prevB)))
        prevA, prevB, prevN = cA[0, hh], cB[0, hh], n[hh]
    z = zstat(cA[0, h], cB[0, h], n[h])
    return pd.DataFrame(rows), z
# H0：途中（3〜6日目）で |z|≥1.96 を越え、14日目には有意でない例を探す
for s in range(1000, 5000):
    df0, z0 = daily_table(s, BASE)
    first = np.argmax(z0 >= Z) + 1 if (z0 >= Z).any() else 0
    if 3 <= first <= 6 and abs(z0[-1]) < 1.0:
        break
# H1：OBF の4回のうち途中（11日目まで）で止まる例
b = pd.read_csv("results/C_bounds_4looks.csv")
for s2 in range(6000, 9000):
    df1, z1 = daily_table(s2, BASE * (1 + LIFT))
    zz = z1[[3, 6, 10, 13]]
    hit = np.abs(zz) >= b["obf"].values
    if hit.any() and hit.argmax() in (1, 2):
        break
df0.to_csv("data/example_test_H0_daily.csv", index=False)
df1.to_csv("data/example_test_H1_daily.csv", index=False)
json.dump(dict(seed_H0=s, first_cross_day_H0=int(first), z_H0=np.round(z0, 4).tolist(), seed_H1=s2, z_H1=np.round(z1, 4).tolist()),
          open("results/B_examples.json", "w"), ensure_ascii=False, indent=1)
print(s, first, np.round(z0, 2)); print(s2, np.round(z1, 2))
