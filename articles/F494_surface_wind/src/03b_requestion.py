"""問い直し：切れ目での段差は、どちら向きで、どの時期に多かったのか。
H2 で、段差を許すと傾きがむしろプラスに寄ったので、切れ目の段差の向きと時期を見る。あわせて、地点の平均からの差を年ごとにまとめる。"""
import json, os
import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
RES = os.path.join(HERE, "..", "results")
s = pd.read_csv(os.path.join(RES, "steps.csv"))
d = pd.read_csv(os.path.join(DATA, "annual_wind.csv"))

bins = [1960, 1975, 1990, 2005, 2025]
labs = ["1961〜1975年", "1976〜1990年", "1991〜2005年", "2006〜2025年"]
s["period"] = pd.cut(s["year"], bins, labels=labs)
per = s.groupby("period", observed=False)["step"].agg(n="count", median="median",
                                                       down=lambda x: int((x < 0).sum()), up=lambda x: int((x > 0).sum()))
per.round(3).to_csv(os.path.join(RES, "requestion_steps_by_period.csv"))

# 年ごとの、地点の平均からの差の中央値（そのまま、と段差を除いたもの）
d["anom"] = d["wind_mean"] - d.groupby("station")["wind_mean"].transform("mean")
d["anom_seg"] = d["wind_mean"] - d.groupby(["station", "seg_mean"])["wind_mean"].transform("mean")
yr = d.groupby("year")[["anom", "anom_seg"]].median()
yr.round(3).to_csv(os.path.join(RES, "requestion_yearly.csv"))

bt = stats.binomtest(int((s.step < 0).sum()), int((s.step != 0).sum()), 0.5)
out = {"n_steps": int(len(s)), "median_step": round(float(s.step.median()), 3),
       "down": int((s.step < 0).sum()), "up": int((s.step > 0).sum()), "sign_p": round(float(bt.pvalue), 3),
       "by_period": {k: {c: (round(float(v), 3) if c == "median" else int(v)) for c, v in row.items()} for k, row in per.iterrows()},
       "decade_anom_median": {f"{a}〜{b}": round(float(d.loc[(d.year >= a) & (d.year <= b), "anom"].median()), 3)
                              for a, b in ((1961, 1970), (1971, 1980), (1981, 1990), (1991, 2000), (2001, 2010), (2011, 2020), (2021, 2025))}}
with open(os.path.join(RES, "requestion.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
