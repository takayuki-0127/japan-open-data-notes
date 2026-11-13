"""628 ランダムフォレストの不純度による重要度は、値の種類の多い列をどれだけ重く見るのか

架空の申込みデータ（学習 1,000件・確かめ 1,000件）。結果（申込みの有無）に効くのは2列だけ：
  x1 連続の値、x2 0/1 の区分（効き方は同じくらいに置く）
効かない列を4つ足す：n2 0/1（2種類）、n10 10種類の区分、n100 100種類の区分、ncont 連続の値（ほぼすべて違う値）。区分は整数の番号で入れる。
ランダムフォレスト（200本）の不純度による重要度（feature_importances_）と、確かめデータで並べ替えたときの重要度（AUC の下がり方）を50回比べる。
数字は置いたデータで決まる。
"""
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の申込みデータ（作成者が乱数で作成、seed 628）"
rng = np.random.default_rng(628)
NTR, NTE, REPS = 1000, 1000, 50
COLS = ["x1", "x2", "n2", "n10", "n100", "ncont"]
LAB = {"x1": "x1 連続（効く）", "x2": "x2 0/1（効く）", "n2": "n2 0/1（効かない）", "n10": "n10 10種類（効かない）",
       "n100": "n100 100種類（効かない）", "ncont": "ncont 連続（効かない）"}


def make(n, rng):
    x1 = rng.normal(0, 1, n); x2 = rng.integers(0, 2, n)
    lin = 0.9 * x1 + 1.8 * (x2 - 0.5)
    y = (rng.random(n) < 1 / (1 + np.exp(-lin))).astype(int)
    X = pd.DataFrame({"x1": x1, "x2": x2, "n2": rng.integers(0, 2, n), "n10": rng.integers(0, 10, n),
                      "n100": rng.integers(0, 100, n), "ncont": rng.normal(0, 1, n)})
    return X, y


imp, per, auc = [], [], []
for r in range(REPS):
    Xtr, ytr = make(NTR, rng); Xte, yte = make(NTE, rng)
    rf = RandomForestClassifier(n_estimators=200, random_state=r, n_jobs=1).fit(Xtr, ytr)
    imp.append(dict(zip(COLS, rf.feature_importances_)))
    pi = permutation_importance(rf, Xte, yte, scoring="roc_auc", n_repeats=5, random_state=r, n_jobs=1)
    per.append(dict(zip(COLS, pi.importances_mean)))
IMP = pd.DataFrame(imp); PER = pd.DataFrame(per)
IMP.round(5).to_csv(RES / "impurity_reps.csv", index=False); PER.round(5).to_csv(RES / "permutation_reps.csv", index=False)
summ = pd.DataFrame({"impurity_mean": IMP.mean(), "impurity_sd": IMP.std(), "perm_mean": PER.mean(), "perm_sd": PER.std(),
                     "impurity_rank_mean": IMP.rank(axis=1, ascending=False).mean(), "perm_rank_mean": PER.rank(axis=1, ascending=False).mean()})
summ.round(4).to_csv(RES / "summary.csv")
above = {}
for c in ["n2", "n10", "n100", "ncont"]:
    above[c] = {"impurity_above_x2_pct": 100 * float((IMP[c] > IMP.x2).mean()), "perm_above_x2_pct": 100 * float((PER[c] > PER.x2).mean())}
noise_share = float(IMP[["n2", "n10", "n100", "ncont"]].sum(1).mean())
out = {"reps": REPS, "n_train": NTR, "trees": 200, "summary": summ.round(4).to_dict(orient="index"), "noise_above_x2": above,
       "impurity_share_of_noise_cols_mean": round(noise_share, 4)}
json.dump(out, open(RES / "a628_main.json", "w"), ensure_ascii=False, indent=1)

COL = [BLUE, BLUE, GRAY, GRAY, ORANGE, ORANGE]
# 図1
fig, ax = plt.subplots(figsize=(8.5, 4))
v = summ.impurity_mean[COLS] * 100
ax.barh([LAB[c] for c in COLS][::-1], v[::-1], xerr=summ.impurity_sd[COLS][::-1] * 100, color=COL[::-1], ecolor=GRAY)
for i, vv in enumerate(v[::-1]):
    ax.text(vv + 1.2, i, f"{vv:.1f}%", va="center", fontsize=9)
ax.set_xlabel("不純度による重要度（合計100%、50回の平均）"); ax.set_xlim(0, v.max() * 1.35)
ax.set_title("不純度による重要度：効かない連続の列が、効く 0/1 の列より上")
save(fig, "a628_impurity.png", SRC)

# 図2
fig, ax = plt.subplots(figsize=(8.5, 4))
v = summ.perm_mean[COLS]
ax.barh([LAB[c] for c in COLS][::-1], v[::-1], xerr=summ.perm_sd[COLS][::-1], color=COL[::-1], ecolor=GRAY)
for i, vv in enumerate(v[::-1]):
    ax.text(max(vv, 0) + 0.004, i, f"{vv:.3f}", va="center", fontsize=9)
ax.axvline(0, color=INK, lw=0.6); ax.set_xlabel("並べ替えたときの AUC の下がり方（確かめデータ、50回の平均）")
ax.set_title("並べ替えの重要度：効かない列はほぼ0")
save(fig, "a628_permutation.png", SRC)

# 図3
fig, ax = plt.subplots(figsize=(8.5, 4))
cs = ["n2", "n10", "n100", "ncont"]; xs = np.arange(4); w = 0.38
a = [above[c]["impurity_above_x2_pct"] for c in cs]; b = [above[c]["perm_above_x2_pct"] for c in cs]
ax.bar(xs - w / 2, a, w, color=ORANGE, label="不純度による重要度")
ax.bar(xs + w / 2, b, w, color=BLUE, label="並べ替えの重要度")
for x, vv in zip(xs - w / 2, a):
    ax.text(x, vv + 1, f"{vv:.0f}%", ha="center", fontsize=9)
for x, vv in zip(xs + w / 2, b):
    ax.text(x, vv + 1, f"{vv:.0f}%", ha="center", fontsize=9)
ax.set_xticks(xs); ax.set_xticklabels([LAB[c] for c in cs], fontsize=9); ax.set_ylim(0, 112)
ax.set_ylabel("効く x2 より上に出た回の割合（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("効かない列が、効く 0/1 の列（x2）より重要に出た割合")
save(fig, "a628_above_x2.png", SRC)
print(summ.round(4)); print(above, noise_share)
