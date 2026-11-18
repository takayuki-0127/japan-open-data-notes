"""出荷量・面積の推移、品目別の変化、家計の支出（名目・実質・頻度）、輸入、仮説の判定、頑健性。乱数は使わない。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"; R = ROOT / "results"
K = pd.read_csv(D / "kaki_national.csv")
A = pd.read_csv(D / "kakei_cutflower_age.csv")
LT = pd.read_csv(D / "kakei_cutflower_longterm.csv")
CPI = pd.read_csv(D / "cpi_cutflower.csv").set_index("year").cpi_cutflower
IM = pd.read_csv(D / "cutflower_import_hs6.csv")
out = {}


def r1(x, k=1):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


def ser(item, m="ship", group=None):
    q = K[(K.item == item) & (K.measure == m)]
    if group:
        q = q[q.group == group]
    return q.set_index("year").value.sort_index()


# --- 類ごとの計（出荷量・面積）
TOT = {"kirihana": "切り花類", "hachimono": "鉢もの類", "naemono": "花壇用苗もの類", "kyukon": "球根類"}
rows = []
for g, name in TOT.items():
    for m in ["ship", "area"]:
        s = ser(name, m, g)
        for y, v in s.items():
            rows.append({"group": name, "measure": m, "year": int(y), "value": v})
T = pd.DataFrame(rows)
T.to_csv(R / "group_totals.csv", index=False)
grp = {}
for name in TOT.values():
    s = T[(T.group == name) & (T.measure == "ship")].set_index("year").value
    a = T[(T.group == name) & (T.measure == "area")].set_index("year").value
    pk = int(s.loc[1990:].idxmax())
    grp[name] = {"peak_year": pk, "peak": r1(s[pk], 0), "v2005": r1(s.get(2005), 0), "v2025": r1(s[2025], 0),
                 "pct_from_peak": r1((s[2025] / s[pk] - 1) * 100, 1), "pct_from_2005": r1((s[2025] / s[2005] - 1) * 100, 1),
                 "area_peak_year": int(a.loc[1990:].idxmax()), "area_pct_from_peak": r1((a[2025] / a.loc[1990:].max() - 1) * 100, 1),
                 "area_pct_from_2005": r1((a[2025] / a[2005] - 1) * 100, 1)}
out["groups"] = grp
kiri = T[(T.group == "切り花類") & (T.measure == "ship")].set_index("year").value
kiri_a = T[(T.group == "切り花類") & (T.measure == "area")].set_index("year").value
out["kirihana_ship"] = {y: r1(kiri[y] / 1e5, 2) for y in [1989, 1990, 2000, 2005, 2010, 2015, 2020, 2024, 2025]}   # 億本
out["kirihana_cagr_pct"] = {"2005_2015": r1(((kiri[2015] / kiri[2005]) ** (1 / 10) - 1) * 100, 2),
                            "2015_2025": r1(((kiri[2025] / kiri[2015]) ** (1 / 10) - 1) * 100, 2)}

# --- 品目別（切り花）：2005年と2025年の両方に値がある品目
items = sorted(set(K[(K.group == "kirihana") & (~K.is_total) & (K.measure == "ship")].item))
irows = []
for it in items:
    s = ser(it, "ship", "kirihana"); a = ser(it, "area", "kirihana")
    if 2005 in s.index and 2025 in s.index:
        irows.append({"item": it, "ship_2005": s[2005], "ship_2025": s[2025], "pct_ship": (s[2025] / s[2005] - 1) * 100,
                      "area_2005": a.get(2005, np.nan), "area_2025": a.get(2025, np.nan),
                      "pct_area": (a.get(2025, np.nan) / a.get(2005, np.nan) - 1) * 100,
                      "share_2005": s[2005] / kiri[2005] * 100, "share_2025": s[2025] / kiri[2025] * 100})
I = pd.DataFrame(irows).sort_values("pct_ship").reset_index(drop=True)
I.to_csv(R / "items_2005_2025.csv", index=False)
MAIN = ["きく", "カーネーション", "ばら", "ゆり", "切り枝", "スターチス", "ガーベラ", "トルコギキョウ", "りんどう", "切り葉"]
out["items_pct_ship"] = {r.item: r1(r.pct_ship, 1) for r in I.itertuples()}
out["items_share_2025"] = {r.item: r1(r.share_2025, 1) for r in I.itertuples() if r.item in MAIN}
out["kirihana_pct_2005_2025"] = grp["切り花類"]["pct_from_2005"]
out["n_items"] = int(len(I)); out["n_items_down"] = int((I.pct_ship < 0).sum())
kiku = I.set_index("item").loc["きく"]
out["kiku"] = {"ship_2005": r1(kiku.ship_2005 / 1e5, 2), "ship_2025": r1(kiku.ship_2025 / 1e5, 2), "pct": r1(kiku.pct_ship, 1),
               "share_2005": r1(kiku.share_2005, 1), "share_2025": r1(kiku.share_2025, 1)}
# きくの減少が切り花類の減少に占める割合
d_tot = kiri[2025] - kiri[2005]
out["kiku_contrib_pct"] = r1((kiku.ship_2025 - kiku.ship_2005) / d_tot * 100, 1)
top3 = I.set_index("item").loc[["きく", "カーネーション", "ばら"]]
out["top3_contrib_pct"] = r1((top3.ship_2025 - top3.ship_2005).sum() / d_tot * 100, 1)

# --- 家計の支出
avg = A[A.age == "平均"].set_index("year").sort_index()
H = pd.DataFrame({"spend": avg.spend, "freq_per100": avg.freq_per100})
H["per_purchase"] = H.spend / (H.freq_per100 / 100)
H["cpi"] = CPI.reindex(H.index)
H["real_spend_2025yen"] = H.spend / H.cpi * 100
H.reset_index().to_csv(R / "household_spend.csv", index=False)
L = LT.set_index("year").spend_nonfarm
out["household"] = {"spend_2002": r1(H.spend[2002], 0), "spend_2025": r1(H.spend[2025], 0), "pct_nominal": r1((H.spend[2025] / H.spend[2002] - 1) * 100, 1),
                    "real_2002": r1(H.real_spend_2025yen[2002], 0), "real_2025": r1(H.real_spend_2025yen[2025], 0),
                    "pct_real": r1((H.real_spend_2025yen[2025] / H.real_spend_2025yen[2002] - 1) * 100, 1),
                    "cpi_2002": r1(H.cpi[2002], 1), "cpi_pct_2002_2025": r1((100 / H.cpi[2002] - 1) * 100, 1),
                    "freq_2002": r1(H.freq_per100[2002], 0), "freq_2025": r1(H.freq_per100[2025], 0), "pct_freq": r1((H.freq_per100[2025] / H.freq_per100[2002] - 1) * 100, 1),
                    "per_purchase_2002": r1(H.per_purchase[2002], 0), "per_purchase_2025": r1(H.per_purchase[2025], 0),
                    "pct_per_purchase": r1((H.per_purchase[2025] / H.per_purchase[2002] - 1) * 100, 1),
                    "pct_real_per_purchase": r1(((H.per_purchase[2025] / H.cpi[2025]) / (H.per_purchase[2002] / H.cpi[2002]) - 1) * 100, 1),
                    "longterm_peak_year": int(L.idxmax()), "longterm_peak": r1(L.max(), 0), "longterm_1963": r1(L[1963], 0)}
real_lt = (L / CPI.reindex(L.index) * 100).dropna()
out["household"]["real_longterm_peak_year"] = int(real_lt.idxmax())
out["household"]["real_longterm_peak"] = r1(real_lt.max(), 0)
out["household"]["pct_real_from_lt_peak"] = r1((H.real_spend_2025yen[2025] / real_lt.max() - 1) * 100, 1)
pd.DataFrame({"year": L.index, "spend_nonfarm": L.values, "real_2025yen": (L / CPI.reindex(L.index) * 100).values}).to_csv(R / "household_longterm.csv", index=False)

# --- 輸入
im = IM.groupby("year", sort=True).agg(kg=("kg", "sum"), value=("value_1000yen", "sum"))
fresh = IM[IM.hs6 != "060390"].groupby("year", sort=True).agg(kg=("kg", "sum"), value=("value_1000yen", "sum"))
out["imports"] = {"kg_2009": r1(fresh.kg[2009] / 1e4, 0), "kg_2025": r1(fresh.kg[2025] / 1e4, 0), "pct_kg": r1((fresh.kg[2025] / fresh.kg[2009] - 1) * 100, 1),
                  "oku_2009": r1(fresh.value[2009] / 1e5, 1), "oku_2025": r1(fresh.value[2025] / 1e5, 1), "pct_value": r1((fresh.value[2025] / fresh.value[2009] - 1) * 100, 1),
                  "peak_kg_year": int(fresh.kg.idxmax())}
byit = IM.pivot_table(index="year", columns="name", values="kg", aggfunc="sum")
out["imports_item_pct_kg_2009_2025"] = {n: r1((byit.loc[2025, n] / byit.loc[2009, n] - 1) * 100, 1) for n in ["きく", "カーネーション", "ばら"]}
out["imports_item_kg_2025_10kt"] = {n: r1(byit.loc[2025, n] / 1e4, 0) for n in ["きく", "カーネーション", "ばら"]}
dom = {n: ser(n, "ship", "kirihana") for n in ["きく", "カーネーション", "ばら"]}
out["domestic_item_pct_2009_2025"] = {n: r1((dom[n][2025] / dom[n][2009] - 1) * 100, 1) for n in dom}
cmp_rows = []
for n in ["きく", "カーネーション", "ばら"]:
    for y in range(2009, 2026):
        cmp_rows.append({"item": n, "year": y, "import_kg": byit.loc[y, n], "domestic_1000stems": dom[n].get(y, np.nan),
                         "import_idx": byit.loc[y, n] / byit.loc[2009, n] * 100, "domestic_idx": dom[n].get(y, np.nan) / dom[n][2009] * 100})
pd.DataFrame(cmp_rows).round(3).to_csv(R / "import_vs_domestic.csv", index=False)
im.reset_index().assign(fresh_kg=fresh.kg.values, fresh_value=fresh.value.values).to_csv(R / "imports_total.csv", index=False)

# --- 仮説の判定
h = {}
v = grp["切り花類"]["pct_from_peak"]; h["H1"] = {"value": v, "rule": "<=-40", "verdict": "支持" if v <= -40 else "外れ"}
h["H2"] = {"value": [out["kiku"]["pct"], out["kirihana_pct_2005_2025"]], "rule": "きく < 計", "verdict": "支持" if out["kiku"]["pct"] < out["kirihana_pct_2005_2025"] else "外れ"}
v = out["household"]["pct_real"]; h["H3"] = {"value": v, "rule": "<=-50", "verdict": "支持" if v <= -50 else "外れ"}
v = out["imports"]["pct_kg"]; h["H4"] = {"value": v, "rule": ">0", "verdict": "支持" if v > 0 else "外れ"}
out["hypotheses"] = h

# --- 頑健性
a0 = kiri.loc[2003:2005].mean(); a1 = kiri.loc[2022:2024].mean()
kk = ser("きく", "ship", "kirihana")
out["rob_3yr"] = {"kirihana_pct": r1((a1 / a0 - 1) * 100, 1), "kiku_pct": r1((kk.loc[2022:2024].mean() / kk.loc[2003:2005].mean() - 1) * 100, 1)}
out["rob_area"] = {"kirihana_area_pct_2005_2025": grp["切り花類"]["area_pct_from_2005"], "kirihana_area_peak_year": grp["切り花類"]["area_peak_year"],
                   "kirihana_area_pct_from_peak": grp["切り花類"]["area_pct_from_peak"], "kiku_area_pct": r1(kiku.pct_area, 1)}
ov = pd.DataFrame({"t46": H.spend.loc[2002:2007], "nonfarm": L.loc[2002:2007]})
out["rob_overlap"] = {"max_abs_diff_pct": r1(((ov.t46 / ov.nonfarm - 1) * 100).abs().max(), 1),
                      "pct_2002_2007_t46": r1((ov.t46[2007] / ov.t46[2002] - 1) * 100, 1), "pct_2002_2007_nonfarm": r1((ov.nonfarm[2007] / ov.nonfarm[2002] - 1) * 100, 1)}
out["rob_import_value"] = out["imports"]["pct_value"]
rob = [
    {"check": "3年平均（2003〜05年→2022〜24年）", "result": f'切り花類 {out["rob_3yr"]["kirihana_pct"]}%、きく {out["rob_3yr"]["kiku_pct"]}%'},
    {"check": "作付面積でくらべる（2005→2025年）", "result": f'切り花類 {out["rob_area"]["kirihana_area_pct_2005_2025"]}%、きく {out["rob_area"]["kiku_area_pct"]}%'},
    {"check": "家計：第4-6表と長期時系列（農林漁家を除く）の2002〜07年", "result": f'差は最大 {out["rob_overlap"]["max_abs_diff_pct"]}%。2002→07年の変化 {out["rob_overlap"]["pct_2002_2007_t46"]}% と {out["rob_overlap"]["pct_2002_2007_nonfarm"]}%'},
    {"check": "輸入を金額で見る（2009→2025年、生鮮の切り花）", "result": f'{out["imports"]["pct_value"]}%（重さは {out["imports"]["pct_kg"]}%）'},
]
pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)
json.dump(out, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
print(I.round(1).to_string())
