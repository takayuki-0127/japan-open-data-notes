"""P06 SHAP：よく似た2つの特徴量があるとき、SHAP と並べ替えの重要度は「効き目」をどう分けるか。
y = 2*x1 + 1*x3 + ノイズ。x2 は x1 と相関 ρ を持つが、y には効かない。ρ を 0〜0.99 で変える（種は固定）。
SHAP は LightGBM の pred_contrib（TreeSHAP）で出す（youtube-views-predictor と同じやり方）。
使い方: cd src && python p06_shap.py
"""
import json
from pathlib import Path
import numpy as np, pandas as pd
import lightgbm as lgb
from sklearn.inspection import permutation_importance
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Noto Sans CJK JP"
HERE = Path(__file__).resolve().parents[1]
R, FG = HERE / "results", HERE / "figures"
R.mkdir(exist_ok=True); FG.mkdir(exist_ok=True)
N, REPS = 4000, 10
RHOS = [0.0, 0.5, 0.8, 0.9, 0.95, 0.99]
FEATS = ["x1（効く）", "x2（x1に似ているが効かない）", "x3（効く）", "x4（関係なし）"]

rows = []
for cs in (1.0, 0.5):
  for rho in RHOS:
    for r in range(REPS):
        rng = np.random.default_rng(int(rho * 1000) * 100 + r)
        x1 = rng.normal(size=N)
        x2 = rho * x1 + np.sqrt(1 - rho ** 2) * rng.normal(size=N)
        x3 = rng.normal(size=N); x4 = rng.normal(size=N)
        X = np.column_stack([x1, x2, x3, x4]); y = 2 * x1 + x3 + rng.normal(size=N)
        tr, te = slice(0, N // 2), slice(N // 2, N)
        m = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=15, colsample_bytree=cs,
                              random_state=r, num_threads=1, verbose=-1).fit(X[tr], y[tr])
        contrib = m.booster_.predict(X[te], pred_contrib=True)[:, :4]
        shap_imp = np.abs(contrib).mean(axis=0)
        perm = permutation_importance(m, X[te], y[te], n_repeats=5, random_state=r, scoring="neg_mean_squared_error").importances_mean
        gain = m.booster_.feature_importance("gain")
        for k, f in enumerate(FEATS):
            rows.append({"colsample": cs, "rho": rho, "rep": r, "feature": f, "shap": shap_imp[k], "perm": perm[k], "gain": gain[k]})

df = pd.DataFrame(rows)
for c in ("shap", "perm", "gain"):
    df[c + "_share"] = df[c].clip(lower=0) / df.groupby(["colsample", "rho", "rep"])[c].transform(lambda s: s.clip(lower=0).sum())
df.round(6).to_csv(R / "sims.csv", index=False, encoding="utf-8")
S = df.groupby(["colsample", "rho", "feature"])[["shap_share", "perm_share", "gain_share"]].mean().reset_index()
S.round(4).to_csv(R / "summary.csv", index=False, encoding="utf-8")
pick = lambda cs, rho, f, c: round(float(S[(S.colsample == cs) & (S.rho == rho) & (S.feature == f)][c].iloc[0]), 3)
main = {f"colsample_{cs}_rho_{rho}": {k: pick(cs, rho, FEATS[i], c + "_share") for k, i, c in
                                    (("x1_shap", 0, "shap"), ("x2_shap", 1, "shap"), ("x3_shap", 2, "shap"),
                                     ("x1_perm", 0, "perm"), ("x2_perm", 1, "perm"), ("x3_perm", 2, "perm"))}
        for cs in (1.0, 0.5) for rho in RHOS}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

fig, axs = plt.subplots(2, 2, figsize=(11, 7.5), dpi=120, sharey=True, sharex=True)
cols = ["#1f5f8b", "#c0692b", "#2e7d4f", "#999999"]
for row, cs in enumerate((1.0, 0.5)):
    for ax, c, t in zip(axs[row], ["shap_share", "perm_share"], ["SHAP（|寄与| の平均）の割合", "並べ替えの重要度の割合"]):
        for f, col in zip(FEATS, cols):
            s_ = S[(S.colsample == cs) & (S.feature == f)]
            ax.plot(s_.rho, s_[c], marker="o", color=col, label=f, lw=2)
        ax.set_title(f"{t}\n木ごとに使う列の割合 {cs:.0%}", fontsize=10); ax.grid(alpha=.3)
        for sp in ("top", "right"): ax.spines[sp].set_visible(False)
for ax in axs[1]: ax.set_xlabel("x1 と x2 の相関 ρ")
for ax in axs[:, 0]: ax.set_ylabel("4つの合計に対する割合")
axs[0, 0].legend(fontsize=8.5)
fig.suptitle("効かない x2 にどれだけ割り振られるかは、相関の強さとモデルの作り方で変わる（10回の平均）", fontsize=11)
fig.tight_layout(); fig.savefig(FG / "p06_01_shares.png"); plt.close(fig)
print(json.dumps(main, ensure_ascii=False, indent=1))
