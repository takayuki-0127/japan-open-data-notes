"""756 ブートストラップの回数を100回・1,000回・10,000回と変えると、95%区間の端はどれだけ揺れるのか

架空の客単価50件（対数正規分布、右に長い）。同じ50件に対して、ブートストラップ（パーセンタイル法）の
回数 B を 100・1,000・10,000 と変え、それぞれ乱数を変えて100回やり直す。
  区間の端（2.5%点・97.5%点）の振れ、区間の幅に対する振れの割合を、平均と中央値で比べる。
あわせて、データを作り直して（600回）、区間が本当の平均・中央値を含む割合を B ごとに数える。seed 756。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 756）"
rng = np.random.default_rng(756)
N, MU, SIG = 50, 8.0, 0.7
BS = [100, 1000, 10000]
REDO = 100
true_mean = np.exp(MU + SIG ** 2 / 2); true_median = np.exp(MU)
x = rng.lognormal(MU, SIG, N)


def boot_ci(data, B, stat):
    idx = rng.integers(0, len(data), (B, len(data)))
    s = data[idx]
    v = s.mean(axis=1) if stat == "mean" else np.median(s, axis=1)
    return np.percentile(v, [2.5, 97.5])


rows = []
for stat in ["mean", "median"]:
    for B in BS:
        for r in range(REDO):
            lo, hi = boot_ci(x, B, stat)
            rows.append((stat, B, r, lo, hi))
R = pd.DataFrame(rows, columns=["stat", "B", "redo", "lo", "hi"])
R.round(2).to_csv(RES / "redo_intervals.csv", index=False)
# 基準：B=10,000 の100回の平均を「その50件の区間の端」とみなす
summ = []
for stat in ["mean", "median"]:
    ref = R[(R.stat == stat) & (R.B == 10000)]
    width = (ref.hi - ref.lo).mean()
    for B in BS:
        s = R[(R.stat == stat) & (R.B == B)]
        summ.append({"stat": stat, "B": B, "lo_sd": s.lo.std(ddof=1), "hi_sd": s.hi.std(ddof=1),
                     "lo_range": s.lo.max() - s.lo.min(), "hi_range": s.hi.max() - s.hi.min(),
                     "width_ref": width, "hi_sd_pct_of_width": s.hi.std(ddof=1) / width * 100,
                     "lo_sd_pct_of_width": s.lo.std(ddof=1) / width * 100})
S = pd.DataFrame(summ)
S.round(3).to_csv(RES / "summary.csv", index=False)
# 当たる割合（データを作り直す）
NCOV = 600
cov = {(stat, B): 0 for stat in ["mean", "median"] for B in BS}
for k in range(NCOV):
    d = rng.lognormal(MU, SIG, N)
    for B in BS:
        for stat, tv in [("mean", true_mean), ("median", true_median)]:
            lo, hi = boot_ci(d, B, stat)
            cov[(stat, B)] += lo <= tv <= hi
C = pd.DataFrame([{"stat": k[0], "B": k[1], "coverage_pct": v / NCOV * 100} for k, v in cov.items()])
C.round(2).to_csv(RES / "coverage.csv", index=False)
g = lambda stat, B, col: float(S[(S.stat == stat) & (S.B == B)][col].iloc[0])
out = {"n": N, "redo": REDO, "B": BS, "sample_mean": round(float(x.mean()), 0), "sample_median": round(float(np.median(x)), 0),
       "mean_ci_ref": [round(float(R[(R.stat == "mean") & (R.B == 10000)].lo.mean()), 0), round(float(R[(R.stat == "mean") & (R.B == 10000)].hi.mean()), 0)],
       "median_ci_ref": [round(float(R[(R.stat == "median") & (R.B == 10000)].lo.mean()), 0), round(float(R[(R.stat == "median") & (R.B == 10000)].hi.mean()), 0)],
       "mean_hi_sd_pct_of_width": {str(B): round(g("mean", B, "hi_sd_pct_of_width"), 1) for B in BS},
       "mean_lo_sd_pct_of_width": {str(B): round(g("mean", B, "lo_sd_pct_of_width"), 1) for B in BS},
       "median_hi_sd_pct_of_width": {str(B): round(g("median", B, "hi_sd_pct_of_width"), 1) for B in BS},
       "median_lo_sd_pct_of_width": {str(B): round(g("median", B, "lo_sd_pct_of_width"), 1) for B in BS},
       "mean_end_sd_pct_of_width": {str(B): round((g("mean", B, "hi_sd_pct_of_width") + g("mean", B, "lo_sd_pct_of_width")) / 2, 1) for B in BS},
       "median_end_sd_pct_of_width": {str(B): round((g("median", B, "hi_sd_pct_of_width") + g("median", B, "lo_sd_pct_of_width")) / 2, 1) for B in BS},
       "mean_hi_range_yen": {str(B): round(g("mean", B, "hi_range"), 0) for B in BS},
       "coverage_n_datasets": NCOV,
       "coverage_mean_pct": {str(B): round(cov[("mean", B)] / NCOV * 100, 1) for B in BS},
       "coverage_median_pct": {str(B): round(cov[("median", B)] / NCOV * 100, 1) for B in BS}}
json.dump(out, open(RES / "a756_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：100回やり直した区間（平均）
fig, axes = plt.subplots(1, 3, figsize=(10, 3.8), sharex=True, sharey=True)
for ax, B in zip(axes, BS):
    s = R[(R.stat == "mean") & (R.B == B)].head(40)
    for i, (lo, hi) in enumerate(zip(s.lo, s.hi)):
        ax.plot([lo, hi], [i, i], color=BLUE, lw=1)
    ax.axvline(out["mean_ci_ref"][0], color=ORANGE, lw=0.8, ls="--"); ax.axvline(out["mean_ci_ref"][1], color=ORANGE, lw=0.8, ls="--")
    ax.set_title(f"B = {B:,}回", fontsize=11); ax.set_yticks([]); ax.set_xlabel("平均の95%区間（円）")
fig.suptitle("同じ50件でも、ブートストラップをやり直すたびに区間の端が動く（40回分）", fontsize=12, y=1.03)
save(fig, "a756_intervals.png", SRC, y=-0.05)
# 図2：区間の端の振れ（幅に対する%）
fig, ax = plt.subplots(figsize=(7.5, 3.8))
for stat, c, lab in [("mean", BLUE, "平均の区間"), ("median", ORANGE, "中央値の区間")]:
    v = [(g(stat, B, "hi_sd_pct_of_width") + g(stat, B, "lo_sd_pct_of_width")) / 2 for B in BS]
    ax.plot(BS, v, marker="o", color=c, label=lab)
    for B, val in zip(BS, v):
        ax.text(B, val + 0.3, f"{val:.1f}%", ha="center", fontsize=9, color=c)
ax.set_xscale("log"); ax.set_xticks(BS); ax.set_xticklabels([f"{b:,}" for b in BS])
ax.set_xlabel("ブートストラップの回数 B"); ax.set_ylabel("端の標準偏差（区間の幅に対する%、両端の平均）", fontsize=10)
ax.legend(frameon=False); ax.set_title("回数を10倍にすると、端の振れはおよそ3分の1になる")
save(fig, "a756_endpoint_sd.png", SRC)
# 図3：当たる割合
fig, ax = plt.subplots(figsize=(7.5, 3.6))
x0 = np.arange(3)
cm = [cov[("mean", B)] / NCOV * 100 for B in BS]; cd = [cov[("median", B)] / NCOV * 100 for B in BS]
ax.bar(x0 - 0.18, cm, 0.36, color=BLUE, label="平均"); ax.bar(x0 + 0.18, cd, 0.36, color=ORANGE, label="中央値")
for i in range(3):
    ax.text(i - 0.18, cm[i] + 0.5, f"{cm[i]:.1f}", ha="center", fontsize=9); ax.text(i + 0.18, cd[i] + 0.5, f"{cd[i]:.1f}", ha="center", fontsize=9)
ax.axhline(95, color=GRAY, ls="--", lw=1)
ax.set_xticks(x0); ax.set_xticklabels([f"B = {b:,}" for b in BS]); ax.set_ylim(80, 100)
ax.set_ylabel("本当の値を含む割合（%）"); ax.legend(frameon=False, loc="lower right")
ax.set_title(f"当たる割合は回数ではほとんど変わらない（データを{NCOV}回作り直した）")
save(fig, "a756_coverage.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
