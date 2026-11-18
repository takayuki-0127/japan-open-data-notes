"""問い直し（結果を見てから足した）：1960年代と今とで、小麦の産地（地方の割合）はどう変わったか。
1960年代の高い自給率から1970年代の底へ、生産と消費のどちらで下がったか。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
NORTH_SOUTH = ["北海道", "東北", "北陸", "関東・東山", "東海", "近畿", "中国", "四国", "九州", "沖縄"]
PERIODS = [(1960, 1964), (1971, 1975), (2000, 2004), (2020, 2024)]


def main():
    c = pd.read_csv(DATA / "crop_wheat_region_year.csv")
    f = pd.read_csv(DATA / "fbs_wheat_fy.csv")
    rows = []
    for a, b in PERIODS:
        s = c[(c.year >= a) & (c.year <= b)].groupby("region", sort=False)[["area_ha", "harvest_t"]].mean()
        nat = s.loc["全国"]
        for g in NORTH_SOUTH:
            rows.append({"period": f"{a}〜{b}", "region": g, "harvest_t": s.loc[g, "harvest_t"], "area_ha": s.loc[g, "area_ha"],
                         "harvest_share_pct": s.loc[g, "harvest_t"] / nat["harvest_t"] * 100,
                         "area_share_pct": s.loc[g, "area_ha"] / nat["area_ha"] * 100,
                         "yield_kg10a": s.loc[g, "harvest_t"] / s.loc[g, "area_ha"] * 100 if s.loc[g, "area_ha"] > 0 else np.nan})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "requestion_region_shares.csv", index=False, float_format="%.3f")
    out = {"periods": [f"{a}〜{b}" for a, b in PERIODS]}
    for g in ["北海道", "関東・東山", "九州"]:
        out[g] = {p: {"share_pct": round(float(df[(df.period == p) & (df.region == g)].harvest_share_pct.iloc[0]), 2),
                      "harvest_kt": round(float(df[(df.period == p) & (df.region == g)].harvest_t.iloc[0]) / 1000, 1)} for p in out["periods"]}
    nat = {}
    for a, b in PERIODS:
        s = c[(c.region == "全国") & (c.year >= a) & (c.year <= b)]
        nat[f"{a}〜{b}"] = {"harvest_kt": round(float(s.harvest_t.mean()) / 1000, 1), "area_kha": round(float(s.area_ha.mean()) / 1000, 1)}
    out["national"] = nat
    # 1960〜64 → 1971〜75：自給率の低下を生産と消費に分ける
    m = lambda col, a, b: f[(f.fy >= a) & (f.fy <= b)][col].mean()
    P0, P1, C0, C1 = m("P", 1960, 1964), m("P", 1971, 1975), m("C", 1960, 1964), m("C", 1971, 1975)
    dl = np.log((P1 / C1) / (P0 / C0))
    out["fall_1960s_to_1970s"] = {"ssr0": round(P0 / C0 * 100, 2), "ssr1": round(P1 / C1 * 100, 2), "P0": round(P0, 0), "P1": round(P1, 0),
                                  "C0": round(C0, 0), "C1": round(C1, 0), "share_from_P": round(float(np.log(P1 / P0) / dl), 3),
                                  "share_from_C": round(float(-np.log(C1 / C0) / dl), 3)}
    # 今の消費のままで、1960〜64年の自給率に届くのに要る生産量
    out["P_needed_for_1960s_ssr_at_2020_24_C_kt"] = round(float(P0 / C0 * m("C", 2020, 2024)), 0)
    (RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
