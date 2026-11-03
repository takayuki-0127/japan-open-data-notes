"""更新のしかた（戦略）ごとに、翌年の価格を「見ていない場所」で当てる評価"""
import numpy as np, pandas as pd
import lightgbm as lgb
from sklearn.linear_model import Ridge
from common import FEAT, NUM, CAT, PARAMS, YEARS, folds, score

STRATS = ["同じ年のモデル（参考）", "毎年更新", "2年ごと", "3年ごと", "5年ごと", "2017年のまま", "2017年のまま＋全国の変化で補正", "直近3年をまとめて学習"]


class RidgeModel:
    def fit(self, X, y):
        self.med = X[NUM].median()
        Z = self._z(X, fit=True)
        self.m = Ridge(alpha=1.0).fit(Z, y); return self

    def _z(self, X, fit=False):
        A = X[NUM].copy()
        miss = A.isna().astype(float).add_suffix("_na")
        A = A.fillna(self.med)
        A["dist_station"] = np.log(A["dist_station"] + 50)
        if fit:
            self.mu, self.sd = A.mean(), A.std().replace(0, 1)
        A = (A - self.mu) / self.sd
        D = pd.get_dummies(X[CAT].astype(str), dtype=float)
        if fit:
            self.cols = D.columns
        D = D.reindex(columns=self.cols, fill_value=0.0)
        return np.hstack([A.values, miss.values, D.values])

    def predict(self, X):
        return self.m.predict(self._z(X))


def make_model(kind, params=None):
    if kind == "ridge":
        return RidgeModel()
    return lgb.LGBMRegressor(**(params or PARAMS))


def run(points, panel, fold_kind="block20", model_kind="lgbm", params=None, window=True, log=print):
    """戻り値：年×戦略の評価表、テスト側の予測（長い表）"""
    pts = points.set_index("code")
    fo = folds(points, fold_kind)
    P = panel[panel["code"].isin(pts.index)].copy()
    P["y"] = np.log(P["price"]); P["fold"] = P["code"].map(fo).values
    X = pts.loc[P["code"], FEAT].reset_index(drop=True); P = P.reset_index(drop=True)
    wide = P.pivot(index="code", columns="year", values="y")
    # 学習側の地点だけで測った「全国の中央値の変化」（a 年→b 年、log）
    def med_change(k, a, b):
        c = fo[fo != k].index
        w = wide.reindex(c)[[a, b]].dropna()
        return float(np.median(w[b] - w[a])) if a != b else 0.0
    pred = {}  # (s, k) -> 予測（テスト側の全年）
    for k in range(5):
        te_all = np.where(P["fold"] == k)[0]
        for s in YEARS:
            tr = np.where((P["fold"] != k) & (P["year"] == s))[0]
            m = make_model(model_kind, params).fit(X.iloc[tr], P["y"].iloc[tr])
            te = te_all[P["year"].values[te_all] >= s]
            pred[(s, k)] = pd.Series(m.predict(X.iloc[te]), index=te)
        log(f"fold {k} done")
    win = {}
    if window:
        for k in range(5):
            for T in YEARS[2:]:
                yrs = [T - 3, T - 2, T - 1]; yrs = [a for a in yrs if a >= YEARS[0]]
                tr = np.where((P["fold"] != k) & P["year"].isin(yrs))[0]
                adj = P["year"].iloc[tr].map({a: med_change(k, a, T - 1) for a in yrs}).values
                m = make_model(model_kind, params).fit(X.iloc[tr], P["y"].iloc[tr].values + adj)
                te = np.where((P["fold"] == k) & (P["year"] == T))[0]
                win[(T, k)] = pd.Series(m.predict(X.iloc[te]), index=te)
    rows, out = [], []
    for T in YEARS[1:]:
        for k in range(5):
            te = np.where((P["fold"] == k) & (P["year"] == T))[0]
            def last_retrain(step):
                return max(s for s in YEARS if s <= T - 1 and (s - YEARS[0]) % step == 0)
            cand = {"同じ年のモデル（参考）": pred[(T, k)].loc[te].values,
                    "毎年更新": pred[(T - 1, k)].loc[te].values,
                    "2017年のまま": pred[(YEARS[0], k)].loc[te].values,
                    "2017年のまま＋全国の変化で補正": pred[(YEARS[0], k)].loc[te].values + med_change(k, YEARS[0], T - 1)}
            for step, name in ((2, "2年ごと"), (3, "3年ごと"), (5, "5年ごと")):
                s = last_retrain(step)
                cand[name] = pred[(s, k)].loc[te].values + med_change(k, s, T - 1)
            if window and T >= YEARS[2]:
                cand["直近3年をまとめて学習"] = win[(T, k)].loc[te].values
            elif window:
                cand["直近3年をまとめて学習"] = pred[(T - 1, k)].loc[te].values
            for name, p in cand.items():
                out.append(pd.DataFrame({"code": P["code"].values[te], "year": T, "fold": k, "strategy": name,
                                         "y": P["y"].values[te], "pred": p}))
    out = pd.concat(out, ignore_index=True)
    for (T, name), g in out.groupby(["year", "strategy"]):
        rows.append(dict(year=T, strategy=name, **score(g["y"], g["pred"])))
    for name, g in out.groupby("strategy"):
        rows.append(dict(year="2018-2026", strategy=name, **score(g["y"], g["pred"])))
    return pd.DataFrame(rows), out
