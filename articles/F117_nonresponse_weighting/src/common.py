"""F117 共通：階級別の度数から平均・分位点を出す関数、レーキング（反復比例調整）。"""
import numpy as np
import pandas as pd

SIZES = ["n1", "n2", "n3", "n4", "n5", "n6p"]
AGES = ["a29", "a30", "a40", "a50", "a60", "a70", "a80"]
STRUCTS = ["single", "couple", "couple_child", "lone_parent", "other3"]  # other3 = 三世代＋その他
SIZE_JA = {"n1": "1人", "n2": "2人", "n3": "3人", "n4": "4人", "n5": "5人", "n6p": "6人以上"}
AGE_JA = {"a29": "29歳以下", "a30": "30歳代", "a40": "40歳代", "a50": "50歳代", "a60": "60歳代", "a70": "70歳代", "a80": "80歳以上"}
STRUCT_JA = {"single": "単独", "couple": "夫婦のみ", "couple_child": "夫婦と未婚の子", "lone_parent": "ひとり親と未婚の子",
             "other3": "三世代・その他"}


class Bins:
    """所得金額階級（万円）。最後は 2,000万円以上の開いた階級。"""

    def __init__(self, lo, hi):
        self.lo = np.asarray(lo, float)
        self.hi = np.asarray([np.nan if (h is None or (isinstance(h, float) and np.isnan(h))) else h for h in hi], float)

    def stats(self, w, within="uniform", alpha=None):
        """階級ごとの重み w（合計は何でもよい）から、平均・中央値・低所得の割合などを返す。

        within="uniform"：階級の中は一様（開いた階級はパレート）
        within="mid"   ：階級の中央の値（開いた階級は下限×α/(α−1)）
        """
        w = np.asarray(w, float)
        p = w / w.sum()
        cum = np.concatenate([[0], np.cumsum(p)])
        top = self.lo[-1]
        if alpha is None:
            s1500 = p[self.lo >= 1500].sum()
            s2000 = p[-1]
            alpha = np.log(s1500 / s2000) / np.log(2000 / 1500)
        mids = np.where(np.isnan(self.hi), top * alpha / (alpha - 1), (self.lo + np.nan_to_num(self.hi)) / 2)
        mean = float((p * mids).sum())

        def q(prob):
            k = np.searchsorted(cum, prob) - 1
            k = min(max(k, 0), len(p) - 1)
            if within == "mid":
                return float(mids[k])
            if k == len(p) - 1:  # パレート
                s_top = p[-1]
                s = 1 - prob
                return float(top * (s_top / s) ** (1 / alpha))
            return float(self.lo[k] + (prob - cum[k]) / p[k] * (self.hi[k] - self.lo[k]))

        def share_below(x):
            out = 0.0
            for k in range(len(p)):
                lo, hi = self.lo[k], self.hi[k]
                if np.isnan(hi):
                    if x > lo:
                        out += p[k] * (1 - (lo / x) ** alpha)
                elif x >= hi:
                    out += p[k]
                elif x > lo:
                    out += p[k] * (x - lo) / (hi - lo)
            return float(out)

        return dict(mean=mean, median=q(0.5), p20=q(0.2), p80=q(0.8), below200=share_below(200) * 100,
                    below300=share_below(300) * 100, above1000=(1 - share_below(1000)) * 100, alpha=float(alpha))


def rake(table, margins, iters=200, tol=1e-10):
    """table：各次元の重みを持つ配列（例：size×age×income）。margins：{軸番号: 目標の合計（その軸の長さ）}。
    income の軸は調整しない。返り値は調整後の配列と、反復回数。"""
    t = table.astype(float).copy()
    total = t.sum()
    for it in range(iters):
        maxdiff = 0.0
        for ax, target in margins.items():
            target = np.asarray(target, float)
            target = target / target.sum() * total
            other = tuple(i for i in range(t.ndim) if i != ax)
            cur = t.sum(axis=other)
            f = np.divide(target, cur, out=np.ones_like(target), where=cur > 0)
            shape = [1] * t.ndim
            shape[ax] = -1
            t *= f.reshape(shape)
            maxdiff = max(maxdiff, np.abs(cur / total - target / total).max())
        if maxdiff < tol:
            break
    return t, it + 1


def kish_deff(weights, counts):
    """セルごとの重み（調整後÷調整前）と、そのセルの人数から、Kish の重みによる設計効果 1+CV² を出す。"""
    w = np.asarray(weights, float).ravel()
    n = np.asarray(counts, float).ravel()
    m = n > 0
    w, n = w[m], n[m]
    mw = (n * w).sum() / n.sum()
    var = (n * (w - mw) ** 2).sum() / n.sum()
    return float(1 + var / mw ** 2)
