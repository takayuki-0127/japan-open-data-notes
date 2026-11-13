"""606 指標を10個見るとき、Bonferroni・Holm・BH の補正で、本当の効果を見つける力はどれだけ違うのか

A/B テストなどで10個の指標を同時に検定する場面を、検定統計量（z）のシミュレーションで作る。
本当に効果のある指標の数 k を 0〜10 で変え、効果のある指標の z は平均 2.5（1つだけ見れば 5% 水準で約70% 見つかる大きさ）。
  無補正（p<0.05）・Bonferroni（p<0.05/m）・Holm（段階的に緩める）・Benjamini–Hochberg（偽発見率を5%に）
偽の「差あり」が1つでも出る割合（FWER）・「差あり」のうち偽の割合（FDR）・効果のある指標を見つける割合（検出力）を数える。
指標どうしに相関がある場合（0.5）と、指標の数 m を変えた場合も見る。各条件2万回、seed 606。
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 606）"
rng = np.random.default_rng(606)
R, ALPHA, DELTA = 20000, 0.05, 2.5


def decide(p):
    """p: (R, m) → 4つの方法の『差あり』の判定 (R, m)"""
    R_, m = p.shape
    out = {"none": p < ALPHA, "bonf": p < ALPHA / m}
    order = np.argsort(p, axis=1); ps = np.take_along_axis(p, order, axis=1)
    j = np.arange(1, m + 1)
    # Holm：小さい順に p_(j) <= alpha/(m-j+1) が続くところまで棄却
    ok = ps <= ALPHA / (m - j + 1)
    holm_n = np.where(ok.all(axis=1), m, np.argmin(ok, axis=1))
    # BH：p_(j) <= j*alpha/m を満たす最大の j まで棄却
    okb = ps <= j * ALPHA / m
    bh_n = np.where(okb.any(axis=1), m - np.argmax(okb[:, ::-1], axis=1), 0)
    for name, n in [("holm", holm_n), ("bh", bh_n)]:
        rej_sorted = j[None, :] <= n[:, None]
        rej = np.zeros_like(rej_sorted)
        np.put_along_axis(rej, order, rej_sorted, axis=1)
        out[name] = rej
    return out


def run(m, k, rho=0.0):
    if rho > 0:
        z = np.sqrt(rho) * rng.standard_normal((R, 1)) + np.sqrt(1 - rho) * rng.standard_normal((R, m))
    else:
        z = rng.standard_normal((R, m))
    z[:, :k] += DELTA
    p = 2 * stats.norm.sf(np.abs(z))
    res = {}
    for name, rej in decide(p).items():
        fp = rej[:, k:].sum(axis=1); tp = rej[:, :k].sum(axis=1); nrej = fp + tp
        res[name] = {"fwer": float((fp > 0).mean()), "fdr": float(np.mean(np.where(nrej > 0, fp / np.maximum(nrej, 1), 0))),
                     "power": float(tp.mean() / k) if k > 0 else np.nan, "any_true_found": float((tp > 0).mean()) if k > 0 else np.nan}
    return res


# scipy の BH・Holm と判定が一致するか（小さな例で確かめる）
from scipy.stats import false_discovery_control
pp = rng.uniform(0, 0.1, (200, 10)); dd = decide(pp)
assert np.array_equal(dd["bh"], false_discovery_control(pp, axis=1) < ALPHA)
rows = []
for rho in [0.0, 0.5]:
    for k in range(0, 11):
        r = run(10, k, rho)
        for name, v in r.items():
            rows.append({"rho": rho, "m": 10, "k": k, "method": name, **{a: round(b, 4) for a, b in v.items()}})
for m in [2, 5, 10, 20, 50, 100]:
    r = run(m, max(1, m // 5))
    for name, v in r.items():
        rows.append({"rho": 0.0, "m": m, "k": max(1, m // 5), "method": name, **{a: round(b, 4) for a, b in v.items()}, "m_series": True})
df = pd.DataFrame(rows); df.to_csv(RES / "summary.csv", index=False)
base = df[(df.rho == 0) & (df.m == 10) & (df.get("m_series").isna())]
mser = df[df.get("m_series") == True]


def pick(d, k, meth, col):
    return float(d[(d.k == k) & (d.method == meth)][col].iloc[0])


single_power = float(stats.norm.sf(1.96 - DELTA) + stats.norm.cdf(-1.96 - DELTA))
out = {"reps": R, "delta": DELTA, "single_test_power": round(single_power, 3),
       "k0_fwer": {mm: pick(base, 0, mm, "fwer") for mm in ["none", "bonf", "holm", "bh"]},
       "k3_power": {mm: pick(base, 3, mm, "power") for mm in ["none", "bonf", "holm", "bh"]},
       "k3_fdr": {mm: pick(base, 3, mm, "fdr") for mm in ["none", "bonf", "holm", "bh"]},
       "k3_fwer": {mm: pick(base, 3, mm, "fwer") for mm in ["none", "bonf", "holm", "bh"]},
       "k8_power": {mm: pick(base, 8, mm, "power") for mm in ["none", "bonf", "holm", "bh"]},
       "k8_fwer": {mm: pick(base, 8, mm, "fwer") for mm in ["none", "bonf", "holm", "bh"]},
       "k1_power": {mm: pick(base, 1, mm, "power") for mm in ["none", "bonf", "holm", "bh"]},
       "rho05_k0_fwer": {mm: pick(df[(df.rho == 0.5) & (df.m == 10)], 0, mm, "fwer") for mm in ["none", "bonf", "holm", "bh"]},
       "m_series_power": {int(mm): {me: float(mser[(mser.m == mm) & (mser.method == me)].power.iloc[0]) for me in ["none", "bonf", "holm", "bh"]} for mm in mser.m.unique()}}
json.dump(out, open(RES / "a606_main.json", "w"), ensure_ascii=False, indent=1)

COL = {"none": GRAY, "bonf": ORANGE, "holm": BLUE, "bh": GREEN}
LAB = {"none": "補正なし（p<0.05）", "bonf": "Bonferroni", "holm": "Holm", "bh": "Benjamini–Hochberg"}
MK = {"none": "o", "bonf": "s", "holm": "^", "bh": "D"}
# 図1：検出力
fig, ax = plt.subplots(figsize=(8, 4))
for mm in ["none", "bonf", "holm", "bh"]:
    s = base[base.method == mm].dropna(subset=["power"])
    ax.plot(s.k, s.power * 100, marker=MK[mm], color=COL[mm], label=LAB[mm])
ax.set_xlabel("10個の指標のうち、本当に効果のある指標の数"); ax.set_ylabel("効果のある指標を見つけた割合（%）")
ax.set_xticks(range(1, 11)); ax.set_ylim(0, 100); ax.legend(frameon=False, fontsize=9)
ax.set_title("本当の効果を見つける力：効果のある指標が多いほど、Holm と BH が追いつく")
save(fig, "a606_power_by_k.png", SRC)
# 図2：FWER と FDR
fig, axs = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw={"wspace": 0.3})
for mm in ["none", "bonf", "holm", "bh"]:
    s = base[base.method == mm]
    axs[0].plot(s.k[s.k < 10], s.fwer[s.k < 10] * 100, marker=MK[mm], color=COL[mm], label=LAB[mm])
    axs[1].plot(s.k[s.k < 10], s.fdr[s.k < 10] * 100, marker=MK[mm], color=COL[mm], label=LAB[mm])
axs[0].axhline(5, color=GRAY, ls=":"); axs[1].axhline(5, color=GRAY, ls=":")
axs[0].set_title("偽の「差あり」が1つでも出る割合"); axs[1].set_title("「差あり」のうち偽の割合（平均）")
for a in axs:
    a.set_xlabel("本当に効果のある指標の数（10個のうち）"); a.set_ylabel("%"); a.set_xticks(range(0, 10))
axs[0].legend(frameon=False, fontsize=8)
save(fig, "a606_fwer_fdr.png", SRC, y=-0.04)
# 図3：指標の数 m を変える（効果のある指標は m/5）
fig, ax = plt.subplots(figsize=(8, 3.8))
for mm in ["none", "bonf", "holm", "bh"]:
    s = mser[mser.method == mm]
    ax.plot(s.m, s.power * 100, marker=MK[mm], color=COL[mm], label=LAB[mm])
ax.set_xscale("log"); ax.set_xticks([2, 5, 10, 20, 50, 100]); ax.set_xticklabels(["2", "5", "10", "20", "50", "100"])
ax.set_xlabel("同時に見る指標の数（そのうち5分の1に効果あり）"); ax.set_ylabel("効果のある指標を見つけた割合（%）"); ax.set_ylim(0, 100)
ax.legend(frameon=False, fontsize=9); ax.set_title("指標を増やすほど、Bonferroni と Holm は見つけにくくなる")
save(fig, "a606_power_by_m.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
