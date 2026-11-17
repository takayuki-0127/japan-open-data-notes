"""問い直し：比率が下がったのは、借金（地方債）の額が減ったからか、貯金（積立金）が増えたからか、それとも分母（標準財政規模）が大きくなったからか。
（地方債−積立金）÷標準財政規模 の2009→2024年度の変化を、地方債の額の変化・積立金の額の変化・分母の変化の3つに分ける（合計の額で。3つの和は変化と一致）。人口規模別も。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
d = pd.read_csv(R / "muni_year_ratio.csv", dtype={"code": str})
LABELS = ["5千人未満", "5千〜1万人", "1万〜3万人", "3万〜10万人", "10万〜30万人", "30万人以上"]


def split(g0, g1):
    D0, F0, S0 = g0.debt.sum(), g0.fund.sum(), g0.sfs.sum()
    D1, F1, S1 = g1.debt.sum(), g1.fund.sum(), g1.sfs.sum()
    tot = 100 * ((D1 - F1) / S1 - (D0 - F0) / S0)
    e_d = 100 * (D1 - D0) / S0
    e_f = -100 * (F1 - F0) / S0
    e_s = 100 * (D1 - F1) * (1 / S1 - 1 / S0)
    assert abs(tot - e_d - e_f - e_s) < 1e-9
    return {"net_2009": round(100 * (D0 - F0) / S0, 1), "net_2024": round(100 * (D1 - F1) / S1, 1), "change_pt": round(tot, 1),
            "debt_effect_pt": round(e_d, 1), "fund_effect_pt": round(e_f, 1), "denominator_effect_pt": round(e_s, 1),
            "debt_change_pct": round(100 * (D1 / D0 - 1), 1), "fund_change_pct": round(100 * (F1 / F0 - 1), 1), "sfs_change_pct": round(100 * (S1 / S0 - 1), 1)}


y0, y1 = d[d.year == 2009], d[d.year == 2024]
rows = [{"group": "全体", **split(y0, y1)}]
# 規模は2024年度の人口で団体をそろえる（2009年度にも同じ名前である団体）
k = y1.set_index("key")["size"]
y0s = y0[y0.key.isin(k.index)].assign(size24=lambda x: x.key.map(k))
for s in LABELS:
    rows.append({"group": s, **split(y0s[y0s.size24 == s], y1[y1["size"] == s])})
t = pd.DataFrame(rows)
t.to_csv(R / "requestion_split.csv", index=False)
a = t.iloc[0]
out = {"question": "比率の低下は、地方債の減少か、積立金の増加か、分母の拡大か",
       "all": {c: float(a[c]) for c in t.columns if c != "group"},
       "largest": max(["debt_effect_pt", "fund_effect_pt", "denominator_effect_pt"], key=lambda c: -a[c]),
       "small_fund_effect_pt": float(t.set_index("group").loc["5千人未満", "fund_effect_pt"]),
       "large_fund_effect_pt": float(t.set_index("group").loc["30万人以上", "fund_effect_pt"])}
m = json.loads((R / "main.json").read_text(encoding="utf-8"))
m["requestion"] = out
(R / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(t.to_string()); print(out)
