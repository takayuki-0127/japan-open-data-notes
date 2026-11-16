"""H1〜H4 と頑健性。結果は results/main.json と CSV。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
D, RES = ROOT / "data", ROOT / "results"; RES.mkdir(exist_ok=True)
r3 = lambda x: round(float(x), 3)
d = pd.read_csv(D / "ritchi_by_industry.csv", dtype={"code": str})
fx = pd.read_csv(D / "usdjpy_annual.csv").set_index("year").usdjpy
T = d[d.code == "TOTAL"].pivot(index="year", columns="measure", values="value")
T["usdjpy"] = fx
T.to_csv(RES / "total_by_year.csv")
A, B = list(range(2015, 2020)), list(range(2021, 2026))
dl = lambda a, b: r3(100 * np.log(b / a))
out = {"check_new_2006": float(T.loc[2006, "new_count"])}
out["H1"] = {k: dict(avg_2015_19=r3(T.loc[A, k].mean()), avg_2021_25=r3(T.loc[B, k].mean()), dlog=dl(T.loc[A, k].mean(), T.loc[B, k].mean())) for k in ["count", "area_1000m2", "new_count", "capex_mil"]}
out["H1_verdict"] = "支持" if out["H1"]["count"]["dlog"] > 0 else "外れ"
cap = d[(d.measure == "capex_mil") & (d.code != "TOTAL") & (d.code != "old")].pivot_table(index="year", columns="name", values="value", aggfunc="sum")
EL = "電子･デバイス"
assert EL in cap.columns, cap.columns.tolist()
tot = T.capex_mil
ex = tot - cap[EL].fillna(0)
out["H2"] = dict(total_dlog=dl(tot.loc[A].mean(), tot.loc[B].mean()), ex_electronics_dlog=dl(ex.loc[A].mean(), ex.loc[B].mean()),
                 electronics_avg=[r3(cap[EL].loc[A].mean()), r3(cap[EL].loc[B].mean())])
out["H2_verdict"] = "支持" if out["H2"]["total_dlog"] >= 20 and out["H2"]["ex_electronics_dlog"] < out["H2"]["total_dlog"] / 2 else "外れ"
share = 100 * cap[EL].loc[B].sum() / tot.loc[B].sum()
out["H3"] = dict(electronics_share_2021_25=r3(share), electronics_share_2015_19=r3(100 * cap[EL].loc[A].sum() / tot.loc[A].sum()),
                 by_year={int(y): r3(100 * cap[EL].loc[y] / tot.loc[y]) for y in range(2015, 2026)})
out["H3_verdict"] = "支持" if share >= 20 else "外れ"
# 業種の寄与（設備投資額、2015〜19 → 2021〜25）
chg = (cap.loc[B].mean() - cap.loc[A].mean()).sort_values()
contrib = pd.DataFrame({"avg_2015_19": cap.loc[A].mean(), "avg_2021_25": cap.loc[B].mean(), "change": chg, "share_of_change": 100 * chg / (tot.loc[B].mean() - tot.loc[A].mean())}).sort_values("change", ascending=False)
contrib.round(3).to_csv(RES / "capex_contrib_by_industry.csv")
cnt = d[(d.measure == "count") & (d.code != "TOTAL") & (d.code != "old")].pivot_table(index="year", columns="name", values="value", aggfunc="sum")
cc = pd.DataFrame({"avg_2015_19": cnt.loc[A].mean(), "avg_2021_25": cnt.loc[B].mean()}); cc["change"] = cc.avg_2021_25 - cc.avg_2015_19
cc.sort_values("change").round(3).to_csv(RES / "count_change_by_industry.csv")
out["count_change_top"] = {k: r3(v) for k, v in cc.change.sort_values(ascending=False).head(5).items()}
out["count_change_bottom"] = {k: r3(v) for k, v in cc.change.sort_values().head(5).items()}
out["capex_contrib_top"] = {k: r3(v) for k, v in contrib.share_of_change.head(5).items()}
# H4 為替
rng = np.random.default_rng(20261116)
def fxcorr(lag=1, drop=()):
    y = 100 * np.log(T["count"]).diff(); x = 100 * np.log(T.usdjpy).diff().shift(lag)
    z = pd.DataFrame({"y": y, "x": x}).dropna(); z = z[~z.index.isin(drop)]
    r = float(np.corrcoef(z.x, z.y)[0, 1])
    perm = np.array([np.corrcoef(rng.permutation(z.x.values), z.y.values)[0, 1] for _ in range(5000)])
    return dict(r=r3(r), p=r3((np.abs(perm) >= abs(r)).mean()), n=int(len(z)), years=[int(z.index.min()), int(z.index.max())])
out["H4"] = fxcorr(1)
out["H4_verdict"] = "支持" if out["H4"]["r"] > 0 and out["H4"]["p"] < 0.10 else "外れ"
out["usdjpy"] = dict(avg_2015_19=r3(fx.loc[A].mean()), avg_2021_25=r3(fx.loc[B].mean()), dlog=dl(fx.loc[A].mean(), fx.loc[B].mean()))
rob = [dict(spec="R1 H1 を敷地面積で", dlog=out["H1"]["area_1000m2"]["dlog"]),
       dict(spec="R2 H1 を新設だけで", dlog=out["H1"]["new_count"]["dlog"]),
       dict(spec="R3 H4 を同じ年のドル円で", **fxcorr(0)),
       dict(spec="R4 H4 を2009・2010年を除いて", **fxcorr(1, (2009, 2010))),
       dict(spec="R5 H1 を2010〜14年平均と比べる", dlog=dl(T.loc[2010:2014, "count"].mean(), T.loc[B, "count"].mean()))]
out["robustness"] = rob
pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0)); print(T.round(0).to_string()); print(contrib.head(6).round(1).to_string())
