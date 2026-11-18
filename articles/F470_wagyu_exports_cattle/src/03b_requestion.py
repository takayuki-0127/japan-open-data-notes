"""問い直し（結果を見てから足した）：「輸出が和牛の増産分のどれだけを吸ったか」は、数え始めの年でどれだけ変わるか。
数え始めを2010〜2020年の各年にして、2024年までの和牛の枝肉生産量の増加と輸出（枝肉換算、歩留まり0.7）の増加をくらべる。
頭数（と畜頭数）でも同じことを見る。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
S = pd.read_csv(R / "export_vs_wagyu.csv").set_index("year")
rows = []
for y0 in range(2010, 2021):
    dw = S.loc[2024, "wagyu_t"] - S.loc[y0, "wagyu_t"]
    de = S.loc[2024, "export_carcass_t_y07"] - S.loc[y0, "export_carcass_t_y07"]
    dh = S.loc[2024, "wagyu_head"] - S.loc[y0, "wagyu_head"]
    deh = S.loc[2024, "export_head_equiv"] - S.loc[y0, "export_head_equiv"]
    rows.append({"start_year": y0, "wagyu_t_start": round(S.loc[y0, "wagyu_t"], 0), "d_wagyu_t": round(dw, 0), "d_export_carcass_t": round(de, 0),
                 "ratio_pct": round(de / dw * 100, 1) if dw > 0 else np.nan,
                 "d_wagyu_head": round(dh, 0), "d_export_head_equiv": round(deh, 0),
                 "ratio_head_pct": round(deh / dh * 100, 1) if dh > 0 else np.nan})
T = pd.DataFrame(rows)
T.to_csv(R / "requestion_start_year.csv", index=False)
low = S.loc[2010:2020, "wagyu_t"]
out = {"min_wagyu_year": int(low.idxmin()), "min_wagyu_t": round(float(low.min()), 0),
       "wagyu_t_2012": round(float(S.loc[2012, "wagyu_t"]), 0), "wagyu_t_2024": round(float(S.loc[2024, "wagyu_t"]), 0),
       "ratio_range_pct": [float(T.ratio_pct.min()), float(T.ratio_pct.max())],
       "ratio_by_start": {int(r.start_year): (None if np.isnan(r.ratio_pct) else float(r.ratio_pct)) for r in T.itertuples()},
       "n_start_years_ratio_below_50": int((T.ratio_pct < 50).sum()), "n_start_years": int(len(T)),
       "head_2019_2024": {"d_wagyu_head": float(T.set_index("start_year").loc[2019, "d_wagyu_head"]),
                          "d_export_head_equiv": float(T.set_index("start_year").loc[2019, "d_export_head_equiv"]),
                          "ratio_head_pct": float(T.set_index("start_year").loc[2019, "ratio_head_pct"])}}
M = json.load(open(R / "main.json", encoding="utf-8"))
M["requestion"] = out
json.dump(M, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(T.to_string()); print(json.dumps(out, ensure_ascii=False, indent=1))
