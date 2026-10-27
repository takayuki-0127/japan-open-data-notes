"""02 整形：5系列の原数値・季節調整値と、4つの見方（前年比・前月比・3か月前比・3か月平均の前月比）を作る"""
import pandas as pd
from common import RAW, DATA, SERIES, indicators

if __name__ == "__main__":
    s = pd.read_csv(RAW / "f42_series.csv", parse_dates=["date"])
    ci = pd.read_csv(RAW / "f35_ci_iip_monthly.csv", parse_dates=["month"]).rename(columns={"month": "date"})
    rows, lv = [], []
    for name, (kind, sign) in SERIES.items():
        if name.startswith("景気動向指数"):
            d = ci[["date", "ci_coin"]].dropna().set_index("date")
            nsa, sa = None, d["ci_coin"]
        else:
            d = s[s.series == name].set_index("date").sort_index()
            nsa, sa = d["nsa"], d["sa_pub"]
        lv.append(pd.DataFrame({"date": sa.index, "series": name, "nsa": None if nsa is None else nsa.values, "sa": sa.values}))
        ind = indicators(nsa, sa, kind, sign)
        ind["series"] = name
        rows.append(ind.reset_index().rename(columns={"index": "date"}))
    levels = pd.concat(lv)
    ind = pd.concat(rows)
    levels.to_csv(DATA / "levels.csv", index=False)
    ind.to_csv(DATA / "indicators.csv", index=False)
    print(ind.groupby("series").date.agg(["min", "max", "count"]))
