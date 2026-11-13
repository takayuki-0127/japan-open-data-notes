"""669 部品の故障の起き方を「毎年同じ割合」と置くと、使った年数ごとの故障の見込みはどれだけずれるのか

架空の部品 5,000 個を同時に使い始め、5年間だけ見る（5年で壊れていない部品は「まだ壊れていない」として打ち切り）。
本当の寿命はワイブル分布。形の値 k を 0.7（初めに壊れやすい）・1.0（毎年同じ割合）・1.5・2.5・3.5（使うほど壊れやすい）で変え、
どの k でも5年までに壊れる割合が 20% になるように尺度を決める。
5年分のデータから2通りで当てはめる：
  指数分布（毎年同じ割合）：壊れた数 ÷ 使った年数の合計
  ワイブル分布：打ち切りを入れた最尤法
そして「使って t 年目に、それまで壊れなかった部品が1年のうちに壊れる割合」（年ごとの故障率）を t=1〜10 で比べる。
6〜10年目に壊れる数の見込みも比べる（データの外の年）。各 200 回くり返す。数字は置いた k と20%で決まる。
"""
import json
import numpy as np
import pandas as pd
from scipy import optimize
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の部品の故障（作成者が乱数で作成、seed 669）"
rng = np.random.default_rng(669)
N, TOBS, P5, REPS = 5000, 5.0, 0.20, 200
KS = [0.7, 1.0, 1.5, 2.5, 3.5]
YEARS = np.arange(1, 11)


def scale_for(k):  # F(5)=P5
    return TOBS / (-np.log(1 - P5)) ** (1 / k)


def surv(t, k, lam):
    return np.exp(-(np.asarray(t, float) / lam) ** k)


def annual_rate(k, lam):  # 年ごとの条件付き故障率
    s0, s1 = surv(YEARS - 1, k, lam), surv(YEARS, k, lam)
    return 1 - s1 / s0


def fit_weibull(t, d):
    def nll(p):
        k, lam = np.exp(p)
        z = (t / lam) ** k
        return -(np.sum(d * (np.log(k) - np.log(lam) + (k - 1) * np.log(t / lam))) - np.sum(z))
    r = optimize.minimize(nll, [0.0, np.log(t.mean() * 3)], method="Nelder-Mead", options={"xatol": 1e-7, "fatol": 1e-7, "maxiter": 4000})
    return np.exp(r.x)


rows, rate_rows = [], []
for k in KS:
    lam = scale_for(k)
    true_rate = annual_rate(k, lam)
    true_6_10 = N * (surv(5, k, lam) - surv(10, k, lam))
    for r in range(REPS):
        life = lam * rng.weibull(k, N)
        t = np.minimum(life, TOBS); d = (life <= TOBS).astype(float)
        h = d.sum() / t.sum()                          # 指数分布
        exp_rate = np.full(10, 1 - np.exp(-h))
        kh, lh = fit_weibull(t, d)
        wb_rate = annual_rate(kh, lh)
        n_alive = N - d.sum()
        exp_6_10 = n_alive * (1 - np.exp(-h * 5))
        wb_6_10 = n_alive * (1 - surv(10, kh, lh) / surv(5, kh, lh))
        rows.append({"k": k, "rep": r, "k_hat": kh, "exp_rate": h, "true_6_10": true_6_10, "exp_6_10": exp_6_10, "wb_6_10": wb_6_10,
                     "exp_y1": exp_rate[0], "exp_y8": exp_rate[7], "wb_y1": wb_rate[0], "wb_y8": wb_rate[7]})
        if r < 50:
            for y in range(10):
                rate_rows.append({"k": k, "rep": r, "year": y + 1, "true": true_rate[y], "exp": exp_rate[y], "wb": wb_rate[y]})
D = pd.DataFrame(rows); R = pd.DataFrame(rate_rows)
RM = R.groupby(["k", "year"])[["true", "exp", "wb"]].mean().reset_index()
RM.round(5).to_csv(RES / "annual_rate_by_year.csv", index=False)
S = D.groupby("k").agg(k_hat=("k_hat", "mean"), k_hat_sd=("k_hat", "std"), true_6_10=("true_6_10", "mean"), exp_6_10=("exp_6_10", "mean"),
                       wb_6_10=("wb_6_10", "mean"), wb_6_10_sd=("wb_6_10", "std"), exp_y1=("exp_y1", "mean"), exp_y8=("exp_y8", "mean"),
                       wb_y1=("wb_y1", "mean"), wb_y8=("wb_y8", "mean")).reset_index()
S["true_y1"] = [annual_rate(k, scale_for(k))[0] for k in S.k]; S["true_y8"] = [annual_rate(k, scale_for(k))[7] for k in S.k]
S.round(5).to_csv(RES / "summary.csv", index=False)
out = {"parts": N, "observed_years": TOBS, "failed_by_5y_pct": P5 * 100, "reps": REPS}
for _, s in S.iterrows():
    out[f"k{s.k}"] = {"k_hat_mean": round(s.k_hat, 3), "k_hat_sd": round(s.k_hat_sd, 3),
                      "true_rate_y1_pct": round(100 * s.true_y1, 2), "exp_rate_y1_pct": round(100 * s.exp_y1, 2), "wb_rate_y1_pct": round(100 * s.wb_y1, 2),
                      "true_rate_y8_pct": round(100 * s.true_y8, 2), "exp_rate_y8_pct": round(100 * s.exp_y8, 2), "wb_rate_y8_pct": round(100 * s.wb_y8, 2),
                      "true_failures_y6_10": round(s.true_6_10, 1), "exp_failures_y6_10": round(s.exp_6_10, 1), "wb_failures_y6_10": round(s.wb_6_10, 1),
                      "exp_vs_true_y6_10_pct": round(100 * (s.exp_6_10 / s.true_6_10 - 1), 1), "wb_vs_true_y6_10_pct": round(100 * (s.wb_6_10 / s.true_6_10 - 1), 1)}
json.dump(out, open(RES / "a669_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：k=2.5 の年ごとの故障率
fig, ax = plt.subplots(figsize=(8.5, 4.2))
q = RM[RM.k == 2.5]
ax.plot(q.year, 100 * q.true, marker="o", color=INK, label="本当（ワイブル、k=2.5）")
ax.plot(q.year, 100 * q.exp, marker="s", color=ORANGE, label="毎年同じ割合で当てた（指数分布）")
ax.plot(q.year, 100 * q.wb, ls="--", color=BLUE, label="ワイブルで当てた")
ax.axvspan(5.5, 10.5, color=LIGHT, alpha=.3); ax.text(8, 1, "データの外（6〜10年目）", ha="center", fontsize=9)
ax.set_xlabel("使って何年目か"); ax.set_ylabel("その年に壊れる割合（%）"); ax.set_xticks(YEARS)
ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_title("使うほど壊れやすい部品を「毎年同じ割合」と見ると、後の年を小さく見る")
save(fig, "a669_rate_by_year.png", SRC)

# 図2：k ごとの 1年目と8年目
fig, ax = plt.subplots(figsize=(8.5, 4.2))
x = np.arange(len(KS)); w = .27
ax.bar(x - w, 100 * S.true_y1, w, color=LIGHT, label="本当の1年目")
ax.bar(x, 100 * S.true_y8, w, color=INK, label="本当の8年目")
ax.bar(x + w, 100 * S.exp_y8, w, color=ORANGE, label="毎年同じ割合で当てた値（どの年も同じ）")
for xx, v in zip(x, 100 * S.true_y8): ax.text(xx, v + .6, f"{v:.1f}", ha="center", fontsize=8.5)
for xx, v in zip(x + w, 100 * S.exp_y8): ax.text(xx, v + .6, f"{v:.1f}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels([f"k={k}" for k in KS]); ax.set_ylabel("その年に壊れる割合（%）")
ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("5年で20%壊れる部品でも、k しだいで8年目の故障率は2.7%から35%まで違う")
save(fig, "a669_bias_by_shape.png", SRC)

# 図3：6〜10年目の故障数
fig, ax = plt.subplots(figsize=(8.5, 4.2))
ax.bar(x - w, S.true_6_10, w, color=INK, label="本当")
ax.bar(x, S.exp_6_10, w, color=ORANGE, label="毎年同じ割合")
ax.bar(x + w, S.wb_6_10, w, color=BLUE, label="ワイブル")
ax.set_xticks(x); ax.set_xticklabels([f"k={k}" for k in KS]); ax.set_ylabel("6〜10年目に壊れる数（5,000個のうち）")
ax.legend(frameon=False, fontsize=9); ax.set_title("6〜10年目に壊れる数の見込み（5年分のデータから）")
save(fig, "a669_failures_6_10.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
