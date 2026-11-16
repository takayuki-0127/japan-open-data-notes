"""問い直し（結果を見てから足した）：
研究費は2023〜2025年調査で急に伸びた（総額 19.7兆円→23.8兆円）。この3年の伸びはどの組織か。
人が増えたのか、1人当たりが増えたのか（研究費の対数差 ＝ 研究者数の対数差 ＋ 1人当たりの対数差）。比べるのは2020〜22年調査の平均と2023〜25年調査の平均。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
r3 = lambda x: round(float(x), 3)
R = pd.read_csv(RES / "researchers_by_sector.csv", index_col=0)
E = pd.read_csv(RES / "expenditure_by_sector.csv", index_col=0)
A, B = [2020, 2021, 2022], [2023, 2024, 2025]
SEC = ["business", "university", "public", "nonprofit", "total"]
rows = []
for s in SEC:
    de = 100 * np.log(E.loc[B, s].mean() / E.loc[A, s].mean()); dr = 100 * np.log(R.loc[B, s].mean() / R.loc[A, s].mean())
    rows.append(dict(sector=s, exp_dlog=r3(de), res_dlog=r3(dr), per_dlog=r3(de - dr), exp_change_100m=r3((E.loc[B, s].mean() - E.loc[A, s].mean()) / 100)))
t = pd.DataFrame(rows).set_index("sector")
tot = t.loc["total", "exp_change_100m"]
t["share_of_change"] = (100 * t.exp_change_100m / tot).round(3)
t.to_csv(RES / "requestion_recent.csv")
out = {"recent": t.to_dict(orient="index"), "total_2022_trillion": r3(E.loc[2022, "total"] / 1e6), "total_2025_trillion": r3(E.loc[2025, "total"] / 1e6)}
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(t.to_string()); print(out["total_2022_trillion"], out["total_2025_trillion"])
