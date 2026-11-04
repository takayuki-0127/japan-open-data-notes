"""両方の値がある日だけを残し、日次・週次の対数収益率を作る（data/returns_*.csv は日経平均由来のためリポジトリには入れない）。"""
import numpy as np
import pandas as pd
from common import RAW, DATA, START, END

fx = pd.read_csv(RAW / "boj_fm08_fxerd04.csv", dtype=str)
fx["date"] = pd.to_datetime(fx.date, format="%Y%m%d"); fx["usdjpy"] = pd.to_numeric(fx.usdjpy_1700, errors="coerce")
nk = pd.read_csv(RAW / "fred_nikkei225.csv")
nk["date"] = pd.to_datetime(nk.observation_date); nk["nikkei"] = pd.to_numeric(nk.NIKKEI225, errors="coerce")
df = fx[["date", "usdjpy"]].merge(nk[["date", "nikkei"]], on="date").dropna().sort_values("date")
df = df[(df.date >= START) & (df.date <= END)].reset_index(drop=True)
d = pd.DataFrame({"date": df.date[1:].values,
                  "r_fx": 100 * np.diff(np.log(df.usdjpy.values)),   # +＝円安
                  "r_nk": 100 * np.diff(np.log(df.nikkei.values))})  # +＝株高
d["gap_days"] = df.date.diff().dt.days[1:].values
d.to_csv(DATA / "returns_daily.csv", index=False)
w = df.set_index("date").resample("W-FRI").last().dropna()
wk = pd.DataFrame({"date": w.index[1:], "r_fx": 100 * np.diff(np.log(w.usdjpy.values)),
                   "r_nk": 100 * np.diff(np.log(w.nikkei.values))})
wk.to_csv(DATA / "returns_weekly.csv", index=False)
print(len(df), len(d), len(wk), d.date.min().date(), d.date.max().date())
