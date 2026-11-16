"""コーホート変化率法による推計と答え合わせ。結果は results/main.json と results/*.csv。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
R.mkdir(exist_ok=True)
import importlib.util
_spec = importlib.util.spec_from_file_location("core", pathlib.Path(__file__).with_name("core.py"))
core = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(core)
d, AGES, MID, REGIONS, PERIODS = core.d, core.AGES, core.MID, core.REGIONS, core.PERIODS
vec, ccr, step, metrics, rates = core.vec, core.ccr, core.step, core.metrics, core.rates

main = {}
RN = rates()
rt = pd.DataFrame({k: v for k, v in RN.items()}, index=AGES)
rt.to_csv(R / "cohort_change_ratios.csv")
main["ccr_2020_25"] = {a: round(float(v), 3) for a, v in zip(AGES[1:], RN["2020-25"][1:])}
main["ccr_by_period_selected"] = {k: {a: round(float(RN[k][AGES.index(a)]), 3) for a in ["25-29", "40-44", "55-59", "65-69", "70-74", "75-79", "85+"]} for k in RN}

# 実績
obs = {}
for y, b in [(2005, "販売農家"), (2010, "販売農家"), (2015, "販売農家"), (2015, "個人経営体"), (2020, "個人経営体"), (2025, "個人経営体")]:
    obs[f"{y}_{b}"] = metrics(vec(y, b))
main["observed"] = {k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in obs.items()}
pd.DataFrame(obs).T.to_csv(R / "observed_metrics.csv")

# ---- 答え合わせ --------------------------------------------------------------
bt = []
n15 = vec(2015, "個人経営体"); n20 = vec(2020, "個人経営体"); n25 = vec(2025, "個人経営体")
cases = [("2020（1期先）", n15, ["2010-15"], n20), ("2025（1期先）", n20, ["2015-20"], n25),
         ("2025（2期先）", n15, ["2010-15", "2010-15"], n25)]
for k in ["2005-10", "2010-15"]:
    cases.append((f"2025（1期先、{k}の率）", n20, [k], n25))
for lab, base, rs, act in cases:
    n = base.copy()
    for r in rs:
        n = step(n, RN[r])
    m, a = metrics(n), metrics(act)
    bt.append({"case": lab, "rates": "+".join(rs), "pred_total": round(m["total"]), "actual_total": round(a["total"]),
               "error_pct": round(100 * (m["total"] / a["total"] - 1), 2),
               "pred_share65": round(m["share65_pct"], 2), "actual_share65": round(a["share65_pct"], 2),
               "pred_under50": round(m["under50"]), "actual_under50": round(a["under50"]),
               "under50_error_pct": round(100 * (m["under50"] / a["under50"] - 1), 2)})
bt = pd.DataFrame(bt)
bt.to_csv(R / "backtest.csv", index=False)
main["backtest"] = bt.set_index("case").to_dict(orient="index")

# ---- 推計 --------------------------------------------------------------------
proj_rows = []
YEARS = [2030, 2035, 2040, 2045]
proj_age = {}
for k in list(PERIODS) + ["平均"]:
    n = n25.copy()
    for y in YEARS:
        n = step(n, RN[k])
        m = metrics(n)
        proj_rows.append({"rates": k, "year": y, **{kk: round(v, 3) for kk, v in m.items()}})
        proj_age[(k, y)] = n.copy()
proj = pd.DataFrame(proj_rows)
proj.to_csv(R / "projection_national.csv", index=False)
pd.DataFrame({f"{k}_{y}": v for (k, y), v in proj_age.items()}, index=AGES).round(1).to_csv(R / "projection_by_age.csv")
main["projection"] = {f"{r.rates}_{r.year}": {"total": round(r.total), "share65_pct": round(r.share65_pct, 1),
                                               "under50": round(r.under50), "under50_share_pct": round(r.under50_share_pct, 1),
                                               "mean_age": round(r.mean_age, 1)} for r in proj.itertuples()}
p35 = proj[proj.year == 2035]
p35_4 = p35[p35.rates.isin(PERIODS)]
main["range_2035"] = {"total": [round(p35_4.total.min()), round(p35_4.total.max())],
                      "share65_pct": [round(p35_4.share65_pct.min(), 1), round(p35_4.share65_pct.max(), 1)],
                      "under50_share_pct": [round(p35_4.under50_share_pct.min(), 1), round(p35_4.under50_share_pct.max(), 1)]}
p45 = proj[(proj.year == 2045) & proj.rates.isin(PERIODS)]
main["range_2045"] = {"total": [round(p45.total.min()), round(p45.total.max())]}
main["observed_2025"] = {k: round(v, 2) for k, v in metrics(n25).items()}

# ---- 頑健性 ------------------------------------------------------------------
rob = []
def proj_sum(groups, ratekey="2020-25", years=(2035,)):
    tot = {y: np.zeros(15) for y in years}
    for (level, name, sex) in groups:
        rr = rates(level, name, sex)[ratekey]
        n = vec(2025, "個人経営体", level, name, sex)
        for y in YEARS:
            n = step(n, rr)
            if y in tot:
                tot[y] += np.nan_to_num(n)
    return tot
main_35 = metrics(proj_age[("2020-25", 2035)])
rob.append({"check": "主の推計（全国・男女計、2020→25年の率）", **{k: round(v, 2) for k, v in main_35.items()}})
t = proj_sum([("全国", "全国", "男"), ("全国", "全国", "女")])[2035]
rob.append({"check": "男女別に推計して足す", **{k: round(v, 2) for k, v in metrics(t).items()}})
t = proj_sum([("地域", r, "計") for r in REGIONS])[2035]
rob.append({"check": "地域別（10地域）に推計して足す", **{k: round(v, 2) for k, v in metrics(t).items()}})
rob.append({"check": "4期間の平均の率", **{k: round(v, 2) for k, v in metrics(proj_age[("平均", 2035)]).items()}})
# 2015年を販売農家で通した2015→20年の率
r_alt = ccr(vec(2015, "販売農家"), n20)
n = n25.copy()
for y in YEARS[:2]:
    n = step(n, r_alt)
rob.append({"check": "2015→20年の率（2015年を販売農家で接続）", **{k: round(v, 2) for k, v in metrics(n).items()}})
# 平均年齢の近似：85歳以上=90歳
mid2 = MID.copy(); mid2[-1] = 90.0
nn = proj_age[("2020-25", 2035)]
rob.append({"check": "平均年齢で85歳以上を90歳とおく", "total": round(nn.sum(), 2), "mean_age": round(float((nn * mid2).sum() / nn.sum()), 2),
            "share65_pct": round(main_35["share65_pct"], 2), "under50": round(main_35["under50"], 2), "under50_share_pct": round(main_35["under50_share_pct"], 2)})
rob = pd.DataFrame(rob)
rob.to_csv(R / "robustness.csv", index=False)
main["robustness"] = rob.set_index("check").to_dict(orient="index")
main["mean_age_2025_alt90"] = round(float((n25 * mid2).sum() / n25.sum()), 2)

# 照合：2025年の表の2020年の再掲と累年統計の2020年
q = d[(d.year == 2020) & (d.level == "全国") & (d.sex == "計")].groupby("source")["n"].sum()
main["check_2020_two_tables"] = {k: float(v) for k, v in q.items()}

# ---- 仮説の判定 -------------------------------------------------------------
e1 = abs(main["backtest"]["2020（1期先）"]["error_pct"]); e2 = abs(main["backtest"]["2025（1期先）"]["error_pct"])
lo, hi = main["range_2035"]["total"]
main["hypotheses"] = {
    "H1": {"errors_pct": [main["backtest"]["2020（1期先）"]["error_pct"], main["backtest"]["2025（1期先）"]["error_pct"]],
           "verdict": "支持" if max(e1, e2) <= 5 else "外れ"},
    "H2": {"range": [lo, hi], "verdict": "支持" if (lo >= 500000 and hi <= 700000) else "外れ"},
    "H3": {"range": main["range_2035"]["share65_pct"], "verdict": "支持" if main["range_2035"]["share65_pct"][0] >= 65 else "外れ"},
    "H4": {"under50_share_2025": round(metrics(n25)["under50_share_pct"], 1),
           "under50_share_2035_main": round(main_35["under50_share_pct"], 1),
           "verdict": "支持" if main_35["under50_share_pct"] > metrics(n25)["under50_share_pct"] else "外れ"},
}
with open(R / "main.json", "w", encoding="utf-8") as f:
    json.dump(main, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main["hypotheses"], ensure_ascii=False))
print(bt.to_string())
print(proj[proj.year.isin([2030, 2035, 2045])].to_string())
print(rob.to_string())
print(rt.round(3).to_string())
