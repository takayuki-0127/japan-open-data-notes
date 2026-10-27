"""マルコフ切り替えモデルの当てはめと、後退期の判定の共通関数"""
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
from common import SEED, episodes  # common を先に読み込み、スレッド数を固定する

warnings.filterwarnings("ignore")


def fit_ms(y, k=3, switching_variance=False, start_params=None, search_reps=20, n_seeds=5):
    """平均（定数）が状態で切り替わるモデル。
    初期値を変えて何度か推定し、対数尤度がいちばん高い当てはめを返す（局所解を避けるため）"""
    y = y.dropna().copy()
    y.index = pd.DatetimeIndex(y.index, freq="MS")
    m = sm.tsa.MarkovRegression(y, k_regimes=k, trend="c", switching_variance=switching_variance)
    best = None
    if start_params is not None:
        try:
            best = m.fit(start_params=start_params, disp=False)
        except Exception:
            best = None
    for i in range(n_seeds):
        np.random.seed(SEED + i)
        try:
            r = m.fit(search_reps=search_reps, disp=False)
        except Exception:
            continue
        if best is None or (np.isfinite(r.llf) and r.llf > best.llf):
            best = r
    return best


def regime_order(r):
    """定数の小さい順に状態の番号を並べる（最後が拡張期）"""
    c = np.array([r.params[f"const[{i}]"] for i in range(r.k_regimes)])
    return np.argsort(c), c


def nonexp_prob(r, kind="smoothed"):
    """平均がマイナスの状態（後退・急落）にいる確率の合計＝後退期の確率"""
    _, c = regime_order(r)
    probs = r.smoothed_marginal_probabilities if kind == "smoothed" else r.filtered_marginal_probabilities
    neg = [i for i in range(r.k_regimes) if c[i] < 0]
    return probs[neg].sum(axis=1) if neg else probs[0] * 0


def classify(prob, min_len=3):
    """確率 0.5 超を後退期とし、min_len か月未満の短い区間は落とす"""
    flag = (prob > 0.5).astype(int)
    out = pd.Series(0, index=flag.index)
    for s, e in episodes(flag):
        if (e.year - s.year) * 12 + e.month - s.month + 1 >= min_len:
            out[s:e] = 1
    return out


def scores(cls, official):
    o = official.reindex(cls.index)
    return {
        "一致率": float((cls == o).mean()),
        "後退期を後退と判定した割合": float(cls[o == 1].mean()),
        "拡張期を拡張と判定した割合": float(1 - cls[o == 0].mean()),
        "月数": int(len(cls)),
    }


def months_between(a, b):
    return (b.year - a.year) * 12 + b.month - a.month


def match_episodes(cls, cycles):
    """公式の後退期（山の翌月〜谷）ごとに、推定の後退期の始まり・終わりのずれ（月）を出す"""
    eps = episodes(cls)
    peaks = cycles[cycles.type == "peak"].month.tolist()
    troughs = cycles[cycles.type == "trough"].month.tolist()
    rows, used = [], set()
    for p in peaks:
        t = [x for x in troughs if x > p][0]
        if p < cls.index.min():
            continue
        start_official = p + pd.DateOffset(months=1)
        hit = [(s, e) for (s, e) in eps if s <= t and e >= start_official]
        used.update(hit)
        if hit:
            s, e = hit[0][0], hit[-1][1]
            rows.append({"山": p.strftime("%Y-%m"), "谷": t.strftime("%Y-%m"),
                         "推定の始まり": s.strftime("%Y-%m"), "推定の終わり": e.strftime("%Y-%m"),
                         "始まりのずれ（月）": months_between(start_official, s),
                         "終わりのずれ（月）": months_between(t, e)})
        else:
            rows.append({"山": p.strftime("%Y-%m"), "谷": t.strftime("%Y-%m"),
                         "推定の始まり": "見つからず", "推定の終わり": "",
                         "始まりのずれ（月）": np.nan, "終わりのずれ（月）": np.nan})
    false = [(s.strftime("%Y-%m"), e.strftime("%Y-%m")) for (s, e) in eps if (s, e) not in used]
    return pd.DataFrame(rows), false
