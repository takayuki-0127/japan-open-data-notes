"""706 件数のデータにばらつきの大きさを考えずポアソン回帰を使うと、効果が0でも何%で「有意」になるのか

架空の200店（半分が施策あり）の1か月の問い合わせ件数。件数は負の二項分布（平均 μ、分散 μ+αμ²）で、
施策の効果は0。α（過分散）を 0〜2 で変え、各2,000回：
  ポアソン回帰の標準誤差／準ポアソン（ピアソンのχ²で膨らます）／負の二項（α をモーメント法で推定）／頑健な標準誤差（サンドイッチ）
で施策の係数を検定（両側5%）し、偽の有意の割合と標準誤差の比を数える。
説明変数が施策の有無だけなので、推定値と標準誤差は式で出せる。1回だけ statsmodels の GLM と一致を確かめる。seed 706。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from scipy import stats
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 706）"
rng = np.random.default_rng(706)
N, MU, REPS = 200, 5.0, 2000
ALPHAS = [0.0, 0.1, 0.25, 0.5, 1.0, 2.0]
x = np.repeat([0, 1], N // 2)


def draw(alpha, size):
    if alpha == 0:
        return rng.poisson(MU, size)
    lam = rng.gamma(1 / alpha, MU * alpha, size)
    return rng.poisson(lam)


def fit(y):
    y0, y1 = y[x == 0], y[x == 1]
    m0, m1 = y0.mean(), y1.mean()
    b = np.log(m1 / m0)
    se_p = np.sqrt(1 / y0.sum() + 1 / y1.sum())
    mu = np.where(x == 1, m1, m0)
    phi = ((y - mu) ** 2 / mu).sum() / (len(y) - 2)
    se_q = se_p * np.sqrt(phi)
    se_r = np.sqrt(((y0 - m0) ** 2).sum() / y0.sum() ** 2 + ((y1 - m1) ** 2).sum() / y1.sum() ** 2)
    a = max(0.0, (((y - mu) ** 2 - y) / mu ** 2).sum() / (len(y) - 2))  # モーメント法
    se_nb = np.sqrt(1 / (len(y0) * m0) + a / len(y0) + 1 / (len(y1) * m1) + a / len(y1))
    return b, se_p, se_q, se_nb, se_r, a


# 1回だけ statsmodels と一致を確かめる
yt = draw(1.0, N)
X = sm.add_constant(x.astype(float))
b, se_p, se_q, se_nb, se_r, a = fit(yt)
g = sm.GLM(yt, X, family=sm.families.Poisson()).fit()
assert np.isclose(g.params[1], b) and np.isclose(g.bse[1], se_p)
gq = sm.GLM(yt, X, family=sm.families.Poisson()).fit(scale="X2")
assert np.isclose(gq.bse[1], se_q)
gr = sm.GLM(yt, X, family=sm.families.Poisson()).fit(cov_type="HC0")
assert np.isclose(gr.bse[1], se_r)
gn = sm.GLM(yt, X, family=sm.families.NegativeBinomial(alpha=a)).fit()
assert np.isclose(gn.bse[1], se_nb, rtol=1e-6)

METHODS = ["ポアソン", "準ポアソン", "負の二項", "頑健な標準誤差"]
rows = []
example = {}
for al in ALPHAS:
    R = np.array([fit(draw(al, N)) for _ in range(REPS)])
    sd_true = R[:, 0].std()
    z = 1.959963984540054
    rec = {"alpha": al}
    for k, m in enumerate(METHODS):
        se = R[:, k + 1]
        rec[f"reject_{m}"] = round(float((np.abs(R[:, 0]) / se > z).mean() * 100), 2)
        rec[f"se_ratio_{m}"] = round(float(se.mean() / sd_true), 3)
    rec["alpha_hat_mean"] = round(float(R[:, 5].mean()), 3)
    rec["var_to_mean"] = round(1 + al * MU, 2)
    rows.append(rec)
    if al in (0.0, 1.0):
        example[al] = draw(al, 5000)
T = pd.DataFrame(rows); T.to_csv(RES / "summary.csv", index=False)
out = {"stores": N, "mean_count": MU, "reps": REPS, "true_effect": 0,
       "by_alpha": {str(r["alpha"]): {k: v for k, v in r.items() if k != "alpha"} for r in rows}}
json.dump(out, open(RES / "a706_main.json", "w"), ensure_ascii=False, indent=1)

cols = [ORANGE, BLUE, GREEN, GRAY]
# 図1：偽の有意の割合
fig, ax = plt.subplots(figsize=(8, 3.8))
for m, c in zip(METHODS, cols):
    ax.plot(T.alpha, T[f"reject_{m}"], "o-", color=c, label=m)
ax.axhline(5, color=GRAY, lw=0.8, ls="--")
ax.set_xlabel("過分散の大きさ α（分散＝平均＋α×平均²）"); ax.set_ylabel("効果0で「有意」になった割合（%）")
ax.legend(frameon=False, fontsize=9); ax.set_title("ポアソン回帰の標準誤差は、過分散が大きいほど「有意」を出しすぎる")
save(fig, "a706_false_positive.png", SRC)
# 図2：標準誤差の比
fig, ax = plt.subplots(figsize=(8, 3.8))
for m, c in zip(METHODS, cols):
    ax.plot(T.alpha, T[f"se_ratio_{m}"], "o-", color=c, label=m)
ax.axhline(1, color=GRAY, lw=0.8, ls="--")
ax.set_xlabel("過分散の大きさ α"); ax.set_ylabel("標準誤差の平均 ÷ 推定値の本当の標準偏差")
ax.legend(frameon=False, fontsize=9); ax.set_title("ポアソンの標準誤差は、α=1 で本当のばらつきの半分以下")
save(fig, "a706_se_ratio.png", SRC)
# 図3：件数の分布
fig, ax = plt.subplots(figsize=(8, 3.6))
bins = np.arange(0, 31)
ax.hist(example[0.0].clip(max=30), bins=bins, density=True, color=LIGHT, label="ポアソン（α=0）")
ax.hist(example[1.0].clip(max=30), bins=bins, density=True, histtype="step", lw=1.6, color=ORANGE, label="過分散あり（α=1）")
ax.set_xlabel("1店1か月の件数（30件以上はまとめた）"); ax.set_ylabel("割合"); ax.legend(frameon=False, fontsize=9)
ax.set_title("平均は同じ5件でも、過分散があると0件の店と多い店がともに増える")
save(fig, "a706_counts.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
