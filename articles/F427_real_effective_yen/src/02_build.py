"""02 整形：月次の表（名目・実質・相対物価・旧系列・ドル円）を作る。
相対物価＝実質÷名目×100（2020年＝100）。旧系列は2010年1月まで。
出力：data/monthly.csv
"""
import pathlib
import numpy as np
import pandas as pd
from bojload import load

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"


def main():
    e = load(RAW / "boj_effective_monthly.json").rename(columns={"FX180110001": "neer", "FX180110002": "reer", "FXCP7JP": "neer_old", "FXCP8JP": "reer_old"})
    e = e.join(load(RAW / "boj_usdjpy_monthly.json")["FXERM07"].rename("usdjpy"))
    e.index.name = "ym"
    e["relprice"] = e.reer / e.neer * 100
    e["relprice_old"] = e.reer_old / e.neer_old * 100
    e.round(4).to_csv(D / "monthly.csv")
    print(e.describe().T[["count", "min", "max"]])


if __name__ == "__main__":
    main()
