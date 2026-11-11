"""F267 05 問い直し（結果を見てから足した）：
客単価は「現場が動かせる」指標か？ 既存店の客単価の前年同月比のうち、物価（消費者物価指数）の動きで説明できる分はどれだけか。
2016〜2025年（CPI の前年比が取れる期間）。"""
import json, pathlib
import numpy as np, pandas as pd
BASE = pathlib.Path(__file__).resolve().parents[1]
DATA, RES, RAW = BASE / "data", BASE / "results", BASE / "data" / "raw"
m = pd.read_csv(DATA / "jfa_cvs_monthly.csv")
cpi = pd.read_csv(RAW / "cpi_gs_monthly.csv", dtype={"ym": str})
cpi["ym"] = cpi.ym.str[:4] + "-" + cpi.ym.str[4:]
cpi = cpi.set_index("ym")
series = {"食料工業製品": "食料工業製品|0208", "生鮮食品を除く財": "生鮮食品を除く財|0241", "財": "財|0202", "総合": "総合|0201"}
d = m.set_index("ym")[["year", "month", "price_ex_yoy", "cust_ex_yoy", "sales_ex_yoy"]].copy()
d["lp"], d["lc"], d["ls"] = np.log1p(d.price_ex_yoy), np.log1p(d.cust_ex_yoy), np.log1p(d.sales_ex_yoy)
for k, c in series.items():
    s = cpi[c].astype(float)
    d["cpi_" + k] = np.log(s / s.shift(12)).reindex(d.index)
d = d[d.year.between(2016, 2025)].dropna()
d.to_csv(RES / "reask_price_vs_cpi_monthly.csv")
out = {"n": int(len(d)), "period": [d.index.min(), d.index.max()]}
COVID = [2020, 2021, 2022]
def fit(dd, k):
    x, y = dd["cpi_" + k].values, dd.lp.values
    b = np.polyfit(x, y, 1)
    r = np.corrcoef(x, y)[0, 1]
    return dict(slope=float(b[0]), intercept=float(b[1]), corr=float(r), r2=float(r ** 2))
out["fit"] = {k: {"all": fit(d, k), "ex_covid": fit(d[~d.year.isin(COVID)], k)} for k in series}
# 年ごと：客単価の伸びと物価の伸び（食料工業製品）
yr = d.groupby("year")[["lp", "lc", "ls"] + ["cpi_" + k for k in series]].mean()
yr.to_csv(RES / "reask_price_vs_cpi_annual.csv")
out["annual"] = (yr * 100).round(2).to_dict(orient="index")
# 物価を引いた客単価（実質の客単価）で、売上の揺れを3つに分ける：客数・物価・実質の客単価
k = "食料工業製品"
d["lreal"] = d.lp - d["cpi_" + k]
def share3(dd):
    X = dd[["lc", "cpi_" + k, "lreal"]].values; s = dd.ls.values
    C = np.cov(np.c_[X, s].T); vs = C[3, 3]
    return {n: float(C[i, :3].sum() / vs) for i, n in enumerate(["cust", "cpi", "real_price"])}
out["share3_all"] = share3(d)
out["share3_ex_covid"] = share3(d[~d.year.isin(COVID)])
# 2022〜2025年：客単価の累積の伸びのうち物価の分
w = d[d.year.between(2022, 2025)]
out["cum_2022_2025"] = dict(price_ex=float(w.lp.sum() / 12), cpi_food=float(w["cpi_" + k].sum() / 12),
                           cust=float(w.lc.sum() / 12), sales=float(w.ls.sum() / 12))
json.dump(out, open(RES / "reask.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({kk: out[kk] for kk in ["n", "period", "fit", "share3_all", "share3_ex_covid", "cum_2022_2025"]}, ensure_ascii=False, indent=1))
print((yr * 100).round(2).to_string())
