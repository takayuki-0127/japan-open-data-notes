"""経済センサスの表から、使う部分を縦長の CSV にする。
出力：data/t1_series.csv、data/form_2016_2021.csv、data/items_2021.csv、data/item_by_industry_2021.csv"""
import pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"


def num(v):
    s = str(v).strip().replace(",", "")
    if s in ("", "-", "x", "X", "nan", "None", "…", "***"):
        return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


# ---- 第1表（1994〜2021年、細分類別）
d = pd.read_excel(RAW / "ec2021_soukatsu_t1.xlsx", header=None, dtype=object)
rows = []
for i in range(len(d)):
    if str(d.iat[i, 0]) != "00_全国":
        continue
    ind = str(d.iat[i, 2]); yr = str(d.iat[i, 3])
    m = re.match(r"^(\S+?)_(.*)$", ind); y = re.match(r"^\d_(\d{4})年$", yr)
    if not m or not y:
        continue
    rows.append({"code": m.group(1), "name": m.group(2), "level": int(d.iat[i, 1]), "year": int(y.group(1)),
                 "est": num(d.iat[i, 4]), "est_corp": num(d.iat[i, 5]), "est_indiv": num(d.iat[i, 6]),
                 "employees": num(d.iat[i, 7]), "sales_mil": num(d.iat[i, 8]), "floor_m2": num(d.iat[i, 9])})
t1 = pd.DataFrame(rows)
t1.to_csv(OUT / "t1_series.csv", index=False)

# ---- 第9表（商品販売形態別、法人の事業所）2016年・2021年
FORMS = ["store", "visit", "catalog", "internet", "vending", "other"]
out = []
d16 = pd.read_excel(RAW / "ec2016_soukatsu.xls", sheet_name="第９表", header=None, dtype=object)
for i in range(14, len(d16)):
    code = str(d16.iat[i, 1]).strip(); name = str(d16.iat[i, 2]).strip()
    if code == "nan" or name == "nan":
        continue
    code = "I2" if code == "ｺｳﾘ" else code
    r = {"year": 2016, "code": code, "name": name, "est": num(d16.iat[i, 3]), "sales_total": num(d16.iat[i, 4]),
         "sales_retail": num(d16.iat[i, 8])}
    for k, f in enumerate(FORMS):
        r[f"sales_{f}"] = num(d16.iat[i, 11 + 3 * k])
    out.append(r)
d21 = pd.read_excel(RAW / "ec2021_soukatsu_t9.xlsx", header=None, dtype=object)
for i in range(len(d21)):
    if str(d21.iat[i, 0]) != "00_全国":
        continue
    m = re.match(r"^(\S+?)_(.*)$", str(d21.iat[i, 2]))
    code = m.group(1); name = m.group(2)
    r = {"year": 2021, "code": code, "name": name, "est": num(d21.iat[i, 3]), "sales_total": num(d21.iat[i, 4]),
         "sales_retail": num(d21.iat[i, 8])}
    for k, f in enumerate(FORMS):
        r[f"sales_{f}"] = num(d21.iat[i, 11 + 3 * k])
    out.append(r)
pd.DataFrame(out).to_csv(OUT / "form_2016_2021.csv", index=False)

# ---- 品目編 第2表（全国の行だけ）
d = pd.read_excel(RAW / "ec2021_hinmoku_t2.xlsx", header=None, dtype=object, nrows=12)
hdr = d.iloc[5].tolist(); nat = d.iloc[9].tolist()
items = []
for j in range(2, len(hdr), 2):
    m = re.match(r"^(\S+?)_(.*)$", str(hdr[j]))
    if not m:
        continue
    items.append({"item_code": m.group(1), "item": m.group(2), "est": num(nat[j]), "sales_mil": num(nat[j + 1])})
pd.DataFrame(items).to_csv(OUT / "items_2021.csv", index=False)

# ---- 品目編 第4表（産業細分類×商品分類）：中古の品目と小売商品計の列だけ
d = pd.read_excel(RAW / "ec2021_hinmoku_t4.xlsx", header=None, dtype=object)
hdr = d.iloc[5].tolist()
keep = [j for j in range(3, len(hdr), 2) if re.search(r"中古|古本|骨とう|I2_小売商品計|乗用車（新車）", str(hdr[j]))]
rows = []
for i in range(9, len(d)):
    if str(d.iat[i, 0]) != "00_全国":
        continue
    m = re.match(r"^(\S+?)_(.*)$", str(d.iat[i, 2]))
    if not m:
        continue
    for j in keep:
        im = re.match(r"^(\S+?)_(.*)$", str(hdr[j]))
        rows.append({"ind_code": m.group(1), "industry": m.group(2), "level": int(d.iat[i, 1]),
                     "item_code": im.group(1), "item": im.group(2), "est": num(d.iat[i, j]), "sales_mil": num(d.iat[i, j + 1])})
pd.DataFrame(rows).to_csv(OUT / "item_by_industry_2021.csv", index=False)
print(len(t1), len(out), len(items), len(rows))
