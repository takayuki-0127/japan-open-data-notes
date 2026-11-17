"""共働きと夫のみ有業の世帯の食料支出の差（対数の差 ×100、%）。収入をそろえた差と推移。結果は results/ に書く。乱数は使わない。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "type_items.csv")
W = d.pivot_table(index="year", columns=["group", "item"], values="value").sort_index()
for g in sorted({g for g, _ in W.columns}):
    W[(g, "生鮮食品")] = W[(g, "生鮮魚介")] + W[(g, "生鮮肉")] + W[(g, "生鮮野菜")] + W[(g, "生鮮果物")]
    W[(g, "生鮮食品＋牛乳・卵")] = W[(g, "生鮮食品")] + W[(g, "牛乳")] + W[(g, "卵")]
W = W.sort_index(axis=1)
YEARS = W.index.to_numpy()

q = pd.read_csv(ROOT / "data" / "quintile_items.csv")
qw = q.pivot_table(index=["sample", "year", "quintile"], columns="item", values="value")
for c in [qw]:
    c["生鮮食品"] = c["生鮮魚介"] + c["生鮮肉"] + c["生鮮野菜"] + c["生鮮果物"]
    c["生鮮食品＋牛乳・卵"] = c["生鮮食品"] + c["牛乳"] + c["卵"]

FOOD = ["調理食品", "一般外食", "生鮮食品", "食料", "主食的調理食品", "他の調理食品", "生鮮食品＋牛乳・卵"]


def elasticity(item, sample="worker", base="消費支出"):
    """年ごとに、5つの五分位の log(品目) を log(基準) に回帰した傾きの平均（2018〜2025年）。"""
    bs = []
    for y in sorted(qw.loc[sample].index.get_level_values(0).unique()):
        t = qw.loc[(sample, y)]
        bs.append(np.polyfit(np.log(t[base].to_numpy()), np.log(t[item].to_numpy()), 1)[0])
    return float(np.mean(bs)), float(np.min(bs)), float(np.max(bs))


def gap(dual, single, item):
    return 100 * (np.log(W[(dual, item)]) - np.log(W[(single, item)]))


def trend(s):
    X = sm.add_constant((s.index.to_numpy() - 2000).astype(float))
    m = sm.OLS(s.to_numpy(), X).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
    b, se = m.params[1], m.bse[1]
    return {"slope_per_10y": 10 * b, "lo": 10 * (b - 1.96 * se), "hi": 10 * (b + 1.96 * se)}


def summarize(dual, single, years=None, base="消費支出", sample="worker"):
    out = {}
    yrs = YEARS if years is None else years
    budget = gap(dual, single, base).loc[yrs]
    for it in FOOD:
        g = gap(dual, single, it).loc[yrs]
        e = elasticity(it, sample, base)[0]
        adj = g - e * budget
        out[it] = {"mean": float(g.mean()), "pos_years": int((g > 0).sum()), "neg_years": int((g < 0).sum()),
                   "n_years": int(len(g)), "elasticity": e, "adj_mean": float(adj.mean()),
                   "first5_mean": float(g.loc[yrs[:5]].mean()), "last5_mean": float(g.loc[yrs[-5:]].mean())}
    out["_budget_gap_mean"] = float(budget.mean())
    return out


out = {"years": f"{YEARS.min()}〜{YEARS.max()}", "n_years": int(len(YEARS))}
D, S = "dual_kid2", "single_kid2"
main = summarize(D, S)
out["main"] = main

# 年ごとの表（図用）
yr = pd.DataFrame({"year": YEARS})
for it in ["調理食品", "一般外食", "生鮮食品", "食料", "消費支出", "実収入"]:
    yr[f"gap_{it}"] = gap(D, S, it).to_numpy()
    yr[f"dual_{it}"] = W[(D, it)].to_numpy()
    yr[f"single_{it}"] = W[(S, it)].to_numpy()
for it in ["調理食品", "一般外食", "生鮮食品"]:
    yr[f"adj_{it}"] = yr[f"gap_{it}"] - main[it]["elasticity"] * yr["gap_消費支出"]
    for g, lab in [(D, "dual"), (S, "single")]:
        yr[f"share_{lab}_{it}"] = 100 * W[(g, it)].to_numpy() / W[(g, "食料")].to_numpy()
yr["dual_age"] = W[(D, "世帯主の年齢")].to_numpy()
yr["single_age"] = W[(S, "世帯主の年齢")].to_numpy()
yr["dual_n"] = W[(D, "集計世帯数")].to_numpy()
yr["single_n"] = W[(S, "集計世帯数")].to_numpy()
yr.to_csv(RES / "gap_by_year.csv", index=False, float_format="%.4f")

el = []
for it in FOOD:
    for base in ["消費支出", "実収入"]:
        m, lo, hi = elasticity(it, "worker", base)
        el.append({"item": it, "base": base, "sample": "worker", "elasticity": m, "min_year": lo, "max_year": hi})
    m, lo, hi = elasticity(it, "all", "消費支出")
    el.append({"item": it, "base": "消費支出", "sample": "all", "elasticity": m, "min_year": lo, "max_year": hi})
pd.DataFrame(el).to_csv(RES / "elasticities.csv", index=False, float_format="%.4f")

# 仮説の判定
h1c, h1e = main["調理食品"], main["一般外食"]
out["H1"] = {"cooked_mean": h1c["mean"], "cooked_pos_years": h1c["pos_years"], "eatout_mean": h1e["mean"],
             "eatout_pos_years": h1e["pos_years"],
             "verdict": "支持" if (h1c["mean"] >= 5 and h1c["pos_years"] >= 20 and h1e["mean"] >= 5 and h1e["pos_years"] >= 20) else "外れ"}
h2 = main["生鮮食品"]
out["H2"] = {"fresh_mean": h2["mean"], "fresh_neg_years": h2["neg_years"],
             "verdict": "支持" if (h2["mean"] <= -3 and h2["neg_years"] >= 20) else "外れ"}
out["H3"] = {"cooked_adj_mean": h1c["adj_mean"], "elasticity": h1c["elasticity"], "budget_gap_mean": main["_budget_gap_mean"],
             "eatout_adj_mean": h1e["adj_mean"], "fresh_adj_mean": h2["adj_mean"],
             "verdict": "支持" if h1c["adj_mean"] >= 3 else "外れ"}
tr = trend(gap(D, S, "調理食品"))
out["H4"] = {**tr, "verdict": "支持" if tr["hi"] < 0 else ("外れ" if tr["lo"] > 0 else "判定できず")}
out["trend_other"] = {it: trend(gap(D, S, it)) for it in ["一般外食", "生鮮食品"]}
out["trend_adj"] = {it: trend(pd.Series(yr[f"adj_{it}"].to_numpy(), index=YEARS)) for it in ["調理食品", "一般外食", "生鮮食品"]}

# 水準（最初と最後の年）
for y in [int(YEARS.min()), int(YEARS.max())]:
    out[f"level_{y}"] = {lab: {it: float(W.loc[y, (g, it)]) for it in ["調理食品", "一般外食", "生鮮食品", "食料", "消費支出",
                                                                       "実収入", "世帯主の年齢", "集計世帯数"]}
                         for g, lab in [(D, "dual"), (S, "single")]}
out["mean_households"] = {"dual": float(W[(D, "集計世帯数")].mean()), "single": float(W[(S, "集計世帯数")].mean())}
out["mean_age_gap"] = float((W[(D, "世帯主の年齢")] - W[(S, "世帯主の年齢")]).mean())
out["income_gap_mean_pct"] = float(gap(D, S, "実収入").mean())

# 頑健性
rob = []
def add(name, s):
    rob.append({"check": name, "cooked": s["調理食品"]["mean"], "cooked_adj": s["調理食品"]["adj_mean"],
                "eatout": s["一般外食"]["mean"], "eatout_adj": s["一般外食"]["adj_mean"],
                "fresh": s["生鮮食品"]["mean"], "fresh_adj": s["生鮮食品"]["adj_mean"],
                "fresh_milk_egg": s["生鮮食品＋牛乳・卵"]["mean"], "budget_gap": s["_budget_gap_mean"]})
add("本線：夫婦と子供2人（消費支出の弾力性・勤労者世帯）", main)
add("夫婦のみの世帯", summarize("dual_couple", "single_couple"))
add("夫婦と子供1人の世帯", summarize("dual_kid1", "single_kid1"))
add("実収入に対する弾力性でそろえる", summarize(D, S, base="実収入"))
add("弾力性を二人以上の世帯（全体）で出す", summarize(D, S, sample="all"))
add("2020・2021年を除く", summarize(D, S, years=np.array([y for y in YEARS if y not in (2020, 2021)])))
rob = pd.DataFrame(rob)
rob.to_csv(RES / "robustness.csv", index=False, float_format="%.4f")
out["robustness"] = rob.to_dict(orient="records")

# 問い直し：妻の勤め先収入の区分（共働きの核家族・計）と、調理食品の内訳
re_rows = []
for g, lab in [("dual_nuc_wlow", "妻の勤め先収入 月1〜79,999円"), ("dual_nuc_whigh", "妻の勤め先収入 月8万円以上")]:
    for it in ["調理食品", "主食的調理食品", "他の調理食品", "一般外食", "生鮮食品"]:
        # 世帯の人数が違うので、1人あたりにしてから夫のみ有業（計）と比べる
        pc = 100 * (np.log(W[(g, it)] / W[(g, "世帯人員")]) - np.log(W[("single_all", it)] / W[("single_all", "世帯人員")]))
        bud = 100 * (np.log(W[(g, "消費支出")] / W[(g, "世帯人員")]) - np.log(W[("single_all", "消費支出")] / W[("single_all", "世帯人員")]))
        e = elasticity(it)[0]
        re_rows.append({"group": lab, "item": it, "per_person_gap": float(pc.mean()), "adj": float((pc - e * bud).mean()),
                        "pos_years": int((pc > 0).sum()), "budget_gap": float(bud.mean()),
                        "households_mean": float(W[(g, "集計世帯数")].mean())})
re_df = pd.DataFrame(re_rows)
re_df.to_csv(RES / "requestion_wife_income.csv", index=False, float_format="%.4f")
out["requestion_wife_income"] = re_df.to_dict(orient="records")
out["requestion_cooked_split"] = {it: {"mean": main[it]["mean"], "adj_mean": main[it]["adj_mean"]}
                                  for it in ["主食的調理食品", "他の調理食品"]}


def rnd(o):
    if isinstance(o, float):
        return round(o, 6)
    if isinstance(o, dict):
        return {k: rnd(v) for k, v in o.items()}
    if isinstance(o, list):
        return [rnd(v) for v in o]
    return o


(RES / "main.json").write_text(json.dumps(rnd(out), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(rnd({k: out[k] for k in ["H1", "H2", "H3", "H4", "trend_other", "trend_adj", "income_gap_mean_pct",
                                          "mean_age_gap", "mean_households", "requestion_cooked_split"]}), ensure_ascii=False, indent=1))
print(pd.DataFrame(main).T.round(2).to_string())
print(rob.round(2).to_string())
print(re_df.round(2).to_string())
print(pd.read_csv(RES / "elasticities.csv").round(2).to_string())
