"""03 分析：仮説 H1〜H4、頑健性、問い直し。結果は results/main.json と CSV。"""
import json, pathlib, math
import numpy as np, pandas as pd
import statsmodels.api as sm
from scipy import stats
B = pathlib.Path(__file__).resolve().parents[1]
P, OUT = B / "data" / "processed", B / "results"
OUT.mkdir(exist_ok=True)
jma = pd.read_csv(P / "jma_counts.csv").set_index("year")
pay = pd.read_csv(P / "payouts_fy_real.csv").set_index("fy")
res_nat = pd.read_csv(P / "residential_national.csv").set_index("fy")
rev = pd.read_csv(B / "data" / "raw" / "giroj_revisions.csv")
defl = pd.read_csv(B / "data" / "raw" / "deflator_from_F256.csv").set_index("fy")
M = {}

def trend(y, years, drop=()):
    """準ポアソン回帰の年率の傾き（%）と95%区間。"""
    m = ~np.isin(years, list(drop))
    X = sm.add_constant(years[m] - 2000.0)
    f = sm.GLM(y[m], X, family=sm.families.Poisson()).fit(scale="X2")
    b, se = f.params[1], f.bse[1]
    return {"pct_per_yr": 100 * (math.exp(b) - 1), "lo": 100 * (math.exp(b - 1.96 * se) - 1), "hi": 100 * (math.exp(b + 1.96 * se) - 1), "b": b, "se": se, "disp": f.scale}

def ols_log(y, years):
    m = y > 0
    f = sm.OLS(np.log(y[m]), sm.add_constant(years[m] - 2000.0)).fit()
    b, se = f.params[1], f.bse[1]
    return {"pct_per_yr": 100 * (math.exp(b) - 1), "lo": 100 * (math.exp(b - 1.96 * se) - 1), "hi": 100 * (math.exp(b + 1.96 * se) - 1), "n_used": int(m.sum())}

yrs = jma.index.values.astype(float)
# ---- H1
s50 = jma["amdhour50mm"].values.astype(float)
t50 = trend(s50, yrs)
first10, last10 = jma.loc[1976:1985, "amdhour50mm"].mean(), jma.loc[2016:2025, "amdhour50mm"].mean()
M["H1"] = {"trend": t50, "first10": first10, "last10": last10, "ratio": last10 / first10,
           "per_decade_pct": 100 * (math.exp(10 * t50["b"]) - 1),
           "support": bool(t50["lo"] > 0 and last10 / first10 >= 1.3)}
# 頑健性：しきい値・推定法・外れ年
rob = []
for c in jma.columns:
    y = jma[c].values.astype(float)
    t = trend(y, yrs); o = ols_log(y, yrs); tx = trend(y, yrs, drop=(2004, 2011))
    rob.append({"series": c, "pois_pct": t["pct_per_yr"], "pois_lo": t["lo"], "pois_hi": t["hi"], "disp": t["disp"],
                "ols_pct": o["pct_per_yr"], "ols_lo": o["lo"], "ols_hi": o["hi"], "ols_n": o["n_used"],
                "pois_ex0411_pct": tx["pct_per_yr"],
                "first10": jma.loc[1976:1985, c].mean(), "last10": jma.loc[2016:2025, c].mean(),
                "ratio10": jma.loc[2016:2025, c].mean() / jma.loc[1976:1985, c].mean()})
rob = pd.DataFrame(rob); rob.to_csv(OUT / "A_hazard_trends.csv", index=False)
M["hazard_trends"] = rob.round(4).to_dict(orient="records")

# ---- H2：料率の累計 vs 改定の基データ期間の大雨の増え方
rev["mult"] = 1 + rev["avg_change_pct"] / 100
cum = float(rev["mult"].prod())
def win_mean(c, end, w):
    return jma.loc[end - w + 1:end, c].mean()
haz = {}
for w in (5, 10, 15):
    for c in jma.columns:
        haz[(c, w)] = win_mean(c, 2022, w) / win_mean(c, 2012, w)
h2_ratio_main = haz[("amdhour50mm", 10)]
M["H2"] = {"cum_mult": cum, "cum_pct": 100 * (cum - 1), "mean_rev_pct": float(rev["avg_change_pct"].mean()),
           "geo_mean_rev_pct": 100 * (cum ** (1 / 5) - 1),
           "haz_ratio_10y_2012_2022": h2_ratio_main, "haz_pct": 100 * (h2_ratio_main - 1),
           "rate_over_haz": (cum - 1) / (h2_ratio_main - 1) if h2_ratio_main != 1 else None,
           "support": bool((cum - 1) >= 2 * (h2_ratio_main - 1)),
           "mean10_2003_2012": win_mean("amdhour50mm", 2012, 10), "mean10_2013_2022": win_mean("amdhour50mm", 2022, 10)}
h2r = pd.DataFrame([{"series": c, "window": w, "haz_ratio": v, "haz_pct": 100 * (v - 1), "rate_pct": 100 * (cum - 1),
                     "rate_ge_2x": bool((cum - 1) >= 2 * (v - 1))} for (c, w), v in haz.items()])
h2r.to_csv(OUT / "B_rate_vs_hazard_windows.csv", index=False)
M["H2_robust"] = {"n_cases": len(h2r), "n_rate_ge_2x": int(h2r["rate_ge_2x"].sum()),
                  "haz_pct_min": float(h2r["haz_pct"].min()), "haz_pct_max": float(h2r["haz_pct"].max()),
                  "amdhour50_by_window": {int(w): float(100 * (haz[("amdhour50mm", w)] - 1)) for w in (5, 10, 15)}}

# ---- H3：年度の支払保険金 vs その年の大雨回数
dfp = pay.join(jma, how="inner")
def sp(a, b):
    r, p = stats.spearmanr(a, b); return float(r), float(p)
h3 = {}
for col in ("合計", "大雨", "台風"):
    for c in ("amdhour50mm", "amdday200mm", "amd3hour100mm"):
        h3[f"{col}|{c}"] = sp(dfp[col], dfp[c])
r_main, p_main = h3["合計|amdhour50mm"]
ex18 = dfp.drop(index=2018)
r_ex18, p_ex18 = sp(ex18["合計"], ex18["amdhour50mm"])
M["H3"] = {"n_years": int(len(dfp)), "spearman_total_50mm": r_main, "p": p_main, "spearman_ex2018": r_ex18, "p_ex2018": p_ex18,
           "all": {k: {"r": v[0], "p": v[1]} for k, v in h3.items()}, "support": bool(r_main < 0.5),
           "share_typhoon": float(pay["台風"].sum() / pay["合計"].sum()), "share_rain": float(pay["大雨"].sum() / pay["合計"].sum()),
           "total_real_oku": float(pay["合計"].sum()), "top2_share": float(pay["合計"].nlargest(2).sum() / pay["合計"].sum())}
pay.join(jma[["amdhour50mm", "amdday200mm"]], how="left").to_csv(OUT / "C_payouts_vs_rain.csv")

# ---- H4：取り込みの遅れによるずれ exp(gL)-1
rev["filing"] = pd.to_datetime(rev["filing_date"])
rev["data_end"] = pd.to_datetime((rev["data_end_fy"] + 1).astype(str) + "-03-31")
rev["gap_yr"] = (rev["filing"] - rev["data_end"]).dt.days / 365.25
g = t50["b"]
L_main = rev["gap_yr"].mean() + 1.0 + 2.5   # 届出まで + 適用まで約1年（推測）+ 保険期間5年の半分
lags = {"main(gap+1+2.5)": L_main, "short(gap+1+0.5)": rev["gap_yr"].mean() + 1.5, "long_window(+5: 10年平均の真ん中)": L_main + 5.0,
        "old_term(gap+1+5)": rev["gap_yr"].mean() + 6.0}
h4 = {k: {"L": v, "gap_pct": 100 * (math.exp(g * v) - 1), "gap_pct_hi": 100 * (math.exp((g + 1.96 * t50["se"]) * v) - 1)} for k, v in lags.items()}
M["H4"] = {"g_pct": t50["pct_per_yr"], "gap_yr_mean": float(rev["gap_yr"].mean()), "gap_yr_each": rev["gap_yr"].round(2).tolist(),
           "lags": h4, "mean_rev_pct": float(rev["avg_change_pct"].mean()),
           "support": bool(h4["main(gap+1+2.5)"]["gap_pct"] < rev["avg_change_pct"].mean())}
# レビュー後の追加（1）：契約期間を改定の時期で分けた遅れ（2014・2018・2019年は最長10年、2021・2023年は最長5年）
rev["half_term"] = np.where(rev["filing"].dt.year <= 2019, 5.0, 2.5)
L_w = float((rev["gap_yr"] + 1.0 + rev["half_term"]).mean())
# レビュー後の追加（2）：2021年の改定の基データの末年度を1年前（2019年度）にずらす
gap_alt = rev["gap_yr"].copy(); gap_alt[rev["filing_date"] == "2021-05-21"] += 1.0
L_alt = float(gap_alt.mean() + 1.0 + 2.5); L_alt_w = float((gap_alt + 1.0 + rev["half_term"]).mean())
M["H4_review"] = {"L_term_by_period": L_w, "gap_pct_term_by_period": 100 * (math.exp(g * L_w) - 1),
                  "L_2021_shift": L_alt, "gap_pct_2021_shift": 100 * (math.exp(g * L_alt) - 1),
                  "L_both": L_alt_w, "gap_pct_both": 100 * (math.exp(g * L_alt_w) - 1)}
# 頑健性：しきい値ごとの g でのずれ
M["H4_by_series"] = {r["series"]: 100 * (math.exp(math.log(1 + r["pois_pct"] / 100) * L_main) - 1) for _, r in rob.iterrows()}

# ---- 問い直し：累計の上がり幅を「大雨」「修理費」「その他」に分ける（対数で）
dh = defl.loc[2022, "defl_house"] / defl.loc[2012, "defl_house"]
decomp = {}
for c in ("amdhour50mm", "amdday200mm", "amd3hour100mm"):
    hz = haz[(c, 10)]
    lt = math.log(cum)
    decomp[c] = {"total_log": lt, "hazard_share": math.log(hz) / lt, "repair_share": math.log(dh) / lt,
                 "other_share": 1 - (math.log(hz) + math.log(dh)) / lt, "hazard_ratio": hz, "repair_ratio": dh}
M["reask"] = {"defl_house_2012": float(defl.loc[2012, "defl_house"]), "defl_house_2022": float(defl.loc[2022, "defl_house"]),
              "repair_ratio": dh, "decomp": decomp}
# レビュー後の追加（3）：期間をそろえた比べ方（H2 と問い直し）
def variant(cum_v, hz, dh_v):
    lt = math.log(cum_v)
    return {"rate_pct": 100 * (cum_v - 1), "haz_pct": 100 * (hz - 1), "ratio": (cum_v - 1) / (hz - 1), "h2_support": bool((cum_v - 1) >= 2 * (hz - 1)),
            "repair_pct": 100 * (dh_v - 1), "hazard_share": math.log(hz) / lt, "repair_share": math.log(dh_v) / lt, "other_share": 1 - (math.log(hz) + math.log(dh_v)) / lt}
cum_ex14 = float(rev["mult"].iloc[1:].prod())
haz03 = win_mean("amdhour50mm", 2022, 10) / win_mean("amdhour50mm", 2003, 10)
dh03 = defl.loc[2022, "defl_house"] / defl.loc[2003, "defl_house"]
M["period_variants"] = {"base_2012_2022": variant(cum, haz[("amdhour50mm", 10)], dh),
                        "drop_2014": variant(cum_ex14, haz[("amdhour50mm", 10)], dh),
                        "start_2003": variant(cum, haz03, dh03),
                        "mean10_1994_2003": win_mean("amdhour50mm", 2003, 10), "defl_2003": float(defl.loc[2003, "defl_house"])}
# H3 の95%区間（フィッシャーの z 変換）
z = math.atanh(r_main); se = 1 / math.sqrt(len(dfp) - 3)
M["H3"]["ci95"] = [math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se)]
# 実際の保険料（保険金額あたり）と保険金（F272、2017〜2024年度）
rn = res_nat
M["residential"] = {"prem_per_1000_2017": float(rn.loc[2017, "prem_per_mil"]), "prem_per_1000_2022": float(rn.loc[2022, "prem_per_mil"]),
                    "prem_per_1000_2024": float(rn.loc[2024, "prem_per_mil"]),
                    "claim_per_1000_mean": float(rn["claim_per_mil"].mean()), "claim_per_1000_2017": float(rn.loc[2017, "claim_per_mil"]),
                    "claim_per_1000_2018": float(rn.loc[2018, "claim_per_mil"]), "claim_per_1000_2024": float(rn.loc[2024, "claim_per_mil"]),
                    "loss_ratio_mean": float((rn["claim_k"].sum() / rn["prem_k"].sum()))}
rev.to_csv(OUT / "D_revisions.csv", index=False)
(OUT / "main.json").write_text(json.dumps(M, ensure_ascii=False, indent=1, default=float) + "\n")
print(json.dumps({k: M[k] for k in ("H1", "H2", "H3", "H4", "reask", "residential")}, ensure_ascii=False, indent=1, default=float)[:6000])
print(rob[["series", "pois_pct", "pois_lo", "pois_hi", "ols_pct", "ratio10", "pois_ex0411_pct"]].round(2))
print(M["H2_robust"]); print(M["H4_by_series"]); print(json.dumps({k: M[k] for k in ("H4_review", "period_variants")}, ensure_ascii=False, indent=1)); print(M["H3"]["ci95"])
