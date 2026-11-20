"""正規分布の分位点（scipy を使わずに求める）"""
import math
import numpy as np


def norm_ppf(p):
    """二分法で Φ^-1(p) を求める"""
    p = np.asarray(p, float)
    out = []
    for q in p.ravel():
        lo, hi = -10.0, 10.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if 0.5 * (1 + math.erf(mid / math.sqrt(2))) < q:
                lo = mid
            else:
                hi = mid
        out.append((lo + hi) / 2)
    return np.array(out).reshape(p.shape)
