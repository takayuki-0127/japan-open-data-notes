"""問い直し（結果を見てから足した）：実数ではインターネットが2021年にテレビを上回ったのに、調整済みの伸びでつなぐと上回らない。
差はどの年に生まれたのか。実数の前年比と調整済み前年比の差（調査対象の追加などによる段差）を年ごとに出す。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "annual.csv")
x = d[d.period_type == "年"]
v = x.pivot(index="year", columns="item", values="value")
g = x.pivot(index="year", columns="item", values="growth")
rows = []
for k in ["internet", "tv", "total"]:
    raw = (v[k] / v[k].shift(1) - 1) * 100
    for y in range(2007, int(v.index.max()) + 1):
        rows.append({"item": k, "year": y, "raw_growth": round(float(raw[y]), 2), "adjusted_growth": float(g[k][y]),
                     "gap": round(float(raw[y] - g[k][y]), 2)})
t = pd.DataFrame(rows)
t.to_csv(R / "raw_vs_adjusted.csv", index=False)
gi = t[t.item == "internet"].set_index("year")
big = gi[gi.gap.abs() >= 5]
res = {"internet_gap_years": {int(y): float(gi.gap[y]) for y in big.index},
       "internet_raw_2020": float(gi.raw_growth[2020]), "internet_adj_2020": float(gi.adjusted_growth[2020]),
       "internet_raw_2011": float(gi.raw_growth[2011]), "internet_adj_2011": float(gi.adjusted_growth[2011]),
       "tv_gap_max_abs": float(t[t.item == "tv"].gap.abs().max()),
       "internet_cum_raw_2006_last": round(float(v.internet.iloc[-1] / v.internet[2006]), 2),
       "internet_cum_adj_2006_last": round(float((1 + g.internet.loc[2007:] / 100).prod()), 2)}
(R / "requestion.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(gi.to_string()); print(res)
