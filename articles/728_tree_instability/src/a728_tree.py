"""728 決定木を学習データを少し入れ替えて作り直すと、最初の分かれ目の変数は何%で入れ替わるのか

架空の店の来店客500人の購入額（千円）。変数は6つ：
  x1 と x2：相関0.8の2つの変数（どちらも購入額に効く。効き方は x1 がやや強い）
  x3：購入額に効く（弱い）、x4〜x6：効かない
購入額 ＝ 2.0×x1 ＋ 1.6×x2 ＋ 0.8×x3 ＋ ノイズ（標準偏差2）
もとの500人で深さ4の決定木を作り、そのあと「500人のうち50人（10%）を新しい50人に入れ替えた」データで作り直す（300回）。
  最初の分かれ目の変数が、もとの木と同じだった割合
  2段目までに使った変数の組が同じだった割合
  テスト用の1,000人への予測が、もとの木とどれだけ違うか
同じことをランダムフォレスト（木100本）でも行い、予測の変わり方を比べる（50回）。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の来店客の購入額（作成者が乱数で作成、seed 728）"
rng = np.random.default_rng(728)
N, NEW = 500, 50
NAMES = ["x1", "x2", "x3", "x4", "x5", "x6"]


def make(n):
    z = rng.normal(0, 1, (n, 6))
    z[:, 1] = 0.8 * z[:, 0] + 0.6 * z[:, 1]
    y = 2.0 * z[:, 0] + 1.6 * z[:, 1] + 0.8 * z[:, 2] + rng.normal(0, 2, n)
    return z, y


def top_feats(tree):
    t = tree.tree_; f = t.feature
    root = f[0]; lv2 = {f[t.children_left[0]], f[t.children_right[0]]}
    return int(root), frozenset({int(root)} | {int(v) for v in lv2 if v >= 0})


X0, y0 = make(N); Xt, yt = make(1000)
base = DecisionTreeRegressor(max_depth=4, random_state=0).fit(X0, y0)
r0, s0 = top_feats(base); p0 = base.predict(Xt)
REPS = 300
roots, same_set, pdiff, rmse = [], [], [], []
for r in range(REPS):
    keep = rng.choice(N, N - NEW, replace=False); Xn, yn = make(NEW)
    X = np.vstack([X0[keep], Xn]); y = np.r_[y0[keep], yn]
    tr = DecisionTreeRegressor(max_depth=4, random_state=0).fit(X, y)
    rr, ss = top_feats(tr); roots.append(NAMES[rr]); same_set.append(ss == s0)
    p = tr.predict(Xt); pdiff.append(np.mean(np.abs(p - p0))); rmse.append(np.sqrt(np.mean((p - yt) ** 2)))
roots = pd.Series(roots)

# ランダムフォレスト
rf0 = RandomForestRegressor(n_estimators=100, max_depth=None, min_samples_leaf=5, random_state=1, n_jobs=1).fit(X0, y0)
q0 = rf0.predict(Xt); RFREPS = 50; rf_diff, rf_rmse, tr_diff_same = [], [], []
for r in range(RFREPS):
    keep = rng.choice(N, N - NEW, replace=False); Xn, yn = make(NEW)
    X = np.vstack([X0[keep], Xn]); y = np.r_[y0[keep], yn]
    rf = RandomForestRegressor(n_estimators=100, max_depth=None, min_samples_leaf=5, random_state=1, n_jobs=1).fit(X, y)
    q = rf.predict(Xt); rf_diff.append(np.mean(np.abs(q - q0))); rf_rmse.append(np.sqrt(np.mean((q - yt) ** 2)))

rc = roots.value_counts()
pd.DataFrame({"root_feature": roots, "same_top_set": same_set, "pred_mean_abs_diff": pdiff, "test_rmse": rmse}).round(4).to_csv(RES / "tree_reps.csv", index=False)
out = {"n": N, "replaced": NEW, "reps": REPS, "depth": 4, "base_root": NAMES[r0], "base_top_set": sorted(NAMES[i] for i in s0),
       "root_share_pct": {k: round(float(v / REPS * 100), 1) for k, v in rc.items()},
       "root_same_as_base_pct": round(float((roots == NAMES[r0]).mean() * 100), 1),
       "top_set_same_pct": round(float(np.mean(same_set) * 100), 1),
       "tree_pred_mean_abs_diff": round(float(np.mean(pdiff)), 3), "tree_test_rmse": round(float(np.mean(rmse)), 3),
       "tree_pred_diff_root_changed": round(float(np.mean(np.array(pdiff)[(roots != NAMES[r0]).values])), 3) if (roots != NAMES[r0]).any() else None,
       "tree_pred_diff_root_same": round(float(np.mean(np.array(pdiff)[(roots == NAMES[r0]).values])), 3),
       "rf_reps": RFREPS, "rf_pred_mean_abs_diff": round(float(np.mean(rf_diff)), 3), "rf_test_rmse": round(float(np.mean(rf_rmse)), 3),
       "base_tree_test_rmse": round(float(np.sqrt(np.mean((p0 - yt) ** 2))), 3), "corr_x1_x2": round(float(np.corrcoef(X0[:, 0], X0[:, 1])[0, 1]), 3),
       "y_sd": round(float(y0.std()), 2)}
json.dump(out, open(RES / "a728_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：最初の分かれ目の変数
fig, ax = plt.subplots(figsize=(7, 3.6))
vals = [rc.get(k, 0) / REPS * 100 for k in NAMES]
ax.bar(NAMES, vals, color=[BLUE if k == NAMES[r0] else ORANGE for k in NAMES])
for i, v in enumerate(vals): ax.text(i, v + 1.5, f"{v:.0f}%", ha="center", fontsize=9)
ax.set_ylabel("最初の分かれ目に選ばれた割合（%）"); ax.set_ylim(0, 105)
ax.set_title(f"10%を入れ替えるだけで、最初の分かれ目が {100 - out['root_same_as_base_pct']:.0f}% で入れ替わる（青がもとの木）", fontsize=11.5)
save(fig, "a728_root.png", SRC)

# 図2：もとの木との予測の違い（分かれ目が同じ回・違う回）
fig, ax = plt.subplots(figsize=(8, 3.6)); pdv = np.array(pdiff); same = (roots == NAMES[r0]).values
bins = np.linspace(0, pdv.max() * 1.05, 30)
ax.hist(pdv[same], bins=bins, color=BLUE, alpha=0.7, label=f"最初の分かれ目が同じ（{same.sum()}回）")
ax.hist(pdv[~same], bins=bins, color=ORANGE, alpha=0.7, label=f"入れ替わった（{(~same).sum()}回）")
ax.set_xlabel("テストの1,000人への予測の、もとの木との平均の差（千円）"); ax.set_ylabel("回数"); ax.legend(frameon=False, fontsize=9)
ax.set_title(f"分かれ目が同じでも予測は平均{out['tree_pred_diff_root_same']:.2f}千円、入れ替わると{out['tree_pred_diff_root_changed']:.2f}千円動く")
save(fig, "a728_pred_diff.png", SRC)

# 図3：決定木とランダムフォレスト
fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
axes[0].bar(["決定木（深さ4）", "ランダムフォレスト"], [out["tree_pred_mean_abs_diff"], out["rf_pred_mean_abs_diff"]], color=[ORANGE, BLUE])
for i, v in enumerate([out["tree_pred_mean_abs_diff"], out["rf_pred_mean_abs_diff"]]): axes[0].text(i, v + 0.02, f"{v:.2f}", ha="center")
axes[0].set_ylabel("もとのモデルとの予測の差（千円）"); axes[0].set_title("入れ替えによる予測の変わり方")
axes[1].bar(["決定木（深さ4）", "ランダムフォレスト"], [out["tree_test_rmse"], out["rf_test_rmse"]], color=[ORANGE, BLUE])
for i, v in enumerate([out["tree_test_rmse"], out["rf_test_rmse"]]): axes[1].text(i, v + 0.03, f"{v:.2f}", ha="center")
axes[1].set_ylabel("テストの誤差（RMSE、千円）"); axes[1].set_title("テストの誤差")
fig.suptitle("木を平均するランダムフォレストは、入れ替えに強い", y=1.02)
save(fig, "a728_tree_vs_rf.png", SRC)
print(json.dumps(out, ensure_ascii=False))
