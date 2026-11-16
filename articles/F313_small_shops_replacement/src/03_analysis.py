"""H1〜H4 と頑健性。結果は results/main.json と CSV。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parents[1]
D, RES = ROOT / "data", ROOT / "results"; RES.mkdir(exist_ok=True)
r3 = lambda x: round(float(x), 3)
d = pd.read_csv(D / "retail_by_industry_year.csv", dtype={"code": str, "year": str})
RET = ("55", "56", "57", "58", "59", "60")
tot = d[d.code == "ｺｳﾘ"].set_index("year")
tot.to_csv(RES / "retail_total_by_year.csv")
out = {}
def totals(y0, y1):
    a, b = tot.loc[y0], tot.loc[y1]
    dt = b.est_total - a.est_total
    return dict(est=[int(a.est_total), int(b.est_total)], corp=[int(a.est_corp), int(b.est_corp)], indiv=[int(a.est_indiv), int(b.est_indiv)],
                change_total=int(dt), change_corp=int(b.est_corp - a.est_corp), change_indiv=int(b.est_indiv - a.est_indiv),
                indiv_share_of_decline=r3(100 * (b.est_indiv - a.est_indiv) / dt) if dt < 0 else None,
                floor_dlog=r3(100 * np.log(b.floor_m2 / a.floor_m2)), floor=[float(a.floor_m2), float(b.floor_m2)],
                floor_per_est_dlog=r3(100 * np.log((b.floor_m2 / b.est_total) / (a.floor_m2 / a.est_total))),
                floor_per_est=[r3(a.floor_m2 / a.est_total), r3(b.floor_m2 / b.est_total)],
                sales_dlog=r3(100 * np.log(b.sales_mil / a.sales_mil)), employees_dlog=r3(100 * np.log(b.employees / a.employees)))
out["main"] = totals("1991r", "2007")
m = out["main"]
out["H1_verdict"] = "支持" if (m["indiv_share_of_decline"] or 0) >= 90 and m["change_corp"] >= 0 else "外れ"
out["H2_verdict"] = "支持" if m["floor_dlog"] >= 15 else "外れ"
out["H4_verdict"] = "支持" if m["floor_per_est_dlog"] >= 40 else "外れ"

det = d[(d.level == "detail") & d.code.str[:2].isin(RET)]
def panel(y0, y1, xcol="floor_m2"):
    a = det[det.year == y0].set_index("code"); b = det[det.year == y1].set_index("code")
    p = pd.DataFrame({"name": b.name, "x0": a[xcol], "x1": b[xcol], "i0": a.est_indiv, "i1": b.est_indiv, "c0": a.est_corp, "c1": b.est_corp}).dropna()
    p = p[(p.x0 > 0) & (p.x1 > 0) & (p.i0 > 0) & (p.i1 > 0)]
    p["dx"] = 100 * np.log(p.x1 / p.x0); p["di"] = 100 * np.log(p.i1 / p.i0); p["dc"] = 100 * np.log(p.c1 / p.c0)
    return p
def slope(p, xc="dx", w=True):
    X = sm.add_constant(p[[xc]])
    mm = (sm.WLS(p.di, X, weights=p.i0) if w else sm.OLS(p.di, X)).fit(cov_type="HC3")
    return dict(slope=r3(mm.params[xc]), se=r3(mm.bse[xc]), p=r3(mm.pvalues[xc]), n=int(len(p)), r2=r3(mm.rsquared))
p = panel("1991r", "2007"); p.round(3).to_csv(RES / "industry_panel_1991r_2007.csv")
out["H3"] = slope(p); out["H3_verdict"] = "支持" if out["H3"]["slope"] < 0 and out["H3"]["p"] < 0.10 else "外れ"
nret = det[det.year == "2007"].code.nunique()
out["H3"]["n_detail_2007"] = int(nret)
out["H3"]["indiv_2007_covered_share"] = r3(100 * p.i1.sum() / tot.loc["2007", "est_indiv"])
rob = []
o = totals("1994", "2007"); rob.append(dict(spec="R1 始点を1994年", indiv_share_of_decline=o["indiv_share_of_decline"], corp_change=o["change_corp"], floor_dlog=o["floor_dlog"], floor_per_est_dlog=o["floor_per_est_dlog"], **{"H3_" + k: v for k, v in slope(panel("1994", "2007")).items()}))
o = totals("1991", "2007"); rob.append(dict(spec="R2 1991年の再集計前の値", indiv_share_of_decline=o["indiv_share_of_decline"], corp_change=o["change_corp"], floor_dlog=o["floor_dlog"], floor_per_est_dlog=o["floor_per_est_dlog"], **{"H3_" + k: v for k, v in slope(panel("1991", "2007")).items()}))
rob.append(dict(spec="R3 H3 を法人の事業所数の伸びで", **{"H3_" + k: v for k, v in slope(p, "dc").items()}))
rob.append(dict(spec="R4 H3 を重みなしで", **{"H3_" + k: v for k, v in slope(p, w=False).items()}))
out["robustness"] = rob
pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
out["by_major"] = {}
for c in RET:
    a = d[(d.code == c) & (d.year == "1991r")].iloc[0]; b = d[(d.code == c) & (d.year == "2007")].iloc[0]
    out["by_major"][c] = dict(name=b["name"], indiv=[int(a.est_indiv), int(b.est_indiv)], corp=[int(a.est_corp), int(b.est_corp)],
                              indiv_dlog=r3(100 * np.log(b.est_indiv / a.est_indiv)), corp_dlog=r3(100 * np.log(b.est_corp / a.est_corp)),
                              floor_dlog=r3(100 * np.log(b.floor_m2 / a.floor_m2)) if a.floor_m2 > 0 and b.floor_m2 > 0 else None)
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0))
