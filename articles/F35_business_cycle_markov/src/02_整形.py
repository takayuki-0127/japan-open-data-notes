"""02 整形：CI一致指数と鉱工業生産指数から、前月比（対数差×100）と3か月前比を作る"""
import numpy as np
import pandas as pd
from common import RAW, DATA, recession_flag

d = pd.read_csv(RAW / "ci_iip_monthly.csv", parse_dates=["month"]).set_index("month")
out = pd.DataFrame(index=d.index)
for col, name in (("ci_coin", "ci"), ("iip", "iip")):
    lv = np.log(d[col])
    out[f"{name}_level"] = d[col]
    out[f"{name}_m1"] = 100 * lv.diff()          # 前月比
    out[f"{name}_m3"] = 100 * (lv - lv.shift(3)) / 3  # 3か月前比（月あたり）
out["recession"] = recession_flag(out.index)
out.to_csv(DATA / "monthly.csv")
print(out.dropna(subset=["ci_m1"]).index.min(), out.index.max(), "後退期の月:", int(out.recession.sum()))
