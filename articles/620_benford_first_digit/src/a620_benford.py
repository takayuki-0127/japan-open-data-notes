"""620 取引の金額の先頭の数字は、ベンフォードの法則にどれだけ従い、入力の偏りをどこまで見つけられるのか

ベンフォードの法則：桁をまたいで広く散らばる数では、先頭の数字が d になる割合は log10(1+1/d)（1 が 30.1%、9 が 4.6%）。
架空の取引金額を作る。
  自然な金額：対数正規（中央値 1万円、対数の標準偏差 σ）。σ を 0.3〜2.0 と変えて、どこまで法則に従うかを見る
  手で作った金額：1,000〜9,999円の一様（先頭の数字はほぼ均等）
自然な金額（σ=1.5）に手で作った金額を 0〜20% 混ぜ、件数 500・2,000・10,000 で、
  カイ二乗の適合度検定（p<0.05）と MAD（各数字の割合と法則の差の絶対値の平均、0.015 を超えたら「合わない」）で
  「合わない」と出る割合を 500 回ずつ数える。数字は置いた金額の分布で決まる。不正の有無を判定するものではない。
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の取引金額（作成者が乱数で作成、seed 620）"
rng = np.random.default_rng(620)
D = np.arange(1, 10)
BEN = np.log10(1 + 1 / D)
MAD_LIMIT = 0.015


def first_digit(x):
    x = np.floor(x).astype(np.int64)
    x = x[x > 0]
    return (x // 10 ** np.floor(np.log10(x)).astype(np.int64)).astype(int)


def shares(fd):
    c = np.bincount(fd, minlength=10)[1:]
    return c, c / c.sum()


def natural(n, sigma, rng):
    return np.exp(rng.normal(np.log(10000), sigma, n))


def made(n, rng):
    return rng.integers(1000, 10000, n).astype(float)


def test(x):
    c, s = shares(first_digit(x))
    p = stats.chisquare(c, BEN * c.sum()).pvalue
    mad = np.abs(s - BEN).mean()
    return p, mad


# 1) 大きな標本での先頭の数字
BIG = 200_000
dist = {"benford": BEN}
for name, x in [("natural_1.5", natural(BIG, 1.5, rng)), ("made", made(BIG, rng)), ("natural_0.3", natural(BIG, 0.3, rng))]:
    dist[name] = shares(first_digit(x))[1]
pd.DataFrame(dist, index=D).round(4).to_csv(RES / "first_digit_shares.csv")

# 2) σ ごとの MAD（自然な金額だけ）
SIG = [0.3, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
sig_rows = []
for s in SIG:
    p, mad = test(natural(BIG, s, rng))
    sig_rows.append({"sigma": s, "mad": mad, "range_p05_p95": f"{np.exp(np.log(1e4)-1.645*s):,.0f}〜{np.exp(np.log(1e4)+1.645*s):,.0f}"})
sig = pd.DataFrame(sig_rows)
sig.round(4).to_csv(RES / "mad_by_sigma.csv", index=False)

# 3) 混ぜた割合と件数ごとの「合わない」と出る割合
FR = [0, 0.01, 0.02, 0.05, 0.10, 0.20]
NS = [500, 2000, 10000]
REPS = 500
det = []
for n in NS:
    for f in FR:
        hit_c = hit_m = 0
        for r in range(REPS):
            k = int(round(n * f))
            x = np.concatenate([natural(n - k, 1.5, rng), made(k, rng)])
            p, mad = test(x)
            hit_c += p < 0.05; hit_m += mad > MAD_LIMIT
        det.append({"n": n, "frac": f, "chi2_flag_pct": 100 * hit_c / REPS, "mad_flag_pct": 100 * hit_m / REPS})
det = pd.DataFrame(det)
det.to_csv(RES / "detection.csv", index=False)
det.to_csv(RES / "summary.csv", index=False)
out = {"benford": dict(zip(D.tolist(), BEN.round(4).tolist())), "shares": {k: dict(zip(D.tolist(), np.round(v, 4).tolist())) for k, v in dist.items()},
       "mad_by_sigma": sig.round(4).to_dict(orient="records"), "detection": det.to_dict(orient="records"), "reps": REPS, "mad_limit": MAD_LIMIT}
json.dump(out, open(RES / "a620_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：先頭の数字の割合
fig, ax = plt.subplots(figsize=(9, 4.2))
w = 0.27
ax.bar(D - w, dist["natural_1.5"] * 100, w, color=BLUE, label="自然な金額（広く散らばる、σ=1.5）")
ax.bar(D, dist["made"] * 100, w, color=ORANGE, label="手で作った金額（1,000〜9,999円の一様）")
ax.bar(D + w, dist["natural_0.3"] * 100, w, color=LIGHT, label="自然な金額（狭い範囲、σ=0.3）")
ax.plot(D, BEN * 100, color=INK, marker="o", lw=1, label="ベンフォードの法則")
ax.set_xticks(D); ax.set_xlabel("先頭の数字"); ax.set_ylabel("割合（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("先頭の数字の割合：広く散らばる金額だけが法則に近い")
save(fig, "a620_first_digit.png", SRC)

# 図2：混ぜた割合ごとの検出
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"wspace": 0.25})
for i, (col, tt) in enumerate([("chi2_flag_pct", "カイ二乗の適合度検定（p<0.05）"), ("mad_flag_pct", "MAD が 0.015 を超える")]):
    for n, c in zip(NS, [LIGHT, BLUE, ORANGE]):
        s = det[det.n == n]
        ax[i].plot(s.frac * 100, s[col], marker="o", color=c, label=f"{n:,}件")
    ax[i].set_title(tt); ax[i].set_xlabel("手で作った金額を混ぜた割合（%）"); ax[i].set_ylim(-3, 103)
ax[0].set_ylabel("「合わない」と出た回の割合（%）"); ax[0].legend(frameon=False, fontsize=9)
save(fig, "a620_detection.png", SRC, y=-0.04)

# 図3：σ ごとの MAD
fig, ax = plt.subplots(figsize=(8.5, 4))
ax.plot(sig.sigma, sig.mad, marker="o", color=BLUE)
ax.axhline(MAD_LIMIT, color=ORANGE, ls="--", label="「合わない」の目安 0.015")
for s, m, r in zip(sig.sigma, sig.mad, sig.range_p05_p95):
    ax.text(s, m + 0.004, f"{m:.3f}", ha="center", fontsize=8.5)
ax.set_xlabel("自然な金額の散らばり（対数の標準偏差 σ）"); ax.set_ylabel("MAD（法則とのずれ）")
ax.set_title("作り手の手の入らない自然な金額でも、範囲が狭いと法則に合わない"); ax.legend(frameon=False, fontsize=9)
save(fig, "a620_mad_by_sigma.png", SRC)
print(sig.round(4)); print(det); print(pd.DataFrame(dist, index=D).round(3))
