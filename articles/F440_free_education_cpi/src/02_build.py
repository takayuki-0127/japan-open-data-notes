"""02 整形（オフライン）：data/raw の CSV から、使う品目だけを抜き出して data/ に置く（3つの基準×月次・年平均）。"""
import csv, pathlib
from cpiload import series

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
CODES = ["0001", "0161", "8080", "8090", "9921", "8020", "8030", "8040", "8060", "8070", "8077", "0044", "0119"]


def main():
    for kind in ["monthly", "annual"]:
        rows = []
        for basis in ["2015", "2020", "2025"]:
            for r in series(RAW / f"cpi{basis}_item_{kind}.csv", CODES):
                r["basis"] = basis
                rows.append(r)
        with open(DATA / f"cpi_items_{kind}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["basis", "period", "code", "name", "weight", "value"], lineterminator="\n")
            w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
