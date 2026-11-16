"""家計調査 第4-6表（2002〜2025年）から、年×年齢×品目の支出金額・購入数量の表を作る（オフライン）。
出力：data/print_by_age.csv（item：書籍・他の印刷物・新聞・雑誌・書籍、および世帯数分布・世帯人員）。あわせて data/cpi_books_annual.csv"""
import glob, pathlib, re, warnings
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
AGES = ["平均", "29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
CODES = {"9.3": "print_total", "850": "newspaper", "851": "magazine", "854": "books"}
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
            if key is None and name7.startswith("世帯人員"):
                key = "hh_size"
            if key is None:
                continue
            for a, j in ages.items():
                amt = pd.to_numeric(v.iloc[i, j], errors="coerce"); qty = pd.to_numeric(v.iloc[i, j + 1], errors="coerce")
                recs.append(dict(year=y, item=key, name=S(i, 8) if key not in ("hh_weight", "hh_size") else key, age=a, amount=amt, quantity=qty))
    else:  # 新しい形：コード col 10、名前 col 11、見出し row 8「年齢・支出金額」
        cols = {S(8, j): j for j in range(13, v.shape[1])}
        for i in range(v.shape[0]):
            code = S(i, 10); key = CODES.get(code)
            if key is None and S(i, 11).startswith("世帯数分布"):
                key = "hh_weight"
            if key is None and S(i, 11) == "世帯人員":
                key = "hh_size"
            if key is None:
                continue
            for a in AGES:
                ja, jq = cols[f"{a}・支出金額"], cols[f"{a}・購入数量"]
                recs.append(dict(year=y, item=key, name=S(i, 11) if key not in ("hh_weight", "hh_size") else key, age=a,
                                 amount=pd.to_numeric(v.iloc[i, ja], errors="coerce"), quantity=pd.to_numeric(v.iloc[i, jq], errors="coerce")))
d = pd.DataFrame(recs).drop_duplicates(["year", "item", "age"], keep="first").sort_values(["item", "year", "age"]).reset_index(drop=True)
d.to_csv(DATA / "print_by_age.csv", index=False)
t = pd.read_csv(RAW / "cpi_middle_class_index.csv", encoding="cp932", header=None, dtype=str)
j = t.iloc[0].tolist().index("書籍・他の印刷物")
b = t.iloc[5:]; b = b[b[0].str.fullmatch(r"\d{6}")]
c = pd.DataFrame({"ym": b[0].astype(int), "cpi_books": pd.to_numeric(b[j], errors="coerce").values})
c["year"] = c.ym // 100
ca = c.groupby("year").agg(cpi_books=("cpi_books", "mean"), n=("cpi_books", "count")).reset_index()
ca = ca[(ca.n == 12) & (ca.year >= 2002)]
ca[["year", "cpi_books"]].to_csv(DATA / "cpi_books_annual.csv", index=False)
print(d.groupby("item").year.agg(["min", "max", "count"]))
print(d.groupby("item").year.agg(["min", "max", "count"]))
