"""年度ごとの合計、増加の分解、施設の比較、仮説、頑健性。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
raw = pd.read_csv(ROOT / "data" / "facilities.csv", low_memory=False, dtype={"fac_code": str})
for c in ["tons", "gen_kw", "gen_mwh", "cap_tpd", "start_fy"]:
    raw[c] = pd.to_numeric(raw[c], errors="coerce")
raw[["tons", "gen_kw", "gen_mwh"]] = raw[["tons", "gen_kw", "gen_mwh"]].fillna(0.0)
cf = raw.gen_mwh / (raw.gen_kw / 1000 * 8784)


def clean(mode):
    f = raw.copy()
    if mode == "fix":  # 本線：設備利用率が10を超える行は kWh の書き間違いとみなして1000で割る
        bad = (f.gen_kw > 0) & (cf > 10)
        f.loc[bad, "gen_mwh"] = f.loc[bad, "gen_mwh"] / 1000
    elif mode == "drop":  # 頑健性：発電能力×時間を超える行（能力0で発電ありを含む）を除く
        f = f[~((cf > 1) | ((f.gen_kw == 0) & (f.gen_mwh > 0)))]
    f["is_gen"] = f.gen_mwh > 0
    return f


def yearly(f):
    g = f.groupby("fy", sort=True)
    y = pd.DataFrame({
        "facilities": g.size(), "tons_mt": g.tons.sum() / 1e6,
        "gen_facilities": g.is_gen.sum(),
        "tons_at_gen_mt": f[f.is_gen].groupby("fy").tons.sum() / 1e6,
        "gen_twh": g.gen_mwh.sum() / 1e6,
        "gen_gw": f[f.is_gen].groupby("fy").gen_kw.sum() / 1e6,
    })
    y["share_tons_at_gen_pct"] = y.tons_at_gen_mt / y.tons_mt * 100
    y["kwh_per_t_all"] = y.gen_twh * 1e9 / (y.tons_mt * 1e6)
    y["kwh_per_t_gen"] = y.gen_twh * 1e9 / (y.tons_at_gen_mt * 1e6)
    y["cap_factor_pct"] = y.gen_twh * 1000 / (y.gen_gw * 8760) * 100  # TWh ÷ (GW×8760h/1000)
    return y


def decompose(y, a, b):
    lg = np.log(y.gen_twh.loc[b] / y.gen_twh.loc[a])
    parts = {"tons": np.log(y.tons_mt.loc[b] / y.tons_mt.loc[a]),
             "share_at_gen": np.log(y.share_tons_at_gen_pct.loc[b] / y.share_tons_at_gen_pct.loc[a]),
             "kwh_per_t_gen": np.log(y.kwh_per_t_gen.loc[b] / y.kwh_per_t_gen.loc[a])}
    return {k: float(v / lg * 100) for k, v in parts.items()}, float((y.gen_twh.loc[b] / y.gen_twh.loc[a] - 1) * 100)


F = clean("fix")
Y = yearly(F)
Y.round(4).to_csv(R / "yearly.csv")
dec, growth = decompose(Y, 2005, 2024)

# H2：2024年度の発電施設、使用開始年度別の1トンあたりの発電量
z = F[(F.fy == 2024) & F.is_gen & (F.tons > 0)].copy()
z["kwh_t"] = z.gen_mwh * 1000 / z.tons
z["era"] = pd.cut(z.start_fy, [0, 1999, 2009, 2100], labels=["〜1999年度", "2000〜2009年度", "2010年度〜"])
era = z.groupby("era", observed=True).kwh_t.agg(["count", "median", "mean"]).round(2)
era.to_csv(R / "kwh_per_t_by_start_2024.csv")
h2_ratio = float(era.loc["2010年度〜", "median"] / era.loc["〜1999年度", "median"])
h2_ratio_mean = float(era.loc["2010年度〜", "mean"] / era.loc["〜1999年度", "mean"])

# H3：規模別の発電施設の割合
sz = F[F.fy.isin([2005, 2014, 2024]) & (F.tons > 0)].copy()
sz["size"] = pd.cut(sz.cap_tpd, [0, 49.99, 99.99, 199.99, 1e9], labels=["50t/日未満", "50〜100t/日", "100〜200t/日", "200t/日以上"])
size_tab = (sz.groupby(["size", "fy"], observed=True).is_gen.mean() * 100).unstack("fy").round(2)
size_tab.to_csv(R / "gen_share_by_size.csv")
big = F[(F.fy == 2024) & (F.cap_tpd >= 100) & (F.tons > 0)]
h3 = float(big.is_gen.mean() * 100)

# H4：設備利用率
cf05, cf24 = float(Y.cap_factor_pct.loc[2005]), float(Y.cap_factor_pct.loc[2024])

# ---- 頑健性 -------------------------------------------------------------------------------
rob = []
for name, f, a, b in [("本線：書き間違いを直す、2005→2024年度", F, 2005, 2024),
                      ("能力×時間を超える行を除く、2005→2024年度", clean("drop"), 2005, 2024),
                      ("期間：2013→2024年度", F, 2013, 2024),
                      ("900kWh/t 超の施設を除く、2005→2024年度", F[~((F.tons > 0) & (F.gen_mwh * 1000 / F.tons.where(F.tons > 0) > 900))], 2005, 2024)]:
    yy = yearly(f); d, gr = decompose(yy, a, b)
    rob.append({"check": name, "gen_growth_pct": round(gr, 1), "contrib_tons_pct": round(d["tons"], 1),
                "contrib_share_at_gen_pct": round(d["share_at_gen"], 1), "contrib_kwh_per_t_gen_pct": round(d["kwh_per_t_gen"], 1),
                "kwh_per_t_gen_start": round(float(yy.kwh_per_t_gen.loc[a]), 1), "kwh_per_t_gen_end": round(float(yy.kwh_per_t_gen.loc[b]), 1),
                "cap_factor_start": round(float(yy.cap_factor_pct.loc[a]), 1), "cap_factor_end": round(float(yy.cap_factor_pct.loc[b]), 1)})
rob = pd.DataFrame(rob)
rob.to_csv(R / "robustness.csv", index=False)

main = {
    "n_rows_fixed_kwh": int(((raw.gen_kw > 0) & (cf > 10)).sum()),
    "n_rows_over_capacity": int(((cf > 1) | ((raw.gen_kw == 0) & (raw.gen_mwh > 0))).sum()),
    "gen_twh_2005": round(float(Y.gen_twh.loc[2005]), 3), "gen_twh_2024": round(float(Y.gen_twh.loc[2024]), 3),
    "gen_growth_pct": round(growth, 1),
    "tons_mt_2005": round(float(Y.tons_mt.loc[2005]), 2), "tons_mt_2024": round(float(Y.tons_mt.loc[2024]), 2),
    "tons_change_pct": round(float((Y.tons_mt.loc[2024] / Y.tons_mt.loc[2005] - 1) * 100), 1),
    "facilities_2005": int(Y.facilities.loc[2005]), "facilities_2024": int(Y.facilities.loc[2024]),
    "gen_facilities_2005": int(Y.gen_facilities.loc[2005]), "gen_facilities_2024": int(Y.gen_facilities.loc[2024]),
    "share_tons_at_gen_2005": round(float(Y.share_tons_at_gen_pct.loc[2005]), 1), "share_tons_at_gen_2024": round(float(Y.share_tons_at_gen_pct.loc[2024]), 1),
    "kwh_per_t_gen_2005": round(float(Y.kwh_per_t_gen.loc[2005]), 1), "kwh_per_t_gen_2024": round(float(Y.kwh_per_t_gen.loc[2024]), 1),
    "kwh_per_t_all_2005": round(float(Y.kwh_per_t_all.loc[2005]), 1), "kwh_per_t_all_2024": round(float(Y.kwh_per_t_all.loc[2024]), 1),
    "gen_gw_2005": round(float(Y.gen_gw.loc[2005]), 3), "gen_gw_2024": round(float(Y.gen_gw.loc[2024]), 3),
    "decomp_pct": {k: round(v, 1) for k, v in dec.items()},
    "era_median_kwh_t": {str(k): float(v) for k, v in era["median"].items()},
    "era_count": {str(k): int(v) for k, v in era["count"].items()},
    "big_gen_share_2024": round(h3, 1),
    "size_gen_share": {str(k): {int(c): float(v) for c, v in row.items()} for k, row in size_tab.iterrows()},
    "cap_factor_2005": round(cf05, 1), "cap_factor_2024": round(cf24, 1),
    "hypotheses": {
        "H1_kwh_per_t_contrib_ge_100": {"value": round(dec["kwh_per_t_gen"], 1), "result": "支持" if dec["kwh_per_t_gen"] >= 100 else "外れ"},
        "H2_new_vs_old_median_ge_1_5": {"value": round(h2_ratio, 2), "mean_ratio": round(h2_ratio_mean, 2), "result": "支持" if h2_ratio >= 1.5 else "外れ"},
        "H3_big_gen_share_ge_75": {"value": round(h3, 1), "result": "支持" if h3 >= 75 else "外れ"},
        "H4_cf_rise_lt_5pt": {"value": round(cf24 - cf05, 1), "result": "支持" if (cf24 - cf05) < 5 else "外れ"},
    },
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1))
print(rob.to_string()); print(Y.round(2).to_string()); print(era); print(size_tab)
