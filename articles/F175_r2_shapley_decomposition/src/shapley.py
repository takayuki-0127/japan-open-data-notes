"""F175 R² の Shapley 分解の部品

- v(S)：グループの組 S だけを使ったときの評価データの R²
  - 学び直し（refit）：S の列だけでモデルを学習し直す（線形回帰なら LMG と同じ考え方）
  - 周辺でならす（SAGE）：学習済みの全変数モデルはそのまま、S 以外の列を評価データの別の行の値に
    まとめて置き換え（基本は K=32 回）、予測を平均してから R² を測る（Covert ほか 2020 の marginal SAGE）
- 2^k 通りをすべて計算して、厳密な Shapley 値を出す（k≤7）
"""
from math import factorial
import numpy as np
import pandas as pd
import lightgbm as lgb
from common import FAST, r2


def masks(k):
    return list(range(1 << k))


def cols_of(mask, groups):
    names = list(groups)
    return [c for i, g in enumerate(names) if mask >> i & 1 for c in groups[g]]


def shapley(v, k):
    """v：長さ 2^k の配列（v[mask]）→ 各グループの Shapley 値"""
    phi = np.zeros(k)
    w = [factorial(s) * factorial(k - s - 1) / factorial(k) for s in range(k)]
    for m in range(1 << k):
        s = bin(m).count("1")
        for i in range(k):
            if not m >> i & 1:
                phi[i] += w[s] * (v[m | 1 << i] - v[m])
    return phi


def coarsen(v_fine, fine_names, coarse):
    """細かいグループの v を、それをまとめた粗いグループの v に読み替える"""
    k2 = len(coarse)
    out = np.zeros(1 << k2)
    for m2 in range(1 << k2):
        feats = {c for j, g in enumerate(coarse) if m2 >> j & 1 for c in coarse[g]}
        m = 0
        for i, g in enumerate(fine_names):
            if set(fine_names[g]) <= feats:
                m |= 1 << i
        out[m2] = v_fine[m]
    return out


# ---- モデル ----
def fit_lgbm(X, y, params=None):
    p = dict(FAST)
    if params:
        p.update(params)
    return lgb.LGBMRegressor(**p).fit(X, y)


def linear_design(X):
    """線形回帰用：カテゴリはダミー、数値は欠測を中央値で埋めて欠測フラグを足す。列→元の変数の対応も返す"""
    parts, owner = [], []
    for c in X.columns:
        s = X[c]
        if str(s.dtype) == "category" or c in ("hour", "dow", "month", "daytype", "lag24_daytype"):
            dm = pd.get_dummies(s.astype(str), prefix=c, drop_first=True, dtype=float)
            parts.append(dm); owner += [c] * dm.shape[1]
        else:
            v = s.astype(float)
            miss = v.isna()
            parts.append(v.fillna(v.median()).rename(c).to_frame()); owner.append(c)
            if miss.any():
                parts.append(miss.astype(float).rename(c + "_na").to_frame()); owner.append(c)
            if c.startswith("temp_") or c in ("cdd", "hdd", "cdd_max"):  # 気温は2乗も
                parts.append((v.fillna(v.median()) ** 2).rename(c + "_sq").to_frame()); owner.append(c)
    return pd.concat(parts, axis=1), np.array(owner)


def refit_values(Xtr, ytr, Xte, yte, groups, kind="lgbm", log=None):
    """2^k 通りすべてで学び直し、評価データの予測（行×組）を返す"""
    k = len(groups)
    P = np.zeros((len(Xte), 1 << k), dtype=np.float32)
    P[:, 0] = np.mean(ytr)
    if kind == "linear":
        D = pd.concat([Xtr, Xte], axis=0)
        Z, owner = linear_design(D)
        Z = Z.values
        Ztr, Zte = Z[:len(Xtr)], Z[len(Xtr):]
    for m in range(1, 1 << k):
        cs = cols_of(m, groups)
        if kind == "lgbm":
            P[:, m] = fit_lgbm(Xtr[cs], ytr).predict(Xte[cs])
        elif kind == "linear":
            j = np.isin(owner, cs)
            A = np.c_[np.ones(len(Ztr)), Ztr[:, j]]
            b = np.linalg.lstsq(A, ytr, rcond=None)[0]
            P[:, m] = np.c_[np.ones(len(Zte)), Zte[:, j]] @ b
        if log and m % 16 == 0:
            log(f"  refit {kind} {m}/{(1 << k) - 1}")
    return P


def sage_values(model, Xte, yte, groups, n=2000, K=8, seed=0):
    """学習済みモデルのまま、S 以外の列を評価データの別の行でまとめて置き換えて平均（marginal SAGE）"""
    rng = np.random.default_rng(seed)
    k = len(groups)
    idx = rng.choice(len(Xte), n, replace=False)
    Xs, ys = Xte.iloc[idx].reset_index(drop=True), yte[idx]
    bg = rng.choice(len(Xte), (n, K))
    Xrep = Xs.loc[np.repeat(np.arange(n), K)].reset_index(drop=True)
    Xbg = Xte.iloc[bg.ravel()].reset_index(drop=True)
    v = np.zeros(1 << k)
    for m in range(1 << k):
        keep = set(cols_of(m, groups))
        Z = Xrep.copy()
        for c in Xte.columns:
            if c not in keep:
                Z[c] = Xbg[c].values if str(Xte[c].dtype) != "category" else pd.Categorical(
                    Xbg[c].values, categories=Xte[c].cat.categories)
        p = model.predict(Z).reshape(n, K).mean(1)
        v[m] = r2(ys, p)
    return v


def r2_matrix(y, P, idx=None):
    if idx is not None:
        y, P = y[idx], P[idx]
    sst = np.sum((y - y.mean()) ** 2)
    return 1 - ((P - y[:, None]) ** 2).sum(0) / sst


def summary_table(v, groups):
    """Shapley・1つだけ外す（drop）・1つだけ使う（alone）"""
    k = len(groups)
    full = (1 << k) - 1
    phi = shapley(v, k)
    drop = [v[full] - v[full & ~(1 << i)] for i in range(k)]
    alone = [v[1 << i] - v[0] for i in range(k)]
    return pd.DataFrame({"グループ": list(groups), "shapley": phi, "drop_one": drop, "alone": alone}), v[full] - v[0]
