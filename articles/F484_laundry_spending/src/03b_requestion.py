"""問い直し（結果を見てから足した）：どの年齢の世帯で減ったのか（2015→2025年、3年平均でも）。消費支出に占める割合も見る。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
age = pd.read_csv(ROOT / "data" / "laundry_age.csv")
AGES = ["平均", "29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
L = age[age.item == "洗濯代"].pivot(index="year", columns="age", values="yen")[AGES]
C = age[age.item == "消費支出"].pivot(index="year", columns="age", values="yen")[AGES]
t = pd.DataFrame({
    "yen_2015": L.loc[2015], "yen_2025": L.loc[2025],
    "change_pct": (L.loc[2025] / L.loc[2015] - 1) * 100,
    "change_3yr_pct": (L.loc[2023:2025].mean() / L.loc[2015:2017].mean() - 1) * 100,
    "share_2015_pct": L.loc[2015] / C.loc[2015] * 100, "share_2025_pct": L.loc[2025] / C.loc[2025] * 100,
}).round(3)
t.to_csv(R / "requestion_by_age.csv")
L.to_csv(R / "laundry_by_age.csv")
sub = t.drop(index="平均")
out = {
    "change_pct": {k: round(float(v), 1) for k, v in t.change_pct.items()},
    "change_3yr_pct": {k: round(float(v), 1) for k, v in t.change_3yr_pct.items()},
    "yen_2015": {k: float(v) for k, v in t.yen_2015.items()}, "yen_2025": {k: float(v) for k, v in t.yen_2025.items()},
    "largest_drop_age": str(sub.change_pct.idxmin()), "smallest_drop_age": str(sub.change_pct.idxmax()),
    "top_spender_2015": str(sub.yen_2015.idxmax()), "top_spender_2025": str(sub.yen_2025.idxmax()),
}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
