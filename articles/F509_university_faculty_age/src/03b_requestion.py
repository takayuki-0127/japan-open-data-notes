"""問い直し（結果を見てから足した）：
(a) 40歳未満の人数そのものは減ったのか。全体の3割にするには、2025年度で何人の差があるか。
(b) 同じ年齢の層で、職名の内訳はどう変わったか（35〜39歳、40〜44歳、45〜49歳）。"""
import json
import pandas as pd
from common import ROOT, load, harmonized, POS_ORDER

R = ROOT / "results"
d = load()
t = d[d.position == "計"]

# (a) 40歳未満の人数
u = t[t.age < 40].groupby(["setter", "year"]).n.sum().unstack("setter")[["計", "国立", "公立", "私立"]]
alln = t.groupby(["setter", "year"]).n.sum().unstack("setter")[["計", "国立", "公立", "私立"]]
u.to_csv(R / "u40_counts.csv")
n25 = int(alln.loc[2025, "計"]); u25 = int(u.loc[2025, "計"])
need = int(round(0.3 * n25)) - u25
low_year = int(u["計"].idxmin())

# (b) 年齢の層ごとの職名の内訳
h = harmonized(d)
bands = [(35, 40), (40, 45), (45, 50)]
rows = []
for y in (1998, 2025):
    for lo, hi in bands:
        g = h[(h.year == y) & (h.age >= lo) & (h.age < hi)]
        n = g.groupby("pos").n.sum()
        for p in POS_ORDER:
            rows.append({"year": y, "band": f"{lo}〜{hi - 1}歳", "pos": p, "n": int(n.get(p, 0)),
                         "share_pct": round(100 * float(n.get(p, 0)) / float(n.sum()), 2)})
bd = pd.DataFrame(rows)
bd.to_csv(R / "position_mix_by_age.csv", index=False)


def sh(y, band, p):
    return float(bd[(bd.year == y) & (bd.band == band) & (bd.pos == p)].share_pct.iloc[0])


res = {
    "u40_count": {int(k): int(v) for k, v in u["計"].items()},
    "u40_count_low_year": low_year,
    "u40_change_1998_2025_pct": round(100 * (u25 / int(u.loc[1998, "計"]) - 1), 1),
    "total_change_1998_2025_pct": round(100 * (n25 / int(alln.loc[1998, "計"]) - 1), 1),
    "u40_change_2022_2025": int(u.loc[2025, "計"] - u.loc[2022, "計"]),
    "u40_count_setter_1998": {s: int(u.loc[1998, s]) for s in ["国立", "公立", "私立"]},
    "u40_count_setter_2025": {s: int(u.loc[2025, s]) for s in ["国立", "公立", "私立"]},
    "need_for_30pct_2025": need,
    "target_30pct_n_2025": int(round(0.3 * n25)),
    "mix_40_44": {str(y): {p: sh(y, "40〜44歳", p) for p in POS_ORDER} for y in (1998, 2025)},
    "mix_35_39": {str(y): {p: sh(y, "35〜39歳", p) for p in POS_ORDER} for y in (1998, 2025)},
    "mix_45_49": {str(y): {p: sh(y, "45〜49歳", p) for p in POS_ORDER} for y in (1998, 2025)},
}
(R / "requestion.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
