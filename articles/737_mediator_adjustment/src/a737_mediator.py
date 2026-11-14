"""737 施策の効き道になる変数を回帰に入れると、施策の効果はどれだけ小さく出るのか

架空の店の会員1,000人。施策（クーポン）を無作為に半分へ配る。
  来店回数 M = 2.0 × 施策 × s + 誤差
  売上 Y = 直接の効果 + 1.0 × 来店回数 + 誤差
全体の効果（売上の差）は10千円に固定し、そのうち来店回数を通る割合 s を 0〜100% で変える。
回帰は2通り：売上 ~ 施策（全体の効果）、売上 ~ 施策 ＋ 来店回数（直接の効果だけが残る）。
さらに、来店回数と売上の両方に効く見えない要因 U（店までの近さなど）があるとき、来店回数を入れた推定がどうずれるかも見る。
各条件1,000回。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 737）"
rng = np.random.default_rng(737)
N, R, TOTAL = 1000, 1000, 10.0


def ols(X, y):
    return np.linalg.lstsq(X, y, rcond=None)[0]


def sim(share, u_strength=0.0):
    T = (rng.random(N) < .5).astype(float)
    U = rng.standard_normal(N)
    a = TOTAL * share                       # 来店回数を通る分（来店1回＝1千円）
    M = a * T + u_strength * U + rng.standard_normal(N) * 3
    Y = TOTAL * (1 - share) * T + 1.0 * M + u_strength * 2 * U + rng.standard_normal(N) * 10
    one = np.ones(N)
    tot = ols(np.column_stack([one, T]), Y)[1]
    dirc = ols(np.column_stack([one, T, M]), Y)[1]
    return tot, dirc


rows = []
SH = [0, .25, .5, .75, 1.0]
for s in SH:
    r = np.array([sim(s) for _ in range(R)])
    rows.append(dict(share=s, true_total=TOTAL, true_direct=TOTAL * (1 - s), est_total=r[:, 0].mean(), est_direct=r[:, 1].mean(),
                     direct_p05=np.quantile(r[:, 1], .05), direct_p95=np.quantile(r[:, 1], .95),
                     total_p05=np.quantile(r[:, 0], .05), total_p95=np.quantile(r[:, 0], .95)))
S = pd.DataFrame(rows); S.to_csv(RES / "by_share.csv", index=False)

rows2 = []
for u in [0, 1, 2, 3, 4]:
    r = np.array([sim(.5, u) for _ in range(R)])
    rows2.append(dict(u_strength=u, true_direct=5.0, est_direct=r[:, 1].mean(), est_total=r[:, 0].mean(),
                      p05=np.quantile(r[:, 1], .05), p95=np.quantile(r[:, 1], .95)))
U = pd.DataFrame(rows2); U.to_csv(RES / "by_confounder.csv", index=False)

# 1回分の分布（通る割合50%）
r50 = np.array([sim(.5) for _ in range(R)])
out = {"members": N, "reps": R, "true_total": TOTAL,
       "by_share": {f"{s:.2f}": {"total": round(float(S.est_total[i]), 2), "with_mediator": round(float(S.est_direct[i]), 2)} for i, s in enumerate(SH)},
       "share50_total": float(S.est_total[2]), "share50_with_mediator": float(S.est_direct[2]),
       "share100_with_mediator": float(S.est_direct[4]),
       "share50_with_mediator_p05_p95": [float(S.direct_p05[2]), float(S.direct_p95[2])],
       "by_confounder": {int(u): round(float(v), 2) for u, v in zip(U.u_strength, U.est_direct)},
       "confounder4_with_mediator": float(U.est_direct.iloc[-1]), "confounder4_total": float(U.est_total.iloc[-1])}
json.dump(out, open(RES / "a737_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：通る割合と推定
fig, ax = plt.subplots(figsize=(9, 4.6))
x = S.share * 100
ax.plot(x, S.est_total, "o-", color=BLUE, label="来店回数を入れない（全体の効果）")
ax.plot(x, S.est_direct, "o-", color=ORANGE, label="来店回数を入れる")
ax.fill_between(x, S.direct_p05, S.direct_p95, color=ORANGE, alpha=.15)
ax.axhline(TOTAL, color=GRAY, ls="--", lw=1); ax.text(2, TOTAL + .3, "本当の全体の効果 10千円", color=GRAY, fontsize=9)
ax.set_xlabel("効果のうち、来店回数を通る割合（%）"); ax.set_ylabel("施策の係数（千円）"); ax.legend(frameon=False, loc="lower left")
ax.set_title("効き道の変数を入れると、通る分だけ施策の効果が消える（各1,000回、帯は90%）")
save(fig, "a737_by_share.png", SRC)

# 図2：通る割合50%の1,000回の分布
fig, ax = plt.subplots(figsize=(9, 4.6))
bins = np.linspace(-2, 18, 61)
ax.hist(r50[:, 0], bins=bins, color=BLUE, alpha=.7, label="来店回数を入れない")
ax.hist(r50[:, 1], bins=bins, color=ORANGE, alpha=.7, label="来店回数を入れる")
ax.axvline(10, color=BLUE, ls="--"); ax.axvline(5, color=ORANGE, ls="--")
ax.set_xlabel("施策の係数（千円）"); ax.set_ylabel("回数"); ax.legend(frameon=False)
ax.set_title("半分が来店回数を通るとき：入れないと約10、入れると約5（1,000回）")
save(fig, "a737_hist.png", SRC)

# 図3：見えない要因があるとき
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(U.u_strength, U.est_direct, "o-", color=ORANGE, label="来店回数を入れた推定")
ax.fill_between(U.u_strength, U.p05, U.p95, color=ORANGE, alpha=.15)
ax.plot(U.u_strength, U.est_total, "o-", color=BLUE, label="入れない推定（全体の効果）")
ax.axhline(5, color=GRAY, ls="--", lw=1); ax.text(0, 5.3, "本当の直接の効果 5千円", color=GRAY, fontsize=9)
ax.set_xlabel("来店回数と売上の両方に効く見えない要因の強さ"); ax.set_ylabel("施策の係数（千円）"); ax.legend(frameon=False)
ax.set_title("見えない要因があると、「直接の効果」としても読めなくなる（通る割合50%）")
save(fig, "a737_confounder.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
