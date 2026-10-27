"""都道府県×年の分析用の表を作る。

使う指標（社会・人口統計体系の都道府県データ、カッコは年）:
  医師  I0920101 医療施設に従事する医師数（人口10万人当たり）  2010・2022
  所得  D02206   課税対象所得（納税義務者1人当たり、千円）      2010・2024
  大卒  E09504   最終学歴が大学・大学院卒の者の割合             2010・2020
  都市  A01401   人口集中地区人口比率                           2010・2020
  高齢  A03503   65歳以上人口割合                               2010・2024
  病床  I0910203 一般病院病床数（人口10万人当たり）             2010・2023
  大学  E0610102 大学数（人口10万人当たり）                     2010・2024
  気温  B02101   年平均気温                                     2010・2024
  失業  F01301   完全失業率                                     2010・2020
  看護  I0920301 看護師・准看護師数（人口10万人当たり）          2010・2022
  標死  I05101   標準化死亡率（人口千人当たり）                 2010・2020
平均寿命（0歳・65歳）は F49 の都道府県別生命表（2010・2015・2020年）。
"""
import pandas as pd
from common import RAW, DATA

ind = pd.read_csv(RAW / "ssds_pref_indicators.csv")
CODES = {"I0920101": "doctors", "D02206": "income", "E09504": "univ_grad", "A01401": "did",
         "A03503": "aged65", "I0910203": "beds", "E0610102": "universities", "B02101": "temp",
         "F01301": "unemp", "I0920301": "nurses", "I05101": "std_mort"}
pcols = [f"p{i:02d}" for i in range(1, 48)]
rows = []
for code, name in CODES.items():
    s = ind[ind.code == code]
    for _, r in s.iterrows():
        for i, c in enumerate(pcols, start=1):
            rows.append({"var": name, "year": int(r.year), "pref_code": i, "value": float(r[c])})
long = pd.DataFrame(rows).drop_duplicates(["var", "year", "pref_code"])

def pick(var, year):
    s = long[(long["var"] == var) & (long.year == year)].set_index("pref_code")["value"]
    assert len(s) == 47, (var, year, len(s))
    return s

le = pd.read_csv(RAW / "life_expectancy_f49.csv")
names = le[["pref_code", "pref"]].drop_duplicates().set_index("pref_code")["pref"]

def e(year, sex, age=0):
    s = le[(le.year == year) & (le.sex == sex) & (le.age == age)].set_index("pref_code")["ex"]
    assert len(s) == 47
    return s

# 基本：説明側は2010年、結果は2015年の平均寿命（5年のずれを置く）
base = pd.DataFrame({"pref": names})
for v in CODES.values():
    base[v] = pick(v, 2010)
for sex, k in (("男", "m"), ("女", "f")):
    base[f"e0_{k}_2015"] = e(2015, sex)
    base[f"e0_{k}_2010"] = e(2010, sex)
    base[f"e0_{k}_2020"] = e(2020, sex)
    base[f"e65_{k}_2015"] = e(2015, sex, 65)
# 新しい年（頑健性）：医師2022・病床2023 など ×  平均寿命2020
for v, y in (("doctors", 2022), ("income", 2024), ("univ_grad", 2020), ("did", 2020), ("aged65", 2024),
             ("beds", 2023), ("universities", 2024), ("temp", 2024), ("unemp", 2020), ("nurses", 2022), ("std_mort", 2020)):
    base[f"{v}_new"] = pick(v, y)
base.index.name = "pref_code"
base.to_csv(DATA / "pref_panel.csv")
print(base.shape)
print(base[["doctors", "doctors_new", "e0_m_2015", "e0_f_2015"]].describe().round(2))
