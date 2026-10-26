"""02 整形：月次パネル data/monthly_panel.csv（変換後）と data/gdp_q.csv（前期比）を作る"""
import json
import numpy as np
import pandas as pd
from common import RAW, DATA, SERIES, START


def ci_table(key):
    d = json.loads((RAW / "f13_ci.json").read_text(encoding="utf-8"))
    rows = d[key]
    out = {}
    for r in rows:
        if len(r) > 3 and isinstance(r[1], (int, float)) and isinstance(r[2], (int, float)):
            out[pd.Timestamp(int(r[1]), int(r[2]), 1)] = r
    return out


def main():
    tabs = {"ci2": ci_table("1026ci2.xlsx"), "ci1": ci_table("1026ci1.xlsx")}
    f13 = pd.read_csv(RAW / "f13_monthly.csv", parse_dates=["month"]).set_index("month")
    raw, tr = {}, {}
    for name, src, col, how, lag, grp in SERIES:
        if src == "f13":
            s = f13[col].astype(float)
        else:
            s = pd.Series({t: (float(r[col]) if col < len(r) and isinstance(r[col], (int, float)) else np.nan)
                           for t, r in tabs[src].items()})
        s = s.sort_index()
        raw[name] = s
        if how == "dlog":
            x = 100 * np.log(s).diff()
        elif how == "diff":
            x = s.diff()
        else:
            x = s
        tr[name] = x
    raw = pd.DataFrame(raw)
    panel = pd.DataFrame(tr)
    # 消費者態度指数は 2001年10月以前は四半期の値を線形補間したもの → 2001年11月より前は欠測にする
    panel.loc[:"2001-11-01", "消費者態度指数"] = np.nan
    panel = panel.loc[START:]
    panel.index.name = "month"
    panel.to_csv(DATA / "monthly_panel.csv")
    raw.loc[START:].to_csv(DATA / "monthly_levels.csv", index_label="month")

    g = pd.read_csv(RAW / "gdp_real_sa.csv")
    g["q"] = pd.PeriodIndex(g["quarter"], freq="Q")
    g = g.set_index("q")["gdp_real_sa"]
    gq = 100 * np.log(g).diff()
    gq.index = gq.index.to_timestamp(how="end").normalize().to_period("M").to_timestamp()  # 四半期の最後の月
    gq.name = "gdp_qoq"
    gq.dropna().to_csv(DATA / "gdp_q.csv", index_label="month")
    print(panel.tail(3).T)
    print("panel", panel.shape, panel.index.min(), panel.index.max(), "gdp", gq.dropna().shape, gq.index.max())
    print(panel.notna().sum())


if __name__ == "__main__":
    main()
