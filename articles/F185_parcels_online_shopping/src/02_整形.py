"""02 整形：年度（4月〜翌3月）の表 data/fy_panel.csv を作る。"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"

# 宅配便（国交省、年度）とゆうパック（郵政民営化前の4年分を足すため）
p = pd.read_csv(RAW / "mlit_parcels_fy.csv")
yp = pd.read_csv(RAW / "yupack_fy.csv")
p = p.merge(yp[["fy", "yupack_mil"]], on="fy", how="left")
# FY2003〜2006 は国交省の集計にゆうパックが入っていないので足す（FY2007 からは集計に含まれる）
p["parcels_adj_mil"] = p.parcels_total_mil + np.where(p.fy <= 2006, p.yupack_mil, 0.0)

# 家計消費状況調査（二人以上の世帯、月平均・円）：月の値を年度に組み替える
m = pd.read_csv(RAW / "kakei_net_monthly.csv")
spend = m[m.series.str.startswith("spend")].copy()
share = m[m.series == "share"].copy()
mon = [f"m{i:02d}" for i in range(1, 13)]


def to_long(df):
    out = df.melt(id_vars=["year", "series"], value_vars=mon, var_name="mm", value_name="v")
    out["month"] = out.mm.str[1:].astype(int)
    out["fy"] = np.where(out.month >= 4, out.year, out.year - 1)
    return out


sl = to_long(spend)
sl["newdef"] = (sl.series == "spend22").astype(float)
fy_sp = sl.groupby("fy").agg(net_spend=("v", "mean"), n_month=("v", "size"), newdef_frac=("newdef", "mean")).reset_index()
fy_sp = fy_sp[fy_sp.n_month == 12]
# 暦年の年平均（年度に組み替えない比較用）
cy_sp = spend[["year", "annual"]].rename(columns={"year": "fy", "annual": "net_spend_cy"})
cy_sp["newdef_cy"] = (spend.series == "spend22").astype(float).values

# 注文した世帯の割合：2015年以降は公表の1万分比（月）、2014年以前は注文世帯数÷集計世帯数（年平均）
shl = to_long(share)
fy_sh = shl.groupby("fy").agg(share_m=("v", "mean"), n=("v", "size")).reset_index()
fy_sh = fy_sh[fy_sh.n == 12][["fy", "share_m"]]
old = pd.read_csv(RAW / "kakei_net_households_2004_2014.csv")
old["share_cy"] = old.order_households / old.tabulated_households * 1e4
cy_share = pd.concat([old[["year", "share_cy"]], share[["year", "annual"]].rename(columns={"annual": "share_cy"})])
cy_share = cy_share.set_index("year").share_cy
fy_share = {}
for fy in range(2004, 2025):
    a, b = cy_share.get(fy), cy_share.get(fy + 1)
    fy_share[fy] = 0.75 * a + 0.25 * b if a is not None and b is not None else np.nan
fy_sh2 = pd.DataFrame({"fy": list(fy_share), "net_share": list(fy_share.values())})
fy_sh2.loc[fy_sh2.fy >= 2015, "net_share"] = fy_sh2.fy.map(fy_sh.set_index("fy").share_m)

# 品目を「モノ」に絞った支出（2015〜2025年、暦年）
it = pd.read_csv(RAW / "net_items_2015_2025.csv")
not_goods = ["出前", "電子書籍", "ダウンロード版の音楽・映像・アプリ", "保険", "旅行（ネット上で決済）", "旅行（ネット以外で決済）", "チケット"]
goods = it[~it.item.isin(not_goods)]
yrs = [c for c in it.columns if c.isdigit()]
g = pd.DataFrame({"year": [int(y) for y in yrs], "goods_cy": goods[yrs].sum().values, "all22_cy": it[yrs].sum().values})
g["goods_fy"] = [0.75 * g.goods_cy[i] + 0.25 * g.goods_cy[i + 1] if i + 1 < len(g) else np.nan for i in range(len(g))]

# 人口（総人口、千人、10月1日）と単独世帯（国勢調査を対数で直線補間、2020年以降と2005年以前は前後5年の伸びでのばす）
pop = pd.read_csv(RAW / "pop_national_year.csv")[["year", "pop_total"]]
ce = pd.read_csv(RAW / "census_households.csv").set_index("year")
yrs_all = np.arange(2003, 2026)
lh = np.interp(yrs_all, ce.index, np.log(ce.one_person_thou))
lt = np.interp(yrs_all, ce.index, np.log(ce.private_households_thou))
for arr, col in [(lh, "one_person_thou"), (lt, "private_households_thou")]:
    lo = np.log(ce[col])
    s_hi = (lo[2020] - lo[2015]) / 5; s_lo = (lo[2010] - lo[2005]) / 5
    arr[yrs_all > 2020] = lo[2020] + s_hi * (yrs_all[yrs_all > 2020] - 2020)
    arr[yrs_all < 2005] = lo[2005] + s_lo * (yrs_all[yrs_all < 2005] - 2005)
hh = pd.DataFrame({"fy": yrs_all, "one_person_thou": np.exp(lh), "households_thou": np.exp(lt)})
hh["hh_interp"] = ~hh.fy.isin(ce.index)

d = (p.merge(fy_sp, on="fy", how="left").merge(cy_sp, on="fy", how="left").merge(fy_sh2, on="fy", how="left")
      .merge(g[["year", "goods_cy", "goods_fy"]].rename(columns={"year": "fy"}), on="fy", how="left")
      .merge(pop.rename(columns={"year": "fy"}), on="fy", how="left").merge(hh, on="fy", how="left"))
d["parcels_per_capita"] = d.parcels_adj_mil * 1e6 / (d.pop_total * 1e3)
d.to_csv(DATA / "fy_panel.csv", index=False)
print(d[["fy", "parcels_total_mil", "parcels_adj_mil", "net_spend", "newdef_frac", "net_share", "goods_fy", "pop_total", "one_person_thou"]].round(1).to_string())
