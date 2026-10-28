"""02 整形：F18 の月次パネル（20系列、変換済み）と四半期 GDP 前期比を、そのまま使える形にして data/ に置く。
変換は F18 と同じ（指数は前月比＝対数差×100、倍率・指数・金利・失業率は前月差、前年比のものはそのまま）。"""
import pandas as pd
from common import RAW, DATA, ALL

if __name__ == "__main__":
    p = pd.read_csv(RAW / "monthly_panel.csv", parse_dates=["month"])
    p["month"] = p["month"].dt.to_period("M").astype(str)
    p = p[["month"] + ALL]
    p.to_csv(DATA / "panel_monthly.csv", index=False)
    g = pd.read_csv(RAW / "gdp_q.csv", parse_dates=["month"])
    g["quarter"] = g["month"].dt.to_period("Q").astype(str)
    g[["quarter", "gdp_qoq"]].to_csv(DATA / "gdp_quarterly.csv", index=False)
    print(p.shape, g.shape, p.month.min(), p.month.max(), g.quarter.min(), g.quarter.max())
