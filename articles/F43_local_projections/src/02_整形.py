"""月次のパネルを作る（1985年7月〜2026年8月）

- 生産・物価・為替・輸入物価は対数×100（%の単位で読めるように）
- 消費者物価は、消費税の引き上げ月の段差を取り除く（その月の前月比から、前後12か月の前月比の中央値を引いた分を段差とみなす）
- 消費者物価は原数値なので、月のダミーで季節性を取り除く（推定期間全体で一定の季節性を仮定）
"""
import numpy as np
import pandas as pd
from common import RAW, DATA, TAX_MONTHS


def boj(fname, code):
    d = pd.read_csv(RAW / fname)
    d = d[d.series_code == code]
    idx = pd.to_datetime(d.date.astype(str).str[:6], format="%Y%m")
    return pd.Series(d.value.values, index=idx).sort_index()


call = boj("f43_boj_callrate.csv", "STRACLUCON")
fx = boj("boj_prices_fx.csv", "FXERM07")
imp = boj("boj_prices_fx.csv", "PRCG20_2500000000")
m12 = pd.read_csv(RAW / "f12_mart_extract.csv", parse_dates=["month"]).set_index("month")
m13 = pd.read_csv(RAW / "f13_monthly.csv", parse_dates=["month"]).set_index("month")
lr = pd.read_csv(RAW / "f18_long_rate.csv", parse_dates=["month"]).set_index("month")["長期金利"]

df = pd.DataFrame({"call": call, "long": lr, "fx_lvl": fx, "imp_lvl": imp,
                   "cpi_lvl": m12.cpi_core, "unemp": m12.unemp_rate_sa, "ip_lvl": m13.iip}).sort_index()
df = df.loc["1985-07-01":"2026-08-01"]

# 消費者物価：消費税の段差を除く
lc = np.log(df.cpi_lvl) * 100
d = lc.diff()
adj = pd.Series(0.0, index=df.index)
tax = {}
for m in TAX_MONTHS:
    t = pd.Timestamp(m)
    if t not in d.index:
        continue
    window = d.loc[t - pd.DateOffset(months=12): t + pd.DateOffset(months=12)].drop(t)
    # 前後の同じ月（季節性）も考える：前年・翌年の同じ月の前月比の平均を基準にする
    same = [d.get(t - pd.DateOffset(months=12)), d.get(t + pd.DateOffset(months=12))]
    base = np.nanmean([x for x in same if x is not None])
    jump = d.loc[t] - base
    tax[m] = jump
    adj.loc[t:] += jump
lc_adj = lc - adj
# 季節性：月ダミーで除く（前月比の月別平均を引いて積み直す）
dd = lc_adj.diff()
mm = dd.groupby(dd.index.month).transform("mean") - dd.mean()
lc_sa = (dd - mm).fillna(0).cumsum() + lc_adj.iloc[0]

out = pd.DataFrame({
    "ip": np.log(df.ip_lvl) * 100,
    "cpi": lc_sa,
    "unemp": df.unemp,
    "call": df.call,
    "long": df.long,
    "fx": np.log(df.fx_lvl) * 100,
    "imp": np.log(df.imp_lvl) * 100,
})
out.index.name = "month"
out.round(5).to_csv(DATA / "panel.csv", encoding="utf-8-sig")
pd.Series(tax, name="段差（ポイント、対数×100）").round(3).to_csv(DATA / "cpi_tax_steps.csv", encoding="utf-8-sig")
df.to_csv(DATA / "levels.csv", encoding="utf-8-sig")
print(out.describe().round(2)); print(tax)
print(out.isna().sum())
