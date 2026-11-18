"""頭数の変化の分解、輸出の割合、仮説の判定、頑健性。結果は results/ に出す。乱数は使わない。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"; R = ROOT / "results"
YIELD = 0.7            # 部分肉の歩留まり（置いた値）
YIELDS = [0.6, 0.7, 0.8]
H = pd.read_csv(D / "cattle_heads.csv")
M = pd.read_csv(D / "slaughter_carcass.csv")
P = pd.read_csv(D / "wagyu_price.csv")
E = pd.read_csv(D / "beef_export_hs4.csv")
VARS = ["farms", "total", "beef_breed", "kuroge", "breeding_cows", "dairy_breed", "holstein", "cross", "per_farm"]
out = {}


def r1(x, k=1):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


# --- 頭数：旧・新をつないだ系列（新の水準にそろえる。2019年の新÷旧の比を2019年以前に掛ける）
old = H[H.method == "old"].set_index("year")[VARS]
new = H[H.method == "new"].set_index("year")[VARS]
ratio = new.loc[2019] / old.loc[2019]
linked = pd.concat([old.loc[:2018] * ratio, new.loc[2019:]]).sort_index()
raw = pd.concat([old.loc[:2019], new.loc[2020:]]).sort_index()   # つながない系列（2019年は旧）
linked.reset_index().to_csv(R / "heads_linked.csv", index=False)
out["link_ratio_2019_new_over_old"] = {k: r1(ratio[k], 4) for k in ["total", "beef_breed", "holstein", "cross", "farms"]}
out["heads_2019"] = {"old_total": r1(old.loc[2019, "total"], 0), "new_total": r1(new.loc[2019, "total"], 0)}


def decompose(S, y0, y1):
    d = S.loc[y1] - S.loc[y0]
    tot = d["total"]
    return {"y0": int(y0), "y1": int(y1), "total_y0": r1(S.loc[y0, "total"], 0), "total_y1": r1(S.loc[y1, "total"], 0),
            "d_total": r1(tot, 0), "d_beef": r1(d["beef_breed"], 0), "d_holstein": r1(d["holstein"], 0), "d_cross": r1(d["cross"], 0),
            "share_beef": r1(d["beef_breed"] / tot * 100, 1), "share_holstein": r1(d["holstein"] / tot * 100, 1), "share_cross": r1(d["cross"] / tot * 100, 1),
            "d_breeding_cows": r1(d["breeding_cows"], 0), "pct_total": r1(d["total"] / S.loc[y0, "total"] * 100, 1),
            "pct_beef": r1(d["beef_breed"] / S.loc[y0, "beef_breed"] * 100, 1), "pct_breeding": r1(d["breeding_cows"] / S.loc[y0, "breeding_cows"] * 100, 1)}


trough = int(linked.loc[2010:2019, "total"].idxmin()); peak = int(linked.loc[2020:2025, "total"].idxmax())
main_dec = decompose(linked, trough, peak)
out["H1_decomp_linked"] = main_dec
out["decomp_peak_to_2025"] = decompose(linked, peak, 2025)
out["decomp_2010_2025"] = decompose(linked, 2010, 2025)
# 頑健性：つながない系列
tr_raw = int(raw.loc[2010:2019, "total"].idxmin()); pk_raw = int(raw.loc[2020:2025, "total"].idxmax())
out["rob_unlinked"] = decompose(raw, tr_raw, pk_raw)
pd.DataFrame([dict(series="linked", **main_dec), dict(series="unlinked", **out["rob_unlinked"]),
              dict(series="linked_peak_to_2025", **out["decomp_peak_to_2025"]), dict(series="linked_2010_2025", **out["decomp_2010_2025"])]).to_csv(R / "heads_decomposition.csv", index=False)

# --- 輸出と和牛の生産
ex = E.groupby("year", sort=True).agg(kg=("kg", "sum"), value=("value_1000yen", "sum")).reset_index()
ex["export_t"] = ex.kg / 1000
ex["export_oku_yen"] = ex.value / 1e5
m = M[["year", "wagyu_head", "wagyu_t", "cross_head", "cross_t", "dairy_head", "dairy_t", "adult_total_t"]].copy()
m["wagyu_kg_per_head"] = m.wagyu_t * 1000 / m.wagyu_head
S = ex.merge(m, on="year", how="left").merge(P, on="year", how="left")
for yv in YIELDS:
    tag = f"{int(yv * 10):02d}"
    S[f"export_carcass_t_y{tag}"] = S.export_t / yv
    S[f"share_of_wagyu_pct_y{tag}"] = S[f"export_carcass_t_y{tag}"] / S.wagyu_t * 100
S["export_head_equiv"] = S.export_carcass_t_y07 * 1000 / S.wagyu_kg_per_head
S["domestic_wagyu_t_lower"] = S.wagyu_t - S.export_carcass_t_y07
S["value_share_pct"] = S.value * 1000 / (S.wagyu_t * 1000 * S.wagyu_price_yen_kg) * 100
S.to_csv(R / "export_vs_wagyu.csv", index=False)

g = S.set_index("year")
out["export"] = {y: {"t": r1(g.loc[y, "export_t"], 0), "oku_yen": r1(g.loc[y, "export_oku_yen"], 1)} for y in [2009, 2012, 2019, 2020, 2024, 2025]}
out["export_growth_2012_2025_x"] = r1(g.loc[2025, "export_t"] / g.loc[2012, "export_t"], 1)
out["wagyu_prod"] = {y: {"carcass_t": r1(g.loc[y, "wagyu_t"], 0), "head": r1(g.loc[y, "wagyu_head"], 0), "kg_per_head": r1(g.loc[y, "wagyu_kg_per_head"], 1)} for y in [2009, 2012, 2019, 2024]}
out["H2_share_2024_pct"] = {f"y{t}": r1(g.loc[2024, f"share_of_wagyu_pct_y{t}"], 1) for t in ["06", "07", "08"]}
out["share_2012_pct_y07"] = r1(g.loc[2012, "share_of_wagyu_pct_y07"], 1)
out["export_head_equiv_2024"] = r1(g.loc[2024, "export_head_equiv"], 0)
out["export_head_equiv_2012"] = r1(g.loc[2012, "export_head_equiv"], 0)


def absorb(y0, y1, tag="07", df=g):
    dw = df.loc[y1, "wagyu_t"] - df.loc[y0, "wagyu_t"]
    de = df.loc[y1, f"export_carcass_t_y{tag}"] - df.loc[y0, f"export_carcass_t_y{tag}"]
    return {"y0": y0, "y1": y1, "d_wagyu_t": r1(dw, 0), "d_export_carcass_t": r1(de, 0), "ratio_pct": r1(de / dw * 100, 1)}


out["H3_absorb_2012_2024"] = {f"y{t}": absorb(2012, 2024, t) for t in ["06", "07", "08"]}
out["absorb_2019_2024"] = absorb(2019, 2024)
out["domestic_wagyu_lower"] = {y: r1(g.loc[y, "domestic_wagyu_t_lower"], 0) for y in [2012, 2019, 2024]}
out["value_share_pct"] = {y: r1(g.loc[y, "value_share_pct"], 1) for y in [2012, 2019, 2024]}
out["wagyu_price"] = {y: r1(g.loc[y, "wagyu_price_yen_kg"], 0) for y in [2012, 2019, 2024]}
# 3年平均でくらべる（頑健性）
a0 = g.loc[2010:2012].mean(numeric_only=True); a1 = g.loc[2022:2024].mean(numeric_only=True)
out["rob_3yr"] = {"share_pct_y07_2022_24": r1(a1.export_carcass_t_y07 / a1.wagyu_t * 100, 1),
                  "absorb_ratio_pct": r1((a1.export_carcass_t_y07 - a0.export_carcass_t_y07) / (a1.wagyu_t - a0.wagyu_t) * 100, 1),
                  "d_wagyu_t": r1(a1.wagyu_t - a0.wagyu_t, 0), "d_export_carcass_t": r1(a1.export_carcass_t_y07 - a0.export_carcass_t_y07, 0)}

# --- 戸数と規模
out["H4_farms"] = {"farms_2015": r1(raw.loc[2015, "farms"], 0), "farms_2025": r1(raw.loc[2025, "farms"], 0),
                   "pct_farms_linked": r1((linked.loc[2025, "farms"] / linked.loc[2015, "farms"] - 1) * 100, 1),
                   "pct_farms_raw": r1((raw.loc[2025, "farms"] / raw.loc[2015, "farms"] - 1) * 100, 1),
                   "per_farm_2015": r1(raw.loc[2015, "per_farm"], 1), "per_farm_2025": r1(raw.loc[2025, "per_farm"], 1),
                   "per_farm_x_raw": r1(raw.loc[2025, "per_farm"] / raw.loc[2015, "per_farm"], 2),
                   "per_farm_x_linked": r1(linked.loc[2025, "per_farm"] / linked.loc[2015, "per_farm"], 2)}

# --- 仮説の判定
h = {}
h["H1"] = {"value": main_dec["share_beef"], "rule": ">=60", "verdict": "支持" if main_dec["share_beef"] >= 60 else "外れ"}
s24 = out["H2_share_2024_pct"]["y07"]
h["H2"] = {"value": s24, "rule": "<10", "verdict": "支持" if s24 < 10 else "外れ"}
a = out["H3_absorb_2012_2024"]["y07"]["ratio_pct"]
h["H3"] = {"value": a, "rule": "<50", "verdict": "支持" if a < 50 else "外れ"}
f4 = out["H4_farms"]
ok4 = f4["pct_farms_raw"] <= -30 and f4["per_farm_x_raw"] >= 1.5
h["H4"] = {"value": [f4["pct_farms_raw"], f4["per_farm_x_raw"]], "rule": "<=-30% and >=1.5x", "verdict": "支持" if ok4 else "外れ"}
out["hypotheses"] = h

# --- 頑健性の表
rob = [
    {"check": "歩留まり0.6・0.7・0.8（2024年の和牛に対する輸出の割合、%）", "result": "／".join(str(out["H2_share_2024_pct"][k]) for k in ["y06", "y07", "y08"])},
    {"check": "歩留まり0.6・0.7・0.8（2012→2024年の和牛の増加に対する輸出の増加、%）", "result": "／".join(str(out["H3_absorb_2012_2024"][k]["ratio_pct"]) for k in ["y06", "y07", "y08"])},
    {"check": "2019年の旧・新をつながない（底→山の肉用種の割合、%）", "result": f'{out["rob_unlinked"]["y0"]}→{out["rob_unlinked"]["y1"]}年 {out["rob_unlinked"]["share_beef"]}'},
    {"check": "3年平均（2010〜12年→2022〜24年）", "result": f'輸出の割合 {out["rob_3yr"]["share_pct_y07_2022_24"]}%、増加の比 {out["rob_3yr"]["absorb_ratio_pct"]}%'},
    {"check": "金額でくらべる（輸出額÷和牛の枝肉の市場価格での額、2024年、%）", "result": str(out["value_share_pct"][2024])},
]
pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)
json.dump(out, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
