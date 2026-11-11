"""03 分析：年齢区分ごとの改善率、コロナ期の上振れ、平均寿命の年齢分解、頑健性。"""
import json
import numpy as np
import pandas as pd
from common import DATA, RAW, RES, SEXES, GLABEL, GSTART, arriaga, group_of

RES.mkdir(exist_ok=True)
g = pd.read_csv(DATA / "group_mx.csv")
s1 = pd.read_csv(DATA / "single_mx.csv")
lm = g.pivot_table(index=["sex", "g"], columns="year", values="mx").apply(np.log)
NG = len(GLABEL)


def rate(t0, t1):
    """t0→t1 の年あたり改善率（%）＝ −Δln m /年数 ×100"""
    return -(lm[t1] - lm[t0]) / (t1 - t0) * 100


def ols_rate(y0, y1, drop=()):
    yrs = [y for y in range(y0, y1 + 1) if y not in drop]
    X = np.array(yrs, float)
    out = {}
    for k, row in lm[yrs].iterrows():
        b = np.polyfit(X, row.values, 1)[0]
        out[k] = -b * 100
    s = pd.Series(out); s.index = s.index.set_names(["sex", "g"]); return s


tab = pd.DataFrame({"A_2000_09": rate(1999, 2009), "B_2010_19": rate(2009, 2019), "C_2020_24": rate(2019, 2024),
                    "A5_2005_09": rate(2004, 2009), "B5_2015_19": rate(2014, 2019),
                    "A_ols": ols_rate(2000, 2009), "B_ols_no2011": ols_rate(2010, 2019, drop=(2011,)),
                    "pre_1990_99": rate(1989, 1999)}).reset_index()
tab["label"] = tab.g.map(lambda i: GLABEL[i]); tab["age0"] = tab.g.map(lambda i: GSTART[i])
tab["slow_AB"] = tab.A_2000_09 - tab.B_2010_19
tab["slow_A5B5"] = tab.A5_2005_09 - tab.B5_2015_19
tab["slow_ols"] = tab.A_ols - tab.B_ols_no2011
tab.to_csv(RES / "A_rates_by_age.csv", index=False)


def judge(t, ca, cb, cs):
    res = {}
    for s in SEXES:
        u = t[t.sex == s]
        o40 = u[u.age0 >= 40]
        n_slow = int((o40[cb] < o40[ca]).sum())
        top = u.loc[u[cs].idxmax()]
        old = u[u.age0 >= 90]
        res[s] = {"H1_n_slow_40plus": n_slow, "H1_n": int(len(o40)),
                  "H2_top_slow_group": top.label, "H2_top_slow_pt": round(float(top[cs]), 3),
                  "H4_B_90_94": round(float(u[u.age0 == 90][cb].iloc[0]), 3),
                  "H4_B_95_99": round(float(u[u.age0 == 95][cb].iloc[0]), 3)}
    v = {"H1": all(res[s]["H1_n_slow_40plus"] >= 7 for s in SEXES),
         "H2": all(int(res[s]["H2_top_slow_group"].split("〜")[0].replace("以上", "")) >= 65 for s in SEXES),
         "H4": all(res[s]["H4_B_90_94"] < 1 and res[s]["H4_B_95_99"] < 1 for s in SEXES)}
    return res, v


main = {}
main["base"], main["verdict_base"] = judge(tab, "A_2000_09", "B_2010_19", "slow_AB")
main["R1_5yr"], main["verdict_R1"] = judge(tab, "A5_2005_09", "B5_2015_19", "slow_A5B5")
main["R2_ols_no2011"], main["verdict_R2"] = judge(tab, "A_ols", "B_ols_no2011", "slow_ols")

# H3：2010〜2019 の対数直線を延ばした予測と実際の比
def excess(y0, y1):
    rows = []
    yrs = list(range(y0, y1 + 1)); X = np.array(yrs, float)
    for k, row in lm.iterrows():
        b, a = np.polyfit(X, row[yrs].values, 1)
        for y in range(2020, 2025):
            pred = a + b * y
            rows.append({"sex": k[0], "g": k[1], "year": y, "ratio": float(np.exp(row[y] - pred) - 1) * 100})
    e = pd.DataFrame(rows); e["label"] = e.g.map(lambda i: GLABEL[i]); e["age0"] = e.g.map(lambda i: GSTART[i])
    return e


def h3(e):
    out = {}
    for s in SEXES:
        u = e[(e.sex == s) & (e.year >= 2022) & (e.age0 >= 75)].groupby("label", sort=False).ratio.mean()
        out[s] = {k: round(v, 2) for k, v in u.items()}
    ok = all(min(out[s].values()) >= 5 for s in SEXES)
    return out, ok


ex = excess(2010, 2019); ex.to_csv(RES / "B_excess_vs_trend.csv", index=False)
main["H3_base"], main["verdict_base"]["H3"] = h3(ex)
ex2 = excess(2005, 2019); ex2.to_csv(RES / "B2_excess_vs_trend_2005.csv", index=False)
main["H3_R3"], main["verdict_R3_H3"] = h3(ex2)
# 若い年齢も含めた上振れの全体像（2022〜24平均）
main["excess_2022_24_all"] = {s: {r.label: round(r.ratio, 2) for r in ex[(ex.sex == s) & (ex.year >= 2022)].groupby(["g", "label"], as_index=False).ratio.mean().itertuples()} for s in SEXES}
main["excess_2020_21_all"] = {s: {r.label: round(r.ratio, 2) for r in ex[(ex.sex == s) & (ex.year <= 2021)].groupby(["g", "label"], as_index=False).ratio.mean().itertuples()} for s in SEXES}

# 10年窓の改善率の地図
roll = []
for t1 in range(1957, 2025):
    r = rate(t1 - 10, t1)
    for (s, gi), v in r.items():
        roll.append({"sex": s, "g": gi, "label": GLABEL[gi], "end": t1, "rate": float(v)})
pd.DataFrame(roll).to_csv(RES / "C_rolling10.csv", index=False)

# Arriaga：平均寿命の変化を5歳階級に
arr = []
piv = s1.pivot_table(index=["sex", "year"], columns="age", values="mx")
for s in SEXES:
    for (y0, y1) in [(2000, 2010), (2010, 2019), (2019, 2024), (1990, 2000)]:
        c, e1, e2 = arriaga(piv.loc[(s, y0)].values, piv.loc[(s, y1)].values)
        for gi in range(len(GLABEL)):
            ages = [a for a in range(len(c)) if group_of(a) == gi]
            arr.append({"sex": s, "period": f"{y0}→{y1}", "g": gi, "label": GLABEL[gi], "contrib": float(c[ages].sum()),
                        "e0_from": e1, "e0_to": e2})
arr = pd.DataFrame(arr); arr.to_csv(RES / "D_arriaga.csv", index=False)
main["e0"] = {s: {p: {"from": round(v.e0_from.iloc[0], 3), "to": round(v.e0_to.iloc[0], 3), "diff": round(v.contrib.sum(), 3),
                       "share_65plus": round(v[v.g >= group_of(65)].contrib.sum() / v.contrib.sum(), 3),
                       "share_85plus": round(v[v.g >= group_of(85)].contrib.sum() / v.contrib.sum(), 3)}
                   for p, v in arr[arr.sex == s].groupby("period")} for s in SEXES}

# R4：簡易生命表（2014→2019）と JMD の5年改善率の照合
mh = pd.read_csv(RAW / "mhlw_qx_from_F268.csv")
mh = mh[mh.age <= 99].copy(); mh["m"] = -np.log(1 - mh.qx.clip(upper=0.999999))
ex19 = s1[s1.year == 2019][["sex", "age", "exposure"]]
mh = mh.merge(ex19, on=["sex", "age"]); mh["g"] = mh.age.map(group_of)
mg = mh.groupby(["sex", "year", "g"]).apply(lambda u: np.average(u.m, weights=u.exposure), include_groups=False).unstack("year")
rm = (-np.log(mg[2019] / mg[2014]) / 5 * 100).rename("mhlw")
cmp_ = tab.set_index(["sex", "g"])[["B5_2015_19"]].join(rm, how="inner")
cmp_ = cmp_[cmp_.index.get_level_values("g") >= 1]
cmp_.reset_index().to_csv(RES / "E_r4_mhlw_vs_jmd.csv", index=False)
main["R4"] = {"corr": round(float(cmp_.corr().iloc[0, 1]), 3), "mean_abs_diff_pt": round(float((cmp_.B5_2015_19 - cmp_.mhlw).abs().mean()), 3),
              "rows": int(len(cmp_))}
(RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1))
print(json.dumps({k: main[k] for k in ["base", "verdict_base", "verdict_R1", "verdict_R2", "verdict_R3_H3", "H3_base", "R4"]}, ensure_ascii=False, indent=1))
