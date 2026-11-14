"""680 歪んだ分布の平均の95%区間は、何件あれば本当に95%当たるのか

4つの分布から n 件を引き、t 分布を使った平均の95%区間（平均 ± t × 標準偏差 / √n）を作る。
  正規分布（比べる基準）
  指数分布（歪度 2）：例えば待ち時間
  対数正規 σ=1（歪度 約6.2）：例えば1人あたりの購入額
  対数正規 σ=1.5（歪度 約33）：一部の人が非常に大きい額を使う場合
件数 n は 10・20・50・100・300・1,000・3,000。各 10,000 回。
当たる割合＝区間が本当の平均を含んだ割合。外れは「区間が低すぎた（本当の平均が上限より上）」と「高すぎた（下限より下）」に分ける。
数字は置いた分布で決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の分布（作成者が乱数で作成、seed 680）"
rng = np.random.default_rng(680)
REPS, CHUNK = 10_000, 1_000
NS = [10, 20, 50, 100, 300, 1000, 3000]
DISTS = {
    "正規分布": (lambda size: rng.normal(1, 1, size), 1.0, 0.0),
    "指数分布": (lambda size: rng.exponential(1, size), 1.0, 2.0),
    "対数正規 σ=1": (lambda size: rng.lognormal(0, 1, size), np.exp(.5), (np.e + 2) * np.sqrt(np.e - 1)),
    "対数正規 σ=1.5": (lambda size: rng.lognormal(0, 1.5, size), np.exp(1.125),
                     (np.exp(2.25) + 2) * np.sqrt(np.exp(2.25) - 1)),
}
COL = {"正規分布": GRAY, "指数分布": GREEN, "対数正規 σ=1": BLUE, "対数正規 σ=1.5": ORANGE}

rows = []; scat = None
for name, (f, mu, skew) in DISTS.items():
    for n in NS:
        hit = low = high = 0; under = 0
        tq = stats.t.ppf(.975, n - 1)
        for c in range(REPS // CHUNK):
            x = f((CHUNK, n))
            m = x.mean(1); s = x.std(1, ddof=1); h = tq * s / np.sqrt(n)
            low += np.sum(mu > m + h); high += np.sum(mu < m - h); under += np.sum(m < mu)
            if name == "対数正規 σ=1" and n == 50 and c == 0:
                scat = (m.copy(), s.copy(), (mu > m + h) | (mu < m - h))
        hit = REPS - low - high
        rows.append(dict(dist=name, skew=skew, n=n, cover=100 * hit / REPS, miss_low_interval=100 * low / REPS,
                         miss_high_interval=100 * high / REPS, mean_below_true=100 * under / REPS))
S = pd.DataFrame(rows)
S.round(3).to_csv(RES / "summary.csv", index=False)


def g(d, n, c, nd=1):
    return round(float(S[(S.dist == d) & (S.n == n)][c].iloc[0]), nd)


def n_needed(d, target=94.0):
    sub = S[(S.dist == d) & (S.cover >= target)]
    return int(sub.n.min()) if len(sub) else None


out = {"reps": REPS,
       "skew": {d: round(float(v[2]), 1) for d, v in DISTS.items()},
       "cover": {d: {str(n): g(d, n, "cover") for n in NS} for d in DISTS},
       "miss_interval_too_low": {d: {str(n): g(d, n, "miss_low_interval") for n in NS} for d in DISTS},
       "miss_interval_too_high": {d: {str(n): g(d, n, "miss_high_interval") for n in NS} for d in DISTS},
       "mean_below_true_pct": {d: {str(n): g(d, n, "mean_below_true") for n in NS} for d in DISTS},
       "first_n_cover_ge_94": {d: n_needed(d) for d in DISTS}}
json.dump(out, open(RES / "a680_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：当たる割合
fig, ax = plt.subplots(figsize=(9, 4.6))
for d in DISTS:
    sub = S[S.dist == d]
    ax.plot(sub.n, sub.cover, "o-", color=COL[d], lw=2, label=f"{d}（歪度 {DISTS[d][2]:.1f}）")
ax.axhline(95, color=INK, lw=.8, ls="--"); ax.text(10, 95.4, "95%", fontsize=9)
ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels([f"{n:,}" for n in NS])
ax.set_xlabel("件数 n（対数の目盛り）"); ax.set_ylabel("区間が本当の平均を含んだ割合（%）")
ax.set_ylim(70, 100); ax.legend(frameon=False, loc="lower right", fontsize=9)
ax.set_title("歪みが強いほど、95%区間が95%当たるまでに多くの件数が要る")
save(fig, "a680_coverage.png", SRC)

# 図2：外れ方（n=50）
fig, ax = plt.subplots(figsize=(9, 4.4))
names = list(DISTS); y = np.arange(len(names))[::-1]
lo = [g(d, 50, "miss_low_interval") for d in names]; hi = [g(d, 50, "miss_high_interval") for d in names]
ax.barh(y, lo, color=ORANGE, label="区間が低すぎた（本当の平均が上限より上）")
ax.barh(y, [-v for v in hi], color=BLUE, label="区間が高すぎた（本当の平均が下限より下）")
for yy, a, b in zip(y, lo, hi):
    ax.text(a + .2, yy, f"{a:.1f}%", va="center", fontsize=9.5)
    ax.text(-b - .2, yy, f"{b:.1f}%", va="center", ha="right", fontsize=9.5)
ax.axvline(0, color=INK, lw=.8); ax.axvline(2.5, color=GRAY, lw=.8, ls=":"); ax.axvline(-2.5, color=GRAY, lw=.8, ls=":")
ax.set_yticks(y); ax.set_yticklabels(names); ax.set_xlim(-8, 20)
ax.set_xticks([-5, -2.5, 0, 2.5, 5, 10, 15, 20]); ax.set_xticklabels(["5", "2.5", "0", "2.5", "5", "10", "15", "20"])
ax.set_xlabel("外れた割合（%）。点線は本来の 2.5%")
ax.legend(frameon=False, loc="upper right", fontsize=9)
ax.set_title("n=50 の外れ方：右に長い分布では、外れはほぼ「区間が低すぎた」側")
save(fig, "a680_misses.png", SRC)

# 図3：平均と標準偏差のつながり（対数正規 σ=1、n=50）
m, s, miss = scat; mu = DISTS["対数正規 σ=1"][1]
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.scatter(m[~miss], s[~miss], s=7, color=LIGHT, label="区間が本当の平均を含んだ")
ax.scatter(m[miss], s[miss], s=12, color=ORANGE, label="外れた")
ax.axvline(mu, color=INK, lw=1, ls="--"); ax.text(mu + .02, ax.get_ylim()[1] * .95, f"本当の平均 {mu:.2f}", fontsize=9.5, va="top")
ax.set_xlabel("50件の平均"); ax.set_ylabel("50件の標準偏差")
ax.legend(frameon=False, loc="upper left", fontsize=9)
ax.set_title("対数正規 σ=1・n=50：平均が低い回は標準偏差も小さく、区間が狭くなる（1,000回）")
save(fig, "a680_mean_vs_sd.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
