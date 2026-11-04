"""data/raw の取得値を、分析用の縦長 CSV に整える。"""
from pathlib import Path
import pandas as pd

D = Path(__file__).resolve().parents[1] / "data"
R = D / "raw"


def kv(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        k, v = line.split(":", 1)
        out[k] = [float(x) for x in v.split(",")]
    return out


# 1) 月次：家計調査（二人以上の世帯）の電気代・消費支出、消費者物価指数（電気代・総合・ガス代）
k = kv(R / "monthly_kakei.txt")
c = kv(R / "cpi_monthly.txt")
months = pd.period_range("2015-01", periods=len(c["elecCPI"]), freq="M")
m = pd.DataFrame({"month": months.astype(str), "cpi_elec": c["elecCPI"], "cpi_total": c["totCPI"], "cpi_gas": c["gasCPI"]})
m["elec_spend"] = pd.Series(k["elec"] + [None] * (len(months) - len(k["elec"])))
m["cons_spend"] = pd.Series(k["cons"] + [None] * (len(months) - len(k["cons"])))
m.to_csv(D / "monthly_national.csv", index=False)

# 2) 年次：全国（二人以上の世帯）の電気代・購入数量（kWh）
n = pd.read_csv(R / "national_kwh_2005_2024.csv", header=None, names=["year", "elec", "price", "kwh"])
g = pd.read_csv(R / "annual_groups.csv")
nat25 = g[(g.year == 2025) & (g.tab == "q5") & (g.group == "avg")].iloc[0]
n = pd.concat([n[["year", "elec", "kwh"]], pd.DataFrame([{"year": 2025, "elec": nat25.elec, "kwh": nat25.kwh}])], ignore_index=True)
n["yen_per_kwh"] = n.elec / n.kwh
n.to_csv(D / "annual_national.csv", index=False)

# 3) 年次：世帯の区分ごと（年間収入五分位・世帯主の年齢・都市階級・地方）
names = {"avg": "平均", "Q1": "第Ⅰ五分位", "Q2": "第Ⅱ五分位", "Q3": "第Ⅲ五分位", "Q4": "第Ⅳ五分位", "Q5": "第Ⅴ五分位",
         "a29": "29歳以下", "a30": "30〜39歳", "a40": "40〜49歳", "a50": "50〜59歳", "a60": "60〜69歳", "a70": "70歳以上",
         "nat": "全国", "cbig": "大都市", "cmid": "中都市", "csmA": "小都市A", "csmB": "小都市B・町村",
         "r_hok": "北海道", "r_toh": "東北", "r_kan": "関東", "r_hkr": "北陸", "r_tok": "東海", "r_kin": "近畿",
         "r_chg": "中国", "r_shk": "四国", "r_kyu": "九州", "r_oki": "沖縄"}
g["label"] = g.group.map(names)
g.loc[(g.tab == "reg") & g.group.str.startswith("c"), "tab"] = "city"
g.loc[(g.tab == "reg") & (g.group == "nat"), "tab"] = "city"
g["yen_per_kwh"] = g.elec / g.kwh
g["share"] = g.elec / g.cons
g.to_csv(D / "annual_groups_tidy.csv", index=False)

# 4) 年次：単身・二人以上・総世帯の電気代と消費支出
h = kv(R / "annual_households.txt")
rows = []
for t, lab in [("single", "単身世帯"), ("two", "二人以上の世帯"), ("total", "総世帯")]:
    for y, e, cs in zip(h["yrs"], h[t + "_elec"], h[t + "_cons"]):
        rows.append({"year": int(y), "type": lab, "elec": e, "cons": cs})
pd.DataFrame(rows).to_csv(D / "annual_households.csv", index=False)
print("ok")
