"""689 結果に効く変数をロジスティック回帰に入れないと、施策と関係のない変数でも、施策の係数はどれだけ小さく出るのか

架空の申込みデータ（2,000人）。施策 T は無作為に半分へ（だから T と X は無関係）。
X はもともとの申込みやすさ（標準正規）。申込む確率：logit p = -1 + 0.7 T + c X。c = 0・1・2・3。
ロジスティック回帰を X あり・X なしで当て、T のオッズ比を比べる。
あわせて、確率の差（施策ありの申込率 − なしの申込率）も比べる。各400回。
"""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の申込みデータ（作成者が乱数で作成、seed 689）"
rng = np.random.default_rng(689)
N, REPS, B0, B = 2000, 400, -1.0, 0.7
CS = [0.0, 1.0, 2.0, 3.0]
expit = lambda z: 1 / (1 + np.exp(-z))

# 本当の確率の差（X の分布で平均した値）を大きな数で求める
xb = rng.normal(0, 1, 2_000_000)
true_rd = {c: float(np.mean(expit(B0 + B + c * xb) - expit(B0 + c * xb))) for c in CS}
true_mor = {}
for c in CS:
    p1, p0 = np.mean(expit(B0 + B + c * xb)), np.mean(expit(B0 + c * xb))
    true_mor[c] = float(p1 / (1 - p1) / (p0 / (1 - p0)))

rows = []
for c in CS:
    for r in range(REPS):
        T = rng.permutation(np.r_[np.ones(N // 2), np.zeros(N // 2)])
        X = rng.normal(0, 1, N)
        y = (rng.uniform(size=N) < expit(B0 + B * T + c * X)).astype(float)
        m1 = sm.Logit(y, sm.add_constant(np.c_[T, X])).fit(disp=0)
        m0 = sm.Logit(y, sm.add_constant(T)).fit(disp=0)
        rd = y[T == 1].mean() - y[T == 0].mean()
        rows.append({"c": c, "rep": r, "or_with_x": np.exp(m1.params[1]), "or_without_x": np.exp(m0.params[1]),
                     "se_with_x": m1.bse[1], "se_without_x": m0.bse[1], "rd": rd, "rate": y.mean()})
R = pd.DataFrame(rows); R.to_csv(RES / "reps.csv.gz", index=False, float_format="%.5g", compression={"method": "gzip", "mtime": 0})
S = R.groupby("c").agg(or_with_x=("or_with_x", "median"), or_without_x=("or_without_x", "median"),
                       se_with_x=("se_with_x", "mean"), se_without_x=("se_without_x", "mean"),
                       rd=("rd", "mean"), rate=("rate", "mean")).reset_index()
S["true_conditional_or"] = np.exp(B); S["true_marginal_or"] = S.c.map(true_mor); S["true_rd"] = S.c.map(true_rd)
S.round(4).to_csv(RES / "summary.csv", index=False)
out = {"n": N, "reps": REPS, "beta_T": B, "true_conditional_or": round(float(np.exp(B)), 3),
       "summary": {f"c{c}": {k: round(float(S[S.c == c][k].iloc[0]), 3) for k in S.columns if k != "c"} for c in CS}}
json.dump(out, open(RES / "a689_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：オッズ比
fig, ax = plt.subplots(figsize=(8.5, 4))
ax.plot(S.c, S.or_with_x, color=BLUE, marker="o", lw=2, label="X を入れた回帰")
ax.plot(S.c, S.or_without_x, color=ORANGE, marker="o", lw=2, label="X を入れない回帰")
for x_, a, b in zip(S.c, S.or_with_x, S.or_without_x):
    ax.text(x_ + 0.05, a + 0.03, f"{a:.2f}", color=BLUE, fontsize=9); ax.text(x_ + 0.05, b - 0.08, f"{b:.2f}", color=ORANGE, fontsize=9)
ax.axhline(np.exp(B), color=INK, ls="--", lw=0.8); ax.text(0, np.exp(B) + 0.04, f"本当のオッズ比（X をそろえたとき）{np.exp(B):.2f}", fontsize=8.5)
ax.set_xticks(CS); ax.set_xlabel("X の効き方の強さ c"); ax.set_ylabel("施策のオッズ比（400回の中央値）")
ax.set_ylim(1, 2.3); ax.legend(frameon=False, loc="lower left")
ax.set_title("施策と無関係な X でも、入れないとオッズ比は1に近づく")
save(fig, "a689_odds_ratio.png", SRC)

# 図2：確率の差は変わらない
fig, ax = plt.subplots(figsize=(8.5, 3.8))
x = np.arange(len(CS)); w = 0.38
ax.bar(x - w / 2, S.true_rd * 100, w, color=LIGHT, label="本当の確率の差")
ax.bar(x + w / 2, S.rd * 100, w, color=ORANGE, label="単純に比べた差（X なし）")
for i in range(len(CS)):
    ax.text(i - w / 2, S.true_rd[i] * 100, f"{S.true_rd[i]*100:.1f}", ha="center", va="bottom", fontsize=9)
    ax.text(i + w / 2, S.rd[i] * 100, f"{S.rd[i]*100:.1f}", ha="center", va="bottom", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([f"c = {c:g}" for c in CS]); ax.set_ylabel("申込率の差（ポイント）")
ax.legend(frameon=False, fontsize=9); ax.set_title("確率の差で見れば、X を入れなくてもずれない（施策が無作為のため）")
save(fig, "a689_risk_diff.png", SRC)

# 図3：標準誤差
fig, ax = plt.subplots(figsize=(8.5, 3.6))
ax.bar(x - w / 2, S.se_with_x, w, color=BLUE, label="X を入れた回帰")
ax.bar(x + w / 2, S.se_without_x, w, color=ORANGE, label="X を入れない回帰")
for i in range(len(CS)):
    ax.text(i - w / 2, S.se_with_x[i], f"{S.se_with_x[i]:.3f}", ha="center", va="bottom", fontsize=8.5)
    ax.text(i + w / 2, S.se_without_x[i], f"{S.se_without_x[i]:.3f}", ha="center", va="bottom", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels([f"c = {c:g}" for c in CS]); ax.set_ylabel("施策の係数の標準誤差（平均）")
ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_title("X を入れると、係数の標準誤差はむしろ大きくなる")
save(fig, "a689_se.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
