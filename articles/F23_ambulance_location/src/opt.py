"""p-median と最大カバー問題を scipy.optimize.milp（HiGHS）で解く共通関数。"""
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import coo_matrix, csr_matrix, hstack, vstack, identity


def p_median(D, w, p, allowed=None, fixed=None, time_limit=300):
    """D: 需要点×候補地の距離、w: 需要点の重み、p: 置く数。
    allowed: 使える候補地の真偽配列。fixed: 必ず使う候補地の真偽配列。
    戻り値：選んだ候補地の番号、重みつき平均距離"""
    N, M = D.shape
    allowed = np.ones(M, bool) if allowed is None else np.asarray(allowed)
    cols = np.where(allowed)[0]
    Ds = D[:, cols]
    m = len(cols)
    nx = N * m
    # 変数：x_ij（N*m）、y_j（m）
    c = np.concatenate([(w[:, None] * Ds).ravel(), np.zeros(m)])
    rows = np.repeat(np.arange(N), m)
    A1 = hstack([coo_matrix((np.ones(nx), (rows, np.arange(nx))), shape=(N, nx)), csr_matrix((N, m))])
    # x_ij - y_j <= 0
    A2 = hstack([identity(nx, format="csr"), -coo_matrix((np.ones(nx), (np.arange(nx), np.tile(np.arange(m), N))), shape=(nx, m))])
    A3 = hstack([csr_matrix((1, nx)), csr_matrix(np.ones((1, m)))])
    A = vstack([A1, A2, A3]).tocsr()
    lb = np.concatenate([np.ones(N), -np.inf * np.ones(nx), [p]])
    ub = np.concatenate([np.ones(N), np.zeros(nx), [p]])
    lo = np.zeros(nx + m)
    hi = np.ones(nx + m)
    if fixed is not None:
        lo[nx:] = np.asarray(fixed)[cols].astype(float)
    integ = np.concatenate([np.zeros(nx), np.ones(m)])
    res = milp(c, constraints=LinearConstraint(A, lb, ub), integrality=integ,
               bounds=Bounds(lo, hi), options={"time_limit": time_limit, "mip_rel_gap": 1e-4})
    y = res.x[nx:] > 0.5
    sel = cols[y]
    dmin = D[:, sel].min(axis=1)
    return sel, float((w * dmin).sum() / w.sum()), res


def max_cover(D, w, p, R, allowed=None, fixed=None, time_limit=300):
    """R 以内に入る重みの合計を最大にする p か所を選ぶ。"""
    N, M = D.shape
    allowed = np.ones(M, bool) if allowed is None else np.asarray(allowed)
    cols = np.where(allowed)[0]
    a = (D[:, cols] <= R).astype(float)
    m = len(cols)
    # 変数：y_j（m）、z_i（N）。max sum w z → min -w z
    c = np.concatenate([np.zeros(m), -w])
    # z_i - sum_j a_ij y_j <= 0
    A1 = hstack([-csr_matrix(a), identity(N, format="csr")])
    A2 = hstack([csr_matrix(np.ones((1, m))), csr_matrix((1, N))])
    A = vstack([A1, A2]).tocsr()
    lb = np.concatenate([-np.inf * np.ones(N), [p]])
    ub = np.concatenate([np.zeros(N), [p]])
    lo = np.zeros(m + N)
    if fixed is not None:
        lo[:m] = np.asarray(fixed)[cols].astype(float)
    res = milp(c, constraints=LinearConstraint(A, lb, ub), integrality=np.concatenate([np.ones(m), np.zeros(N)]),
               bounds=Bounds(lo, np.ones(m + N)), options={"time_limit": time_limit, "mip_rel_gap": 1e-4})
    sel = cols[res.x[:m] > 0.5]
    cov = float(w[(D[:, sel] <= R).any(axis=1)].sum() / w.sum())
    return sel, cov, res


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0088
    p1, p2 = np.radians(lat1)[:, None], np.radians(lat2)[None, :]
    dphi = p2 - p1
    dl = np.radians(lon2)[None, :] - np.radians(lon1)[:, None]
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))
