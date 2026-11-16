"""02 整形：月次（1996〜2026年9月）と年次（1985〜2013年、組替）を表にし、暦年の表を作る。
- 1996〜2025年は月次の合計。1985〜1995年は年次の組替の値。単位は億円。
- ドル建ては、月ごとの値をその月のドル円（月中平均）で割って合計（億ドル）。
出力：data/monthly.csv, data/annual.csv
"""
import pathlib
import numpy as np
import pandas as pd
from bojload import load

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"
NAME = {"BPBP6JYNCB": "ca", "BPBP6JYNTB": "trade", "BPBP6JYNEX": "exports", "BPBP6JYNIM": "imports", "BPBP6JYNSN": "services",
        "BPBP6JYNPIN": "primary", "BPBP6JYNPIC": "primary_rec", "BPBP6JYNPID": "primary_pay", "BPBP6JYNSIN": "secondary",
        "BPBP6JYNPIN1": "comp_employees", "BPBP6JYNPIN2": "invest_income", "BPBP6JYNPIN21": "di_income",
        "BPBP6JYNPIN2111": "di_dividends", "BPBP6JYNPIN2112": "di_reinvested", "BPBP6JYNPIN212": "di_interest",
        "BPBP6JYNPIN22": "portfolio_income", "BPBP6JYNPIN221": "pf_dividends", "BPBP6JYNPIN222": "pf_bond_interest",
        "BPBP6JYNPIN29": "other_invest_income", "BPBP6JYNPIN9": "other_primary"}
ANAME = {"BPBP6RACYJYNCB": "ca", "BPBP6RACYJYNTS": "trade_services", "BPBP6RACYJYNTB": "trade", "BPBP6RACYJYNSN": "services",
         "BPBP6RACYJYNPIN": "primary", "BPBP6RACYJYNSIN": "secondary"}


def main():
    m = load(RAW / "boj_bop_monthly.json").rename(columns=NAME)
    fx = load(RAW / "boj_usdjpy_monthly.json")["FXERM07"].rename("usdjpy")
    m = m.join(fx, how="left")
    m.index.name = "ym"
    m["year"] = m.index // 100
    m["trade_services"] = m.trade + m.services
    m.round(4).to_csv(D / "monthly.csv")
    full = m[m.year <= 2025]
    assert full.groupby("year").size().eq(12).all()
    cols = [c for c in NAME.values()] + ["trade_services"]
    ay = full.groupby("year")[cols].sum(min_count=12)
    usd = full[cols].div(full.usdjpy, axis=0)
    usd["year"] = full.year
    ay_usd = usd.groupby("year")[cols].sum(min_count=12).add_suffix("_usd")
    ay = ay.join(ay_usd)
    ay["usdjpy"] = full.groupby("year").usdjpy.mean()
    ay["source"] = "monthly_sum"
    old = load(RAW / "boj_bop_annual_1985_2013.json").rename(columns=ANAME)
    old.index.name = "year"
    pre = old.loc[1985:1995].copy()
    fxy = fx.groupby(fx.index // 100).mean()
    for c in ANAME.values():
        pre[c + "_usd"] = pre[c] / fxy.loc[pre.index]
    pre["usdjpy"] = fxy.loc[pre.index]
    pre["source"] = "annual_reorganized"
    a = pd.concat([pre, ay]).sort_index()
    a.index.name = "year"
    a.round(4).to_csv(D / "annual.csv")
    # 重なる年の差（頑健性4用）
    ov = old.loc[1996:2013, ["ca", "trade", "primary"]].join(ay.loc[1996:2013, ["ca", "trade", "primary"]], rsuffix="_m")
    ov.round(4).to_csv(D / "overlap_check.csv")
    print(a[["ca", "trade", "services", "primary", "secondary"]].tail(3)); print((ov.trade - ov.trade_m).abs().max(), (ov.primary - ov.primary_m).abs().max())


if __name__ == "__main__":
    main()
