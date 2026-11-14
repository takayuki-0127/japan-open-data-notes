"""776 差の差で対照を1店だけ選ぶと、施策の効果の推定はどれだけ振れるのか

架空の月次の売上。対照の候補50店と施策の店1店、24か月（前12か月・後12か月）。
売上 = 店の水準 + 店ごとの傾き（年に±数%）× 月 + 全店に共通の動き + ばらつき。施策の効果は0（または+5）。
差の差を、対照1店（無作為に選ぶ）・5店・全50店の平均・合成コントロール（前12か月に合うように非負の重みで組む）で出す。
月ごとの差（施策の店−対照）を前後で t 検定し、効果0のときに「有意（5%）」になる割合も数える。各1,000回。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from scipy.optimize import nnls
from common import RES, save, BLUE, ORANGE, GRAY, GREEN

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 776）"
rng = np.random.default_rng(776)
J, T, T0, R = 50, 24, 12, 1000
t = np.arange(T)


def make(effect):
    lvl = rng.normal(100, 15, J + 1)
    slope = rng.normal(0, .25, J + 1)                 # 月あたり（年に±3ほど）
    common = np.cumsum(rng.normal(0, 1, T))
    Y = lvl[:, None] + slope[:, None] * t + common + rng.normal(0, 1.5, (J + 1, T))
    Y[0, T0:] += effect
    return Y


def did(tr, ct):
    d = tr - ct
    est = d[T0:].mean() - d[:T0].mean()
    p = stats.ttest_ind(d[T0:], d[:T0], equal_var=False).pvalue
    return est, p


def synth(Y):
    w, _ = nnls(Y[1:, :T0].T, Y[0, :T0]); w = w / w.sum() if w.sum() > 0 else np.full(J, 1 / J)
    return w @ Y[1:]


rows = []
for eff in [0.0, 5.0]:
    for r in range(R):
        Y = make(eff); tr = Y[0]
        one = Y[1 + rng.integers(J)]
        five = Y[1 + rng.choice(J, 5, replace=False)].mean(0)
        allc = Y[1:].mean(0)
        sc = synth(Y)
        for name, ct in [("1店", one), ("5店", five), ("全50店", allc), ("合成コントロール", sc)]:
            e, p = did(tr, ct); rows.append(dict(effect=eff, rep=r, method=name, est=e, p=p))
D = pd.DataFrame(rows)
D.to_csv(RES / "reps.csv", index=False, float_format="%.5f")
S = D.groupby(["effect", "method"], sort=False).agg(mean=("est", "mean"), sd=("est", "std"),
                                                     sig=("p", lambda s: (s < .05).mean()),
                                                     p5=("est", lambda s: s.quantile(.05)), p95=("est", lambda s: s.quantile(.95))).reset_index()
S.to_csv(RES / "summary.csv", index=False)
g = lambda e, m, k: float(S[(S.effect == e) & (S.method == m)][k].iloc[0])
M = ["1店", "5店", "全50店", "合成コントロール"]
out = {"control_pool": J, "months": T, "pre": T0, "reps": R,
       "effect0": {m: {k: round(g(0.0, m, k), 3) for k in ["mean", "sd", "sig", "p5", "p95"]} for m in M},
       "effect5": {m: {k: round(g(5.0, m, k), 3) for k in ["mean", "sd", "sig"]} for m in M},
       "sd_ratio_one_vs_all": g(0.0, "1店", "sd") / g(0.0, "全50店", "sd")}
json.dump(out, open(RES / "a776_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：効果0のときの推定の分布
fig, ax = plt.subplots(figsize=(9, 4.6))
bins = np.linspace(-15, 15, 61)
for m, c in zip(M, [ORANGE, GREEN, BLUE, GRAY]):
    ax.hist(D[(D.effect == 0) & (D.method == m)].est.clip(-15, 15), bins=bins, histtype="step", lw=2, color=c, label=f"{m}（標準偏差 {g(0.0, m, 'sd'):.1f}）")
ax.axvline(0, color="black", lw=1); ax.set_xlabel("効果の推定（本当は0）"); ax.set_ylabel("回数（1,000回）")
ax.legend(frameon=False, fontsize=9); ax.set_title("対照が1店だと、効果0でも推定が大きく振れる")
save(fig, "a776_hist.png", SRC)
# 図2：偽の有意
fig, ax = plt.subplots(figsize=(9, 4.6))
v = [g(0.0, m, "sig") * 100 for m in M]
b = ax.bar(M, v, color=[ORANGE, GREEN, BLUE, GRAY])
for bb, x in zip(b, v): ax.text(bb.get_x() + bb.get_width() / 2, x + 1, f"{x:.0f}%", ha="center")
ax.axhline(5, color="black", ls="--", lw=1); ax.text(3.45, 6, "5%", ha="right")
ax.set_ylabel("効果0なのに「有意」になった割合（%）"); ax.set_title("月ごとの差の t 検定は、対照の店の傾きを効果と取り違える")
save(fig, "a776_false.png", SRC)
# 図3：1回の例
Y = make(0.0); one_i = 1 + rng.integers(J)
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(t + 1, Y[0], "o-", color="black", ms=3, label="施策の店（効果0）")
ax.plot(t + 1, Y[one_i], "s-", color=ORANGE, ms=3, label="対照に選んだ1店")
ax.plot(t + 1, synth(Y), "-", color=GRAY, lw=2, label="合成コントロール")
ax.axvline(T0 + .5, color=GRAY, ls="--"); ax.text(T0 + .7, ax.get_ylim()[1], "施策の開始", va="top", fontsize=9)
e1, _ = did(Y[0], Y[one_i]); es, _ = did(Y[0], synth(Y))
ax.set_xlabel("月"); ax.set_ylabel("売上（架空の単位）"); ax.legend(frameon=False, fontsize=9)
ax.set_title(f"例：1店の対照では効果 {e1:+.1f}、合成コントロールでは {es:+.1f}（本当は0）")
save(fig, "a776_example.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
