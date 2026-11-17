"""問い直し（結果を見てから足した）：2024年度の稲作のメタンの減少（−9%）は、作付面積で説明できるか。
前年度比を「面積の変化」と「面積あたりの変化」に分け、面積あたりの前年度比が過去の年と比べてどれだけ大きいかを見る。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
W = pd.read_csv(R / "ch4_series.csv").set_index("fy")
yo = pd.DataFrame({
    "rice_yoy_pct": W.rice.pct_change() * 100,
    "area_yoy_pct": W.rice_area_mha.pct_change() * 100,
    "per_ha_yoy_pct": W.rice_per_ha.pct_change() * 100,
}).loc[1991:2024]
yo.round(3).to_csv(R / "requestion_rice_yoy.csv")
ph = yo.per_ha_yoy_pct
prev = ph.loc[:2023]
rank = int((ph.abs() >= abs(ph.loc[2024])).sum())  # 2024年度を含めて、絶対値がそれ以上の年の数
out = {
    "rice_yoy_2024_pct": round(float(yo.rice_yoy_pct.loc[2024]), 1),
    "area_yoy_2024_pct": round(float(yo.area_yoy_pct.loc[2024]), 1),
    "per_ha_yoy_2024_pct": round(float(ph.loc[2024]), 1),
    "per_ha_yoy_max_abs_1991_2023": round(float(prev.abs().max()), 1),
    "per_ha_yoy_max_abs_year": int(prev.abs().idxmax()),
    "per_ha_yoy_sd_1991_2023": round(float(prev.std(ddof=1)), 2),
    "per_ha_2024_rank_by_abs": rank,
    "rice_per_ha_2024": round(float(W.rice_per_ha.loc[2024]), 3),
    "rice_per_ha_same_level_year": int(W.rice_per_ha.loc[:2023].sub(W.rice_per_ha.loc[2024]).abs().idxmin()),
}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
