"""問い直し（結果を見てから足した）：道路は延び続けているが、延び方は遅くなっているのか。地方別（北から南）に1人あたりの道路も見る。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"
nat = pd.read_csv(R / "national_road_pop.csv")
pf = pd.read_csv(R / "prefecture_road_pop.csv", index_col="code")
pop = pd.read_csv(ROOT / "data" / "population_thousand.csv", index_col="code"); pop.columns = pop.columns.astype(int)
# 5年ごとの1年あたりの増加（km/年）、年度当初の時点（2019年からは年度末）
T = nat.set_index("t")
pts = [1975.25, 1980.25, 1985.25, 1990.25, 1995.25, 2000.25, 2005.25, 2008.25, 2010.25, 2015.25, 2019.25, 2024.25]
rows = []
for a, b in zip(pts[:-1], pts[1:]):
    rows.append(dict(start=a, end=b, km_per_year=(T.loc[b, "total_km"] - T.loc[a, "total_km"]) / (b - a),
                     municipal_km_per_year=(T.loc[b, "municipal"] - T.loc[a, "municipal"]) / (b - a)))
pace = pd.DataFrame(rows); pace.to_csv(R / "requestion_pace.csv", index=False, float_format="%.1f")
REG = {"北海道": [1], "東北": range(2, 8), "関東": range(8, 15), "中部": range(15, 24), "近畿": range(24, 31),
       "中国": range(31, 36), "四国": range(36, 40), "九州・沖縄": range(40, 48)}
reg = []
for k, codes in REG.items():
    c = list(codes)
    r15 = pf.loc[c, "road_2016ed_km"].sum(); r23 = pf.loc[c, "road_2025ed_km"].sum()
    p15 = pop.loc[c, 2015].sum(); p23 = pop.loc[c, 2023].sum()
    reg.append(dict(region=k, road_pct=(r23 / r15 - 1) * 100, pop_pct=(p23 / p15 - 1) * 100,
                    m_per_person_2015=r15 / p15, m_per_person_2023=r23 / p23,
                    m_per_person_pct=((r23 / p23) / (r15 / p15) - 1) * 100))
rg = pd.DataFrame(reg); rg.to_csv(R / "requestion_regions.csv", index=False, float_format="%.3f")
out = {"pace": {f"{int(r.start)}-{int(r.end)}": round(r.km_per_year) for r in pace.itertuples()},
       "regions": {r.region: {k: round(getattr(r, k), 2) for k in ["road_pct", "pop_pct", "m_per_person_2015", "m_per_person_2023", "m_per_person_pct"]} for r in rg.itertuples()}}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
