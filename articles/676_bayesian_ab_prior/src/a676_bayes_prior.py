"""676 ベイズの A/B テストで、事前分布を強く置くと、効果の推定と「勝つ確率」はどれだけ動くのか

架空の申込み率の A/B テスト。A の申込み率は 5%。B は本当に 0%・+5%・+10%（A に対する相対の伸び）。
1案あたりの人数は 1,000・5,000・20,000。事前分布は A・B とも同じものを置く（ベータ分布）：
  無情報：Beta(1, 1)
  弱い：  Beta(5, 95)      … 平均 5%、100人ぶんの重み
  強い：  Beta(500, 9500)  … 平均 5%、1万人ぶんの重み
事後分布から 4,000 回ずつ引き、伸び（B/A−1）の事後平均と、「B が勝つ確率」P(B>A) を出す。各設定 400 回くり返す。
数字は置いた申込み率と人数で決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の A/B テスト（作成者が乱数で作成、seed 676）"
rng = np.random.default_rng(676)
PA, LIFTS, NS, REPS, DRAWS = 0.05, [0.0, 0.05, 0.10], [1000, 5000, 20000], 400, 4000
PRIORS = {"無情報": (1, 1), "弱い": (5, 95), "強い": (500, 9500)}
COL = {"無情報": BLUE, "弱い": GREEN, "強い": ORANGE}


def posterior(xa, xb, n, prior, size=DRAWS):
    a, b = prior
    pa = rng.beta(a + xa, b + n - xa, size)
    pb = rng.beta(a + xb, b + n - xb, size)
    return pa, pb


rows = []
for lift in LIFTS:
    for n in NS:
        xa = rng.binomial(n, PA, REPS)
        xb = rng.binomial(n, PA * (1 + lift), REPS)
        for name, pr in PRIORS.items():
            est = np.empty(REPS); win = np.empty(REPS)
            for r in range(REPS):
                pa, pb = posterior(xa[r], xb[r], n, pr)
                est[r] = np.mean(pb / pa - 1); win[r] = np.mean(pb > pa)
            rows.append(dict(lift=lift, n=n, prior=name,
                             est_mean=100 * est.mean(), est_sd=100 * est.std(),
                             win_mean=100 * win.mean(), win_sd=100 * win.std(),
                             win95_share=100 * np.mean(win > 0.95)))
S = pd.DataFrame(rows)
S.round(3).to_csv(RES / "summary.csv", index=False)

# 例：1案 5,000人、本当は +10%
n_ex = 5000
xa_ex = int(rng.binomial(n_ex, PA)); xb_ex = int(rng.binomial(n_ex, PA * 1.1))
ex = {}
for name, pr in PRIORS.items():
    pa, pb = posterior(xa_ex, xb_ex, n_ex, pr, 40000)
    ex[name] = 100 * (pb / pa - 1)

def g(lift, n, prior, col):
    return round(float(S[(S.lift == lift) & (S.n == n) & (S.prior == prior)][col].iloc[0]), 2)

out = {"pa": PA, "reps": REPS, "draws": DRAWS,
       "example": {"n": n_ex, "xa": xa_ex, "xb": xb_ex, "obs_lift_pct": round(100 * (xb_ex / xa_ex - 1), 2),
                   **{k: {"post_mean": round(float(v.mean()), 2), "p_win": round(float(np.mean(v > 0)) * 100, 1),
                          "lo": round(float(np.percentile(v, 2.5)), 2), "hi": round(float(np.percentile(v, 97.5)), 2)}
                      for k, v in ex.items()}},
       "est_lift10": {p: {str(n): g(0.10, n, p, "est_mean") for n in NS} for p in PRIORS},
       "win_mean_lift10": {p: {str(n): g(0.10, n, p, "win_mean") for n in NS} for p in PRIORS},
       "win95_lift10": {p: {str(n): g(0.10, n, p, "win95_share") for n in NS} for p in PRIORS},
       "win95_lift0": {p: {str(n): g(0.0, n, p, "win95_share") for n in NS} for p in PRIORS},
       "win_sd_lift0": {p: {str(n): g(0.0, n, p, "win_sd") for n in NS} for p in PRIORS},
       "est_lift5": {p: {str(n): g(0.05, n, p, "est_mean") for n in NS} for p in PRIORS}}
json.dump(out, open(RES / "a676_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：例の事後分布
fig, ax = plt.subplots(figsize=(9, 4.6))
bins = np.linspace(-30, 50, 161)
for name, v in ex.items():
    ax.hist(v, bins=bins, density=True, histtype="step", lw=2, color=COL[name],
            label=f"{name}（事後平均 {v.mean():+.1f}%、勝つ確率 {np.mean(v > 0) * 100:.0f}%）")
ax.axvline(10, color=INK, lw=1, ls="--"); ax.text(10.5, ax.get_ylim()[1] * .5, "本当の伸び +10%", fontsize=10)
ax.axvline(0, color=GRAY, lw=.8)
ax.set_xlabel("B の A に対する伸び（%）"); ax.set_ylabel("事後分布の密度")
ax.set_title(f"同じデータ（1案{n_ex:,}人）でも、強い事前は伸びを0の近くへ引き戻す")
ax.legend(frameon=False, fontsize=9, loc="upper right")
save(fig, "a676_example.png", SRC)

# 図2：伸びの推定（本当は +10%）
fig, ax = plt.subplots(figsize=(9, 4.6))
x = np.arange(len(NS)); w = .26
for i, p in enumerate(PRIORS):
    vals = [g(0.10, n, p, "est_mean") for n in NS]
    bars = ax.bar(x + (i - 1) * w, vals, w, color=COL[p], label=f"事前：{p}")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + .2, f"{v:.1f}%", ha="center", fontsize=9)
ax.axhline(10, color=INK, lw=1, ls="--"); ax.text(-0.45, 10.3, "本当 +10%", fontsize=10)
ax.set_xticks(x); ax.set_xticklabels([f"1案 {n:,}人" for n in NS])
ax.set_ylabel("伸びの事後平均の平均（%）"); ax.set_ylim(0, 16)
ax.set_title("強い事前は、人数が少ないほど伸びを小さく見積もる（400回の平均）")
ax.legend(frameon=False, fontsize=9, loc="upper right")
save(fig, "a676_estimate.png", SRC)

# 図3：勝つ確率が95%を超えた割合
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
for ax, lift, ttl in [(axes[0], 0.0, "本当は差がない（0%）"), (axes[1], 0.10, "本当は +10%")]:
    for i, p in enumerate(PRIORS):
        vals = [g(lift, n, p, "win95_share") for n in NS]
        bars = ax.bar(x + (i - 1) * w, vals, w, color=COL[p], label=f"事前：{p}")
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.0f}", ha="center", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels([f"{n:,}人" for n in NS]); ax.set_title(ttl, fontsize=11)
    ax.set_xlabel("1案あたりの人数")
axes[0].set_ylabel("「勝つ確率 95%超」になった割合（%）"); axes[0].set_ylim(0, 105)
axes[1].legend(frameon=False, fontsize=9, loc="upper left")
fig.suptitle("強い事前は、差がないときの「勝ち」を減らすが、本当の差も見つけにくくする", fontsize=12)
save(fig, "a676_win95.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
