"""Aalen–Johansen（新しく設立された法人、指定からの月数）。"""
import numpy as np, pandas as pd

def aj_new(df, maxage=131):
    # 期間 age の月のはじめにリスク集合にいる数 = 打ち切り月数 >= age かつ まだイベントなし
    ev = df[df.route > 0].groupby(["age", "route"]).n.sum().unstack(fill_value=0).reindex(range(maxage + 1), fill_value=0)
    for r in (1, 2, 3):
        if r not in ev: ev[r] = 0
    ev = ev[[1, 2, 3]]
    # 打ち切り（イベントなし）の法人は cens 月まで観察される
    cz = df[df.route == 0].groupby("cens").n.sum().reindex(range(maxage + 2), fill_value=0)
    evt = df[df.route > 0].groupby("age").n.sum().reindex(range(maxage + 2), fill_value=0)
    N = df.n.sum()
    # age の月にリスクにいる数: N - (age 未満でイベント) - (age 未満で打ち切り)
    atrisk = N - evt.cumsum().shift(fill_value=0) - cz.cumsum().shift(fill_value=0)
    atrisk = atrisk.iloc[: maxage + 1]
    S = 1.0; F = np.zeros(3); res = []; km1 = 1.0
    for a in range(maxage + 1):
        n = atrisk.iloc[a]
        if n <= 0: res.append([a, *F, S, 1 - km1]); continue
        d = ev.iloc[a].values
        F = F + S * d / n
        km1 *= 1 - d[0] / n
        S *= 1 - d.sum() / n
        res.append([a, *F, S, 1 - km1])
    return pd.DataFrame(res, columns=["age_m", "清算の結了など", "合併", "登記官による閉鎖", "活動", "1-KM_清算だけ"]), atrisk

