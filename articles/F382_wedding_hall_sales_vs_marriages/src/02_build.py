"""data/raw から分析用の表を作る（ネットにはつながない）。
- data/wedding_annual.csv：結婚式場業の年の実数と伸び率（旧様式 2000〜2014年、新様式 2015〜2024年）
- data/wedding_monthly.csv：同じく月の実数と伸び率
- data/marriage_annual.csv：婚姻件数（総数・夫妻とも初婚）
- data/cpi_annual.csv：消費者物価指数（総合・生鮮食品を除く総合）の年平均"""
import pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def num(v):
    s = str(v).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


def year_of(s):
    m = re.search(r"(\d{4})年", str(s))
    return int(m.group(1)) if m else None


# 旧様式（2000〜2014年）：列 4=売上高、6=取扱件数、10=従業者数
OLD = RAW / "tokusabi_wedding_2000_2014.xls"
NEW = RAW / "tokusabi_wedding_2015_2024.xls"
rows = []
for sheet, kind in [("年・実数", "level"), ("年・伸び率", "growth")]:
    x = pd.read_excel(OLD, sheet_name=sheet, header=None, dtype=str)
    for i in range(len(x)):
        y = year_of(x.iat[i, 2])
        if y and 2000 <= y <= 2014:
            rows.append({"era": "old", "year": y, "kind": kind, "sales": num(x.iat[i, 4]), "count": num(x.iat[i, 6]), "emp": num(x.iat[i, 10])})
    z = pd.read_excel(NEW, sheet_name=sheet, header=None, dtype=str)
    for i in range(len(z)):
        if re.match(r"^\d{4}000000$", str(z.iat[i, 0])):
            rows.append({"era": "new", "year": int(str(z.iat[i, 0])[:4]), "kind": kind, "sales": num(z.iat[i, 2]), "count": num(z.iat[i, 3]), "emp": num(z.iat[i, 4])})
a = pd.DataFrame(rows).pivot_table(index=["era", "year"], columns="kind", values=["sales", "count", "emp"], dropna=False)
a.columns = [f"{v}_{k}" for v, k in a.columns]
a = a.dropna(how="all").reset_index().sort_values("year").reset_index(drop=True)
a.to_csv(ROOT / "data" / "wedding_annual.csv", index=False)

# 月
mrows = []
for sheet, kind in [("月・実数", "level"), ("月・伸び率", "growth")]:
    x = pd.read_excel(OLD, sheet_name=sheet, header=None, dtype=str)
    cur = None
    for i in range(len(x)):
        y = year_of(x.iat[i, 1])
        if y:
            cur = y
        mm = re.match(r"^(\d{1,2})月$", str(x.iat[i, 2]).strip())
        if cur and mm and 2000 <= cur <= 2014:
            mrows.append({"era": "old", "year": cur, "month": int(mm.group(1)), "kind": kind, "sales": num(x.iat[i, 4]), "count": num(x.iat[i, 6])})
    z = pd.read_excel(NEW, sheet_name=sheet, header=None, dtype=str)
    for i in range(len(z)):
        c = str(z.iat[i, 0])
        if re.match(r"^\d{4}00\d{4}$", c) and c[6:8] == c[8:10]:
            mrows.append({"era": "new", "year": int(c[:4]), "month": int(c[8:10]), "kind": kind, "sales": num(z.iat[i, 2]), "count": num(z.iat[i, 3])})
m = pd.DataFrame(mrows).pivot_table(index=["era", "year", "month"], columns="kind", values=["sales", "count"], dropna=False)
m.columns = [f"{v}_{k}" for v, k in m.columns]
m = m.dropna(how="all").reset_index().sort_values(["year", "month"]).reset_index(drop=True)
m.to_csv(ROOT / "data" / "wedding_monthly.csv", index=False)

# 婚姻件数
lines = open(RAW / "vs2025_t9_5_marriage_first_re.csv", encoding="cp932").read().splitlines()
mar = []
for l in lines:
    f = l.split(",")
    if re.match(r"^\d{4}$", f[0].strip()):
        mar.append({"year": int(f[0]), "marriages": num(f[1]), "both_first": num(f[2])})
mar = pd.DataFrame(mar).sort_values("year").reset_index(drop=True)
mar.to_csv(ROOT / "data" / "marriage_annual.csv", index=False)

# 消費者物価指数（年平均）
raw = pd.read_csv(RAW / "cpi_2025base_middle_class_monthly.csv", encoding="cp932", header=None, dtype=str)
hdr = list(raw.iloc[0])
r = raw[raw[0].str.match(r"^\d{6}$", na=False)]
cpi = pd.DataFrame({"year": r[0].str[:4].astype(int), "month": r[0].str[4:].astype(int),
                    "cpi_all": r[hdr.index("総合")].astype(float), "cpi_core": r[hdr.index("生鮮食品を除く総合")].astype(float)})
cnt = cpi.groupby("year").size()
cpi = cpi[cpi.year.isin(cnt[cnt == 12].index)].groupby("year", sort=True)[["cpi_all", "cpi_core"]].mean().reset_index()
cpi.to_csv(ROOT / "data" / "cpi_annual.csv", index=False, float_format="%.4f")
print("monthly", len(m), m.groupby("era").size().to_dict(), "| marriages", mar.year.min(), mar.year.max(), "| cpi", cpi.year.min(), cpi.year.max())
