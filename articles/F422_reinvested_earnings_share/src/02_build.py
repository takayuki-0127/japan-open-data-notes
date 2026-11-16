"""02 整形：月次の JSON から月次の表と暦年（1996〜2025年）の表を作る（単位：億円）。
出力：data/monthly.csv, data/annual.csv
"""
import pathlib
import pandas as pd
from bojload import load

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"
NAME = {"BPBP6JYNCB": "ca", "BPBP6JYNTB": "trade", "BPBP6JYNPIN": "primary", "BPBP6JYNPIC": "primary_rec",
        "BPBP6JYNPIC21": "di_rec", "BPBP6JYNPIC2111": "di_div_rec", "BPBP6JYNPIC2112": "di_reinv_rec", "BPBP6JYNPIC212": "di_int_rec",
        "BPBP6JYNPID21": "di_pay", "BPBP6JYNPID2111": "di_div_pay", "BPBP6JYNPID2112": "di_reinv_pay", "BPBP6JYNPID212": "di_int_pay",
        "BPBP6JYNPIC22": "pf_rec", "BPBP6JYNPIC29": "oth_rec", "BPBP6JYNFA132": "fa_reinv_asset"}


def main():
    m = load(RAW / "boj_bop_monthly.json").rename(columns=NAME)
    m = m.join(load(RAW / "boj_usdjpy_monthly.json")["FXERM07"].rename("usdjpy"))
    m.index.name = "ym"
    m["year"] = m.index // 100
    m.round(4).to_csv(D / "monthly.csv")
    full = m[m.year <= 2025]
    assert full.groupby("year").size().eq(12).all()
    cols = list(NAME.values())
    a = full.groupby("year")[cols].sum(min_count=12)
    usd = full[cols].div(full.usdjpy, axis=0); usd["year"] = full.year
    a = a.join(usd.groupby("year")[["di_rec", "di_div_rec", "di_reinv_rec"]].sum().add_suffix("_usd"))
    a["usdjpy"] = full.groupby("year").usdjpy.mean()
    a.round(4).to_csv(D / "annual.csv")


if __name__ == "__main__":
    main()
