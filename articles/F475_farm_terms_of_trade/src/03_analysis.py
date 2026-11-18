"""交易条件・寄与の分解・米を除いた指数・頑健性。数字はすべて results に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
idx = pd.read_csv(D / "index_long.csv")
w = pd.read_csv(D / "weights_class.csv")
W = {(g, c): v for g, c, v in w[["group", "class", "weight"]].itertuples(index=False)}
PT, IT = "農産物総合", "農業生産資材総合"


def wide(kind, group):
    x = idx[(idx.kind == kind) & (idx.group == group)]
    key = ["year"] if kind != "month" else ["year", "month"]
    return x.pivot_table(index=key, columns="class", values="index", aggfunc="first").sort_index()


def r1(v, n=1):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), n)


# ---- 年（暦年 1995〜2025） ----
P = wide("calendar_year", "products"); I = wide("calendar_year", "inputs")
wr, wv = W[("products", "米")], W[("products", "野菜")]
A = pd.DataFrame(index=P.index)
A["products"] = P[PT]; A["inputs"] = I[IT]
A["tot"] = A.products / A.inputs * 100
A["products_ex_rice"] = (P[PT] * 10000 - P["米"] * wr) / (10000 - wr)
A["tot_ex_rice"] = A.products_ex_rice / A.inputs * 100
A["products_ex_rice_veg"] = (P[PT] * 10000 - P["米"] * wr - P["野菜"] * wv) / (10000 - wr - wv)
A["tot_ex_rice_veg"] = A.products_ex_rice_veg / A.inputs * 100
A["rice"] = P["米"]; A["livestock"] = P["畜産物"]; A["feed"] = I["飼料"]
A["tot_livestock_feed"] = P["畜産物"] / I["飼料"] * 100
trio = ["肥料", "農業薬剤", "光熱動力"]
wt = sum(W[("inputs", c)] for c in trio)
A["rice_inputs"] = sum(I[c] * W[("inputs", c)] for c in trio) / wt
A["tot_rice_inputs"] = P["米"] / A.rice_inputs * 100
for c in ["肥料", "飼料", "光熱動力", "農機具"]:
    A[f"in_{c}"] = I[c]
A = A.reset_index()
A.round(2).to_csv(R / "annual_tot.csv", index=False)

# 類の合成と公表値の差（ウエイトで足し戻せるか）
pc = [c for (g, c) in W if g == "products" and c != PT]
ic = [c for (g, c) in W if g == "inputs" and c != IT]
chk = pd.DataFrame({"year": P.index,
                    "products_published": P[PT].values,
                    "products_from_classes": (sum(P[c] * W[("products", c)] for c in pc) / 10000).values,
                    "inputs_published": I[IT].values,
                    "inputs_from_classes": (sum(I[c] * W[("inputs", c)] for c in ic) / 10000).values})
chk = chk[chk.year >= 2020]

# ---- 寄与（2020→各年、ポイント） ----
rows = []
for y in range(2021, 2026):
    for g, X, tot, cl in [("inputs", I, IT, ic), ("products", P, PT, pc)]:
        for c in cl:
            rows.append((g, y, c, W[(g, c)] * (X.loc[y, c] - 100) / 10000))
        rows.append((g, y, "（公表の総合−100）", X.loc[y, tot] - 100))
contrib = pd.DataFrame(rows, columns=["group", "year", "class", "points"])
contrib.round(3).to_csv(R / "contributions_2020base.csv", index=False)

def share(g, y, cls):
    c = contrib[(contrib.group == g) & (contrib.year == y)]
    tot = c[c["class"].isin(ic if g == "inputs" else pc)].points.sum()
    return c[c["class"].isin(cls)].points.sum() / tot, tot

sh23, tot23 = share("inputs", 2023, ["肥料", "飼料", "光熱動力"])
sh25, tot25 = share("inputs", 2025, ["肥料", "飼料", "光熱動力"])
rice25 = contrib[(contrib.group == "products") & (contrib.year == 2025) & (contrib["class"] == "米")].points.iloc[0]
ptot25 = contrib[(contrib.group == "products") & (contrib.year == 2025) & contrib["class"].isin(pc)].points.sum()

# ---- 月（2015〜2025） ----
Pm = wide("month", "products"); Im = wide("month", "inputs")
M = pd.DataFrame({"products": Pm[PT], "inputs": Im[IT], "rice": Pm["米"]}).dropna()
M["tot"] = M.products / M.inputs * 100
M["products_ex_rice"] = (Pm[PT] * 10000 - Pm["米"] * wr) / (10000 - wr)
M["tot_ex_rice"] = M.products_ex_rice / M.inputs * 100
M = M.reset_index()
M["tot_ma12"] = M.tot.rolling(12).mean()
M["tot_ex_rice_ma12"] = M.tot_ex_rice.rolling(12).mean()
Mr = M[M.year >= 2015].copy()
Mr.round(2).to_csv(R / "monthly_tot_2015_2025.csv", index=False)

# 月の底（2021年以降）
m21 = Mr[Mr.year >= 2021]
lo = m21.loc[m21.tot.idxmin()]
lo12 = m21.loc[m21.tot_ma12.idxmin()]
above = Mr[(Mr.year >= 2023) & (Mr.tot >= 100)]
first_above = above.iloc[0] if len(above) else None
streak = Mr[Mr.year >= 2024].copy()
# 2024年以降で100以上が続き始めた月
run_start = None
for i in range(len(streak)):
    if (streak.tot.iloc[i:] >= 100).all():
        run_start = streak.iloc[i]; break

# ---- 長い期間：月の値から暦年平均（1958〜2025） ----
Pm_all = Pm[PT].dropna(); Im_all = Im[IT].dropna()
L = pd.DataFrame({"products": Pm_all, "inputs": Im_all}).dropna().reset_index()
cnt = L.groupby("year").month.count()
full = cnt[cnt == 12].index
L = L[L.year.isin(full)].groupby("year")[["products", "inputs"]].mean()
L["tot"] = L.products / L.inputs * 100
L = L.reset_index()
L.round(2).to_csv(R / "long_calendar_from_monthly.csv", index=False)
# 公表の暦年値との照合（1995年以降）
cmpL = L.merge(A[["year", "tot"]], on="year", suffixes=("_from_month", "_published"))
maxdiff = float((cmpL.tot_from_month - cmpL.tot_published).abs().max())
maxdiff_year = int(cmpL.loc[(cmpL.tot_from_month - cmpL.tot_published).abs().idxmax(), "year"])
c05 = cmpL[cmpL.year >= 2005]
maxdiff05 = float((c05.tot_from_month - c05.tot_published).abs().max())
dec = []
for a in range(1960, 2030, 10):
    s = L[(L.year >= a) & (L.year <= a + 9)]
    if len(s):
        dec.append({"decade": f"{a}s", "years": int(len(s)), "first": int(s.year.min()), "last": int(s.year.max()),
                    "tot_mean": float(s.tot.mean()), "products_mean": float(s.products.mean()), "inputs_mean": float(s.inputs.mean())})
dec = pd.DataFrame(dec); dec.round(2).to_csv(R / "long_decades.csv", index=False)
slope = np.polyfit(L.year, np.log(L.tot), 1)[0]
slope_9519 = np.polyfit(A[(A.year <= 2019)].year, np.log(A[(A.year <= 2019)].tot), 1)[0]

a = A.set_index("year")
t2223 = a.loc[[2022, 2023], "tot"].mean()
H = {
    "H1": {"rule": "2022〜2023年の交易条件の平均が95以下なら支持", "value": r1(t2223, 2),
           "min_year": int(a.loc[2021:2025, "tot"].idxmin()), "min_value": r1(a.loc[2021:2025, "tot"].min(), 2),
           "judge": "支持" if t2223 <= 95 else "外れ"},
    "H2": {"rule": "資材総合の2020→2023年の上昇のうち肥料・飼料・光熱動力の寄与が70%以上なら支持",
           "share": r1(sh23 * 100, 1), "rise_points": r1(tot23, 2), "judge": "支持" if sh23 >= 0.7 else "外れ"},
    "H3": {"rule": "2025年の交易条件が100以上、米を除くと100未満なら支持",
           "tot_2025": r1(a.loc[2025, "tot"], 2), "tot_ex_rice_2025": r1(a.loc[2025, "tot_ex_rice"], 2),
           "judge": "支持" if (a.loc[2025, "tot"] >= 100 and a.loc[2025, "tot_ex_rice"] < 100) else "外れ"},
    "H4": {"rule": "畜産物÷飼料の2022〜2025年平均が全体の交易条件より低ければ支持",
           "livestock_feed_2225": r1(a.loc[2022:2025, "tot_livestock_feed"].mean(), 2),
           "tot_2225": r1(a.loc[2022:2025, "tot"].mean(), 2),
           "judge": "支持" if a.loc[2022:2025, "tot_livestock_feed"].mean() < a.loc[2022:2025, "tot"].mean() else "外れ"},
}

# ---- 頑健性 ----
rob = []
rob.append(("月の値の底（2021年以降）", f"{int(lo.year)}年{int(lo.month)}月", r1(lo.tot, 2)))
rob.append(("12か月移動平均の底（2021年以降）", f"{int(lo12.year)}年{int(lo12.month)}月", r1(lo12.tot_ma12, 2)))
base = A[(A.year >= 2015) & (A.year <= 2019)]
pb, ib = base.products.mean(), base.inputs.mean()
tb = lambda y: (a.loc[y, "products"] / pb) / (a.loc[y, "inputs"] / ib) * 100
rob.append(("基準を2015〜19年平均にした交易条件 2022〜23年平均", "2015〜19年=100", r1((tb(2022) + tb(2023)) / 2, 2)))
rob.append(("基準を2015〜19年平均にした交易条件 2025年", "2015〜19年=100", r1(tb(2025), 2)))
rob.append(("米と野菜を除いた交易条件 2025年", "2020年=100", r1(a.loc[2025, "tot_ex_rice_veg"], 2)))
rob.append(("米と野菜を除いた交易条件 2022〜23年平均", "2020年=100", r1(a.loc[[2022, 2023], "tot_ex_rice_veg"].mean(), 2)))
rob.append(("長期（月から作った暦年 %d〜2025年）の交易条件の傾き" % int(L.year.min()), "年あたり%", r1(slope * 100, 2)))
rob.append(("1995〜2019年（公表の暦年）の交易条件の傾き", "年あたり%", r1(slope_9519 * 100, 2)))
rob.append(("月から作った暦年平均と公表の暦年値の差の最大（1995〜2025年）", "交易条件のポイント", r1(maxdiff, 2)))
robd = pd.DataFrame(rob, columns=["check", "unit_or_when", "value"])
robd.to_csv(R / "robustness.csv", index=False)

main = {
    "years": [int(A.year.min()), int(A.year.max())],
    "annual": {int(y): {k: r1(a.loc[y, k], 2) for k in ["products", "inputs", "tot", "tot_ex_rice", "tot_ex_rice_veg",
                                                           "tot_livestock_feed", "tot_rice_inputs", "rice", "livestock", "feed",
                                                           "in_肥料", "in_飼料", "in_光熱動力", "in_農機具", "products_ex_rice"]}
               for y in [1995, 2000, 2005, 2010, 2015, 2019, 2020, 2021, 2022, 2023, 2024, 2025]},
    "hypotheses": H,
    "inputs_rise_2020_2023": {"total_points": r1(tot23, 2), "share_fert_feed_energy_pct": r1(sh23 * 100, 1),
                              "by_class": {c: r1(contrib[(contrib.group == "inputs") & (contrib.year == 2023) & (contrib["class"] == c)].points.iloc[0], 2) for c in ic}},
    "inputs_rise_2020_2025": {"total_points": r1(tot25, 2), "share_fert_feed_energy_pct": r1(sh25 * 100, 1),
                              "by_class": {c: r1(contrib[(contrib.group == "inputs") & (contrib.year == 2025) & (contrib["class"] == c)].points.iloc[0], 2) for c in ic}},
    "products_rise_2020_2025": {"total_points": r1(ptot25, 2), "rice_points": r1(rice25, 2), "rice_share_pct": r1(rice25 / ptot25 * 100, 1),
                                "by_class": {c: r1(contrib[(contrib.group == "products") & (contrib.year == 2025) & (contrib["class"] == c)].points.iloc[0], 2) for c in pc}},
    "class_sum_check_max_abs_diff": {"products": r1((chk.products_published - chk.products_from_classes).abs().max(), 3),
                                     "inputs": r1((chk.inputs_published - chk.inputs_from_classes).abs().max(), 3)},
    "monthly": {"min_since2021": {"ym": f"{int(lo.year)}-{int(lo.month):02d}", "tot": r1(lo.tot, 2)},
                "first_month_ge100_since2023": None if first_above is None else f"{int(first_above.year)}-{int(first_above.month):02d}",
                "run_ge100_start": None if run_start is None else f"{int(run_start.year)}-{int(run_start.month):02d}",
                "tot_2025_12": r1(Mr[(Mr.year == 2025) & (Mr.month == 12)].tot.iloc[0], 2),
                "tot_ex_rice_2025_12": r1(Mr[(Mr.year == 2025) & (Mr.month == 12)].tot_ex_rice.iloc[0], 2),
                "months_ge100_2024_2025": int((Mr[Mr.year >= 2024].tot >= 100).sum()),
                "months_ex_rice_ge100_2024_2025": int((Mr[Mr.year >= 2024].tot_ex_rice >= 100).sum())},
    "long": {"first_year": int(L.year.min()), "slope_pct_per_year": r1(slope * 100, 3),
             "slope_1995_2019_pct_per_year": r1(slope_9519 * 100, 3), "max_diff_vs_published": r1(maxdiff, 2), "max_diff_year": maxdiff_year, "max_diff_since2005": r1(maxdiff05, 2),
             "decades": {d: r1(v, 1) for d, v in zip(dec.decade, dec.tot_mean)}},
    "weights": {"rice": wr, "vegetables": wv, "livestock": W[("products", "畜産物")], "feed": W[("inputs", "飼料")],
                "fert": W[("inputs", "肥料")], "energy": W[("inputs", "光熱動力")]},
    "robustness": {r.check: r.value for r in robd.itertuples()},
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=False)
print(json.dumps(H, ensure_ascii=False, indent=1))
print(robd.to_string()); print(chk.round(2).to_string())
print(A[["year", "products", "inputs", "tot", "tot_ex_rice", "tot_livestock_feed", "tot_rice_inputs"]].round(1).tail(12).to_string())
