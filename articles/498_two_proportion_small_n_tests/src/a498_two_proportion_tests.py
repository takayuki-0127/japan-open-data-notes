"""A498 件数が少ないとき、2つの割合の差の検定は、効果が0でも何%で「差あり」と出るのか
乱数は使わず、2群の起こりうる結果をすべて数え上げて正確な確率を出す（架空の設定）"""
import json
import numpy as np
import pandas as pd
from scipy import stats
from common import plt, save, DATA, RES, BLUE, ORANGE, GRAY, GREEN, INK

SRC = "架空の2群の設定（作成者が式で計算、乱数なし）"
ALPHA = 0.05


def pvals(n1, n2):
    """2群の「起きた件数」(a, b) の全組み合わせについて、4つの検定の p 値を返す"""
    out = {k: np.ones((n1 + 1, n2 + 1)) for k in ("z", "yates", "fisher", "midp")}
    N = n1 + n2
    for a in range(n1 + 1):
        for b in range(n2 + 1):
            k = a + b
            if k == 0 or k == N:
                continue                                     # どちらも全部0か全部1：差は計算できない（差なしとする）
            p1, p2, p = a / n1, b / n2, k / N
            se = np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
            z = (p1 - p2) / se
            out["z"][a, b] = 2 * stats.norm.sf(abs(z))     # カイ二乗（補正なし）と同じ
            d = abs(p1 - p2) - 0.5 * (1 / n1 + 1 / n2)      # イェーツの補正
            out["yates"][a, b] = 1.0 if d <= 0 else 2 * stats.norm.sf(d / se)
            hg = stats.hypergeom(N, n1, k)                  # フィッシャーの正確検定（両側、確率が小さい順に足す）
            pr = hg.pmf(np.arange(max(0, k - n2), min(k, n1) + 1))
            pa = hg.pmf(a)
            out["fisher"][a, b] = min(1.0, pr[pr <= pa * (1 + 1e-7)].sum())
            out["midp"][a, b] = min(1.0, pr[pr < pa * (1 - 1e-7)].sum() + 0.5 * pr[np.abs(pr - pa) <= pa * 1e-7].sum())
    return out


def reject_rate(n1, n2, q1, q2, P):
    w = np.outer(stats.binom.pmf(np.arange(n1 + 1), n1, q1), stats.binom.pmf(np.arange(n2 + 1), n2, q2))
    return {k: float((w * (v < ALPHA)).sum()) for k, v in P.items()}


NAMES = {"z": "カイ二乗（補正なし）", "yates": "カイ二乗（イェーツの補正）", "fisher": "フィッシャーの正確検定", "midp": "フィッシャー（mid-p）"}
rows = []
cache = {}
for n in (10, 20, 30, 50, 100, 200):
    P = cache.setdefault(n, pvals(n, n))
    for q in (0.02, 0.05, 0.1, 0.2, 0.3, 0.5):
        r0 = reject_rate(n, n, q, q, P)                       # 本当は差がない：空振りの割合
        q2 = min(0.99, q + 0.2)
        r1 = reject_rate(n, n, q, q2, P)                      # 本当は +20ポイント：見つける割合
        rows.append(dict(n=n, q=q, **{f"false_{k}": v for k, v in r0.items()}, q_alt=q2, **{f"power_{k}": v for k, v in r1.items()}))
df = pd.DataFrame(rows)
df.to_csv(RES / "rates_by_n_and_p.csv", index=False, float_format="%.4f")

# 割合を細かく動かした空振りの線（n=20, 50）
fine = []
for n in (20, 50):
    P = cache[n]
    for q in np.round(np.arange(0.01, 0.991, 0.01), 2):
        fine.append(dict(n=n, q=q, **reject_rate(n, n, q, q, P)))
fine = pd.DataFrame(fine); fine.to_csv(RES / "false_rate_fine_grid.csv", index=False, float_format="%.4f")
# 片側の群だけ件数が少ない場合
uneq = []
for n1, n2 in ((10, 100), (20, 200), (50, 50)):
    P = pvals(n1, n2)
    for q in (0.05, 0.1, 0.3):
        uneq.append(dict(n1=n1, n2=n2, q=q, **reject_rate(n1, n2, q, q, P)))
uneq = pd.DataFrame(uneq); uneq.to_csv(RES / "false_rate_unequal_n.csv", index=False, float_format="%.4f")

# 数え上げの例：n=20 の全 441 通りと、どの検定で「差あり」か
P = cache[20]
ex = [dict(a=a, b=b, **{k: P[k][a, b] for k in P}) for a in range(21) for b in range(21)]
pd.DataFrame(ex).to_csv(DATA / "pvalues_all_outcomes_n20.csv", index=False, float_format="%.5f")

col = {"z": ORANGE, "yates": GREEN, "fisher": BLUE, "midp": INK}
# --- 図1：割合ごとの空振り（n=20, 50）
fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
for a, n in zip(ax, (20, 50)):
    s = fine[fine.n == n]
    for k, c in col.items():
        a.plot(s.q * 100, s[k] * 100, color=c, label=NAMES[k], lw=1.6)
    a.axhline(5, color=GRAY, ls="--", lw=1); a.set_title(f"各群 {n} 件、本当は差がない"); a.set_xlabel("起きる割合（%、2群とも同じ）")
ax[0].set_ylabel("「差あり」と出た割合（%）"); ax[0].legend(frameon=False, fontsize=8.5)
save(fig, "a498_false_by_p.png", "出典：" + SRC)

# --- 図2：件数ごとの空振り（割合5%と30%）
fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
for a, q in zip(ax, (0.05, 0.3)):
    s = df[df.q == q]
    for k, c in col.items():
        a.plot(s.n, s[f"false_{k}"] * 100, "o-", color=c, label=NAMES[k])
    a.axhline(5, color=GRAY, ls="--", lw=1); a.set_xscale("log"); a.set_xticks([10, 20, 50, 100, 200]); a.set_xticklabels([10, 20, 50, 100, 200])
    a.set_title(f"起きる割合 {int(q*100)}%、本当は差がない"); a.set_xlabel("各群の件数")
ax[0].set_ylabel("「差あり」と出た割合（%）"); ax[1].legend(frameon=False, fontsize=8.5)
save(fig, "a498_false_by_n.png", "出典：" + SRC)

# --- 図3：本当に +20ポイントの差があるとき見つける割合
fig, ax = plt.subplots(figsize=(8, 4.2))
s = df[df.q == 0.1]
for k, c in col.items():
    ax.plot(s.n, s[f"power_{k}"] * 100, "o-", color=c, label=NAMES[k])
ax.set_xscale("log"); ax.set_xticks([10, 20, 50, 100, 200]); ax.set_xticklabels([10, 20, 50, 100, 200])
ax.set_xlabel("各群の件数"); ax.set_ylabel("差を見つけた割合（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("10% と 30% の差（本当に +20ポイント）を見つける割合")
save(fig, "a498_power.png", "出典：" + SRC)

g = lambda n, q: df[(df.n == n) & (df.q == q)].iloc[0].to_dict()
main = {f"n{n}_q{q}": g(n, q) for n in (10, 20, 50, 100) for q in (0.05, 0.1, 0.3, 0.5)}
for n in (20, 50):
    s = fine[fine.n == n]
    main[f"fine_n{n}"] = {k: dict(max=float(s[k].max()), at=float(s.q[s[k].idxmax()]), share_over_5=float((s[k] > 0.05).mean()),
                                   mean=float(s[k].mean())) for k in col}
main["unequal"] = uneq.to_dict("records")
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
print(df.round(3).to_string()); print(json.dumps({k: main[k] for k in ("fine_n20", "fine_n50")}, indent=1)); print(uneq.round(3))
