"""709 y を対数にした回帰の係数を「そのまま%」と読むと、効果が大きいときどれだけずれるのか

log(y) = a + b×施策 + e（e は正規、標準偏差0.5）。本当の効果（y が何%変わるか）＝exp(b)−1。
  1) 係数×100 を%と読んだときのずれ（式）
  2) 架空の店（施策あり・なし各50店）で、本当の効果を−60%〜+200%に置いて各3,000回、
     係数×100・exp(係数)−1・ケネディの補正 exp(係数−分散/2)−1 の平均を本当の効果と比べる
  3) 平均の比（算術平均）と exp(b)−1 が同じになることの確認
statsmodels の OLS と一致を確かめる。seed 709。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 709）"
rng = np.random.default_rng(709)
N, SD, REPS = 50, 0.5, 3000
EFF = [-60, -40, -20, -10, 0, 10, 20, 50, 100, 200]
# 1) 読み方のずれ（式）
bs = np.linspace(-1.0, 1.1, 211)
curve = pd.DataFrame({"b": bs, "read_pct": bs * 100, "true_pct": (np.exp(bs) - 1) * 100})
curve["gap_pt"] = curve.read_pct - curve.true_pct
curve.round(4).to_csv(RES / "reading_curve.csv", index=False)
gap1 = curve[curve.gap_pt.abs() >= 1]
thr_pos = float(curve[(curve.b > 0) & (curve.gap_pt.abs() >= 1)].b.min()); thr_neg = float(curve[(curve.b < 0) & (curve.gap_pt.abs() >= 1)].b.max())
# 2) シミュレーション
x = np.repeat([0, 1], N)
X = sm.add_constant(x.astype(float))
rows = []
for e in EFF:
    b_true = np.log(1 + e / 100)
    ly = 3 + b_true * x + rng.normal(0, SD, (REPS, 2 * N))
    m0, m1 = ly[:, :N].mean(1), ly[:, N:].mean(1)
    b = m1 - m0
    s2 = (((ly[:, :N] - m0[:, None]) ** 2).sum(1) + ((ly[:, N:] - m1[:, None]) ** 2).sum(1)) / (2 * N - 2)
    vb = s2 * (2 / N)
    if e == 50:
        f = sm.OLS(ly[0], X).fit(); assert np.isclose(f.params[1], b[0]) and np.isclose(f.bse[1] ** 2, vb[0])
    y = np.exp(ly)
    ratio_mean = y[:, N:].mean(1) / y[:, :N].mean(1) - 1
    rows.append({"true_pct": e, "b_true": round(float(b_true), 4), "read_b100_mean": round(float((b * 100).mean()), 2),
                 "exp_minus1_mean": round(float(((np.exp(b) - 1) * 100).mean()), 2),
                 "kennedy_mean": round(float(((np.exp(b - vb / 2) - 1) * 100).mean()), 2),
                 "ratio_of_means_mean": round(float((ratio_mean * 100).mean()), 2)})
T = pd.DataFrame(rows); T.to_csv(RES / "summary.csv", index=False)
pick = lambda v: {k: round(float(curve.loc[(curve.b - v).abs().idxmin(), k]), 1) for k in ["read_pct", "true_pct", "gap_pt"]}
out = {"sd_log": SD, "stores_per_group": N, "reps": REPS,
       "gap_reaches_1pt_at_b": {"positive": round(thr_pos, 2), "negative": round(thr_neg, 2)},
       "examples": {"b=0.10": pick(0.10), "b=0.30": pick(0.30), "b=0.69": pick(0.69), "b=-0.69": pick(-0.69), "b=1.10": pick(1.10)},
       "simulation": {str(r["true_pct"]): {k: v for k, v in r.items() if k != "true_pct"} for r in rows}}
json.dump(out, open(RES / "a709_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：係数と本当の%
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.plot(bs, curve.true_pct, color=BLUE, label="本当の変化 exp(係数)−1")
ax.plot(bs, curve.read_pct, color=ORANGE, ls="--", label="係数×100 を%と読む")
ax.axhline(0, color=GRAY, lw=0.6); ax.axvline(0, color=GRAY, lw=0.6)
ax.set_xlabel("対数の回帰の係数"); ax.set_ylabel("y の変化（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("係数が0に近いうちは同じ。大きくなるほど、プラスは小さく、マイナスは大きく読み違える")
save(fig, "a709_curve.png", SRC)
# 図2：ずれ（ポイント）
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.plot(curve.true_pct, curve.gap_pt, color=ORANGE)
ax.axhline(1, color=GRAY, lw=0.6, ls="--"); ax.axhline(-1, color=GRAY, lw=0.6, ls="--")
for e in [-50, -20, 20, 50, 100]:
    g = 100 * np.log(1 + e / 100) - e
    ax.scatter([e], [g], color=ORANGE); ax.annotate(f"{e:+d}%→読み{100*np.log(1+e/100):+.0f}%", (e, g), xytext=(4, 4), textcoords="offset points", fontsize=8.5)
ax.set_xlabel("本当の変化（%）"); ax.set_ylabel("読みのずれ（ポイント）")
ax.set_title("本当の変化が+15%・−14%を超えると、ずれは1ポイントを超える")
save(fig, "a709_gap.png", SRC)
# 図3：シミュレーションの平均
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.plot(T.true_pct, T.read_b100_mean - T.true_pct, "o-", color=ORANGE, label="係数×100")
ax.plot(T.true_pct, T.exp_minus1_mean - T.true_pct, "s-", color=BLUE, label="exp(係数)−1")
ax.plot(T.true_pct, T.kennedy_mean - T.true_pct, "^-", color=GREEN, label="exp(係数−分散/2)−1")
ax.axhline(0, color=GRAY, lw=0.8)
ax.set_xlabel("本当の変化（%）"); ax.set_ylabel("推定の平均 − 本当の値（ポイント）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("各50店・3,000回の平均：exp(係数)−1 はわずかに大きく出る。補正するとほぼ0")
save(fig, "a709_simulation.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
