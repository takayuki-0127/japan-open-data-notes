"""02 整形：財・サービス分類指数（月次）から使う区分を取り出し、前年比・前月比を付ける。
出力：data/cpi_monthly.csv
"""
import csv, io, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"
USE = {"0201": "all", "0202": "goods", "0241": "goods_ex_fresh", "0214": "petroleum", "0218": "utilities", "0207": "industrial",
       "0208": "food_products", "0220": "services", "0242": "services_ex_rent", "0221": "public_services", "0228": "general_services",
       "0229": "eating_out", "0230": "private_rent", "0231": "imputed_rent", "0232": "other_services"}


def main():
    rows = list(csv.reader(io.StringIO((RAW / "cpi_goods_services_monthly.csv").read_bytes().decode("cp932"))))
    codes = rows[2]
    cols = {j: USE[c] for j, c in enumerate(codes) if c in USE}
    out = []
    for r in rows[6:]:
        if not r or not r[0].isdigit():
            continue
        rec = {"ym": int(r[0])}
        for j, n in cols.items():
            rec[n] = float(r[j]) if r[j].strip() else np.nan
        out.append(rec)
    d = pd.DataFrame(out).set_index("ym").sort_index()
    d.to_csv(D / "cpi_monthly.csv")
    print(d.shape, d.index.min(), d.index.max())


if __name__ == "__main__":
    main()
