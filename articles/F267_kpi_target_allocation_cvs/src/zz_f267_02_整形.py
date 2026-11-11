"""F267 02 整形：協会の PDF を pdftotext -layout で文字にし、月ごとの表にする。"""
import pathlib, re, subprocess
import pandas as pd
BASE = pathlib.Path(__file__).resolve().parents[1]
RAW, OUT = BASE / "data" / "raw", BASE / "data"
COLS = ["sales_all", "sales_all_yoy", "sales_ex", "sales_ex_yoy", "stores", "stores_yoy",
        "cust_all", "cust_all_yoy", "cust_ex", "cust_ex_yoy", "price_all", "price_all_yoy",
        "price_ex", "price_ex_yoy"]
num = r"(-?[\d,]+(?:\.\d+)?%?|―)"

def parse(pdf, y0):
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    rows, annual, y = [], [], y0
    for line in txt.splitlines():
        m = re.search(r"(\d{1,2})月\s+" + r"\s+".join([num] * 14) + r"\s*$", line)
        ma = re.search(r"1月～12月\s+" + r"\s+".join([num] * 14) + r"\s*$", line)
        if ma:
            vals = ma.groups()
            annual.append([y] + list(vals)); y += 1; continue
        if m:
            mon = int(m.group(1)); vals = m.groups()[1:]
            rows.append([y, mon] + list(vals))
    return rows, annual

def conv(v):
    if v == "―": return float("nan")
    v = v.replace(",", "")
    if v.endswith("%"): return float(v[:-1]) / 100
    return float(v)

r1, a1 = parse(RAW / "jfa_cvs_monthly_2005_2016.pdf", 2005)
r2, a2 = parse(RAW / "jfa_cvs_monthly_2017_2025.pdf", 2017)
m = pd.DataFrame(r1 + r2, columns=["year", "month"] + COLS)
a = pd.DataFrame(a1 + a2, columns=["year"] + COLS)
for c in COLS:
    m[c] = m[c].map(conv); a[c] = a[c].map(conv)
assert len(m) == 21 * 12, len(m)
assert list(a.year) == list(range(2005, 2026)), list(a.year)
assert (m.groupby("year").month.apply(list) == pd.Series({y: list(range(1, 13)) for y in range(2005, 2026)})).all()
m.insert(0, "ym", m.year.astype(str) + "-" + m.month.map("{:02d}".format))
m.to_csv(OUT / "jfa_cvs_monthly.csv", index=False)
a.to_csv(OUT / "jfa_cvs_annual.csv", index=False)
# 照合：月の売上の合計＝年の売上（全店）
chk = m.groupby("year").sales_all.sum().values - a.sales_all.values
print("months", len(m), "years", len(a), "annual sum diff max", abs(chk).max())

# 商業動態統計（コンビニ合計）
meti = pd.read_csv(RAW / "meti_sales_monthly_6types.csv")
meti = meti[meti["業態"] == "コンビニ"][["ym", "販売額_百万円"]].rename(columns={"販売額_百万円": "meti_sales"})
meti.to_csv(OUT / "meti_cvs_monthly.csv", index=False)
print("meti", len(meti), meti.ym.min(), meti.ym.max())
