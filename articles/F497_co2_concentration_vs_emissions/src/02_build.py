"""data/raw から、月の表 data/monthly.csv（地点×年月の CO2 濃度）、NINO.3 の月の表 data/nino3.csv、
日本の CO2 排出量の年度の表 data/emissions.csv を作る。ネットにはつながない。"""
import pathlib, re, io, html
import numpy as np
import pandas as pd
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
rows = []
for code, name in [("ryo", "綾里"), ("mnm", "南鳥島"), ("yon", "与那国島")]:
    t = (RAW / f"co2_monthave_{code}.csv").read_bytes().decode("cp932")
    for line in t.splitlines():
        m = re.match(r"^(\d{4}),\s*(\d+),\s*([^,]*),\s*(\)?)", line)
        if m:
            v = m.group(3).strip()
            rows.append({"station": name, "year": int(m.group(1)), "month": int(m.group(2)),
                         "co2": float(v) if re.match(r"^\d+(\.\d+)?$", v) else np.nan, "prelim": int(m.group(4) == ")")})
M = pd.DataFrame(rows)
M.to_csv(ROOT / "data" / "monthly.csv", index=False)

t = re.sub(r"<[^>]+>", " ", html.unescape((RAW / "nino3idx.html").read_text(encoding="utf-8", errors="replace")))
nr = []
for line in t.splitlines():
    p = line.split()
    if len(p) == 13 and re.match(r"^\d{4}$", p[0]):
        for i, v in enumerate(p[1:], start=1):
            try:
                nr.append({"year": int(p[0]), "month": i, "nino3": float(v)})
            except ValueError:
                pass
pd.DataFrame(nr).to_csv(ROOT / "data" / "nino3.csv", index=False)

wb = openpyxl.load_workbook(str(RAW / "L5-7gas_2026_gioweb_ver1.0.xlsx"), read_only=True, data_only=True)
S = [list(r) for r in wb["1.Summary"].iter_rows(values_only=True)]
years = [int(y) for y in S[3][26:] if isinstance(y, (int, float))]
cols = list(range(26, 26 + len(years)))
lab = re.sub(r"\s", "", str(S[4][18])) + "|" + re.sub(r"\s", "", str(S[4][19]))
E = pd.DataFrame({"fy": years, "co2_total_Mt": [float(S[4][c]) for c in cols]})
E.to_csv(ROOT / "data" / "emissions.csv", index=False)
print(M.groupby("station").year.agg(["min", "max"]), len(nr), lab, E.iloc[[0, 23, -1]].to_dict("records"))
