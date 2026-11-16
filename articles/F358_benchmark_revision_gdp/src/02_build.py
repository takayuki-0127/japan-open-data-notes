"""二つの公表回の暦年 CSV（cp932）から、年×項目×新旧の縦長の表 data/vintages.csv を作る（オフライン）。"""
import pathlib, io, csv
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
ITEMS = [("国内総生産(支出側)", 2, "gdp"), ("民間最終消費支出", 2, "pce"), ("民間住宅", 2, "housing"), ("民間企業設備", 2, "business_inv"), ("民間在庫変動", 2, "private_inv_change"),
         ("政府最終消費支出", 2, "gov_cons"), ("公的固定資本形成", 2, "public_inv"), ("公的在庫変動", 2, "public_inv_change"), ("輸出", 3, "exports"), ("輸入", 3, "imports")]


def num(s):
    try:
        return float(str(s).replace(",", "").strip())
    except ValueError:
        return np.nan


def read(name):
    rows = list(csv.reader(io.StringIO((RAW / name).read_bytes().decode("cp932"))))
    cols = {}
    for jp, lev, key in ITEMS:
        idx = [i for i, h in enumerate(rows[lev]) if h.strip() == jp]
        if idx:
            cols[key] = idx[0]
    out = []
    for r in rows:
        if r and r[0].endswith("/1-12."):
            y = int(r[0][:4])
            for k, c in cols.items():
                out.append(dict(year=y, item=k, value=num(r[c])))
    return pd.DataFrame(out)


def main():
    parts = []
    for s, vint in [("2531", "2015年基準"), ("2532", "2020年基準")]:
        for kind, f in [("nominal", f"esri_gaku-mcy{s}.csv"), ("real", f"esri_gaku-jcy{s}.csv"), ("deflator", f"esri_def-cy{s}.csv")]:
            d = read(f); d["kind"] = kind; d["vintage"] = vint; parts.append(d)
    v = pd.concat(parts, ignore_index=True)
    v.to_csv(ROOT / "data" / "vintages.csv", index=False)
    print(v.groupby(["vintage", "kind"]).year.agg(["min", "max"]).to_string())


if __name__ == "__main__":
    main()
