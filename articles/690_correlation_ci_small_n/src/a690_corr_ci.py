"""690 30件で相関0.3と出たとき、本当の相関はどの範囲にあると言えるのか

(1) 観測した相関 r = 0.3 に対する95%区間（フィッシャーの z 変換）を、件数10〜1,000で計算する
(2) 本当の相関 ρ = 0・0.3・0.6、件数 n = 10・20・30・50・100・300 の2次元正規のデータを各500回作り、
    フィッシャーの z 変換の区間と、ブートストラップ（パーセンタイル、500回）の区間が本当の相関を含む割合と幅を数える
(3) n = 30 のとき、ρ = 0 と ρ = 0.3 で、観測される相関がどれだけ重なるかを見る
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 690）"
rng = np.random.default_rng(690)
Z = stats.norm.ppf(0.975)


def fisher_ci(r, n):
    z = np.arctanh(r); h = Z / np.sqrt(n - 3)
    return np.tanh(z - h), np.tanh(z + h)


def corr_rows(x, y):
    xm = x - x.mean(-1, keepdims=True); ym = y - y.mean(-1, keepdims=True)
    return (xm * ym).sum(-1) / np.sqrt((xm ** 2).sum(-1) * (ym ** 2).sum(-1))


# (1)
NS1 = [10, 15, 20, 30, 50, 100, 200, 300, 500, 1000]
ci1 = pd.DataFrame([{"n": n, "lo": fisher_ci(0.3, n)[0], "hi": fisher_ci(0.3, n)[1]} for n in NS1])
ci1.round(4).to_csv(RES / "ci_r03.csv", index=False)

# (2)
NS, RHOS, REPS, BOOT = [10, 20, 30, 50, 100, 300], [0.0, 0.3, 0.6], 500, 500
rows = []
for rho in RHOS:
    for n in NS:
        for r_ in range(REPS):
            x = rng.normal(0, 1, n); y = rho * x + np.sqrt(1 - rho ** 2) * rng.normal(0, 1, n)
            r = corr_rows(x, y)
            lo, hi = fisher_ci(r, n)
            idx = rng.integers(0, n, (BOOT, n))
            rb = corr_rows(x[idx], y[idx]); rb = rb[np.isfinite(rb)]
            blo, bhi = np.quantile(rb, [0.025, 0.975])
            rows.append({"rho": rho, "n": n, "rep": r_, "r": r, "f_lo": lo, "f_hi": hi, "b_lo": blo, "b_hi": bhi})
D = pd.DataFrame(rows); D.to_csv(RES / "reps.csv.gz", index=False, float_format="%.5g", compression={"method": "gzip", "mtime": 0})
D["f_cover"] = (D.f_lo <= D.rho) & (D.rho <= D.f_hi); D["b_cover"] = (D.b_lo <= D.rho) & (D.rho <= D.b_hi)
D["f_width"] = D.f_hi - D.f_lo; D["b_width"] = D.b_hi - D.b_lo
S = D.groupby(["rho", "n"]).agg(f_cover=("f_cover", "mean"), b_cover=("b_cover", "mean"), f_width=("f_width", "mean"),
                                b_width=("b_width", "mean"), r_sd=("r", "std"), r_p5=("r", lambda v: np.quantile(v, 0.05)),
                                r_p95=("r", lambda v: np.quantile(v, 0.95))).reset_index()
S["f_cover"] *= 100; S["b_cover"] *= 100
S.round(4).to_csv(RES / "summary.csv", index=False)
r0 = D[(D.rho == 0) & (D.n == 30)]["r"]; r3 = D[(D.rho == 0.3) & (D.n == 30)]["r"]
out = {"ci_for_r03": {str(n): [round(a, 2), round(b, 2)] for n, a, b in zip(ci1.n, ci1.lo, ci1.hi)},
       "n_for_width_under_0_2": int(next(n for n in range(10, 5000) if np.diff(fisher_ci(0.3, n))[0] < 0.2)),
       "coverage": {f"rho{rho}": {str(n): {"fisher": round(float(S[(S.rho == rho) & (S.n == n)].f_cover.iloc[0]), 1),
                                           "boot": round(float(S[(S.rho == rho) & (S.n == n)].b_cover.iloc[0]), 1)} for n in NS} for rho in RHOS},
       "n30_rho0_share_r_ge_03": round(float((r0 >= 0.3).mean() * 100), 1),
       "n30_rho03_share_r_le_0": round(float((r3 <= 0).mean() * 100), 1),
       "n30_rho03_r_range_90": [round(float(np.quantile(r3, 0.05)), 2), round(float(np.quantile(r3, 0.95)), 2)],
       "reps": REPS, "boot": BOOT}
json.dump(out, open(RES / "a690_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：r=0.3 の区間と件数
fig, ax = plt.subplots(figsize=(8.5, 4))
for i, (n, lo, hi) in enumerate(zip(ci1.n, ci1.lo, ci1.hi)):
    ax.plot([lo, hi], [i, i], color=BLUE, lw=3); ax.scatter(0.3, i, color=INK, zorder=3, s=18)
    ax.text(hi + 0.02, i, f"{lo:.2f} 〜 {hi:.2f}", va="center", fontsize=9)
ax.axvline(0, color=GRAY, lw=0.8); ax.set_yticks(range(len(NS1))); ax.set_yticklabels([f"{n}件" for n in ci1.n])
ax.set_xlim(-0.5, 1.05); ax.set_xlabel("相関の95%区間（観測した相関 0.3）"); ax.invert_yaxis()
lo30, hi30 = fisher_ci(0.3, 30); ax.set_title(f"相関0.3と出ても、30件なら区間は {lo30:.2f}〜{hi30:.2f} と0をまたぐ")
save(fig, "a690_ci_by_n.png", SRC)

# 図2：観測される相関のばらつき（n=30）
fig, ax = plt.subplots(figsize=(8.5, 3.8))
bins = np.linspace(-0.7, 0.9, 41)
ax.hist(r0, bins=bins, color=GRAY, alpha=0.6, label="本当の相関 0")
ax.hist(r3, bins=bins, color=BLUE, alpha=0.6, label="本当の相関 0.3")
ax.axvline(0.3, color=INK, ls="--", lw=0.8)
ax.set_xlabel("30件で観測した相関"); ax.set_ylabel("回数（500回中）"); ax.legend(frameon=False)
ax.set_title(f"30件では、本当は0でも{out['n30_rho0_share_r_ge_03']:.0f}%の回で0.3以上、本当は0.3でも{out['n30_rho03_share_r_le_0']:.0f}%の回で0以下")
save(fig, "a690_sampling.png", SRC)

# 図3：区間の当たり方（ρ=0.3 と 0.6）
fig, ax = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True, gridspec_kw={"wspace": 0.08})
for a_, rho in zip(ax, [0.3, 0.6]):
    s = S[S.rho == rho]; xi = np.arange(len(NS)); w = 0.38
    a_.bar(xi - w / 2, s.f_cover, w, color=BLUE, label="フィッシャーの z 変換"); a_.bar(xi + w / 2, s.b_cover, w, color=ORANGE, label="ブートストラップ")
    for i, (f, b) in enumerate(zip(s.f_cover, s.b_cover)):
        a_.text(i - w / 2, f, f"{f:.0f}", ha="center", va="bottom", fontsize=8); a_.text(i + w / 2, b, f"{b:.0f}", ha="center", va="bottom", fontsize=8)
    a_.axhline(95, color=INK, ls="--", lw=0.8); a_.set_ylim(70, 102); a_.set_xticks(xi); a_.set_xticklabels([f"{n}件" for n in NS], fontsize=9)
    a_.set_title(f"本当の相関 {rho}", fontsize=11)
ax[0].set_ylabel("95%区間が本当の相関を含んだ割合（%）"); ax[0].legend(frameon=False, fontsize=8.5, loc="lower right")
save(fig, "a690_coverage.png", SRC, y=-0.06)
print(json.dumps(out, ensure_ascii=False, indent=1))
