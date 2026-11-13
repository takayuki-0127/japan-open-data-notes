"""610 説明変数に測りまちがいがあると、回帰の係数はどれだけ小さく出るのか

架空の店500店。本当の指標 x（例：店内の混み具合を表す点数）が売上 y に効く（本当の係数0.5）。
x は測りまちがい u を含んで x* = x + u としてしか見えない。信頼性 λ = Var(x)/Var(x*) を 1.0〜0.3 で変える。
  O 観測値でそのまま回帰
  A 同じ店を2回測った値の平均で回帰
  C 2回の測定から信頼性を出して係数を割り戻す（λ̂ = Cov(x1,x2)/Var(x1)）
  IV 2回目の測定を操作変数にする
さらに、x と相関する別の変数 z（本当の係数0）を一緒に入れると、z に見かけの係数が出るかを見る。各2,000回、seed 610。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 610）"
rng = np.random.default_rng(610)
N, B, REPS = 500, 0.5, 2000


def ols(X, y):
    X = np.column_stack([np.ones(len(y)), X])
    return np.linalg.lstsq(X, y, rcond=None)[0][1:]


rows = []
lams = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
for lam in lams:
    su = np.sqrt((1 - lam) / lam)
    for r in range(REPS):
        x = rng.standard_normal(N)
        z = 0.6 * x + 0.8 * rng.standard_normal(N)
        y = 2 + B * x + 0.0 * z + rng.standard_normal(N)
        x1 = x + su * rng.standard_normal(N); x2 = x + su * rng.standard_normal(N)
        bO = ols(x1, y)[0]
        bA = ols((x1 + x2) / 2, y)[0]
        lam_hat = np.cov(x1, x2)[0, 1] / np.var(x1, ddof=1)
        bC = bO / lam_hat
        bIV = np.cov(x2, y)[0, 1] / np.cov(x2, x1)[0, 1]
        bxz = ols(np.column_stack([x1, z]), y)
        rows.append({"lam": lam, "O": bO, "A": bA, "C": bC, "IV": bIV, "lam_hat": lam_hat, "x_with_z": bxz[0], "z_with_x": bxz[1]})
df = pd.DataFrame(rows)
summ = df.groupby("lam").agg(["mean", "std"]).round(4)
summ.columns = [f"{a}_{b}" for a, b in summ.columns]
summ.to_csv(RES / "summary.csv")
s = summ
out = {"true_coef": B, "n": N, "reps": REPS,
       "by_lambda": {str(l): {"O": s.loc[l, "O_mean"], "A": s.loc[l, "A_mean"], "C": s.loc[l, "C_mean"], "IV": s.loc[l, "IV_mean"],
                              "O_sd": s.loc[l, "O_std"], "C_sd": s.loc[l, "C_std"], "IV_sd": s.loc[l, "IV_std"], "A_sd": s.loc[l, "A_std"],
                              "z_with_x": s.loc[l, "z_with_x_mean"], "x_with_z": s.loc[l, "x_with_z_mean"], "lam_hat": s.loc[l, "lam_hat_mean"]} for l in lams},
       "theory_O": {str(l): round(B * l, 4) for l in lams}}
json.dump(out, open(RES / "a610_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：信頼性と係数
fig, ax = plt.subplots(figsize=(8, 3.8))
L = np.array(lams)
ax.plot(L, s.O_mean, marker="o", color=ORANGE, label="測った値でそのまま回帰")
ax.plot(L, s.A_mean, marker="s", color=BLUE, label="2回測った平均で回帰")
ax.plot(L, s.C_mean, marker="^", color=GREEN, label="信頼性で割り戻す")
ax.plot(L, B * L, color=GRAY, ls=":", lw=1, label="0.5×信頼性（理論）")
ax.axhline(B, color=GREEN, ls="--", lw=0.8)
ax.invert_xaxis(); ax.set_xlabel("測った値の信頼性 λ（1は測りまちがいなし）"); ax.set_ylabel("係数の平均（本当は0.5）")
ax.set_ylim(0, 0.6); ax.legend(frameon=False, fontsize=9, loc="lower left"); ax.set_title("測りまちがいが大きいほど、係数は0に向かって縮む")
save(fig, "a610_attenuation.png", SRC)
# 図2：λ=0.5 での4つの推定の分布
d5 = df[df.lam == 0.5]
fig, ax = plt.subplots(figsize=(8, 3.8))
lab = ["そのまま", "2回の平均", "信頼性で割り戻す", "2回目を操作変数に"]
bp = ax.boxplot([d5.O, d5.A, d5.C, d5.IV], tick_labels=lab, patch_artist=True, widths=0.5, flierprops={"markersize": 2})
for b, c in zip(bp["boxes"], [ORANGE, BLUE, GREEN, LIGHT]):
    b.set_facecolor(c); b.set_alpha(0.7)
ax.axhline(B, color=GRAY, ls=":"); ax.set_ylabel("係数（2,000回）"); ax.set_title("信頼性0.5のとき：直すと偏りは消えるが、散らばりは広がる")
save(fig, "a610_corrections.png", SRC)
# 図3：z の見かけの係数
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.plot(L, s.z_with_x_mean, marker="o", color=ORANGE, label="z の係数（本当は0）")
ax.plot(L, s.x_with_z_mean, marker="s", color=BLUE, label="x の係数（本当は0.5）")
ax.axhline(0, color=GRAY, lw=0.8); ax.axhline(B, color=BLUE, ls=":", lw=0.8)
ax.invert_xaxis(); ax.set_xlabel("x を測った値の信頼性 λ"); ax.set_ylabel("係数の平均")
ax.legend(frameon=False, fontsize=9); ax.set_title("x と相関する z を一緒に入れると、縮んだ分を z が拾う")
save(fig, "a610_spillover.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
