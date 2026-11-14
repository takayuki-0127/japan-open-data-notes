"""678 A/B テストで、前の期間の購入額を使って調整すると、必要な人数はどれだけ減るのか

架空の通販の A/B テスト。1案 5,000人。テスト期間の購入額 Y は平均 3,000円・標準偏差 3,000円の右に長い分布。
テスト前の期間の購入額 X とのつながり（相関）ρ を 0・0.3・0.5・0.7・0.9 と変える。B は購入額が本当に 3% 増える。
  ふつうの差：B の平均 − A の平均
  CUPED：Y − θ(X − X の平均) の平均の差。θ は A・B を合わせたデータの Cov(X,Y)/Var(X)
各 1,000 回くり返し、推定のばらつき（標準偏差）と、検出力 80%・有意水準 5%（両側）に要る1案あたりの人数を出す。
人数は 2×(1.96+0.84)²×σ²÷差² で、σ² は1人あたりのばらつき（CUPED では Y − θX のばらつき）を1,000回で平均したもの。
理屈では、CUPED のばらつき（分散）は ふつうの (1−ρ²) 倍になる。数字は置いた分布で決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の通販の A/B テスト（作成者が乱数で作成、seed 678）"
rng = np.random.default_rng(678)
N, REPS, MU, SD, LIFT = 5000, 1000, 3000.0, 3000.0, 0.03
RHOS = [0.0, 0.3, 0.5, 0.7, 0.9]
SIG = 0.8
Z = 1.959964 + 0.841621


def std_lognorm(size):
    e = rng.lognormal(0, SIG, size)
    m, v = np.exp(SIG ** 2 / 2), (np.exp(SIG ** 2) - 1) * np.exp(SIG ** 2)
    return (e - m) / np.sqrt(v)


def draw(rho, size):
    x = MU + SD * std_lognorm(size)
    y = MU + rho * (x - MU) + np.sqrt(1 - rho ** 2) * SD * std_lognorm(size)
    return np.maximum(x, 0), np.maximum(y, 0)


rows = []; keep = {}
for rho in RHOS:
    xa, ya = draw(rho, (REPS, N)); xb, yb = draw(rho, (REPS, N)); yb = yb * (1 + LIFT)
    plain = yb.mean(1) - ya.mean(1)
    X = np.concatenate([xa, xb], 1); Y = np.concatenate([ya, yb], 1)
    xc = X - X.mean(1, keepdims=True)
    theta = (xc * (Y - Y.mean(1, keepdims=True))).sum(1) / (xc ** 2).sum(1)
    xbar = X.mean(1)
    cuped = (yb.mean(1) - theta * (xb.mean(1) - xbar)) - (ya.mean(1) - theta * (xa.mean(1) - xbar))
    true = LIFT * ya.mean()
    r_real = np.mean([np.corrcoef(xa[i], ya[i])[0, 1] for i in range(50)])
    sp, sc = plain.std(), cuped.std()
    s2p = np.mean((ya.var(1) + yb.var(1)) / 2)                                   # 1人あたりのばらつき
    s2c = np.mean(((ya - theta[:, None] * xa).var(1) + (yb - theta[:, None] * xb).var(1)) / 2)
    rows.append(dict(rho=rho, rho_real=r_real, true_diff=true, plain_mean=plain.mean(), cuped_mean=cuped.mean(),
                     plain_sd=sp, cuped_sd=sc, var_ratio=(sc / sp) ** 2, theory=1 - r_real ** 2,
                     var_ratio_formula=s2c / s2p, n_plain=2 * Z ** 2 * s2p / true ** 2, n_cuped=2 * Z ** 2 * s2c / true ** 2,
                     power_plain=100 * np.mean(np.abs(plain / sp) > 1.959964),
                     power_cuped=100 * np.mean(np.abs(cuped / sc) > 1.959964)))
    if rho == 0.7:
        keep = dict(plain=plain, cuped=cuped, true=true)
S = pd.DataFrame(rows)
S.round(4).to_csv(RES / "summary.csv", index=False)

out = {"n_per_arm": N, "reps": REPS, "lift": LIFT,
       "by_rho": {str(r["rho"]): {"rho_real": round(r["rho_real"], 3), "true_diff": round(r["true_diff"], 1),
                                  "plain_mean": round(r["plain_mean"], 1), "cuped_mean": round(r["cuped_mean"], 1),
                                  "plain_sd": round(r["plain_sd"], 1), "cuped_sd": round(r["cuped_sd"], 1),
                                  "var_ratio": round(r["var_ratio"], 3), "var_ratio_formula": round(r["var_ratio_formula"], 3), "theory_1_minus_rho2": round(r["theory"], 3),
                                  "n_plain": int(round(r["n_plain"], -1)), "n_cuped": int(round(r["n_cuped"], -1)),
                                  "power_plain_pct": round(r["power_plain"], 1), "power_cuped_pct": round(r["power_cuped"], 1)}
                  for r in rows}}
json.dump(out, open(RES / "a678_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：ρ=0.7 の推定の分布
fig, ax = plt.subplots(figsize=(9, 4.6))
bins = np.linspace(-200, 400, 121)
ax.hist(keep["plain"], bins=bins, color=GRAY, alpha=.7, label=f"ふつうの差（標準偏差 {keep['plain'].std():.0f}円）")
ax.hist(keep["cuped"], bins=bins, color=BLUE, alpha=.7, label=f"CUPED（標準偏差 {keep['cuped'].std():.0f}円）")
ax.axvline(keep["true"], color=INK, lw=1.2, ls="--"); ax.text(keep["true"] + 5, ax.get_ylim()[1] * .9, f"本当の差 {keep['true']:.0f}円", fontsize=10)
ax.axvline(0, color=GRAY, lw=.8)
ax.set_xlabel("B − A の平均購入額の差（円）"); ax.set_ylabel("回数（1,000回のうち）")
ax.set_title("前の期間とのつながり ρ=0.7：CUPED は推定の振れ幅を狭くする")
ax.legend(frameon=False, loc="upper left", fontsize=9)
save(fig, "a678_estimates.png", SRC)

# 図2：分散の比
fig, ax = plt.subplots(figsize=(9, 4.6))
rr = np.linspace(0, .95, 50)
ax.plot(rr, 1 - rr ** 2, color=GRAY, lw=1.5, ls="--", label="理屈：1 − ρ²")
ax.plot(S.rho_real, S.var_ratio, "o-", color=BLUE, lw=2, label="シミュレーション")
for _, r in S.iterrows():
    ax.text(r.rho_real + .015, r.var_ratio + .03, f"{r.var_ratio:.2f}", fontsize=9, color=BLUE)
ax.set_xlabel("前の期間の購入額とのつながり（相関 ρ、実際の値）"); ax.set_ylabel("CUPED の分散 ÷ ふつうの差の分散")
ax.set_ylim(0, 1.12); ax.legend(frameon=False, loc="lower left")
ax.set_title("ばらつき（分散）は、およそ 1 − ρ² 倍になる")
save(fig, "a678_var_ratio.png", SRC)

# 図3：必要な人数
fig, ax = plt.subplots(figsize=(9, 4.6))
x = np.arange(len(RHOS)); w = .38
b1 = ax.bar(x - w / 2, S.n_plain, w, color=GRAY, label="ふつうの差")
b2 = ax.bar(x + w / 2, S.n_cuped, w, color=BLUE, label="CUPED")
for bs in (b1, b2):
    for b in bs:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 300, f"{b.get_height():,.0f}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels([f"ρ={r}" for r in RHOS])
ax.set_ylabel("1案あたりに要る人数（人）"); ax.set_ylim(0, 21500); ax.legend(frameon=False, loc="upper right", ncol=2)
ax.set_title("購入額を3%上げる差を、検出力80%で見つけるのに要る人数")
save(fig, "a678_sample_size.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
