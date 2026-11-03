"""5つのモデルを同じ形（評価時点 G での生存確率の行列）で返す共通部分。

- Cox: 比例ハザード、主効果だけ（scikit-survival CoxPHSurvivalAnalysis、ごく弱いリッジ）
- Cox＋交互作用: 種別×(地域区分・地方・指定年)、地域区分×指定年、指定年²を足した Cox
- RSF: ランダムサバイバルフォレスト（scikit-survival）
- GBM-Cox: 勾配ブースティング（xgboost, survival:cox）＋ Breslow の基準ハザード。比例ハザードは仮定したまま
- GBM-離散時間: 四半期ごとの「その期に閉鎖するか」を xgboost の二値分類で学習。経過時間を特徴量に入れるので比例ハザードを仮定しない
"""
import numpy as np, pandas as pd, xgboost as xgb
from sksurv.linear_model import CoxPHSurvivalAnalysis
from sksurv.ensemble import RandomSurvivalForest
from sksurv.util import Surv

G = np.round(np.arange(0.25, 10.01, 0.25), 2)   # 評価時点（年）
CAT_ALL = ["kind", "area", "region", "pref", "month", "dow"]
NUM_ALL = ["cohort", "dom", "muni_logn", "muni_llc", "muni_other", "lmuni_rate"]
FEATSETS = {
    "basic": (["kind", "area", "region"], ["cohort"]),
    "all_no_rate": (CAT_ALL, NUM_ALL[:-1]),
    "all": (CAT_ALL, NUM_ALL),
}


def design(df, featset, ref=None):
    cat, num = FEATSETS[featset]
    X = pd.get_dummies(df[cat].astype(str), drop_first=False, dtype=float)
    for c in num:
        X[c] = df[c].astype(float)
    if ref is not None:
        X = X.reindex(columns=ref, fill_value=0.0)
    else:
        # 基準カテゴリを落とす（Cox の識別のため）。木のモデルも同じ列を使う
        drop = [f"{c}_{df[c].astype(str).mode()[0]}" for c in cat]
        X = X.drop(columns=drop)
    return X


def add_interactions(X):
    Z = X.copy()
    c = (Z["cohort"] - 2021) / 3
    Z["cohort2"] = c ** 2
    kinds = [k for k in Z.columns if k.startswith("kind_")]
    areas = [k for k in Z.columns if k.startswith("area_")]
    regs = [k for k in Z.columns if k.startswith("region_")]
    for k in kinds:
        Z[f"{k}:cohort"] = Z[k] * c
        for a in areas + regs:
            Z[f"{k}:{a}"] = Z[k] * Z[a]
    for a in areas:
        Z[f"{a}:cohort"] = Z[a] * c
    return Z


def step_eval(times, S, grid):
    idx = np.searchsorted(times, grid, side="right") - 1
    out = np.ones((S.shape[0], len(grid)))
    ok = idx >= 0
    out[:, ok] = S[:, idx[ok]]
    return out


def breslow(margin_tr, T, E, grid):
    o = np.argsort(T)
    T, E, r = T[o], E[o], np.exp(margin_tr[o])
    risk = np.cumsum(r[::-1])[::-1]
    ut, first = np.unique(T, return_index=True)
    d = np.add.reduceat(E, first)
    rs = risk[first]
    H = np.cumsum(d / rs)
    idx = np.searchsorted(ut, grid, side="right") - 1
    return np.where(idx >= 0, H[np.clip(idx, 0, None)], 0.0)


def add_splines(X, ref=None):
    """数値の特徴量を3次スプライン（内側の節4つ）に置き換える。ref は学習データ（節の位置を決める）"""
    from sklearn.preprocessing import SplineTransformer
    ref = X if ref is None else ref
    Z = X.copy()
    for c in ["cohort", "dom", "muni_logn", "muni_llc", "muni_other", "lmuni_rate"]:
        if c not in X:
            continue
        st = SplineTransformer(n_knots=6, degree=3, knots="quantile", extrapolation="constant", include_bias=False).fit(ref[[c]])
        B = st.transform(X[[c]])
        for j in range(B.shape[1]):
            Z[f"{c}_s{j}"] = B[:, j]
        Z = Z.drop(columns=c)
    return Z


def fit_predict(name, Xtr, Ttr, Etr, Xte, seed=42, params=None):
    """Xte に DataFrame のリストを渡すと、1回の学習でそれぞれの予測を返す（並べ替えによる重要度用）"""
    many = isinstance(Xte, list)
    Xl = Xte if many else [Xte]
    out = _fit_predict(name, Xtr, Ttr, Etr, Xl, seed, params or {})
    return out if many else out[0]


def _fit_predict(name, Xtr, Ttr, Etr, Xl, seed, params):
    y = Surv.from_arrays(Etr.astype(bool), Ttr)
    if name in ("Cox", "Cox＋交互作用", "Cox＋スプライン"):
        f = {"Cox": lambda X: X, "Cox＋交互作用": add_interactions, "Cox＋スプライン": lambda X: add_splines(X, Xtr)}[name]
        A = f(Xtr)
        keep = A.columns[A.std() > 0]
        A = A[keep]; mu, sd = A.mean(), A.std()
        m = CoxPHSurvivalAnalysis(alpha=1e-3, ties="breslow", n_iter=200).fit(((A - mu) / sd).values, y)
        res = []
        for Xte in Xl:
            B = f(Xte)[keep]
            res.append(step_eval(m.unique_times_, m.predict_survival_function(((B - mu) / sd).values, return_array=True), G))
        return res
    if name == "RSF":
        m = RandomSurvivalForest(n_estimators=params.get("n_estimators", 200), min_samples_leaf=params.get("leaf", 50),
                                 max_features=params.get("mf", "sqrt"), max_samples=params.get("ms", 0.5),
                                 n_jobs=2, random_state=seed, low_memory=False).fit(Xtr.values.astype(np.float32), y)
        return [step_eval(m.unique_times_, m.predict_survival_function(Xte.values.astype(np.float32), return_array=True), G)
                for Xte in Xl]
    rng = np.random.default_rng(seed)
    va = rng.random(len(Xtr)) < 0.2
    p = dict(eta=0.05, max_depth=params.get("depth", 4), min_child_weight=params.get("mcw", 20), subsample=0.8,
             colsample_bytree=0.8, seed=seed, nthread=2, tree_method="hist")
    if name == "GBM-Cox(深さ1)":
        name = "GBM-Cox"; p["max_depth"] = 1
    if name == "GBM-Cox":
        lab = np.where(Etr == 1, Ttr, -Ttr)
        dtr = xgb.DMatrix(Xtr[~va].values, label=lab[~va]); dva = xgb.DMatrix(Xtr[va].values, label=lab[va])
        b = xgb.train({**p, "objective": "survival:cox", "eval_metric": "cox-nloglik"}, dtr, 3000, evals=[(dva, "va")],
                      early_stopping_rounds=100, verbose_eval=False)
        b = xgb.train({**p, "objective": "survival:cox"}, xgb.DMatrix(Xtr.values, label=lab), b.best_iteration + 1)
        mtr = b.predict(xgb.DMatrix(Xtr.values), output_margin=True)
        H0 = breslow(mtr, Ttr, Etr, G)
        return [np.exp(-np.outer(np.exp(b.predict(xgb.DMatrix(Xte.values), output_margin=True)), H0)) for Xte in Xl]
    if name == "GBM-離散時間":
        w = 0.25; K = len(G)

        def expand(X, T, E):
            n = len(X); k = np.minimum(np.ceil(T / w).astype(int), K)
            rows = np.repeat(np.arange(n), k)
            kk = np.concatenate([np.arange(1, kk_ + 1) for kk_ in k])
            last = kk == np.repeat(k, k)
            ev = (last & (np.repeat(E, k) == 1)).astype(float)
            expo = np.where(last, np.repeat(T, k) - (kk - 1) * w, w) / w
            wt = np.where(ev == 1, 1.0, np.clip(expo, 0, 1))
            Z = np.column_stack([X.values[rows], kk * w])
            return Z, ev, wt
        Ztr, ytr, wtr = expand(Xtr[~va], Ttr[~va], Etr[~va]); Zva, yva, wva = expand(Xtr[va], Ttr[va], Etr[va])
        b = xgb.train({**p, "objective": "binary:logistic", "eval_metric": "logloss"}, xgb.DMatrix(Ztr, ytr, weight=wtr), 3000,
                      evals=[(xgb.DMatrix(Zva, yva, weight=wva), "va")], early_stopping_rounds=100, verbose_eval=False)
        Zall, yall, wall = expand(Xtr, Ttr, Etr)
        b = xgb.train({**p, "objective": "binary:logistic"}, xgb.DMatrix(Zall, yall, weight=wall), b.best_iteration + 1)
        res = []
        for Xte in Xl:
            n = len(Xte); out = np.empty((n, K)); Xv = Xte.values
            for j in range(K):
                out[:, j] = b.predict(xgb.DMatrix(np.column_stack([Xv, np.full(n, G[j])])))
            res.append(np.cumprod(1 - out, axis=1))
        return res
    raise ValueError(name)
