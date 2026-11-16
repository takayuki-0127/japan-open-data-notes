"""問い直し（結果を見てから足した）：小口化は、出荷する業種（製造業・卸売業・倉庫業など）のどこで進んだのか（2005→2021年）。
あわせて、一車貸切（トラックを1台借り切る運び方）の件数とロットの変化を見る。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "industry.csv")
d["lot"] = d.ton / d["count"]
P = d.pivot(index="industry", columns="year", values="lot")
C = d.pivot(index="industry", columns="year", values="count")
T = d.pivot(index="industry", columns="year", values="ton")
out = {}
rows = []
for ind in ["鉱業", "製造業", "卸売業", "倉庫業", "合計"]:
    r = dict(industry=ind, lot_2005=P.loc[ind, 2005], lot_2021=P.loc[ind, 2021], lot_pct=(P.loc[ind, 2021] / P.loc[ind, 2005] - 1) * 100,
             count_pct=(C.loc[ind, 2021] / C.loc[ind, 2005] - 1) * 100, ton_pct=(T.loc[ind, 2021] / T.loc[ind, 2005] - 1) * 100,
             count_share_2021=C.loc[ind, 2021] / C.loc["合計", 2021] * 100)
    rows.append(r); out[ind] = {k: round(float(v), 2) for k, v in r.items() if k != "industry"}
pd.DataFrame(rows).to_csv(R / "requestion_industry.csv", index=False, float_format="%.4f")
m = pd.read_csv(ROOT / "data" / "modes.csv")
k = m[m["mode"] == "一車貸切"].set_index("year")
out["charter"] = {"count_2005": round(float(k.loc[2005, "count"])), "count_2021": round(float(k.loc[2021, "count"])),
                  "lot_2005": round(float(k.loc[2005, "ton"] / k.loc[2005, "count"]), 3), "lot_2021": round(float(k.loc[2021, "ton"] / k.loc[2021, "count"]), 3),
                  "ton_pct": round(float((k.loc[2021, "ton"] / k.loc[2005, "ton"] - 1) * 100), 1)}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
