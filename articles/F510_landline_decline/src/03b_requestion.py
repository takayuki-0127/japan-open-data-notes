"""問い直し（結果を見てから足した）：0ABJ-IP による置き換わりは、いつ止まったのか。
期間ごとの置き換わりの割合と、四半期の 0ABJ-IP の最高の時点、NTT東西以外の固定電話の動き。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
w = pd.read_csv(ROOT / "data" / "series.csv").pivot(index="date", columns="series", values="value").sort_index()
a = w[w.index.str.endswith("-03")].copy()
a.index = [int(i[:4]) - 1 for i in a.index]
LAST = int(a.index.max())


def r(x, k=1):
    return round(float(x), k)


rows = []
for p0, p1 in [(2004, 2010), (2010, 2016), (2016, 2022), (2022, LAST)]:
    dd = a.fixed_total[p0] - a.fixed_total[p1]
    ii = a.ip_0abj[p1] - a.ip_0abj[p0]
    rows.append({"from_fy": p0, "to_fy": p1, "fixed_decrease": r(dd), "ip_0abj_increase": r(ii), "ratio_pct": r(100 * ii / dd),
                 "fixed_decrease_per_year": r(dd / (p1 - p0)), "ip_0abj_increase_per_year": r(ii / (p1 - p0))})
rp = pd.DataFrame(rows)
rp.to_csv(R / "replacement_by_period.csv", index=False)

q = w.ip_0abj.dropna()
comb = (a.fixed_total + a.ip_0abj).dropna()
comb_yoy = (comb / comb.shift(1) - 1) * 100
other = (a.fixed_total - a.ntt_total).dropna()
res = {
    "periods": rows,
    "ip_0abj_quarter_peak": q.idxmax(), "ip_0abj_quarter_peak_value": r(q.max()),
    "ip_0abj_latest": q.index[-1], "ip_0abj_latest_value": r(q.iloc[-1]),
    "fixed_latest": w.fixed_total.dropna().index[-1], "fixed_latest_value": r(w.fixed_total.dropna().iloc[-1]),
    "combined_yoy_last_pct": r(comb_yoy[LAST], 2),
    "combined_first_decline_fy": int(comb_yoy[comb_yoy < 0].index.min()),
    "combined_yoy_2016_pct": r(comb_yoy[2016], 2),
    "other_than_ntt_first": {"fy": int(other.index.min()), "value": r(other.iloc[0])},
    "other_than_ntt_peak": {"fy": int(other.idxmax()), "value": r(other.max())},
    "other_than_ntt_last": {"fy": LAST, "value": r(other.iloc[-1])},
}
(R / "requestion.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
