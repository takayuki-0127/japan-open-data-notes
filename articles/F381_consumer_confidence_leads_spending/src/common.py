"""03・03b・04 で共通に使う、四半期の表の作り方。"""
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
COMP = {"kurashi": "暮らし向き", "shunyu": "収入の増え方", "koyo": "雇用環境", "kaidoki": "耐久消費財の買い時判断"}
# 消費税の引き上げの駆け込み・反動、感染症の時期（その四半期だけ1のダミー）
SHOCKS = {"tax1997": [(1997, 1), (1997, 2)], "tax2014": [(2014, 1), (2014, 2)],
          "tax2019": [(2019, 3), (2019, 4)], "covid": [(2020, 2), (2020, 3)]}


def quarterly():
    c = pd.read_csv(DATA / "cci_monthly.csv")
    c["q"] = (c["month"] + 2) // 3
    cols = ["cci"] + list(COMP)
    cq = c.groupby(["year", "q"], sort=True)[cols].mean().reset_index()   # 2004年3月までは四半期に1つの値なので、そのまま
    qe = pd.read_csv(DATA / "qe_quarterly.csv")
    d = qe.merge(cq, on=["year", "q"], how="left").sort_values(["year", "q"]).reset_index(drop=True)
    d["t"] = d["year"].astype(str) + "Q" + d["q"].astype(str)
    for v in ["hc_xrent", "hc", "pc", "durable", "services", "nondur", "semidur"]:
        d["g_" + v] = 100 * np.log(d[v]).diff()
    for v in cols:
        d["d_" + v] = d[v].diff()
    d["d_cci_brk"] = d["d_cci"].where(~((d.year == 2013) & (d.q == 2)))    # 2013年の調査方法の変更をまたぐ変化を除く
    for k, qs in SHOCKS.items():
        d["D_" + k] = [1.0 if (y, q) in qs else 0.0 for y, q in zip(d.year, d.q)]
    d["shock"] = d[[c for c in d.columns if c.startswith("D_")]].sum(axis=1)
    return d


def add_lags(d, cols, lags):
    d = d.copy()
    for c in cols:
        for L in lags:
            d[f"{c}_L{L}"] = d[c].shift(L)
    return d
