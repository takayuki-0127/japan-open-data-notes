"""data/raw から整った CSV を作る（オフライン）。"""
import pathlib, io, csv, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"


def num(x):
    try:
        return float(str(x).replace(",", "").strip())
    except ValueError:
        return np.nan


def read_customs(fname):
    rows = list(csv.reader(io.StringIO((RAW / fname).read_bytes().decode("cp932"))))
    return rows


def commodity_table(fname, flow):
    rows = read_customs(fname)
    codes = rows[4]; names = rows[2]
    out = []
    for row in rows:
        if not row or not row[0].strip().isdigit():
            continue
        y = int(row[0].strip())
        out.append(dict(flow=flow, year=y, code="total", name="総額", value_kyen=num(row[1]), qty=np.nan))
        # 概況品コードの列 c に数量、c+1 に金額が並ぶ
        for c in range(2, len(codes) - 1):
            code = codes[c].strip()
            if code and code.startswith("'"):
                out.append(dict(flow=flow, year=y, code=code.strip("'").replace("'", ""), name=names[c].strip(),
                                value_kyen=num(row[c + 1]) if c + 1 < len(row) else np.nan, qty=num(row[c]) if c < len(row) else np.nan))
    return pd.DataFrame(out)


def boj(fname):
    j = json.loads((RAW / fname).read_text(encoding="utf-8"))
    rows = []
    for s in j["RESULTSET"]:
        for d, v in zip(s["VALUES"]["SURVEY_DATES"], s["VALUES"]["VALUES"]):
            rows.append(dict(series=s["SERIES_CODE"], name=s["NAME_OF_TIME_SERIES_J"], ym=int(d), value=v))
    return pd.DataFrame(rows)


def main():
    tot = read_customs("customs_world_total_yearly.csv")
    t = [dict(year=int(r[0].strip()), exports_kyen=num(r[1]), imports_kyen=num(r[2])) for r in tot if r and r[0].strip().isdigit()]
    pd.DataFrame(t).to_csv(OUT / "trade_totals.csv", index=False)
    cm = pd.concat([commodity_table("customs_world_imports_by_commodity_yearly.csv", "輸入"),
                    commodity_table("customs_world_exports_by_commodity_yearly.csv", "輸出")], ignore_index=True)
    cm = cm.drop_duplicates(["flow", "year", "code"], keep="first").sort_values(["flow", "code", "year"]).reset_index(drop=True)
    cm.to_csv(OUT / "trade_by_commodity.csv", index=False)
    b = pd.concat([boj("boj_usdjpy_monthly.json"), boj("boj_import_prices_monthly.json")], ignore_index=True)
    b["value"] = pd.to_numeric(b["value"], errors="coerce")
    b["year"] = b["ym"] // 100
    b.to_csv(OUT / "boj_monthly.csv", index=False)
    ann = b.groupby(["series", "year"])["value"].agg(["mean", "count"]).reset_index()
    ann = ann[ann["count"] == 12]
    ann.pivot(index="year", columns="series", values="mean").to_csv(OUT / "boj_annual.csv")
    print(cm[(cm.flow == "輸入") & (cm.year == 2020) & cm.code.isin(["3", "30301", "3050103", "30101", "total"])])


if __name__ == "__main__":
    main()
