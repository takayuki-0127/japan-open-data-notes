"""4つの「何が効いているか」の手法：SHAP・並べ替え重要度・部分依存（PDP）・ALE を同じ物差しで計算する"""
import numpy as np, pandas as pd
import shap


def _is_discrete(s):
    return str(s.dtype) == "category" or s.nunique() <= 10


def _levels(s, y=None):
    """離散の変数の水準。カテゴリは目的変数の平均の順に並べる（ALE の隣どうしの差を取るため）"""
    if str(s.dtype) == "category":
        lv = list(s.cat.categories)
        if y is not None:
            m = pd.Series(np.asarray(y)).groupby(s.values, observed=True).mean()
            lv = [l for l in m.sort_values().index if l in set(s.dropna().unique())]
        return lv
    return sorted(s.dropna().unique())


def _set(X, f, v):
    Z = X.copy()
    if str(X[f].dtype) == "category":
        Z[f] = pd.Categorical([v] * len(Z), categories=X[f].cat.categories)
    else:
        Z[f] = v
    return Z


def shap_importance(model, X, n=3000, seed=0):
    Xs = X.sample(min(n, len(X)), random_state=seed)
    sv = shap.TreeExplainer(model).shap_values(Xs)
    return pd.Series(np.abs(sv).mean(0), index=X.columns), sv, Xs


def permutation_importance(model, X, y, n_repeats=5, seed=0, groups=None):
    """並べ替えた後の RMSE の増え方。groups を渡すと、その変数のまとまりを同じ並べ替えで一緒に崩す"""
    rng = np.random.default_rng(seed)
    base = np.sqrt(np.mean((model.predict(X) - y) ** 2))
    cols = groups if groups is not None else {c: [c] for c in X.columns}
    out = {}
    for name, cs in cols.items():
        inc = []
        for _ in range(n_repeats):
            Z = X.copy()
            idx = rng.permutation(len(Z))
            for c in cs:
                Z[c] = X[c].values[idx]
                if str(X[c].dtype) == "category":
                    Z[c] = pd.Categorical(Z[c], categories=X[c].cat.categories)
            inc.append(np.sqrt(np.mean((model.predict(Z) - y) ** 2)) - base)
        out[name] = np.mean(inc)
    return pd.Series(out)


def pdp_curve(model, X, f, y=None, grid=20):
    s = X[f]
    if _is_discrete(s):
        g = _levels(s, y)
    else:
        g = np.unique(np.quantile(s.dropna(), np.linspace(0.05, 0.95, grid)))
    vals = [model.predict(_set(X, f, v)).mean() for v in g]
    return pd.DataFrame({"x": g, "pdp": vals})


def ale_curve(model, X, f, y=None, grid=20):
    """ALE（Apley & Zhu 2020）。連続はデータの分位点で区切り、各区間の中の点だけを動かして差を積み上げる。
    離散（カテゴリ・0/1 など）は水準を並べ、隣の水準へ動かしたときの差を、その2つの水準の点で平均して積み上げる"""
    s = X[f]
    if _is_discrete(s):
        lv = _levels(s, y)
        eff, n = [0.0], [int((s == lv[0]).sum())]
        for a, b in zip(lv[:-1], lv[1:]):
            rows = X[(s == a) | (s == b)]
            d = (model.predict(_set(rows, f, b)) - model.predict(_set(rows, f, a))).mean()
            eff.append(eff[-1] + d); n.append(int((s == b).sum()))
        eff, n = np.array(eff), np.array(n)
        eff = eff - np.average(eff, weights=np.maximum(n, 1))
        return pd.DataFrame({"x": lv, "ale": eff})
    edges = np.unique(np.quantile(s.dropna(), np.linspace(0.05, 0.95, grid)))
    eff, n = [0.0], [0]
    for lo, hi in zip(edges[:-1], edges[1:]):
        rows = X[(s >= lo) & (s <= hi)]
        d = 0.0 if len(rows) == 0 else (model.predict(_set(rows, f, hi)) - model.predict(_set(rows, f, lo))).mean()
        eff.append(eff[-1] + d); n.append(len(rows))
    eff, n = np.array(eff), np.array(n, dtype=float)
    w = np.r_[n[1], n[1:]]
    eff = eff - np.average(eff, weights=np.maximum(w, 1))
    return pd.DataFrame({"x": edges, "ale": eff})


def curve_importance(model, X, y=None, kind="pdp", grid=20):
    """曲線が動く幅（最大−最小）。PDP と ALE を同じ物差しにするため、どちらも 5〜95% の範囲で測る"""
    out, curves = {}, {}
    for f in X.columns:
        c = pdp_curve(model, X, f, y, grid) if kind == "pdp" else ale_curve(model, X, f, y, grid)
        v = c.iloc[:, 1].values
        out[f] = float(np.nanmax(v) - np.nanmin(v))
        curves[f] = c
    return pd.Series(out), curves


def all_importances(model, Xte, yte, n_shap=3000, n_curve=2000, n_repeats=5, seed=0):
    sh, sv, Xs = shap_importance(model, Xte, n_shap, seed)
    pi = permutation_importance(model, Xte, yte, n_repeats, seed)
    Xc = Xte.sample(min(n_curve, len(Xte)), random_state=seed)
    yc = pd.Series(yte, index=Xte.index).loc[Xc.index].values
    pdp, pdp_c = curve_importance(model, Xc, yc, "pdp")
    ale, ale_c = curve_importance(model, Xc, yc, "ale")
    imp = pd.DataFrame({"SHAP": sh, "並べ替え重要度": pi, "部分依存（PDP）": pdp, "ALE": ale})
    return imp, dict(shap=(sv, Xs), pdp=pdp_c, ale=ale_c)
