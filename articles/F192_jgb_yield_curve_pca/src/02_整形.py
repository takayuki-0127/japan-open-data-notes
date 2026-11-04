"""和暦の日付を西暦に直し、年限ごとの日次金利（%）の表にする。"""
import pathlib, datetime as dt
import pandas as pd, numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data"
ERA = {"S": 1925, "H": 1988, "R": 2018}

def conv(s):
    e, rest = s[0], s[1:]
    y, m, d = map(int, rest.split("."))
    return dt.date(ERA[e] + y, m, d)

rows = []
for f in ["jgbcm_all.csv", "jgbcm_current.csv"]:
    for line in (RAW / f).read_text(encoding="utf-8").splitlines():
        if line[:1] in ERA and line[1:2].isdigit():
            c = line.split(",")
            rows.append([conv(c[0])] + [np.nan if v in ("-", "", "*") else float(v) for v in c[1:16]])
cols = ["date"] + [f"y{m}" for m in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30, 40)]
df = pd.DataFrame(rows, columns=cols).drop_duplicates("date").sort_values("date")
df.to_csv(OUT / "jgb_yields_daily.csv", index=False)
print(len(df), df.date.min(), df.date.max())
print(df.set_index("date").apply(lambda s: s.first_valid_index()))
