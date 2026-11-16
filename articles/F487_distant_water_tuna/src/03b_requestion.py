"""問い直し（結果を見てから足した）：遠洋漁業の減少のうち、カツオ・マグロの3漁法の分はどれくらいか。
遠洋漁業（部門別）を「カツオ・マグロの3漁法（種類別）」と「それ以外の遠洋」に分け、最大の年（1987年）→2000年→2024年の減り方を比べる。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
b = pd.read_csv(R / "bumon_series.csv").set_index("year")
s = pd.read_csv(R / "shurui_series.csv").set_index("year")
d = pd.DataFrame({"distant": b.distant, "tuna3": s.tuna3_distant.reindex(b.index)})
d["other_distant"] = d.distant - d.tuna3
d["tuna3_share_pct"] = d.tuna3 / d.distant * 100
d.round(3).to_csv(R / "requestion_split.csv")
py = int(d.distant.idxmax())
out = {"peak_year": py}
for a, z in [(py, 2000), (2000, 2024), (py, 2024)]:
    dd = d.loc[z] - d.loc[a]
    out[f"{a}-{z}"] = {"distant_change_kt": round(float(dd.distant), 1), "tuna3_change_kt": round(float(dd.tuna3), 1),
                       "other_change_kt": round(float(dd.other_distant), 1),
                       "tuna3_share_of_change_pct": round(float(dd.tuna3 / dd.distant * 100), 1)}
out["tuna3_share_peak_year_pct"] = round(float(d.tuna3_share_pct.loc[py]), 1)
out["tuna3_share_2000_pct"] = round(float(d.tuna3_share_pct.loc[2000]), 1)
out["tuna3_share_2024_pct"] = round(float(d.tuna3_share_pct.loc[2024]), 1)
out["other_peak_kt"] = round(float(d.other_distant.loc[py]), 1); out["other_2024_kt"] = round(float(d.other_distant.loc[2024]), 1)
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
