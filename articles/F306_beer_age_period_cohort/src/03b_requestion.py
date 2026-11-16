"""問い直し（結果を見てから足した）：
若い世帯ほど大きく減ったが、「世代＋時代」の当てはまりは「年齢＋時代」に勝たなかった。
では、同じ世代を10年後まで追うと、年をとるにつれて買う量が増える（年齢の伸び）は、新しい世代でも同じように起きているのか。
3年平均（2004〜06、2014〜16、2023〜25年）で、隣の年齢の階級へ移ったときの数量の比（10年後 ÷ 今）を世代ごとに比べる。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "alcohol_by_age.csv")
P = d[d.item == "beer"].pivot(index="year", columns="age", values="quantity")
AG = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
PER = {"2005年ごろ": [2004, 2005, 2006], "2015年ごろ": [2014, 2015, 2016], "2024年ごろ": [2023, 2024, 2025]}
r3 = lambda x: round(float(x), 3)
M = pd.DataFrame({k: P.loc[v, AG].mean() for k, v in PER.items()}).T
M.round(3).to_csv(RES / "requestion_period_means.csv")
rows = []
keys = list(PER)
for k0, k1 in ((keys[0], keys[1]), (keys[1], keys[2])):
    for i in range(len(AG) - 1):
        a0, a1 = AG[i], AG[i + 1]
        rows.append(dict(from_period=k0, to_period=k1, age_from=a0, age_to=a1, q_from=r3(M.loc[k0, a0]), q_to=r3(M.loc[k1, a1]),
                         ratio=r3(M.loc[k1, a1] / M.loc[k0, a0])))
c = pd.DataFrame(rows); c.to_csv(RES / "requestion_cohort_growth.csv", index=False)
w = c.pivot(index="age_from", columns="from_period", values="ratio").loc[AG[:-1]]
out = dict(ratios={a: [r3(w.loc[a, keys[0]]), r3(w.loc[a, keys[1]])] for a in w.index},
           same_age_30s=[r3(M.loc[k, "30～39歳"]) for k in keys], same_age_20s=[r3(M.loc[k, "29歳以下"]) for k in keys],
           n_ratio_lower_in_newer=int((w[keys[1]] < w[keys[0]]).sum()),
           change_2015_2024_pct={a: r3(100 * (M.loc[keys[2], a] / M.loc[keys[1], a] - 1)) for a in AG})
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0)); print(M.round(2).to_string())
