"""頑健性：(a) 1回だけの調査で1年目の閉鎖が高く出る理由（設立年の違い） (b) 種別ごとの曲線 (c) 2019年までの設立に絞ったハザード比 (d) 1割の抽出をくり返したときのばらつき"""
import numpy as np, pandas as pd
from common import DATA, RES, SEED
from icens import *

d = pd.read_parquet(DATA / "firms.parquet")
d["year"] = (D0 + pd.to_timedelta(d.s, "D")).dt.year
M = np.arange(J + 1)
rows = []

def cmp(sub, label, k, **kw):
    t = km_days((sub.e - sub.s).values, sub.event.values, M / 12.0)
    L, R = observe(sub, k, **kw); Lm, Rm = to_months(L, R)
    S, _ = turnbull(Lm, Rm, tol=1e-13, maxit=300000)
    iv = Rm >= 0
    Smid = km_months(np.where(iv, np.ceil((Lm + np.where(iv, Rm, Lm)) / 2), Lm).astype(int), iv.astype(int))
    Srp = km_months(np.where(iv, Rm, Lm), iv.astype(int))
    Sln, _ = fit_param("lognormal", Lm, Rm)
    for nm, s_ in [("真の値", t), ("Turnbull", S), ("中点で代入", Smid), ("右端で代入", Srp), ("対数正規", Sln)]:
        r = dict(check=label, k=str(k), method=nm, n=len(sub))
        for y in (1, 3, 5, 10):
            r[f"closed_{y}y_pct"] = 100 * (1 - s_[12 * y]) if 12 * y <= J else np.nan
        r["max_abs_err_pt"] = 100 * np.abs(s_[1:121] - t[1:121]).max()
        rows.append(r)

# (a) 設立年の違い：2025年以降の設立を除くと、1回だけの調査の1年目はどうなるか
cmp(d, "全法人", "once")
cmp(d[d.year <= 2024], "2024年までの設立", "once")
cmp(d[d.year <= 2024], "2024年までの設立", 5)
# (b) 種別ごと
for kj in ["株式会社", "合同会社", "その他の法人"]:
    cmp(d[d.kindj == kj], kj, 5)
pd.DataFrame(rows).round(3).to_csv(RES / "robust_curves.csv", index=False)

# (c) 2019年までの設立のハザード比
VARS = ["合同会社", "その他の法人", "東京23区", "政令市"]
def hr(sub, k):
    X = np.column_stack([(sub.kindj == "合同会社"), (sub.kindj == "その他の法人"), (sub.area == "東京23区"), (sub.area == "政令市")]).astype(float)
    if k is None:
        T = np.round((sub.e - sub.s).values / YR, 4); ex = sub.event.values == 1
        L, R = T, np.where(ex, T, np.inf)
    else:
        L, R = observe(sub, k); Lm, Rm = to_months(L, R); L = Lm / 12.0; R = np.where(Rm < 0, np.inf, Rm / 12.0); ex = np.zeros(len(sub), bool)
    df = pd.DataFrame(X, columns=VARS); df["L"] = L; df["R"] = R; df["ex"] = ex
    g = df.groupby(VARS + ["L", "R", "ex"]).size().reset_index(name="n")
    b, se, _ = fit_ph(g.L.values, g.R.values, g[VARS].values, g.n.values, exact=g.ex.values.astype(bool))
    return np.exp(b)
hrows = []
sub = d[d.year <= 2019]
for k in [None, 5, "once"]:
    hrows.append(dict(subset="2019年までの設立", k=str(k), **dict(zip(VARS, hr(sub, k)))))
pd.DataFrame(hrows).round(3).to_csv(RES / "robust_hr.csv", index=False)

# (d) 1割の抽出を10回：5年おきの Turnbull と対数正規の誤差のばらつき
rng = np.random.default_rng(SEED)
srows = []
for rep in range(10):
    sub = d.sample(frac=0.1, random_state=int(rng.integers(1e9)))
    t = km_days((sub.e - sub.s).values, sub.event.values, M / 12.0)
    tfull = km_days((d.e - d.s).values, d.event.values, M / 12.0)
    L, R = observe(sub, 5); Lm, Rm = to_months(L, R)
    S, _ = turnbull(Lm, Rm, tol=1e-13, maxit=300000)
    Sln, _ = fit_param("lognormal", Lm, Rm)
    srows.append(dict(rep=rep, km_exact_vs_full_max=100 * np.abs(t[1:121] - tfull[1:121]).max(),
                      turnbull_max=100 * np.abs(S[1:121] - tfull[1:121]).max(),
                      lognormal_max=100 * np.abs(Sln[1:121] - tfull[1:121]).max(),
                      turnbull_5y=100 * (1 - S[60]), turnbull_10y=100 * (1 - S[120])))
pd.DataFrame(srows).round(3).to_csv(RES / "robust_subsample.csv", index=False)
print(pd.DataFrame(rows).round(2).to_string()); print(pd.DataFrame(hrows).round(3)); print(pd.DataFrame(srows).describe().round(2))
