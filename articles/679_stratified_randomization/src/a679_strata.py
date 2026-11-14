"""679 層別に割り付けると、単純な無作為の割り付けよりも効果の推定のばらつきはどれだけ小さくなるのか

架空の店 40店。大きさで3つの層：大 8店・中 16店・小 16店。
  場面A（大きさの差が大きい）：テスト期間の売上の平均は 大 3,000万円・中 1,000万円・小 300万円
  場面B（大きさの差が小さい）：大 1,200万円・中 1,000万円・小 800万円
各店の売上は、層の平均に ±15%（標準偏差）の振れを掛けたもの。施策は各店の売上を本当に 5% 上げる。
本当の効果＝施策の店1店あたりの平均の上がり幅（40店の売上×5%の平均）。
割り付けは 20店ずつ。3つの方法を比べる：
  単純：40店から無作為に20店
  層別：各層の半分（大4・中8・小8）を無作為に
  単純＋層で調整：単純に割り付けたあと、層の違いを回帰（層のダミー）で調整
推定は施策の店と対照の店の売上の平均の差（調整は回帰の係数）。各 5,000 回。数字は置いた売上で決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の店の売上（作成者が乱数で作成、seed 679）"
rng = np.random.default_rng(679)
REPS, NOISE, EFF = 5000, 0.15, 0.05
SIZES = {"大": 8, "中": 16, "小": 16}
SCEN = {"A": {"大": 3000, "中": 1000, "小": 300}, "B": {"大": 1200, "中": 1000, "小": 800}}
METHODS = ["単純", "層別", "単純＋層で調整"]
COL = {"単純": GRAY, "層別": BLUE, "単純＋層で調整": GREEN}
strata = np.repeat(np.arange(3), list(SIZES.values()))
NS = len(strata)
D = np.stack([(strata == j).astype(float) for j in range(3)], 1)   # 層のダミー


def assign_simple():
    t = np.zeros(NS, bool); t[rng.choice(NS, NS // 2, replace=False)] = True
    return t


def assign_strat():
    t = np.zeros(NS, bool)
    for j in range(3):
        idx = np.where(strata == j)[0]; t[rng.choice(idx, len(idx) // 2, replace=False)] = True
    return t


def adjust(y, t):
    Xm = np.column_stack([t.astype(float), D])
    return np.linalg.lstsq(Xm, y, rcond=None)[0][0]


rows = []; keep = {}
for sc, means in SCEN.items():
    mu = np.array([means[k] for k in SIZES])[strata]
    est = {m: np.empty(REPS) for m in METHODS}; truth = np.empty(REPS); n_big = np.empty(REPS, int)
    for r in range(REPS):
        y0 = mu * (1 + NOISE * rng.standard_normal(NS)); y1 = y0 * (1 + EFF)
        truth[r] = (y1 - y0).mean()
        t = assign_simple(); y = np.where(t, y1, y0)
        est["単純"][r] = y[t].mean() - y[~t].mean()
        est["単純＋層で調整"][r] = adjust(y, t)
        n_big[r] = t[strata == 0].sum()
        ts = assign_strat(); ys = np.where(ts, y1, y0)
        est["層別"][r] = ys[ts].mean() - ys[~ts].mean()
    for m in METHODS:
        err = est[m] - truth
        rows.append(dict(scene=sc, method=m, truth_mean=truth.mean(), est_mean=est[m].mean(), bias=err.mean(),
                         sd=err.std(), p_wrong_sign=100 * np.mean(est[m] < 0),
                         p_far=100 * np.mean(np.abs(err) > truth.mean())))
    keep[sc] = dict(est=est, truth=truth, n_big=n_big)
S = pd.DataFrame(rows)
S.round(3).to_csv(RES / "summary.csv", index=False)

kA = keep["A"]; errA = kA["est"]["単純"] - kA["truth"]
B = pd.DataFrame({"n_big": kA["n_big"], "err": errA}).groupby("n_big").err.agg(["mean", "std", "size"]).reset_index()
B.round(2).to_csv(RES / "simple_by_big_count.csv", index=False)


def g(sc, m, c, nd=1):
    return round(float(S[(S.scene == sc) & (S.method == m)][c].iloc[0]), nd)


out = {"stores": NS, "reps": REPS, "effect": EFF, "noise": NOISE,
       "truth_mean": {sc: round(float(keep[sc]["truth"].mean()), 1) for sc in SCEN},
       "sd": {sc: {m: g(sc, m, "sd") for m in METHODS} for sc in SCEN},
       "bias": {sc: {m: g(sc, m, "bias", 2) for m in METHODS} for sc in SCEN},
       "p_wrong_sign": {sc: {m: g(sc, m, "p_wrong_sign") for m in METHODS} for sc in SCEN},
       "p_far": {sc: {m: g(sc, m, "p_far") for m in METHODS} for sc in SCEN},
       "sd_ratio_strat_vs_simple": {sc: round(g(sc, "層別", "sd", 3) / g(sc, "単純", "sd", 3), 3) for sc in SCEN},
       "simple_A_by_big": {int(r.n_big): {"mean_err": round(float(r["mean"]), 1), "n": int(r["size"])} for _, r in B.iterrows()},
       "simple_A_big_imbalanced_pct": round(100 * float(np.mean(np.abs(kA["n_big"] - 4) >= 2)), 1)}
json.dump(out, open(RES / "a679_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：場面Aの推定の分布
fig, ax = plt.subplots(figsize=(9, 4.6))
tm = kA["truth"].mean()
bins = np.linspace(-1500, 1700, 129)
for m in METHODS:
    ax.hist(kA["est"][m], bins=bins, histtype="step", lw=2, color=COL[m], label=f"{m}（標準偏差 {g('A', m, 'sd'):.0f}万円）")
ax.axvline(tm, color=INK, lw=1.2, ls="--"); ax.text(tm + 30, ax.get_ylim()[1] * .92, f"本当の効果 {tm:.0f}万円", fontsize=10)
ax.axvline(0, color=GRAY, lw=.8)
ax.set_xlabel("推定した効果（1店あたりの売上の差、万円）"); ax.set_ylabel("回数（5,000回のうち）")
ax.set_title("店の大きさの差が大きいとき、単純な割り付けの推定は大きく振れる")
ax.legend(frameon=False, loc="upper left", fontsize=9)
save(fig, "a679_estimates.png", SRC)

# 図2：単純な割り付けで、大の店が施策側に何店入ったかと、推定のずれ
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.bar(B.n_big, B["mean"], color=[ORANGE if abs(v - 4) >= 2 else LIGHT for v in B.n_big], width=.7)
for _, r in B.iterrows():
    ax.text(r.n_big, r["mean"] + (40 if r["mean"] >= 0 else -40), f"{r['mean']:+.0f}\n（{int(r['size'])}回）",
            ha="center", va="bottom" if r["mean"] >= 0 else "top", fontsize=8.5)
ax.axhline(0, color=INK, lw=.8)
ax.set_xticks(range(9)); ax.set_xlabel("施策側に入った「大」の店の数（8店のうち。層別なら必ず4）")
ax.set_ylabel("推定のずれの平均（万円）"); ax.set_ylim(-1800, 1800)
ax.set_title(f"単純な割り付け：大の店の入り方で、推定が丸ごとずれる（本当の効果 {tm:.0f}万円）")
save(fig, "a679_by_big_count.png", SRC)

# 図3：標準偏差
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
for ax, sc, ttl in [(axes[0], "A", "場面A：大きさの差が大きい"), (axes[1], "B", "場面B：大きさの差が小さい")]:
    vals = [g(sc, m, "sd") for m in METHODS]
    bars = ax.bar(range(3), vals, color=[COL[m] for m in METHODS], width=.6)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.02, f"{v:.0f}", ha="center", fontsize=9.5)
    ax.set_xticks(range(3)); ax.set_xticklabels(METHODS, fontsize=9.5); ax.set_title(ttl, fontsize=11)
    ax.set_ylim(0, max(vals) * 1.18)
    ax.text(2.4, max(vals) * 1.1, f"本当の効果 {keep[sc]['truth'].mean():.0f}万円", ha="right", fontsize=9)
axes[0].set_ylabel("推定のずれの標準偏差（万円）")
fig.suptitle("層別に割り付ける（または層で調整する）と、ばらつきが小さくなる", fontsize=12)
save(fig, "a679_sd.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
