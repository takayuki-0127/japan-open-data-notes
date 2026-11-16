"""問い直し（結果を見てから足した）：2025年に米がパンを上回ったのは、どの年齢の世帯でもか。
世帯主の年齢階級別に、パン÷米の比を2019・2023・2025年で比べる。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
g = pd.read_csv(ROOT / "data" / "grain.csv")
GROUPS = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
rows = []
for y in [2002, 2011, 2019, 2023, 2024, 2025]:
    for grp in ["平均"] + GROUPS:
        x = g[(g.year == y) & (g.group == grp)].set_index("item").amount
        rows.append({"year": y, "group": grp, "rice": x["rice"], "bread": x["bread"], "ratio": round(float(x["bread"] / x["rice"]), 3)})
t = pd.DataFrame(rows)
t.to_csv(R / "ratio_by_age.csv", index=False)
res = {
    str(y): {grp: float(t[(t.year == y) & (t.group == grp)].ratio.iloc[0]) for grp in ["平均"] + GROUPS} for y in [2002, 2011, 2019, 2023, 2024, 2025]
}
res["groups_bread_over_rice_2025"] = [grp for grp in GROUPS if res["2025"][grp] > 1]
res["groups_bread_over_rice_2023"] = [grp for grp in GROUPS if res["2023"][grp] > 1]
res["groups_bread_over_rice_2002"] = [grp for grp in GROUPS if res["2002"][grp] > 1]
(R / "requestion.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(t.pivot(index="group", columns="year", values="ratio").loc[["平均"] + GROUPS])
