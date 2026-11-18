"""02 整形（オフライン）：data/raw の CSV から、使う品目だけを抜き出して data/ に置く。"""
import csv, pathlib
from cpiload import series

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"

# 使う品目（符号）：POS で作る7品目、比べる家電など、総合
POS7 = ["9013", "9078", "9079", "9043", "9080", "9081", "9034"]
COMP = ["4021", "4042", "4063", "4032", "4003", "7446"]
AGG = ["0001", "0123", "0061"]
CODES = POS7 + COMP + AGG


def write(path, rows, cols):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    rows = []
    for basis, fn in [("2025", "cpi2025_item_annual.csv"), ("2020", "cpi2020_item_annual.csv"), ("2015", "cpi2015_item_annual.csv")]:
        for r in series(RAW / fn, CODES):
            r["basis"] = basis
            rows.append(r)
    write(DATA / "cpi_items_annual.csv", rows, ["basis", "period", "code", "name", "weight", "value"])

    m = [r for r in series(RAW / "cpi2025_item_monthly.csv", CODES)]
    write(DATA / "cpi_items_monthly_2025.csv", m, ["period", "code", "name", "weight", "value"])

    # 貿易統計：電算機類（含周辺機器）と電話機の金額（千円）と台数
    with open(RAW / "trade_import_world_annual.csv", encoding="cp932", newline="") as f:
        t = list(csv.reader(f))
    head = t[2]
    want = {"電算機類(含周辺機器)": "computers", "（電話機）": "phones"}
    out = []
    for r in t[7:]:
        if not r or not r[0].strip().isdigit():
            continue
        y = int(r[0].strip())
        for label, key in want.items():
            j = head.index(label)  # この列が数量、次の列が金額
            q, v = r[j].strip(), r[j + 1].strip()
            if q in ("", "-") or v in ("", "-"):
                continue
            out.append({"year": y, "item": key, "units": int(q), "value_thousand_yen": int(v)})
    write(DATA / "trade_units.csv", out, ["year", "item", "units", "value_thousand_yen"])


if __name__ == "__main__":
    main()
