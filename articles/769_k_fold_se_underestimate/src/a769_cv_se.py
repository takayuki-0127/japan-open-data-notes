"""769 交差検証の fold ごとの成績から出した標準誤差は、本当のばらつきをどれだけ小さく見るのか

架空のデータ。説明変数5つ（標準正規）、本当の確率は logistic(0.8·x1 − 0.6·x2 + 0.4·x3)。
件数 n（100・300・1,000）と fold の数 K（5・10）を変え、各条件でデータを400回作り直す。
1回ごとに K-fold の交差検証で正解率を出し、fold ごとの正解率の標準偏差÷√K を「標準誤差」とする。
本当のばらつきは、400回の交差検証の正解率の標準偏差。区間「平均±1.96×標準誤差」が、
そのデータで学習したモデルの本当の正解率（別に作った20万件で測る）を含む割合も数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold
from common import RES, save, BLUE, ORANGE, GRAY, GREEN

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 769）"
rng = np.random.default_rng(769)
B = np.array([.8, -.6, .4, 0, 0])
NS, KS, R = [100, 300, 1000], [5, 10], 400


def make(n):
    X = rng.standard_normal((n, 5)); p = 1 / (1 + np.exp(-X @ B))
    return X, (rng.random(n) < p).astype(int)


XT, YT = make(200_000)
rows = []
for n in NS:
    for K in KS:
        for r in range(R):
            X, y = make(n)
            accs = []
            for tr, te in KFold(K, shuffle=True, random_state=r).split(X):
                m = LogisticRegression(C=1e6, max_iter=200).fit(X[tr], y[tr]); accs.append((m.predict(X[te]) == y[te]).mean())
            accs = np.array(accs)
            full = LogisticRegression(C=1e6, max_iter=200).fit(X, y)
            true_acc = (full.predict(XT) == YT).mean()
            se = accs.std(ddof=1) / np.sqrt(K)
            rows.append(dict(n=n, K=K, rep=r, cv=accs.mean(), se=se, true=true_acc,
                             cover=abs(accs.mean() - true_acc) <= 1.96 * se))
D = pd.DataFrame(rows)
S = D.groupby(["n", "K"]).agg(cv_mean=("cv", "mean"), cv_sd=("cv", "std"), se_mean=("se", "mean"),
                               err_sd=("cv", lambda s: np.nan), cover=("cover", "mean"), true_mean=("true", "mean")).reset_index()
S["err_sd"] = D.assign(e=D.cv - D.true).groupby(["n", "K"]).e.std().to_numpy()
S["ratio"] = S.se_mean / S.cv_sd
S.to_csv(RES / "summary.csv", index=False)
D.to_csv(RES / "reps.csv", index=False, float_format="%.6f")
g = lambda n, K, k: float(S[(S.n == n) & (S.K == K)][k].iloc[0])
out = {"reps": R, "test_n": len(YT),
       "by_cond": {f"n{n}_K{K}": {k: round(g(n, K, k), 4) for k in ["cv_mean", "cv_sd", "se_mean", "ratio", "cover"]} for n in NS for K in KS}}
for n in NS:
    out[f"ratio_n{n}_K10"] = g(n, 10, "ratio"); out[f"cover_n{n}_K10"] = g(n, 10, "cover")
    out[f"ratio_n{n}_K5"] = g(n, 5, "ratio"); out[f"cover_n{n}_K5"] = g(n, 5, "cover")
json.dump(out, open(RES / "a769_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：標準誤差と本当のばらつき
fig, ax = plt.subplots(figsize=(9, 4.6)); x = np.arange(len(S)); w = .38
lab = [f"n={n}\nK={K}" for n, K in zip(S.n, S.K)]
ax.bar(x - w / 2, S.cv_sd * 100, w, color=GRAY, label="本当のばらつき（400回の標準偏差）")
ax.bar(x + w / 2, S.se_mean * 100, w, color=ORANGE, label="fold から出した標準誤差（平均）")
for xx, a, b in zip(x, S.cv_sd * 100, S.se_mean * 100):
    ax.text(xx + w / 2, b + .1, f"{b / a:.0%}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(lab); ax.set_ylabel("正解率のばらつき（ポイント）")
ax.legend(frameon=False); ax.set_title("fold から出した標準誤差は、本当のばらつきより小さい（数字は比）")
save(fig, "a769_se_vs_sd.png", SRC)

# 図2：区間の当たる割合
fig, ax = plt.subplots(figsize=(9, 4.6))
for K, c in [(5, BLUE), (10, ORANGE)]:
    s = S[S.K == K]; ax.plot(s.n, s.cover * 100, "o-", color=c, label=f"K={K}")
    for a, b in zip(s.n, s.cover * 100): ax.text(a, b + 1.5, f"{b:.0f}%", ha="center", fontsize=9, color=c)
ax.axhline(95, color=GRAY, ls="--"); ax.text(1000, 96, "95%", ha="right", color=GRAY)
ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels([str(v) for v in NS])
ax.set_xlabel("件数 n"); ax.set_ylabel("区間が本当の正解率を含む割合（%）"); ax.set_ylim(0, 100)
ax.legend(frameon=False); ax.set_title("「平均±1.96×標準誤差」の区間は、95%に届かない")
save(fig, "a769_coverage.png", SRC)

# 図3：n=300, K=10 の400回
s = D[(D.n == 300) & (D.K == 10)].sort_values("cv").reset_index(drop=True).iloc[::8]
fig, ax = plt.subplots(figsize=(9, 4.6)); i = np.arange(len(s))
ok = s.cover.to_numpy()
ax.errorbar(i[ok], s.cv[ok] * 100, yerr=1.96 * s.se[ok] * 100, fmt="o", color=BLUE, ms=3, label="区間が本当の正解率を含む")
ax.errorbar(i[~ok], s.cv[~ok] * 100, yerr=1.96 * s.se[~ok] * 100, fmt="o", color=ORANGE, ms=3, label="含まない")
ax.scatter(i, s.true * 100, marker="_", color="black", s=40, label="本当の正解率")
ax.set_xlabel("400回のうち50回（交差検証の正解率の順）"); ax.set_ylabel("正解率（%）")
ax.legend(frameon=False, fontsize=9); ax.set_title("n=300、K=10 の例：外れるのは、正解率が端に出た回")
save(fig, "a769_examples.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
