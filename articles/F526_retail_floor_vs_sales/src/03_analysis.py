"""全国・業態別・地方別の売場面積と販売額、1㎡あたり販売額、仮説の判定、頑健性。"""
import json
import pandas as pd
from common import DATA, RES, REGION_OF, REGIONS, GYOTAI_JA

RES.mkdir(exist_ok=True)
nat = pd.read_csv(DATA / "national_ts.csv")
gy = pd.read_csv(DATA / "gyotai_pref.csv")
ref = pd.read_csv(DATA / "gyotai_2014_reference.csv")
cpi = pd.read_csv(DATA / "cpi_annual.csv").set_index("year")
YG = [1991, 1994, 1997, 1999, 2002, 2004, 2007]
eff = lambda s, f: s * 100 / f  # 百万円÷㎡ → 万円/㎡
pct = lambda a, b: round((b / a - 1) * 100, 1)
r1 = lambda x: round(float(x), 1)

# ---- 全国（表2の1972〜2004年＋2007年の業態表の合計）----
lv = nat[nat.kind == "level"][["year", "sales_mil_yen", "floor_m2"]].copy()
g7 = gy[(gy.pref == "全国") & (gy.gyotai == "total") & (gy.year == 2007)]
lv = pd.concat([lv, pd.DataFrame({"year": [2007], "sales_mil_yen": g7.sales_mil_yen.values, "floor_m2": g7.floor_m2.values})])
lv = lv.set_index("year").sort_index()
lv["eff_10k_yen_m2"] = eff(lv.sales_mil_yen, lv.floor_m2)
lv["cpi_all"] = cpi.cpi_all.reindex(lv.index)
lv["real_eff_2025yen"] = lv.eff_10k_yen_m2 / lv.cpi_all * 100
for c in ("sales_mil_yen", "floor_m2", "eff_10k_yen_m2", "real_eff_2025yen"):
    lv[c + "_idx1991"] = lv[c] / lv.loc[1991, c] * 100
lv.round(3).to_csv(RES / "national_by_year.csv")

m = {"note": "1㎡あたり販売額＝年間商品販売額÷売場面積（万円/㎡、単純な比）。実質は消費者物価指数（総合、暦年、2025年=100）で割った値。"}
m["national"] = {int(y): {"sales_trillion_yen": round(lv.loc[y, "sales_mil_yen"] / 1e6, 1), "floor_100m_m2": round(lv.loc[y, "floor_m2"] / 1e8, 3),
                          "eff": r1(lv.loc[y, "eff_10k_yen_m2"]), "real_eff": r1(lv.loc[y, "real_eff_2025yen"]) if pd.notna(lv.loc[y, "real_eff_2025yen"]) else None}
                 for y in lv.index}
m["national_change_1991_2007"] = {"floor_pct": pct(lv.loc[1991, "floor_m2"], lv.loc[2007, "floor_m2"]),
                                  "sales_pct": pct(lv.loc[1991, "sales_mil_yen"], lv.loc[2007, "sales_mil_yen"]),
                                  "eff_pct": pct(lv.loc[1991, "eff_10k_yen_m2"], lv.loc[2007, "eff_10k_yen_m2"]),
                                  "real_eff_pct": pct(lv.loc[1991, "real_eff_2025yen"], lv.loc[2007, "real_eff_2025yen"]),
                                  "cpi_pct": pct(cpi.cpi_all[1991], cpi.cpi_all[2007])}
m["sales_peak_year"] = int(lv.sales_mil_yen.idxmax())
m["eff_peak_year"] = int(lv.eff_10k_yen_m2.idxmax())
m["real_eff_peak_year"] = int(lv.real_eff_2025yen.dropna().idxmax())
m["floor_change_1972_2007_pct"] = pct(lv.loc[1972, "floor_m2"], lv.loc[2007, "floor_m2"])

# ---- 業態別（全国）----
G = ["dept", "gms", "sm_food", "sm_home", "sm_cloth", "cvs", "drug", "other_super", "specialty", "center", "total"]
gn = gy[gy.pref == "全国"].pivot_table(index="year", columns="gyotai", values=["sales_mil_yen", "floor_m2"], aggfunc="first")
S, F = gn["sales_mil_yen"].copy(), gn["floor_m2"].copy()
store = ["dept", "gms", "spec_super", "cvs", "drug", "other_super"]  # 店舗型の業態（売場のない販売が少ない）
S["store_types"] = S[store].sum(axis=1, min_count=1); F["store_types"] = F[store].sum(axis=1, min_count=1)
E_ = eff(S, F)
rows = []
for g in G + ["store_types"]:
    for y in YG:
        if pd.notna(S.loc[y, g]) and pd.notna(F.loc[y, g]):
            rows.append({"gyotai": g, "name": GYOTAI_JA.get(g, "店舗型の業態の合計"), "year": y, "sales_mil_yen": S.loc[y, g], "floor_m2": F.loc[y, g],
                         "eff_10k_yen_m2": round(E_.loc[y, g], 2), "real_eff_2025yen": round(E_.loc[y, g] / cpi.cpi_all[y] * 100, 2)})
for _, r in ref.iterrows():
    rows.append({"gyotai": r.gyotai, "name": GYOTAI_JA.get(r.gyotai, r.gyotai) + "（2014年・参考）", "year": 2014, "sales_mil_yen": r.sales_mil_yen,
                 "floor_m2": r.floor_m2, "eff_10k_yen_m2": round(eff(r.sales_mil_yen, r.floor_m2), 2),
                 "real_eff_2025yen": round(eff(r.sales_mil_yen, r.floor_m2) / cpi.cpi_all[2014] * 100, 2)})
gb = pd.DataFrame(rows)
gb.to_csv(RES / "gyotai_by_year.csv", index=False)
m["gyotai_eff"] = {g: {int(y): r1(E_.loc[y, g]) for y in YG if pd.notna(E_.loc[y, g])} for g in G + ["store_types"]}
m["gyotai_change_1991_2007"] = {g: {"floor_pct": pct(F.loc[1991, g], F.loc[2007, g]), "sales_pct": pct(S.loc[1991, g], S.loc[2007, g]),
                                    "eff_pct": pct(E_.loc[1991, g], E_.loc[2007, g])} for g in G + ["store_types"] if g != "drug"}
m["gyotai_change_1997_2007"] = {g: {"eff_pct": pct(E_.loc[1997, g], E_.loc[2007, g])} for g in G + ["store_types"] if g != "drug"}
m["drug_1999_2007"] = {"floor_pct": pct(F.loc[1999, "drug"], F.loc[2007, "drug"]), "eff_pct": pct(E_.loc[1999, "drug"], E_.loc[2007, "drug"])}
m["ref_2014_eff"] = {r.gyotai: r1(eff(r.sales_mil_yen, r.floor_m2)) for _, r in ref.iterrows()}
m["gyotai_names"] = {g: GYOTAI_JA.get(g, "店舗型の業態の合計") for g in G + ["store_types"]}

# ---- 問い直しの材料：増えた売場はどの業態か（1991→2007年）----
parts = ["dept", "gms", "sm_cloth", "sm_food", "sm_home", "cvs", "drug", "other_super", "specialty", "center", "other_store"]
d = {g: float((F.loc[2007, g] if pd.notna(F.loc[2007, g]) else 0) - (F.loc[1991, g] if pd.notna(F.loc[1991, g]) else 0)) for g in parts}
tot = F.loc[2007, "total"] - F.loc[1991, "total"]
m["floor_increase_by_gyotai_1991_2007"] = {g: {"m2_million": round(v / 1e6, 2), "share_pct": round(v / tot * 100, 1)} for g, v in d.items()}
m["floor_increase_total_million_m2"] = round(tot / 1e6, 2)
ds = {g: float((S.loc[2007, g] if pd.notna(S.loc[2007, g]) else 0) - (S.loc[1991, g] if pd.notna(S.loc[1991, g]) else 0)) for g in parts}
m["sales_change_by_gyotai_1991_2007_trillion"] = {g: round(v / 1e6, 2) for g, v in ds.items()}

# ---- 地方別 ----
t = gy[(gy.gyotai == "total") & (gy.pref != "全国")].copy()
t["region"] = t.pref.map(REGION_OF)
rg = t.groupby(["region", "year"], sort=True)[["sales_mil_yen", "floor_m2"]].sum().reset_index()
rg["eff_10k_yen_m2"] = eff(rg.sales_mil_yen, rg.floor_m2).round(2)
rg["order"] = rg.region.map({r: i for i, r in enumerate(REGIONS)})
rg = rg.sort_values(["order", "year"]).drop(columns="order")
rg.to_csv(RES / "region_by_year.csv", index=False)
R = rg.set_index(["region", "year"])
m["region"] = {r: {"floor_pct_1991_2007": pct(R.loc[(r, 1991), "floor_m2"], R.loc[(r, 2007), "floor_m2"]),
                   "sales_pct_1991_2007": pct(R.loc[(r, 1991), "sales_mil_yen"], R.loc[(r, 2007), "sales_mil_yen"]),
                   "eff_1991": r1(R.loc[(r, 1991), "eff_10k_yen_m2"]), "eff_2007": r1(R.loc[(r, 2007), "eff_10k_yen_m2"]),
                   "eff_pct_1991_2007": pct(R.loc[(r, 1991), "eff_10k_yen_m2"], R.loc[(r, 2007), "eff_10k_yen_m2"])} for r in REGIONS}
# 店舗型の業態だけの地方別（頑健性）
st = gy[gy.gyotai.isin(store) & (gy.pref != "全国")].copy()
st["region"] = st.pref.map(REGION_OF)
st = st.groupby(["region", "year"], sort=True)[["sales_mil_yen", "floor_m2"]].sum()
m["region_store_types_eff_pct_1991_2007"] = {r: pct(eff(st.loc[(r, 1991), "sales_mil_yen"], st.loc[(r, 1991), "floor_m2"]),
                                                    eff(st.loc[(r, 2007), "sales_mil_yen"], st.loc[(r, 2007), "floor_m2"])) for r in REGIONS}

# ---- 仮説 ----
c = m["national_change_1991_2007"]
H = {"H1": {"text": "1991→2007年に売場面積は20%以上増え、1㎡あたり販売額（名目）は15%以上下がった", "value": c,
            "verdict": "支持" if c["floor_pct"] >= 20 and c["eff_pct"] <= -15 else "外れ"},
     "H2": {"text": "物価をならしても1㎡あたり販売額は10%以上下がった", "value": c["real_eff_pct"], "verdict": "支持" if c["real_eff_pct"] <= -10 else "外れ"},
     "H3": {"text": "1㎡あたり販売額の低下率は総合スーパーが百貨店より大きい（参考）",
            "value": {"gms": m["gyotai_change_1991_2007"]["gms"]["eff_pct"], "dept": m["gyotai_change_1991_2007"]["dept"]["eff_pct"]},
            "verdict": "支持" if m["gyotai_change_1991_2007"]["gms"]["eff_pct"] < m["gyotai_change_1991_2007"]["dept"]["eff_pct"] else "外れ"},
     "H4": {"text": "8地方すべてで売場面積の伸び率が販売額の伸び率を上回った",
            "value": {r: [m["region"][r]["floor_pct_1991_2007"], m["region"][r]["sales_pct_1991_2007"]] for r in REGIONS},
            "verdict": "支持" if all(m["region"][r]["floor_pct_1991_2007"] > m["region"][r]["sales_pct_1991_2007"] for r in REGIONS) else "外れ"}}
m["hypotheses"] = H

# ---- 頑健性 ----
adj = nat[nat.kind == "adj_pct"].set_index("year")
link = {}
for col in ("sales_mil_yen", "floor_m2"):
    v97 = lv.loc[1997, col]
    v99_adj = v97 * (1 + adj.loc[1999, col] / 100)  # 1997→1999年は調整済前回比でつなぐ
    v04 = v99_adj * lv.loc[2004, col] / lv.loc[1999, col]
    link[col] = {"1991": lv.loc[1991, col], "2004_linked": v04}
rob = [
    {"check": "本線：全国の小売業、1991→2007年", "floor_pct": c["floor_pct"], "sales_pct": c["sales_pct"], "eff_pct": c["eff_pct"]},
    {"check": "1991→2004年（表2だけ）", "floor_pct": pct(lv.loc[1991, "floor_m2"], lv.loc[2004, "floor_m2"]),
     "sales_pct": pct(lv.loc[1991, "sales_mil_yen"], lv.loc[2004, "sales_mil_yen"]), "eff_pct": pct(lv.loc[1991, "eff_10k_yen_m2"], lv.loc[2004, "eff_10k_yen_m2"])},
    {"check": "1991→2004年、1997→1999年を調整済前回比でつなぐ", "floor_pct": pct(link["floor_m2"]["1991"], link["floor_m2"]["2004_linked"]),
     "sales_pct": pct(link["sales_mil_yen"]["1991"], link["sales_mil_yen"]["2004_linked"]),
     "eff_pct": pct(link["sales_mil_yen"]["1991"] / link["floor_m2"]["1991"], link["sales_mil_yen"]["2004_linked"] / link["floor_m2"]["2004_linked"])},
    {"check": "1997→2007年（販売額の山から）", "floor_pct": pct(lv.loc[1997, "floor_m2"], lv.loc[2007, "floor_m2"]),
     "sales_pct": pct(lv.loc[1997, "sales_mil_yen"], lv.loc[2007, "sales_mil_yen"]), "eff_pct": pct(lv.loc[1997, "eff_10k_yen_m2"], lv.loc[2007, "eff_10k_yen_m2"])},
    {"check": "1991年を再集計値（平成6年調査と対応）に", "floor_pct": pct(F.loc[1991, "total"], F.loc[2007, "total"]),
     "sales_pct": pct(S.loc[1991, "total"], S.loc[2007, "total"]), "eff_pct": pct(E_.loc[1991, "total"], E_.loc[2007, "total"])},
    {"check": "店舗型の業態の合計（百貨店・スーパー・コンビニなど）", "floor_pct": m["gyotai_change_1991_2007"]["store_types"]["floor_pct"],
     "sales_pct": m["gyotai_change_1991_2007"]["store_types"]["sales_pct"], "eff_pct": m["gyotai_change_1991_2007"]["store_types"]["eff_pct"]},
    {"check": "実質（物価指数：総合）", "floor_pct": None, "sales_pct": None, "eff_pct": c["real_eff_pct"]},
    {"check": "実質（物価指数：持家の帰属家賃を除く総合）", "floor_pct": None, "sales_pct": None,
     "eff_pct": pct(lv.loc[1991, "eff_10k_yen_m2"] / cpi.cpi_ex_rent[1991], lv.loc[2007, "eff_10k_yen_m2"] / cpi.cpi_ex_rent[2007])},
]
pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
m["robustness"] = rob
m["regions_all_eff_down"] = all(m["region"][r]["eff_pct_1991_2007"] < 0 for r in REGIONS)
m["regions_store_types_all_down"] = all(v < 0 for v in m["region_store_types_eff_pct_1991_2007"].values())
json.dump(m, open(RES / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: m[k] for k in ["national_change_1991_2007", "sales_peak_year", "eff_peak_year", "real_eff_peak_year", "gyotai_eff", "gyotai_change_1991_2007", "drug_1999_2007", "ref_2014_eff", "floor_increase_by_gyotai_1991_2007", "sales_change_by_gyotai_1991_2007_trillion", "region", "region_store_types_eff_pct_1991_2007", "hypotheses"]}, ensure_ascii=False))
print(pd.DataFrame(rob).to_string())
print(lv[["sales_mil_yen", "floor_m2", "eff_10k_yen_m2", "real_eff_2025yen"]].round(1).to_string())
