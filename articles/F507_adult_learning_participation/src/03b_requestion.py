"""問い直し（結果を見てから足した）：25〜64歳で2016→2021年に上がった分は、仕事のための学習か、教養のための学習か。
第1-4表（目的別）の5歳階級の率を、2021年の推定人口で重みをつけて年齢をそろえる。"""
import json
import pandas as pd
from common import DATA, RES

pu = pd.read_csv(DATA / "purpose_2016_2021.csv")
AGES = ["25～29歳", "30～34歳", "35～39歳", "40～44歳", "45～49歳", "50～54歳", "55～59歳", "60～64歳"]
PURP = ["総数", "自分の教養を高めるため", "現在の仕事に役立てるため", "仕事につくため", "その他"]
KINDS = ["total", "business_total", "computing", "business", "foreign", "home", "humanities", "arts"]


def std(year, purpose, kind, sex="総数", ages=AGES):
    w = pu[(pu.year == 2021) & (pu.sex == sex) & (pu.purpose == "総数") & (pu.kind == "total") & pu.age.isin(ages)].set_index("age").pop_1000
    r = pu[(pu.year == year) & (pu.sex == sex) & (pu.purpose == purpose) & (pu.kind == kind) & pu.age.isin(ages)].set_index("age").rate
    return float(sum(r[a] * w[a] for a in ages) / sum(w[a] for a in ages))


rows = []
for sx in ("総数", "男", "女"):
    for p in PURP:
        for k in KINDS:
            a, b = std(2016, p, k, sx), std(2021, p, k, sx)
            rows.append({"sex": sx, "purpose": p, "kind": k, "std_2016": round(a, 2), "std_2021": round(b, 2), "diff": round(b - a, 2)})
df = pd.DataFrame(rows)
df.to_csv(RES / "requestion_purpose.csv", index=False)
g = df[(df.sex == "総数") & (df.kind == "total")].set_index("purpose")
q = {"note": "25〜64歳、2021年の推定人口の重みで年齢をそろえた行動者率（%）。目的は複数を選べるので、目的別の率の和は総数より大きい。",
     "total_by_purpose": {p: {"2016": round(g.loc[p, "std_2016"], 1), "2021": round(g.loc[p, "std_2021"], 1), "diff": round(g.loc[p, "diff"], 1)} for p in PURP},
     "sum_of_purposes_2021": round(float(g.loc[PURP[1:], "std_2021"].sum()), 1)}
c = df[(df.sex == "総数") & (df.kind == "computing")].set_index("purpose")
q["computing_by_purpose"] = {p: {"2016": round(c.loc[p, "std_2016"], 1), "2021": round(c.loc[p, "std_2021"], 1), "diff": round(c.loc[p, "diff"], 1)} for p in PURP}
q["by_sex_total"] = {sx: {p: round(float(df[(df.sex == sx) & (df.kind == "total") & (df.purpose == p)]["diff"].iloc[0]), 1) for p in PURP} for sx in ("男", "女")}
q["work_vs_culture_diff_ratio"] = round(q["total_by_purpose"]["現在の仕事に役立てるため"]["diff"] / q["total_by_purpose"]["自分の教養を高めるため"]["diff"], 2) if q["total_by_purpose"]["自分の教養を高めるため"]["diff"] else None
json.dump(q, open(RES / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(q, ensure_ascii=False, indent=1))
