"""03_analysis.py : 年齢別の賃金の曲線の形（50〜54歳÷20〜24歳など）の推移と分解（オフライン）。"""
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
g = pd.read_csv(ROOT / "data" / "general.csv")
AGES = ["〜19歳", "20〜24歳", "25〜29歳", "30〜34歳", "35〜39歳", "40〜44歳", "45〜49歳",
        "50〜54歳", "55〜59歳", "60〜64歳", "65〜69歳", "70歳〜"]
WORK = AGES[1:10]  # 20〜64歳
SIZES = ["企業規模計", "1000人以上", "100〜999人", "10〜99人"]
HARM = {"中学卒": "中学", "中学": "中学", "高校卒": "高校", "高校": "高校", "高専・短大卒": "高専短大専門",
        "高専・短大": "高専短大専門", "専門学校": "高専短大専門", "大学・大学院卒": "大学大学院",
        "大学": "大学大学院", "大学院": "大学大学院"}
g = g[g.age.isin(AGES + ["年齢計"])].copy()


def r(x, k=3):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


# 学歴をそろえる（2020年以降の大学と大学院、専門学校と高専・短大を労働者数で合わせる）
e = g[g.edu.isin(HARM)].copy()
e["eh"] = e.edu.map(HARM)
e["ww"] = e.wage * e.workers10
eh = e.groupby(["year", "sex", "eh", "age", "size"], as_index=False)[["ww", "workers10"]].sum(min_count=1)
eh["wage"] = eh.ww / eh.workers10
eh = eh.drop(columns="ww")
tot = g[g.edu == "学歴計"][["year", "sex", "age", "size", "wage", "workers10"]].assign(eh="学歴計")
H = pd.concat([tot, eh], ignore_index=True)
H.round(3).to_csv(RES / "wage_by_sex_edu_age_size.csv", index=False)


def curve(sex="男", eh_="学歴計", size="企業規模計"):
    s = H[(H.sex == sex) & (H.eh == eh_) & (H["size"] == size) & (H.age.isin(AGES))]
    p = s.pivot_table(index="year", columns="age", values="wage")
    return p[[a for a in AGES if a in p.columns]]


def ratio(sex="男", eh_="学歴計", size="企業規模計", num="50〜54歳", den="20〜24歳"):
    c = curve(sex, eh_, size)
    return c[num] / c[den]


main = {}
# ---- 曲線（20〜24歳=100）----
rows = []
for sex in ["男", "女", "男女計"]:
    c = curve(sex)
    for y in [2006, 2015, 2019, 2025]:
        for a in WORK:
            rows.append({"sex": sex, "year": y, "age": a, "wage": c.loc[y, a], "index_20_24": c.loc[y, a] / c.loc[y, "20〜24歳"] * 100})
cv = pd.DataFrame(rows)
cv.round(2).to_csv(RES / "curves_index.csv", index=False)
for sex in ["男", "女"]:
    c = curve(sex)
    idx = c[WORK].div(c["20〜24歳"], axis=0) * 100
    pk = idx.idxmax(axis=1)
    main[f"peak_{sex}"] = {int(y): {"age": pk.loc[y], "index": r(idx.loc[y].max(), 1)} for y in [2006, 2010, 2015, 2019, 2025]}

# ---- 指標の推移 ----
ts = pd.DataFrame({
    "male_50_54_over_20_24": ratio("男"), "female_50_54_over_20_24": ratio("女"),
    "male_55_59_over_25_29": ratio("男", num="55〜59歳", den="25〜29歳"),
    "male_univ": ratio("男", "大学大学院"), "male_high": ratio("男", "高校"),
    "male_1000": ratio("男", size="1000人以上"), "male_100_999": ratio("男", size="100〜999人"),
    "male_10_99": ratio("男", size="10〜99人"),
    "male_univ_1000": ratio("男", "大学大学院", "1000人以上"),
})
# 学歴構成を2006年に固定
def fixed_edu(sex="男", size="企業規模計", base=2006, ages=("20〜24歳", "50〜54歳")):
    out = {}
    for a in ages:
        d = H[(H.sex == sex) & (H["size"] == size) & (H.age == a) & (H.eh.isin(["中学", "高校", "高専短大専門", "大学大学院"]))]
        w = d[d.year == base].set_index("eh")["workers10"]
        w = w / w.sum()
        p = d.pivot_table(index="year", columns="eh", values="wage")[w.index]
        out[a] = (p * w).sum(axis=1)
    return out[ages[1]] / out[ages[0]]


ts["male_fixed_edu2006"] = fixed_edu()
ts.index.name = "year"
ts.round(4).to_csv(RES / "ratio_timeseries.csv")


def change(s, y0=2006, y1=2025):
    return {"y0": y0, "y1": y1, "v0": r(s.loc[y0]), "v1": r(s.loc[y1]), "pct": r((s.loc[y1] / s.loc[y0] - 1) * 100, 2)}


main["ratio_change"] = {k: change(ts[k]) for k in ts.columns}

# ---- 分解（男・学歴計・規模計）----
c = curve("男")
dec = {}
for y0, y1 in [(2006, 2025), (2006, 2019), (2019, 2025), (2010, 2025)]:
    g50 = np.log(c.loc[y1, "50〜54歳"] / c.loc[y0, "50〜54歳"])
    g20 = np.log(c.loc[y1, "20〜24歳"] / c.loc[y0, "20〜24歳"])
    dr = g50 - g20
    dec[f"{y0}_{y1}"] = {"g50_pct": r((np.exp(g50) - 1) * 100, 2), "g20_pct": r((np.exp(g20) - 1) * 100, 2),
                         "dlog_ratio": r(dr, 4), "share_denominator": r(g20 / abs(dr), 3) if dr < 0 else None}
main["decomposition_male"] = dec
# 年齢別の伸び（男、2006→2025）
agg = []
for sex in ["男", "女"]:
    c2 = curve(sex)
    for a in WORK:
        agg.append({"sex": sex, "age": a, "w2006": c2.loc[2006, a], "w2019": c2.loc[2019, a], "w2025": c2.loc[2025, a],
                    "g_2006_2025": (c2.loc[2025, a] / c2.loc[2006, a] - 1) * 100,
                    "g_2006_2019": (c2.loc[2019, a] / c2.loc[2006, a] - 1) * 100,
                    "g_2019_2025": (c2.loc[2025, a] / c2.loc[2019, a] - 1) * 100})
agg = pd.DataFrame(agg)
agg.round(2).to_csv(RES / "growth_by_age.csv", index=False)
main["growth_by_age_male"] = {row.age: {"2006_2025": r(row.g_2006_2025, 2), "2006_2019": r(row.g_2006_2019, 2), "2019_2025": r(row.g_2019_2025, 2)} for row in agg[agg.sex == "男"].itertuples()}

# ---- 規模別 ----
sz = {}
for s_, k in [("1000人以上", "male_1000"), ("100〜999人", "male_100_999"), ("10〜99人", "male_10_99")]:
    sz[s_] = change(ts[k])
main["size_male"] = sz

# ---- 学歴の区分の確かめ（2019年の高校卒と2020年の高校・専門学校の労働者の割合）----
chk = {}
for y in [2018, 2019, 2020, 2021]:
    d = g[(g.year == y) & (g.sex == "男") & (g["size"] == "企業規模計") & (g.age == "年齢計")].set_index("edu")["workers10"]
    tot_ = d.get("学歴計")
    chk[y] = {k: r(v / tot_ * 100, 1) for k, v in d.items() if k != "学歴計"}
main["edu_share_male_check"] = chk

# ---- 仮説 ----
rc = main["ratio_change"]
main["judgement"] = {
    "H1": "支持" if rc["male_50_54_over_20_24"]["v1"] <= rc["male_50_54_over_20_24"]["v0"] * 0.9 else "外れ",
    "H2": "支持" if (dec["2006_2025"]["share_denominator"] or 0) > 0.5 else "外れ",
    "H3": "支持" if rc["male_univ"]["pct"] < 0 and rc["male_high"]["pct"] < 0 else "外れ",
    "H4": "支持" if rc["male_1000"]["pct"] < rc["male_10_99"]["pct"] else "外れ",
}

# ---- 頑健性 ----
rb = []


def add(name, s, y0=2006, y1=2025):
    rb.append({"check": name, "y0": y0, "y1": y1, "v0": s.loc[y0], "v1": s.loc[y1], "pct": (s.loc[y1] / s.loc[y0] - 1) * 100})


add("主：男 50〜54歳÷20〜24歳", ts.male_50_54_over_20_24)
add("1 男 55〜59歳÷25〜29歳", ts.male_55_59_over_25_29)
add("2 学歴構成を2006年に固定", ts.male_fixed_edu2006)
add("3 女 50〜54歳÷20〜24歳", ts.female_50_54_over_20_24)
add("4a 期間 2006→2019年", ts.male_50_54_over_20_24, 2006, 2019)
add("4b 期間 2010→2025年", ts.male_50_54_over_20_24, 2010, 2025)
m3 = ts.male_50_54_over_20_24
rb.append({"check": "5 3年平均（2006〜08年→2023〜25年）", "y0": 2007, "y1": 2024, "v0": m3.loc[2006:2008].mean(),
           "v1": m3.loc[2023:2025].mean(), "pct": (m3.loc[2023:2025].mean() / m3.loc[2006:2008].mean() - 1) * 100})
add("6 男・大学大学院卒・1,000人以上", ts.male_univ_1000)
rbd = pd.DataFrame(rb)
rbd[["v0", "v1"]] = rbd[["v0", "v1"]].round(3)
rbd["pct"] = rbd.pct.round(2)
rbd.to_csv(RES / "robustness.csv", index=False)
main["robustness"] = rbd.to_dict(orient="records")

# ---- 問い直し：同じ世代を15年追う ----
c = curve("男")
coh = []
for y0 in range(2006, 2011):
    for a0 in ["20〜24歳", "25〜29歳", "30〜34歳", "35〜39歳"]:
        i = AGES.index(a0)
        a1 = AGES[i + 3]
        coh.append({"start_year": y0, "start_age": a0, "end_year": y0 + 15, "end_age": a1,
                    "w0": c.loc[y0, a0], "w1": c.loc[y0 + 15, a1], "growth_pct": (c.loc[y0 + 15, a1] / c.loc[y0, a0] - 1) * 100})
# 比べるため、5年ずつ前の世代（15年でなく10年）も：2006→2016 と 2015→2025
for a0 in ["20〜24歳", "25〜29歳", "30〜34歳", "35〜39歳", "40〜44歳"]:
    i = AGES.index(a0)
    a1 = AGES[i + 2]
    for y0 in range(2006, 2016):
        coh.append({"start_year": y0, "start_age": a0, "end_year": y0 + 10, "end_age": a1,
                    "w0": c.loc[y0, a0], "w1": c.loc[y0 + 10, a1], "growth_pct": (c.loc[y0 + 10, a1] / c.loc[y0, a0] - 1) * 100})
coh = pd.DataFrame(coh)
coh.round(2).to_csv(RES / "cohort_growth_male.csv", index=False)
c10 = coh[coh.end_year - coh.start_year == 10]
main["cohort10_male"] = {a: {"first": r(c10[(c10.start_age == a) & (c10.start_year == 2006)].growth_pct.iloc[0], 2),
                             "last": r(c10[(c10.start_age == a) & (c10.start_year == 2015)].growth_pct.iloc[0], 2),
                             "slope_per_year": r(np.polyfit(c10[c10.start_age == a].start_year, c10[c10.start_age == a].growth_pct, 1)[0], 3)}
                         for a in ["20〜24歳", "25〜29歳", "30〜34歳", "35〜39歳", "40〜44歳"]}
c15 = coh[coh.end_year - coh.start_year == 15]
main["cohort15_male"] = {a: {int(y): r(v, 2) for y, v in c15[c15.start_age == a].set_index("start_year").growth_pct.items()}
                         for a in ["20〜24歳", "25〜29歳", "30〜34歳", "35〜39歳"]}

with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(main, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=1, sort_keys=True))
