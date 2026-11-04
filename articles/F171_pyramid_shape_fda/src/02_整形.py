"""02 整形：国勢調査（不詳補完値）の年齢各歳別人口から、市区町村ごとの「年齢別の割合」を作る。

入力  data/census_age_single_2015_2020.csv（01_取得.py で作成）
出力  data/shares_<年>_<性別>.csv（行＝市区町村、列＝0〜100歳以上の割合ではなく人数）
      data/units.csv（分析に使う 1,741 市区町村の一覧）

分析の単位
- 市（政令指定都市は市全体）・町・村と、東京都の特別区（23区）
- 政令指定都市の「区」と「特別区部」全体は使わない
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

raw = pd.read_csv(DATA / "census_age_single_2015_2020.csv", dtype={"code": str, "level": str})
# 列 000 は総数、001〜101 が 0歳〜100歳以上
age_cols = [f"{i:03d}" for i in range(1, 102)]
ren = {c: int(c) - 1 for c in age_cols}

def unit_mask(d):
    lv, cd = d["level"], d["code"]
    muni = lv.isin(["2", "3"])
    seirei = (lv == "1") & (cd != "13100")
    tokubetsu = (lv == "0") & cd.str.startswith("131")
    return muni | seirei | tokubetsu

d = raw[unit_mask(raw)].copy()
d["pref"] = d["code"].str[:2]

units = d[(d.year == 2020) & (d.sex == 0)][["code", "name", "pref", "level", "000"]].rename(columns={"000": "pop2020"})
units.to_csv(DATA / "units.csv", index=False)

for (y, s), g in d.groupby(["year", "sex"]):
    m = g.set_index("code")[age_cols].rename(columns=ren)
    m.to_csv(DATA / f"counts_{y}_{s}.csv")

# 都道府県（代替案・比較用）
p = raw[(raw.level == "a") & (raw.code != "00000")]
for (y, s), g in p.groupby(["year", "sex"]):
    m = g.set_index("code")[age_cols].rename(columns=ren)
    m.to_csv(DATA / f"pref_counts_{y}_{s}.csv")

print("units 2020:", len(units))
print(d.groupby(["year", "sex"]).size())
