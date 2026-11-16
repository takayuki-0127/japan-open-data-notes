"""問い直し（結果を見てから足した）。
Q：家計調査の二人以上の世帯では、構成の変化（−2.1ポイント）より勤労者世帯の黒字率の上がり（＋5.2ポイント）が大きく、
   国民経済計算の貯蓄率の低下と向きが合わない。国民経済計算では、消費が所得より伸びた。所得の伸びが小さかったのは、どの項目のせいか。
   1994→2024年と2000→2024年の可処分所得（純）の変化を、受取・支払の項目に分ける。
結果は results/requestion.json と results/requestion_income_components.csv。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
c = pd.read_csv(ROOT / "data" / "sna_household_income_components.csv").pivot(index="year", columns="item", values="value_bn")
s = pd.read_csv(ROOT / "data" / "sna_household_saving.csv")
s = s[s.kind == "可処分所得ベース"].set_index("year")
SIGN = {"雇用者報酬": 1, "営業余剰・混合所得（純）": 1, "財産所得（受取）": 1, "財産所得（支払）": -1, "社会給付（現物以外）": 1,
        "その他の経常移転（受取）": 1, "所得・富等に課される経常税": -1, "純社会負担": -1, "その他の経常移転（支払）": -1}
out = {}
rows = []
for a, b in [(1994, 2024), (2000, 2024)]:
    d = {k: round(SIGN[k] * (c.loc[b, k] - c.loc[a, k]) / 1000, 2) for k in SIGN}  # 兆円
    total = round((c.loc[b, "可処分所得（純）"] - c.loc[a, "可処分所得（純）"]) / 1000, 2)
    sub = {k: round((c.loc[b, k] - c.loc[a, k]) / 1000, 2) for k in ["うち営業余剰（持ち家）", "うち混合所得"]}
    dc = round((s.loc[b, "consumption_bn"] - s.loc[a, "consumption_bn"]) / 1000, 2)
    out[f"{a}_{b}"] = {"d_disposable_income_tyen": total, "sum_components_tyen": round(sum(d.values()), 2), "components_tyen": d,
                       "operating_surplus_detail_tyen": sub, "d_consumption_tyen": dc}
    for k, v in d.items():
        rows.append({"period": f"{a}-{b}", "item": k, "contribution_tyen": v})
pd.DataFrame(rows).to_csv(R / "requestion_income_components.csv", index=False)
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
