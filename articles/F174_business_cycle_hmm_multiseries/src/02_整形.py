"""02 整形：3か月前比（対数差×100÷3、%/月）と公式の後退期の印を作る → data/monthly.csv"""
import numpy as np, pandas as pd
from common import RAW, DATA

RATE = ["C6", "C7"]          # 前年同月比（%）の系列は差をとる
DIFF = ["L6"]                 # 消費者態度指数も差をとる

def official_recession(index, cyc):
    rec = pd.Series(0, index=index)
    peaks = cyc[cyc.type == "peak"].month.tolist()
    troughs = cyc[cyc.type == "trough"].month.tolist()
    for p in peaks:
        t = min([x for x in troughs if x > p])
        rec[(rec.index > p) & (rec.index <= t)] = 1   # 山の翌月〜谷
    return rec

if __name__ == "__main__":
    raw = pd.read_csv(RAW / "ci_series_monthly.csv", parse_dates=["month"]).set_index("month")
    cyc = pd.read_csv(RAW / "cycle_dates.csv")
    cyc["month"] = pd.to_datetime(cyc.month + "-01")
    out = pd.DataFrame(index=raw.index)
    for c in raw.columns:
        x = raw[c]
        for h in (3, 6):
            if c in RATE or c in DIFF:
                out[f"g{h}_{c}"] = (x - x.shift(h)) / h
            else:
                out[f"g{h}_{c}"] = (np.log(x) - np.log(x.shift(h))) * 100 / h
    out["rec"] = official_recession(out.index, cyc)
    out.to_csv(DATA / "monthly.csv", float_format="%.5f")
    print(out.shape, out.index.min(), out.index.max(), int(out.rec.sum()))
