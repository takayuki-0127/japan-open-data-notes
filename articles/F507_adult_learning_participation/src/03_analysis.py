"""年齢をそろえた行動者率、変化の分解、種類別・男女別、仮説の判定、頑健性。"""
import json
import pandas as pd
from common import DATA, RES, TS_AGES, GROUPS, AGE_WIDTH, YEARS, KIND_JA

RES.mkdir(exist_ok=True)
ts = pd.read_csv(DATA / "ts_rates.csv")
pw = pd.read_csv(DATA / "pop_weights.csv")
pu = pd.read_csv(DATA / "purpose_2016_2021.csv")
KINDS = ["total", "foreign", "english", "business_total", "computing", "business", "home", "humanities", "arts"]


def rate(sex, age, kind, year):
    v = ts[(ts.sex == sex) & (ts.age == age) & (ts.kind == kind) & (ts.year == year)].rate
    return float(v.iloc[0]) if len(v) == 1 and pd.notna(v.iloc[0]) else None


def weights(kind_w, sex="総数"):
    if kind_w in ("w2021", "w2016"):
        y = int(kind_w[1:])
        g = pw[(pw.year == y) & (pw.sex == sex)].set_index("ts_age").pop_1000
        return {a: float(g[a]) for a in TS_AGES}
    if kind_w == "width":
        return dict(AGE_WIDTH)
    raise ValueError(kind_w)


def std(group, year, kind="total", sex="総数", w="w2021"):
    W = weights(w, sex)
    ages = GROUPS[group]
    vals = [rate(sex, a, kind, year) for a in ages]
    if any(v is None for v in vals):
        return None
    return sum(v * W[a] for v, a in zip(vals, ages)) / sum(W[a] for a in ages)


r1 = lambda x: None if x is None else round(x, 1)
def dif(a, b):
    return None if a is None or b is None else b - a
r2 = lambda x: None if x is None else round(x, 2)

# ---- 年ごとの表（年齢をそろえた率）----
rows = []
for sex in ("総数", "男", "女"):
    for g in ("25_64", "30_64", "65plus", "25plus"):
        for k in KINDS:
            for y in YEARS:
                v = std(g, y, k, sex)
                rows.append({"sex": sex, "group": g, "kind": k, "year": y, "std_rate_w2021": r2(v)})
by = pd.DataFrame(rows)
by.to_csv(RES / "by_year.csv", index=False)

m = {"note": "std_* は2021年の推定人口の年齢構成で重みをつけた行動者率（%）。差はポイント。"}
S = lambda g, y, k="total", sex="総数", w="w2021": std(g, y, k, sex, w)
m["std_25_64"] = {y: r1(S("25_64", y)) for y in YEARS}
m["std_65plus"] = {y: r1(S("65plus", y)) for y in YEARS}
m["std_25plus"] = {y: r1(S("25plus", y)) for y in YEARS}
m["age_rates_total"] = {a: {y: rate("総数", a, "total", y) for y in YEARS} for a in TS_AGES}
m["all10plus_total"] = {y: rate("総数", "総数", "total", y) for y in YEARS}
m["crude15plus_total"] = {y: rate("総数", "(再掲)15歳以上", "total", y) for y in YEARS}
m["crude65plus_total"] = {y: rate("総数", "(再掲)65歳以上", "total", y) for y in YEARS}

# 15歳以上の年齢をそろえた値（15〜19・20〜24歳も入れる）。2021年の推定人口の重み
w15 = pu[(pu.year == 2021) & (pu.sex == "総数") & (pu.purpose == "総数") & (pu.kind == "total") & pu.age.isin(["15～19歳", "20～24歳"])].set_index("age").pop_1000
W21 = weights("w2021")
def std15(y):
    ages = ["15～19歳", "20～24歳"] + TS_AGES
    W = {**{a: float(w15[a]) for a in ["15～19歳", "20～24歳"]}, **W21}
    v = [rate("総数", a, "total", y) for a in ages]
    return sum(x * W[a] for x, a in zip(v, ages)) / sum(W.values())
m["std15plus_total"] = {y: r1(std15(y)) for y in YEARS}
m["pop_share_65plus_of_15plus_2016_2021"] = {}
for y in (2016, 2021):
    q = pu[(pu.year == y) & (pu.sex == "総数") & (pu.purpose == "総数") & (pu.kind == "total")].set_index("age").pop_1000
    m["pop_share_65plus_of_15plus_2016_2021"][y] = round(float(q["(再掲)65歳以上"] / q["(再掲)15歳以上"] * 100), 1)

# ---- そのままの25歳以上（2016・2021年は各年の推定人口で重み）と分解 ----
def crude25(y):
    W = weights(f"w{y}")
    return sum(rate("総数", a, "total", y) * W[a] for a in TS_AGES) / sum(W.values())
c16, c21 = crude25(2016), crude25(2021)
W16, W21 = weights("w2016"), weights("w2021")
s16 = {a: W16[a] / sum(W16.values()) for a in TS_AGES}; s21 = {a: W21[a] / sum(W21.values()) for a in TS_AGES}
rate_eff = sum((rate("総数", a, "total", 2021) - rate("総数", a, "total", 2016)) * (s16[a] + s21[a]) / 2 for a in TS_AGES)
comp_eff = sum((s21[a] - s16[a]) * (rate("総数", a, "total", 2021) + rate("総数", a, "total", 2016)) / 2 for a in TS_AGES)
m["decomp_25plus_2016_2021"] = {"crude_2016": r2(c16), "crude_2021": r2(c21), "crude_diff": r2(c21 - c16),
                                 "rate_effect": r2(rate_eff), "composition_effect": r2(comp_eff),
                                 "std_diff_w2021": r2(S("25plus", 2021) - S("25plus", 2016)),
                                 "share_65plus_of_25plus": {2016: round((s16["65～69歳"] + s16["70歳以上"]) * 100, 1),
                                                             2021: round((s21["65～69歳"] + s21["70歳以上"]) * 100, 1)}}

# ---- 種類別（25〜64歳、年齢をそろえた値）----
m["kind_25_64"] = {k: {y: r1(S("25_64", y, k)) for y in YEARS} for k in KINDS}
m["kind_change_25_64"] = {k: {"1996_2021": r1(dif(S("25_64", 1996, k), S("25_64", 2021, k))),
                              "2001_2021": r1(dif(S("25_64", 2001, k), S("25_64", 2021, k))),
                              "2016_2021": r1(dif(S("25_64", 2016, k), S("25_64", 2021, k)))} for k in KINDS}
m["kind_change_65plus"] = {k: {"2001_2021": r1(dif(S("65plus", 2001, k), S("65plus", 2021, k))),
                               "2016_2021": r1(dif(S("65plus", 2016, k), S("65plus", 2021, k)))} for k in KINDS}

# ---- 男女別 ----
m["sex_25_64"] = {sx: {y: r1(std("25_64", y, "total", sx)) for y in YEARS} for sx in ("男", "女")}
m["sex_65plus"] = {sx: {y: r1(std("65plus", y, "total", sx)) for y in YEARS} for sx in ("男", "女")}

# ---- 仮説 ----
d1 = S("25_64", 2021) - S("25_64", 1996)
d_crude15 = rate("総数", "(再掲)15歳以上", "total", 2021) - rate("総数", "(再掲)15歳以上", "total", 1996)
d_std15 = std15(2021) - std15(1996)
d3b = S("25_64", 2021, "business_total") - S("25_64", 2016, "business_total")
d3f = S("25_64", 2021, "foreign") - S("25_64", 2016, "foreign")
d4o = S("65plus", 2021) - S("65plus", 1996)
H = {
    "H1": {"text": "25〜64歳（年齢をそろえた値）は1996→2021年に5ポイント以上上がった", "value": r1(d1),
           "verdict": "支持" if d1 >= 5 else "外れ"},
    "H2": {"text": "そのままの値は年齢をそろえた値より上がり方が小さい",
           "value": {"15plus_1996_2021_crude": r1(d_crude15), "15plus_1996_2021_std": r1(d_std15),
                     "25plus_2016_2021_crude": r2(c21 - c16), "25plus_2016_2021_std": r2(S("25plus", 2021) - S("25plus", 2016))},
           "verdict": "支持" if (d_crude15 < d_std15 and (c21 - c16) < S("25plus", 2021) - S("25plus", 2016)) else
                      ("外れ" if (d_crude15 >= d_std15 and (c21 - c16) >= S("25plus", 2021) - S("25plus", 2016)) else "判定できず")},
    "H3": {"text": "25〜64歳の2016→2021年の上昇は、商業実務・ビジネス関係（パソコンを含む）が外国語より大きい",
           "value": {"business_total": r1(d3b), "foreign": r1(d3f)}, "verdict": "支持" if d3b > d3f else "外れ"},
    "H4": {"text": "1996→2021年の上昇は65歳以上の方が25〜64歳より大きい", "value": {"65plus": r1(d4o), "25_64": r1(d1)},
           "verdict": "支持" if d4o > d1 else "外れ"},
}
m["hypotheses"] = H

# ---- 頑健性 ----
rob = []
def add(name, a, b, note=""):
    rob.append({"check": name, "from": r1(a), "to": r1(b), "diff": r1(b - a), "note": note})
add("本線：25〜64歳、2021年の人口の重み、1996→2021年", S("25_64", 1996), S("25_64", 2021))
add("重み：2016年の人口", S("25_64", 1996, w="w2016"), S("25_64", 2021, w="w2016"))
add("重み：年齢区分の幅だけ", S("25_64", 1996, w="width"), S("25_64", 2021, w="width"))
add("期間：2001→2021年", S("25_64", 2001), S("25_64", 2021))
add("期間：2016→2021年", S("25_64", 2016), S("25_64", 2021))
add("参考：1986→2021年（調べ方の違いの可能性あり）", S("25_64", 1986), S("25_64", 2021))
add("年齢：30〜64歳", S("30_64", 1996), S("30_64", 2021))
add("男だけ", std("25_64", 1996, "total", "男"), std("25_64", 2021, "total", "男"))
add("女だけ", std("25_64", 1996, "total", "女"), std("25_64", 2021, "total", "女"))
add("65歳以上（本線の重み）", S("65plus", 1996), S("65plus", 2021))
up_all = all(rate("総数", a, "total", 2021) > rate("総数", a, "total", 1996) for a in TS_AGES)
pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
m["robustness"] = rob
m["all_ts_ages_up_1996_2021"] = up_all
m["ages_up_2016_2021"] = {a: r1(rate("総数", a, "total", 2021) - rate("総数", a, "total", 2016)) for a in TS_AGES}
m["ages_up_1996_2021"] = {a: r1(rate("総数", a, "total", 2021) - rate("総数", a, "total", 1996)) for a in TS_AGES}
# 2011年と2006年の谷（25〜64歳）
m["std_25_64_min_year_after_1996"] = int(min((y for y in YEARS if y >= 1996), key=lambda y: S("25_64", y)))
m["kind_ja"] = KIND_JA
json.dump(m, open(RES / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: m[k] for k in ["std_25_64", "std_65plus", "std15plus_total", "crude15plus_total", "decomp_25plus_2016_2021", "hypotheses", "kind_change_25_64", "sex_25_64", "ages_up_2016_2021"]}, ensure_ascii=False, indent=0))
print(pd.DataFrame(rob).to_string())
