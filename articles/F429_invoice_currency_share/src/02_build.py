"""02 整形：通貨別比率（長い形）、地域別の輸出額（半期）、ドル円（半期平均）。
半期の名前：2000Jul.-Dec. → 2000H2、2001Jan.-Jun. → 2001H1。
出力：data/currency_long.csv, data/exports_half.csv, data/fx_half.csv
"""
import csv, io, pathlib
import pandas as pd
from bojload import load

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"
AREAS = {"d51ma": "WORLD", "d52ma001": "USA", "d52ma002": "EU", "d52ma003": "ASIA"}


def half(p):
    y = int(p[:4]); return f"{y}H1" if "Jan" in p else f"{y}H2"


def main():
    rows = []
    for k, flow in [("e", "export"), ("i", "import")]:
        d = pd.read_csv(RAW / f"timeseriesSCT_{k}.csv", skiprows=4, encoding="cp932")
        for _, r in d.iterrows():
            for n in ["1st", "2nd", "3rd", "4th", "5th", "OTH"]:
                rows.append((flow, half(r["Year & Month"]), r.Area.strip(), r[f"currency_{n}"], float(r[f"share_{n}"])))
    c = pd.DataFrame(rows, columns=["flow", "half", "area", "currency", "share"])
    c.to_csv(D / "currency_long.csv", index=False)
    ex = []
    for f, area in AREAS.items():
        rr = list(csv.reader(io.StringIO((RAW / f"{f}.csv").read_bytes().decode("cp932"))))
        for r in rr[7:]:
            if len(r) < 2 or "/" not in r[0]:
                continue
            v = r[1].strip()
            if v in ("", "-"):
                continue
            y, mth = int(r[0][:4]), int(r[0][5:7])
            ex.append((area, f"{y}H{1 if mth <= 6 else 2}", y * 100 + mth, int(v)))
    e = pd.DataFrame(ex, columns=["area", "half", "ym", "value"])
    n = e.groupby(["area", "half"]).ym.count()
    e = e.groupby(["area", "half"]).value.sum()[n == 6].unstack(0)
    e["OTHER"] = e.WORLD - e.USA - e.EU - e.ASIA
    e.index.name = "half"
    e.to_csv(D / "exports_half.csv")
    fx = load(RAW / "boj_usdjpy_monthly.json")["FXERM07"]
    h = [f"{i // 100}H{1 if i % 100 <= 6 else 2}" for i in fx.index]
    fx.groupby(h).mean().rename("usdjpy").rename_axis("half").round(4).to_csv(D / "fx_half.csv")
    print(c.half.nunique(), e.shape)


if __name__ == "__main__":
    main()
