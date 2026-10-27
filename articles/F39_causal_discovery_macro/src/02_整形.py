"""F39 整形：月次の6変数をそろえ、前年比（主）と前月比（頑健性）の2通りに変換する"""
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL
from common import RAW, DATA, residualize, tax_window_dummies, tax_month_dummies

boj = pd.read_csv(RAW / "boj_prices_fx.csv", encoding="utf-8-sig")
boj["month"] = pd.to_datetime(boj["date"].astype(str), format="%Y%m")
w = boj.pivot(index="month", columns="series_code", values="value")
lv = pd.DataFrame({
    "fx": w["FXERM07"],
    "imp": w["PRCG20_2500000000"],
    "imp_yen": w["PRCG20_2600000000"],
})
m = pd.read_csv(RAW / "f12_mart_extract.csv", parse_dates=["month"]).set_index("month")
lr = pd.read_csv(RAW / "f18_long_rate.csv", parse_dates=["month"]).set_index("month")
lv = lv.join(m[["cpi_core", "cpi_core_yoy", "unemp_rate_sa", "wage_total_idx", "wage_total_yoy", "wage_scheduled_yoy"]], how="left")
lv = lv.join(lr.rename(columns={"長期金利": "rate"}), how="left")
lv.to_csv(DATA / "levels.csv")

# ---- 前年比（主）----
y = pd.DataFrame(index=lv.index)
y["fx"] = 100 * np.log(lv["fx"]).diff(12)
y["imp"] = 100 * np.log(lv["imp"]).diff(12)
y["imp_yen"] = 100 * np.log(lv["imp_yen"]).diff(12)
y["cpi_raw"] = lv["cpi_core_yoy"]
y["wage"] = lv["wage_total_yoy"]
y["wage_sched"] = lv["wage_scheduled_yoy"]
y["rate"] = lv["rate"].diff(12)
y["unemp"] = lv["unemp_rate_sa"].diff(12)
y = y.loc["1995-01-01":"2026-08-01"]
# 消費税の引き上げで生鮮除く総合の前年比が12か月押し上げられる分を、期間ダミーで取り除く
y["cpi"] = residualize(y["cpi_raw"], tax_window_dummies(y.index))
assert y[["fx", "imp", "cpi", "wage", "rate", "unemp"]].notna().all().all(), y.isna().sum()
y.to_csv(DATA / "yoy.csv")
print("yoy", y.index.min().date(), y.index.max().date(), len(y))

# ---- 前月比（頑健性）：季節性のある系列は STL で季節成分を除いてから対数差 ----
def sa(s):
    s = s.dropna()
    r = STL(np.log(s), period=12, robust=True).fit()
    return np.exp(r.trend + r.resid)

mm = pd.DataFrame(index=lv.index)
mm["fx"] = 100 * np.log(lv["fx"]).diff()
mm["imp"] = 100 * np.log(lv["imp"]).diff()
mm["cpi_raw"] = 100 * np.log(sa(lv["cpi_core"].loc["1990":"2026-08"])).diff()
mm["wage"] = 100 * np.log(sa(lv["wage_total_idx"].loc["1990":"2026-08"])).diff()
mm["rate"] = lv["rate"].diff()
mm["unemp"] = lv["unemp_rate_sa"].diff()
mm = mm.loc["1995-01-01":"2026-08-01"]
mm["cpi"] = residualize(mm["cpi_raw"], tax_month_dummies(mm.index))
mm.to_csv(DATA / "mom.csv")
print("mom", mm[["fx", "imp", "cpi", "wage", "rate", "unemp"]].isna().sum().to_dict())
