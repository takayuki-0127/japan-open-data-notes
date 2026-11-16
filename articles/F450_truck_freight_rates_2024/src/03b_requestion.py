"""問い直し（結果を見てから足した）：今回の上昇は、前の人手不足の波（2017〜2018年度）と比べてどうか。
道路貨物輸送 ÷ 総平均（除く国際運輸）の比（相対価格）で比べる。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"
m = pd.read_csv(ROOT / "data" / "monthly.csv", index_col="ym").loc[201501:202609]
rel = (m.road / m.all_ex_intl * 100).rename("road_relative")
rel.to_csv(R / "road_relative_price.csv", float_format="%.4f")
def c(s, a, b): return float((s.loc[b] / s.loc[a] - 1) * 100)
out = {
    "wave1_road_1703_1903": round(c(m.road, 201703, 201903), 1), "wave1_allex_1703_1903": round(c(m.all_ex_intl, 201703, 201903), 1),
    "wave2_road_2303_2503": round(c(m.road, 202303, 202503), 1), "wave2_allex_2303_2503": round(c(m.all_ex_intl, 202303, 202503), 1),
    "rel_201501": round(float(rel.loc[201501]), 1), "rel_201703": round(float(rel.loc[201703]), 1), "rel_201903": round(float(rel.loc[201903]), 1),
    "rel_202303": round(float(rel.loc[202303]), 1), "rel_202503": round(float(rel.loc[202503]), 1), "rel_202609": round(float(rel.loc[202609]), 1),
    "rel_max": round(float(rel.max()), 1), "rel_max_ym": int(rel.idxmax()),
}
out["yoy_road_202609"] = round(c(m.road, 202509, 202609), 1); out["yoy_allex_202609"] = round(c(m.all_ex_intl, 202509, 202609), 1)
out["wave1_rel_change"] = round(out["rel_201903"] - out["rel_201703"], 1)
out["wave2_rel_change"] = round(out["rel_202503"] - out["rel_202303"], 1)
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(out)
