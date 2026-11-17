"""data/raw の Excel を整形して data/ に CSV を作る。
- data/pref_use.csv：2018・2023年、全国・都道府県・政令市 × 利用現況(6区分)
- data/pref_acq.csv：2018・2023年、全国・都道府県・政令市 × 取得方法(5区分)
- data/japan_long.csv：2008・2013・2018・2023年 全国の総数と「利用していない」
数値は世帯数・所有件数・1件当たり面積（総数・持ち家・借家（持ち家以外））。
"""
import pathlib, re
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
VAL = ["hh_total", "hh_own", "hh_rent", "lots_total", "lots_own", "lots_rent", "area_total", "area_own", "area_rent"]


def num(v):
    return pd.to_numeric(str(v).replace(",", "").strip(), errors="coerce")


def parse_pref(path, year, c_code, c_reg, c_cat, c_val):
    d = pd.read_excel(path, header=None)
    rows = []
    for i in range(len(d)):
        r = d.iloc[i].tolist()
        reg = str(r[c_reg])
        if not re.match(r"^\d{5}_", reg):
            continue
        vals = [num(v) for v in r[c_val:c_val + 9]]
        rows.append([year, str(r[c_code]), reg[:5], reg[6:], str(r[c_cat]).strip()] + vals)
    return pd.DataFrame(rows, columns=["year", "level", "code", "region", "category"] + VAL)


def find_row(d, key, nth=0):
    hits = []
    for i in range(len(d)):
        s = re.sub(r"[\s　]", "", "".join(str(v) for v in d.iloc[i, :9].tolist()))
        if key in s and isinstance(d.iloc[i, 10], (int, float)):
            hits.append(i)
    return [num(v) for v in d.iloc[hits[nth], 10:19].tolist()]


def main():
    use = pd.concat([parse_pref(RAW / "hl2018_t253_2_use_pref.xlsx", 2018, 4, 5, 7, 8),
                     parse_pref(RAW / "hl2023_t252_2_use_pref.xlsx", 2023, 0, 1, 2, 3)])
    acq = pd.concat([parse_pref(RAW / "hl2018_t250_acq_pref.xlsx", 2018, 4, 5, 7, 8),
                     parse_pref(RAW / "hl2023_t249_acq_pref.xlsx", 2023, 0, 1, 2, 3)])
    for df in (use, acq):
        df["level"] = df["level"].map({"a": "pref", "1": "city"})
        assert df["level"].notna().all()
    use.to_csv(DATA / "pref_use.csv", index=False)
    acq.to_csv(DATA / "pref_acq.csv", index=False)

    # 全国の長期（総数と、利用していない土地）
    rows = []
    for y, f in [(2008, "hl2008_t145_japan.xls"), (2013, "hl2013_t172_japan.xls")]:
        d = pd.read_excel(RAW / f, header=None)
        rows.append([y, "総数"] + find_row(d, "総数"))
        rows.append([y, "利用していない（空き地・原野など）"] + find_row(d, "利用していない"))
    for y, f, cc in [(2018, "hl2018_t253_1_use_japan.xlsx", (6, 7)), (2023, "hl2023_t252_1_use_japan.xlsx", (1, 2))]:
        d = pd.read_excel(RAW / f, header=None)
        for i in range(len(d)):
            cat = str(d.iloc[i, cc[0]]).strip()
            if re.match(r"^\d+_", cat):
                rows.append([y, cat.split("_", 1)[1]] + [num(v) for v in d.iloc[i, cc[1]:cc[1] + 9].tolist()])
    jp = pd.DataFrame(rows, columns=["year", "category"] + VAL)
    jp.to_csv(DATA / "japan_long.csv", index=False)
    print(len(use), len(acq), len(jp))


if __name__ == "__main__":
    main()
