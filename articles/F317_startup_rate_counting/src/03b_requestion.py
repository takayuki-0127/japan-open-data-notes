"""問い直し（結果を見てから足した）：
開業率は令和2年度（2020年度）だけ5.1%に跳ねた。どの産業の新規適用が増えたのか。
令和元年度→令和2年度の新規適用の増減を産業に分け、跳ねた分を除いた開業率（宿泊業，飲食サービス業を除く）も出す。
あわせて、平成29年度（2017年度）の建設業の新規適用の多さ（前後の年度の約2倍）も記録する。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
D, RES = ROOT / "data", ROOT / "results"
r3 = lambda x: round(float(x), 3)
d = pd.read_csv(D / "koyouhoken_by_industry.csv")
NAMES = d[d.fy == d.fy.max()].set_index("code").name.to_dict()
N = d.pivot(index="fy", columns="code", values="new"); S = d.pivot(index="fy", columns="code", values="stock_end")
ch = (N.loc[2020] - N.loc[2019]).drop("TOTAL").sort_values(ascending=False)
tot = float(N.loc[2020, "TOTAL"] - N.loc[2019, "TOTAL"])
Y = list(range(2018, 2026))
exM = 100 * (N.loc[Y, "TOTAL"] - N.loc[Y, "Ｍ"]) / (S.shift(1).loc[Y, "TOTAL"] - S.shift(1).loc[Y, "Ｍ"])
out = dict(total_change_2019_2020=int(tot), top_changes={f"{c} {NAMES[c]}": int(v) for c, v in ch.head(4).items()},
           share_M=r3(100 * ch["Ｍ"] / tot), rate_2020_exM=r3(exM.loc[2020]), rate_2019_exM=r3(exM.loc[2019]),
           M_new=[int(N.loc[y, "Ｍ"]) for y in [2019, 2020, 2021, 2022]],
           construction_new_2017_2019=[int(N.loc[y, "Ｄ"]) for y in [2017, 2018, 2019]],
           rate_exM_by_fy={int(y): r3(v) for y, v in exM.items()})
pd.DataFrame({"change_2019_2020": ch, "name": [NAMES[c] for c in ch.index]}).to_csv(RES / "requestion_2020_change.csv")
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0))
