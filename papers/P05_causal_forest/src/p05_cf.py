"""P05 因果フォレスト：人によって違う効果（CATE）を、どこまで当てられるか。区間はどれだけ信じられるか。
架空の会員（6,000人）に割引クーポンを配った場面。配る確率は会員の特徴で変わる（交絡あり）。
真の効果は「利用頻度が高い人ほど小さい」形にしてある。種を固定して10回つくる。
比べるもの：econml の CausalForestDML（正直な分割あり／なし）と、2つのランダムフォレストの差（T-learner）
使い方: cd src && python p05_cf.py
"""
import json, warnings
from pathlib import Path
import numpy as np, pandas as pd
from econml.dml import CausalForestDML
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")
plt.rcParams["font.family"] = "Noto Sans CJK JP"
HERE = Path(__file__).resolve().parents[1]
R, FG = HERE / "results", HERE / "figures"
R.mkdir(exist_ok=True); FG.mkdir(exist_ok=True)
N, NTEST, REPS = 6000, 2000, 10


def make(rng, n):
    X = rng.normal(size=(n, 5))                      # x0 利用頻度、x1 在籍年数、x2〜x4 関係なし（標準化した値）
    tau = 1.0 - 0.8 * np.tanh(X[:, 0])               # 真の効果（月の購入額の増え方、千円）：0.2〜1.8
    p = 1 / (1 + np.exp(-(0.8 * X[:, 0] - 0.5 * X[:, 1])))   # よく使う人ほど配られやすい
    T = (rng.random(n) < p).astype(int)
    y = 3 + 1.5 * X[:, 0] + X[:, 1] + 0.5 * X[:, 2] ** 2 + tau * T + rng.normal(0, 1.5, n)
    return X, T, y, tau


rows, ex = [], None
for r in range(REPS):
    rng = np.random.default_rng(500 + r)
    X, T, y, _ = make(rng, N); Xt, _, _, tau_t = make(rng, NTEST)
    res = {}
    for honest in (True, False):
        cf = CausalForestDML(model_y=RandomForestRegressor(n_estimators=100, min_samples_leaf=20, random_state=r),
                             model_t=RandomForestClassifier(n_estimators=100, min_samples_leaf=20, random_state=r),
                             discrete_treatment=True, n_estimators=400, min_samples_leaf=10, honest=honest,
                             cv=3, random_state=r, n_jobs=1)
        cf.fit(y, T, X=X)
        est = cf.effect(Xt); lo, hi = cf.effect_interval(Xt, alpha=0.1)
        key = "因果フォレスト（正直な分割あり）" if honest else "因果フォレスト（正直な分割なし）"
        res[key] = (est, lo, hi)
    m1 = RandomForestRegressor(n_estimators=200, min_samples_leaf=10, random_state=r).fit(X[T == 1], y[T == 1])
    m0 = RandomForestRegressor(n_estimators=200, min_samples_leaf=10, random_state=r).fit(X[T == 0], y[T == 0])
    res["T-learner（2つのランダムフォレストの差）"] = (m1.predict(Xt) - m0.predict(Xt), None, None)
    for k, (est, lo, hi) in res.items():
        rows.append({"rep": r, "method": k, "rmse": float(np.sqrt(np.mean((est - tau_t) ** 2))),
                     "corr": float(np.corrcoef(est, tau_t)[0, 1]),
                     "coverage90": None if lo is None else float(np.mean((lo <= tau_t) & (tau_t <= hi))),
                     "width90": None if lo is None else float(np.mean(hi - lo)),
                     "ate_err": float(est.mean() - tau_t.mean())})
    if r == 0:
        ex = pd.DataFrame({"x0": Xt[:, 0], "tau": tau_t, **{k: v[0] for k, v in res.items()}})

df = pd.DataFrame(rows)
df.round(6).to_csv(R / "sims.csv", index=False, encoding="utf-8")
S = df.groupby("method", sort=False)[["rmse", "corr", "coverage90", "width90", "ate_err"]].mean()
S.round(4).to_csv(R / "summary.csv", encoding="utf-8")
json.dump({k: {c: (None if pd.isna(v) else round(float(v), 4)) for c, v in S.loc[k].items()} for k in S.index},
          open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
ex.round(5).to_csv(R / "example_rep0.csv", index=False, encoding="utf-8")

fig, axs = plt.subplots(1, 3, figsize=(13, 4), dpi=120, sharey=True)
o = np.argsort(ex.x0.values)
for ax, k, c in zip(axs, S.index, ["#1f5f8b", "#c0692b", "#999999"]):
    ax.scatter(ex.x0, ex[k], s=4, alpha=.35, color=c)
    ax.plot(ex.x0.values[o], ex.tau.values[o], color="#222", lw=2, label="真の効果")
    ax.set_title(f"{k}\nRMSE {S.loc[k, 'rmse']:.2f}（10回の平均）", fontsize=9.5)
    ax.set_xlabel("利用頻度（標準化）")
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
axs[0].set_ylabel("推定した効果（千円）"); axs[0].legend(fontsize=8)
fig.suptitle("人ごとの効果：因果フォレストは形をつかむが、端では真の値より平らになる（1回目のデータ）", fontsize=11)
fig.tight_layout(); fig.savefig(FG / "p05_01_cate.png"); plt.close(fig)
print(S.round(3).to_string())
