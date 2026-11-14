"""738 件数の少ないデータでジニ係数を出すと、本当の値よりどれだけ小さく出るのか

架空の店の売上（対数正規、σ＝1）。本当のジニ係数は 2Φ(σ/√2)−1＝0.520。
件数 n を 5〜500 に変え、各2,000回、次の3つで推定する。
  ふつう：Σ|xi−xj| /(2 n² 平均)
  補正：ふつう × n/(n−1)
  ブートストラップの偏り補正：2×ふつう − ブートストラップ200回の平均（回数を500回に減らす）
あわせて σ＝0.5・1・1.5（本当のジニ 0.276・0.520・0.711）で、n＝10 のときの偏りを見る。
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 738）"
rng = np.random.default_rng(738)


def gini(x):
    x = np.sort(x); n = len(x); i = np.arange(1, n + 1)
    return float(np.sum((2 * i - n - 1) * x) / (n * n * x.mean()))


def gini_rows(X):
    """行ごとのふつうのジニ係数"""
    X = np.sort(X, axis=1); n = X.shape[1]; i = np.arange(1, n + 1)
    return (X * (2 * i - n - 1)).sum(1) / (n * n * X.mean(1))


true_g = lambda s: 2 * stats.norm.cdf(s / np.sqrt(2)) - 1
NS = [5, 10, 20, 50, 100, 500]
R, RB, B = 2000, 500, 200
rows = []
for n in NS:
    X = rng.lognormal(0, 1, size=(R, n))
    g = gini_rows(X); gc = g * n / (n - 1)
    gb = []
    for r in range(RB):
        idx = rng.integers(0, n, size=(B, n))
        gb.append(2 * g[r] - gini_rows(X[r][idx]).mean())
    gb = np.array(gb)
    rows.append(dict(n=n, true=true_g(1), plain=g.mean(), corrected=gc.mean(), boot=gb.mean(),
                     plain_bias_pct=(g.mean() / true_g(1) - 1) * 100, corrected_bias_pct=(gc.mean() / true_g(1) - 1) * 100,
                     boot_bias_pct=(gb.mean() / true_g(1) - 1) * 100,
                     plain_sd=g.std(), corrected_sd=gc.std(), boot_sd=gb.std(),
                     plain_p05=np.quantile(g, .05), plain_p95=np.quantile(g, .95)))
S = pd.DataFrame(rows); S.to_csv(RES / "by_n.csv", index=False)
assert abs(gini(np.array([1, 2, 3, 4.])) - gini_rows(np.array([[1, 2, 3, 4.]]))[0]) < 1e-12

rows2 = []
for s in [0.5, 1.0, 1.5]:
    X = rng.lognormal(0, s, size=(R, 10)); g = gini_rows(X)
    rows2.append(dict(sigma=s, true=true_g(s), plain=g.mean(), corrected=(g * 10 / 9).mean(),
                      plain_bias_pct=(g.mean() / true_g(s) - 1) * 100, corrected_bias_pct=((g * 10 / 9).mean() / true_g(s) - 1) * 100))
G = pd.DataFrame(rows2); G.to_csv(RES / "by_sigma_n10.csv", index=False)

f = lambda n, c: float(S[S.n == n][c].iloc[0])
out = {"true_gini": float(true_g(1)), "reps": R, "boot_reps": RB, "boot_B": B,
       "by_n": {int(n): {"plain": round(f(n, "plain"), 3), "corrected": round(f(n, "corrected"), 3), "boot": round(f(n, "boot"), 3)} for n in NS},
       "n5_plain_bias_pct": f(5, "plain_bias_pct"), "n10_plain_bias_pct": f(10, "plain_bias_pct"),
       "n20_plain_bias_pct": f(20, "plain_bias_pct"), "n100_plain_bias_pct": f(100, "plain_bias_pct"),
       "n10_corrected_bias_pct": f(10, "corrected_bias_pct"), "n10_boot_bias_pct": f(10, "boot_bias_pct"),
       "n5_corrected_bias_pct": f(5, "corrected_bias_pct"),
       "n10_plain_p05_p95": [f(10, "plain_p05"), f(10, "plain_p95")],
       "by_sigma_n10": rows2}
json.dump(out, open(RES / "a738_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：件数ごとの平均
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(S.n, S.plain, "o-", color=ORANGE, label="ふつうの式")
ax.fill_between(S.n, S.plain_p05, S.plain_p95, color=ORANGE, alpha=.12)
ax.plot(S.n, S.corrected, "o-", color=BLUE, label="n/(n−1) の補正")
ax.plot(S.n, S.boot, "o--", color=GREEN, label="ブートストラップの補正")
ax.axhline(true_g(1), color=GRAY, ls="--", lw=1); ax.text(5, true_g(1) + .01, f"本当の値 {true_g(1):.3f}", color=GRAY, fontsize=9)
ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels(NS)
ax.set_xlabel("件数（対数の目盛り）"); ax.set_ylabel("ジニ係数（平均）"); ax.legend(frameon=False, loc="lower right")
ax.set_title("ふつうの式は件数が少ないほど小さく出る（各2,000回、帯は90%）")
save(fig, "a738_by_n.png", SRC)

# 図2：偏り（%）
fig, ax = plt.subplots(figsize=(9, 4.6))
x = np.arange(len(NS)); w = .27
for k, (c, l, colr) in enumerate([("plain_bias_pct", "ふつうの式", ORANGE), ("corrected_bias_pct", "n/(n−1) の補正", BLUE), ("boot_bias_pct", "ブートストラップの補正", GREEN)]):
    b = ax.bar(x + (k - 1) * w, S[c], w, color=colr, label=l)
    for bb in b:
        v = bb.get_height(); ax.text(bb.get_x() + w / 2, v - 1.6 if v < 0 else v + .3, f"{v:.1f}", ha="center", fontsize=7.5)
ax.axhline(0, color=GRAY, lw=1); ax.set_xticks(x); ax.set_xticklabels([f"{n}件" for n in NS])
ax.set_ylabel("本当の値とのずれ（%）"); ax.legend(frameon=False, loc="lower right")
ax.set_title("補正すると、10件で数%まで縮む")
save(fig, "a738_bias.png", SRC)

# 図3：ばらつきの大きさごと（10件）
fig, ax = plt.subplots(figsize=(9, 4.6))
x = np.arange(3)
ax.bar(x - .2, G.plain_bias_pct, .4, color=ORANGE, label="ふつうの式")
ax.bar(x + .2, G.corrected_bias_pct, .4, color=BLUE, label="n/(n−1) の補正")
for i in range(3):
    ax.text(i - .2, G.plain_bias_pct[i] - 1.5, f"{G.plain_bias_pct[i]:.1f}", ha="center", fontsize=9)
    ax.text(i + .2, G.corrected_bias_pct[i] - 1.5 if G.corrected_bias_pct[i] < 0 else G.corrected_bias_pct[i] + .3, f"{G.corrected_bias_pct[i]:.1f}", ha="center", fontsize=9)
ax.axhline(0, color=GRAY, lw=1)
ax.set_xticks(x); ax.set_xticklabels([f"σ={s}（本当のジニ {t:.2f}）" for s, t in zip(G.sigma, G.true)])
ax.set_ylabel("本当の値とのずれ（%）"); ax.legend(frameon=False, loc="lower left")
ax.set_title("10件のとき、ふつうの式は12〜17%小さく出る。ばらつきが大きいほど補正しても残る")
save(fig, "a738_by_sigma.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
