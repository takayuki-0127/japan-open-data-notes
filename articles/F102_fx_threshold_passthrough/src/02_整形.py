"""F102 整形：月次の4変数（輸入物価・ドル円・国内企業物価・消費者物価）の前月比を作り、
季節性と特殊な月（消費税など）を取り除く"""
import numpy as np
import pandas as pd
from common import RAW, DATA, POLICY_MONTHS

boj = pd.read_csv(RAW / "boj_prices_fx.csv", encoding="utf-8-sig")
boj["month"] = pd.to_datetime(boj["date"].astype(str), format="%Y%m")
w = boj.pivot(index="month", columns="series_code", values="value")
m = pd.read_csv(RAW / "f12_mart_extract.csv", parse_dates=["month"]).set_index("month")

lv = pd.DataFrame({
    "fx": w["FXERM07"],
    "imp": w["PRCG20_2500000000"],
    "imp_yen": w["PRCG20_2600000000"],
    "ppi": w["PRCG20_2200000000"],
}).join(m[["cpi_core"]].rename(columns={"cpi_core": "cpi"}), how="left")
lv = lv.loc["1978-01-01":"2026-08-01"]
lv.to_csv(DATA / "levels.csv", encoding="utf-8-sig")

# 前月比（対数差×100）
mom = 100 * np.log(lv).diff()
mom = mom.loc["1980-01-01":]

# 季節性（月ダミー）と特殊な月のダミーを OLS で取り除く（平均は残す）
idx = mom.index
D = pd.get_dummies(idx.month, prefix="m", drop_first=True).astype(float)
D.index = idx
for d in POLICY_MONTHS:
    D["p_" + d[:7]] = (idx == pd.Timestamp(d)).astype(float)
X = np.column_stack([np.ones(len(idx)), D.values])
clean = pd.DataFrame(index=idx)
coef = {}
for c in ["imp", "fx", "imp_yen", "ppi", "cpi"]:
    y = mom[c].values
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    clean[c] = y - (D.values - D.values.mean(0)) @ b[1:]
    coef[c] = dict(zip(["const"] + list(D.columns), b))
clean.to_csv(DATA / "mom_clean.csv", encoding="utf-8-sig")
pd.DataFrame(coef).to_csv(DATA / "dummy_coefs.csv", encoding="utf-8-sig")

# しきい値に使う「過去12か月のドル円の変化率」（t-1 までの12か月、対数差×100）
lfx = 100 * np.log(lv["fx"])
z = pd.DataFrame({
    "z12": (lfx.shift(1) - lfx.shift(13)).loc[idx],
    "z6": (lfx.shift(1) - lfx.shift(7)).loc[idx],
})
z.to_csv(DATA / "threshold_vars.csv", encoding="utf-8-sig")

# 図用：前年比（消費者物価は特殊な月の段差を除いた系列から作る）
cum = clean.cumsum()
yoy = pd.DataFrame({
    "fx": lfx.diff(12).loc[idx],
    "imp_yen": (100 * np.log(lv["imp_yen"])).diff(12).loc[idx],
    "cpi_adj": cum["cpi"] - cum["cpi"].shift(12),
    "ppi_adj": cum["ppi"] - cum["ppi"].shift(12),
})
yoy.to_csv(DATA / "yoy_for_figures.csv", encoding="utf-8-sig")
print(clean.describe().round(3))
print(clean.index.min().date(), clean.index.max().date(), len(clean))
