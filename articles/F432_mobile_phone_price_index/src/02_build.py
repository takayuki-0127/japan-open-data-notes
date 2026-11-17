"""02 整形：品目別価格指数から 携帯電話機・通信料（携帯電話）・通信料（固定電話）・通信・総合 を取り出し、ドル円とつなぐ。
品目は「類・品目符号」で選ぶ。出力：data/monthly.csv
"""
import csv, io, pathlib
import numpy as np
import pandas as pd
from bojload import load

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"
CODES = {"7446": "phone_device", "7430": "mobile_fee", "7410": "fixed_fee", "0117": "communication", "0001": "all"}


def main():
    rows = list(csv.reader(io.StringIO((RAW / "cpi_item_monthly.csv").read_bytes().decode("cp932"))))
    pos = {CODES[c]: j for j, c in enumerate(rows[2]) if c in CODES}
    assert len(pos) == len(CODES)
    out = []
    for r in rows[6:]:
        if r and r[0].isdigit():
            out.append({"ym": int(r[0]), **{k: (float(r[j]) if r[j].strip() else np.nan) for k, j in pos.items()}})
    d = pd.DataFrame(out).set_index("ym")
    d = d.join(load(RAW / "boj_usdjpy_monthly.json")["FXERM07"].rename("usdjpy"))
    d.loc[200001:].to_csv(D / "monthly.csv")


if __name__ == "__main__":
    main()
