"""747 ランダムフォレストの OOB 誤差は、交差検証の誤差やテストの誤差とどれだけ合うのか

架空の回帰のデータ（Friedman #1：効く変数5つ＋効かない変数5つ、ばらつき sd 1）。
学習の件数 n＝100・300・1,000、木の数 10・30・100。各条件で次の誤差（平均二乗誤差）を出す。
  OOB（そのまま）：scikit-learn の oob_prediction_ をそのまま使う。どの木でも学習に使われた点は予測が0になっている
  OOB：各木の学習に使われなかった点（袋の外）で当てた誤差。追加の学習はいらない
  交差検証：5分割
  テスト：同じ作り方の新しいデータ5,000件（本当の成績の代わり）
くり返しは n＝100・300 で15回、n＝1,000 で8回（CPU を軽くするため）。scikit-learn、n_jobs=1。
"""
import json
import time
import warnings
import numpy as np
import pandas as pd
from sklearn.datasets import make_friedman1
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

warnings.filterwarnings("ignore")
SRC = "出典：架空のデータ（作成者が乱数で作成、seed 747）"
rng = np.random.default_rng(747)
Xt, yt = make_friedman1(n_samples=5000, n_features=10, noise=1.0, random_state=7470)
rows = []
for n in [100, 300, 1000]:
    reps = 8 if n == 1000 else 15
    for trees in [10, 30, 100]:
        for r in range(reps):
            seed = int(rng.integers(1e9))
            X, y = make_friedman1(n_samples=n, n_features=10, noise=1.0, random_state=seed)
            rf = RandomForestRegressor(n_estimators=trees, oob_score=True, n_jobs=1, random_state=seed).fit(X, y)
            oobp = rf.oob_prediction_
            inbag = np.zeros(n, int)
            for smp in rf.estimators_samples_:
                mk = np.zeros(n, bool); mk[smp] = True; inbag += mk
            ok = inbag < trees                                   # 1本以上の木で袋の外に出た点
            oob_raw = float(np.mean((y - oobp) ** 2))           # oob_prediction_ をそのまま（袋の外に出なかった点は予測0）
            oob = float(np.mean((y[ok] - oobp[ok]) ** 2)); no_oob = int((~ok).sum())
            sse = 0
            for tr, va in KFold(5, shuffle=True, random_state=seed).split(X):
                m = RandomForestRegressor(n_estimators=trees, n_jobs=1, random_state=seed).fit(X[tr], y[tr])
                sse += np.sum((y[va] - m.predict(X[va])) ** 2)
            test = float(np.mean((yt - rf.predict(Xt)) ** 2))
            rows.append(dict(n=n, trees=trees, rep=r, oob_raw=oob_raw, oob=oob, cv=sse / n, test=test, no_oob_points=no_oob))
D = pd.DataFrame(rows); D.to_csv(RES / "all_runs.csv", index=False)
S = D.groupby(["n", "trees"]).agg(oob_raw=("oob_raw", "mean"), oob=("oob", "mean"), cv=("cv", "mean"), test=("test", "mean"),
                                   no_oob=("no_oob_points", "mean"), reps=("rep", "size")).reset_index()
S["oob_raw_vs_test"] = S.oob_raw / S.test - 1; S["oob_vs_test"] = S.oob / S.test - 1; S["cv_vs_test"] = S.cv / S.test - 1
S.to_csv(RES / "summary.csv", index=False)
D["oob_err"] = D.oob / D.test - 1; D["cv_err"] = D.cv / D.test - 1
spread = D.groupby(["n", "trees"]).agg(oob_abs=("oob_err", lambda s: s.abs().mean()), cv_abs=("cv_err", lambda s: s.abs().mean())).reset_index()
spread.to_csv(RES / "abs_error.csv", index=False)
g = lambda n, t, c: float(S[(S.n == n) & (S.trees == t)][c].iloc[0])
out = {"test_size": 5000, "by": {f"n{n}_trees{t}": {c: round(g(n, t, c), 3) for c in ["oob_raw", "oob", "cv", "test", "oob_raw_vs_test", "oob_vs_test", "cv_vs_test", "no_oob"]}
                                 for n in [100, 300, 1000] for t in [10, 30, 100]},
       "n300_t100_oob_vs_test": g(300, 100, "oob_vs_test"), "n300_t100_cv_vs_test": g(300, 100, "cv_vs_test"),
       "n100_t10_oob_vs_test": g(100, 10, "oob_vs_test"), "n100_t10_oob_raw_vs_test": g(100, 10, "oob_raw_vs_test"), "n300_t10_oob_raw_vs_test": g(300, 10, "oob_raw_vs_test"), "n300_t10_oob_vs_test": g(300, 10, "oob_vs_test"), "n300_t10_cv_vs_test": g(300, 10, "cv_vs_test"), "n300_t30_oob_raw_vs_test": g(300, 30, "oob_raw_vs_test"), "n100_t10_cv_vs_test": g(100, 10, "cv_vs_test"),
       "n1000_t100_oob_vs_test": g(1000, 100, "oob_vs_test"), "n1000_t100_cv_vs_test": g(1000, 100, "cv_vs_test"),
       "n100_t10_no_oob_points": g(100, 10, "no_oob"),
       "fits_per_run": {"oob": 1, "cv": 5}}
json.dump(out, open(RES / "a747_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：木の数ごとの、テストに対するずれ
fig, axs = plt.subplots(1, 3, figsize=(10, 4), sharey=True)
for ax, n in zip(axs, [100, 300, 1000]):
    d = S[S.n == n]; x = np.arange(3); w = .27
    for j, (c, l, colr) in enumerate([("oob_raw_vs_test", "OOB（予測0の点も含む）", LIGHT), ("oob_vs_test", "OOB（袋の外に出た点だけ）", ORANGE), ("cv_vs_test", "5分割の交差検証", BLUE)]):
        ax.bar(x + (j - 1) * w, (d[c] * 100).clip(upper=60), w, color=colr, label=l)
        for i, v in enumerate(d[c]):
            ax.text(i + (j - 1) * w, min(v * 100, 60) + 1, f"{v * 100:.0f}", ha="center", fontsize=7)
    ax.axhline(0, color=GRAY, lw=1); ax.set_xticks(x); ax.set_xticklabels(d.trees); ax.set_xlabel("木の数"); ax.set_title(f"学習 {n}件", fontsize=11)
    ax.set_ylim(-5, 68)
axs[0].set_ylabel("テストの誤差とのずれ（%、60で切る）"); axs[0].legend(frameon=False, fontsize=8, loc="upper right")
fig.suptitle("木が100本なら OOB は交差検証と同じくらい当たる。10本では大きく外れる", y=1.03)
save(fig, "a747_bias.png", SRC, y=-0.05)

# 図2：1回ごとのずれ（n=300、木100）
fig, ax = plt.subplots(figsize=(9, 4.6))
d = D[(D.n == 300) & (D.trees == 100)]
ax.scatter(d.test, d.oob, color=ORANGE, label="OOB", s=30)
ax.scatter(d.test, d.cv, color=BLUE, label="5分割の交差検証", s=30, marker="s")
lo, hi = min(d[["test", "oob", "cv"]].min()) * .9, max(d[["test", "oob", "cv"]].max()) * 1.05
ax.plot([lo, hi], [lo, hi], color=GRAY, lw=1)
ax.set_xlabel("テストの誤差（新しい5,000件）"); ax.set_ylabel("見積もった誤差"); ax.legend(frameon=False)
ax.set_title("学習300件・木100本：1回ごとの見積もり（15回）")
save(fig, "a747_scatter.png", SRC)

# 図3：袋の外に一度も入らない点（木が少ないとき）
fig, ax = plt.subplots(figsize=(9, 4.6))
for n, c in zip([100, 300, 1000], [LIGHT, BLUE, ORANGE]):
    d = S[S.n == n]; ax.plot(d.trees, d.no_oob / n * 100, "o-", color=c, label=f"学習 {n}件")
ax.set_xscale("log"); ax.set_xticks([10, 30, 100]); ax.set_xticklabels([10, 30, 100])
ax.set_xlabel("木の数"); ax.set_ylabel("OOB の予測がない点の割合（%）")
ax.plot([10, 30, 100], [(1 - np.exp(-1)) ** t * 100 for t in [10, 30, 100]], "--", color=GRAY, label="目安 0.632^木の数"); ax.legend(frameon=False)
ax.set_title("木が少ないと、どの木でも学習に使われ OOB の予測がない点が残る")
save(fig, "a747_no_oob.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
