"""問い直し（結果を見てから足した）：家計の切り花の支出の減少は、名目では買う回数の減少だった（1回あたりの名目の額はほぼ同じ）。
では、買う回数・支出が減ったのは、世帯の年齢の構成が変わったからか、どの年齢でも減ったからか。
2002年と2025年の年齢階級別の支出と世帯数分布（重み）で、変化を「年齢の構成」と「年齢の中」に分ける（シフトシェア分解）。
分解の順番による差を避けるため、両方の年の重みの平均・支出の平均を使う対称な分解にする。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"; R = ROOT / "results"
A = pd.read_csv(D / "kakei_cutflower_age.csv")
AGES = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]


def table(y):
    q = A[(A.year == y) & (A.age.isin(AGES))].set_index("age").loc[AGES]
    return q.assign(w=q.weight / q.weight.sum())


def decompose(y0, y1):
    a, b = table(y0), table(y1)
    total0 = (a.w * a.spend).sum(); total1 = (b.w * b.spend).sum()
    comp = ((b.w - a.w) * (a.spend + b.spend) / 2).sum()      # 年齢の構成が変わった分
    within = (((b.spend - a.spend) * (a.w + b.w) / 2)).sum()   # 年齢の中で変わった分
    return {"y0": y0, "y1": y1, "weighted_avg_y0": round(total0, 0), "weighted_avg_y1": round(total1, 0), "change": round(total1 - total0, 0),
            "composition": round(comp, 0), "within": round(within, 0), "within_share_pct": round(within / (total1 - total0) * 100, 1),
            "fixed_weight_y0_pct": round(((a.w * b.spend).sum() / total0 - 1) * 100, 1)}


out = {"decomp_2002_2025": decompose(2002, 2025), "decomp_2015_2025": decompose(2015, 2025)}
a, b = table(2002), table(2025)
rows = []
for ag in AGES:
    rows.append({"age": ag, "spend_2002": a.loc[ag, "spend"], "spend_2025": b.loc[ag, "spend"], "pct_spend": round((b.loc[ag, "spend"] / a.loc[ag, "spend"] - 1) * 100, 1),
                 "freq_2002": a.loc[ag, "freq_per100"], "freq_2025": b.loc[ag, "freq_per100"], "pct_freq": round((b.loc[ag, "freq_per100"] / a.loc[ag, "freq_per100"] - 1) * 100, 1),
                 "w_2002_pct": round(a.loc[ag, "w"] * 100, 1), "w_2025_pct": round(b.loc[ag, "w"] * 100, 1)})
T = pd.DataFrame(rows)
T.to_csv(R / "requestion_age.csv", index=False)
out["age_table"] = {r.age: {"pct_spend": float(r.pct_spend), "spend_2002": float(r.spend_2002), "spend_2025": float(r.spend_2025),
                            "w_2002_pct": float(r.w_2002_pct), "w_2025_pct": float(r.w_2025_pct)} for r in T.itertuples()}
out["n_age_groups_down"] = int((T.pct_spend < 0).sum())
# 年齢別の推移（図のため）
P = A[A.age.isin(AGES)].pivot_table(index="year", columns="age", values="spend")[AGES]
P.reset_index().to_csv(R / "spend_by_age_year.csv", index=False)
M = json.load(open(R / "main.json", encoding="utf-8"))
M["requestion"] = out
json.dump(M, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(T.to_string()); print(json.dumps(out, ensure_ascii=False, indent=1))
