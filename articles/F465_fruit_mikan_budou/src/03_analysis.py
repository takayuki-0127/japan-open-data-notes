"""面積・収穫量・産出額の推移、産出額の変化の分解（面積・単収・1kg あたり産出額）、仮説の判定、頑健性、主な産地。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
D = ROOT / "data"; R = ROOT / "results"
MAIN = ["みかん", "ぶどう", "りんご", "日本なし", "もも", "かき", "おうとう"]


def r(x, n=1):
    return None if pd.isna(x) else float(round(float(x), n))


def decomp(df, item, y0, y1, qty="harvest_t"):
    """産出額 = 面積 × 単収 × 1kg あたり産出額。y0, y1 は年か、年のリスト（平均）。"""
    g = df[df.item == item].set_index("year")
    pick = lambda y: g.loc[y if isinstance(y, list) else [y]].mean(numeric_only=True)
    a, b = pick(y0), pick(y1)
    la = np.log(b.area_ha / a.area_ha)
    ly = np.log((b[qty] / b.area_ha) / (a[qty] / a.area_ha))
    lp = np.log((b.value_oku / b[qty]) / (a.value_oku / a[qty]))
    lv = np.log(b.value_oku / a.value_oku)
    return {"value_change_pct": r((np.exp(lv) - 1) * 100), "area_change_pct": r((np.exp(la) - 1) * 100),
            "yield_change_pct": r((np.exp(ly) - 1) * 100), "unit_value_change_pct": r((np.exp(lp) - 1) * 100),
            "harvest_change_pct": r((b[qty] / a[qty] - 1) * 100),
            "log_share_area_pct": r(la / lv * 100) if abs(lv) > 1e-9 else None,
            "value0_oku": r(a.value_oku, 0), "value1_oku": r(b.value_oku, 0),
            "unit_value0_yen_kg": r(a.value_oku * 1e5 / a[qty], 0), "unit_value1_yen_kg": r(b.value_oku * 1e5 / b[qty], 0),
            "log_area": r(la, 4), "log_yield": r(ly, 4), "log_unit_value": r(lp, 4), "log_value": r(lv, 4)}


def main():
    nat = pd.read_csv(D / "fruit_national.csv")
    val = pd.read_csv(D / "output_value.csv")
    tot = pd.read_csv(D / "fruit_total_value.csv").set_index("year")
    df = nat.merge(val, on=["item", "year"], how="left")
    df["yield_kg_10a"] = df.harvest_t * 1000 / (df.area_ha * 10)
    df["unit_value_yen_kg"] = df.value_oku * 1e5 / df.harvest_t
    df["share_of_fruit_value_pct"] = df.value_oku / df.year.map(tot.fruit_total_oku) * 100
    df[df.item.isin(MAIN)].to_csv(R / "national_series.csv", index=False, float_format="%.3f")

    m = df.set_index(["item", "year"])
    out = {"series": {}}
    for it in ["みかん", "ぶどう"]:
        g = m.loc[it]
        out["series"][it] = {str(y): {"area_ha": r(g.area_ha[y], 0), "harvest_t": r(g.harvest_t[y], 0), "value_oku": r(g.value_oku.get(y), 0),
                                      "unit_value_yen_kg": r(g.unit_value_yen_kg.get(y), 0), "yield_kg_10a": r(g.yield_kg_10a[y], 0),
                                      "share_of_fruit_value_pct": r(g.share_of_fruit_value_pct.get(y))}
                             for y in [1973, 1985, 1994, 2003, 2004, 2009, 2014, 2020, 2023, 2024]}
        peak = g.area_ha.idxmax()
        out["series"][it]["area_peak"] = {"year": int(peak), "area_ha": r(g.area_ha[peak], 0)}
    out["fruit_total_value_oku"] = {str(y): r(tot.fruit_total_oku[y], 0) for y in [2003, 2004, 2024]}
    # 産出額の順位（ぶどうがみかんを上回った最初の年）
    v = val.pivot(index="year", columns="item", values="value_oku")
    over = [int(y) for y in v.index if v.loc[y, "ぶどう"] > v.loc[y, "みかん"]]
    out["budou_over_mikan_years"] = over

    # 仮説
    a04, a24 = m.loc[("みかん", 2004)], m.loc[("みかん", 2024)]
    da = (a24.area_ha / a04.area_ha - 1) * 100; dh = (a24.harvest_t / a04.harvest_t - 1) * 100
    out["H1"] = {"area_change_pct": r(da), "harvest_change_pct": r(dh), "judge": "支持" if (da <= -20 and dh <= -20) else "外れ"}
    b04, b24 = m.loc[("ぶどう", 2004)], m.loc[("ぶどう", 2024)]
    out["H2"] = {"area_2004": r(b04.area_ha, 0), "area_2024": r(b24.area_ha, 0), "change_pct": r((b24.area_ha / b04.area_ha - 1) * 100),
                 "harvest_change_pct": r((b24.harvest_t / b04.harvest_t - 1) * 100), "judge": "支持" if b24.area_ha < b04.area_ha else "外れ"}
    dv = (b24.value_oku / b04.value_oku - 1) * 100
    out["H3"] = {"value_2004": r(b04.value_oku, 0), "value_2024": r(b24.value_oku, 0), "change_pct": r(dv), "judge": "支持" if dv >= 50 else "外れ"}
    up_b = b24.unit_value_yen_kg / b04.unit_value_yen_kg; up_m = a24.unit_value_yen_kg / a04.unit_value_yen_kg
    out["H4"] = {"budou_unit_value_ratio": r(up_b, 2), "mikan_unit_value_ratio": r(up_m, 2), "judge": "支持" if up_b > up_m else "外れ"}

    # 分解
    dec = {it: decomp(df, it, 2004, 2024) for it in MAIN}
    out["decomp_2004_2024"] = dec
    pd.DataFrame(dec).T.to_csv(R / "decomp_2004_2024.csv", float_format="%.4f")

    # 頑健性
    rob = {}
    rob["R1_3yr_avg"] = {it: decomp(df, it, [2003, 2004, 2005], [2022, 2023, 2024]) for it in ["みかん", "ぶどう"]}
    rob["R2_shipped"] = {it: decomp(df, it, 2004, 2024, qty="shipped_t") for it in ["みかん", "ぶどう"]}
    rob["R3_base_2009"] = {it: decomp(df, it, 2009, 2024) for it in ["みかん", "ぶどう"]}
    others = {it: dec[it]["unit_value_change_pct"] for it in MAIN}
    rob["R4_unit_value_change_all"] = others
    rob["R4_n_items_value_up"] = int(sum(dec[it]["value_change_pct"] > 0 for it in MAIN))
    out["robustness"] = rob

    # 主な産地（2004年と2024年の両方に数字がある県）
    pref = pd.read_csv(D / "fruit_pref.csv")
    rows = []
    for it in ["みかん", "ぶどう"]:
        p = pref[pref.item == it]
        w = p.pivot(index=["pref_code", "pref"], columns="year", values="area_ha")
        nat_a = m.loc[it].area_ha
        for (code, nm), row in w.iterrows():
            if pd.notna(row.get(2004)) and pd.notna(row.get(2024)):
                rows.append({"item": it, "pref_code": code, "pref": nm, "area_2004": row[2004], "area_2024": row[2024],
                             "share_2004_pct": row[2004] / nat_a[2004] * 100, "share_2024_pct": row[2024] / nat_a[2024] * 100,
                             "change_pct": (row[2024] / row[2004] - 1) * 100})
    pr = pd.DataFrame(rows).sort_values(["item", "pref_code"])
    pr.to_csv(R / "pref_area_2004_2024.csv", index=False, float_format="%.3f")
    big = pr[pr.share_2004_pct >= 3]
    out["pref_main"] = {it: {g.pref: {"area_2004": r(g.area_2004, 0), "area_2024": r(g.area_2024, 0), "change_pct": r(g.change_pct),
                                      "share_2024_pct": r(g.share_2024_pct)} for g in big[big.item == it].itertuples()} for it in ["みかん", "ぶどう"]}
    out["pref_n_up"] = {it: {"n_pref": int((pr.item == it).sum()), "n_area_up": int(((pr.item == it) & (pr.change_pct > 0)).sum())} for it in ["みかん", "ぶどう"]}
    json.dump(out, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps({k: out[k] for k in ["H1", "H2", "H3", "H4", "budou_over_mikan_years", "pref_main", "pref_n_up", "fruit_total_value_oku"]}, ensure_ascii=False, indent=1))
    print(pd.DataFrame(dec).T[["value_change_pct", "area_change_pct", "yield_change_pct", "unit_value_change_pct", "value0_oku", "value1_oku", "unit_value0_yen_kg", "unit_value1_yen_kg"]].to_string())
    for k in ["R1_3yr_avg", "R2_shipped", "R3_base_2009"]:
        print(k, {it: {kk: rob[k][it][kk] for kk in ["value_change_pct", "area_change_pct", "unit_value_change_pct"]} for it in rob[k]})
    print(json.dumps(out["series"], ensure_ascii=False)[:3000])


if __name__ == "__main__":
    main()
