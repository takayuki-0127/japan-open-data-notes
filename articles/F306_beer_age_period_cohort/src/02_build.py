"""家計調査 第4-6表（2002〜2025年）から、年×年齢×品目の支出金額・購入数量の表を作る（オフライン）。
出力：data/alcohol_by_age.csv（item：酒類・ビール・発泡酒等・チューハイ等、および世帯数分布）"""
import glob, pathlib, re, warnings
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
AGES = ["平均", "29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
CODES = {"1.11": "alcohol_total", "3X4": "beer", "3X7": "happoshu", "3X8": "chuhai"}
recs = []
for f in sorted(glob.glob(str(RAW / "kakei_4-6_*"))):
    y = int(re.search(r"_(\d{4})\.", f).group(1))
    v = list(pd.read_excel(f, sheet_name=None, header=None).values())[0]
    S = lambda i, j: str(v.iloc[i, j]).strip()
    if y <= 2019:  # 旧い形：品目コード col 7、名前 col 8、年齢の見出し row 7（col 11 から4列おき）、値は 頻度・金額・数量・価格
        ages = {S(7, j): j for j in range(11, v.shape[1], 4) if S(7, j) in AGES}
        assert list(ages) == AGES, (y, ages)
        for i in range(v.shape[0]):
            code, name7 = S(i, 7), S(i, 7)
            key = CODES.get(code)
            if key is None and "世帯数分布" in name7:
                key = "hh_weight"
            if key is None:
                continue
            for a, j in ages.items():
                amt = pd.to_numeric(v.iloc[i, j], errors="coerce"); qty = pd.to_numeric(v.iloc[i, j + 1], errors="coerce")
                recs.append(dict(year=y, item=key, name=S(i, 8) if key != "hh_weight" else "世帯数分布", age=a, amount=amt, quantity=qty))
    else:  # 新しい形：コード col 10、名前 col 11、見出し row 8「年齢・支出金額」
        cols = {S(8, j): j for j in range(13, v.shape[1])}
        for i in range(v.shape[0]):
            code = S(i, 10); key = CODES.get(code)
            if key is None and S(i, 11).startswith("世帯数分布"):
                key = "hh_weight"
            if key is None:
                continue
            for a in AGES:
                ja, jq = cols[f"{a}・支出金額"], cols[f"{a}・購入数量"]
                recs.append(dict(year=y, item=key, name=S(i, 11) if key != "hh_weight" else "世帯数分布", age=a,
                                 amount=pd.to_numeric(v.iloc[i, ja], errors="coerce"), quantity=pd.to_numeric(v.iloc[i, jq], errors="coerce")))
d = pd.DataFrame(recs).drop_duplicates(["year", "item", "age"], keep="first").sort_values(["item", "year", "age"]).reset_index(drop=True)
d.to_csv(DATA / "alcohol_by_age.csv", index=False)
print(d.groupby("item").year.agg(["min", "max", "count"]))
print(d[(d.item == "beer") & (d.year.isin([2002, 2025]))])
print(d[d.item == "happoshu"].drop_duplicates("name")[["year", "name"]])
