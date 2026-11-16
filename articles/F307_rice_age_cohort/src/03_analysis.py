"""H1〜H4 と頑健性（オフライン）。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "grains_by_age.csv")
AG = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
LOW = {"29歳以下": 20, "30～39歳": 30, "40～49歳": 40, "50～59歳": 50, "60～69歳": 60, "70歳以上": 70}
r3 = lambda x: round(float(x), 3)
piv = lambda item, col: d[d.item == item].pivot(index="year", columns="age", values=col)
rq, ra = piv("rice", "quantity"), piv("rice", "amount")
hs = piv("hh_size", "amount")
rpp = rq / hs  # 1人あたり

def change(P, s, e):
    a, b = P.loc[s].mean(), P.loc[e].mean()
    return pd.DataFrame({"start": a, "end": b, "logchange": 100 * np.log(b / a)}).loc[AG + ["平均"]]
def yo(c):
    return r3(c.loc[["29歳以下", "30～39歳"], "logchange"].mean()), r3(c.loc[["60～69歳", "70歳以上"], "logchange"].mean())

S, E, E2 = [2002, 2003, 2004], [2019, 2020, 2021], [2023, 2024, 2025]
out = {}
c1 = change(rq, S, E); c1.round(3).to_csv(RES / "h1_rice_quantity_change.csv")
out["H1"] = {a: [r3(c1.loc[a, "start"]), r3(c1.loc[a, "end"]), r3(c1.loc[a, "logchange"])] for a in c1.index}
out["H1_verdict"] = "支持" if (c1.loc[AG, "logchange"] < 0).all() else "外れ"
cp = change(rpp, S, E); cp.round(3).to_csv(RES / "h2_rice_per_person_change.csv")
out["H2"] = dict(avg_household=r3(c1.loc["平均", "logchange"]), avg_per_person=r3(cp.loc["平均", "logchange"]),
                 share_remaining=r3(cp.loc["平均", "logchange"] / c1.loc["平均", "logchange"]),
                 hh_size_avg=[r3(hs.loc[S, "平均"].mean()), r3(hs.loc[E, "平均"].mean())])
out["H2_verdict"] = "支持" if out["H2"]["share_remaining"] >= 0.7 else "外れ"
y, o = yo(c1); out["H3"] = dict(young_mean=y, old_mean=o, gap=r3(y - o))
out["H3_verdict"] = "支持" if (y - o) <= -10 else "外れ"

def apc_fit(P, years):
    rows = [dict(year=yy, age=a, cohort=yy - LOW[a], ly=np.log(P.loc[yy, a])) for yy in years for a in AG]
    t = pd.DataFrame(rows); t["year_s"] = t.year.astype(str); t["cohort_s"] = t.cohort.astype(str)
    f = lambda fm: smf.ols(fm, t).fit()
    ap, cp_, ac = f("ly ~ C(age) + C(year_s)"), f("ly ~ C(cohort_s) + C(year_s)"), f("ly ~ C(age) + C(cohort_s)")
    return dict(years="-".join(map(str, years)), aic_age_period=r3(ap.aic), aic_cohort_period=r3(cp_.aic), aic_age_cohort=r3(ac.aic),
                r2_age_period=r3(ap.rsquared), r2_cohort_period=r3(cp_.rsquared), r2_age_cohort=r3(ac.rsquared))
sets = [[2005, 2015, 2025], [2004, 2014, 2024], [2003, 2013, 2023]]
h4 = [apc_fit(rq, s) for s in sets]
out["H4"] = h4
out["H4_n_cohort_better"] = int(sum(h["aic_cohort_period"] < h["aic_age_period"] for h in h4))
out["H4_verdict"] = "支持" if out["H4_n_cohort_better"] >= 2 else "外れ"

rob = []
ce = change(rq, S, E2); y2, o2 = yo(ce)
rob.append(dict(spec="R1 終点を2023〜25年", all_down=bool((ce.loc[AG, "logchange"] < 0).all()), avg=r3(ce.loc["平均", "logchange"]), young=y2, old=o2,
                detail={a: r3(ce.loc[a, "logchange"]) for a in AG}))
ca = change(ra, S, E); y3, o3 = yo(ca)
rob.append(dict(spec="R2 支出金額で", all_down=bool((ca.loc[AG, "logchange"] < 0).all()), avg=r3(ca.loc["平均", "logchange"]), young=y3, old=o3,
                detail={a: r3(ca.loc[a, "logchange"]) for a in AG}))
y4, o4 = yo(cp)
rob.append(dict(spec="R3 1人あたりで H3", all_down=bool((cp.loc[AG, "logchange"] < 0).all()), avg=r3(cp.loc["平均", "logchange"]), young=y4, old=o4,
                detail={a: r3(cp.loc[a, "logchange"]) for a in AG}))
h4pp = [apc_fit(rpp, s) for s in sets]
rob.append(dict(spec="R3' 1人あたりで H4", n_cohort_better=int(sum(h["aic_cohort_period"] < h["aic_age_period"] for h in h4pp)), detail=h4pp))
c5 = change(rq, [2005, 2006, 2007], E); y5, o5 = yo(c5)
rob.append(dict(spec="R4 始点を2005〜07年", all_down=bool((c5.loc[AG, "logchange"] < 0).all()), avg=r3(c5.loc["平均", "logchange"]), young=y5, old=o5,
                detail={a: r3(c5.loc[a, "logchange"]) for a in AG}))
out["robustness"] = rob
rq.loc[:, AG + ["平均"]].round(3).to_csv(RES / "rice_quantity_by_year.csv")
rpp.loc[:, AG + ["平均"]].round(4).to_csv(RES / "rice_per_person_by_year.csv")
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False))
