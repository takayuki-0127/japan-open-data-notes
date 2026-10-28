"""追加の頑健性チェック
1. 東京の電力需要：年周期（フーリエ項）を足して季節の残りを除いても d は残るか
2. 物価：15年の窓をずらしながら d を推定すると、期間でどれだけ動くか
"""
import warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from common import DATA, RAW, RES
from lm import all_estimates, local_whittle

warnings.filterwarnings("ignore")

# ---------- 1. 年周期を足す ----------
d = pd.read_csv(RAW / "daily_tokyo_f67.csv.gz", parse_dates=["date"])
d = d[d.n == 24].copy()
doy = d.date.dt.dayofyear / 365.25 * 2 * np.pi
for k in range(1, 5):
    d[f"s{k}"], d[f"c{k}"] = np.sin(k * doy), np.cos(k * doy)
F = "log_d ~ cr(temp_mean, df=8) + C(dow) + holiday + obon + nenmatsu + gw + covid + C(month)"
F4 = F + "".join(f" + s{k} + c{k}" for k in range(1, 5))
rows = []
for lab, f in [("年周期（フーリエ4組）を足す", F4), ("年周期＋年度", F4 + " + C(fy)"),
               ("湿度・前日の気温も足す", F + " + humid + temp_lag1")]:
    r = all_estimates(smf.ols(f, data=d).fit().resid.values)
    r.update(area="東京", spec=lab, n=len(d))
    rows.append(r)
x = pd.DataFrame(rows)
x.to_csv(RES / "power_estimates_extra.csv", index=False)
print(x[["spec", "lw_0.5", "lw_0.6", "lw_0.7", "gph_0.6", "arfima_d", "dfa_d", "rs_d"]].round(3).to_string())

# ---------- 2. 物価：15年の窓をずらす ----------
mom = pd.read_csv(DATA / "cpi_mom.csv", index_col=0, parse_dates=True)
TAX = pd.to_datetime(["1989-04-01", "1997-04-01", "2014-04-01", "2019-10-01"])


def clean(s):
    df = pd.DataFrame({"y": s.values, "m": s.index.month}, index=s.index)
    f = "y ~ C(m)"
    for i, t in enumerate(TAX):
        df[f"t{i}"] = (s.index == t).astype(int)
        if df[f"t{i}"].sum():
            f += f" + t{i}"
    return smf.ols(f, data=df).fit().resid.values


out = []
for nm in ["総合", "生鮮食品を除く総合", "生鮮食品及びエネルギーを除く総合", "生鮮食品"]:
    s = mom[nm].dropna()
    for start in pd.date_range("1970-02-01", "2011-10-01", freq="12MS"):
        end = start + pd.DateOffset(months=179)
        w = s.loc[start:end]
        if len(w) < 180:
            continue
        dd, se = local_whittle(clean(w), 0.6)
        out.append({"name": nm, "start": start.date(), "end": end.date(),
                    "mid": (start + pd.DateOffset(months=90)).date(), "lw_0.6": dd, "se": se})
roll = pd.DataFrame(out)
roll.to_csv(RES / "cpi_rolling.csv", index=False)
print(roll.pivot_table(index="start", columns="name", values="lw_0.6").round(2).to_string())
