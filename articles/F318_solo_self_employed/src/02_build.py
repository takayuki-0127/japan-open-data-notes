"""労働力調査 長期時系列表4(1) から、年×男女の表を作る（オフライン）。
出力：data/lfs_status.csv（year, sex, employed, self_employed, with_employees, family, employees）単位：万人"""
import pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
v = pd.read_excel(RAW / "lfs_longterm_t4_1.xlsx", header=None)
COLS = ["employed", "self_employed", "with_employees", "family", "employees", "regular", "temporary", "daily"]
recs = []
for i in range(9, v.shape[0]):
    y = pd.to_numeric(v.iloc[i, 1], errors="coerce")
    if pd.isna(y) or not (1950 <= y <= 2030): continue
    for k, sex in enumerate(["total", "male", "female"]):
        vals = [pd.to_numeric(v.iloc[i, 2 + 8 * k + j], errors="coerce") for j in range(8)]
        recs.append(dict(year=int(y), sex=sex, **dict(zip(COLS, vals)), note=str(v.iloc[i, 0]).strip()))
d = pd.DataFrame(recs)
dup = d.duplicated(["year", "sex"], keep=False)
print("duplicated years:", sorted(d[dup].year.unique()))
d = d.drop_duplicates(["year", "sex"], keep="last")
d["solo"] = d.self_employed - d.with_employees
d.to_csv(DATA / "lfs_status.csv", index=False)
print(d[(d.sex == "total") & (d.year.isin([1953, 1990, 2000, 2011, 2025]))].to_string())
