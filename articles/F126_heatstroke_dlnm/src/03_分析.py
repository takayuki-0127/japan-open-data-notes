"""03 分析：分布ラグ非線形モデル（DLNM）
- 目的変数：都道府県×日の熱中症の救急搬送人員（6〜9月）
- クロス基底：気温の自然スプライン（全国の6〜9月の最高気温の 50・75・90% 点に節）× 遅れの自然スプライン（0〜L日、対数等間隔の節2つ）
- 固定効果：都道府県×年×月（季節と年ごとの水準を吸収）、曜日
- ポアソン回帰（pyfixest.fepois）、標準誤差は都道府県でクラスター
- 比べ方：最高気温 35℃ の日と 25℃ の日。遅れごとの相対リスク（RR）と、0〜L日の累積 RR
"""
import json
import numpy as np
import pandas as pd
import pyfixest as pf
from common import DATA, RES, BLOCKS

np.random.seed(126)
P = pd.read_csv(DATA / "panel.csv", parse_dates=["date"])
P["year"] = P.date.dt.year; P["month"] = P.date.dt.month


def ns_basis(x, knots, bnd):
    """自然3次スプライン（ESL 5.2.1 の切断べき型、切片なし）。列数 = 内側の節の数 + 1。境界の外では線形"""
    lo, hi = bnd
    z = (np.asarray(x, float) - lo) / (hi - lo)
    k = (np.r_[lo, knots, hi] - lo) / (hi - lo)
    K = len(k)
    def d(j):
        return (np.maximum(z - k[j], 0) ** 3 - np.maximum(z - k[K - 1], 0) ** 3) / (k[K - 1] - k[j])
    return np.column_stack([z] + [d(j) - d(K - 2) for j in range(K - 2)])


def lag_basis(L, nk=2):
    lags = np.arange(L + 1)
    if L < 4:
        return np.eye(L + 1), []
    kn = np.exp(np.linspace(0, np.log(L), nk + 2))[1:-1]
    return np.column_stack([np.ones(L + 1), ns_basis(lags, kn, (0, L))]), kn


def prepare(var="tmax", L=10, data=P, tknots_q=(50, 75, 90)):
    d = data.sort_values(["pref", "date"]).copy()
    g = d.groupby(["pref", "year"])[var]
    lagm = np.column_stack([g.shift(l).values for l in range(L + 1)])
    summer = d.month.between(6, 9).values
    ref_all = d.loc[summer, var].dropna()
    tk = np.percentile(ref_all, tknots_q); bnd = (ref_all.min(), ref_all.max())
    C, lk = lag_basis(L)
    ok = summer & ~np.isnan(lagm).any(1) & d.total.notna().values
    Xl = lagm[ok]
    vx = len(tk) + 1
    cb = np.zeros((ok.sum(), vx * C.shape[1]))
    for l in range(L + 1):
        Bx = ns_basis(Xl[:, l], tk, bnd)
        for i in range(vx):
            for j in range(C.shape[1]):
                cb[:, i * C.shape[1] + j] += Bx[:, i] * C[l, j]
    out = d.loc[ok, ["pref", "date", "year", "month", "block", "total", "elderly", "severe", "death"]].copy()
    out["dow"] = out.date.dt.dayofweek
    out["ym"] = out.pref.astype(str) + "_" + out.year.astype(str) + "_" + out.month.astype(str)
    names = [f"cb{i}" for i in range(cb.shape[1])]
    out[names] = cb
    meta = dict(tk=tk, bnd=bnd, C=C, vx=vx, L=L, names=names, var=var)
    return out, meta


def fit(out, meta, y="total", vc=None):
    o = out[out.groupby("ym")[y].transform("sum") > 0]
    f = pf.fepois(f"{y} ~ {' + '.join(meta['names'])} + C(dow) | ym", data=o, vcov=vc or {"CRV1": "pref"})
    b = f.coef()[meta["names"]].values
    V = f._vcov[np.ix_([list(f.coef().index).index(n) for n in meta["names"]], [list(f.coef().index).index(n) for n in meta["names"]])]
    return b, V, len(o)


def predict(b, V, meta, t, ref):
    """温度 t（対 ref）の、遅れごとの logRR と SE、累積 logRR と SE"""
    Bt = ns_basis([t], meta["tk"], meta["bnd"])[0] - ns_basis([ref], meta["tk"], meta["bnd"])[0]
    C = meta["C"]
    M = np.array([np.kron(Bt, C[l]) for l in range(meta["L"] + 1)])  # (L+1) × p
    lr = M @ b; se = np.sqrt(np.einsum("ij,jk,ik->i", M, V, M))
    Mc = M.sum(0); cl = Mc @ b; cse = np.sqrt(Mc @ V @ Mc)
    return lr, se, cl, cse


def summarize(lr, se):
    lo = lr - 1.96 * se; hi = lr + 1.96 * se
    sig = np.where(lo > 0)[0]
    last = int(sig.max()) if len(sig) else -1
    # 「連続して」有意な最後の遅れ
    cont = -1
    for l in range(len(lr)):
        if lo[l] > 0: cont = l
        else: break
    neg = np.where(hi < 0)[0]
    return dict(last_sig_lag=last, last_contig_sig_lag=cont, neg_lags=[int(x) for x in neg],
                share_lag0=float(lr[0] / lr.sum()) if lr.sum() != 0 else None,
                share_lag01=float(lr[:2].sum() / lr.sum()) if lr.sum() != 0 else None)


res = {}; rob = []; curves = []

# ---- 基本：最高気温、遅れ 0〜10日 ----
out, meta = prepare("tmax", 10)
b, V, n = fit(out, meta)
res["n_obs"] = n; res["n_pref"] = int(out.pref.nunique()); res["years"] = [int(out.year.min()), int(out.year.max())]
res["total_cases"] = int(out.total.sum())
res["tknots"] = [float(x) for x in meta["tk"]]; res["bnd"] = [float(x) for x in meta["bnd"]]
for t in [28, 30, 33, 35, 37]:
    lr, se, cl, cse = predict(b, V, meta, t, 25)
    s = summarize(lr, se)
    res[f"t{t}"] = dict(lag_rr=np.exp(lr).round(3).tolist(), lag_lo=np.exp(lr - 1.96 * se).round(3).tolist(),
                        lag_hi=np.exp(lr + 1.96 * se).round(3).tolist(), cum_rr=float(np.exp(cl)),
                        cum_lo=float(np.exp(cl - 1.96 * cse)), cum_hi=float(np.exp(cl + 1.96 * cse)), **s)
    for l in range(11):
        curves.append(dict(model="基本", t=t, lag=l, rr=np.exp(lr[l]), lo=np.exp(lr[l] - 1.96 * se[l]), hi=np.exp(lr[l] + 1.96 * se[l])))
# 累積の気温反応曲線と、気温×遅れの面
grid = np.arange(18, 39.5, 0.5)
er = []
for t in grid:
    lr, se, cl, cse = predict(b, V, meta, t, 25)
    er.append(dict(t=t, cum_rr=np.exp(cl), lo=np.exp(cl - 1.96 * cse), hi=np.exp(cl + 1.96 * cse), lag0_rr=np.exp(lr[0]),
                   **{f"lag{l}": np.exp(lr[l]) for l in range(11)}))
pd.DataFrame(er).to_csv(RES / "exposure_response.csv", index=False)
np.save(RES / "base_coef.npy", b); np.save(RES / "base_vcov.npy", V)

# 同じ日だけのモデル（遅れを入れない）と比べる：35℃の RR
_, m0 = prepare("tmax", 1)


def fit_lag0():
    d = P.sort_values(["pref", "date"]).copy()
    d = d[d.month.between(6, 9) & d.total.notna() & d.tmax.notna()]
    B = ns_basis(d.tmax.values, m0["tk"], m0["bnd"])
    nm = [f"b{i}" for i in range(B.shape[1])]
    d[nm] = B; d["dow"] = d.date.dt.dayofweek
    d["ym"] = d.pref.astype(str) + "_" + d.year.astype(str) + "_" + d.month.astype(str)
    d = d[d.groupby("ym").total.transform("sum") > 0]
    f = pf.fepois(f"total ~ {' + '.join(nm)} + C(dow) | ym", data=d, vcov={"CRV1": "pref"})
    bb = f.coef()[nm].values; idx = [list(f.coef().index).index(x) for x in nm]; VV = f._vcov[np.ix_(idx, idx)]
    Bt = ns_basis([35], m0["tk"], m0["bnd"])[0] - ns_basis([25], m0["tk"], m0["bnd"])[0]
    return float(np.exp(Bt @ bb)), float(np.sqrt(Bt @ VV @ Bt))
rr0, se0 = fit_lag0()
res["lag0_only_model_rr35"] = rr0

# ---- 頑健性 ----
def rob_row(label, b, V, meta, t, ref, n):
    lr, se, cl, cse = predict(b, V, meta, t, ref)
    s = summarize(lr, se)
    rob.append(dict(check=label, n=n, t=round(float(t), 2), ref=round(float(ref), 2), cum_rr=np.exp(cl), cum_lo=np.exp(cl - 1.96 * cse), cum_hi=np.exp(cl + 1.96 * cse),
                    lag0_rr=np.exp(lr[0]), lag1_rr=np.exp(lr[1]), lag2_rr=np.exp(lr[2]), **s))
    return lr, se

rob_row("基本（最高気温・0〜10日）", b, V, meta, 35, 25, n)
# 1) 遅れの長さ
for L in [5, 7, 14, 21]:
    o, m = prepare("tmax", L); bb, VV, nn = fit(o, m)
    lr, se = rob_row(f"遅れ 0〜{L}日", bb, VV, m, 35, 25, nn)
    for l in range(L + 1):
        curves.append(dict(model=f"L{L}", t=35, lag=l, rr=np.exp(lr[l]), lo=np.exp(lr[l] - 1.96 * se[l]), hi=np.exp(lr[l] + 1.96 * se[l])))
# 2) 気温の指標（全国の 97.5% 点 対 50% 点で比べる）
for var, lab in [("tmax", "最高気温"), ("tmean", "日平均気温"), ("wbgt", "WBGT の近似")]:
    o, m = prepare(var, 10); bb, VV, nn = fit(o, m)
    s = P.loc[P.month.between(6, 9), var].dropna()
    lr, se = rob_row(f"指標：{lab}（97.5%点 対 50%点）", bb, VV, m, np.percentile(s, 97.5), np.percentile(s, 50), nn)
    for l in range(11):
        curves.append(dict(model=f"指標:{lab}", t=0, lag=l, rr=np.exp(lr[l]), lo=np.exp(lr[l] - 1.96 * se[l]), hi=np.exp(lr[l] + 1.96 * se[l])))
# 3) 地方ブロックごと（各ブロックの 97.5% 点 対 50% 点）
for bl in BLOCKS:
    sub = P[P.block == bl]
    o, m = prepare("tmax", 10, data=sub); bb, VV, nn = fit(o, m, vc="hetero")  # 県の数が少ないブロックがあるので、クラスターではなく不均一分散に頑健な SE
    s = sub.loc[sub.month.between(6, 9), "tmax"].dropna()
    hot, mid = np.percentile(s, 97.5), np.percentile(s, 50)
    lr, se = rob_row(f"地方：{bl}（{hot:.1f}℃ 対 {mid:.1f}℃）", bb, VV, m, hot, mid, nn)
    for l in range(11):
        curves.append(dict(model=f"地方:{bl}", t=hot, lag=l, rr=np.exp(lr[l]), lo=np.exp(lr[l] - 1.96 * se[l]), hi=np.exp(lr[l] + 1.96 * se[l])))
# 4) 2020年（コロナ・6月から）を除く／2023〜2025年だけ
for lab, sub in [("2020年を除く", P[P.date.dt.year != 2020]), ("2015〜2019年", P[P.date.dt.year <= 2019]), ("2021〜2025年", P[P.date.dt.year >= 2021])]:
    o, m = prepare("tmax", 10, data=sub); bb, VV, nn = fit(o, m)
    rob_row(lab, bb, VV, m, 35, 25, nn)
# 5) 年齢・重さ（高齢者／重症以上）
for y, lab in [("elderly", "高齢者だけ"), ("severe", "重症だけ")]:
    o, m = prepare("tmax", 10); o = o[o[y].notna()]
    bb, VV, nn = fit(o, m, y=y)
    lr, se = rob_row(lab, bb, VV, m, 35, 25, nn)
    for l in range(11):
        curves.append(dict(model=lab, t=35, lag=l, rr=np.exp(lr[l]), lo=np.exp(lr[l] - 1.96 * se[l]), hi=np.exp(lr[l] + 1.96 * se[l])))
# 6) 節の位置を変える（気温 25・50・75・90%点、遅れの節3つは別関数で）
o, m = prepare("tmax", 10, tknots_q=(25, 50, 75, 90)); bb, VV, nn = fit(o, m)
rob_row("気温の節を4つに", bb, VV, m, 35, 25, nn)
# 7) 標準誤差を不均一分散に頑健なもの（クラスターなし）にする
bb, VV, nn = fit(out, meta, vc="hetero")
rob_row("SE をクラスターなしに", bb, VV, meta, 35, 25, nn)

pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
pd.DataFrame(curves).to_csv(RES / "lag_curves.csv", index=False)
json.dump(res, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: res[k] for k in ["n_obs", "total_cases", "tknots", "lag0_only_model_rr35"]}, ensure_ascii=False, default=float))
print(json.dumps(res["t35"], ensure_ascii=False, default=float))
print(pd.DataFrame(rob).round(3).to_string())
