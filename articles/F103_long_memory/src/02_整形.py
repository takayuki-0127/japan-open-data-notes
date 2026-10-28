"""整形：電力需要は「気温・暦で説明できない部分（残差）」、物価は「季節を除いた前月比」を作る"""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from common import RAW, DATA

# ---------- 電力需要（日次） ----------
FORM = ("log_d ~ cr(temp_mean, df=8) + C(dow) + holiday + obon + nenmatsu + gw + covid + C(month)")
out = []
for area, fn in [("東京", "daily_tokyo_f67.csv.gz"), ("関西", "daily_kansai_f67.csv.gz")]:
    d = pd.read_csv(RAW / fn, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    d = d[d["n"] == 24].copy()
    full = pd.date_range(d["date"].min(), d["date"].max())
    assert len(full) == len(d), (area, len(full), len(d))  # 欠けた日がないこと
    for spec, f in [("暦と気温", FORM), ("暦と気温＋年度", FORM + " + C(fy)")]:
        m = smf.ols(f, data=d).fit()
        out.append(pd.DataFrame({"date": d["date"], "area": area, "spec": spec,
                                 "log_d": d["log_d"], "resid": m.resid, "temp_mean": d["temp_mean"]}))
        print(area, spec, "日数", len(d), "R2", round(m.rsquared, 3))
pw = pd.concat(out)
pw.to_csv(DATA / "power_resid.csv", index=False)

# ---------- 消費者物価（中分類・月次） ----------
raw = pd.read_csv(RAW / "cpi_chubunrui_f12.csv.gz", header=None, dtype=str)
names = raw.iloc[0, 1:].tolist()
weights = pd.to_numeric(raw.iloc[5, 1:], errors="coerce").tolist()
body = raw.iloc[6:].copy()
body.columns = ["ym"] + names
body["month"] = pd.to_datetime(body["ym"], format="%Y%m")
lv = body.set_index("month")[names].apply(pd.to_numeric, errors="coerce")
pd.DataFrame({"name": names, "weight10000": weights}).to_csv(DATA / "cpi_items.csv", index=False)
# 前月比（対数差、%）
mom = 100 * np.log(lv).diff()
mom.to_csv(DATA / "cpi_mom.csv")
print("CPI", lv.shape, lv.index.min().date(), lv.index.max().date())
print("系列ごとの最初の月:", lv.apply(lambda s: s.first_valid_index()).value_counts().head())
