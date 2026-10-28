"""F102 分析：円安の物価への伝わり方は、円安が大きいときだけ強いのか？

1. 線形 VAR（4変数：輸入物価〔契約通貨〕→ドル円→国内企業物価→消費者物価、Cholesky）
2. 閾値 VAR（TVAR）：しきい値変数は「前月までの12か月のドル円の変化率」。
   しきい値はグリッドで探し（対数行列式の最小化）、線形との差は sup-LR 検定（線形 VAR からのブートストラップ）
3. 局面ごとのインパルス応答と、パススルー率（消費者物価の累積の反応 ÷ ドル円の累積の反応）
   ブートストラップ（局面の並びは観測どおりに固定した再帰的ブートストラップ）で区間
4. 一般化インパルス応答（GIRF、Koop–Pesaran–Potter）：ショックの大きさ・向きを変えたとき、局面が切り替わることも含めて
5. 状態で分けた局所射影（設計の代替案）：大きい円安局面とそれ以外で、ドル円の動きへの反応を分ける
6. 頑健性：ラグ／しきい値変数（6か月・12か月の絶対値）／しきい値を固定／期間／順番
"""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from common import DATA, RES, SEED, VARS

rng = np.random.default_rng(SEED)
H = 36
clean = pd.read_csv(DATA / "mom_clean.csv", index_col=0, parse_dates=True)


def zvar(df: pd.DataFrame, kind: str) -> pd.Series:
    """t の局面を決めるしきい値変数（t-1 までの値だけを使う）
    z12/z6 : ドル円の12か月・6か月の変化（前月比の和、＋が円安）
    z12abs : 12か月の変化の大きさ（円高も含む）
    cpi12  : 消費者物価の過去12か月の上昇率（物価が上がっている時期か）"""
    if kind == "cpi12":
        return df["cpi"].rolling(12).sum().shift(1)
    k = 6 if kind.startswith("z6") else 12
    z = df["fx"].rolling(k).sum().shift(1)
    return z.abs() if kind.endswith("abs") else z


def lagmat(Y: np.ndarray, p: int) -> np.ndarray:
    T = Y.shape[0]
    X = [np.ones(T - p)]
    for i in range(1, p + 1):
        X.append(Y[p - i:T - i].T)
    return np.vstack(X).T


def ols(X, Y):
    B, *_ = np.linalg.lstsq(X, Y, rcond=None)
    E = Y - X @ B
    return B, E


def logdet(E):
    S = E.T @ E / E.shape[0]
    return np.linalg.slogdet(S)[1]


def prep(df: pd.DataFrame, p: int, kind: str, order):
    z = zvar(df, kind)
    Y = df[order].values
    X = lagmat(Y, p)
    Yd = Y[p:]
    zz = z.values[p:]
    ok = ~np.isnan(zz)
    return X[ok], Yd[ok], zz[ok], df.index[p:][ok], Y, z


def grid_search(X, Y, z, trim=0.15, n=71):
    qs = np.quantile(z, np.linspace(trim, 1 - trim, n))
    out = []
    for g in qs:
        S = z > g
        if S.mean() < trim or (~S).mean() < trim:
            continue
        _, E1 = ols(X[S], Y[S])
        _, E0 = ols(X[~S], Y[~S])
        E = np.zeros_like(Y)
        E[S], E[~S] = E1, E0
        out.append((g, logdet(E)))
    return np.array(out)


def irf(B, Sig, p, k, shock, H=H):
    """Cholesky で識別した shock 番目のショック。ドル円の当月の反応が1%になるよう基準化し、累積（水準）で返す"""
    A = [B[1 + i * k:1 + (i + 1) * k].T for i in range(p)]
    P = np.linalg.cholesky(Sig)
    Psi = [np.eye(k)]
    for h in range(1, H + 1):
        M = np.zeros((k, k))
        for i in range(1, min(h, p) + 1):
            M += A[i - 1] @ Psi[h - i]
        Psi.append(M)
    R = np.array([Ps @ P[:, shock] for Ps in Psi])
    return R


def regime_fit(X, Y, S):
    B1, E1 = ols(X[S], Y[S])
    B0, E0 = ols(X[~S], Y[~S])
    return (B0, E0, E0.T @ E0 / len(E0)), (B1, E1, E1.T @ E1 / len(E1))


def passthrough(R, ifx, icpi, hs=(12, 24)):
    C = np.cumsum(R, axis=0)
    C = C / C[0, ifx]  # 当月のドル円の反応を1%に
    return C, {h: C[h, icpi] / C[h, ifx] for h in hs}


def tvar_run(df, p=None, kind="z12", order=VARS, gamma=None, nboot=500, seed=SEED, keep_paths=False):
    rg = np.random.default_rng(seed)
    if p is None:
        p = P_MAIN
    X, Y, z, idx, Yfull, zfull = prep(df, p, kind, order)
    k = len(order)
    ifx, icpi, ippi = order.index("fx"), order.index("cpi"), order.index("ppi")
    grid = None
    if gamma is None:
        grid = grid_search(X, Y, z)
        gamma = grid[grid[:, 1].argmin(), 0]
    elif isinstance(gamma, str):  # 分位点で固定
        gamma = np.quantile(z, float(gamma))
    S = z > gamma
    (B0, E0, S0), (B1, E1, S1) = regime_fit(X, Y, S)
    R0 = irf(B0, S0, p, k, ifx)
    R1 = irf(B1, S1, p, k, ifx)
    C0, pt0 = passthrough(R0, ifx, icpi)
    C1, pt1 = passthrough(R1, ifx, icpi)
    _, ppt0 = passthrough(R0, ifx, ippi)
    _, ppt1 = passthrough(R1, ifx, ippi)
    # 局面の並びを観測どおりに固定した再帰的ブートストラップ
    T = len(Y)
    Ys0 = Yfull[:p].copy()
    bs = []
    paths = []
    for b in range(nboot):
        Ysim = np.zeros((T + p, k))
        # 最初の p か月は実データ（サンプルの最初の X に対応する値）
        Ysim[:p] = np.array([X[0, 1 + i * k:1 + (i + 1) * k] for i in range(p)])[::-1]
        i0 = rg.integers(0, len(E0), T)
        i1 = rg.integers(0, len(E1), T)
        for t in range(T):
            x = np.concatenate([[1.0]] + [Ysim[p + t - i] for i in range(1, p + 1)])
            if S[t]:
                Ysim[p + t] = x @ B1 + E1[i1[t]]
            else:
                Ysim[p + t] = x @ B0 + E0[i0[t]]
        Xs = lagmat(Ysim, p)
        Ysd = Ysim[p:]
        try:
            (b0, e0, s0), (b1, e1, s1) = regime_fit(Xs, Ysd, S)
            r0, r1 = irf(b0, s0, p, k, ifx), irf(b1, s1, p, k, ifx)
            c0, q0 = passthrough(r0, ifx, icpi)
            c1, q1 = passthrough(r1, ifx, icpi)
            _, w0 = passthrough(r0, ifx, ippi)
            _, w1 = passthrough(r1, ifx, ippi)
        except np.linalg.LinAlgError:
            continue
        bs.append([q0[12], q1[12], q0[24], q1[24], w0[12], w1[12], w0[24], w1[24]])
        if keep_paths:
            paths.append((c0, c1))
    bs = np.array(bs)
    res = dict(p=p, kind=kind, order=order, gamma=float(gamma), share_high=float(S.mean()),
               n=int(T), n_high=int(S.sum()),
               pt12_low=pt0[12], pt12_high=pt1[12], pt24_low=pt0[24], pt24_high=pt1[24],
               ppi12_low=ppt0[12], ppi12_high=ppt1[12], ppi24_low=ppt0[24], ppi24_high=ppt1[24],
               start=str(idx[0].date()), end=str(idx[-1].date()))
    names = ["pt12_low", "pt12_high", "pt24_low", "pt24_high", "ppi12_low", "ppi12_high", "ppi24_low", "ppi24_high"]
    for j, nm in enumerate(names):
        res[nm + "_lo"], res[nm + "_hi"] = np.percentile(bs[:, j], [2.5, 97.5])
    for h in (12, 24):
        d = bs[:, names.index(f"pt{h}_high")] - bs[:, names.index(f"pt{h}_low")]
        res[f"diff{h}"] = res[f"pt{h}_high"] - res[f"pt{h}_low"]
        res[f"diff{h}_lo"], res[f"diff{h}_hi"] = np.percentile(d, [2.5, 97.5])
        res[f"diff{h}_p_le0"] = float((d <= 0).mean())
        dp = bs[:, names.index(f"ppi{h}_high")] - bs[:, names.index(f"ppi{h}_low")]
        res[f"ppidiff{h}_lo"], res[f"ppidiff{h}_hi"] = np.percentile(dp, [2.5, 97.5])
    extra = dict(X=X, Y=Y, z=z, idx=idx, S=S, B0=B0, B1=B1, S0=S0, S1=S1, E0=E0, E1=E1, C0=C0, C1=C1,
                 grid=grid, paths=paths, Yfull=Yfull, zfull=zfull)
    return res, extra


# ---------- 0. ラグの選択（線形 VAR、BIC） ----------
df = clean[VARS].loc["1980-01-01":]
bic = {}
for p in range(1, 7):
    Yall = df.values
    Xp = lagmat(Yall, 6)[:, :1 + 4 * p]  # 同じ期間でそろえる
    Yp = Yall[6:]
    _, E = ols(Xp, Yp)
    T = len(Yp)
    bic[p] = logdet(E) + np.log(T) * (4 * (1 + 4 * p)) / T
P_MAIN = min(bic, key=bic.get)
print("BIC", {k: round(v, 4) for k, v in bic.items()}, "-> p =", P_MAIN)

# ---------- 1-3. 主設定 ----------
main, ex = tvar_run(df, nboot=500, keep_paths=True)
print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in main.items()}, ensure_ascii=False))

# 線形 VAR
X, Y, z = ex["X"], ex["Y"], ex["z"]
BL, EL = ols(X, Y)
SL = EL.T @ EL / len(EL)
RL = irf(BL, SL, P_MAIN, 4, 1)
CL, ptL = passthrough(RL, 1, 3)
_, pptL = passthrough(RL, 1, 2)
main["pt12_linear"], main["pt24_linear"] = ptL[12], ptL[24]
main["ppi12_linear"], main["ppi24_linear"] = pptL[12], pptL[24]

# sup-LR 検定（線形 VAR を帰無仮説としたブートストラップ。しきい値変数はシミュレーションしたドル円から作る）
grid = ex["grid"]
T = len(Y)
LR = T * (logdet(EL) - grid[:, 1].min())
p = P_MAIN
fx_hist = ex["Yfull"][:, 1]
nsim = 300
LRb = []
Xfirst = X[0]
for b in range(nsim):
    Ysim = np.zeros((T + p, 4))
    Ysim[:p] = np.array([Xfirst[1 + i * 4:1 + (i + 1) * 4] for i in range(p)])[::-1]
    ii = rng.integers(0, T, T)
    for t in range(T):
        x = np.concatenate([[1.0]] + [Ysim[p + t - i] for i in range(1, p + 1)])
        Ysim[p + t] = x @ BL + EL[ii[t]]
    # しきい値変数：最初の12か月は実データのドル円を使い、その後はシミュレーションの値
    # （実データの X[0] の前の12か月の実績 + シミュレーション）
    n_before = int(np.where(~np.isnan(ex["zfull"].values))[0][0])  # z が初めて出る位置
    start_pos = len(ex["Yfull"]) - T  # Y の最初の行が Yfull のどこか
    pre = fx_hist[start_pos - 12:start_pos]
    fxs = np.concatenate([pre, Ysim[p:, 1]])
    zs = pd.Series(fxs).rolling(12).sum().shift(1).values[12:]
    Xs = lagmat(Ysim, p)
    Ysd = Ysim[p:]
    _, Es = ols(Xs, Ysd)
    gs = grid_search(Xs, Ysd, zs, n=41)
    LRb.append(len(Ysd) * (logdet(Es) - gs[:, 1].min()))
LRb = np.array(LRb)
main["supLR"] = float(LR)
main["supLR_p"] = float((LRb >= LR).mean())
print("supLR", round(LR, 2), "p", main["supLR_p"])

# 局面の時期
S = ex["S"]
idx = ex["idx"]
reg = pd.DataFrame({"month": idx, "z12": z, "high": S.astype(int)})
reg.to_csv(RES / "regimes.csv", index=False, encoding="utf-8-sig")
# エピソード（連続する大きい円安の局面）
eps = []
cur = None
for m_, s_ in zip(idx, S):
    if s_ and cur is None:
        cur = [m_, m_]
    elif s_:
        cur[1] = m_
    elif cur is not None:
        eps.append(cur)
        cur = None
if cur is not None:
    eps.append(cur)
eps_df = pd.DataFrame([(a.strftime("%Y-%m"), b.strftime("%Y-%m"), (b.year - a.year) * 12 + b.month - a.month + 1) for a, b in eps],
                      columns=["start", "end", "months"])
eps_df.to_csv(RES / "high_regime_episodes.csv", index=False, encoding="utf-8-sig")
print(eps_df.to_string())

# グリッドと IRF の保存
pd.DataFrame(grid, columns=["gamma", "logdet"]).to_csv(RES / "threshold_grid.csv", index=False)
LRboot = pd.DataFrame({"LR_boot": LRb})
LRboot.to_csv(RES / "supLR_bootstrap.csv", index=False)
paths = ex["paths"]
P0 = np.array([c[0] for c in paths])
P1 = np.array([c[1] for c in paths])
rows = []
for h in range(H + 1):
    for j, v in enumerate(VARS):
        rows.append(dict(h=h, var=v,
                         low=ex["C0"][h, j], low_lo=np.percentile(P0[:, h, j], 5), low_hi=np.percentile(P0[:, h, j], 95),
                         high=ex["C1"][h, j], high_lo=np.percentile(P1[:, h, j], 5), high_hi=np.percentile(P1[:, h, j], 95),
                         linear=CL[h, j]))
pd.DataFrame(rows).to_csv(RES / "irf_regimes.csv", index=False, encoding="utf-8-sig")

# ---------- 4. GIRF（ショックの大きさ・向き、局面の切り替わりを含む） ----------
B0, B1, S0, S1, E0, E1 = ex["B0"], ex["B1"], ex["S0"], ex["S1"], ex["E0"], ex["E1"]
P0c, P1c = np.linalg.cholesky(S0), np.linalg.cholesky(S1)
# 構造ショック（標準化）をまとめて引く
U = np.vstack([np.linalg.solve(P0c, E0.T).T, np.linalg.solve(P1c, E1.T).T])
Hg = 24
start_pos = len(ex["Yfull"]) - T
fx_all = ex["Yfull"][:, 1]
sd_fx = {0: P0c[1, 1], 1: P1c[1, 1]}
R = 100
girf_rows = []
for delta in [-2, -1, 1, 2, 3]:
    for t0 in range(T):
        pos = start_pos + t0  # Yfull での位置（この月にショック）
        hist = ex["Yfull"][pos - p:pos]  # 直前の p か月
        fxh = fx_all[pos - 12:pos]
        draws = U[rng.integers(0, len(U), (R, Hg + 1))]
        out = {}
        for tag, shock in [("base", 0.0), ("shock", float(delta))]:
            Yh = np.tile(hist[None], (R, 1, 1))  # R × p × 4
            fxw = np.tile(fxh[None], (R, 1))  # R × 12
            path = np.zeros((R, Hg + 1, 4))
            for h in range(Hg + 1):
                zt = fxw[:, -12:].sum(1)
                hi = zt > main["gamma"]
                x = np.concatenate([np.ones((R, 1))] + [Yh[:, -i] for i in range(1, p + 1)], axis=1)
                mean = np.where(hi[:, None], x @ B1, x @ B0)
                u = draws[:, h].copy()
                if h == 0:
                    u[:, 1] += shock
                e = np.where(hi[:, None], u @ P1c.T, u @ P0c.T)
                y = mean + e
                path[:, h] = y
                Yh = np.concatenate([Yh[:, 1:], y[:, None]], axis=1)
                fxw = np.concatenate([fxw[:, 1:], y[:, 1:2]], axis=1)
            out[tag] = path
        g = (out["shock"] - out["base"]).mean(0)
        cg = np.cumsum(g, axis=0)
        girf_rows.append(dict(delta=delta, t0=str(idx[t0].date()), high0=int(S[t0]),
                              fx12=cg[12, 1], cpi12=cg[12, 3], ppi12=cg[12, 2],
                              fx24=cg[24, 1], cpi24=cg[24, 3], ppi24=cg[24, 2], fx0=cg[0, 1]))
G = pd.DataFrame(girf_rows)
G.to_csv(RES / "girf_by_history.csv", index=False, encoding="utf-8-sig")
gs = G.groupby(["delta", "high0"])[["fx0", "fx12", "cpi12", "ppi12", "fx24", "cpi24", "ppi24"]].mean()
gs["pt12"] = gs["cpi12"] / gs["fx12"]
gs["pt24"] = gs["cpi24"] / gs["fx24"]
ga = G.groupby("delta")[["fx0", "fx12", "cpi12", "fx24", "cpi24"]].mean()
ga["pt12"] = ga["cpi12"] / ga["fx12"]
ga["pt24"] = ga["cpi24"] / ga["fx24"]
ga["cpi12_per_fx0"] = ga["cpi12"] / ga["fx0"]
gs.to_csv(RES / "girf_summary_by_regime.csv", encoding="utf-8-sig")
ga.to_csv(RES / "girf_summary_all.csv", encoding="utf-8-sig")
print(gs.round(3))
print(ga.round(3))

# ---------- 5. 状態で分けた局所射影 ----------
def lp(df, p, gamma, kind="z12", split="state", Hmax=24):
    d = df.copy()
    d["z"] = zvar(d, kind)
    d["S"] = (d["z"] > gamma).astype(float)
    rows = []
    for h in range(Hmax + 1):
        dep = {v: d[v][::-1].rolling(h + 1).sum()[::-1] for v in ["cpi", "ppi", "fx", "imp_yen"]}
        Xd = pd.DataFrame(index=d.index)
        if split == "state":
            Xd["a"] = d["fx"] * d["S"]
            Xd["b"] = d["fx"] * (1 - d["S"])
            Xd["S"] = d["S"]
        elif split == "size":
            big = d["fx"].abs() > d["fx"].abs().quantile(0.8)
            Xd["a"] = d["fx"] * big
            Xd["b"] = d["fx"] * (~big)
        elif split == "sign":
            Xd["a"] = d["fx"].clip(lower=0)
            Xd["b"] = d["fx"].clip(upper=0)
        Xd["imp"] = d["imp"]
        for v in VARS:
            for i in range(1, p + 1):
                Xd[f"{v}_l{i}"] = d[v].shift(i)
        Xd = sm.add_constant(Xd)
        for v, yv in dep.items():
            dd = pd.concat([yv.rename("y"), Xd], axis=1).dropna()
            r = sm.OLS(dd["y"], dd.drop(columns="y")).fit(cov_type="HAC", cov_kwds={"maxlags": h + 1})
            c = r.cov_params()
            diff = r.params["a"] - r.params["b"]
            se_d = np.sqrt(c.loc["a", "a"] + c.loc["b", "b"] - 2 * c.loc["a", "b"])
            rows.append(dict(split=split, h=h, var=v, a=r.params["a"], a_se=r.bse["a"], b=r.params["b"], b_se=r.bse["b"],
                             diff=diff, diff_se=se_d, n=int(r.nobs)))
    return pd.DataFrame(rows)


LPs = pd.concat([lp(clean.loc["1980-01-01":], P_MAIN, main["gamma"], split=s) for s in ["state", "size", "sign"]])
LPs.to_csv(RES / "local_projections.csv", index=False, encoding="utf-8-sig")


def lp_pt(L, split, h):
    a = L[(L.split == split) & (L.h == h)].set_index("var")
    return dict(a=a.loc["cpi", "a"] / a.loc["fx", "a"], b=a.loc["cpi", "b"] / a.loc["fx", "b"],
                cpi_a=a.loc["cpi", "a"], cpi_b=a.loc["cpi", "b"], diff=a.loc["cpi", "diff"], diff_se=a.loc["cpi", "diff_se"],
                fx_a=a.loc["fx", "a"], fx_b=a.loc["fx", "b"],
                impy_a=a.loc["imp_yen", "a"], impy_b=a.loc["imp_yen", "b"])


lp_sum = {f"{s}_{h}": lp_pt(LPs, s, h) for s in ["state", "size", "sign"] for h in (12, 24)}
print(json.dumps({k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in lp_sum.items()}, ensure_ascii=False, indent=0))

# ---------- 6. 頑健性 ----------
variants = [
    ("主設定（ラグ{}・12か月・1981年〜）".format(P_MAIN), dict()),
    ("ラグ2", dict(p=2)),
    ("ラグ3", dict(p=3)),
    ("ラグ4", dict(p=4)),
    ("ラグ6", dict(p=6)),
    ("しきい値変数：6か月の変化", dict(kind="z6")),
    ("しきい値変数：12か月の変化の大きさ（円高も含む）", dict(kind="z12abs")),
    ("しきい値を固定：上位30%", dict(gamma="0.70")),
    ("しきい値を固定：上位20%", dict(gamma="0.80")),
    ("しきい値を固定：上位10%", dict(gamma="0.90")),
    ("しきい値を固定：下位20%（大きな円高とそれ以外）", dict(gamma="0.20")),
    ("しきい値を固定：下位10%（大きな円高とそれ以外）", dict(gamma="0.10")),
    ("しきい値変数：消費者物価の過去12か月の上昇率", dict(kind="cpi12")),
    ("期間：1995年〜", dict(start="1995-01-01")),
    ("期間：〜2021年（2022年以降を除く）", dict(end="2021-12-01")),
    ("期間：〜2012年", dict(end="2012-12-01")),
    ("順番：ドル円を最初に", dict(order=["fx", "imp", "ppi", "cpi"])),
]
rob = []
for i, (nm, kw) in enumerate(variants):
    if i == 0:
        r = dict(main)
    else:
        start = kw.pop("start", "1980-01-01")
        end = kw.pop("end", "2026-08-01")
        order = kw.get("order", VARS)
        r, _ = tvar_run(clean[VARS].loc[start:end], nboot=300, seed=SEED + i, **kw)
    r["variant"] = nm
    rob.append(r)
    print(nm, "γ=%.1f high=%.2f PT12 %.3f/%.3f PT24 %.3f/%.3f diff24 [%.3f, %.3f]" % (
        r["gamma"], r["share_high"], r["pt12_low"], r["pt12_high"], r["pt24_low"], r["pt24_high"], r["diff24_lo"], r["diff24_hi"]))
rob_df = pd.DataFrame(rob)
rob_df["order"] = rob_df["order"].astype(str)
rob_df.to_csv(RES / "robustness.csv", index=False, encoding="utf-8-sig")

main["bic"] = bic
main["lp"] = lp_sum
json.dump(main, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print("done")
