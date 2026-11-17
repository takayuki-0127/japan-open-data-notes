"""02_build.py : 家計調査 長期時系列 表2（勤労者世帯・月）の xlsx を、縦長の CSV に直す（オフライン）。
出力：data/monthly_long.csv（item, year, month, value）と data/items.csv（行の一覧）。
"""
import pathlib
import openpyxl
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "kakei_longterm_workers_monthly.xlsx"


def main():
    wb = openpyxl.load_workbook(RAW, read_only=True)
    rows = list(wb["支出金額（月）"].iter_rows(values_only=True))
    # 列の年月：行9 に年（12列ごと）、行11 に月
    year, cols = None, []
    for j in range(16, len(rows[11])):
        if rows[9][j]:
            year = int(str(rows[9][j]).replace("年", ""))
        m = rows[11][j]
        if m is None:
            continue
        cols.append((j, year, int(str(m).replace("　", "").replace("月", ""))))
    recs, items = [], []
    for i in range(13, len(rows)):
        r = rows[i]
        label = "|".join(str(c).strip() for c in r[6:16] if c is not None and str(c).strip())
        if not label or label.startswith("注") or (r[5] is None and label[:1].isdigit() and ")" in label[:3]):
            continue
        key = f"r{i:03d}"
        items.append({"key": key, "code": r[5], "label": label})
        for j, y, m in cols:
            v = r[j]
            if isinstance(v, (int, float)):
                recs.append((key, y, m, float(v)))
    items = pd.DataFrame(items)
    items.to_csv(ROOT / "data" / "items.csv", index=False)
    df = pd.DataFrame(recs, columns=["key", "year", "month", "value"]).sort_values(["key", "year", "month"])
    df.to_csv(ROOT / "data" / "monthly_long.csv", index=False)
    print(len(items), len(df), df.year.min(), df.year.max())


if __name__ == "__main__":
    main()
