"""AR(1) の動学パネルを、Arellano–Bond の差分GMM と Blundell–Bond の system GMM で推定する最小の実装。
y_it = rho*y_i,t-1 + tau_t + mu_i + e_it。操作変数は y のラグ（lags=(2,4) など）を「collapse」した形で使う。
1段階目の重みは差分の誤差の MA(1) 構造（H 行列）。2段階目は1段階目の残差から作る。
標準誤差は1段階目の頑健な標準誤差（2段階目の標準誤差は小標本で小さく出すぎるため）。"""
import numpy as np, pandas as pd
from scipy import stats

def _prep(df, ycol='r', idcol='code', tcol='t'):
    df = df.sort_values([idcol, tcol])
    T = int(df[tcol].max()) + 1
    Y = {i: np.full(T, np.nan) for i in df[idcol].unique()}
    for i, t, v in df[[idcol, tcol, ycol]].itertuples(index=False):
        Y[i][int(t)] = v
    return Y, T

def estimate(df, lags=(2, 4), system=False, ycol='r', idcol='code', tcol='t'):
    Y, T = _prep(df, ycol, idcol, tcol)
    lmin, lmax = lags
    tdum_cols = list(range(2, T))              # 差分式で使える期（t=2..T-1）
    blocks = []
    for i, y in Y.items():
        # 差分式
        rows_d = []
        for t in range(2, T):
            if np.isnan(y[t]) or np.isnan(y[t-1]) or np.isnan(y[t-2]): continue
            dy = y[t]-y[t-1]; dx = y[t-1]-y[t-2]
            z = [y[t-l] if t-l >= 0 and not np.isnan(y[t-l]) else 0.0 for l in range(lmin, lmax+1)]
            td = [1.0 if t == s else (-1.0 if t-1 == s else 0.0) for s in range(1, T)]
            rows_d.append((t, dy, dx, z, td))
        rows_l = []
        if system:
            for t in range(2, T):
                if np.isnan(y[t]) or np.isnan(y[t-1]) or np.isnan(y[t-2]): continue
                zl = [y[t-1]-y[t-2]]                # 水準式の操作変数：1期前の差分（collapse）
                td = [1.0 if t == s else 0.0 for s in range(1, T)]
                rows_l.append((t, y[t], y[t-1], zl, td))
        if not rows_d: continue
        blocks.append((rows_d, rows_l))
    nz = lmax-lmin+1; ntd = T-1
    def build(rows_d, rows_l):
        nd, nl = len(rows_d), len(rows_l)
        k = 1 + ntd
        X = np.zeros((nd+nl, k)); yv = np.zeros(nd+nl)
        zc = nz + (1 if system else 0) + ntd
        Z = np.zeros((nd+nl, zc))
        for j, (t, dy, dx, z, td) in enumerate(rows_d):
            yv[j] = dy; X[j, 0] = dx; X[j, 1:] = td; Z[j, :nz] = z; Z[j, -ntd:] = td
        for j, (t, yl, xl, zl, td) in enumerate(rows_l):
            yv[nd+j] = yl; X[nd+j, 0] = xl; X[nd+j, 1:] = td; Z[nd+j, nz] = zl[0]; Z[nd+j, -ntd:] = td
        H = np.zeros((nd+nl, nd+nl))
        for a in range(nd):
            H[a, a] = 2
            if a+1 < nd and rows_d[a+1][0] == rows_d[a][0]+1: H[a, a+1] = H[a+1, a] = -1
        for a in range(nl): H[nd+a, nd+a] = 1
        return X, yv, Z, H
    mats = [build(*b) for b in blocks]
    # 全部 0 の列（使われない時点ダミー）を落とす
    Xall = np.vstack([m[0] for m in mats]); Zall = np.vstack([m[2] for m in mats])
    kx = [0] + [c for c in range(1, Xall.shape[1]) if np.abs(Xall[:, c]).sum() > 0]
    kz = [c for c in range(Zall.shape[1]) if np.abs(Zall[:, c]).sum() > 0]
    # 時点ダミーの1つは定数と重なるので、差分GMMでは最初の列を落とす（多重共線性の回避）
    mats = [(X[:, kx], yv, Z[:, kz], H) for X, yv, Z, H in mats]
    def solve(W):
        A = sum(X.T @ Z for X, yv, Z, H in mats); b = sum(Z.T @ yv for X, yv, Z, H in mats)
        M = A @ W @ A.T
        beta = np.linalg.lstsq(M, A @ W @ b, rcond=None)[0]
        return beta, A, M
    W1 = np.linalg.pinv(sum(Z.T @ H @ Z for X, yv, Z, H in mats))
    b1, A, M = solve(W1)
    res1 = [yv - X @ b1 for X, yv, Z, H in mats]
    S = sum(Z.T @ np.outer(e, e) @ Z for (X, yv, Z, H), e in zip(mats, res1))
    Minv = np.linalg.pinv(M)
    V1 = Minv @ (A @ W1 @ S @ W1 @ A.T) @ Minv
    W2 = np.linalg.pinv(S)
    b2, A2, M2 = solve(W2)
    res2 = [yv - X @ b2 for X, yv, Z, H in mats]
    g = sum(Z.T @ e for (X, yv, Z, H), e in zip(mats, res2))
    J = float(g @ W2 @ g); df_j = len(kz) - len(kx)
    # AR(2) 検定（差分式の残差の2期ずれの相関、簡易版）
    num = 0.0; den = 0.0
    for (X, yv, Z, H), e, blk in zip(mats, res1, blocks):
        rd = blk[0]; ts = [r[0] for r in rd]; ed = dict(zip(ts, e[:len(rd)]))
        s_i = sum(ed[t]*ed[t-2] for t in ts if t-2 in ed); num += s_i; den += s_i**2
    m2 = num/np.sqrt(den) if den > 0 else np.nan
    return dict(rho_1step=float(b1[0]), se_1step=float(np.sqrt(V1[0, 0])), rho=float(b2[0]),
                n_inst=len(kz), n_ind=len(mats), hansen=J, hansen_df=df_j,
                hansen_p=float(1-stats.chi2.cdf(J, df_j)) if df_j > 0 else np.nan,
                ar2_z=float(m2), ar2_p=float(2*(1-stats.norm.cdf(abs(m2)))) if m2 == m2 else np.nan)
