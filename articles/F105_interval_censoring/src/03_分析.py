"""調査の間隔を変えて、区間打ち切りのデータから生存曲線とハザード比をどこまで取り戻せるかを調べる。
真の値は、正確な閉鎖日を使った Kaplan–Meier（日単位）と区分指数の比例ハザード。"""
import numpy as np, pandas as pd, json, time
from common import DATA, RES
from icens import *
from icens import _H0

d = pd.read_parquet(DATA / "firms.parquet")
ev = d.event.values
M = np.arange(J + 1)
truth = km_days((d.e - d.s).values, ev, M / 12.0)
YEARS = [1, 3, 5, 10]

def pw_curve(Lm, Rm):
    L = Lm / 12.0; R = np.where(Rm < 0, np.inf, Rm / 12.0)
    g = pd.DataFrame({"L": L, "R": R}).groupby(["L", "R"]).size().reset_index(name="n")
    _, _, ll0 = fit_ph(g.L.values, g.R.values, np.zeros((len(g), 0)), g.n.values)
    return np.exp(-_H0(M / 12.0, ll0))

def curves(Lm, Rm):
    out = {}
    out["Turnbull"], _ = turnbull(Lm, Rm, tol=1e-13, maxit=300000)
    iv = Rm >= 0
    for name, imp in [("中点で代入", (Lm + np.where(iv, Rm, Lm)) / 2.0), ("右端で代入", np.where(iv, Rm, Lm))]:
        Tm = np.where(iv, np.ceil(imp), Lm).astype(int)
        out[name] = km_months(Tm, iv.astype(int))
    for dist, nm in [("weibull", "ワイブル"), ("loglogistic", "対数ロジスティック"), ("lognormal", "対数正規")]:
        out[nm], _ = fit_param(dist, Lm, Rm)
    out["区分指数（1年ごと）"] = pw_curve(Lm, Rm)
    return out

SCHEMES = [("正確な日付（月に丸め）", dict(k=None)), ("1年おき", dict(k=1)), ("2年おき", dict(k=2)),
           ("3年おき", dict(k=3)), ("5年おき", dict(k=5)), ("1回だけ（2026-09-30）", dict(k="once")),
           ("5年おき・調査日を3月末に", dict(k=5, month=3, day=31)),
           ("設立から1年ごと", dict(k=1, scheme="anniv")), ("設立から5年ごと", dict(k=5, scheme="anniv"))]

rows, curve_rows, info = [], [], []
t0 = time.time()
for sname, kw in SCHEMES:
    L, R = observe(d, **kw)
    if kw.get("k") is None:
        Lm = np.floor(L / MON).astype(int); Rm = np.where(ev == 1, Lm + 1, -1)
        Lm = np.minimum(Lm, J); Rm = np.where(Rm > J, J, Rm)
    else:
        Lm, Rm = to_months(L, R)
    w = (Rm[Rm >= 0] - Lm[Rm >= 0])
    info.append(dict(scheme=sname, n_interval=int((Rm >= 0).sum()), mean_width_months=float(w.mean()),
                     median_width_months=float(np.median(w))))
    cs = curves(Lm, Rm)
    for mname, S in cs.items():
        err = (1 - S[1:121]) - (1 - truth[1:121])
        r = dict(scheme=sname, method=mname, max_abs_err_pt=100 * np.abs(err).max(), mean_abs_err_pt=100 * np.abs(err).mean())
        for y in YEARS:
            r[f"closed_{y}y_pct"] = 100 * (1 - S[12 * y])
        rows.append(r)
        for m in M:
            curve_rows.append(dict(scheme=sname, method=mname, month=m, S=S[m]))
    print(sname, round(time.time() - t0), flush=True)
for m in M:
    curve_rows.append(dict(scheme="真の値", method="KM（日単位）", month=m, S=truth[m]))
r = dict(scheme="真の値", method="KM（日単位）", max_abs_err_pt=0.0, mean_abs_err_pt=0.0)
for y in YEARS: r[f"closed_{y}y_pct"] = 100 * (1 - truth[12 * y])
rows.insert(0, r)
pd.DataFrame(rows).round(4).to_csv(RES / "curve_errors.csv", index=False)
pd.DataFrame(curve_rows).round(6).to_csv(RES / "curves.csv", index=False)
pd.DataFrame(info).round(2).to_csv(RES / "interval_widths.csv", index=False)

# ---- ハザード比（区分指数の比例ハザード） ----
VARS = ["合同会社", "その他の法人", "東京23区", "政令市"]
X_all = np.column_stack([(d.kindj == "合同会社"), (d.kindj == "その他の法人"), (d.area == "東京23区"), (d.area == "政令市")]).astype(float)

def hr_fit(L, R, exact, mask=None):
    df = pd.DataFrame(X_all, columns=VARS)
    df["L"] = L; df["R"] = R; df["ex"] = exact
    if mask is not None: df = df[mask]
    g = df.groupby(VARS + ["L", "R", "ex"]).size().reset_index(name="n")
    b, se, _ = fit_ph(g.L.values, g.R.values, g[VARS].values, g.n.values, exact=g.ex.values.astype(bool))
    return b, se

hr_rows = []
def add(sname, method, b, se):
    for v, bi, si in zip(VARS, b, se):
        hr_rows.append(dict(scheme=sname, method=method, var=v, HR=np.exp(bi), lo=np.exp(bi - 1.96 * si), hi=np.exp(bi + 1.96 * si)))

T = (d.e - d.s).values / YR
b, se = hr_fit(np.round(T, 4), np.where(ev == 1, np.round(T, 4), np.inf), ev == 1)
add("真の値", "正確な日付", b, se)
print("exact HR", np.exp(b).round(3), flush=True)
for sname, kw in [("1年おき", dict(k=1)), ("2年おき", dict(k=2)), ("3年おき", dict(k=3)), ("5年おき", dict(k=5)),
                  ("1回だけ（2026-09-30）", dict(k="once")), ("設立から5年ごと", dict(k=5, scheme="anniv"))]:
    L, R = observe(d, **kw)
    Lm, Rm = to_months(L, R)
    Ly = Lm / 12.0; Ry = np.where(Rm < 0, np.inf, Rm / 12.0)
    b, se = hr_fit(Ly, Ry, np.zeros(len(d), bool)); add(sname, "区間打ち切り", b, se)
    iv = Rm >= 0
    mid = np.where(iv, (Ly + Ry.clip(max=99)) / 2, Ly)
    b, se = hr_fit(mid, np.where(iv, mid, np.inf), iv); add(sname, "中点で代入", b, se)
    rp = np.where(iv, Ry.clip(max=99), Ly)
    b, se = hr_fit(rp, np.where(iv, rp, np.inf), iv); add(sname, "右端で代入", b, se)
    print(sname, "HR done", round(time.time() - t0), flush=True)
hr = pd.DataFrame(hr_rows).round(4)
hr.to_csv(RES / "hazard_ratios.csv", index=False)
print(hr.pivot_table(index=["scheme", "method"], columns="var", values="HR").round(3).to_string())
