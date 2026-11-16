"""data/raw の4つの CSV から、地点×年の長い表 data/phenology.csv を作る。ネットにはつながない。
値は「1月1日からの日数」（平年の暦で数える）。1〜6月の値は翌年に入った落葉とみなし365を足す。"""
import pathlib, io
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
ITEMS = {"015": "kaede_color", "016": "kaede_fall", "013": "ichou_color", "014": "ichou_fall"}
CUM = np.cumsum([0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30])

rows = []
for code, item in ITEMS.items():
    t = pd.read_csv(io.StringIO((RAW / f"phenology_{code}.csv").read_bytes().decode("cp932")), header=None, skiprows=1, dtype=str)
    hdr = t.iloc[0].tolist()
    ycols = [(j, int(h)) for j, h in enumerate(hdr) if str(h).isdigit() and 1900 < int(h) < 2100]
    for i in range(1, len(t)):
        st, name = t.iat[i, 0], str(t.iat[i, 1]).replace("　", "").strip()
        for j, y in ycols:
            v = int(t.iat[i, j]); mk = int(t.iat[i, j + 1])
            if v == 0:
                continue
            m, d = divmod(v, 100)
            doy = int(CUM[m - 1] + d)
            if m <= 6:
                doy += 365
            rows.append({"station": int(st), "name": name, "item": item, "year": y, "doy": doy, "mark": mk})
p = pd.DataFrame(rows).sort_values(["item", "station", "year"])
p.to_csv(ROOT / "data" / "phenology.csv", index=False)
print(p.groupby("item").agg(n=("doy", "size"), st=("station", "nunique"), y0=("year", "min"), y1=("year", "max")).to_string())
print(p.mark.value_counts().to_dict())
