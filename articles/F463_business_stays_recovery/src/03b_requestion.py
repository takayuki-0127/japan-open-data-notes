"""問い直し：50%未満の施設で、県外から来た人と県内の人の宿泊はそれぞれどう動いたか。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
z = pd.read_csv(ROOT / "data" / "stays_purpose_residence.csv")
z["unknown_res"] = z.total - z.in_pref - z.out_pref
z.to_csv(R / "requestion_residence.csv", index=False)
out = {"question": "50%未満の施設で、県外から来た人と県内の人の宿泊はそれぞれどう動いたか（居住地不詳は外国人などを含む）"}
for g in ["tourism_under50", "tourism50plus"]:
    s = z[z.group == g].set_index("year")
    out[g] = {c: {"2019_m": round(s.loc[2019, c] / 1e6, 2), "2025_m": round(s.loc[2025, c] / 1e6, 2), "ratio": round(s.loc[2025, c] / s.loc[2019, c], 3)}
              for c in ["in_pref", "out_pref", "unknown_res"]}
    out[g]["in_pref_share_2015_2019_2025"] = [round(s.loc[y, "in_pref"] / s.loc[y, "total"] * 100, 1) for y in (2015, 2019, 2025)]
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print("requestion ok")
