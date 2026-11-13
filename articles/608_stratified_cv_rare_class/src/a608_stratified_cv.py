"""608 件数の少ないクラスがあるとき、層化しない交差検証では何%の fold にそのクラスが入らないのか

架空の解約予測のデータ（2,000件、特徴量5つ、解約は1%＝約20件）を作り、ロジスティック回帰を交差検証で評価する。
  KF ふつうの K-fold（並べ替えてから K 等分）
  SKF 層化 K-fold（各 fold の解約の割合をそろえる）
K=5・10 で、解約が0件の fold の割合、fold ごとの AUC の散らばり、CV の AUC（fold の平均）の振れを比べる。
解約の割合を 0.5〜5% で変えた比較も行う（こちらは学習を省き、点数の作り方を固定して分け方だけを比べる）。
データ200組、seed 608。
"""
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.metrics import roc_auc_score
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

warnings.filterwarnings("ignore")
SRC = "出典：シミュレーション（作成者が乱数で作成、seed 608）"
rng = np.random.default_rng(608)
N, P = 2000, 5
BETA = np.array([0.9, 0.6, 0.4, 0.0, 0.0])


def make(rate, rs):
    X = rs.standard_normal((N, P))
    lin = X @ BETA
    e = rs.logistic(size=N)
    # 切片を合わせて、解約の割合をちょうど rate にする
    b0 = -np.quantile(lin + e, 1 - rate)
    y = (lin + e + b0 > 0).astype(int)
    return X, y


def cv_eval(X, y, K, strat, seed, fit=True):
    spl = StratifiedKFold(K, shuffle=True, random_state=seed) if strat else KFold(K, shuffle=True, random_state=seed)
    aucs, zero, pos = [], 0, []
    for tr, te in spl.split(X, y):
        npos = int(y[te].sum()); pos.append(npos)
        if npos == 0 or npos == len(te):
            zero += 1; continue
        if fit:
            if y[tr].sum() == 0:
                continue
            m = LogisticRegression(C=1.0, max_iter=200).fit(X[tr], y[tr])
            s = m.decision_function(X[te])
        else:
            s = X[te] @ BETA
        aucs.append(roc_auc_score(y[te], s))
    return aucs, zero, pos


rows, fold_auc = [], []
for d in range(200):
    rs = np.random.default_rng(608_000 + d)
    X, y = make(0.01, rs)
    # 正解に近い AUC：同じ作り方の大きなデータで本当の係数を使った AUC
    for K in [5, 10]:
        for strat in [False, True]:
            aucs, zero, pos = cv_eval(X, y, K, strat, seed=d)
            rows.append({"data": d, "K": K, "strat": strat, "n_pos": int(y.sum()), "zero_folds": zero, "cv_auc": float(np.mean(aucs)),
                         "fold_auc_sd": float(np.std(aucs, ddof=1)), "min_pos_in_fold": int(min(pos)), "max_pos_in_fold": int(max(pos))})
            if d < 50:
                fold_auc += [{"K": K, "strat": strat, "auc": a} for a in aucs]
df = pd.DataFrame(rows); df.to_csv(RES / "main_rate1pct.csv", index=False)
pd.DataFrame(fold_auc).to_csv(RES / "fold_auc_first50.csv", index=False)
# 本当の AUC（大きなデータ・本当の係数）
big = np.random.default_rng(3); Xl = big.standard_normal((400000, P)); lin = Xl @ BETA; el = big.logistic(size=400000)
yl = (lin + el - np.quantile(lin + el, 0.99) > 0).astype(int)
true_auc = float(roc_auc_score(yl, lin))

# 解約の割合を変える（学習なし、分け方だけ）
sweep = []
for rate in [0.005, 0.01, 0.02, 0.05]:
    for K in [5, 10]:
        for strat in [False, True]:
            z, any0, sds = [], [], []
            for d in range(300):
                rs = np.random.default_rng(608_500 + d)
                X, y = make(rate, rs)
                aucs, zero, pos = cv_eval(X, y, K, strat, seed=d, fit=False)
                z.append(zero / K); any0.append(zero > 0); sds.append(np.std(aucs, ddof=1) if len(aucs) > 1 else np.nan)
            sweep.append({"rate": rate, "K": K, "strat": strat, "zero_fold_share_pct": round(100 * np.mean(z), 2),
                          "any_zero_fold_pct": round(100 * np.mean(any0), 1), "fold_auc_sd_mean": round(float(np.nanmean(sds)), 4)})
sw = pd.DataFrame(sweep); sw.to_csv(RES / "by_rate.csv", index=False)


def g(K, strat, col, f=np.mean):
    return float(f(df[(df.K == K) & (df.strat == strat)][col]))


out = {"datasets": 200, "n": N, "pos_mean": round(float(df.n_pos.mean()), 1), "true_auc": round(true_auc, 4),
       "main": {f"K{K}_{'SKF' if s else 'KF'}": {"zero_fold_share_pct": round(100 * g(K, s, "zero_folds") / K, 2),
                                                 "any_zero_fold_pct": round(100 * g(K, s, "zero_folds", lambda v: (v > 0).mean()), 1),
                                                 "fold_auc_sd_mean": round(g(K, s, "fold_auc_sd"), 4),
                                                 "cv_auc_mean": round(g(K, s, "cv_auc"), 4), "cv_auc_sd": round(g(K, s, "cv_auc", np.std), 4),
                                                 "pos_range_mean": [round(g(K, s, "min_pos_in_fold"), 2), round(g(K, s, "max_pos_in_fold"), 2)]}
                for K in [5, 10] for s in [False, True]},
       "by_rate": sweep}
json.dump(out, open(RES / "a608_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：解約0件の fold の割合（解約の割合ごと）
fig, ax = plt.subplots(figsize=(8, 3.8))
for K, mk in [(5, "o"), (10, "s")]:
    s = sw[(sw.K == K) & (~sw.strat)]; t = sw[(sw.K == K) & (sw.strat)]
    ax.plot(s.rate * 100, s.zero_fold_share_pct, marker=mk, color=ORANGE if K == 10 else BLUE, label=f"ふつうの {K}-fold")
    ax.plot(t.rate * 100, t.zero_fold_share_pct, marker=mk, color=GREEN, ls="--", label=f"層化 {K}-fold" if K == 5 else None)
ax.set_xscale("log"); ax.set_xticks([0.5, 1, 2, 5]); ax.set_xticks([], minor=True); ax.set_xticklabels(["0.5%", "1%", "2%", "5%"])
ax.set_xlabel("解約の割合（2,000件のうち）"); ax.set_ylabel("解約が0件の fold の割合（%）")
ax.legend(frameon=False, fontsize=9); ax.set_title("ふつうの K-fold では、少ないクラスが入らない fold ができる")
save(fig, "a608_zero_folds.png", SRC)
# 図2：fold ごとの AUC（解約1%、最初の50組）
fa = pd.DataFrame(fold_auc)
fig, ax = plt.subplots(figsize=(8, 3.8))
grp = [("ふつうの5-fold", 5, False, BLUE), ("層化5-fold", 5, True, GREEN), ("ふつうの10-fold", 10, False, ORANGE), ("層化10-fold", 10, True, LIGHT)]
data = [fa[(fa.K == K) & (fa.strat == s)].auc for _, K, s, _ in grp]
bp = ax.boxplot(data, tick_labels=[g_[0] for g_ in grp], patch_artist=True, widths=0.5, flierprops={"markersize": 3})
for b, (_, _, _, c) in zip(bp["boxes"], grp):
    b.set_facecolor(c); b.set_alpha(0.7)
ax.axhline(true_auc, color=GRAY, ls=":", lw=1)
ax.set_ylabel("fold ごとの AUC"); ax.set_title("解約1%（約20件）：fold ごとの AUC の散らばり（点線は本当の AUC）")
save(fig, "a608_fold_auc.png", SRC)
# 図3：CV の AUC（fold の平均）の振れ
fig, ax = plt.subplots(figsize=(8, 3.6))
lab = [g_[0] for g_ in grp]
sd = [out["main"][f"K{K}_{'SKF' if s else 'KF'}"]["cv_auc_sd"] for _, K, s, _ in grp]
zero_any = [out["main"][f"K{K}_{'SKF' if s else 'KF'}"]["any_zero_fold_pct"] for _, K, s, _ in grp]
ax.bar(lab, sd, color=[c for *_, c in grp])
for i, (x, z) in enumerate(zip(sd, zero_any)):
    ax.text(i, x, f"{x:.3f}\n（0件の fold あり {z:.0f}%）", ha="center", va="bottom", fontsize=9)
ax.set_ylim(0, max(sd) * 1.35); ax.set_ylabel("CV の AUC の標準偏差（データ200組）")
ax.set_title("交差検証で出した AUC の振れ（解約1%）")
save(fig, "a608_cv_auc_sd.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
