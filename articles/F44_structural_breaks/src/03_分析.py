"""構造変化の分析：Chow 検定・sup-F・Bai–Perron（BIC/LWZ）・ブートストラップの区間・CUSUM・都道府県別・頑健性"""
import json
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.diagnostic import recursive_olsresiduals
from common import DATA, RES, SEED, bai_perron, info_criteria, fit_segments, seg_ssr

rng = np.random.default_rng(SEED)
d = pd.read_csv(DATA / "tfr_long.csv")
nat = d[d.pref == "全国"].set_index("year").tfr
nat = nat.loc[1950:2023]  # 1951年から毎年。1925・1930年は除く
assert nat.index.is_monotonic_increasing and len(nat) == 74
H_DEFAULT = 8
MAXM = 5


def run(series, h=H_DEFAULT, log=False, use_dummy=True, crit="bic", maxm=MAXM):
    y = np.log(series.values) if log else series.values.astype(float)
    t = series.index.values.astype(float)
    dummy = (series.index.values == 1966).astype(float) if (use_dummy and 1966 in series.index) else None
    res = bai_perron(y, t, h, maxm, dummy)
    ic = info_criteria(res, len(y), extra=(1 if dummy is not None else 0))
    m = int(ic.loc[ic[crit].idxmin(), "m"])
    bks = res[m][1]
    years = [int(t[k + 1]) for k in bks]  # 新しい区間が始まる年
    return dict(m=m, years=years, bks=bks, ic=ic, y=y, t=t, dummy=dummy)


def chow(series, year, use_dummy=True):
    y = series.values.astype(float); t = series.index.values.astype(float)
    dm = (series.index.values == 1966).astype(float) if use_dummy and 1966 in series.index else None
    k = 2 + (dm is not None)
    s0 = seg_ssr(y, t, dm)
    i = int(np.where(t == year)[0][0])
    def sub(a, b):
        dd = None if dm is None else dm[a:b]
        if dd is not None and (dd.sum() == 0):
            dd = None
        return seg_ssr(y[a:b], t[a:b], dd)
    s1 = sub(0, i) + sub(i, len(y))
    q = 2
    dfd = len(y) - 2 * 2 - (1 if dm is not None else 0)
    F = ((s0 - s1) / q) / (s1 / dfd)
    return F, 1 - stats.f.cdf(F, q, dfd)


out = {}
# ---- 1. 全国：Bai–Perron ----
base = run(nat)
out["national_base"] = dict(m=base["m"], years=base["years"], ic=base["ic"].drop(columns="breaks").round(3).to_dict("records"),
                            ic_breaks={int(r.m): [int(base["t"][k + 1]) for k in r.breaks] for r in base["ic"].itertuples()})
fitted, segs = fit_segments(base["y"], base["t"], base["bks"], base["dummy"])
out["national_segments"] = segs
pd.DataFrame(dict(year=nat.index, tfr=nat.values, fitted=fitted)).to_csv(RES / "national_fit.csv", index=False)
base["ic"].assign(breaks=[str([int(base["t"][k + 1]) for k in b]) for b in base["ic"].breaks]).to_csv(RES / "national_ic.csv", index=False)
print("national", base["m"], base["years"], segs)

# ---- 2. Chow 検定（決め打ちの年） ----
chows = []
for yr in [1975, 1990, 2006, 2016]:
    F, p = chow(nat, yr)
    chows.append(dict(year=yr, F=round(F, 2), p=p))
out["chow"] = chows
pd.DataFrame(chows).to_csv(RES / "chow.csv", index=False)
print("chow", chows)

# ---- 3. sup-F（1か所の折れ目、位置は不明）：p 値は残差のブロック・ブートストラップ ----
def supF(y, t, dm, h):
    s0 = seg_ssr(y, t, dm)
    best = 0; arg = None
    for i in range(h, len(y) - h + 1):
        d1 = None if dm is None or dm[:i].sum() == 0 else dm[:i]
        d2 = None if dm is None or dm[i:].sum() == 0 else dm[i:]
        s1 = seg_ssr(y[:i], t[:i], d1) + seg_ssr(y[i:], t[i:], d2)
        F = ((s0 - s1) / 2) / (s1 / (len(y) - 4))
        if F > best:
            best, arg = F, int(t[i])
    return best, arg

y = base["y"]; t = base["t"]; dm = base["dummy"]
F_obs, yr_obs = supF(y, t, dm, H_DEFAULT)
# 帰無仮説（折れ目なし）のもとで、AR(1) の残差を使って系列を作り直す
X0 = np.column_stack([np.ones_like(t), t, dm])
b0, *_ = np.linalg.lstsq(X0, y, rcond=None); e0 = y - X0 @ b0
rho = np.corrcoef(e0[:-1], e0[1:])[0, 1]
u = e0[1:] - rho * e0[:-1]
B = 499
Fs = []
for _ in range(B):
    uu = rng.choice(u, size=len(y), replace=True)
    ee = np.zeros(len(y)); ee[0] = e0[0]
    for k in range(1, len(y)):
        ee[k] = rho * ee[k - 1] + uu[k]
    Fs.append(supF(X0 @ b0 + ee, t, dm, H_DEFAULT)[0])
p_sup = float(np.mean(np.array(Fs) >= F_obs))
# 比較：誤差に時間のつながりがない（独立）と仮定した場合
Fs_iid = [supF(X0 @ b0 + rng.choice(e0, size=len(y), replace=True), t, dm, H_DEFAULT)[0] for _ in range(B)]
p_iid = float(np.mean(np.array(Fs_iid) >= F_obs))
q95_ar, q95_iid = float(np.percentile(Fs, 95)), float(np.percentile(Fs_iid, 95))
out["supF"] = dict(F=round(F_obs, 2), year=yr_obs, p_boot_ar1=p_sup, p_boot_iid=p_iid, q95_ar1=round(q95_ar, 1), q95_iid=round(q95_iid, 1), rho=round(float(rho), 3), B=B)
print("supF", out["supF"])

# ---- 4. 折れ目の年のブートストラップ区間（選ばれた m を固定、AR(1) 残差で作り直す） ----
fit_full = fitted
e = base["y"] - fit_full
rho1 = np.corrcoef(e[:-1], e[1:])[0, 1]
u1 = e[1:] - rho1 * e[:-1]
bs_years = []
for _ in range(299):
    uu = rng.choice(u1, size=len(y), replace=True)
    ee = np.zeros(len(y)); ee[0] = e[0]
    for k in range(1, len(y)):
        ee[k] = rho1 * ee[k - 1] + uu[k]
    yy = fit_full + ee
    r = bai_perron(yy, t, H_DEFAULT, base["m"], dm)
    bks = r[base["m"]][1]
    bs_years.append([int(t[k + 1]) for k in bks])
bs = np.array(bs_years)
ci = [dict(est=int(base["years"][j]), lo=int(np.percentile(bs[:, j], 5)), hi=int(np.percentile(bs[:, j], 95)),
           share_within2=float(np.mean(np.abs(bs[:, j] - base["years"][j]) <= 2))) for j in range(base["m"])]
out["break_ci90"] = ci
pd.DataFrame(bs, columns=[f"break{j+1}" for j in range(base["m"])]).to_csv(RES / "bootstrap_break_years.csv", index=False)
print("ci", ci)

# ---- 5. CUSUM（1975〜2023年を1本の直線で当てはめた場合） ----
s = nat.loc[1975:2023]
Xc = sm.add_constant(s.index.values.astype(float))
rr = recursive_olsresiduals(sm.OLS(s.values, Xc).fit(), skip=3, alpha=0.95)
cus = rr[5]  # 再帰的残差の累積和（標準化済み）、長さ n-k
nobs, kk = len(s), 2
nn = len(cus)
idx = np.arange(0, nn)
bound = 0.948 * np.sqrt(nobs - kk) * (1 + 2 * idx / (nobs - kk))  # Brown–Durbin–Evans の5%の線
cdf = pd.DataFrame(dict(year=s.index.values[-nn:], cusum=cus, lo=-bound, hi=bound))
cdf.to_csv(RES / "cusum_1975_2023.csv", index=False)
exceed = cdf[(cdf.cusum > cdf.hi) | (cdf.cusum < cdf.lo)]
out["cusum"] = dict(first_exceed=(int(exceed.year.iloc[0]) if len(exceed) else None), n_exceed=int(len(exceed)))
print("cusum", out["cusum"])

# ---- 6. 都道府県ごと（1972〜2023年） ----
prefs = [p for p in d.pref.unique() if p != "全国"]
pr = []
nat72 = nat.loc[1972:2023]
nat_r = run(nat72, use_dummy=False)
out["national_1972"] = dict(m=nat_r["m"], years=nat_r["years"])
for p in prefs:
    sp = d[(d.pref == p)].set_index("year").tfr.loc[1972:2023]
    assert len(sp) == 52, p
    r = run(sp, use_dummy=False, maxm=5)
    rl = run(sp, use_dummy=False, maxm=5, crit="lwz")
    _, sg = fit_segments(r["y"], r["t"], r["bks"])
    pr.append(dict(pref=p, m_bic=r["m"], years_bic=r["years"], m_lwz=rl["m"], years_lwz=rl["years"],
                   last_slope=sg[-1]["slope"], last_start=sg[-1]["start"]))
prdf = pd.DataFrame(pr)
prdf.to_csv(RES / "pref_breaks.csv", index=False)
allyrs = [y for ys in prdf.years_bic for y in ys]
out["pref"] = dict(m_counts=prdf.m_bic.value_counts().sort_index().to_dict(),
                   m_counts_lwz=prdf.m_lwz.value_counts().sort_index().to_dict(),
                   n_breaks=len(allyrs),
                   year_hist={int(k): int(v) for k, v in pd.Series(allyrs).value_counts().sort_index().items()},
                   n_with_break_2003_2008=int(sum(any(2003 <= y <= 2008 for y in ys) for ys in prdf.years_bic)),
                   n_with_break_2013_2018=int(sum(any(2013 <= y <= 2018 for y in ys) for ys in prdf.years_bic)),
                   n_last_slope_neg=int((prdf.last_slope < 0).sum()))
print("pref", out["pref"])

# ---- 7. 頑健性（全国） ----
rob = []
for name, kw, ser in [
    ("基本（1950〜、h=8、BIC、1966年ダミー）", {}, nat),
    ("最小区間 h=5", dict(h=5), nat),
    ("最小区間 h=10", dict(h=10), nat),
    ("対数をとる", dict(log=True), nat),
    ("LWZ で選ぶ", dict(crit="lwz"), nat),
    ("1966年ダミーなし", dict(use_dummy=False), nat),
    ("1960年から", {}, nat.loc[1960:]),
    ("1975年から", {}, nat.loc[1975:]),
    ("1972年から（都道府県と同じ期間）", dict(use_dummy=False), nat.loc[1972:]),
]:
    r = run(ser, **kw)
    rob.append(dict(setting=name, m=r["m"], years=r["years"]))
pref_rob = []
for name, kw in [("基本 h=8", {}), ("h=5", dict(h=5)), ("h=10", dict(h=10)), ("対数", dict(log=True))]:
    yrs = []; ms = []; n0308 = 0; n1318 = 0
    for p in prefs:
        sp = d[(d.pref == p)].set_index("year").tfr.loc[1972:2023]
        r = run(sp, use_dummy=False, maxm=5, **kw)
        ms.append(r["m"]); yrs += r["years"]
        n0308 += any(2003 <= y <= 2008 for y in r["years"]); n1318 += any(2013 <= y <= 2018 for y in r["years"])
    pref_rob.append(dict(setting=name, mean_m=round(float(np.mean(ms)), 2), n_pref_2003_2008=n0308, n_pref_2013_2018=n1318,
                         share_2003_2008=round(float(np.mean([2003 <= y <= 2008 for y in yrs])), 3) if yrs else None,
                         share_2013_2018=round(float(np.mean([2013 <= y <= 2018 for y in yrs])), 3) if yrs else None))
out["robust_national"] = rob
out["robust_pref"] = pref_rob
pd.DataFrame(rob).to_csv(RES / "robust_national.csv", index=False)
pd.DataFrame(pref_rob).to_csv(RES / "robust_pref.csv", index=False)
print(pd.DataFrame(rob).to_string()); print(pd.DataFrame(pref_rob).to_string())

json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=lambda o: o if not isinstance(o, np.generic) else o.item())
