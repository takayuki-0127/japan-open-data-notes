"""元の表から分析用の表を作る。
- data/cpi_rent_annual.csv：CPI 民営家賃ほかの年平均
- data/jutaku_rent_timeseries.csv：住調の1畳当たり家賃・1か月当たり家賃（1973〜2023年）
- data/t27_cells.csv：2023年 入居時期×建築時期 の借家数・1畳当たり家賃（民営借家など）"""
import pathlib, re
import pandas as pd
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data"

# CPI
c = pd.read_csv(RAW / "cpi_item_annual.csv", header=None, dtype=str, encoding="cp932")
code = c.iloc[2]
want = {"0001": "all_items", "0046": "rent_total", "3000": "private_rent", "3016": "public_rent", "3017": "ur_rent", "3030": "imputed_rent"}
cols = [i for i in range(1, c.shape[1]) if code[i] in want]
rows = c.iloc[6:]
rows = rows[rows[0].str.strip().str.fullmatch(r"\d{4}")]
cpi = pd.DataFrame({"year": rows[0].str.strip().astype(int)})
for i in cols:
    cpi[want[code[i]]] = pd.to_numeric(rows[i], errors="coerce")
cpi.to_csv(OUT / "cpi_rent_annual.csv", index=False)

# 住調 時系列（第34-1表）
ws = openpyxl.load_workbook(RAW / "jutaku2023_t34_1_rent_timeseries.xlsx", read_only=True, data_only=True).worksheets[0]
R = [list(r) for r in ws.iter_rows(values_only=True)]
names = ["total", "total_dedicated", "public", "ur", "private_wood", "private_wood_shared", "private_nonwood", "issued", "mixed_use", "mixed_agri"]
part, recs = None, []
for r in R:
    s = " ".join(str(x) for x in r if x is not None)
    if "その１" in s: part = "monthly_rent"
    elif "その２" in s: part = "rent_per_tatami"
    elif "増減" in s: part = None if part in ("monthly_rent", "rent_per_tatami") and False else part
    v = [x for x in r if x is not None]
    if part and len(v) >= 3 and isinstance(v[1], int) and 1970 <= v[1] <= 2030 and str(v[0]).strip().startswith(("昭和", "平成", "令和")):
        for n, x in zip(names, v[2:]):
            recs.append(dict(measure=part, year=v[1], tenure=n, value=pd.to_numeric(x, errors="coerce")))
ts = pd.DataFrame(recs).drop_duplicates(["measure", "year", "tenure"])
ts.to_csv(OUT / "jutaku_rent_timeseries.csv", index=False)

# 第27表
ws = openpyxl.load_workbook(RAW / "jutaku2023_t27_rent_by_movein_construction.xlsx", read_only=True, data_only=True).worksheets[0]
R = [list(r) for r in ws.iter_rows(values_only=True)]
COLS = {12: "all_rented", 13: "dedicated_total", 14: "public", 15: "ur", 16: "private", 17: "private_wood", 18: "private_nonwood", 19: "issued", 20: "mixed_use"}
SECT = ["count", "rent_per_tatami", "rent_per_tatami_incl_fee"]
sec, movein, recs = -1, None, []
for r in R:
    if not isinstance(r[5], int):
        continue
    if r[5] in (1, 76, 151):
        sec += 1; movein = "総数"
    if r[8]:
        movein = str(r[8]).strip(); cons = "総数"
    elif r[9]:
        cons = str(r[9]).strip()
    else:
        cons = "総数"
    for j, n in COLS.items():
        recs.append(dict(section=SECT[sec], serial=r[5], movein=movein, construction=cons, tenure=n, value=pd.to_numeric(r[j], errors="coerce")))
t = pd.DataFrame(recs)
t.to_csv(OUT / "t27_cells.csv", index=False)
print(cpi.tail(3).to_string(), ts.measure.value_counts().to_dict(), t.groupby("section").size().to_dict(), sorted(t.movein.unique()), sorted(t.construction.unique()), sep="\n")
