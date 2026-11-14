"""777 大きい店では有意・小さい店では有意でない、を「効き方が違う」と読むと、何%で誤るのか

架空の A/B テスト。施策の効き方（標準化した差 d）は大きい店でも小さい店でも同じ。
大きい店は1群 n_L 人、小さい店は1群 n_S 人。店の種類ごとに2群の t 検定をし、
「片方だけ有意（5%）」を「効き方が違う」と読む割合と、交互作用の検定（差の差の z 検定）で「違う」と出る割合を比べる。
d を 0〜0.4、各4,000回。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from common import RES, save, BLUE, ORANGE, GRAY, GREEN

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 777）"
rng = np.random.default_rng(777)
NL, NS, R = 400, 60, 4000
DS = [0.0, 0.1, 0.2, 0.3, 0.4]


def arm_stats(n, d):
    a = rng.standard_normal((R, n)); b = rng.standard_normal((R, n)) + d
    diff = b.mean(1) - a.mean(1); se = np.sqrt(a.var(1, ddof=1) / n + b.var(1, ddof=1) / n)
    p = 2 * stats.t.sf(np.abs(diff / se), 2 * n - 2)
    return diff, se, p


rows = []; keep = {}
for d in DS:
    dL, sL, pL = arm_stats(NL, d); dS, sS, pS = arm_stats(NS, d)
    sigL, sigS = pL < .05, pS < .05
    one_only = sigL ^ sigS
    z = (dL - dS) / np.sqrt(sL ** 2 + sS ** 2); inter = 2 * stats.norm.sf(np.abs(z)) < .05
    rows.append(dict(d=d, sig_large=sigL.mean(), sig_small=sigS.mean(), one_only=one_only.mean(),
                     large_only=(sigL & ~sigS).mean(), small_only=(sigS & ~sigL).mean(), interaction=inter.mean()))
    if d == 0.2: keep = dict(dL=dL[:300], sL=sL[:300], dS=dS[:300], sS=sS[:300])
S = pd.DataFrame(rows); S.to_csv(RES / "summary.csv", index=False)
g = lambda d, k: float(S[S.d == d][k].iloc[0])
out = {"n_large_per_arm": NL, "n_small_per_arm": NS, "reps": R,
       "by_d": {str(d): {k: round(g(d, k), 4) for k in S.columns[1:]} for d in DS},
       "d02_one_only": g(.2, "one_only"), "d02_interaction": g(.2, "interaction"),
       "d02_sig_large": g(.2, "sig_large"), "d02_sig_small": g(.2, "sig_small"),
       "max_one_only": float(S.one_only.max()), "max_one_only_d": float(S.d[S.one_only.idxmax()])}
json.dump(out, open(RES / "a777_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：「違う」と読む割合
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(S.d, S.one_only * 100, "o-", color=ORANGE, label="片方だけ有意 →「違う」と読む")
ax.plot(S.d, S.interaction * 100, "s-", color=BLUE, label="交互作用の検定で「違う」")
for a, b in zip(S.d, S.one_only * 100): ax.text(a, b + 2, f"{b:.0f}%", ha="center", fontsize=9, color=ORANGE)
ax.axhline(5, color=GRAY, ls="--", lw=1)
ax.set_xlabel("施策の効き方 d（大きい店も小さい店も同じ）"); ax.set_ylabel("「効き方が違う」とする割合（%）"); ax.set_ylim(0, 100)
ax.legend(frameon=False); ax.set_title(f"本当は同じでも、片方だけ有意で読むと最大{S.one_only.max():.0%}が「違う」になる")
save(fig, "a777_wrong_rate.png", SRC)
# 図2：それぞれの検出力
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(S.d, S.sig_large * 100, "o-", color=BLUE, label=f"大きい店（1群{NL}人）")
ax.plot(S.d, S.sig_small * 100, "o-", color=GREEN, label=f"小さい店（1群{NS}人）")
ax.set_xlabel("施策の効き方 d"); ax.set_ylabel("有意（5%）になる割合（%）"); ax.set_ylim(0, 105)
ax.legend(frameon=False); ax.set_title("有意になりやすさは、効き方ではなく人数で決まる")
save(fig, "a777_power.png", SRC)
# 図3：d=0.2 の推定と区間
fig, ax = plt.subplots(figsize=(9, 4.6)); i = np.arange(40)
ax.errorbar(i - .15, keep["dL"][:40], yerr=1.96 * keep["sL"][:40], fmt="o", ms=3, color=BLUE, label="大きい店")
ax.errorbar(i + .15, keep["dS"][:40], yerr=1.96 * keep["sS"][:40], fmt="o", ms=3, color=GREEN, label="小さい店")
ax.axhline(.2, color="black", lw=1); ax.axhline(0, color=GRAY, ls="--", lw=1)
ax.set_xlabel("くり返しの回（40回分）"); ax.set_ylabel("差の推定と95%区間")
ax.legend(frameon=False); ax.set_title("d=0.2：小さい店は区間が広く0をまたぐが、推定の中心は同じ0.2")
save(fig, "a777_intervals.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
