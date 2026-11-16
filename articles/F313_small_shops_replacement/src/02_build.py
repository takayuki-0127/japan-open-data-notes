"""平成19年商業統計表 第1巻 第1表から、業種×年の表を作る（オフライン）。
出力：data/retail_by_industry_year.csv（code, name, level, year, est_total, est_corp, est_indiv, employees, sales_mil, floor_m2）
1991年は、上段（その年の分類のまま）を 1991、下段（1994年調査と対応するよう再集計）を 1991r とする。"""
import pathlib, re, warnings
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
v = pd.read_excel(RAW / "shogyo2007_vol1_sangyo_soukatsu.xls", sheet_name="１巻１表", header=None, engine="xlrd")
ERA = {"昭和": 1925, "平成": 1988}
def to_year(s):
    s = str(s).replace("　", "").replace(" ", "")
    m = re.match(r"(昭和|平成)(\d+|[０-９]+)年", s)
    if not m: return None
    n = int(m.group(2).translate(str.maketrans("０１２３４５６７８９", "0123456789")))
    return ERA[m.group(1)] + n
recs, prev = [], None
for i in range(10, v.shape[0]):
    code, name = str(v.iloc[i, 1]).strip(), str(v.iloc[i, 2]).strip().replace("　", "")
    if code in ("nan", ""): continue
    y = to_year(v.iloc[i, 3])
    if y is None:
        if prev == 1991 and pd.isna(v.iloc[i, 3]):
            y = "1991r"
        else:
            continue
    prev = y
    vals = [pd.to_numeric(v.iloc[i, j], errors="coerce") for j in range(4, 11)]
    recs.append(dict(code=code, name=name, year=str(y), est_total=vals[0], est_corp=vals[1], est_indiv=vals[2], employees=vals[3], sales_mil=vals[4], stock_mil=vals[5], floor_m2=vals[6]))
d = pd.DataFrame(recs)
d["level"] = d.code.map(lambda c: "total" if not c.isdigit() else {2: "major", 3: "minor", 4: "detail"}.get(len(c), "other"))
d.to_csv(DATA / "retail_by_industry_year.csv", index=False)
print(d.code.nunique(), d.year.value_counts().sort_index().to_dict())
print(d[d.level == "total"].drop_duplicates("code")[["code", "name"]].to_string())
print(d[(d.level == "major")].drop_duplicates("code")[["code", "name"]].to_string())
