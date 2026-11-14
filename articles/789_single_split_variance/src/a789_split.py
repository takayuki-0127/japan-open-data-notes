"""789 学習とテストを1回だけ分けたとき、テストの成績はどれだけ振れるのか

架空のデータ。x は5つの正規乱数、y は 0/1（ロジスティックの式で作る。本当のモデルで当てると約75%）。
件数 n（200・500・2,000）のデータを1つ作り、学習7割・テスト3割の分け方を100通り変えて、
ロジスティック回帰と決定木（深さ3）のテストの正解率を出す。
2つのモデルの本当の正解率（大きな別データで測る）と比べ、1回の分割でどちらが良いかを取り違える割合も数える。
5-fold の交差検証（分け方を変えて20回）の振れも並べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 789）"
rng = np.random.default_rng(789)
BETA = np.array([1.0, -0.8, 0.6, 0.0, 0.0])
NS, SPLITS = [200, 500, 2000], 100


def make(n):
    X = rng.standard_normal((n, 5)); p = 1 / (1 + np.exp(-(X @ BETA + .5 * X[:, 0] * X[:, 1])))
    return X, (rng.random(n) < p).astype(int)


Xbig, ybig = make(100000)
models = {"logit": lambda: LogisticRegression(max_iter=500), "tree": lambda: DecisionTreeClassifier(max_depth=3, random_state=0)}
rows = []; cvrows = []
for n in NS:
    X, y = make(n)
    true = {k: m().fit(X, y).score(Xbig, ybig) for k, m in models.items()}   # 全部で学習したモデルの本当の正解率
    for s in range(SPLITS):
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=.3, random_state=s)
        r = dict(n=n, split=s)
        for k, m in models.items():
            mm = m().fit(Xtr, ytr); r[f"{k}_test"] = mm.score(Xte, yte); r[f"{k}_true"] = mm.score(Xbig, ybig)
        rows.append(r)
    for s in range(20):
        cv = KFold(5, shuffle=True, random_state=s)
        cvrows.append(dict(n=n, rep=s, **{f"{k}_cv": cross_val_score(m(), X, y, cv=cv).mean() for k, m in models.items()}))
D = pd.DataFrame(rows); C = pd.DataFrame(cvrows)
D.to_csv(RES / "splits.csv", index=False); C.to_csv(RES / "cv_reps.csv", index=False)

summ = []
for n in NS:
    d = D[D.n == n]; c = C[C.n == n]
    better_true = (d.logit_true.mean() > d.tree_true.mean())
    flip = float(((d.logit_test > d.tree_test) != better_true).mean())
    tie = float((d.logit_test == d.tree_test).mean())
    summ.append(dict(n=n, logit_test_min=d.logit_test.min(), logit_test_max=d.logit_test.max(), logit_test_sd=d.logit_test.std(),
                     logit_true_mean=d.logit_true.mean(), tree_true_mean=d.tree_true.mean(),
                     logit_test_p05=d.logit_test.quantile(.05), logit_test_p95=d.logit_test.quantile(.95),
                     flip=flip, tie=tie, cv_sd=c.logit_cv.std(), cv_min=c.logit_cv.min(), cv_max=c.logit_cv.max(),
                     test_n=int(round(n * .3))))
S = pd.DataFrame(summ); S.to_csv(RES / "summary.csv", index=False)
g = lambda n, c: float(S[S.n == n][c].iloc[0])
out = {"ns": NS, "splits": SPLITS, "big_n": 100000,
       "by_n": {str(n): {c: round(g(n, c), 4) for c in S.columns if c != "n"} for n in NS},
       "n200_range": [g(200, "logit_test_min"), g(200, "logit_test_max")], "n200_sd": g(200, "logit_test_sd"),
       "n2000_range": [g(2000, "logit_test_min"), g(2000, "logit_test_max")],
       "n200_flip": g(200, "flip"), "n500_flip": g(500, "flip"), "n2000_flip": g(2000, "flip"),
       "n200_cv_sd": g(200, "cv_sd"), "n200_true_logit": g(200, "logit_true_mean"), "n200_true_tree": g(200, "tree_true_mean")}
json.dump(out, open(RES / "a789_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：100通りの分け方でのテスト正解率（ロジスティック）
fig, ax = plt.subplots(figsize=(8.5, 4.6))
for i, (n, c) in enumerate(zip(NS, [ORANGE, GRAY, BLUE])):
    d = D[D.n == n]; ax.scatter(np.full(len(d), i) + rng.uniform(-.15, .15, len(d)), d.logit_test, s=10, color=c, alpha=.7)
    ax.plot([i - .25, i + .25], [d.logit_true.mean()] * 2, color="#0b0b0b", lw=2)
    ax.text(i + .28, d.logit_test.max(), f"{d.logit_test.min():.0%}〜{d.logit_test.max():.0%}", fontsize=9, va="top")
ax.set_xticks(range(3)); ax.set_xticklabels([f"{n:,}件\n（テスト{int(n*.3)}件）" for n in NS]); ax.set_ylabel("テストの正解率")
ax.set_title("同じデータでも、分け方だけでテストの正解率がこれだけ振れる（黒線は本当の正解率）")
save(fig, "a789_spread.png", SRC)

# 図2：2つのモデルの差（ロジスティック − 決定木）
fig, ax = plt.subplots(figsize=(8.5, 4.6))
for i, (n, c) in enumerate(zip(NS, [ORANGE, GRAY, BLUE])):
    d = D[D.n == n]; diff = d.logit_test - d.tree_test
    ax.scatter(np.full(len(d), i) + rng.uniform(-.15, .15, len(d)), diff, s=10, color=c, alpha=.7)
    ax.plot([i - .25, i + .25], [(d.logit_true - d.tree_true).mean()] * 2, color="#0b0b0b", lw=2)
    ax.text(i, diff.min() - .01, f"逆向き・同点 {g(n,'flip'):.0%}", ha="center", va="top", fontsize=9)
ax.set_ylim(D.logit_test.sub(D.tree_test).min() - .04, None)
ax.axhline(0, color=GRAY, lw=.8, ls="--"); ax.set_xticks(range(3)); ax.set_xticklabels([f"{n:,}件" for n in NS])
ax.set_ylabel("テストの正解率の差（ロジスティック − 決定木）")
ax.set_title("1回の分割では、どちらのモデルが良いかの向きも入れ替わる（黒線は本当の差）")
save(fig, "a789_model_diff.png", SRC)

# 図3：1回の分割と、交差検証の振れ
fig, ax = plt.subplots(figsize=(8.5, 4.4)); x = np.arange(3); w = .38
ax.bar(x - w / 2, S.logit_test_sd, w, color=ORANGE, label="1回の分割（100通りの標準偏差）")
ax.bar(x + w / 2, S.cv_sd, w, color=BLUE, label="5-fold の交差検証（20通りの標準偏差）")
for xi, a, b in zip(x, S.logit_test_sd, S.cv_sd):
    ax.text(xi - w / 2, a, f"{a*100:.1f}pt", ha="center", va="bottom", fontsize=9); ax.text(xi + w / 2, b, f"{b*100:.1f}pt", ha="center", va="bottom", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([f"{n:,}件" for n in NS]); ax.set_ylabel("正解率の振れ（標準偏差）")
ax.legend(frameon=False); ax.set_title("交差検証は分け方による振れを小さくする（同じデータの中での振れ）")
save(fig, "a789_cv.png", SRC)
print(S.round(4).to_string())
