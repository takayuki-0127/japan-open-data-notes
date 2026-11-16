"""H1〜H4 と頑健性（オフライン）。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "alcohol_by_age.csv")
AG = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
LOW = {"29歳以下": 20, "30～39歳": 30, "40～49歳": 40, "50～59歳": 50, "60～69歳": 60, "70歳以上": 70}
r3 = lambda x: round(float(x), 3)
def piv(item, col):
    return d[d.item == item].pivot(index="year", columns="age", values=col)
beer_q, beer_a = piv("beer", "quantity"), piv("beer", "amount")
hap_q, hap_a = piv("happoshu", "quantity"), piv("happoshu", "amount")
alc_a = piv("alcohol_total", "amount")

def change(P, s, e):
    a, b = P.loc[s].mean(), P.loc[e].mean()
    return pd.DataFrame({"start": a, "end": b, "logchange": 100 * np.log(b / a)}).loc[AG + ["平均"]]

S, E = [2002, 2003, 2004], [2023, 2024, 2025]
out = {}
c1 = change(beer_q, S, E); c1.round(3).to_csv(RES / "h1_beer_quantity_change.csv")
out["H1"] = {a: [r3(c1.loc[a, "start"]), r3(c1.loc[a, "end"]), r3(c1.loc[a, "logchange"])] for a in c1.index}
out["H1_verdict"] = "支持" if (c1.loc[AG, "logchange"] < 0).all() else "外れ"
young = c1.loc[["29歳以下", "30～39歳"], "logchange"].mean(); old = c1.loc[["60～69歳", "70歳以上"], "logchange"].mean()
out["H2"] = dict(young_mean=r3(young), old_mean=r3(old), gap=r3(young - old))
out["H2_verdict"] = "支持" if (young - old) <= -10 else "外れ"

# H3：10年おきの3時点で、年齢＋時代 と 世代＋時代 の当てはまり（対数）
def apc_fit(P, years):
    rows = []
    for y in years:
        for a in AG:
            rows.append(dict(year=y, age=a, cohort=y - LOW[a], ly=np.log(P.loc[y, a])))
    t = pd.DataFrame(rows)
    t["year_s"] = t.year.astype(str); t["cohort_s"] = t.cohort.astype(str)
    ap = smf.ols("ly ~ C(age) + C(year_s)", t).fit()
    cp = smf.ols("ly ~ C(cohort_s) + C(year_s)", t).fit()
    ac = smf.ols("ly ~ C(age) + C(cohort_s)", t).fit()
    return dict(years="-".join(map(str, years)), n=len(t), aic_age_period=r3(ap.aic), aic_cohort_period=r3(cp.aic), aic_age_cohort=r3(ac.aic),
                r2_age_period=r3(ap.rsquared), r2_cohort_period=r3(cp.rsquared), r2_age_cohort=r3(ac.rsquared),
                df_age_period=int(ap.df_model), df_cohort_period=int(cp.df_model)), t
h3a, ta = apc_fit(beer_q, [2005, 2015, 2025]); h3b, _ = apc_fit(beer_q, [2004, 2014, 2024])
ta.to_csv(RES / "h3_cells_2005_2015_2025.csv", index=False)
out["H3"] = [h3a, h3b]
out["H3_verdict"] = "支持" if all(h["aic_cohort_period"] < h["aic_age_period"] for h in (h3a, h3b)) else "外れ"

# H4：酒類に占めるビールの割合
sh = 100 * beer_a / alc_a
c4 = pd.DataFrame({"start": sh.loc[S].mean(), "end": sh.loc[E].mean()}).loc[AG + ["平均"]]; c4["change_pt"] = c4.end - c4.start
c4.round(3).to_csv(RES / "h4_beer_share.csv")
out["H4"] = {a: [r3(c4.loc[a, "start"]), r3(c4.loc[a, "end"]), r3(c4.loc[a, "change_pt"])] for a in c4.index}
out["H4_verdict"] = "支持" if (c4.loc[AG, "change_pt"] < 0).all() else "外れ"

# 頑健性
rob = []
ca = change(beer_a, S, E)
rob.append(dict(spec="R1 支出金額で H1・H2", all_down=bool((ca.loc[AG, "logchange"] < 0).all()),
                young=r3(ca.loc[["29歳以下", "30～39歳"], "logchange"].mean()), old=r3(ca.loc[["60～69歳", "70歳以上"], "logchange"].mean()),
                detail={a: r3(ca.loc[a, "logchange"]) for a in AG}))
bq = beer_q + hap_q
cb = change(bq, S, E)
rob.append(dict(spec="R2 ビール類（ビール＋発泡酒等）の数量で H1・H2", all_down=bool((cb.loc[AG, "logchange"] < 0).all()),
                young=r3(cb.loc[["29歳以下", "30～39歳"], "logchange"].mean()), old=r3(cb.loc[["60～69歳", "70歳以上"], "logchange"].mean()),
                detail={a: r3(cb.loc[a, "logchange"]) for a in AG}))
h3c, _ = apc_fit(beer_q, [2003, 2013, 2023])
rob.append(dict(spec="R3 H3 を 2003・2013・2023年で", **{k: v for k, v in h3c.items()}))
h3d, _ = apc_fit(bq, [2005, 2015, 2025])
rob.append(dict(spec="R3' H3 をビール類で（2005・2015・2025年）", **h3d))
c5 = change(beer_q, [2005, 2006, 2007], [2017, 2018, 2019])
rob.append(dict(spec="R4 2005〜07 → 2017〜19（コロナ・酒税改定の前）", all_down=bool((c5.loc[AG, "logchange"] < 0).all()),
                young=r3(c5.loc[["29歳以下", "30～39歳"], "logchange"].mean()), old=r3(c5.loc[["60～69歳", "70歳以上"], "logchange"].mean()),
                detail={a: r3(c5.loc[a, "logchange"]) for a in AG}))
out["robustness"] = rob
# 年ごとの表（図用）
beer_q.loc[:, AG + ["平均"]].round(3).to_csv(RES / "beer_quantity_by_year.csv")
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0))
