"""data/raw の Excel から、整った CSV を data/ に作る（オフライン）。"""
import pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"


def num(x):
    if pd.isna(x):
        return np.nan
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    s = str(x).strip().replace(",", "")
    if s in ("-", "－"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return np.nan


def label(x):
    s = str(x)
    m = re.search(r"\((\d{4})\)", s)
    if not m:
        return None, None
    v = "旧" if "旧" in s else ("新" if "新" in s else "")
    return int(m.group(1)), v


def herd(fname, region):
    d = pd.read_excel(RAW / fname, header=None)
    rows = []
    for i in range(9, len(d)):
        y, v = label(d.iat[i, 0])
        if y is None:
            continue
        rows.append(dict(region=region, year=y, version=v, farms=num(d.iat[i, 1]), female_total=num(d.iat[i, 2]),
                         age2plus=num(d.iat[i, 3]), parous=num(d.iat[i, 4]), milking=num(d.iat[i, 5]), dry=num(d.iat[i, 6]),
                         heifers=num(d.iat[i, 7]), under2=num(d.iat[i, 8]), per_farm_table=num(d.iat[i, 9])))
    return rows


def main():
    rows = herd("dairy_herd_national_1960_2025.xlsx", "全国") + herd("dairy_herd_hokkaido_1960_2025.xlsx", "北海道") + \
        herd("dairy_herd_tofuken_1960_2025.xlsx", "都府県")
    h = pd.DataFrame(rows).sort_values(["region", "year", "version"]).reset_index(drop=True)
    h.to_csv(OUT / "dairy_herd.csv", index=False)

    d = pd.read_excel(RAW / "raw_milk_production_1985_2024.xlsx", header=None)
    pr = []
    for i in range(6, len(d)):
        y, _ = label(d.iat[i, 0])
        if y is None:
            continue
        pr.append(dict(year=y, milk_t=num(d.iat[i, 1]), **{f"m{k:02d}": num(d.iat[i, 1 + k]) for k in range(1, 13)}))
    pd.DataFrame(pr).to_csv(OUT / "raw_milk_production.csv", index=False)

    # 規模別の成畜頭数（全国）：100頭以上＝2019年までは「100頭以上」列、2020年からは「100〜199」＋「200頭以上」
    d = pd.read_excel(RAW / "dairy_adults_by_size_national.xlsx", header=None)
    sz = []
    for i in range(7, len(d)):
        y, v = label(d.iat[i, 0])
        if y is None:
            continue
        tot = num(d.iat[i, 1]); c100 = num(d.iat[i, 19]); c100_199 = num(d.iat[i, 17]); c200 = num(d.iat[i, 20])
        ge100 = c100 if not np.isnan(c100) else (c100_199 + c200 if not (np.isnan(c100_199) or np.isnan(c200)) else np.nan)
        sz.append(dict(year=y, version=v, adults_total=tot, ge100=ge100, ge200=c200, ge300=num(d.iat[i, 21]),
                       c50_79=num(d.iat[i, 15]), c80_99=num(d.iat[i, 16])))
    pd.DataFrame(sz).to_csv(OUT / "dairy_adults_by_size.csv", index=False)

    d = pd.read_excel(RAW / "dairy_farms_by_size_national.xlsx", header=None)
    fs = []
    for i in range(7, len(d)):
        y, v = label(d.iat[i, 0])
        if y is None:
            continue
        c100 = num(d.iat[i, 32]); c100_199 = num(d.iat[i, 27]); c200 = num(d.iat[i, 33])
        ge100 = c100 if not np.isnan(c100) else (c100_199 + c200 if not (np.isnan(c100_199) or np.isnan(c200)) else np.nan)
        fs.append(dict(year=y, version=v, farms_total=num(d.iat[i, 1]), farms_with_adults=num(d.iat[i, 3]), farms_ge100=ge100))
    pd.DataFrame(fs).to_csv(OUT / "dairy_farms_by_size.csv", index=False)
    print(h.groupby("region").size(), len(pr), len(sz), len(fs))


if __name__ == "__main__":
    main()
