"""頑健性：ハイパーパラメータ・期間・結果の指標・乱数の種・処置の入れ替え（プラセボ）"""
import json, numpy as np, pandas as pd
import statsmodels.api as sm
from scipy.stats import spearmanr
from sklearn.model_selection import GroupKFold
from common import DATA, RES, X_COLS, SEED
import importlib; m = importlib.import_module("02_forest")

df = pd.read_csv(DATA / "f17_panel.csv")
main = pd.read_csv(RES / "pref_effects.csv").set_index("code")["tau"]

def run(label, d, outcome="d_emp", cv=False, **kw):
    cf = m.fit_cf(d, outcome=outcome, **kw)
    Y, T, X, W, g = m.arrays(d, outcome)
    ate = cf.ate_inference(X=X); lo, hi = ate.conf_int_mean(alpha=0.05)
    tau = cf.effect(X)
    yr, tr = cf.residuals_[0].ravel(), cf.residuals_[1].ravel()
    cen = tau - tau.mean()
    blp = sm.OLS(yr, np.column_stack([tr, tr * cen])).fit(cov_type="cluster", cov_kwds={"groups": g})
    pt = pd.Series(tau, index=d.code.values).groupby(level=0).mean()
    rho = spearmanr(pt.reindex(main.index), main).correlation
    imp = pd.Series(cf.feature_importances_, index=X_COLS).sort_values(ascending=False)
    hp = np.nan
    if cv:   # 県のグループごとに外した森で予測した効果で BLP（自分を学習に使わない）
        tcv = np.zeros(len(d))
        for k, (a, b) in enumerate(GroupKFold(5).split(X, groups=g)):
            tcv[b] = m.fit_cf(d.iloc[a], outcome=outcome, n=1000, seed=SEED + k, **kw).effect(X[b])
        c2 = tcv - tcv.mean()
        hp = float(sm.OLS(yr, np.column_stack([tr, tr * c2])).fit(cov_type="cluster", cov_kwds={"groups": g}).pvalues[1])
    r = {"設定": label, "n": len(d), "平均効果": float(ate.mean_point), "下限": float(np.ravel(lo)[0]), "上限": float(np.ravel(hi)[0]),
         "効果のばらつき（SD）": float(tau.std()), "BLP p値（同じデータで予測）": float(blp.pvalues[1]), "BLP p値（県を外して予測）": hp,
         "県の効果の順位相関（基本と）": float(rho), "重要度1位": imp.index[0]}
    print(r); return r

rows = []
base = m.sample(df, "main")
rows.append(run("基本（2010〜25年、2020〜22年を除く）", base, cv=True))
rows.append(run("葉の最小サイズ 5", base, leaf=5))
rows.append(run("葉の最小サイズ 20", base, cv=True, leaf=20))
rows.append(run("木の深さ 最大4", base, depth=4))
for s in [1, 2, 3]:
    rows.append(run(f"乱数の種を変える（{s}）", base, seed=SEED + 100 * s))
rows.append(run("2010〜19年だけ（コロナ前）", m.sample(df, "pre")))
rows.append(run("2016〜25年（2020〜22年を除く）", m.sample(df, "post").query("year not in [2020,2021,2022]")))
rows.append(run("2020〜22年も含める", m.sample(df, "all")))
rows.append(run("結果を完全失業率の前年差にする", base, outcome="d_unemp"))
# プラセボ：同じ年の中で、処置（上がり幅）を県の間でシャッフル
rng = np.random.default_rng(SEED)
for k in range(3):
    pb = base.copy()
    pb["treat"] = pb.groupby("year")["treat"].transform(lambda s: rng.permutation(s.values))
    rows.append(run(f"プラセボ：年の中で上がり幅をシャッフル（{k+1}）", pb, cv=True))
out = pd.DataFrame(rows)
out.round(4).to_csv(RES / "robustness.csv", index=False)
print(out.round(3).to_string())
