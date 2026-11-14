"""758 件数が少ないとき、モデルの「上位10%のリフト」はどれだけ揺れるのか

架空の DM の反応（反応率は全体で2%か5%）。本当の反応のしやすさ z に対して、2つのモデルの点数を
  モデル A：z に小さな雑音、モデル B：z に大きめの雑音（本当のリフトは A のほうが高い）
とする。検証データの件数 n を 1,000〜30,000 と変え、各1,000回：
  上位10%のリフト（上位10%の反応率 ÷ 全体の反応率）の振れ、B が A を上回る割合、
  1回分のデータからのブートストラップ区間（500回）の幅を測る。本当のリフトは100万件で出す。seed 758。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 758）"
rng = np.random.default_rng(758)
NS = [1000, 3000, 10000, 30000]
REPS = 1000
SA, SB = 0.5, 0.8
RATES = {0.02: None, 0.05: None}


from scipy.stats import norm
from scipy.optimize import brentq
ZQ = norm.ppf((np.arange(20000) + 0.5) / 20000)
INTERCEPT = {b: brentq(lambda a: np.mean(1 / (1 + np.exp(-(a + 1.1 * ZQ)))) - b, -12, 2) for b in [0.02, 0.05]}


def make(n, base):
    z = rng.normal(0, 1, n)
    a = INTERCEPT[base]  # 全体の反応率が base になる切片
    p = 1 / (1 + np.exp(-(a + 1.1 * z)))
    y = rng.random(n) < p
    sa = z + rng.normal(0, SA, n); sb = z + rng.normal(0, SB, n)
    return y, sa, sb


def lift(y, s):
    k = len(y) // 10
    top = np.argpartition(-s, k)[:k]
    m = y.mean()
    return y[top].mean() / m if m > 0 else np.nan


rows = []; truth = {}
for base in RATES:
    y, sa, sb = make(1_000_000, base)
    truth[base] = (float(y.mean()), lift(y, sa), lift(y, sb))
    for n in NS:
        for r in range(REPS):
            y, sa, sb = make(n, base)
            rows.append((base, n, r, y.sum(), lift(y, sa), lift(y, sb)))
R = pd.DataFrame(rows, columns=["base", "n", "rep", "responders", "lift_A", "lift_B"])
S = R.groupby(["base", "n"]).agg(lift_A_mean=("lift_A", "mean"), lift_A_p05=("lift_A", lambda v: np.nanpercentile(v, 5)),
                                 lift_A_p95=("lift_A", lambda v: np.nanpercentile(v, 95)), lift_A_sd=("lift_A", "std"),
                                 B_wins_pct=("lift_A", lambda v: 0), responders=("responders", "mean")).reset_index()
S["B_wins_pct"] = [float(((g.lift_B > g.lift_A).mean()) * 100) for _, g in R.groupby(["base", "n"])]
S.round(3).to_csv(RES / "summary.csv", index=False)
# ブートストラップ（1回分、反応率2%、n=1,000 と 10,000）
boot = {}
for n in [1000, 10000]:
    y, sa, sb = make(n, 0.02)
    bl = []
    for b in range(500):
        i = rng.integers(0, n, n)
        bl.append(lift(y[i], sa[i]))
    boot[n] = (lift(y, sa), np.nanpercentile(bl, 2.5), np.nanpercentile(bl, 97.5), int(y.sum()))
g = lambda base, n, c: float(S[(S.base == base) & (S.n == n)][c].iloc[0])
out = {"reps": REPS, "n_list": NS,
       "true": {str(b): {"rate_pct": round(t[0] * 100, 2), "lift_A": round(t[1], 2), "lift_B": round(t[2], 2)} for b, t in truth.items()},
       "lift_A_90pct_range": {str(b): {str(n): [round(g(b, n, "lift_A_p05"), 2), round(g(b, n, "lift_A_p95"), 2)] for n in NS} for b in RATES},
       "lift_A_sd": {str(b): {str(n): round(g(b, n, "lift_A_sd"), 2) for n in NS} for b in RATES},
       "B_beats_A_pct": {str(b): {str(n): round(g(b, n, "B_wins_pct"), 1) for n in NS} for b in RATES},
       "responders_mean": {str(b): {str(n): round(g(b, n, "responders"), 0) for n in NS} for b in RATES},
       "bootstrap_one_sample_rate2pct": {str(n): {"lift": round(v[0], 2), "ci95": [round(v[1], 2), round(v[2], 2)], "responders": v[3]} for n, v in boot.items()}}
json.dump(out, open(RES / "a758_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：リフトの分布（反応率2%）
fig, ax = plt.subplots(figsize=(8.5, 3.8))
data = [R[(R.base == 0.02) & (R.n == n)].lift_A.dropna().values for n in NS]
bp = ax.boxplot(data, whis=(5, 95), showfliers=False, patch_artist=True, tick_labels=[f"{n:,}件\n（反応 約{int(g(0.02, n, 'responders'))}件）" for n in NS])
for b in bp["boxes"]: b.set_facecolor(LIGHT)
ax.axhline(truth[0.02][1], color=ORANGE, ls="--", lw=1.2); ax.text(4.35, truth[0.02][1], f"本当\n{truth[0.02][1]:.2f}", color=ORANGE, va="center", fontsize=9)
ax.set_ylabel("上位10%のリフト（モデル A）"); ax.set_xlabel("検証データの件数（反応率2%）")
lo_, hi_ = out["lift_A_90pct_range"]["0.02"]["1000"]
ax.set_title(f"1,000件（反応 約{int(g(0.02, 1000, 'responders'))}件）では、同じモデルのリフトが{lo_:.1f}〜{hi_:.1f}まで振れる（90%の範囲）")
save(fig, "a758_lift_spread.png", SRC, y=-0.07)
# 図2：B が A を上回る割合
fig, ax = plt.subplots(figsize=(7.5, 3.6))
for b, c in [(0.02, BLUE), (0.05, ORANGE)]:
    v = [g(b, n, "B_wins_pct") for n in NS]
    ax.plot(NS, v, marker="o", color=c, label=f"反応率{int(b * 100)}%")
    for n, val in zip(NS, v):
        ax.text(n, val + 1.2, f"{val:.0f}%", ha="center", fontsize=9, color=c)
ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels([f"{n:,}" for n in NS])
ax.set_xlabel("検証データの件数"); ax.set_ylabel("劣るモデル B が上回った割合（%）")
ax.legend(frameon=False); ax.set_title(f"本当のリフトは A {truth[0.02][1]:.2f}・B {truth[0.02][2]:.2f}。少ない件数では順位が入れ替わる")
save(fig, "a758_b_wins.png", SRC)
# 図3：1回分のデータのブートストラップ区間
fig, ax = plt.subplots(figsize=(7.5, 3.2))
for i, n in enumerate([1000, 10000]):
    L, lo, hi, resp = boot[n]
    ax.plot([lo, hi], [i, i], color=BLUE, lw=3); ax.plot(L, i, "o", color=BLUE)
    ax.text(hi + 0.05, i, f"{L:.2f}（{lo:.2f}〜{hi:.2f}）", va="center", fontsize=10)
ax.axvline(truth[0.02][1], color=ORANGE, ls="--"); ax.set_yticks([0, 1]); ax.set_yticklabels(["1,000件", "10,000件"])
ax.set_xlabel("上位10%のリフトと95%区間（ブートストラップ、反応率2%）"); ax.set_ylim(-0.6, 1.6)
ax.set_title("1回分のデータからも、区間を付ければ振れの大きさが分かる")
save(fig, "a758_bootstrap.png", SRC, y=-0.09)
print(json.dumps(out, ensure_ascii=False, indent=1))
