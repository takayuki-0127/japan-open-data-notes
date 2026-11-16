"""問い直し（結果を見てから足した）：温泉地全体の延べ宿泊は30年で1割ほどの減りだったが、国民保養温泉地では4割減った。
国民保養温泉地の延べ宿泊が全体に占める割合と、それを除いた残りの推移を見る。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"
d = pd.read_csv(R / "onsen_series.csv", index_col="fy").loc[1976:]
d["kokumin_share"] = d.kokumin_stays / d.stays * 100
d["other_stays"] = d.stays - d.kokumin_stays
d[["stays", "kokumin_stays", "other_stays", "kokumin_share"]].to_csv(R / "requestion_kokumin.csv", float_format="%.3f")
p = lambda c, a, b: round(float((d.loc[b, c] / d.loc[a, c] - 1) * 100), 1)
out = {"share_1994": round(float(d.loc[1994, "kokumin_share"]), 1), "share_2024": round(float(d.loc[2024, "kokumin_share"]), 1),
       "kokumin_peak_fy": int(d.kokumin_stays.idxmax()), "kokumin_peak": float(d.kokumin_stays.max()),
       "kokumin_1994": float(d.loc[1994, "kokumin_stays"]), "kokumin_2024": float(d.loc[2024, "kokumin_stays"]),
       "other_pct_1994_2024": p("other_stays", 1994, 2024), "kokumin_pct_1994_2024": p("kokumin_stays", 1994, 2024),
       "kokumin_pct_2019_2024": p("kokumin_stays", 2019, 2024), "other_pct_2019_2024": p("other_stays", 2019, 2024)}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(out)
