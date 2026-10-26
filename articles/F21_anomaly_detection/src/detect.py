"""detect.py ― 月次の統計に「いつもと違う動き」の印を付ける関数（他の系列にもそのまま使える）

使い方の例:
    from detect import stl_robust_z, flag, isolation_scores, change_points
    z = stl_robust_z(series)            # pandas.Series（月次、DatetimeIndex）→ 残差の頑健な z スコア
    f = flag(z, thr=4.0)                # |z| が閾値を超えた月に True
"""
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL


def to_change(s: pd.Series, kind: str) -> pd.Series:
    """水準の系列を「前月からの変化」にする。kind='log' は対数差（%に近い）、'diff' はそのままの差。"""
    s = s.astype(float)
    if kind == "log":
        s = s.where(s > 0)
        return np.log(s).diff() * 100
    return s.diff()


def robust_z(x: pd.Series) -> pd.Series:
    """中央値と MAD（中央絶対偏差）で標準化。外れ値に引っぱられにくい z スコア。"""
    med = np.nanmedian(x)
    dev = np.abs(x - med)
    mad = np.nanmedian(dev) * 1.4826
    # 値がほとんど動かない系列（物価の公共料金など）は MAD が 0 近くになり、z が爆発する。
    # 平均絶対偏差（×1.2533 で正規分布の標準偏差に合わせる）を下限にする。
    meanad = np.nanmean(dev) * 1.2533
    scale = max(mad, meanad)
    if not np.isfinite(scale) or scale == 0:
        scale = 1.0
    return (x - med) / scale


def stl_robust_z(change: pd.Series, period: int = 12, seasonal: int = 13, robust: bool = True) -> pd.Series:
    """前月からの変化を STL で「季節」「トレンド」「残差」に分け、残差を頑健な z スコアにする。"""
    c = change.dropna()
    if len(c) < 3 * period:
        return pd.Series(np.nan, index=change.index)
    res = STL(c, period=period, seasonal=seasonal, robust=robust).fit()
    z = robust_z(res.resid)
    return z.reindex(change.index)


def flag(z: pd.DataFrame | pd.Series, thr: float = 4.0):
    """|z| が閾値を超えたところに True。"""
    return z.abs() > thr


def isolation_scores(Z: pd.DataFrame, clip: float = 10.0, n_estimators: int = 500, seed: int = 0) -> pd.Series:
    """月×系列の z スコア行列から、Isolation Forest で「月ごとの異常の度合い」を出す（大きいほど異常）。"""
    from sklearn.ensemble import IsolationForest
    X = Z.fillna(0).clip(-clip, clip).abs()
    m = IsolationForest(n_estimators=n_estimators, random_state=seed).fit(X)
    return pd.Series(-m.score_samples(X), index=Z.index)


def change_points(level: pd.Series, period: int = 12, pen: float | None = None, model: str = "l2",
                  min_size: int = 6, deseason: bool = True, pen_mult: float = 4.0):
    """水準の系列（必要なら STL で季節を除く）から、PELT で水準の変わり目（新しい水準が始まる月）を返す。
    pen を省略すると、前月差の標準偏差を使った BIC 型の罰則（× pen_mult）。"""
    import ruptures as rpt
    s = level.dropna().astype(float)
    sa = s - STL(s, period=period, robust=True).fit().seasonal if deseason else s
    x = sa.values.reshape(-1, 1)
    sigma = np.nanstd(np.diff(sa.values)) or 1.0
    if pen is None:
        pen = 2 * np.log(len(x)) * sigma ** 2 * pen_mult
    bk = rpt.Pelt(model=model, min_size=min_size, jump=1).fit(x).predict(pen=pen)
    return [s.index[b] for b in bk[:-1]], sa
