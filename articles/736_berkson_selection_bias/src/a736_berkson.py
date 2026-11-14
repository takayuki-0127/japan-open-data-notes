"""736 「新しさ」と「手堅さ」のどちらかが高い企画だけ通る審査では、通った企画の中で2つはどれだけ逆の関係に見えるのか

架空の企画。新しさと手堅さの点は、どちらも平均0・標準偏差1の正規分布で、本当は無関係（相関0）。
通し方は2通り：
  合計で通す：新しさ＋手堅さ が上位 q%
  どちらかで通す：新しさ か 手堅さ のどちらかが基準を超える（通る割合が q% になる基準）
通る割合 q を 5〜100% で変え、通った企画の中の相関を見る。
1回の審査は応募2,000件。各条件500回くり返す。
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 736）"
rng = np.random.default_rng(736)
N, R = 2000, 500
QS = [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]


def select(a, b, q, rule):
    if q >= 1:
        return np.ones(len(a), bool)
    if rule == "sum":
        s = a + b; return s >= np.quantile(s, 1 - q)
    m = np.maximum(a, b); return m >= np.quantile(m, 1 - q)


rows = []
for rule in ["sum", "either"]:
    for q in QS:
        rs = []
        for r in range(R):
            a, b = rng.standard_normal(N), rng.standard_normal(N)
            k = select(a, b, q, rule)
            rs.append(np.corrcoef(a[k], b[k])[0, 1])
        rs = np.array(rs)
        rows.append(dict(rule=rule, pass_rate=q, n_pass=int(round(N * q)), corr_mean=float(rs.mean()),
                         corr_p05=float(np.quantile(rs, .05)), corr_p95=float(np.quantile(rs, .95))))
S = pd.DataFrame(rows); S.to_csv(RES / "summary.csv", index=False)

# 通った件数ごとに、「有意な負の相関」と言ってしまう割合（合計で通す、通過20%）
det = []
for n_app in [50, 100, 200, 500, 1000]:
    hit = 0
    for r in range(R):
        a, b = rng.standard_normal(n_app), rng.standard_normal(n_app)
        k = select(a, b, 0.2, "sum")
        rr, p = stats.pearsonr(a[k], b[k])
        hit += (p < 0.05) and (rr < 0)
    det.append(dict(applications=n_app, n_pass=int(round(n_app * .2)), sig_negative=hit / R))
Dt = pd.DataFrame(det); Dt.to_csv(RES / "detect_by_n.csv", index=False)

# 1回分の例（合計で通す、通過20%）
a, b = rng.standard_normal(N), rng.standard_normal(N); k = select(a, b, 0.2, "sum")
ex = dict(all=float(np.corrcoef(a, b)[0, 1]), passed=float(np.corrcoef(a[k], b[k])[0, 1]), n_pass=int(k.sum()))
g = lambda rule, q: S[(S.rule == rule) & (S.pass_rate == q)].iloc[0]
out = {"applications": N, "reps": R, "example_sum20": ex,
       "sum": {f"{q:.2f}": round(float(g('sum', q).corr_mean), 3) for q in QS},
       "either": {f"{q:.2f}": round(float(g('either', q).corr_mean), 3) for q in QS},
       "sum20_mean": float(g("sum", .2).corr_mean), "sum5_mean": float(g("sum", .05).corr_mean),
       "either20_mean": float(g("either", .2).corr_mean), "sum50_mean": float(g("sum", .5).corr_mean),
       "detect_by_n": det}
json.dump(out, open(RES / "a736_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：1回分の散布図
fig, ax = plt.subplots(figsize=(7.5, 6))
ax.scatter(a[~k], b[~k], s=6, color=LIGHT, label="通らなかった企画")
ax.scatter(a[k], b[k], s=8, color=ORANGE, label=f"通った企画（{k.sum()}件）")
for x, y, c in [(a, b, GRAY), (a[k], b[k], ORANGE)]:
    p = np.polyfit(x, y, 1); xs = np.linspace(x.min(), x.max(), 10); ax.plot(xs, np.polyval(p, xs), color=c, lw=2)
ax.set_xlabel("新しさの点"); ax.set_ylabel("手堅さの点"); ax.legend(frameon=False, loc="lower left")
ax.set_title(f"全体の相関 {ex['all']:+.2f}、通った企画だけでは {ex['passed']:+.2f}（合計の上位20%）")
save(fig, "a736_scatter.png", SRC)

# 図2：通る割合と相関
fig, ax = plt.subplots(figsize=(9, 4.6))
for rule, lab, c in [("sum", "合計で通す", ORANGE), ("either", "どちらかが高ければ通す", BLUE)]:
    d = S[S.rule == rule]
    ax.fill_between(d.pass_rate * 100, d.corr_p05, d.corr_p95, color=c, alpha=.15)
    ax.plot(d.pass_rate * 100, d.corr_mean, "o-", color=c, label=lab)
ax.axhline(0, color=GRAY, lw=1); ax.set_xlabel("通る割合（%）"); ax.set_ylabel("通った企画の中の相関")
ax.legend(frameon=False); ax.set_title("本当は無関係でも、厳しく選ぶほど強い負の相関に見える（各500回、帯は90%）")
save(fig, "a736_by_rate.png", SRC)

# 図3：件数と「有意な負の相関」の割合
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.bar([str(n) for n in Dt.applications], Dt.sig_negative * 100, color=ORANGE)
for i, v in enumerate(Dt.sig_negative):
    ax.text(i, v * 100 + 2, f"{v * 100:.0f}%", ha="center")
ax.set_xlabel("応募の件数（通るのはその20%）"); ax.set_ylabel("有意な負の相関が出た割合（%）"); ax.set_ylim(0, 112)
ax.set_title("応募が多いほど、ないはずの関係が「有意」になる（合計の上位20%、各500回）")
save(fig, "a736_detect.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
