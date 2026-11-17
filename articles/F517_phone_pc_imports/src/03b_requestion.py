"""問い直し（結果を見てから足した）：電算機類（含周辺機器）の輸入で、中国の割合が2021年77.6%から2025年62.8%へ下がった。
中国以外からの輸入（世界−中国）は、台数と金額のどちらで増えたのか。単価は中国と中国以外でどう違うか。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "imports.csv")
x = d[d.item == "computers"].pivot(index="year", columns="area", values=["qty", "value_thousand_yen"])
rows = []
for y in range(2017, int(x.index.max()) + 1):
    wq, wv = x.loc[y, ("qty", "世界")], x.loc[y, ("value_thousand_yen", "世界")] * 1000
    cq, cv = x.loc[y, ("qty", "中国")], x.loc[y, ("value_thousand_yen", "中国")] * 1000
    rows.append({"year": y, "china_qty_m": round(cq / 1e6, 3), "china_value_t": round(cv / 1e12, 4), "china_unit_yen": round(cv / cq, 0),
                 "other_qty_m": round((wq - cq) / 1e6, 3), "other_value_t": round((wv - cv) / 1e12, 4), "other_unit_yen": round((wv - cv) / (wq - cq), 0),
                 "china_qty_share": round(100 * cq / wq, 2), "china_value_share": round(100 * cv / wv, 2)})
t = pd.DataFrame(rows).set_index("year")
t.to_csv(R / "computers_china_vs_other.csv")
res = {"china_value_share": {str(y): float(t.china_value_share[y]) for y in [2017, 2021, 2025]},
       "china_qty_share": {str(y): float(t.china_qty_share[y]) for y in [2017, 2021, 2025]},
       "other_value_t": {str(y): float(t.other_value_t[y]) for y in [2017, 2021, 2025]},
       "china_value_t": {str(y): float(t.china_value_t[y]) for y in [2017, 2021, 2025]},
       "china_unit_yen": {str(y): float(t.china_unit_yen[y]) for y in [2017, 2021, 2025]},
       "other_unit_yen": {str(y): float(t.other_unit_yen[y]) for y in [2017, 2021, 2025]},
       "other_qty_m": {str(y): float(t.other_qty_m[y]) for y in [2017, 2021, 2025]},
       "china_qty_m": {str(y): float(t.china_qty_m[y]) for y in [2017, 2021, 2025]}}
(R / "requestion.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(t.to_string())
