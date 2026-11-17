"""02 整形：特殊分類の指数を取り出す。出力：data/cpi.csv"""
import csv, io, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"
CODES = {"0001": "headline", "0161": "core", "0178": "corecore", "0168": "us_core", "0167": "energy"}


def main():
    rows = list(csv.reader(io.StringIO((RAW / "cpi_item_monthly.csv").read_bytes().decode("cp932"))))
    pos = {CODES[c]: j for j, c in enumerate(rows[2]) if c in CODES}
    w = {k: float(rows[5][j]) for k, j in pos.items()}
    out = [{"ym": int(r[0]), **{k: (float(r[j]) if r[j].strip() else np.nan) for k, j in pos.items()}} for r in rows[6:] if r and r[0].isdigit()]
    d = pd.DataFrame(out).set_index("ym")
    d.to_csv(D / "cpi.csv")
    pd.Series(w, name="weight_per_10000").to_csv(D / "weights.csv")
    print(d.shape, w)


if __name__ == "__main__":
    main()
