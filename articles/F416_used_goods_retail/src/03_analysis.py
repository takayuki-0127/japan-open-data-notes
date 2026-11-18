"""中古品を売る店の推移、小売全体との比較、2016→2021年（法人）、品目と売る店、ネット販売の割合。
出力：results/*.csv、results/main.json"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
t1 = pd.read_csv(ROOT / "data" / "t1_series.csv", dtype={"code": str})
fm = pd.read_csv(ROOT / "data" / "form_2016_2021.csv", dtype={"code": str})
it = pd.read_csv(ROOT / "data" / "items_2021.csv", dtype={"item_code": str})
ib = pd.read_csv(ROOT / "data" / "item_by_industry_2021.csv", dtype={"ind_code": str, "item_code": str})
r1 = lambda x: float(round(x, 1)); r2 = lambda x: float(round(x, 2)); r3 = lambda x: float(round(x, 3))
USED = {"5912": "中古自動車小売業", "5933": "中古電気製品小売業", "6062": "古本小売業", "6097": "骨とう品小売業", "6098": "中古品小売業（骨とう品を除く）"}
YEARS = [1994, 1997, 2002, 2007, 2012, 2014, 2016]

# ---- 1. 推移（1994〜2016年は個人を含む。2021年は法人だけ）
s = t1[t1.code.isin(list(USED) + ["I2"])].copy()
s["name"] = s.code.map({**USED, "I2": "小売業計"})
s = s.sort_values(["code", "year"])
tot = s[s.code == "I2"].set_index("year")
s["sales_share_of_retail_pct"] = s.apply(lambda r: r.sales_mil / tot.sales_mil[r.year] * 100, axis=1)
s["sales_per_est_mil"] = s.sales_mil / s.est
s["emp_per_est"] = s.employees / s.est
s["corp_share_est_pct"] = s.est_corp / s.est * 100
s.round(5).to_csv(RES / "series_used_retail.csv", index=False)
sp = s.pivot(index="year", columns="code", values="sales_mil")
sh = s.pivot(index="year", columns="code", values="sales_share_of_retail_pct")
es = s.pivot(index="year", columns="code", values="est")
ec = s.pivot(index="year", columns="code", values="est_corp")
em = s.pivot(index="year", columns="code", values="employees")

# ---- 2. 2016→2021年（法人の事業所、第9表）
f = fm[fm.code.isin(list(USED) + ["I2"])].copy()
f["name"] = f.code.map({**USED, "I2": "小売業計"})
f["internet_share_pct"] = f.sales_internet / f.sales_retail * 100
f["catalog_share_pct"] = f.sales_catalog / f.sales_retail * 100
f["store_share_pct"] = f.sales_store / f.sales_retail * 100
f.round(4).to_csv(RES / "corp_2016_2021.csv", index=False)
fp = f.pivot(index="code", columns="year", values="sales_retail")
growth_corp = (fp[2021] / fp[2016] - 1) * 100
fi = f.pivot(index="code", columns="year", values="internet_share_pct")
fe = f.pivot(index="code", columns="year", values="est")

# ---- 3. 品目：中古の品目の販売額と、どの業種の店で売られたか（2021年、法人）
UI = {"59121": "乗用車（中古）", "59122": "トラック（中古）", "59331": "中古電気製品", "60621": "古本", "60971": "骨とう品", "60981": "中古品（骨とう品を除く）"}
HOME = {"59121": "5912", "59122": "5912", "59331": "5933", "60621": "6062", "60971": "6097", "60981": "6098"}
items = it[it.item_code.isin(UI)].copy()
items["item"] = items.item_code.map(UI)
retail_items_total = float(it[it.item_code == "I2"].sales_mil.iloc[0])
items["share_of_retail_items_pct"] = items.sales_mil / retail_items_total * 100
ibu = ib[ib.item_code.isin(UI)]
lvl4 = ibu[ibu.ind_code.str.fullmatch(r"\d{4}")]
rows = []
for ic, nm in UI.items():
    tot_i = float(ibu[(ibu.item_code == ic) & (ibu.ind_code == "I2")].sales_mil.iloc[0])
    home = float(lvl4[(lvl4.item_code == ic) & (lvl4.ind_code == HOME[ic])].sales_mil.fillna(0).sum())
    sub = lvl4[(lvl4.item_code == ic) & (lvl4.ind_code != HOME[ic])].sort_values("sales_mil", ascending=False)
    top = sub.head(3)
    rows.append({"item_code": ic, "item": nm, "sales_retail_mil": tot_i, "home_industry": HOME[ic],
                 "home_sales_mil": home, "outside_share_pct": (1 - home / tot_i) * 100,
                 "top_other_1": f"{top.industry.iloc[0]}:{top.sales_mil.iloc[0]:.0f}" if len(top) > 0 else "",
                 "top_other_2": f"{top.industry.iloc[1]}:{top.sales_mil.iloc[1]:.0f}" if len(top) > 1 else "",
                 "top_other_3": f"{top.industry.iloc[2]}:{top.sales_mil.iloc[2]:.0f}" if len(top) > 2 else "",
                 "top_other_1_share_pct": float(top.sales_mil.iloc[0] / tot_i * 100) if len(top) > 0 else np.nan})
where = pd.DataFrame(rows)
where.round(4).to_csv(RES / "where_used_items_sold.csv", index=False)
items = items.merge(where[["item_code", "sales_retail_mil", "outside_share_pct"]], on="item_code")
items.round(5).to_csv(RES / "used_items_2021.csv", index=False)
used_total = float(items.sales_mil.sum())
used_total_excl_car = float(items[~items.item_code.isin(["59121", "59122"])].sales_mil.sum())
# 中古品（骨とう品を除く）の品目を売るほかの業種の内訳（小分類の段で、上位をすべて書き出す）
o = lvl4[(lvl4.item_code == "60981")].sort_values("sales_mil", ascending=False)[["ind_code", "industry", "sales_mil", "est"]]
o.to_csv(RES / "used_goods_item_by_industry.csv", index=False)

# ---- 4. 頑健性：期間・指標を変えた伸び
def g(a, b, code, tab):
    return float((tab.loc[b, code] / tab.loc[a, code] - 1) * 100)
rob = []
for code in ["6098", "5912", "I2"]:
    rob.append({"code": code, "check": "販売額 1994→2016年", "value": g(1994, 2016, code, sp)})
    rob.append({"code": code, "check": "販売額 2007→2016年", "value": g(2007, 2016, code, sp)})
    rob.append({"code": code, "check": "販売額 2012→2016年", "value": g(2012, 2016, code, sp)})
    rob.append({"code": code, "check": "販売額 2016→2021年（法人だけ、第9表）", "value": float(growth_corp[code])})
    rob.append({"code": code, "check": "販売額 2016→2021年（第1表。2021年は法人だけ）", "value": g(2016, 2021, code, sp) if not np.isnan(sp.loc[2021, code]) else np.nan})
    rob.append({"code": code, "check": "事業所数 1994→2016年", "value": g(1994, 2016, code, es)})
    rob.append({"code": code, "check": "法人の事業所数 2016→2021年", "value": g(2016, 2021, code, ec)})
    rob.append({"code": code, "check": "従業者数 1994→2016年", "value": g(1994, 2016, code, em)})
rob = pd.DataFrame(rob)
rob.round(2).to_csv(RES / "robustness.csv", index=False)
rv = rob.set_index(["code", "check"]).value

h1 = float(sh.loc[2016, "6098"] / sh.loc[1994, "6098"])
# 問い直し：2016→2021年（法人）の伸びは、店頭とネットのどちらから来たか
fx = f.set_index(["code", "year"])
dec = {}
for c in ["6098", "5912", "I2"]:
    d_tot = fx.loc[(c, 2021), "sales_retail"] - fx.loc[(c, 2016), "sales_retail"]
    dec[c] = {"d_total_oku": r1(d_tot / 100),
              "d_store_oku": r1((fx.loc[(c, 2021), "sales_store"] - fx.loc[(c, 2016), "sales_store"]) / 100),
              "d_internet_oku": r1((fx.loc[(c, 2021), "sales_internet"] - fx.loc[(c, 2016), "sales_internet"]) / 100),
              "internet_2016_oku": r1(fx.loc[(c, 2016), "sales_internet"] / 100), "internet_2021_oku": r1(fx.loc[(c, 2021), "sales_internet"] / 100),
              "store_2016_oku": r1(fx.loc[(c, 2016), "sales_store"] / 100), "store_2021_oku": r1(fx.loc[(c, 2021), "sales_store"] / 100),
              "store_growth_pct": r1((fx.loc[(c, 2021), "sales_store"] / fx.loc[(c, 2016), "sales_store"] - 1) * 100)}
main = {
    "years": YEARS + [2021],
    "used6098": {"sales_oku": {int(y): r1(sp.loc[y, "6098"] / 100) for y in YEARS + [2021]},
                 "share_pct": {int(y): r3(sh.loc[y, "6098"]) for y in YEARS},
                 "est": {int(y): int(es.loc[y, "6098"]) for y in YEARS + [2021]},
                 "est_corp": {int(y): int(ec.loc[y, "6098"]) for y in YEARS + [2021]},
                 "employees": {int(y): int(em.loc[y, "6098"]) for y in YEARS + [2021]},
                 "share_ratio_2016_1994": r2(h1),
                 "sales_per_est_mil": {int(y): r1(sp.loc[y, "6098"] / es.loc[y, "6098"]) for y in YEARS},
                 "sales_per_est_corp_mil_2021": r1(fp.loc["6098", 2021] / fe.loc["6098", 2021]),
                 "sales_per_est_corp_mil_2016": r1(fp.loc["6098", 2016] / fe.loc["6098", 2016]),
                 "emp_per_est": {int(y): r1(em.loc[y, "6098"] / es.loc[y, "6098"]) for y in YEARS}},
    "used_car5912": {"sales_oku": {int(y): r1(sp.loc[y, "5912"] / 100) for y in [1994, 2002, 2007, 2012, 2016] if not np.isnan(sp.loc[y, "5912"])},
                     "share_pct": {int(y): r2(sh.loc[y, "5912"]) for y in [1994, 2002, 2007, 2012, 2016]}},
    "other_used": {c: {"sales_oku_2012": r1(sp.loc[2012, c] / 100), "sales_oku_2016": r1(sp.loc[2016, c] / 100),
                       "sales_oku_2021_corp": r1(fp.loc[c, 2021] / 100), "corp_growth_2016_2021_pct": r1(growth_corp[c])} for c in ["5933", "6062", "6097"]},
    "retail_total_choen": {int(y): r1(sp.loc[y, "I2"] / 1e6) for y in YEARS},
    "corp_2016_2021": {c: {"2016_oku": r1(fp.loc[c, 2016] / 100), "2021_oku": r1(fp.loc[c, 2021] / 100), "growth_pct": r1(growth_corp[c])} for c in ["6098", "5912", "I2"]},
    "internet_share": {c: {"2016": r1(fi.loc[c, 2016]), "2021": r1(fi.loc[c, 2021])} for c in list(USED) + ["I2"]},
    "est_corp_2016_2021": {c: {"2016": int(ec.loc[2016, c]), "2021": int(ec.loc[2021, c]), "growth_pct": r1(g(2016, 2021, c, ec))} for c in ["6098", "5912", "I2"]},
    "items_2021": {UI[k]: {"sales_oku": r1(v / 100)} for k, v in items.set_index("item_code").sales_mil.items()},
    "items_used_total_choen": r2(used_total / 1e6), "items_used_total_excl_car_oku": r1(used_total_excl_car / 100),
    "items_used_share_of_retail_pct": r2(used_total / retail_items_total * 100),
    "items_retail_total_choen": r1(retail_items_total / 1e6),
    "where": {r.item: {"outside_share_pct": r1(r.outside_share_pct), "top_other_1": r.top_other_1, "top_other_1_share_pct": r1(r.top_other_1_share_pct)} for r in where.itertuples()},
    "rob": {f"{c}|{k}": r1(v) for (c, k), v in rv.items() if not np.isnan(v)},
    "requestion_store_vs_internet": dec,
    "env_reuse_ref": {"note": "環境省 令和6年度リユース市場規模調査（概要版）の値。比べ先としてだけ使う（手入力）",
                      "store_excl_car_oku_2024": 4468, "total_incl_car_oku_2024": 34986, "total_excl_car_oku_2024": 12813},
}
main["hypotheses"] = {"H1": h1 >= 3, "H2": bool(growth_corp["6098"] > growth_corp["I2"]),
                      "H3": main["where"]["中古品（骨とう品を除く）"]["outside_share_pct"] >= 30,
                      "H4": main["where"]["乗用車（中古）"]["outside_share_pct"] >= 40}
(RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(main, ensure_ascii=False, indent=1))
