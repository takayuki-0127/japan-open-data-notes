"""問い直し（結果を見てから足した）。
Q1：二人以上の世帯で、外食の割合の伸びはいつ止まったのか。調理食品の割合の伸びは続いているのか。
    1963〜2019年（2020年からの落ち込みの前）の割合に、折れ線（1か所で傾きが変わる直線）を当てはめ、折れ目の年を探す。
Q2：単身世帯で外食＋調理食品の割合が下がったのと並んで、単身世帯の年齢・働く人の割合はどう動いたか（記述だけ）。
結果は results/requestion.json と results/requestion_breaks.csv。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
link = pd.read_csv(R / "shares_linked.csv", index_col=0)
d = pd.read_csv(ROOT / "data" / "food_spending.csv")


def broken_line(y, years, lo, hi):
    best = None
    x = years.astype(float)
    for b in range(lo, hi + 1):
        X = np.column_stack([np.ones_like(x), x - b, np.clip(x - b, 0, None)])
        coef, res, *_ = np.linalg.lstsq(X, y, rcond=None)
        sse = float(((y - X @ coef) ** 2).sum())
        if best is None or sse < best["sse"]:
            best = {"break_year": b, "sse": sse, "slope_before": float(coef[1]), "slope_after": float(coef[1] + coef[2])}
    X1 = np.column_stack([np.ones_like(x), x])
    c1, *_ = np.linalg.lstsq(X1, y, rcond=None)
    best["sse_straight"] = float(((y - X1 @ c1) ** 2).sum())
    return best


out = {"q1": {}}
rows = []
for col in ["away_pct", "prepared_pct", "both_pct"]:
    for lab, (a, b) in {"1963-2019": (1963, 2019), "1963-2007": (1963, 2007), "1970-2019": (1970, 2019)}.items():
        q = link.loc[a:b, col]
        res = broken_line(q.values, q.index.values, a + 5, b - 5)
        res = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in res.items()}
        res.update({"series": col, "window": lab, "slope_before_pt_per_10y": round(10 * res["slope_before"], 2),
                    "slope_after_pt_per_10y": round(10 * res["slope_after"], 2)})
        rows.append(res)
        out["q1"][f"{col}_{lab}"] = res
pd.DataFrame(rows).to_csv(R / "requestion_breaks.csv", index=False)

s = d[(d.series == "単身 2000-") & (d.kind == "名目")].pivot(index="year", columns="item", values="value")
sh = 100 * (s["外食"] + s["調理食品"]) / s["食料"]
out["q2"] = {"single_age": {str(y): float(s.loc[y, "年齢(歳)"]) for y in (2000, 2010, 2019, 2025)},
             "single_employed_ratio": {str(y): float(s.loc[y, "有業者比率"]) for y in (2000, 2010, 2019, 2025)},
             "single_both_pct": {str(y): round(float(sh.loc[y]), 1) for y in (2000, 2010, 2019, 2025)},
             "corr_both_pct_vs_age_2000_2019": round(float(np.corrcoef(sh.loc[2000:2019], s.loc[2000:2019, "年齢(歳)"])[0, 1]), 3),
             "corr_both_pct_vs_employed_2000_2019": round(float(np.corrcoef(sh.loc[2000:2019], s.loc[2000:2019, "有業者比率"])[0, 1]), 3)}
pd.DataFrame({"both_pct": sh, "age": s["年齢(歳)"], "employed_ratio": s["有業者比率"]}).to_csv(R / "requestion_single.csv")
with open(R / "requestion.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
print(pd.DataFrame(rows)[["series", "window", "break_year", "slope_before_pt_per_10y", "slope_after_pt_per_10y", "sse", "sse_straight"]].to_string())
print(json.dumps(out["q2"], ensure_ascii=False))
