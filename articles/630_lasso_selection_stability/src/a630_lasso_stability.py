"""630 Lasso で選ばれる変数は、データを少し変えるとどれだけ入れ替わるのか

架空のデータ（150件）。候補の変数は40個で、本当に効くのは6個（係数 0.5）。
効く変数にはそれぞれ「よく似た効かない変数」が1つずつあり（相関0.7）、ほかの変数どうしは相関0.2。
LassoCV（5分割で強さを選ぶ）で選んだ変数が、
  1) 同じデータから8割（120件）を取り出して当て直す50回でどれだけ入れ替わるか（選ばれる割合・2回の選択の重なり＝ジャカード係数）
  2) 安定選択（半分を取り出して Lasso を当てる 100回、強さは元の CV の値、70%以上の回で選ばれた変数を残す）では何が残るか
を、独立に作った10組のデータで数える。数字は置いたデータで決まる。
"""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LassoCV, Lasso
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 630）"
rng = np.random.default_rng(630)
N, P, K, B, NSUB, DATASETS = 150, 40, 6, 50, 100, 10
TRUE = np.arange(K); TWIN = np.arange(K, 2 * K)
C = np.full((P, P), 0.2); np.fill_diagonal(C, 1)
for a, b in zip(TRUE, TWIN):
    C[a, b] = C[b, a] = 0.7
L = np.linalg.cholesky(C)
beta = np.zeros(P); beta[TRUE] = 0.5


def make(rng):
    X = rng.standard_normal((N, P)) @ L.T
    y = X @ beta + rng.normal(0, 1, N)
    return StandardScaler().fit_transform(X), y


def jacc(a, b):
    a, b = set(a), set(b)
    return len(a & b) / max(len(a | b), 1)


rows, freq_all, stab_rows, jac_all = [], [], [], []
for d in range(DATASETS):
    X, y = make(rng)
    cv = LassoCV(cv=5, alphas=30, random_state=d, max_iter=5000).fit(X, y)
    sel0 = np.nonzero(cv.coef_)[0]
    sels = []
    for b in range(B):
        idx = rng.choice(N, int(N * 0.8), replace=False)
        m = LassoCV(cv=5, alphas=30, random_state=b, max_iter=5000).fit(X[idx], y[idx])
        sels.append(np.nonzero(m.coef_)[0])
    f = np.zeros(P)
    for s in sels:
        f[s] += 1
    freq_all.append(f / B)
    jac = [jacc(sels[i], sels[j]) for i in range(B) for j in range(i + 1, B)]
    jac_all.append(np.mean(jac))
    # 安定選択
    cnt = np.zeros(P)
    for s_ in range(NSUB):
        idx = rng.choice(N, N // 2, replace=False)
        m = Lasso(alpha=cv.alpha_, max_iter=5000).fit(X[idx], y[idx])
        cnt[np.nonzero(m.coef_)[0]] += 1
    stab = np.nonzero(cnt / NSUB >= 0.7)[0]
    sizes = [len(s) for s in sels]
    rows.append({"dataset": d, "cv_selected": len(sel0), "cv_true": int(np.isin(sel0, TRUE).sum()), "cv_twin": int(np.isin(sel0, TWIN).sum()),
                 "cv_other": int(len(sel0) - np.isin(sel0, TRUE).sum() - np.isin(sel0, TWIN).sum()),
                 "boot_size_min": int(min(sizes)), "boot_size_max": int(max(sizes)), "boot_jaccard_mean": float(np.mean(jac)),
                 "stab_selected": len(stab), "stab_true": int(np.isin(stab, TRUE).sum()), "stab_false": int(len(stab) - np.isin(stab, TRUE).sum())})
R = pd.DataFrame(rows); R.round(4).to_csv(RES / "by_dataset.csv", index=False)
F = np.array(freq_all)
FR = pd.DataFrame({"var": [f"v{i+1:02d}" for i in range(P)], "kind": ["効く"] * K + ["効く変数の似た列"] * K + ["その他"] * (P - 2 * K),
                   "boot_freq_mean": F.mean(0)})
FR.round(4).to_csv(RES / "boot_freq.csv", index=False)
summ = {"cv_selected_mean": float(R.cv_selected.mean()), "cv_true_mean": float(R.cv_true.mean()), "cv_twin_mean": float(R.cv_twin.mean()),
        "cv_other_mean": float(R.cv_other.mean()), "boot_jaccard_mean": float(R.boot_jaccard_mean.mean()),
        "boot_freq_true_mean": float(F[:, TRUE].mean()), "boot_freq_twin_mean": float(F[:, TWIN].mean()), "boot_freq_other_mean": float(F[:, 2 * K:].mean()),
        "share_other_vars_selected_in_some_boot_pct": float(100 * (F[:, 2 * K:] > 0).mean()),
        "stab_selected_mean": float(R.stab_selected.mean()), "stab_true_mean": float(R.stab_true.mean()), "stab_false_mean": float(R.stab_false.mean()),
        "boot_size_range": [int(R.boot_size_min.min()), int(R.boot_size_max.max())]}
pd.DataFrame([summ]).round(4).to_csv(RES / "summary.csv", index=False)
json.dump({"n": N, "p": P, "true": K, "boot": B, "subsamples": NSUB, "datasets": DATASETS, "summary": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in summ.items()},
           "by_dataset": R.round(4).to_dict(orient="records")}, open(RES / "a630_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：ブートストラップで選ばれる割合（1組目）
fig, ax = plt.subplots(figsize=(9.5, 4))
col = [BLUE] * K + [ORANGE] * K + [GRAY] * (P - 2 * K)
ax.bar(np.arange(P), F[0] * 100, color=col)
ax.set_xlabel("候補の変数（青＝効く6個、橙＝それぞれによく似た効かない列、灰＝その他）"); ax.set_ylabel("選ばれた割合（%）")
ax.set_title("1組目のデータ：8割を取り出して当て直す50回で、各変数が選ばれた割合"); ax.set_xticks([])
save(fig, "a630_boot_freq.png", SRC)

# 図2：選ばれた数の内訳（CV の1回、10組）
fig, ax = plt.subplots(figsize=(8.5, 4))
x = np.arange(DATASETS)
ax.bar(x, R.cv_true, color=BLUE, label="効く変数")
ax.bar(x, R.cv_twin, bottom=R.cv_true, color=ORANGE, label="効く変数によく似た列")
ax.bar(x, R.cv_other, bottom=R.cv_true + R.cv_twin, color=GRAY, label="その他の効かない変数")
ax.set_xticks(x); ax.set_xticklabels([f"{i+1}" for i in x]); ax.set_xlabel("データの組"); ax.set_ylabel("選ばれた変数の数")
ax.set_title("交差検証で強さを選んだ Lasso が選んだ変数（40個中）"); ax.legend(frameon=False, fontsize=9)
save(fig, "a630_cv_selected.png", SRC)

# 図3：安定選択
fig, ax = plt.subplots(figsize=(8.5, 4))
ax.bar(x - 0.2, R.stab_true, 0.4, color=BLUE, label="残った効く変数")
ax.bar(x + 0.2, R.stab_false, 0.4, color=ORANGE, label="残った効かない変数")
ax.axhline(K, color=GRAY, ls=":")
ax.set_xticks(x); ax.set_xticklabels([f"{i+1}" for i in x]); ax.set_xlabel("データの組"); ax.set_ylabel("変数の数")
ax.set_title("安定選択（半分を100回、70%以上で選ばれた変数）で残った変数"); ax.legend(frameon=False, fontsize=9)
save(fig, "a630_stability_selection.png", SRC)
print(R.round(3).to_string()); print(summ)
