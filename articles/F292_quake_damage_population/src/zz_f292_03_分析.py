"""03 分析：2025年想定の都府県別・原因別の死者数を、人口の規模と年齢構成だけ変えて 2050 年まで動かす。
- 規模：各原因 × P_p(t)/P_p(2020)（社人研2023中位。2020年は国勢調査の実績）
  手法資料（sanko_gaiyo pp.28–29 ほか）では、人口の大きさに比例するのは 建物倒壊（建物1棟当たり滞留人口）、津波、
  火災 b（倒壊・焼失家屋内の救出困難者）・c（焼失人口＝焼失率×滞留人口）。
  急傾斜地（0.098×全壊棟数×0.7×滞留人口比率）と 火災 a（0.055×出火件数×屋内滞留人口比率）は「比率」なので人口の大きさは消える。
  表は 火災 を a/b/c に分けていないため、主の計算は全原因を人口に比例させる近似とし、
  感度として 急傾斜地と火災（全部）を固定した場合も出す（S1。火災 b・c まで固定するので、影響の上限側）。
- 年齢：津波の死者だけ × C_p(t)/C_p(2015)。C＝Σ年齢区分比率×重み（0.34, 0.62, 1.79, 2.81）。
  想定は 2015 年国勢調査の市区町村別比率で補正係数を作っている。ここでは都道府県の比率で近似する。
- 分解：対数平均（LMDI）で、変化を「規模」と「年齢」に分ける。
- H4：計画どおり「人口の規模＋年齢」で説明できる割合が半分未満かで判定（規模だけの割合も併記）。
都道府県の個別の値は出さない（集計だけ）。
"""
import sys, json, pathlib
import numpy as np, pandas as pd
out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
proc, res = out / "data/processed", out / "results"
res.mkdir(exist_ok=True)
CAUSES = ["建物倒壊", "津波", "急傾斜地", "火災", "ブロック塀等"]
W = {"main": [0.34, 0.62, 1.79, 2.81], "pool65": [0.34, 0.62, 2.30, 2.30],
     "half": [1 + (x - 1) / 2 for x in [0.34, 0.62, 1.79, 2.81]]}
d = pd.read_csv(proc / "deaths_long.csv")
d = d[d.cause.isin(CAUSES)]
pop = pd.read_csv(proc / "pop_long.csv")
checks = json.load(open(proc / "table_checks.json"))
tot = d.groupby("table").deaths.sum()
MAIN = int(tot.idxmax())
meta = {k: checks[MAIN][k] for k in ["地震動", "津波ケース", "季節時刻", "風速", "避難"]}


def C(src, year, w):
    p = pop[(pop.src == src) & (pop.year == year)].set_index("pref")
    sh = p[["a0_14", "a15_64", "a65_74", "a75p"]].div(p.total, axis=0)
    return pd.Series(sh.values @ np.array(w), index=sh.index)


def P(src, year):
    return pop[(pop.src == src) & (pop.year == year)].set_index("pref").total


def L(a, b):
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(np.isclose(a, b), a, (a - b) / (np.log(a) - np.log(b)))


def project(tab, year, src="ipss2023", base_year=2020, w="main", age_base=("ipss2018", 2015), prefs=None):
    """表 tab の死者を year の人口に置き換える。返り値：原因別の (基準, 規模だけ, 規模＋年齢, 規模効果, 年齢効果)。"""
    x = d[d.table == tab]
    if prefs is not None:
        x = x[x.pref.isin(prefs)]
    S = (P(src, year) / P(src, base_year))
    A = C(src, year, W[w]) / C(*age_base, W[w])
    outr = {}
    for c in CAUSES:
        y = x[x.cause == c].set_index("pref").deaths
        y = y[y > 0]
        s, a = S.reindex(y.index).values, (A.reindex(y.index).values if c == "津波" else np.ones(len(y)))
        d1 = y.values * s * a
        lm = L(d1, y.values)
        outr[c] = dict(base=float(y.sum()), size_only=float((y.values * s).sum()), both=float(d1.sum()),
                       eff_size=float((lm * np.log(s)).sum()), eff_age=float((lm * np.log(a)).sum()))
    return outr


def summ(r):
    b = sum(v["base"] for v in r.values())
    return dict(base=b, size_only=sum(v["size_only"] for v in r.values()), both=sum(v["both"] for v in r.values()),
                eff_size=sum(v["eff_size"] for v in r.values()), eff_age=sum(v["eff_age"] for v in r.values()))


YEARS = [2020, 2025, 2030, 2035, 2040, 2045, 2050]
M = {"main_table": MAIN, "main_meta": meta, "main_printed_total": checks[MAIN]["printed"]["合計"]}
# 主表の推移
traj = []
for t in YEARS:
    r = project(MAIN, t)
    s = summ(r)
    traj.append({"year": t, **{k: round(v, 1) for k, v in s.items()},
                 **{f"{c}_both": round(r[c]["both"], 1) for c in CAUSES},
                 **{f"{c}_size": round(r[c]["size_only"], 1) for c in CAUSES}})
pd.DataFrame(traj).to_csv(res / "A_main_trajectory.csv", index=False)
r50 = project(MAIN, 2050)
s50 = summ(r50)
M["main_2050"] = {k: round(v) for k, v in s50.items()}
M["main_2050_by_cause"] = {c: {k: round(v) for k, v in r50[c].items()} for c in CAUSES}
pct = lambda a, b: round(100 * (a / b - 1), 2)
M["H1_size_only_pct"] = pct(s50["size_only"], s50["base"])
M["H1"] = M["H1_size_only_pct"] <= -15
ts = r50["津波"]
M["H2_tsunami_offset_share"] = round(-ts["eff_age"] / ts["eff_size"], 3)
M["H2"] = M["H2_tsunami_offset_share"] >= 1 / 3
M["H3_net_pct"] = pct(s50["both"], s50["base"])
M["H3"] = M["H3_net_pct"] > -15
M["age_offset_share_total"] = round(-s50["eff_age"] / s50["eff_size"], 3)
# S1（レビューで追加）：急傾斜地と火災を人口に比例させず固定した場合
fix = ["急傾斜地", "火災"]
fx = sum(r50[c]["base"] for c in fix)
s1_size = sum(r50[c]["size_only"] for c in CAUSES if c not in fix) + fx
s1_both = sum(r50[c]["both"] for c in CAUSES if c not in fix) + fx
M["S1_fix_slope_fire"] = {"size_pct": pct(s1_size, s50["base"]), "net_pct": pct(s1_both, s50["base"]),
                          "diff_size_pt": round(pct(s1_size, s50["base"]) - M["H1_size_only_pct"], 2),
                          "diff_net_pt": round(pct(s1_both, s50["base"]) - M["H3_net_pct"], 2)}
# 被災の大きい 40 都府県の人口そのもの（参考：集計）
pp = d[d.table == MAIN].groupby("pref").deaths.sum()
pw = pp[pp > 0].index
M["affected_pop_change_2050_pct_unweighted"] = pct(P("ipss2023", 2050)[pw].sum(), P("ipss2023", 2020)[pw].sum())
M["affected_65p_share"] = {str(t): round(float(
    pop[(pop.src == "ipss2023") & (pop.year == t) & pop.pref.isin(pw)][["a65_74", "a75p"]].sum().sum()
    / pop[(pop.src == "ipss2023") & (pop.year == t) & pop.pref.isin(pw)].total.sum() * 100), 1) for t in [2020, 2050]}
M["affected_65p_share"]["2015"] = round(float(
    pop[(pop.src == "ipss2018") & (pop.year == 2015) & pop.pref.isin(pw)][["a65_74", "a75p"]].sum().sum()
    / pop[(pop.src == "ipss2018") & (pop.year == 2015) & pop.pref.isin(pw)].total.sum() * 100), 1)
# 2015→2020 で既に動いた年齢係数（想定の作り時点のずれ）
r20 = summ(project(MAIN, 2020))
M["age_drift_2015_2020_pct"] = pct(r20["both"], r20["base"])

# H4：2012年想定（最大 約32.3万人）→2025年想定（約29.8万人）。基準人口の 2010→2020 の変化だけでどれだけ説明できるか
P10, P20 = P("ipss2013", 2010), P("ipss2023", 2020)
x = d[d.table == MAIN]
k = x.assign(s=x.pref.map(P10 / P20))
d2012_size = float((k.deaths * k.s).sum())
A10 = C("ipss2013", 2010, W["main"]) / C("ipss2018", 2015, W["main"])
k["a"] = np.where(k.cause == "津波", k.pref.map(A10), 1.0)
d2012_both = float((k.deaths * k.s * k.a).sum())
base = float(x.deaths.sum())
obs = (298000 - 323000)
M["H4"] = dict(published_2012=323000, published_2025=298000, observed_change=obs,
               demographic_change_size=round(base - d2012_size), demographic_change_size_age=round(base - d2012_both),
               share_size=round((base - d2012_size) / obs, 3), share_size_age=round((base - d2012_both) / obs, 3))
M["H4"]["H4_as_planned_size_age"] = abs(M["H4"]["share_size_age"]) < 0.5  # 計画の判定（規模＋年齢）
M["H4"]["H4_size_only"] = abs(M["H4"]["share_size"]) < 0.5  # 参考：規模だけ

# 頑健性
rob = []
for tab in sorted(d.table.unique()):
    s = summ(project(int(tab), 2050))
    rob.append({"table": int(tab), **{k: checks[tab][k] for k in ["地震動", "津波ケース", "季節時刻", "風速", "避難"]},
                "base": round(s["base"]), "size_pct": pct(s["size_only"], s["base"]), "net_pct": pct(s["both"], s["base"]),
                "tsunami_share": round(summ({"津波": project(int(tab), 2050)["津波"]})["base"] / s["base"], 3),
                "offset": round(-s["eff_age"] / s["eff_size"], 3)})
R1 = pd.DataFrame(rob)
R1.to_csv(res / "B_R1_all_tables_2050.csv", index=False)
M["R1"] = {"net_pct_min": float(R1.net_pct.min()), "net_pct_max": float(R1.net_pct.max()),
           "size_pct_min": float(R1.size_pct.min()), "size_pct_max": float(R1.size_pct.max()),
           "corr_tsunami_share_net": round(float(R1[["tsunami_share", "net_pct"]].corr().iloc[0, 1]), 3),
           "n_net_le_-15": int((R1.net_pct <= -15).sum()), "n": len(R1)}
R = [{"case": "主（重み 0.34/0.62/1.79/2.81・2023推計・年齢基準2015）", **{k: v for k, v in
      [("size_pct", M["H1_size_only_pct"]), ("net_pct", M["H3_net_pct"]), ("offset", M["age_offset_share_total"])]}}]
for w, lab in [("pool65", "R2a 65歳以上を一つに（2.30）"), ("half", "R2b 重みの強さを半分")]:
    s = summ(project(MAIN, 2050, w=w))
    R.append({"case": lab, "size_pct": pct(s["size_only"], s["base"]), "net_pct": pct(s["both"], s["base"]),
              "offset": round(-s["eff_age"] / s["eff_size"], 3)})
for src, lab in [("ipss2023", "R3 比較用：2023推計で2045年"), ("ipss2018", "R3 2018推計で2045年")]:
    s = summ(project(MAIN, 2045, src=src, age_base=("ipss2018", 2015)))
    R.append({"case": lab, "size_pct": pct(s["size_only"], s["base"]), "net_pct": pct(s["both"], s["base"]),
              "offset": round(-s["eff_age"] / s["eff_size"], 3)})
s = summ(project(MAIN, 2050, age_base=("ipss2023", 2020)))
R.append({"case": "R4 年齢の基準を2020年に", "size_pct": pct(s["size_only"], s["base"]), "net_pct": pct(s["both"], s["base"]),
          "offset": round(-s["eff_age"] / s["eff_size"], 3)})
big = pp[pp >= 1000].index
s = summ(project(MAIN, 2050, prefs=big))
R.append({"case": f"R5 主表で死者1,000人以上の都府県だけ（{len(big)}）", "size_pct": pct(s["size_only"], s["base"]),
          "net_pct": pct(s["both"], s["base"]), "offset": round(-s["eff_age"] / s["eff_size"], 3)})
pd.DataFrame(R).to_csv(res / "C_robustness.csv", index=False)
M["robust"] = R

# 問い直し（事後に決めた）：同じ条件で「早期避難率高＋呼びかけ」に変わると、どれだけ減るか。人口の変化と比べる
cols = ["地震動", "津波ケース", "季節時刻", "風速"]
ck = pd.DataFrame([{**{k: c[k] for k in cols + ["避難"]}, "table": c["table"]} for c in checks])
ck["tot"] = ck.table.map(tot)
pv = ck.pivot_table(index=cols, columns="避難", values="tot")
pv["evac_pct"] = 100 * (pv["高＋呼びかけ"] / pv["低"] - 1)
lowtab = ck[ck.避難 == "低"].set_index(cols).table
pv["demog_pct"] = [R1.set_index("table").net_pct[lowtab[i]] for i in pv.index]
pv.reset_index().to_csv(res / "D_reask_evac_vs_demog.csv", index=False)
mk = tuple(meta[k] for k in cols)
M["reask"] = {"main_evac_pct": round(float(pv.loc[mk, "evac_pct"]), 2), "main_demog_pct": M["H3_net_pct"],
              "evac_pct_range": [round(float(pv.evac_pct.min()), 1), round(float(pv.evac_pct.max()), 1)],
              "demog_pct_range_low_tables": [round(float(pv.demog_pct.min()), 1), round(float(pv.demog_pct.max()), 1)],
              "n_pairs": len(pv), "n_evac_larger": int((pv.evac_pct.abs() > pv.demog_pct.abs()).sum()),
              "note": "事後に決めた比較"}
hitab = int(ck[(ck.避難 != "低") & (ck[cols].apply(tuple, axis=1) == mk)].table.iloc[0])
s_hi = summ(project(hitab, 2050))
M["reask"]["main_high_table"] = hitab
M["reask"]["main_high_table_2050_net_pct"] = pct(s_hi["both"], s_hi["base"])
json.dump(M, open(res / "main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: M[k] for k in ["main_table", "main_meta", "H1_size_only_pct", "H2_tsunami_offset_share",
                                     "H3_net_pct", "age_offset_share_total", "S1_fix_slope_fire", "H4", "R1", "reask",
                                     "age_drift_2015_2020_pct", "affected_65p_share",
                                     "affected_pop_change_2050_pct_unweighted"]}, ensure_ascii=False, indent=0))
print(pd.DataFrame(R).to_string())
print(json.dumps(M["main_2050_by_cause"], ensure_ascii=False))
