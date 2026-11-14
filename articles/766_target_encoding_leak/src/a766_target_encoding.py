"""766 カテゴリを「目的変数の平均」で置きかえて学習すると、学習データの成績はどれだけよく見えるのか

架空の会員の購入予測（購入は約20%）。購入に効く数の変数 x と、購入とは無関係なカテゴリ（地区コード、50〜1,000種類）がある。
カテゴリを「そのカテゴリの購入率」（目的変数の平均）で置きかえてロジスティック回帰に入れる方法を4通り比べる。
  A 学習データ全体の平均（自分の行も含む）、B 5-fold で自分の fold 以外の平均（fold の外の平均）、
  C 平滑化（全体の購入率に寄せる、m=20）だが学習データ全体で計算、D カテゴリを使わない
学習5,000件・テスト5,000件、各60回で、学習とテストの AUC、置きかえた列の係数の z 値を測る。seed 766。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 766）"
rng = np.random.default_rng(766)
N, REPS = 5000, 60
LEVELS = [50, 200, 1000]


def make(n, L):
    x = rng.normal(0, 1, n)
    p = 1 / (1 + np.exp(-(-1.6 + 0.8 * x)))
    y = (rng.random(n) < p).astype(int)
    c = rng.integers(0, L, n)  # 購入と無関係
    return x, c, y


def enc_full(c, y, L, m=0):
    g = np.bincount(c, minlength=L); s = np.bincount(c, weights=y, minlength=L); prior = y.mean()
    return (s + m * prior) / np.maximum(g + m, 1e-9), prior


def fit_eval(Xtr, ytr, Xte, yte):
    lr = LogisticRegression(C=1e6, max_iter=1000).fit(Xtr, ytr)
    ptr = lr.predict_proba(Xtr)[:, 1]; pte = lr.predict_proba(Xte)[:, 1]
    # 2番目の列（置きかえた列）の z 値
    z = np.nan
    if Xtr.shape[1] == 2:
        X1 = np.column_stack([np.ones(len(ytr)), Xtr]); W = ptr * (1 - ptr)
        cov = np.linalg.inv(X1.T @ (X1 * W[:, None])); b = np.r_[lr.intercept_, lr.coef_[0]]
        z = b[2] / np.sqrt(cov[2, 2])
    return roc_auc_score(ytr, ptr), roc_auc_score(yte, pte), z


rows = []
for L in LEVELS:
    for r in range(REPS):
        x, c, y = make(N, L); xt, ct, yt = make(N, L)
        # A 全体の平均
        tab, prior = enc_full(c, y, L)
        eA = tab[c]; eAt = np.where(np.bincount(c, minlength=L)[ct] > 0, tab[ct], prior)
        # B fold の外の平均
        fold = rng.permutation(N) % 5; eB = np.empty(N)
        for k in range(5):
            tr = fold != k
            tk, pk = enc_full(c[tr], y[tr], L)
            cnt = np.bincount(c[tr], minlength=L)
            eB[~tr] = np.where(cnt[c[~tr]] > 0, tk[c[~tr]], pk)
        eBt = eAt  # テストは学習データ全体の平均で置きかえる
        # C 平滑化（m=20）を全体で
        tabC, _ = enc_full(c, y, L, m=20); eC = tabC[c]; eCt = tabC[ct]
        res = {"A": fit_eval(np.column_stack([x, eA]), y, np.column_stack([xt, eAt]), yt),
               "B": fit_eval(np.column_stack([x, eB]), y, np.column_stack([xt, eBt]), yt),
               "C": fit_eval(np.column_stack([x, eC]), y, np.column_stack([xt, eCt]), yt),
               "D": fit_eval(x[:, None], y, xt[:, None], yt)}
        for m, (atr, ate, z) in res.items():
            rows.append((L, r, m, atr, ate, z))
R = pd.DataFrame(rows, columns=["levels", "rep", "method", "auc_train", "auc_test", "z_enc"])
S = R.groupby(["levels", "method"]).agg(auc_train=("auc_train", "mean"), auc_test=("auc_test", "mean"),
                                        z_abs_mean=("z_enc", lambda v: np.nanmean(np.abs(v))),
                                        sig_pct=("z_enc", lambda v: np.nanmean(np.abs(v) > 1.96) * 100)).reset_index()
S["gap"] = S.auc_train - S.auc_test
S.round(4).to_csv(RES / "summary.csv", index=False)
gS = lambda L, m, c: float(S[(S.levels == L) & (S.method == m)][c].iloc[0])
LAB = {"A": "A 全体の平均", "B": "B fold の外の平均", "C": "C 平滑化（全体で計算）", "D": "D カテゴリなし"}
out = {"n_train": N, "n_test": N, "reps": REPS, "levels": LEVELS, "purchase_rate_pct": 20,
       "auc_train": {m: {str(L): round(gS(L, m, "auc_train"), 3) for L in LEVELS} for m in "ABCD"},
       "auc_test": {m: {str(L): round(gS(L, m, "auc_test"), 3) for L in LEVELS} for m in "ABCD"},
       "enc_significant_pct": {m: {str(L): round(gS(L, m, "sig_pct"), 1) for L in LEVELS} for m in "ABC"}}
json.dump(out, open(RES / "a766_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：学習とテストの AUC（1,000種類）
fig, ax = plt.subplots(figsize=(8, 3.8))
x0 = np.arange(4)
tr = [gS(1000, m, "auc_train") for m in "ABCD"]; te = [gS(1000, m, "auc_test") for m in "ABCD"]
ax.bar(x0 - 0.18, tr, 0.36, color=ORANGE, label="学習データの AUC"); ax.bar(x0 + 0.18, te, 0.36, color=BLUE, label="テストデータの AUC")
for i in range(4):
    ax.text(i - 0.18, tr[i] + 0.004, f"{tr[i]:.3f}", ha="center", fontsize=9); ax.text(i + 0.18, te[i] + 0.004, f"{te[i]:.3f}", ha="center", fontsize=9)
ax.set_xticks(x0); ax.set_xticklabels([LAB[m] for m in "ABCD"], fontsize=9); ax.set_ylim(0.6, max(tr) + 0.04); ax.set_ylabel("AUC")
ax.legend(frameon=False, loc="upper right"); ax.set_title("無関係なカテゴリ（1,000種類）を全体の平均で置きかえると、学習は上がりテストは下がる", fontsize=12)
save(fig, "a766_auc.png", SRC)
# 図2：種類の数ごとの学習とテストの差
fig, ax = plt.subplots(figsize=(7.8, 3.6))
for m, c in [("A", ORANGE), ("C", GRAY), ("B", BLUE), ("D", GREEN)]:
    ax.plot(LEVELS, [gS(L, m, "gap") for L in LEVELS], marker="o", color=c, label=LAB[m])
ax.set_xscale("log"); ax.set_xticks(LEVELS); ax.set_xticklabels([f"{L:,}種類" for L in LEVELS])
ax.set_ylabel("学習の AUC − テストの AUC"); ax.legend(frameon=False, fontsize=9)
ax.set_title("種類が多いほど、1種類あたりの件数が減り、差が開く")
save(fig, "a766_gap.png", SRC)
# 図3：置きかえた列が「有意」になった割合
fig, ax = plt.subplots(figsize=(7.8, 3.6))
for k, (m, c) in enumerate([("A", ORANGE), ("C", GRAY), ("B", BLUE)]):
    v = [gS(L, m, "sig_pct") for L in LEVELS]
    ax.bar(np.arange(3) + (k - 1) * 0.26, v, 0.26, color=c, label=LAB[m])
    for i, val in enumerate(v):
        ax.text(i + (k - 1) * 0.26, val + 1.5, f"{val:.0f}", ha="center", fontsize=8.5)
ax.axhline(5, color=GREEN, ls="--", lw=1); ax.text(2.45, 7, "5%（無関係なら本来この程度）", color=GREEN, fontsize=8.5, ha="right")
ax.set_xticks(np.arange(3)); ax.set_xticklabels([f"{L:,}種類" for L in LEVELS]); ax.set_ylabel("係数が有意（|z|>1.96）だった割合（%）")
ax.set_ylim(0, 110); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("無関係なカテゴリが「効いている」と出る割合")
save(fig, "a766_significant.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
