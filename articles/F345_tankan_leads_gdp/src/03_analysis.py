"""短観 DI と GDP の前期比：ずらし相関、拡張窓の予測（AR(1) と AR(1)+ΔDI）、1次速報。results/main.json と CSV。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "panel_quarterly.csv")
d["t"] = d["year"] + (d["q"] - 1) / 4
DI = {"全規模全産業": "TK99F0000601GCQ00000", "全規模製造業": "TK99F1000601GCQ00000", "全規模非製造業": "TK99F2000601GCQ00000",
      "大企業製造業": "TK99F1000601GCQ01000", "大企業非製造業": "TK99F2000601GCQ01000", "大企業全産業": "TK99F0000601GCQ01000"}
for k, c in DI.items():
    d[f"dDI_{k}"] = d[c] - d[c].shift(1)
    d[f"DI_{k}"] = d[c]
d["y"] = d["gdp_latest"]
d["y_lag"] = d["y"].shift(1)
d["yf"] = d["gdp_first"]
d["yf_lag"] = d["gdp_first"].shift(1)
CRISIS = set([(2008, 4), (2009, 1), (2009, 2), (2020, 1), (2020, 2), (2020, 3), (2020, 4)])
d["crisis"] = [(y, q) in CRISIS for y, q in zip(d.year, d.q)]


def r(x, k=3):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


main = {}
# ずらし相関（ΔDI_t と y_{t+k}）
sample = d[(d.t >= 1994.5)]
xc = {}
for k in range(-2, 3):
    yy = sample["y"].shift(-k)
    ok = sample["dDI_全規模全産業"].notna() & yy.notna()
    xc[str(k)] = r(np.corrcoef(sample.loc[ok, "dDI_全規模全産業"], yy[ok])[0, 1])
main["crosscorr_dDI_y_lead_k"] = xc
okc = sample["dDI_全規模全産業"].notna() & sample["y"].notna() & ~sample["crisis"]
main["corr_lag0_excl_crisis"] = r(np.corrcoef(sample.loc[okc, "dDI_全規模全産業"], sample.loc[okc, "y"])[0, 1])
xc2 = {}
for k in range(-2, 3):
    yy = sample["y"].shift(-k); ok = sample["dDI_全規模全産業"].notna() & yy.notna() & ~sample["crisis"]
    xc2[str(k)] = r(np.corrcoef(sample.loc[ok, "dDI_全規模全産業"], yy[ok])[0, 1])
main["crosscorr_excl_crisis"] = xc2


def ols(X, y):
    X = np.column_stack([np.ones(len(y)), X])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return b


def oos(target="y", lag="y_lag", xcol="dDI_全規模全産業", start=2005.0, est_start=1994.5, end=2026.25):
    rows = []
    for i in d.index[(d.t >= start) & (d.t <= end)]:
        tr = d[(d.t >= est_start) & (d.t < d.loc[i, "t"])].dropna(subset=[target, lag, xcol])
        if d.loc[[i], [target, lag, xcol]].isna().any(axis=None) or len(tr) < 12:
            continue
        b0 = ols(tr[[lag]].values, tr[target].values)
        b1 = ols(tr[[lag, xcol]].values, tr[target].values)
        p0 = b0[0] + b0[1] * d.loc[i, lag]
        p1 = b1[0] + b1[1] * d.loc[i, lag] + b1[2] * d.loc[i, xcol]
        rows.append({"year": int(d.loc[i, "year"]), "q": int(d.loc[i, "q"]), "actual": d.loc[i, target], "pred_ar": p0, "pred_ardi": p1,
                     "crisis": bool(d.loc[i, "crisis"])})
    return pd.DataFrame(rows)


def score(o, mask=None):
    o = o if mask is None else o[mask]
    e0 = o.actual - o.pred_ar; e1 = o.actual - o.pred_ardi
    rm0, rm1 = np.sqrt((e0 ** 2).mean()), np.sqrt((e1 ** 2).mean())
    # Diebold–Mariano（2乗誤差の差、Newey–West ラグ1）
    dlt = (e0 ** 2 - e1 ** 2).values
    n = len(dlt); m = dlt.mean(); g0 = ((dlt - m) ** 2).mean(); g1 = ((dlt[1:] - m) * (dlt[:-1] - m)).mean()
    v = (g0 + 2 * 0.5 * g1) / n
    dm = m / np.sqrt(v) if v > 0 else np.nan
    sign0 = ((o.pred_ar < 0) == (o.actual < 0)).mean(); sign1 = ((o.pred_ardi < 0) == (o.actual < 0)).mean()
    neg = o.actual < 0
    return {"n": int(n), "rmse_ar": r(rm0), "rmse_ardi": r(rm1), "improve_pct": r(100 * (1 - rm1 / rm0), 1), "dm_stat": r(dm, 2),
            "dm_p_two_sided": r(2 * (1 - stats.norm.cdf(abs(dm))), 3) if not np.isnan(dm) else None,
            "sign_hit_ar": r(sign0), "sign_hit_ardi": r(sign1), "neg_quarters": int(neg.sum()),
            "neg_caught_ar": int(((o.pred_ar < 0) & neg).sum()), "neg_caught_ardi": int(((o.pred_ardi < 0) & neg).sum())}


main_oos = oos()
main_oos.round(4).to_csv(R / "oos_latest_2005.csv", index=False)
main["oos_latest_2005_2026"] = score(main_oos)
main["oos_latest_2005_2026_excl_crisis"] = score(main_oos, ~main_oos.crisis)
# 1次速報を目標に（推定も1次速報の系列だけ、2008年から予測）
f_oos = oos(target="yf", lag="yf_lag", start=2008.0, est_start=2004.0)
f_oos.round(4).to_csv(R / "oos_first_2008.csv", index=False)
main["oos_first_2008_2026"] = score(f_oos)
main["oos_first_2008_2026_excl_crisis"] = score(f_oos, ~f_oos.crisis)
l08 = main_oos[main_oos.year >= 2008]
main["oos_latest_2008_2026"] = score(l08)
main["oos_latest_2008_2026_excl_crisis"] = score(l08, ~l08.crisis)

# 頑健性
rob = {}
for k in DI:
    if k == "全規模全産業":
        continue
    rob[f"dDI_{k}"] = score(oos(xcol=f"dDI_{k}"))
rob["DI水準_全規模全産業"] = score(oos(xcol="DI_全規模全産業"))
rob["start2010"] = score(main_oos[main_oos.year >= 2010])
rob["start2010_excl_crisis"] = score(main_oos[(main_oos.year >= 2010) & ~main_oos.crisis])
main["robust"] = rob
# 全期間の回帰（参考）
full = d[(d.t >= 1994.5)].dropna(subset=["y", "y_lag", "dDI_全規模全産業"])
b = ols(full[["y_lag", "dDI_全規模全産業"]].values, full["y"].values)
main["full_sample_coef"] = {"const": r(b[0]), "y_lag": r(b[1]), "dDI": r(b[2]), "n": int(len(full))}

m0 = main["oos_latest_2005_2026"]; m1 = main["oos_latest_2005_2026_excl_crisis"]
main["hypotheses"] = {
    "H1": {"crosscorr": xc, "verdict": "支持" if xc["0"] >= xc["1"] else "外れ"},
    "H2": {"improve_pct": m0["improve_pct"], "verdict": "支持" if m0["improve_pct"] >= 10 else "外れ"},
    "H3": {"improve_all": m0["improve_pct"], "improve_excl": m1["improve_pct"], "verdict": "支持" if m1["improve_pct"] <= m0["improve_pct"] / 2 else "外れ"},
    "H4": {"first": main["oos_first_2008_2026"]["improve_pct"], "latest_same_period": main["oos_latest_2008_2026"]["improve_pct"],
           "verdict": "支持" if abs(main["oos_first_2008_2026"]["improve_pct"] - main["oos_latest_2008_2026"]["improve_pct"]) <= 5 else "外れ"},
}
with open(R / "main.json", "w", encoding="utf-8") as fo:
    json.dump(main, fo, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps({k: v for k, v in main.items() if k != "robust"}, ensure_ascii=False, indent=0))
print(json.dumps(main["robust"], ensure_ascii=False))
