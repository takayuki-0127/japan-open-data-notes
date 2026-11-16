"""H1〜H4 と頑健性（オフライン）。"""
import json, pathlib, warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "print_by_age.csv")
cpi = pd.read_csv(ROOT / "data" / "cpi_books_annual.csv").set_index("year").cpi_books
AG = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
MID = {"29歳以下": 25, "30～39歳": 35, "40～49歳": 45, "50～59歳": 55, "60～69歳": 65, "70歳以上": 75}
r3 = lambda x: round(float(x), 3)
piv = lambda item: d[d.item == item].pivot(index="year", columns="age", values="amount")
P = {k: piv(k) for k in ["print_total", "newspaper", "magazine", "books"]}
real = {k: v.div(cpi, axis=0) * 100 for k, v in P.items()}
def change(X, s, e):
    a, b = X.loc[s].mean(), X.loc[e].mean()
    return pd.DataFrame({"start": a, "end": b, "logchange": 100 * np.log(b / a)}).loc[AG + ["平均"]]
yo = lambda c: (r3(c.loc[["29歳以下", "30～39歳"], "logchange"].mean()), r3(c.loc[["60～69歳", "70歳以上"], "logchange"].mean()))
S, E = [2002, 2003, 2004], [2023, 2024, 2025]
out = {}
tab = []
for k in P:
    for kind, X in (("nominal", P[k]), ("real", real[k])):
        c = change(X, S, E)
        tab.append(dict(item=k, kind=kind, **{a: r3(c.loc[a, "logchange"]) for a in AG + ["平均"]},
                        start_avg=r3(c.loc["平均", "start"]), end_avg=r3(c.loc["平均", "end"])))
T = pd.DataFrame(tab); T.to_csv(RES / "changes_by_item_age.csv", index=False)
g = lambda item, kind, col: float(T[(T.item == item) & (T.kind == kind)][col].iloc[0])
out["levels_avg_nominal"] = {k: [g(k, "nominal", "start_avg"), g(k, "nominal", "end_avg")] for k in P}
out["H1"] = dict(real_print_total=r3(g("print_total", "real", "平均")), nominal_print_total=r3(g("print_total", "nominal", "平均")),
                 cpi_books_change=r3(100 * np.log(cpi.loc[E].mean() / cpi.loc[S].mean())))
out["H1_verdict"] = "支持" if out["H1"]["real_print_total"] <= -30 else "外れ"
out["H2"] = dict(newspaper=r3(g("newspaper", "nominal", "平均")), books=r3(g("books", "nominal", "平均")), magazine=r3(g("magazine", "nominal", "平均")))
out["H2_verdict"] = "支持" if out["H2"]["newspaper"] < out["H2"]["books"] else "外れ"
cn = change(P["newspaper"], S, E); y, o = yo(cn)
out["H3"] = dict(young=y, old=o, gap=r3(y - o), detail={a: r3(cn.loc[a, "logchange"]) for a in AG})
out["H3_verdict"] = "支持" if (y - o) <= -10 else "外れ"
def apc(X):
    rows = [dict(year=yy, age=a, cohort5=int(5 * np.floor((yy - MID[a]) / 5)), ly=np.log(X.loc[yy, a])) for yy in X.index for a in AG if X.loc[yy, a] > 0]
    t = pd.DataFrame(rows)
    f = lambda fm: smf.ols(fm, t).fit()
    ap, ac, cp = f("ly ~ C(age) + C(year)"), f("ly ~ C(age) + C(cohort5)"), f("ly ~ C(cohort5) + C(year)")
    return dict(n=int(len(t)), aic_age_period=r3(ap.aic), aic_age_cohort=r3(ac.aic), aic_cohort_period=r3(cp.aic),
                r2_age_period=r3(ap.rsquared), r2_age_cohort=r3(ac.rsquared)), ac
h4, ac_np = apc(P["newspaper"]); out["H4"] = h4
out["H4_verdict"] = "支持" if h4["aic_age_cohort"] < h4["aic_age_period"] else "外れ"
co = ac_np.params.filter(like="cohort5"); eff = {"1925": 0.0}
for k, v in co.items(): eff[k.split("[T.")[1].rstrip("]")] = r3(100 * v)
out["newspaper_cohort_effects"] = eff
rob = []
c1 = change(P["print_total"].div(cpi, axis=0), S, [2017, 2018, 2019])
rob.append(dict(spec="R1 終点を2017〜19年（実質、書籍・他の印刷物）", avg=r3(c1.loc["平均", "logchange"])))
cr = change(real["newspaper"], S, E); y2, o2 = yo(cr)
rob.append(dict(spec="R2 新聞の実質で H3", young=y2, old=o2, gap=r3(y2 - o2)))
for k in ("books", "magazine"):
    h, _ = apc(P[k]); rob.append(dict(spec=f"R3 H4 を{ {'books': '書籍', 'magazine': '雑誌'}[k] }で", **h))
c4 = change(real["print_total"], [2005, 2006, 2007], E)
rob.append(dict(spec="R4 始点を2005〜07年（実質）", avg=r3(c4.loc["平均", "logchange"])))
out["robustness"] = rob
P["newspaper"].loc[:, AG + ["平均"]].round(1).to_csv(RES / "newspaper_by_year.csv")
pd.DataFrame({k: P[k]["平均"] for k in P}).round(1).to_csv(RES / "items_avg_by_year.csv")
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False))
print(T.to_string())
